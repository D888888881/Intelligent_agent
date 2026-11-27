import base64
import io
import logging
import time

import httpx
from django.conf import settings
from PIL import Image

logger = logging.getLogger(__name__)

TERMINAL_STATUSES = frozenset({"succeeded", "failed", "violation"})


class GrsaiError(Exception):
    pass


class GrsaiDownloadError(GrsaiError):
    """Grsai 任务已成功，但从 CDN 拉取成片失败。"""

    def __init__(self, message: str, *, image_url: str = ""):
        super().__init__(message)
        self.image_url = image_url


class GrsaiTransientError(GrsaiError):
    """HTTP 断连、握手超时等瞬时错误，可重试生图或轮询。"""


class GrsaiRemoteTaskError(GrsaiTransientError):
    """中转站任务已经提交。后续只能继续查询或下载，不能再 POST 一次新的生图。"""

    def __init__(self, message: str, *, task_id: str = "", image_url: str = ""):
        super().__init__(message)
        self.task_id = task_id or ""
        self.image_url = image_url or ""


def _headers() -> dict:
    key = (settings.GRSAI_API_KEY or "").strip()
    if not key:
        raise GrsaiError("未配置 GRSAI_API_KEY")
    auth = key if key.lower().startswith("bearer ") else f"Bearer {key}"
    return {
        "Authorization": auth,
        "Content-Type": "application/json",
    }


def _api_root() -> str:
    return (settings.GRSAI_BASE_URL or "https://grsai.dakka.com.cn").rstrip("/")


def _public_file_url(file_field) -> str | None:
    if not file_field:
        return None
    rel = file_field.url
    if rel.startswith("http://") or rel.startswith("https://"):
        return rel
    name = (file_field.name or "").lstrip("/")
    if getattr(settings, "COS_USE_STORAGE", False) and name:
        local = settings.MEDIA_ROOT / name
        if local.is_file():
            base = (getattr(settings, "PUBLIC_SITE_URL", None) or "").strip().rstrip("/")
            if base:
                return f"{base}/media/{name}"
    base = (getattr(settings, "PUBLIC_SITE_URL", None) or "").strip().rstrip("/")
    if not base:
        return None
    if not rel.startswith("/"):
        rel = f"/{rel}"
    return f"{base}{rel}"


def _bytes_to_data_url(raw: bytes, mime: str = "image/jpeg") -> str:
    b64 = base64.standard_b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _optimize_image_bytes(raw: bytes, *, mime_hint: str = "") -> tuple[bytes, str]:
    max_edge = int(getattr(settings, "GRSAI_REF_MAX_EDGE", 1280))
    max_bytes = int(getattr(settings, "GRSAI_REF_MAX_BYTES", 850_000))
    if len(raw) <= max_bytes and not mime_hint.lower().endswith(("heic", "heif")):
        try:
            img = Image.open(io.BytesIO(raw))
            w, h = img.size
            if max(w, h) <= max_edge:
                out_mime = mime_hint or "image/png"
                if "jpeg" in out_mime or "jpg" in out_mime:
                    return raw, "image/jpeg"
                return raw, out_mime if out_mime.startswith("image/") else "image/png"
        except Exception:
            pass

    img = Image.open(io.BytesIO(raw))
    img = img.convert("RGB")
    img.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    quality = 88
    for _ in range(4):
        buf.seek(0)
        buf.truncate(0)
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        if buf.tell() <= max_bytes or quality <= 72:
            break
        quality -= 4
    return buf.getvalue(), "image/jpeg"


def file_field_to_image_payload(file_field, mime: str = "image/png") -> str:
    """Storage 文件 → Grsai images 项（URL 或压缩 data URL）。"""
    if not file_field:
        raise GrsaiError("缺少图片文件")
    mode = (getattr(settings, "GRSAI_REFERENCE_IMAGE_MODE", "auto") or "auto").lower()
    public_url = _public_file_url(file_field)
    if public_url and mode in ("auto", "url"):
        return public_url
    if mode == "url" and not public_url:
        logger.warning("GRSAI_REFERENCE_IMAGE_MODE=url 但未配置 PUBLIC_SITE_URL，回退 base64")
    with file_field.open("rb") as f:
        raw = f.read()
    optimized, out_mime = _optimize_image_bytes(raw, mime_hint=mime or "")
    return _bytes_to_data_url(optimized, out_mime)


