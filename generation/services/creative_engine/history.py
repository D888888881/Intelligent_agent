"""Creative History：同 SKU 成功 + 失败半条（弱化避让）。"""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from generation.services.listing_bundle import LISTING_PLAN_TEMPLATES
from generation.services.visual_batch_variance import product_fingerprint

ATTEMPT_HISTORY_HOURS = 48
ATTEMPT_HISTORY_LIMIT = 2
SUCCESS_HISTORY_LIMIT = 5


def _record_from_plan(
    plan: dict,
    *,
    job_id: int,
    record_type: str = "success",
) -> dict | None:
    if not plan or not (plan.get("shots")):
        return None
    if plan.get("plan_template") not in LISTING_PLAN_TEMPLATES:
        return None

    creative = plan.get("creative_set") or {}
    dimensions = creative.get("dimensions") or plan.get("creative_dimension_matrix") or {}
    concept_id = (
        creative.get("concept_id")
        or plan.get("creative_concept_id")
        or ""
    )
    if not concept_id:
        return None

    return {
        "job_id": job_id,
        "record_type": record_type,
        "concept_id": concept_id,
        "concept_label_zh": creative.get("label_zh") or plan.get("creative_concept_label_zh") or "",
        "dimensions": dimensions,
        "pack_name": plan.get("visual_batch_pack_name") or creative.get("pack_name") or "",
        "color_palette": dimensions.get("color_palette") or (plan.get("listing_color_mood_en") or "")[:80],
        "scene_environment": dimensions.get("scene_environment") or "",
        "visual_style": dimensions.get("visual_style") or "",
        "composition": dimensions.get("composition") or "",
        "lighting": dimensions.get("lighting") or "",
    }


def load_creative_history(
    job,
    *,
    product_analysis: dict | None = None,
    success_limit: int = SUCCESS_HISTORY_LIMIT,
    attempt_limit: int = ATTEMPT_HISTORY_LIMIT,
    attempt_hours: int = ATTEMPT_HISTORY_HOURS,
) -> list[dict]:
    from generation.models import GenerationJob

    fp = product_fingerprint(job, product_analysis=product_analysis)
    history: list[dict] = []

    qs_ok = (
        GenerationJob.objects.filter(
            user_id=job.user_id,
            status=GenerationJob.Status.SUCCEEDED,
        )
        .exclude(pk=job.pk)
        .order_by("-finished_at")[:40]
    )
    for j in qs_ok:
        if product_fingerprint(j, product_analysis=product_analysis) != fp:
            continue
        rec = _record_from_plan(j.plan_json or {}, job_id=j.id, record_type="success")
        if rec:
            history.append(rec)
        if sum(1 for x in history if x.get("record_type") == "success") >= success_limit:
            break

    cutoff = timezone.now() - timedelta(hours=max(1, attempt_hours))
    seen_attempt_concepts: set[str] = set()
    qs_attempt = (
        GenerationJob.objects.filter(
            user_id=job.user_id,
            status__in=(GenerationJob.Status.FAILED, GenerationJob.Status.CANCELLED),
            created_at__gte=cutoff,
        )
        .exclude(pk=job.pk)
        .order_by("-created_at")[:25]
    )
    attempt_count = 0
    for j in qs_attempt:
        if product_fingerprint(j, product_analysis=product_analysis) != fp:
            continue
        plan = j.plan_json or {}
        cid = (plan.get("creative_concept_id") or (plan.get("creative_set") or {}).get("concept_id") or "")
        if not cid or cid in seen_attempt_concepts:
            continue
        rec = _record_from_plan(plan, job_id=j.id, record_type="attempt")
        if rec:
            history.append(rec)
            seen_attempt_concepts.add(cid)
            attempt_count += 1
        if attempt_count >= attempt_limit:
            break

    return history


def build_creative_history_avoid_en(history: list[dict]) -> str:
    success = [h for h in history if h.get("record_type") == "success"]
    attempts = [h for h in history if h.get("record_type") == "attempt"]
    if not success and not attempts:
        return ""

    parts: list[str] = []
    if success:
        parts.append(
            "CREATIVE HISTORY — Prior SUCCESSFUL listing sets (do NOT repeat these whole directions):"
        )
        for h in success:
            dims = h.get("dimensions") or {}
            parts.append(
                f"Job #{h.get('job_id')} concept={h.get('concept_id')}; "
                f"style={dims.get('visual_style') or h.get('visual_style')}; "
                f"scene={dims.get('scene_environment') or h.get('scene_environment')}; "
                f"palette={dims.get('color_palette') or h.get('color_palette')}; "
                f"pack={h.get('pack_name')}."
            )

    if attempts:
        parts.append(
            "RECENT ATTEMPTS (failed/cancelled, same SKU within 48h) — prefer a different concept_id if possible:"
        )
        for h in attempts:
            parts.append(
                f"Job #{h.get('job_id')} attempted concept={h.get('concept_id')} "
                f"(not a full ban — failure may be model/API, not creative)."
            )

    parts.append(
        "MANDATORY: require a NEW creative concept across visual style, scene family, lighting, "
        "camera language, and composition — NOT the same centered product with only background hue change. "
        "Within any single new set, keep color span and scene-style span controlled (one campaign feel)."
    )
    return " ".join(parts)
