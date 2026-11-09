"""TK 九图：固定 4 帧标记；创意 5 帧由 visual_batch_variance 按批次轮换。"""

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
    if plan.get("plan_template") != "tk_mx_ecommerce_9":
        return plan

    shots = plan.get("shots") or []
    for shot in shots:
        role = (shot.get("role") or "").strip()
        if role in FIXED_FRAME_ROLES:
            shot["frame_contract"] = "fixed"
            shot.setdefault(
                "diversity_lock",
                "Fixed TK frame — keep mandated marketing role; unique camera vs other 8 frames.",
            )
    plan["fixed_frame_roles"] = sorted(FIXED_FRAME_ROLES)
    plan["shots"] = shots

    from generation.services.visual_batch_variance import apply_visual_batch_variance

    return apply_visual_batch_variance(plan, job=job)


def resolve_detail_variant_offset(job) -> int:
    from generation.services.visual_batch_variance import resolve_visual_batch_index

    return resolve_visual_batch_index(job)