def attachment_to_image_payload(attachment) -> str:
    """Attachment → Grsai images 项（优先公网 URL，否则压缩 base64）。"""
    mime = attachment.mime_type or "image/png"
    mode = (getattr(settings, "GRSAI_REFERENCE_IMAGE_MODE", "auto") or "auto").lower()
    public_url = _public_file_url(attachment.file)
    if public_url and mode in ("auto", "url"):
        return public_url
    if mode == "url" and not public_url:
        logger.warning("GRSAI_REFERENCE_IMAGE_MODE=url 但未配置 PUBLIC_SITE_URL，回退 base64")
    with attachment.file.open("rb") as f:
        raw = f.read()
    optimized, out_mime = _optimize_image_bytes(raw, mime_hint=mime)
    return _bytes_to_data_url(optimized, out_mime)


def storage_file_to_image_payload(file_field, mime: str = "image/png") -> str:
    return file_field_to_image_payload(file_field, mime=mime)


def _aspect_for_gpt(aspect_ratio: str) -> str:
    mapping = {
        "1:1": "1024x1024",
        "16:9": "1672x941",
        "9:16": "941x1672",
        "4:3": "1443x1090",
        "3:4": "1090x1443",
        "3:2": "1536x1024",
        "2:3": "1024x1536",
    }
    if "x" in aspect_ratio:
        return aspect_ratio
    return mapping.get(aspect_ratio, settings.GRSAI_GPT_ASPECT_RATIO)


def build_generate_payload(
    *,
    model: str,
    prompt: str,
    reference_images: list[str] | None = None,
    aspect_ratio: str = "1:1",
) -> dict:
    payload = {
        "model": model,
        "prompt": prompt[:8000],
        "images": reference_images or [],
        "replyType": settings.GRSAI_REPLY_TYPE,
    }
    if model.startswith("gpt-image"):
        payload["aspectRatio"] = _aspect_for_gpt(aspect_ratio)
        payload["quality"] = settings.GRSAI_GPT_IMAGE_QUALITY
        if settings.GRSAI_GPT_BACKGROUND:
            payload["background"] = settings.GRSAI_GPT_BACKGROUND
    else:
        payload["aspectRatio"] = aspect_ratio or settings.GRSAI_ASPECT_RATIO
        payload["imageSize"] = settings.GRSAI_IMAGE_SIZE
    return payload


def payload_images_summary(payload: dict) -> str:
    images = payload.get("images") or []
    parts: list[str] = []
    for img in images:
        if not isinstance(img, str):
            parts.append("?")
            continue
        if img.startswith("data:"):
            parts.append(f"b64~{len(img) // 1024}KB")
        elif img.startswith("http"):
            parts.append("url")
        else:
            parts.append(f"str~{len(img) // 1024}KB")
    return f"count={len(images)} [{', '.join(parts) or '-'}]"


def _http_call_attempts() -> int:
    return max(1, int(getattr(settings, "GRSAI_HTTP_RETRIES", 3)))


def _post_read_timeout(payload: dict) -> float:
    cap = float(_per_image_max_seconds())
    base = float(getattr(settings, "GRSAI_POST_READ_TIMEOUT", cap))
    base = min(base, cap)
    images = payload.get("images") or []
    extra = 0.0
    for img in images:
        if isinstance(img, str) and img.startswith("data:"):
            extra += min(60.0, len(img) / (400 * 1024))
    return min(cap, base + extra)


