"""单槽位套图修复：商品原图 + 当前成图双参考，生成候选后再由用户确认替换。"""

from __future__ import annotations

import re

from django.core.files.base import ContentFile

from generation.models import GeneratedImage, GenerationJob, SlotRefineCandidate
from generation.services.grsai import GrsaiError, attachment_to_image_payload, storage_file_to_image_payload
from generation.services.image_gen import generate_image_file
from generation.services.model_strategy import model_family
from generation.services.prompt_builder import is_reference_refusal_error, is_violation_error

SLOT_REFINE_AVOID = (
    "collage, grid layout, split screen, multiple panels, watermark, wrong SKU, "
    "redesigned packaging, altered label, wrong bottle color, duplicate reference packshot, "
    "full scene replacement, unrelated new background, new camera angle, relayout of headline or CTA, "
    "English or Chinese text unless already in frame, blurry text, low resolution, "
    "unchanged copy of reference image 2, identical output when edit requests resize, "
    "unchanged wrong product or prop in scene, generic substitute instead of reference SKU"
)

_SCALE_KEYWORDS = (
    "缩小",
    "变小",
    "小一点",
    "小一些",
    "小一下",
    "缩小一点",
    "缩小一些",
    "修小",
    "略小",
    "稍微",
    "适当",
    "smaller",
    "shrink",
    "reduce size",
    "scale down",
    "enlarge",
    "放大",
    "变大",
    "larger",
    "scale up",
)

_SCALE_STRONG = ("大幅", "大幅度", "大缩", "明显", "很多", " greatly", "much smaller", "significantly")
_SCALE_SUBTLE = ("一点", "一下", "稍微", "适当", "略", "slightly", "a bit", "a little")

_CONSISTENCY_ISSUE = (
    "不一致",
    "不符",
    "不符合",
    "不对",
    "不像",
    "错了",
    "有误",
    "不匹配",
    "不一样",
    "和原产品",
    "和商品",
    "和参考",
    "产品图",
    "原产品",
    "实物",
    "mismatch",
    "inconsistent",
    "wrong product",
    "doesn't match",
    "does not match",
    "not the same",
)
_CONSISTENCY_ACTION = (
    "修复",
    "纠正",
    "改正",
    "换成",
    "改成",
    "替换",
    "对齐",
    "fix",
    "correct",
    "replace",
    "match",
)


def _shot_for_index(plan: dict, index: int) -> dict | None:
    for shot in plan.get("shots") or []:
        if int(shot.get("index") or 0) == index:
            return shot
    return None


def _identity_snippet(plan: dict, *, max_len: int = 800) -> str:
    identity = (
        plan.get("identity_lock") or plan.get("product_identity") or plan.get("subject_lock") or ""
    ).strip()
    if not identity:
        return ""
    cap = max(200, max_len)
    return f"SKU identity (when product is visible): {identity[:cap]}"


def _is_scale_edit_request(user_prompt: str) -> bool:
    u = user_prompt or ""
    if not u.strip():
        return False
    lower = u.lower()
    if any(k in u or k in lower for k in _SCALE_KEYWORDS):
        return True
    return bool(re.search(r"缩.{0,4}小|变.{0,2}小|小.{0,2}一[点儿下]", u))


def _scale_magnitude_phrase(user_prompt: str) -> str:
    u = user_prompt or ""
    lower = u.lower()
    if any(s in u for s in _SCALE_STRONG[:5]) or "much smaller" in lower or "significantly" in lower:
        return "about 35–50% of the current apparent size"
    if any(s in u for s in _SCALE_SUBTLE) or "slightly" in lower or "a bit" in lower:
        return "about 75–82% of the current apparent size (clearly smaller but not tiny)"
    return "about 70–80% of the current apparent size"


def _ref_frame_sku_labels(ref_layout: str) -> tuple[str, str]:
    layout = (ref_layout or "sku_first").lower()
    if layout == "canvas_first":
        return "reference image 1 (listing frame)", "reference image 2 (SKU packshot)"
    if layout == "canvas_only":
        return "the attached listing frame", "the SKU description in this prompt"
    return "reference image 2 (listing frame)", "reference image 1 (SKU packshot)"


