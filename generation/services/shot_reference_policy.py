"""P0：分镜分级参考 — 主图/白底锁 SKU，创意镜少附参考以降低抄拍摄角。"""

from __future__ import annotations

from django.conf import settings

CATALOG_ROLES = frozenset({"white_bg_catalog"})
HERO_ROLES = frozenset({"hero_hook", "hero", "main_hero"})


def tiered_shot_references_enabled(plan: dict) -> bool:
    if not getattr(settings, "GEN_SHOT_REF_TIERED", True):
        return False
    if plan.get("plan_template") == "reference_guided":
        return False
    if plan.get("generation_mode") == "reference_guided":
        return False
    return True


def resolve_shot_reference_mode(
    shot: dict,
    plan: dict,
    *,
    family: str,
    has_reference: bool,
) -> str:
    if not has_reference:
        return "none"
    if not tiered_shot_references_enabled(plan):
        return (
            (shot.get("reference_mode") or plan.get("default_reference_mode") or "identity")
            .strip()
            .lower()
        )

    role = (shot.get("role") or "").strip()
    try:
        idx = int(shot.get("index") or 0)
    except (TypeError, ValueError):
        idx = 0

    if role in CATALOG_ROLES or idx == 2:
        return "identity"
    if idx == 1:
        return "identity"
    if family == "gpt_image" and idx <= 2 and role in frozenset({"white_bg_catalog"}):
        return "identity"

    # 纯成分镜可无图；其余创意镜仍附参考锁 SKU（机位由 mandate 约束，不抄参考角度）
    if shot.get("ingredient_composition_only"):
        return "none"
    if (shot.get("frame3_variant") or "") == "ingredient_composition" and role == "pain_empathy":
        return "none"
    if (shot.get("frame5_variant") or "") == "ingredient_composition" and role == "usp_secondary":
        return "none"
    return "identity"


def apply_tiered_shot_reference_policy(
    plan: dict,
    *,
    family: str,
    has_reference: bool,
) -> dict:
    if not tiered_shot_references_enabled(plan):
        return plan

    shots = plan.get("shots") or []
    identity_count = 0
    creative_no_ref = 0
    for shot in shots:
        mode = resolve_shot_reference_mode(shot, plan, family=family, has_reference=has_reference)
        shot["reference_mode"] = mode
        if mode == "identity":
            identity_count += 1
        elif mode == "none":
            creative_no_ref += 1

    if family == "banana":
        plan["reference_policy"] = "banana_tiered"
    elif family == "gpt_image":
        plan["reference_policy"] = "gpt_tiered"

    plan["shot_reference_tier_en"] = (
        f"Reference attach: {identity_count} frames with identity SKU ref "
        f"(rotate camera per mandate — never clone reference angle); "
        f"{creative_no_ref} ingredient-only frames without product ref."
    )
    plan["shots"] = shots
    return plan