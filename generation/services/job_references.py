"""套图任务参考图：多 SKU / 多色号附件解析与按镜头排序。"""

from __future__ import annotations

from django.conf import settings

from generation.services.grsai import attachment_to_image_payload


def normalize_attachment_id_list(raw) -> list[int]:
    if not raw:
        return []
    if isinstance(raw, int):
        return [raw]
    out: list[int] = []
    for item in raw:
        try:
            n = int(item)
        except (TypeError, ValueError):
            continue
        if n > 0 and n not in out:
            out.append(n)
    return out


def job_attachment_ids(job) -> list[int]:
    ids = normalize_attachment_id_list(getattr(job, "reference_attachment_ids", None))
    if ids:
        return ids
    plan_ids = normalize_attachment_id_list((job.plan_json or {}).get("reference_attachment_ids"))
    if plan_ids:
        return plan_ids
    if job.reference_attachment_id:
        return [int(job.reference_attachment_id)]
    return []


def job_attachments(job):
    from uploads.models import Attachment

    ids = job_attachment_ids(job)
    if not ids:
        return []
    cap = max(1, int(getattr(settings, "GEN_MAX_REFERENCE_IMAGES", 8)))
    ids = ids[:cap]
    by_id = {
        a.id: a
        for a in Attachment.objects.filter(id__in=ids, user_id=job.user_id)
    }
    return [by_id[i] for i in ids if i in by_id]


def order_attachments_for_shot(attachments, shot: dict) -> list:
    if not attachments:
        return []
    ordered = list(attachments)
    fi = shot.get("featured_variant_index")
    if fi is None:
        return ordered
    try:
        idx = int(fi)
    except (TypeError, ValueError):
        return ordered
    if 0 <= idx < len(ordered):
        return [ordered[idx]] + [a for j, a in enumerate(ordered) if j != idx]
    return ordered


def max_ref_images_per_grsai_request() -> int:
    return max(1, int(getattr(settings, "GRSAI_MAX_REF_IMAGES_PER_REQUEST", 2)))


def max_ref_images_showcase() -> int:
    cap = int(getattr(settings, "GRSAI_MAX_REF_IMAGES_SHOWCASE", 4))
    cap = min(cap, int(getattr(settings, "GEN_MAX_REFERENCE_IMAGES", 8)))
    return max(1, cap)


def reference_image_payloads_for_shot(job, shot: dict) -> list[str]:
    attachments = job_attachments(job)
    if shot.get("use_all_reference_images"):
        attachments = attachments[: max_ref_images_showcase()]
    else:
        attachments = order_attachments_for_shot(attachments, shot)
        attachments = attachments[: max_ref_images_per_grsai_request()]
    return [attachment_to_image_payload(a) for a in attachments]
