"""套图 SKU / 品类锚定 — 降低无关商品（灯泡、厨房小家电等）漂移与白底镜职能错乱。"""

from __future__ import annotations

from generation.services.listing_bundle import is_listing_ecommerce_plan

WRONG_PRODUCT_NEGATIVE = (
    "wrong product category, substitute appliances, light bulb, bulb base, lamp socket, "
    "onion chopper, vegetable chopper, vegetable slicer, carrot slicer, food processor, blender base, "
    "dish soap, dishwashing liquid, detergent bottle, limpiador multiusos, spray cleaner, "
    "cleaning product as hero, unrelated kitchen gadget, unrelated electronics, random hardware, "
    "generic tool that is not the listed SKU, competitor unrelated product type"
)

# LLM 常把「对比」写成无关小家电；命中则丢弃整条 generic 描述
_GENERIC_HALUCINATION_NEEDLES = (
    "light bulb",
    "bulb socket",
    "lamp base",
    "onion",
    "chopper",
    "slicer",
    "blender",
    "food processor",
    "juicer",
    "vacuum",
    "drill",
    "screwdriver",
    "dish soap",
    "detergent",
    "limpiador",
    "multiusos",
    "spray cleaner",
    "kitchen gadget",
)


def primary_product_noun_en(analysis: dict, user_prompt: str = "") -> str:
    for key in ("product_name_en", "category", "primary_function"):
        v = (analysis.get(key) or "").strip()
        if v:
            return v[:200]
    up = (user_prompt or "").strip()
    return up[:240] if up else "the exact product from the user brief and reference identity"


def _generic_text_suspect(text: str) -> bool:
    low = (text or "").lower()
    return any(n in low for n in _GENERIC_HALUCINATION_NEEDLES)


def _sanitize_state_field(val: str, noun: str) -> str:
    text = (val or "").strip()
    if not text or _generic_text_suspect(text):
        return (
            f"Oral/personal-care or {noun} use context only — "
            "problem vs improved outcome with THE SAME hero SKU visible, not other product categories"
        )[:400]
    return text[:400]


def sanitize_transformation_states(analysis: dict, noun: str) -> None:
    if analysis.get("before_use_state"):
        analysis["before_use_state"] = _sanitize_state_field(str(analysis["before_use_state"]), noun)
    if analysis.get("after_use_state"):
        analysis["after_use_state"] = _sanitize_state_field(str(analysis["after_use_state"]), noun)
    visual = (analysis.get("before_after_visual_en") or "").strip()
    if visual and _generic_text_suspect(visual):
        analysis["before_after_visual_en"] = (
            f"One photo: same {noun} — muted/problem side vs brighter improved outcome; "
            "SKU packaging unchanged; no cleaning spray or kitchen tools."
        )


def sanitize_same_category_comparison(analysis: dict, noun: str) -> None:
    comp = analysis.get("same_category_comparison")
    if not isinstance(comp, dict):
        analysis["same_category_comparison"] = {
            "generic_alternative_en": (
                f"plain unbranded generic {noun} in the same product category — "
                "dull packaging, no competitor logos"
            ),
            "our_advantages_en": analysis.get("key_selling_points") or [],
        }
        return
    generic = (comp.get("generic_alternative_en") or "").strip()
    if not generic or _generic_text_suspect(generic):
        comp["generic_alternative_en"] = (
            f"plain unbranded generic {noun} only — same category as hero SKU, "
            "NOT kitchen appliances, NOT electronics, NOT home hardware"
        )
    shot = (comp.get("comparison_shot_en") or "").strip()
    if shot and _generic_text_suspect(shot):
        comp.pop("comparison_shot_en", None)


def build_sku_anchor_block(plan: dict, shot: dict) -> str:
    analysis = plan.get("product_analysis") or {}
    noun = plan.get("product_category_anchor_en") or primary_product_noun_en(
        analysis, plan.get("user_prompt") or plan.get("subject_lock") or ""
    )
    identity = (plan.get("identity_lock") or plan.get("product_identity") or noun)[:600]
    if shot.get("ingredient_composition_only"):
        return (
            f"INGREDIENT STORY LOCK — Visuals must match ingredients for {noun} only "
            f"(oral care, skincare actives, etc. per analysis). {identity[:400]}"
        )
    variant = (shot.get("frame5_variant") or "").strip()
    if variant == "category_compare":
        extra = (
            f"The generic/unbranded item on the comparison side MUST be the same category as {noun} "
            "(e.g. another plain toothpaste tube, not a kitchen gadget)."
        )
    else:
        extra = (
            f"Every visible product, prop, and comparison item MUST belong to category: {noun}. "
            "Props support real use (bathroom sink for toothpaste, vanity for skincare) — "
            "never unrelated appliances or hardware."
        )
    return (
        f"STRICT SKU / CATEGORY — Hero object is ONLY {noun}. "
        f"{extra} Match packaging from identity: {identity}"
    )


def apply_product_sku_guard(plan: dict) -> dict:
    if not is_listing_ecommerce_plan(plan):
        return plan
    if plan.get("plan_template") == "reference_guided":
        return plan

    analysis = dict(plan.get("product_analysis") or {})
    user = (plan.get("user_prompt") or plan.get("subject_lock") or "")[:800]
    noun = primary_product_noun_en(analysis, user)
    plan["product_category_anchor_en"] = noun
    sanitize_same_category_comparison(analysis, noun)
    sanitize_transformation_states(analysis, noun)
    plan["product_analysis"] = analysis

    plan["sku_strict_guard_en"] = build_sku_anchor_block(plan, {})

    neg = (plan.get("negative_prompt") or "").strip()
    if "wrong product category" not in neg.lower():
        plan["negative_prompt"] = f"{neg}, {WRONG_PRODUCT_NEGATIVE}".strip(", ")

    hero_lock = (
        f"HERO SKU MANDATORY — The product for sale MUST be {noun} from the reference image "
        "(same tube/bottle/box graphics). NEVER replace the hero with vegetable choppers, "
        "dish soap, spray cleaners, or any unrelated category."
    )
    for shot in plan.get("shots") or []:
        idx = int(shot.get("index") or 0)
        if idx == 2 or (shot.get("role") or "") == "white_bg_catalog":
            shot.setdefault("sku_only_frame", True)
        if idx >= 3 and not shot.get("ingredient_composition_only"):
            v3 = (shot.get("frame3_variant") or "")
            v5 = (shot.get("frame5_variant") or "")
            if v3 != "ingredient_composition" and v5 != "ingredient_composition":
                shot["hero_sku_mandatory_en"] = hero_lock
        extra = (shot.get("negative_extra") or "").strip()
        if "wrong product category" not in extra.lower():
            shot["negative_extra"] = f"{extra}, {WRONG_PRODUCT_NEGATIVE}".strip(", ")

    return plan