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


def attachments_for_shot_indices(job, shot: dict) -> list:
    """参考图导演：按 shot.reference_attachment_indices 取上传顺序中的图。"""
    attachments = job_attachments(job)
    if not attachments:
        return []
    indices = shot.get("reference_attachment_indices")
    if indices is None:
        return []
    selected = []
    for raw in indices:
        try:
            i = int(raw)
        except (TypeError, ValueError):
            continue
        if 0 <= i < len(attachments):
            selected.append(attachments[i])
    cap = max_ref_images_per_grsai_request()
    if plan_allows_extra_ref_slots(job):
        cap = max(cap, min(4, int(getattr(settings, "GRSAI_MAX_REF_IMAGES_SHOWCASE", 4))))
    return selected[:cap]


def plan_allows_extra_ref_slots(job) -> bool:
    plan = job.plan_json or {}
    return plan.get("plan_template") == "reference_guided"


_MIMIC_MODES = frozenset(
    {"style_mimic", "layout_mimic", "model_mimic", "scene_mimic", "full_mimic"}
)


def _reorder_payloads_canvas_first(shot: dict, payloads: list[str]) -> list[str]:
    """版式模仿：中转 images[0] 放布局底图，SKU 随后（与 slot 精修底图逻辑一致）。"""
    if len(payloads) < 2:
        return payloads
    modes = [str(m).lower() for m in (shot.get("reference_modes") or [])]
    if not any(m in _MIMIC_MODES for m in modes):
        return payloads
    layout_i = None
    for i, mode in enumerate(modes):
        if mode in _MIMIC_MODES and mode != "identity":
            layout_i = i
            break
    if layout_i is None:
        layout_i = 1 if len(payloads) > 1 else 0
    if layout_i >= len(payloads):
        return payloads
    ordered = [payloads[layout_i]]
    for i, p in enumerate(payloads):
        if i != layout_i:
            ordered.append(p)
    return ordered


def shot_requests_all_references(shot: dict, attachment_count: int) -> bool:
    if shot.get("use_all_reference_images"):
        return True
    if attachment_count <= 1:
        return False
    role = (shot.get("role") or "").strip()
    try:
        idx = int(shot.get("index") or 0)
    except (TypeError, ValueError):
        idx = 0
    return role in ("white_bg_catalog", "multi_variant_showcase") or idx == 2


def reference_image_payloads_for_shot(job, shot: dict) -> list[str]:
    attachments = job_attachments(job)
    plan = job.plan_json or {}
    if plan.get("plan_template") == "reference_guided":
        picked = attachments_for_shot_indices(job, shot)
        if picked:
            payloads = [attachment_to_image_payload(a) for a in picked]
            return _reorder_payloads_canvas_first(shot, payloads)
    n_att = len(attachments)
    if shot_requests_all_references(shot, n_att):
        attachments = attachments[: max_ref_images_showcase()]
    elif plan.get("multi_variant_listing") and shot.get("featured_variant_index") is not None:
        attachments = order_attachments_for_shot(attachments, shot)[:1]
    else:
        attachments = order_attachments_for_shot(attachments, shot)
        attachments = attachments[: max_ref_images_per_grsai_request()]
    return [attachment_to_image_payload(a) for a in attachments]