def _is_transient_exc(exc: BaseException) -> bool:
    if isinstance(exc, GrsaiTransientError):
        return True
    proxy_error = getattr(httpx, "ProxyError", None)
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError)):
        return True
    if proxy_error and isinstance(exc, proxy_error):
        return True
    text = str(exc).lower()
    needles = (
        "disconnected",
        "handshake",
        "timeout",
        "timed out",
        "connection reset",
        "connection aborted",
        "failed to connect",
        "proxy",
        "eof occurred",
        "server_timeout",
    )
    return any(n in text for n in needles)


def _task_error_retriable(data: dict) -> bool:
    err = (data.get("error") or data.get("message") or "").lower()
    return "server_timeout" in err or err in ("timeout", "server busy")


def _post_generate(payload: dict) -> dict:
    url = f"{_api_root()}/v1/api/generate"
    attempts = _http_call_attempts()
    read_timeout = _post_read_timeout(payload)
    last: Exception | None = None
    summary = payload_images_summary(payload)
    for n in range(attempts):
        try:
            timeout = httpx.Timeout(read_timeout, connect=45.0)
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, headers=_headers(), json=payload)
            if resp.status_code >= 400:
                try:
                    body = resp.json()
                    err = body.get("error") or body
                except Exception:
                    err = resp.text
                raise GrsaiError(f"Grsai 请求失败 ({resp.status_code}): {err}")
            return resp.json()
        except GrsaiError:
            raise
        except Exception as exc:
            last = exc
            if n + 1 < attempts and _is_transient_exc(exc):
                logger.warning(
                    "Grsai POST retry %s/%s %s: %s",
                    n + 1,
                    attempts,
                    summary,
                    exc,
                )
                time.sleep(min(2 * (n + 1), 6))
                continue
            if _is_transient_exc(exc):
                raise GrsaiTransientError(f"Grsai 提交断连: {exc}") from exc
            raise GrsaiError(str(exc)) from exc
    raise GrsaiTransientError(f"Grsai 提交失败: {last}") from last


def _get_result(task_id: str) -> dict:
    url = f"{_api_root()}/v1/api/result"
    attempts = _http_call_attempts()
    last: Exception | None = None
    for n in range(attempts):
        try:
            with httpx.Client(timeout=httpx.Timeout(60.0, connect=45.0)) as client:
                resp = client.get(url, headers=_headers(), params={"id": task_id})
            if resp.status_code >= 400:
                try:
                    body = resp.json()
                    err = body.get("error") or body
                except Exception:
                    err = resp.text
                raise GrsaiError(f"Grsai 查询失败 ({resp.status_code}): {err}")
            return resp.json()
        except GrsaiError:
            raise
        except Exception as exc:
            last = exc
            if n + 1 < attempts and _is_transient_exc(exc):
                logger.warning("Grsai GET result retry %s/%s task=%s: %s", n + 1, attempts, task_id, exc)
                time.sleep(min(2 * (n + 1), 6))
                continue
            if _is_transient_exc(exc):
                raise GrsaiTransientError(f"Grsai 轮询断连: {exc}") from exc
            raise GrsaiError(str(exc)) from exc
    raise GrsaiTransientError(f"Grsai 查询失败: {last}") from last


def _per_image_max_seconds() -> int:
    return int(getattr(settings, "GRSAI_PER_IMAGE_MAX_SECONDS", 180))


def per_shot_active_poll_seconds(shot_index: int | None, model: str | None = None) -> int:
    """1–7 张到点就先继续后面的图。8–9 张不参与回收，等到中转站自己的时限。"""
    if shot_index in (8, 9):
        return _poll_budget_seconds(model)
    return max(30, _per_image_max_seconds())


def deferred_recovery_wait_seconds() -> int:
    return max(0, int(getattr(settings, "GRSAI_DEFERRED_RECOVERY_WAIT_SECONDS", 30)))


def is_deferrable_shot_index(shot_index: int | None) -> bool:
    try:
        idx = int(shot_index or 0)
    except (TypeError, ValueError):
        return False
    return 1 <= idx <= 7


