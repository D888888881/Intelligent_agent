"""套图视觉一致性：统一色温/调色板；按镜分配合理背景类型；强化机位互斥。"""

from __future__ import annotations

from generation.services.listing_bundle import is_listing_ecommerce_plan, listing_image_count

# 每镜背景类型（可纯色/棚拍/真实内外景，但属同一色彩世界）
BACKGROUND_STRATEGY_BY_INDEX: dict[int, str] = {
    1: (
        "BACKGROUND — Studio sweep, bold solid/gradient accent, OR shallow-DOF lifestyle interior; "
        "must use the SET unified palette (not a random opposite color temperature)."
    ),
    2: "BACKGROUND — Pure #FFFFFF seamless compliance only; shadow tint harmonizes with set palette edges.",
    3: (
        "BACKGROUND — Soft gradient OR real bathroom/vanity still-life; contextual props; "
        "not duplicate hero layout."
    ),
    4: (
        "BACKGROUND — Before/after in the SET theme color. Only brightness may change between halves; "
        "do not switch the after-half to pink, gold, or another hue."
    ),
    5: (
        "BACKGROUND — Studio strip, vertical gradient, or clean tabletop; specs/compare layout."
    ),
    6: (
        "BACKGROUND — Real residential interior (bathroom, bedroom, living) matching product use; "
        "natural window light in SET color grade."
    ),
    7: (
        "BACKGROUND — Real in-use lifestyle interior; TikTok organic lighting; same color grade as set."
    ),
    8: (
        "BACKGROUND — Textured surface flat-lay (marble, linen, wood) — overhead only for this index."
    ),
    9: (
        "BACKGROUND — Same location family and the SAME color grade as frames 1–8. "
        "Do not switch this frame to golden hour, sunset pink, rose, or a warmer accent."
    ),
}

_TYPE_RECIPES: tuple[tuple[str, str], ...] = (
    (
        "condensed geometric grotesque",
        "Headline: extra-bold condensed geometric grotesque, tight tracking, oversized. "
        "Introduction: same family, regular weight. Proof chips: same family, small, wide tracking.",
    ),
    (
        "high-contrast modern serif",
        "Headline: high-contrast modern serif, large, slightly italic. "
        "Introduction: a clean humanist sans, regular. Proof chips: small sans, not the serif.",
    ),
    (
        "wide neo-grotesk",
        "Headline: ultra-bold wide neo-grotesk, open tracking. "
        "Introduction: same family, book weight. Proof chips: compact, same family.",
    ),
    (
        "rounded grotesque",
        "Headline: bold rounded grotesque, generous x-height. Not handwritten, not comic. "
        "Introduction: same family, regular. Proof chips: pill-shaped, same family.",
    ),
    (
        "sharp grotesque",
        "Headline: black-weight sharp grotesque, tight, square terminals. "
        "Introduction: light weight of the same family. Proof lines: tiny uppercase labels.",
    ),
    (
        "editorial serif",
        "Headline: editorial old-style serif, high contrast, oversized. "
        "Introduction: a neutral grotesque. Proof lines: small-caps grotesque.",
    ),
)


def _product_seed(analysis: dict) -> int:
    parts = [
        analysis.get("product_name_es"),
        analysis.get("product_name_en"),
        analysis.get("product_name_zh"),
        analysis.get("primary_function"),
        str(analysis.get("label_text_exact") or "")[:120],
    ]
    total = 0
    for ch in "|".join(str(p or "") for p in parts):
        total = (total * 33 + ord(ch)) % 1000003
    return total or 1


_TITLE_TREATMENTS: tuple[tuple[str, str], ...] = (
    (
        "solid color block",
        "Put the headline on a solid theme-colored rectangle. The block is required. Do not switch it to a thin line.",
    ),
    (
        "type on the photo",
        "Set the headline directly on the photograph with a soft shadow. No rectangle behind the words and no underline.",
    ),
    (
        "hairline underline",
        "Draw one thin rule under the headline only. No color rectangle behind the words.",
    ),
    (
        "side accent",
        "Put a short vertical theme-color bar beside the headline. No rectangle behind the words and no underline.",
    ),
    (
        "outline title",
        "Draw the headline as large outline or knockout type. No filled rectangle and no underline.",
    ),
    (
        "editorial margin",
        "Align the headline to a wide magazine margin with open tracking. No rectangle and no underline.",
    ),
)