def _scale_edit_directive(user_prompt: str, *, ref_layout: str = "sku_first") -> str:
    if not _is_scale_edit_request(user_prompt):
        return ""
    frame, _sku = _ref_frame_sku_labels(ref_layout)
    mag = _scale_magnitude_phrase(user_prompt)
    return (
        "REQUIRED VISIBLE CHANGE — the edit request is a size/scale adjustment. "
        f"Resize the object named in the primary edit to {mag} in {frame}. "
        "The difference must be obvious when comparing side-by-side at listing thumbnail size. "
        "Keep the object in the same screen region; update shadows and floor contact naturally. "
        f"Do NOT return a nearly pixel-identical copy of {frame}."
    )


def _is_product_consistency_edit(user_prompt: str) -> bool:
    u = user_prompt or ""
    if not u.strip():
        return False
    lower = u.lower()
    has_issue = any(k in u or k in lower for k in _CONSISTENCY_ISSUE)
    has_action = any(k in u or k in lower for k in _CONSISTENCY_ACTION)
    if has_issue and has_action:
        return True
    if has_issue:
        return True
    return bool(
        re.search(
            r"(产品|商品|包装|sku|夹子|工具|手持|拿着|瓶子|牙膏|抓取).{0,16}(不一致|不对|不符|不像|错了)",
            u,
            re.IGNORECASE,
        )
    )


def _edit_focus_clause(user_prompt: str, *, sku_label: str) -> str:
    u = user_prompt or ""
    for pat in (
        r"(?:图中|图片中|画面里)?(?:女人|女性|模特)?(?:手中|手里|手持)(?:的)?(.+?)(?:和|与|跟)",
        r"手持的(.+?)(和|与|跟)",
        r"拿着(.+?)(和|与|跟)",
    ):
        m = re.search(pat, u)
        if m:
            obj = m.group(1).strip("的 ")
            if obj:
                return f"Focus correction on this in-scene item: {obj} (must match {sku_label})."
    return ""


def _product_consistency_directive(user_prompt: str, *, ref_layout: str = "sku_first") -> str:
    if not _is_product_consistency_edit(user_prompt):
        return ""
    frame, sku = _ref_frame_sku_labels(ref_layout)
    focus = _edit_focus_clause(user_prompt, sku_label=sku)
    parts = [
        f"REQUIRED PRODUCT CORRECTION — {frame} shows the wrong product, prop, or SKU variant. "
        "Repaint or replace ONLY the incorrect in-scene product/handheld item described in the primary edit "
        f"so it matches {sku} (exact model, shape, materials, logo, label, and colors). "
        f"Keep the person, pose, hand grip, camera angle, background, lighting, on-image text, and overall layout from {frame}. "
        f"The before/after comparison must clearly show the product fix — do NOT return an unchanged duplicate of {frame}.",
    ]
    if focus:
        parts.append(focus)
    return " ".join(parts)