def _poll_budget_seconds(model: str | None) -> int:
    """轮询时限与提交耗时分开。提交很慢时不能把已经在中转站跑着的任务提前放弃。"""
    name = (model or "").lower()
    if "gpt-image" in name:
        budget = int(getattr(settings, "GRSAI_GPT_POLL_TIMEOUT", 900))
    else:
        budget = int(getattr(settings, "GRSAI_POLL_TIMEOUT", 600))
    cap = int(getattr(settings, "GRSAI_POLL_MAX_SECONDS", 1200))
    return max(30, min(budget, cap))


def is_per_shot_poll_timeout(exc: BaseException) -> bool:
    """单张轮询达到 GRSAI_PER_IMAGE_MAX_SECONDS，应跳过该张继续套图。"""
    text = str(exc)
    return "单张超时" in text or "提交后无剩余轮询时间" in text


def _result_download_attempts() -> int:
    return max(1, int(getattr(settings, "GRSAI_RESULT_DOWNLOAD_RETRIES", 4)))


def _result_download_timeout() -> httpx.Timeout:
    connect = float(getattr(settings, "GRSAI_RESULT_DOWNLOAD_CONNECT", 45))
    read = float(getattr(settings, "GRSAI_RESULT_DOWNLOAD_READ", 120))
    return httpx.Timeout(read, connect=connect)


def _download_result_image(image_url: str) -> bytes:
    attempts = _result_download_attempts()
    last_exc: Exception | None = None
    for n in range(attempts):
        try:
            with httpx.Client(timeout=_result_download_timeout()) as client:
                img_resp = client.get(image_url, follow_redirects=True)
            if img_resp.status_code >= 400:
                raise GrsaiDownloadError(f"下载图片失败 HTTP {img_resp.status_code}")
            if not img_resp.content:
                raise GrsaiDownloadError("下载图片失败：响应体为空")
            logger.info(
                "Grsai result downloaded bytes=%s attempt=%s/%s",
                len(img_resp.content),
                n + 1,
                attempts,
            )
            return img_resp.content
        except GrsaiDownloadError:
            raise
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "Grsai result download failed attempt=%s/%s url=%s err=%s",
                n + 1,
                attempts,
                image_url[:120],
                exc,
            )
            if n + 1 < attempts:
                time.sleep(min(2 * (n + 1), 8))
    raise GrsaiDownloadError(
        f"Grsai 任务已成功，但下载成片失败（已重试 {attempts} 次）: {last_exc}",
        image_url=image_url,
    ) from last_exc


def wait_for_task(task_id: str, *, model: str | None = None, max_seconds: int | None = None) -> dict:
    if max_seconds is None:
        max_seconds = _per_image_max_seconds()
    started = time.time()
    deadline = started + max_seconds
    interval = settings.GRSAI_POLL_INTERVAL
    last = None
    polls = 0

    while time.time() < deadline:
        try:
            data = _get_result(task_id)
        except GrsaiTransientError as exc:
            last = {"error": str(exc), "status": "running"}
            logger.warning("Grsai poll transient error task=%s: %s", task_id, exc)
            time.sleep(interval)
            continue
        last = data
        polls += 1
        status = (data.get("status") or "").lower()
        if status in TERMINAL_STATUSES:
            logger.info(
                "Grsai task %s done status=%s polls=%s progress=%s elapsed=%.0fs err=%s",
                task_id,
                status,
                polls,
                data.get("progress"),
                time.time() - started,
                data.get("error"),
            )
            return data
        if polls % 10 == 0:
            logger.info(
                "Grsai task %s waiting status=%s progress=%s elapsed=%.0fs",
                task_id,
                status,
                data.get("progress"),
                time.time() - started,
            )
        time.sleep(interval)

    raise GrsaiError(f"Grsai 单张超时 ({max_seconds}s) task={task_id}: {last}")


