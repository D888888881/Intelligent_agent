import io

from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, ImageDraw

from generation.services.grsai import GrsaiError, attachment_to_image_payload, generate_image_bytes, is_grsai_configured
from generation.services.model_strategy import reference_prefix_for_model


def generate_image_file(
    prompt: str,
    index: int,
    job_id: int,
    *,
    reference_attachment=None,
    reference_payloads: list[str] | None = None,
    reference_images: list[str] | None = None,
    aspect_ratio: str = "1:1",
    image_model: str | None = None,
    reference_purpose: str = "generation",
) -> ContentFile:
    if is_grsai_configured():
        if reference_images is not None:
            refs = list(reference_images)
        else:
            refs = []
            if reference_attachment:
                refs.append(attachment_to_image_payload(reference_attachment))
            if reference_payloads:
                refs.extend(reference_payloads)
        model = image_model or settings.GRSAI_IMAGE_MODEL
        full_prompt = prompt
        if refs:
            prefix = reference_prefix_for_model(
                model,
                has_reference=True,
                purpose=reference_purpose,
            )
            full_prompt = prefix + prompt
            if len(refs) > 1:
                full_prompt = (
                    f"Multiple product reference images ({len(refs)}) are attached — different SKUs, "
                    "colorways, or angles of the same listing. Follow this frame's variant instructions. "
                    + full_prompt
                )
        try:
            content = generate_image_bytes(
                prompt=full_prompt,
                model=model,
                reference_images=refs,
                aspect_ratio=aspect_ratio,
                shot_index=index,
            )
            return ContentFile(content, name=f"job{job_id}_{index}.png")
        except GrsaiError:
            raise
        except Exception as exc:
            raise GrsaiError(str(exc)) from exc

    if settings.OPENAI_API_KEY and settings.OPENAI_IMAGE_BACKEND == "openai":
        content = _generate_openai_legacy(prompt)
        if content:
            return ContentFile(content, name=f"job{job_id}_{index}.png")

    return _generate_placeholder(prompt, index, job_id)


def _generate_openai_legacy(prompt: str) -> bytes | None:
    from chat.services.openai_client import get_openai_client

    client = get_openai_client()
    try:
        if settings.OPENAI_IMAGE_MODEL.startswith("dall-e"):
            resp = client.images.generate(
                model=settings.OPENAI_IMAGE_MODEL,
                prompt=prompt[:4000],
                size="1024x1024",
                n=1,
            )
            url = resp.data[0].url
            if not url:
                b64 = getattr(resp.data[0], "b64_json", None)
                if b64:
                    import base64

                    return base64.b64decode(b64)
                return None
            import httpx

            r = httpx.get(url, timeout=120)
            r.raise_for_status()
            return r.content
    except Exception:
        return None
    return None


def _generate_placeholder(prompt: str, index: int, job_id: int) -> ContentFile:
    img = Image.new("RGB", (1024, 1024), color=(240, 242, 248))
    draw = ImageDraw.Draw(img)
    text = f"Demo #{index}\nJob {job_id}\n\n{prompt[:120]}..."
    draw.rectangle([40, 40, 984, 984], outline=(80, 120, 200), width=4)
    draw.multiline_text((60, 60), text, fill=(30, 30, 40), spacing=8)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return ContentFile(buf.getvalue(), name=f"job{job_id}_{index}.png")