def build_slot_refine_prompt(
    *,
    user_prompt: str,
    job: GenerationJob,
    slot_index: int,
    image_model: str | None = None,
    mode: str = "standard",
    ref_layout: str = "sku_first",
) -> str:
    user = (user_prompt or "").strip()
    plan = job.plan_json or {}
    shot = _shot_for_index(plan, slot_index) or {}
    role = (shot.get("marketing_pillar") or shot.get("role") or "").strip()
    locale = plan.get("locale") or ""
    family = model_family(image_model)
    scale_edit = _is_scale_edit_request(user)
    consistency_edit = _is_product_consistency_edit(user) and not scale_edit

    head = f"Retouch e-commerce listing frame #{slot_index}"
    if role:
        head += f" ({role})"
    head += "."

    parts: list[str] = []

    if mode == "forced_attach":
        parts.append(
            "Two reference images are already attached in the images array "
            "(image 1 = SKU, image 2 = frame to edit). Generate the edited photograph now; "
            "never reply with text asking for uploads or reference photos."
        )
    elif mode == "moderation_safe":
        parts.append(
            "Professional TikTok Shop e-commerce listing photo, square format, safe commercial content, "
            "no people, no hands, no faces, no nudity."
        )
    elif family == "gpt_image":
        parts.append(
            "The images array already contains both references. Output the retouched listing image directly."
        )

    parts.append(head)
    parts.append(f"Primary edit (must be visible in output; Chinese or English): {user}")

    consistency_directive = _product_consistency_directive(user, ref_layout=ref_layout)
    scale_directive = (
        _scale_edit_directive(user, ref_layout=ref_layout) if not consistency_edit else ""
    )
    if consistency_directive:
        parts.append(consistency_directive)
        parts.append(
            "Reference image 1 is the ground-truth SKU for the corrected product in the scene — "
            "use its industrial design and colors, not a generic look-alike."
        )
        parts.append(
            "Keep everything else in the frame identical to reference image 2 except the corrected product geometry and appearance."
        )
    elif scale_directive:
        parts.append(scale_directive)
        parts.append(
            "Keep background, on-image marketing text, props other than the resized product, camera angle, "
            "and overall layout the same as reference image 2."
        )
    else:
        parts.append(
            "Use reference image 2 as the base photograph. Change ONLY what the edit request specifies; "
            "keep scene, camera angle, lighting direction, props, and overall layout as image 2 unless the edit asks otherwise."
        )

    if family == "banana":
        if consistency_edit:
            parts.append(
                "For product correction: embed the SKU from image 1 into the lifestyle frame of image 2 — "
                "do not replace the whole scene with image 1's packshot."
            )
        else:
            parts.append(
                "Reference image 1 is for packaging graphics, label text, logo, and colors only — "
                "do not paste image 1's packshot layout or camera pose into the frame."
            )
    elif consistency_edit:
        parts.append(
            "Reference image 1 defines the exact product to render in the model's hands or in-scene placement."
        )
    else:
        parts.append(
            "Reference image 1 locks product packaging, logo, label, and colors when the product appears in the frame."
        )

    if consistency_edit:
        identity_max = 900
    elif scale_edit:
        identity_max = 320
    else:
        identity_max = 800
    identity = _identity_snippet(plan, max_len=identity_max)
    if identity and mode != "moderation_safe":
        parts.append(identity)

    parts.append(
        "Output: one photorealistic full-frame photo. No collage. No instructional text in the image."
    )
    if locale and mode != "moderation_safe":
        parts.append(f"If the frame contains marketing copy, keep language consistent with locale {locale}.")
    parts.append(f"Avoid: {SLOT_REFINE_AVOID}")
    return " ".join(parts)


def _image_model_for_job(job: GenerationJob) -> str:
    plan = job.plan_json or {}
    from django.conf import settings

    return plan.get("image_model") or settings.GRSAI_IMAGE_MODEL


def _image_model_for_candidate(candidate: SlotRefineCandidate) -> str:
    from Intelligent_agent.model_catalog import resolve_image_model

    if (candidate.image_model or "").strip():
        return resolve_image_model(candidate.image_model)
    return _image_model_for_job(candidate.job)


def _aspect_for_job(job: GenerationJob) -> str:
    return (job.plan_json or {}).get("aspect_ratio") or "1:1"


def _slot_refine_reference_images(job: GenerationJob, gen_img: GeneratedImage) -> list[str]:
    from generation.services.job_references import job_attachments

    attachments = job_attachments(job)
    if not attachments and job.reference_attachment:
        attachments = [job.reference_attachment]
    if not attachments:
        raise GrsaiError("任务缺少商品原图参考，无法修复")
    from generation.services.job_references import max_ref_images_per_grsai_request

    cap = max(1, max_ref_images_per_grsai_request() - 1)
    product_payloads = [attachment_to_image_payload(a) for a in attachments[:cap]]
    slot_payload = storage_file_to_image_payload(gen_img.file)
    return product_payloads + [slot_payload]