def relay_task_terminal_bytes(data: dict, *, task_id: str) -> bytes:
    status = (data.get("status") or "").lower()
    if status == "violation":
        raise GrsaiError(data.get("error") or "内容审核未通过")
    if status != "succeeded":
        err = data.get("error") or data.get("message") or f"生成失败: {status}"
        raise GrsaiError(f"{err} (task={task_id})")
    results = data.get("results") or []
    if not results or not results[0].get("url"):
        raise GrsaiRemoteTaskError("Grsai 成功但未返回图片 URL", task_id=task_id)
    image_url = results[0]["url"]
    try:
        return _download_result_image(image_url)
    except GrsaiDownloadError as exc:
        raise GrsaiRemoteTaskError(
            str(exc),
            task_id=task_id,
            image_url=exc.image_url or image_url,
        ) from exc


def get_relay_task_snapshot(task_id: str) -> dict:
    if not task_id:
        raise GrsaiError("没有中转站任务 id")
    return _get_result(task_id)


def recover_deferred_task_bytes(
    task_id: str,
    *,
    image_url: str = "",
    model: str | None = None,
    grace_wait: int | None = None,
) -> bytes:
    """第 9 张后回收：先查一次，running 则 grace_wait 后再短轮询。"""
    grace = deferred_recovery_wait_seconds() if grace_wait is None else max(0, grace_wait)
    if image_url:
        try:
            return _download_result_image(image_url)
        except GrsaiDownloadError:
            pass
    data = get_relay_task_snapshot(task_id)
    status = (data.get("status") or "").lower()
    if status == "succeeded":
        return relay_task_terminal_bytes(data, task_id=task_id)
    if status in ("failed", "violation"):
        err = data.get("error") or data.get("message") or status
        raise GrsaiError(f"中转站任务已结束: {err} (task={task_id})")
    if grace > 0:
        logger.info("Grsai deferred task=%s still running, wait %ss", task_id, grace)
        time.sleep(grace)
    data = wait_for_task(task_id, model=model, max_seconds=60)
    return relay_task_terminal_bytes(data, task_id=task_id)


def _generate_once(
    *,
    prompt: str,
    model: str,
    reference_images: list[str] | None,
    aspect_ratio: str,
    shot_index: int | None = None,
) -> bytes:
    payload = build_generate_payload(
        model=model,
        prompt=prompt,
        reference_images=reference_images,
        aspect_ratio=aspect_ratio,
    )
    img_summary = payload_images_summary(payload)
    logger.info(
        "Grsai generate POST model=%s prompt_len=%s images=%s",
        model,
        len(payload.get("prompt") or ""),
        img_summary,
    )
    data = _post_generate(payload)
    status = (data.get("status") or "").lower()
    task_id = data.get("id")
    if not task_id:
        raise GrsaiError(f"Grsai 未返回任务 id: {data}")

    logger.info("Grsai task created id=%s model=%s status=%s", task_id, model, status)

    poll_cap = per_shot_active_poll_seconds(shot_index, model)
    try:
        if status == "running" or status not in TERMINAL_STATUSES:
            data = wait_for_task(task_id, model=model, max_seconds=poll_cap)
    except GrsaiError as exc:
        raise GrsaiRemoteTaskError(str(exc), task_id=str(task_id)) from exc

    try:
        return relay_task_terminal_bytes(data, task_id=str(task_id))
    except GrsaiRemoteTaskError:
        raise
    except GrsaiError as exc:
        err = str(exc)
        if _task_error_retriable(data):
            raise GrsaiTransientError(
                f"Grsai 上游超时或繁忙 ({err})，task={task_id}，images={img_summary}。"
                "若控制台无参数，多为请求体过大未入库；已限制单次参考图张数并压缩参考图。"
            ) from exc
        raise


