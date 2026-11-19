"""套图创意：单批内色彩/场景气质一致，背景类型与机位可大胆变化。"""

from __future__ import annotations

CREATIVE_SET_COHESION_CORE_EN = (
    "SET COHESION — Entire listing is ONE visual campaign. "
    "Color span stays controlled: one hue family with shared neutrals; "
    "no unrelated palettes (cold neon vs warm amber vs random primaries) in the same set. "
    "Scene STYLE span stays controlled: one production-design world; "
    "background TYPE may differ per frame but mood and treatment must match. "
    "Camera angles and product placement may be bold and frame-specific when they serve the SKU."
)

BACKGROUND_TYPES_WITHIN_FAMILY_EN = (
    "Allowed background types within the same scene family (pick per frame, do not mix unrelated genres): "
    "solid or gradient color backdrop; stylized fictional set; real residential interior; "
    "real outdoor street/park/café; controlled photo studio sweep; textured surface still-life; "
    "soft environmental bokeh. White catalog frame stays compliant white — "
    "its accent color and shadow tone must still harmonize with the set color system."
)


def _product_story_hint(plan: dict) -> str:
    analysis = plan.get("product_analysis") or {}
    for key in ("product_identity_en", "product_identity", "short_title_en", "category_guess"):
        val = (analysis.get(key) or "").strip()
        if val:
            return val[:240]
    ident = (plan.get("product_identity") or "").strip()
    if ident:
        return ident[:240]
    return "SKU shape, material, scale, and core selling points from reference image"


def build_color_system_lock_en(*, palette: str, color_mood: str) -> str:
    anchor = palette or color_mood or "derive from product packaging and category"
    mood = color_mood or palette or ""
    parts = [
        "COLOR SYSTEM LOCK — All frames share one palette:",
        anchor + ".",
    ]
    if mood and mood != anchor:
        parts.append(f"Mood accents: {mood}.")
    parts.append(
        "Keep saturation and hue within one harmonious family (analogous or muted complementary). "
        "Repeat 1–2 accent colors across frames; white-bg frame uses the same shadow/tint logic. "
        "Forbidden: jumping to unrelated color worlds frame-to-frame."
    )
    return " ".join(parts)


def build_scene_family_lock_en(*, visual_style: str, scene_environment: str) -> str:
    return (
        f"SCENE FAMILY LOCK — Visual style: {visual_style or 'editorial lifestyle'}; "
        f"environment anchor: {scene_environment or 'coherent campaign set'}. "
        f"{BACKGROUND_TYPES_WITHIN_FAMILY_EN} "
        "Forbidden: mixing unrelated genres (e.g. cyberpunk + rustic farmhouse + clinical lab) in one set."
    )


def build_camera_innovation_lock_en(*, camera_language: str, plan: dict) -> str:
    product_hint = _product_story_hint(plan)
    baseline = camera_language or "varied purposeful angles"
    return (
        "CAMERA & PRODUCT STAGING — Innovate boldly: low/high hero, elevated 3/4, overhead flatlay, "
        "tight macro, wide environmental, dynamic asymmetry — each frame may differ. "
        f"Product rationale: {product_hint}. "
        f"Baseline camera language: {baseline}. "
        "Choose angles that show material, structure, and use case — not gimmick angles that hide the SKU or label. "
        "Do NOT reuse identical centered packshot pose on every frame."
    )


def build_conversion_story_lock_en(plan: dict) -> str:
    theme = (plan.get("listing_story_theme_en") or "").strip()
    color_mood = (plan.get("listing_color_mood_en") or "").strip()
    chunks = []
    if theme:
        chunks.append(theme)
    if color_mood:
        chunks.append(f"Color mood: {color_mood}.")
    chunks.append(CREATIVE_SET_COHESION_CORE_EN)
    for key in (
        "creative_color_system_lock_en",
        "creative_scene_family_lock_en",
        "creative_camera_innovation_lock_en",
        "creative_concept_mandate_en",
    ):
        block = (plan.get(key) or "").strip()
        if block:
            chunks.append(block)
    return " ".join(chunks).strip()


def apply_creative_set_cohesion(plan: dict, concept: dict) -> dict:
    dims = concept.get("dimensions") or {}
    palette = (dims.get("color_palette") or "").strip()
    color_mood = (concept.get("color_mood_en") or "").strip()
    visual_style = (dims.get("visual_style") or "").strip()
    scene_env = (dims.get("scene_environment") or "").strip()
    camera = (dims.get("camera_language") or "").strip()

    plan["creative_set_cohesion_en"] = CREATIVE_SET_COHESION_CORE_EN
    plan["creative_color_system_lock_en"] = build_color_system_lock_en(
        palette=palette, color_mood=color_mood
    )
    plan["creative_scene_family_lock_en"] = build_scene_family_lock_en(
        visual_style=visual_style, scene_environment=scene_env
    )
    plan["creative_camera_innovation_lock_en"] = build_camera_innovation_lock_en(
        camera_language=camera, plan=plan
    )
    plan["creative_background_variety_en"] = BACKGROUND_TYPES_WITHIN_FAMILY_EN
    return plan
