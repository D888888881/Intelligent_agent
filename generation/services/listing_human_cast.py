"""套图人物出镜：职能镜强制人物；防止人物预算策略误删模特。"""

from __future__ import annotations

from generation.services.listing_bundle import is_listing_ecommerce_plan
from generation.services.product_usage_semantics import zone_requires_model

# role → (human_cast_mode, mandate_en)
MANDATED_HUMAN_BY_ROLE: dict[str, tuple[str, str]] = {
    "usp_primary": (
        "face",
        "MANDATORY HUMAN — TK Frame 4: photorealistic model showing before→after transformation "
        "while using the hero SKU on the correct body zone; face or half-body visible; "
        "NOT product-only still life; no antes/después text on image.",
    ),
    "ease_objection": (
        "full",
        "MANDATORY HUMAN — This frame MUST show a real target consumer (face visible, half-body or 3/4) "
        "actively using the hero SKU in a believable Mexico daily-life moment; TikTok UGC social proof; "
        "product clearly in use; NOT product-only still life; NOT hands-only macro.",
    ),
}

# 可选强化：收尾镜可露脸（系统不强制，避免预算冲突）
ENCOURAGED_HUMAN_BY_ROLE: dict[str, tuple[str, str]] = {
    "lifestyle_payoff": (
        "face",
        "HUMAN ENCOURAGED — Conversion close may show relatable person with product in daily payoff scene; "
        "face or candid 3/4 optional but preferred for purchase atmosphere.",
    ),
}


def _is_mandatory(shot: dict) -> bool:
    return bool((shot.get("human_cast_mandatory_en") or "").strip()) or shot.get(
        "human_cast_mandatory"
    )


def apply_mandated_human_casts(plan: dict) -> dict:
    if not is_listing_ecommerce_plan(plan):
        return plan

    tpl = (plan.get("plan_template") or "").strip()
    mandated_indices: set[int] = set()
    if tpl == "amazon_listing_7":
        mandated_indices.add(6)
    else:
        mandated_indices.add(7)

    for shot in plan.get("shots") or []:
        role = (shot.get("role") or "").strip()
        try:
            idx = int(shot.get("index") or 0)
        except (TypeError, ValueError):
            idx = 0

        if idx == 4 and tpl == "tk_mx_ecommerce_9":
            zone = (plan.get("product_analysis") or {}).get("application_zone") or ""
            if zone_requires_model(zone):
                mode, lock = MANDATED_HUMAN_BY_ROLE["usp_primary"]
                if zone == "body_bath":
                    mode = "full"
                shot["human_cast_mode"] = shot.get("human_cast_mode") or mode
                shot["human_cast_mandatory"] = True
                if not (shot.get("human_cast_mandatory_en") or "").strip():
                    shot["human_cast_mandatory_en"] = lock
            else:
                shot["human_cast_mandatory"] = False
                shot["human_cast_mode"] = "none"
                shot.pop("human_cast_mandatory_en", None)
        elif role in MANDATED_HUMAN_BY_ROLE or idx in mandated_indices:
            mode, lock = MANDATED_HUMAN_BY_ROLE.get(
                role,
                (
                    "full",
                    MANDATED_HUMAN_BY_ROLE["ease_objection"][1],
                ),
            )
            shot["human_cast_mode"] = mode
            shot["human_cast_mandatory"] = True
            shot["human_cast_mandatory_en"] = lock
            shot.pop("_force_hands_only", None)
            if "NO HUMAN" in (shot.get("action_lock") or ""):
                shot["action_lock"] = (
                    shot.get("action_lock") or ""
                ).replace("NO HUMAN — Product, material, environment, or infographic story only;", "").strip()
        elif role in ENCOURAGED_HUMAN_BY_ROLE and (shot.get("human_cast_mode") or "none") == "none":
            mode, hint = ENCOURAGED_HUMAN_BY_ROLE[role]
            shot["human_cast_mode"] = mode
            shot.setdefault("human_cast_encourage_en", hint)

    plan["listing_human_mandate_en"] = (
        "LISTING HUMAN RULES — TK Index 4: model required ONLY when product application zone is "
        "hair/body/oral/skin (see application_zone); home cleaners show toilet/surface before→after with NO model. "
        "Index 7 (TK) / 6 (Amazon) MUST show a visible human actively using the SKU — NON-NEGOTIABLE. "
        "White catalog (2) stays product-only upright packshot. "
        "Do NOT omit models on frame 7 when mandated; do NOT add models on frame 4 for toilet/cleaning SKUs."
    )
    return plan