def fetch_submitted_image(
    task_id: str,
    *,
    image_url: str = "",
    model: str | None = None,
    max_seconds: int | None = None,
) -> bytes:
    """继续取回已经提交的中转站任务，不发起新的生图。"""
    if image_url:
        try:
            return _download_result_image(image_url)
        except GrsaiDownloadError as exc:
            if not task_id:
                raise GrsaiRemoteTaskError(str(exc), image_url=exc.image_url or image_url) from exc
    if not task_id:
        raise GrsaiError("没有可继续的中转站任务")
    try:
        data = wait_for_task(task_id, model=model, max_seconds=max_seconds)
    except GrsaiError as exc:
        raise GrsaiRemoteTaskError(str(exc), task_id=task_id, image_url=image_url) from exc
    return relay_task_terminal_bytes(data, task_id=task_id)


def generate_image_bytes(
    *,
    prompt: str,
    model: str | None = None,
    reference_images: list[str] | None = None,
    aspect_ratio: str = "1:1",
    shot_index: int | None = None,
) -> bytes:
    model = model or settings.GRSAI_IMAGE_MODEL
    poll_cap = per_shot_active_poll_seconds(shot_index, model)
    extra_retries = max(0, int(getattr(settings, "GRSAI_PER_IMAGE_RETRIES", 1)))
    total_attempts = extra_retries + 1

    logger.info(
        "Grsai generate model=%s shot_index=%s active_poll_max=%ss attempts=%s",
        model,
        shot_index,
        poll_cap,
        total_attempts,
    )

    last_err: GrsaiError | None = None
    last_download_err: GrsaiDownloadError | None = None
    held_task_id = ""
    held_image_url = ""
    for attempt in range(total_attempts):
        try:
            if held_task_id or held_image_url:
                return fetch_submitted_image(
                    held_task_id,
                    image_url=held_image_url,
                    model=model,
                )
            return _generate_once(
                prompt=prompt,
                model=model,
                reference_images=reference_images,
                aspect_ratio=aspect_ratio,
                shot_index=shot_index,
            )
        except GrsaiRemoteTaskError as exc:
            held_task_id = exc.task_id or held_task_id
            held_image_url = exc.image_url or held_image_url
            last_err = exc
            if is_per_shot_poll_timeout(exc) or attempt + 1 >= total_attempts:
                raise
            logger.warning(
                "Grsai 已提交任务 shot_index=%s task=%s 第 %s/%s 次取回失败，不重新生图: %s",
                shot_index,
                held_task_id,
                attempt + 1,
                total_attempts,
                exc,
            )
            time.sleep(min(2 * (attempt + 1), 6))
            continue
        except GrsaiDownloadError as exc:
            last_download_err = exc
            if exc.image_url and attempt + 1 < total_attempts:
                logger.warning(
                    "Grsai 下载成片失败 shot_index=%s 第 %s/%s 次，沿用已完成任务重试下载: %s",
                    shot_index,
                    attempt + 1,
                    total_attempts,
                    exc,
                )
                time.sleep(2)
                try:
                    return _download_result_image(exc.image_url)
                except GrsaiDownloadError:
                    raise
            raise
        except GrsaiError as exc:
            last_err = exc
            if is_per_shot_poll_timeout(exc):
                raise
            retriable = isinstance(exc, GrsaiTransientError) or _is_transient_exc(exc)
            if attempt + 1 < total_attempts and retriable:
                logger.warning(
                    "Grsai 单张 shot_index=%s 第 %s/%s 次失败，将重试: %s",
                    shot_index,
                    attempt + 1,
                    total_attempts,
                    exc,
                )
                time.sleep(min(2 * (attempt + 1), 6))
                continue
            raise
        except Exception as exc:
            if attempt + 1 < total_attempts and _is_transient_exc(exc):
                logger.warning(
                    "Grsai 单张 shot_index=%s 第 %s/%s 次失败，将重试: %s",
                    shot_index,
                    attempt + 1,
                    total_attempts,
                    exc,
                )
                time.sleep(min(2 * (attempt + 1), 6))
                continue
            raise GrsaiError(str(exc)) from exc
    if last_download_err:
        raise last_download_err
    if last_err:
        raise last_err
    raise GrsaiError("Grsai 生成失败")


def is_grsai_configured() -> bool:
    return bool((settings.GRSAI_API_KEY or "").strip())
