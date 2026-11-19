"""Listing 成分图：整帧展示原料/质地细节，不放产品瓶与包装。"""

from __future__ import annotations

from generation.services.listing_bundle import is_listing_ecommerce_plan


def _text_list(val) -> list[str]:
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    if isinstance(val, str) and val.strip():
        return [val.strip()]
    return []


def listing_has_ingredient_story(plan: dict) -> bool:
    from generation.services.beauty_personal_care import plan_uses_beauty_action_pool

    if not plan_uses_beauty_action_pool(plan):
        return False
    analysis = plan.get("product_analysis") or {}
    return bool(_text_list(analysis.get("key_ingredients")) or _text_list(analysis.get("ingredients")))


INGREDIENT_NO_PRODUCT_NEGATIVE = (
    "product bottle, pump bottle, tube packaging, cap, SKU packshot, brand label, "
    "hero product unit, hand holding product, barcode, price tag"
)


def build_ingredient_frame_lock_en(plan: dict) -> str:
    analysis = plan.get("product_analysis") or {}
    ings = _text_list(analysis.get("key_ingredients")) or _text_list(analysis.get("ingredients"))
    ing_txt = ", ".join(ings[:6]) if ings else "hero actives implied by category (botanicals, vitamins, minerals)"
    on_img = (plan.get("on_image_language") or "Spanish (Mexico)").strip()
    return (
        "INGREDIENT COMPOSITION FRAME — CRITICAL: The full 1:1 canvas is ONLY a premium ingredient still-life "
        f"({ing_txt}) edge-to-edge — textures, slices, droplets, powders, leaves, honey, oils as appropriate. "
        "NO sellable product, NO bottle, NO box, NO pump/cap from the SKU, NO brand packaging, NO mini product prop. "
        "Shoppers already see the SKU on other listing frames; this frame is 100% ingredient story. "
        f"Optional minimal on-image callouts in {on_img} (2–6 word tags max), no Chinese unless exact packaging "
        "from reference on another frame. Single photograph, NOT a collage grid or split panels."
    )


def shot_is_ingredient_composition_frame(shot: dict) -> bool:
    if shot.get("ingredient_composition_only"):
        return True
    if (shot.get("primary_action_id") or "").strip() == "B07":
        return True
    vid3 = (shot.get("frame3_variant") or "").strip()
    vid5 = (shot.get("frame5_variant") or "").strip()
    sub = (shot.get("layout_subtype") or "").strip()
    return vid3 == "ingredient_composition" or vid5 == "ingredient_composition" or sub == "ingredient_composition"


def apply_ingredient_frame_policy(plan: dict) -> dict:
    """墨西哥/巴西九图、Amazon 七图共用 Listing 管线。"""
    if not is_listing_ecommerce_plan(plan):
        return plan

    lock = build_ingredient_frame_lock_en(plan)
    plan["ingredient_composition_doctrine_en"] = lock

    from generation.services.action_planning.catalog import action_by_id, display_label_zh
    from generation.services.beauty_personal_care import plan_uses_beauty_action_pool

    beauty = plan_uses_beauty_action_pool(plan)
    b07 = action_by_id("B07") or {}
    b07_lock = (b07.get("lock_en") or lock).strip()

    for shot in plan.get("shots") or []:
        if not shot_is_ingredient_composition_frame(shot):
            continue
        shot["ingredient_composition_only"] = True
        shot["ingredient_frame_lock_en"] = lock
        shot["primary_action_id"] = "B07"
        shot["action_master_zh"] = display_label_zh("B07", beauty=beauty)
        shot["product_action_lock_en"] = b07_lock
        neg = (shot.get("negative_extra") or "").strip()
        shot["negative_extra"] = (
            f"{neg}, {INGREDIENT_NO_PRODUCT_NEGATIVE}".strip(", ")
            if neg
            else INGREDIENT_NO_PRODUCT_NEGATIVE
        )

    return plan