def _generate_slot_refine_file(
    *,
    job: GenerationJob,
    slot_index: int,
    user_prompt: str,
    image_model: str,
    aspect: str,
    gen_img: GeneratedImage,
) -> ContentFile:
    refs = _slot_refine_reference_images(job, gen_img)
    prompt_body = build_slot_refine_prompt(
        user_prompt=user_prompt,
        job=job,
        slot_index=slot_index,
        image_model=image_model,
        mode="standard",
    )

    def _call(body: str) -> ContentFile:
        return generate_image_file(
            body,
            slot_index,
            job.id,
            reference_images=refs,
            aspect_ratio=aspect,
            image_model=image_model,
            reference_purpose="slot_refine",
        )

    try:
        return _call(prompt_body)
    except Exception as exc:
        if is_reference_refusal_error(exc):
            forced = build_slot_refine_prompt(
                user_prompt=user_prompt,
                job=job,
                slot_index=slot_index,
                image_model=image_model,
                mode="forced_attach",
            )
            return _call(forced)
        if is_violation_error(exc):
            safe = build_slot_refine_prompt(
                user_prompt=user_prompt,
                job=job,
                slot_index=slot_index,
                image_model=image_model,
                mode="moderation_safe",
            )
            return _call(safe)
        if isinstance(exc, GrsaiError):
            raise
        raise GrsaiError(str(exc)) from exc


def run_slot_refine_candidate(candidate_id: int) -> None:
    candidate = (
        SlotRefineCandidate.objects.select_related(
            "job",
            "job__reference_attachment",
            "user",
        )
        .filter(pk=candidate_id)
        .first()
    )
    if not candidate or candidate.status in (
        SlotRefineCandidate.Status.APPLIED,
        SlotRefineCandidate.Status.DISCARDED,
    ):
        return

    job = candidate.job
    slot_index = candidate.slot_index
    gen_img = GeneratedImage.objects.filter(job=job, index=slot_index).first()
    if not gen_img or not gen_img.file:
        candidate.status = SlotRefineCandidate.Status.FAILED
        candidate.error_message = "该槽位尚无可用成图"
        candidate.save(update_fields=["status", "error_message"])
        return

    if not job.reference_attachment:
        candidate.status = SlotRefineCandidate.Status.FAILED
        candidate.error_message = "任务缺少商品原图参考，无法修复"
        candidate.save(update_fields=["status", "error_message"])
        return

    candidate.status = SlotRefineCandidate.Status.RUNNING
    candidate.error_message = ""
    candidate.save(update_fields=["status", "error_message"])

    try:
        image_model = _image_model_for_candidate(candidate)
        aspect = _aspect_for_job(job)
        content_file = _generate_slot_refine_file(
            job=job,
            slot_index=slot_index,
            user_prompt=candidate.prompt,
            image_model=image_model,
            aspect=aspect,
            gen_img=gen_img,
        )
        candidate.file.save(
            f"job{job.id}_slot{slot_index}_c{candidate.id}.png",
            content_file,
            save=False,
        )
        candidate.status = SlotRefineCandidate.Status.SUCCEEDED
        candidate.save(update_fields=["status", "file"])
    except GrsaiError as exc:
        candidate.status = SlotRefineCandidate.Status.FAILED
        candidate.error_message = str(exc)
        candidate.save(update_fields=["status", "error_message"])
    except Exception as exc:
        candidate.status = SlotRefineCandidate.Status.FAILED
        candidate.error_message = str(exc)[:2000]
        candidate.save(update_fields=["status", "error_message"])


def apply_slot_refine_candidate(candidate: SlotRefineCandidate) -> GeneratedImage:
    if candidate.status != SlotRefineCandidate.Status.SUCCEEDED or not candidate.file:
        raise ValueError("候选图尚未生成成功")
    gen_img = GeneratedImage.objects.get(job=candidate.job, index=candidate.slot_index)
    with candidate.file.open("rb") as f:
        data = f.read()
    gen_img.file.save(
        f"slot{candidate.slot_index}_applied_{candidate.id}.png",
        ContentFile(data),
        save=False,
    )
    gen_img.status = GeneratedImage.Status.SUCCEEDED
    gen_img.error_message = ""
    image_model = _image_model_for_candidate(candidate)
    gen_img.prompt = build_slot_refine_prompt(
        user_prompt=candidate.prompt,
        job=candidate.job,
        slot_index=candidate.slot_index,
        image_model=image_model,
    )
    gen_img.save()
    candidate.status = SlotRefineCandidate.Status.APPLIED
    candidate.save(update_fields=["status"])
    return gen_img
