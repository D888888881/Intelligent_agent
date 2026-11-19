"""TK 九图：固定 2 帧标记；图 4/5 灵活职能；创意 5 帧由 visual_batch_variance 轮换。"""

from __future__ import annotations

from generation.services.shot_diversity_constants import (
    CREATIVE_DETAIL_INDICES,
    CREATIVE_DETAIL_SPECS,
    DETAIL_SHOT_NEGATIVE,
    FIXED_FRAME_ROLES,
)

# 兼容旧引用
_DETAIL_NEGATIVE = DETAIL_SHOT_NEGATIVE


def apply_detail_shot_diversity(plan: dict, *, job=None) -> dict:
    from generation.services.listing_bundle import is_listing_ecommerce_plan

    if not is_listing_ecommerce_plan(plan):
        return plan

    if (plan.get("plan_template") or "") == "amazon_listing_7":
        from generation.services.amazon_listing_flex import apply_amazon_listing_flex

        return apply_amazon_listing_flex(plan, job=job)

    shots = plan.get("shots") or []
    for shot in shots:
        role = (shot.get("role") or "").strip()
        try:
            idx = int(shot.get("index") or 0)
        except (TypeError, ValueError):
            idx = 0
        if role in FIXED_FRAME_ROLES:
            shot["frame_contract"] = "fixed"
            shot.setdefault(
                "diversity_lock",
                "Fixed TK frame — keep mandated marketing role; unique camera vs other 8 frames.",
            )
        elif idx in (4, 5):
            shot.setdefault(
                "diversity_lock",
                (
                    shot.get("diversity_lock")
                    or f"Frame {idx} — unique product facing vs all other listing frames; not reference clone."
                ),
            )
    plan["fixed_frame_roles"] = sorted(FIXED_FRAME_ROLES)
    plan["shots"] = shots

    from generation.services.visual_batch_variance import apply_visual_batch_variance
    from generation.services.frame3_flex import apply_frame3_flex_variant
    from generation.services.frame4_flex import apply_frame4_flex_variant
    from generation.services.frame5_flex import apply_frame5_flex_variant

    plan = apply_visual_batch_variance(plan, job=job)
    plan = apply_frame3_flex_variant(plan, job=job)
    plan = apply_frame4_flex_variant(plan, job=job)
    plan = apply_frame5_flex_variant(plan, job=job)
    from generation.services.frame9_conversion import apply_frame9_conversion_variant

    return apply_frame9_conversion_variant(plan, job=job)


def resolve_detail_variant_offset(job) -> int:
    from generation.services.visual_batch_variance import resolve_visual_batch_index

    return resolve_visual_batch_index(job)