def ensure_listing_variation(plan: dict) -> dict:
    """每一套生成单独抽一次。同一套里各张图共用，下一套重新抽。"""
    import random

    plan["listing_variation_nonce"] = random.SystemRandom().randrange(1, 1_000_003)
    return plan


def _variation_nonce(plan: dict) -> int:
    try:
        nonce = int(plan.get("listing_variation_nonce") or 0)
    except (TypeError, ValueError):
        nonce = 0
    if nonce:
        return nonce
    ensure_listing_variation(plan)
    return int(plan["listing_variation_nonce"])


def build_listing_design_system(plan: dict) -> str:
    nonce = _variation_nonce(plan)
    name, type_line = _TYPE_RECIPES[nonce % len(_TYPE_RECIPES)]
    treat, treat_line = _TITLE_TREATMENTS[(nonce // 6) % len(_TITLE_TREATMENTS)]
    plan["listing_type_recipe"] = name
    plan["listing_title_treatment"] = treat
    return (
        "LISTING DESIGN SYSTEM — This set is one campaign. The next set must be allowed to look different. "
        f"TYPE RECIPE «{name}» — {type_line} "
        "Use this type on every text frame of THIS set only. "
        f"TITLE TREATMENT «{treat}» — REQUIRED: {treat_line} "
        "Every text frame in THIS set uses this treatment. "
        "Do not replace it with a thin underline, and do not replace it with a color block, "
        "unless this treatment itself asks for that. "
        "COLOR: only the set theme, split into a deep tone and a light tint. "
        "Keep the letters readable. "
        "No third hue, no rainbow, no default black caption bar, no random script or comic font. "
        "LAYOUT: editorial. The headline is large and is this frame's selling point. "
        "BACKGROUND: a refined campaign surface in the same theme — layered planes and a quiet material "
        "recolored into the theme. Not a blank wall. "
        "Index 2 stays pure #FFFFFF with no design overlay. Index 4 keeps the background and has no marketing type."
    )

COLOR_TEMP_NEGATIVE = (
    "inconsistent color temperature vs other listing frames, one frame in a different hue, "
    "pink or rose frame inside a gray set, gold sunset frame inside a cool set, "
    "random color grade shift, mismatched white balance, second accent color"
)

ANGLE_REPEAT_NEGATIVE = (
    "duplicate camera angle vs other listing frames, same centered 3/4 packshot pose repeated, "
    "identical product rotation and placement as another frame in the set"
)


def _text_list(val) -> list[str]:
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    if isinstance(val, str) and val.strip():
        return [val.strip()]
    return []


def _forbidden_drift(theme: str) -> str:
    blob = (theme or "").lower()
    grayish = any(
        w in blob
        for w in (
            "gray",
            "grey",
            "silver",
            "charcoal",
            "black",
            "white",
            "neutral",
            "灰",
            "银",
            "黑",
            "白",
        )
    )
    if grayish:
        return (
            "This set is gray/neutral. Do not turn walls, light, props, clothes, or the background "
            "pink, rose, peach, coral, magenta, or sunset gold."
        )
    return (
        f"Stay inside {theme}. Do not introduce pink, gold, or any second accent the rest of the set does not use."
    )


def build_set_style_lock(plan: dict) -> str:
    theme = (plan.get("listing_theme_color_en") or "the packaging dominant color").strip()
    temp = (plan.get("listing_color_temperature_lock_en") or "").strip()
    grade = "the same soft grade"
    if "cool-fresh" in temp:
        grade = "one cool-fresh grade"
    elif "warm-premium" in temp:
        grade = "one warm grade"
    elif "balanced-neutral" in temp:
        grade = "one neutral grade"
    return (
        "SET STYLE LOCK — This frame is the same photoshoot as every other frame in the set. "
        f"Color, white balance, contrast, and material finish stay in {theme}, {grade}. "
        f"{_forbidden_drift(theme)} "
        "Do not give this frame its own filter, golden hour, sunset, neon, or a pink cast. "
        "Later lines that mention another light color lose to this lock. "
        "Index 2 stays pure white; the product itself still matches the set."
    )


def _infer_temperature_label(analysis: dict, concept_palette: str) -> str:
    blob = (
        " ".join(_text_list(analysis.get("primary_colors")))
        + " "
        + (analysis.get("visual_identity") or "")
        + " "
        + concept_palette
    ).lower()
    cool_hits = sum(1 for w in ("blue", "cyan", "mint", "teal", "ice", "cool", "clinical") if w in blob)
    warm_hits = sum(1 for w in ("red", "orange", "gold", "amber", "warm", "sun", "terracotta") if w in blob)
    if cool_hits > warm_hits + 1:
        return "cool-fresh cohesive"
    if warm_hits > cool_hits + 1:
        return "warm-premium cohesive"
    return "balanced-neutral cohesive"


def _build_unified_palette(plan: dict) -> str:
    analysis = plan.get("product_analysis") or {}
    dims = plan.get("creative_dimension_matrix") or {}
    product_colors = ", ".join(_text_list(analysis.get("primary_colors"))) or "SKU packaging primaries"
    concept_palette = (dims.get("color_palette") or "").strip()
    color_mood = (plan.get("listing_color_mood_en") or "").strip()
    lighting = (dims.get("lighting") or "").strip()
    parts = [f"Packaging anchors: {product_colors}"]
    if concept_palette:
        parts.append(f"Campaign palette: {concept_palette}")
    if color_mood:
        parts.append(f"Mood: {color_mood}")
    if lighting:
        parts.append(f"Lighting style: {lighting}")
    return "; ".join(parts)


def _category_palette_override(analysis: dict, user_prompt: str) -> str | None:
    blob = (
        (analysis.get("category") or "")
        + " "
        + (analysis.get("primary_function") or "")
        + " "
        + user_prompt[:200]
    ).lower()
    if any(x in blob for x in ("tooth", "oral", "dental", "paste", "牙膏")):
        return (
            "oral-care campaign: crisp white, label reds from packaging, soft mint or clean blue bathroom tones — "
            "one harmonious cool-fresh family across all 9 frames (no warm kitchen orange drift)"
        )
    if any(x in blob for x in ("skin", "cream", "serum", "lotion", "护肤", "洁面")):
        return (
            "beauty campaign: soft neutrals taken from the packaging, one cohesive grade, no extra rose or pink cast — "
            "single cohesive grade"
        )
    if any(
        x in blob
        for x in ("body wash", "shower gel", "沐浴露", "沐浴", "洗浴", "gel de ducha")
    ):
        return (
            "body-wash campaign: shower tile, steam-soft light, white foam on skin; "
            "fresh aqua/mint from packaging — NOT hair salon frizz narrative"
        )
    if any(x in blob for x in ("shampoo", "conditioner", "hair", "护发", "洗发", "发膜", "护发素")):
        return (
            "hair-care campaign: clean bathroom whites, soft green botanical, packaging accent — "
            "vanity/shower contexts; no kitchen citrus drift"
        )
    return None


def apply_listing_visual_cohesion(plan: dict) -> dict:
    if not is_listing_ecommerce_plan(plan):
        return plan
    if plan.get("plan_template") == "reference_guided":
        return plan

    analysis = plan.get("product_analysis") or {}
    user = (plan.get("user_prompt") or plan.get("subject_lock") or "")[:800]
    theme_color = _text_list(analysis.get("primary_colors"))
    theme = theme_color[0] if theme_color else "the packaging dominant color"
    override = _category_palette_override(analysis, user)
    if override and "This set is gray" not in _forbidden_drift(theme):
        plan["listing_color_mood_en"] = override
        dims = dict(plan.get("creative_dimension_matrix") or {})
        dims["color_palette"] = override[:120]
        plan["creative_dimension_matrix"] = dims
        if plan.get("creative_color_system_lock_en"):
            from generation.services.creative_engine.cohesion import build_color_system_lock_en

            plan["creative_color_system_lock_en"] = build_color_system_lock_en(
                palette=override[:120], color_mood=override
            )
    dims = plan.get("creative_dimension_matrix") or {}
    concept_palette = (dims.get("color_palette") or plan.get("listing_color_mood_en") or "").strip()
    temp = _infer_temperature_label(analysis, concept_palette)
    unified = _build_unified_palette(plan)

    plan["listing_unified_palette_en"] = unified
    plan["listing_theme_color_en"] = theme
    plan["listing_color_temperature_lock_en"] = (
        f"LISTING COLOR TEMPERATURE — All {listing_image_count(plan)} frames share ONE temperature: {temp}. "
        f"ONE theme color family from the product: {theme}. Unified palette: {unified}. "
        f"{_forbidden_drift(theme)} "
        "Props, walls, window light, and wardrobe are recolored into this theme. "
        "Hero must not contradict later frames. "
        "White catalog (index 2) stays #FFFFFF; its shadow tint still belongs to this palette."
    )
    mode = (plan.get("background_mode") or "random").strip().lower()
    if mode not in ("random", "solid_virtual", "real_environment"):
        mode = "random"
    plan["background_mode"] = mode
    if mode == "solid_virtual":
        plan["listing_background_variety_policy_en"] = (
            f"BACKGROUND POLICY — Except index 2 (pure #FFFFFF catalog), EVERY frame is a virtual studio "
            f"solid or very soft gradient in the SAME theme color ({theme}). "
            "No rooms, furniture, windows, tiles, streets, or outdoor locations. "
            "Hue, saturation, and color grade stay identical across the set."
        )
    elif mode == "real_environment":
        plan["listing_background_variety_policy_en"] = (
            f"BACKGROUND POLICY — Except index 2 (pure #FFFFFF catalog), EVERY frame is a real environment "
            f"(bathroom, vanity, kitchen, or bedroom that matches how this product is used). "
            f"Color grade stays in ONE theme ({theme}, {temp}). "
            "No plain color sweep, no unrelated location, no second accent hue."
        )
    else:
        plan["listing_background_variety_policy_en"] = (
            "BACKGROUND POLICY — Background TYPE may vary per frame (solid/gradient studio, real interior, real outdoor) "
            f"but every frame uses the SAME theme color ({theme}) and {temp} grade. "
            "Pick background type per frame mandate below; do not mix unrelated genres or a second hue."
        )

    neg = (plan.get("negative_prompt") or "").strip()
    for chunk in (COLOR_TEMP_NEGATIVE, ANGLE_REPEAT_NEGATIVE):
        if chunk.split(",")[0] not in neg:
            neg = f"{neg}, {chunk}".strip(", ")
    plan["negative_prompt"] = neg

    hero_harmony = (
        f"HERO COLOR HARMONY — Index 1 uses the same unified palette and {temp} grade as frames 3–9; "
        f"bold contrast OK, but NOT opposite color temperature. Palette: {unified}."
    )

    for shot in plan.get("shots") or []:
        try:
            idx = int(shot.get("index") or 0)
        except (TypeError, ValueError):
            continue
        bg = BACKGROUND_STRATEGY_BY_INDEX.get(idx)
        if mode == "solid_virtual" and idx != 2:
            bg = (
                f"BACKGROUND — Virtual studio only. Seamless solid or very soft gradient in {theme}. "
                "No real room, furniture, window, tile, street, or outdoor. "
                "Same hue on every non-white frame in this set."
            )
        elif mode == "real_environment" and idx != 2:
            bg = (
                f"BACKGROUND — Real environment only, matching product use, graded in {theme} ({temp}). "
                "Show a believable place (bathroom, vanity, kitchen, or bedroom). "
                "No plain studio color sweep. Same place-family and color grade as the rest of the set."
            )
        if bg and idx != 2:
            bg = (
                f"{bg} DESIGNED SURFACE — refined campaign background in {theme}: "
                "layered planes, a quiet material recolored into the theme, soft geometric shadow. "
                "Not a blank wall and not a flat empty fill."
            )
        if bg:
            shot["listing_background_strategy_en"] = bg
        shot["listing_palette_lock_en"] = (
            f"THEME COLOR — this frame uses only {theme}. "
            f"Palette: {unified}. Grade: {temp}. {_forbidden_drift(theme)} "
            "If a scene idea suggests another color, recolor it into the theme before rendering."
        )
        if idx == 1:
            shot["hero_color_harmony_en"] = hero_harmony
        extra = (shot.get("negative_extra") or "").strip()
        shot["negative_extra"] = f"{extra}, {COLOR_TEMP_NEGATIVE}, {ANGLE_REPEAT_NEGATIVE}".strip(", ")
        shot["set_style_lock_en"] = build_set_style_lock(plan)

    plan["listing_style_lock_en"] = build_set_style_lock(plan)
    plan["listing_design_system_en"] = build_listing_design_system(plan)
    return plan