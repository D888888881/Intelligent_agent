"""将策划 JSON 中的单镜头字段合成为发给 Grsai 的最终 prompt。"""

from generation.services.image_text_policy import on_image_text_mandate_for_plan
from generation.services.model_strategy import model_family, reference_prefix_for_model


def _safe_text(val, default: str = "") -> str:
    if val is None:
        return default
    if isinstance(val, (list, tuple)):
        joined = " ".join(_safe_text(x) for x in val if x is not None).strip()
        return joined or default
    return str(val).strip() or default


def _shot_needs_sku_only_reference_guard(shot: dict) -> bool:
    role = (shot.get("role") or "").strip()
    modes = [str(m).lower() for m in (shot.get("reference_modes") or [])]
    if role == "reference_directed" and "identity" in modes and any(
        m in ("style_mimic", "model_mimic", "full_mimic", "scene_mimic") for m in modes
    ):
        return True
    cast_mode = (shot.get("human_cast_mode") or "").strip().lower()
    if cast_mode in ("full", "face") and role in (
        "pain_empathy",
        "lifestyle_payoff",
        "hero_hook",
    ):
        return True
    return cast_mode in ("full", "face", "hands") and bool(shot.get("human_model_lock"))


def _reference_guided_attach_block(shot: dict, plan: dict) -> str:
    indices = shot.get("reference_attachment_indices") or []
    modes = shot.get("reference_modes") or []
    roles = plan.get("reference_roles") or []
    lines = [
        "REFERENCE-GUIDED FRAME — Multiple images are attached IN ORDER for this shot. "
        "Follow reference_modes per image; never copy competitor trademarks from style refs.",
    ]
    if any(m in ("layout_mimic", "full_mimic", "style_mimic", "scene_mimic") for m in modes):
        lines.append(
            "LAYOUT MIMIC ACTIVE: layout/style references define composition, crop, zones, "
            "typography blocks and scene structure — identity reference defines the product SKU only."
        )
    if shot.get("reference_payload_canvas_first") and len(indices) >= 2:
        lines.append(
            "API images[] order for this request: index 0 = LAYOUT CANVAS (mimic structure exactly); "
            "index 1+ = SKU identity — replace product inside the canvas only."
        )
    mode_help = {
        "identity": "lock SKU packaging, colors, label from this image only",
        "style_mimic": "match composition, lighting, layout zones — not logo text",
        "layout_mimic": "match information layout (e.g. size chart grid)",
        "model_mimic": "match model pose/lighting/scene tone — new face unless user asked",
        "scene_mimic": "match environment and camera mood",
        "full_mimic": "match overall style but still lock SKU from identity image",
    }
    for pos, att_i in enumerate(indices):
        try:
            ai = int(att_i)
        except (TypeError, ValueError):
            continue
        mode = modes[pos] if pos < len(modes) else "identity"
        hint = mode_help.get(mode, mode)
        label = ""
        for r in roles:
            if isinstance(r, dict) and int(r.get("index", -1)) == ai:
                label = (r.get("label_zh") or r.get("role") or "").strip()
                break
        lines.append(f"Attached image {pos + 1} = user upload #{ai + 1} ({mode}): {hint}.{(' ' + label) if label else ''}")
    mimic = _safe_text(shot.get("mimic_instruction_en"))
    if mimic:
        lines.append(f"Mimic directive: {mimic}")
    intent = _safe_text(shot.get("intent_zh"))
    if intent:
        lines.append(f"Director intent: {intent}")
    return " ".join(lines)


def build_shot_generation_prompt(shot: dict, plan: dict, *, attach_reference: bool = False) -> str:
    parts: list[str] = []
    family = plan.get("image_model_family") or model_family(plan.get("image_model"))
    if attach_reference and family == "gpt_image":
        parts.append(
            "The request includes the product reference image in the images array. "
            "Generate the final 1024x1024 listing image directly; never reply with text-only refusals "
            "asking the user to upload photos — the reference is already attached."
        )
        if _shot_needs_sku_only_reference_guard(shot):
            parts.append(SKU_ONLY_REFERENCE_GUARD)

    quality = _safe_text(plan.get("quality_prefix"))
    if quality:
        parts.append(quality)

    parts.append(on_image_text_mandate_for_plan(plan))
    typo = _safe_text(plan.get("on_image_text_density_mandate_en"))
    if typo:
        parts.append(typo)
    usp_div = _safe_text(plan.get("listing_usp_diversity_lock_en"))
    if usp_div:
        parts.append(usp_div)

    if plan.get("plan_template") == "reference_guided":
        parts.append(_reference_guided_attach_block(shot, plan))
        parts.append(
            "Frame contract: reference_directed — execute this shot per director intent; "
            "not the fixed TK nine-frame matrix."
        )

    identity_lock = _safe_text(
        plan.get("identity_lock") or plan.get("product_identity") or plan.get("subject_lock")
    )
    analysis = plan.get("product_analysis") or {}
    label_exact = _safe_text(analysis.get("label_text_exact"))
    if label_exact:
        identity_lock = f"{identity_lock} Exact label text: {label_exact}".strip()

    variants = analysis.get("product_variants") or []
    is_showcase = bool(shot.get("use_all_reference_images")) or (
        (shot.get("role") or "") == "multi_variant_showcase"
    )

    if is_showcase and isinstance(variants, list) and len(variants) > 1:
        catalog = (shot.get("multi_variant_catalog_en") or plan.get("variants_catalog_en") or "").strip()
        parts.append(
            "MULTI-VARIANT SHOWCASE — One single professional e-commerce photograph showing ALL colorways and styles "
            "listed below together (e.g. lipsticks in a row, multi-color sneakers side-by-side, "
            "bras/camisoles/underwear in a color lineup, mixed sizes only if listed). "
            "Single real photo, not a collage grid with panels or contact sheet. "
            "Each SKU must match its variant identity (color + style + material); do not duplicate one item."
        )
        if catalog:
            parts.append(f"All variants to include: {catalog}")
        parts.append(
            "Use every attached reference image to lock packaging, shades, and shapes; "
            "arrange products clearly so each shade is recognizable at thumbnail size."
        )
    else:
        variant_label = (shot.get("variant_label") or "").strip()
        variant_extra = (shot.get("variant_identity_extra") or "").strip()
        variant_pos = (shot.get("variant_in_frame_position") or "").strip()
        if variant_label:
            parts.append(
                f"This frame features SKU/colorway: {variant_label}. "
                "Match the reference image that shows this exact variant; do not swap colors between variants."
            )
        if variant_extra:
            parts.append(f"Variant identity lock: {variant_extra}")
        vstyle = (shot.get("variant_style_en") or "").strip()
        vsize = (shot.get("variant_size_en") or "").strip()
        if vstyle:
            parts.append(f"Garment/footwear style for this frame: {vstyle}.")
        if vsize:
            parts.append(f"Size/fit label for this frame (if visible on product): {vsize}.")
        if variant_pos:
            parts.append(f"If using a multi-product reference photo, the target variant is at: {variant_pos}.")
        if isinstance(variants, list) and len(variants) > 1:
            parts.append(
                f"Listing has {len(variants)} colorways/SKUs across reference images; "
                "this frame must show only the assigned variant."
            )

    orient = (shot.get("orientation_lock") or "").strip()
    if orient:
        parts.append(
            "MANDATORY PRODUCT ORIENTATION (override reference photo pose — rotate product accordingly): "
            f"{orient}"
        )

    roster = plan.get("camera_roster") or {}
    try:
        cur_idx = int(shot.get("index") or 0)
    except (TypeError, ValueError):
        cur_idx = 0
    if roster and cur_idx:
        others = [f"#{i} uses {roster[i]}" for i in sorted(roster.keys()) if i != cur_idx]
        if others:
            parts.append(
                "Angle diversity lock — other frames already use these orientations; "
                f"this frame must differ: {'; '.join(others)}."
            )

    if identity_lock and not shot.get("ingredient_composition_only"):
        if family == "banana":
            parts.append(
                "CRITICAL SKU — packaging graphics, bottle/box colors, and label must match reference "
                "and this spec exactly (no redesign): "
                f"{identity_lock}"
            )
        else:
            parts.append(
                "Product identity (same SKU, colors, label wording): "
                f"{identity_lock}"
            )

    ingredient_only = (shot.get("ingredient_frame_lock_en") or "").strip()
    if ingredient_only or shot.get("ingredient_composition_only"):
        if ingredient_only:
            parts.append(ingredient_only)
        else:
            from generation.services.ingredient_frame_policy import build_ingredient_frame_lock_en

            parts.append(build_ingredient_frame_lock_en(plan))
    product_action = (shot.get("product_action_lock_en") or "").strip()
    if product_action:
        parts.append(product_action)
    set_actions = (plan.get("action_set_diversity_en") or "").strip()
    if set_actions:
        parts.append(set_actions)

    comp = (shot.get("composition_mandate") or "").strip()
    if comp:
        parts.append(comp)
    elif shot.get("ingredient_composition_only"):
        parts.append(
            "Composition: full-bleed ingredient still-life edge-to-edge; NO sellable SKU unit; "
            "textures and actives fill the frame; professional listing detail photo."
        )
    elif family == "gpt_image":
        parts.append(
            "Composition: product is the clear hero (≥50% visual weight), professional TikTok Shop layout, "
            "strong focal point, balanced typography space, not a duplicate angle of other listing shots."
        )

    tpl = (plan.get("plan_template") or "").strip()
    try:
        shot_idx = int(shot.get("index") or 0)
    except (TypeError, ValueError):
        shot_idx = 0
    is_amazon = tpl == "amazon_listing_7"

    role = (shot.get("role") or "").strip()
    if role == "white_bg_catalog":
        if is_amazon and shot_idx == 1:
            parts.append(
                "Frame type: Amazon main image — pure #FFFFFF compliance catalog; product only; "
                "NO added marketing text, icons, or captions; only factory packaging print on SKU."
            )
        else:
            parts.append(
                "Frame type: TikTok Shop compliance white background (#FFFFFF) — product only; "
                "NO added marketing text, NO icons, NO captions; authentic packaging print on SKU only."
            )
        wb = (shot.get("white_bg_text_lock") or "").strip()
        if wb:
            parts.append(wb)
    elif role == "hero_hook":
        impact = (shot.get("hero_visual_impact_lock") or "").strip()
        if impact:
            parts.append(impact)
        lang = (plan.get("on_image_language") or "English").strip()
        if is_amazon and shot_idx == 2:
            parts.append(
                f"Frame type: Amazon core value hero — scroll-stopping impact with bold {lang} headline zone; "
                "communicates primary purchase reason; NOT white catalog clone of index 1."
            )
        else:
            parts.append(
                "Frame type: INDEX 1 hero — maximum scroll-stopping visual impact (contrast, depth, lighting, "
                "color accent) plus Spanish headline zone; NOT a plain catalog packshot."
            )
    elif role == "usp_primary":
        if is_amazon and shot_idx == 4 and (shot.get("frame4_variant") or "") == "scene_immersion":
            geo = (plan.get("scene_geo_en") or "local").strip()
            parts.append(
                f"Frame type: Amazon scene immersion — authentic {geo} daily-life usage context; "
                "NOT before/after layout this batch."
            )
        else:
            parts.append(
                "Frame type: pain before/after in ONE single photograph (not collage grid); "
                "visual transformation only — NO generic-vs-hero product compare on this frame; "
                "NO before/after/antes/después/使用前/使用后 labels on image."
            )
        flex4 = (plan.get("frame4_flex_summary_en") or "").strip()
        if flex4:
            parts.append(flex4)
    elif role == "usp_secondary":
        variant = (shot.get("frame5_variant") or "category_compare").strip()
        _frame5_hints = {
            "category_compare": (
                "Frame type: our SKU vs generic unbranded same-category product side-by-side in one shot; "
                "no competitor trademarks or real rival brand packaging."
            ),
            "specs_features": (
                "Frame type: specs & attributes — size, capacity, color, dimensions with minimal Spanish labels; "
                "single 1:1 photo, not index-2 white duplicate."
            ),
            "kit_contents": (
                "Frame type: what's in the box — kit items and quantity in one angled layout; "
                "distinct from index 8 pure value story."
            ),
            "usage_steps": (
                "Frame type: 2–4 usage steps in ONE photo (flow, not collage grid); short Spanish step tags."
            ),
            "core_functions": (
                "Frame type: core function highlights — 3–4 feature cues with minimal Spanish callouts."
            ),
            "ingredient_composition": (
                "Frame type: full-frame ingredient composition — actives and textures only; NO product unit."
            ),
        }
        parts.append(_frame5_hints.get(variant, _frame5_hints["category_compare"]))
        flex_sum = (plan.get("frame5_flex_summary_en") or "").strip()
        if flex_sum:
            parts.append(flex_sum)
    elif role == "pain_empathy":
        v3 = (shot.get("frame3_variant") or "benefit_solve_visual").strip()
        if v3 == "ingredient_composition":
            parts.append(
                "Frame type: full-frame ingredient composition — botanicals/actives edge-to-edge; "
                "NO product bottle or packaging in this image."
            )
        elif v3 == "product_detail_macro":
            parts.append(
                "Frame type: product detail — material, texture, craft, interface, label/packaging macro; "
                "not white catalog clone; not frame 6 room scene."
            )
        else:
            parts.append(
                "Frame type: benefit contrast — visualize solved pains (comfort, storage, space, smooth, "
                "durable, slimming, convenience); visual only, no antes/después labels."
            )
        flex3 = (plan.get("frame3_flex_summary_en") or "").strip()
        if flex3:
            parts.append(flex3)
    elif role == "trust_quality":
        geo = (plan.get("scene_geo_adj_en") or plan.get("scene_geo_en") or "local").strip()
        if is_amazon and shot_idx == 4:
            parts.append(
                f"Frame type: Amazon scene immersion — product in authentic {geo} daily context; "
                "natural light; purchase代入感; no before/after split; no dominant face."
            )
        else:
            parts.append(
                "Frame type: real-life trust — product naturally placed in authentic daily scene "
                "(home, bathroom, bedroom, kitchen, street café, or office); natural light, no sterile macro; "
                "no dominant face."
            )
    elif role == "ease_objection":
        demo = (shot.get("feature_demo_lock_en") or "").strip()
        if demo:
            parts.append(demo)
        elif is_amazon and shot_idx == 6:
            parts.append(
                "Frame type: Amazon feature demonstration — active use proving function/effect; "
                "hands allowed; not crowd portrait."
            )
        else:
            parts.append(
                "Frame type: target-audience crowd scene — real consumer mid-use with TikTok organic seeding look; "
                "natural light, candid half-body or 3/4; product clearly in use; not hands-only step macro."
            )
    elif role == "value_stack":
        kit = (plan.get("amazon_kit_summary_en") or "").strip()
        if is_amazon and shot_idx == 7:
            parts.append(
                "Frame type: Amazon what's-in-the-box — all included items, accessories, and quantity in one "
                "angled or shelf layout; warm premium styling; not a repeat of white main image."
            )
            if kit:
                parts.append(kit)
        else:
            parts.append(
                "Frame type: value bundle / kit contents — show package items and quantity; premium layout."
            )
    elif role == "lifestyle_payoff":
        v9 = (shot.get("frame9_variant") or "conversion_close").strip()
        _frame9_hints = {
            "daily_essential": (
                "Frame type: conversion close — daily essential routine scene; product in real daily Mexico context; "
                "not a sterile packshot."
            ),
            "gift_worthy": (
                "Frame type: conversion close — gift-giving moment (ribbon, bag, hands presenting); regalo atmosphere."
            ),
            "family_must_have": (
                "Frame type: conversion close — family household must-have; shared home props; warm domestic mood."
            ),
            "smart_buy": (
                "Frame type: conversion close — worth-buying confidence; smart purchase decision staging."
            ),
            "benefit_summary": (
                "Frame type: conversion close — benefit summary slide with 3–4 unique Spanish bullets + visible product."
            ),
            "lifestyle_aspiration": (
                "Frame type: conversion close — aspirational lifestyle payoff; environment sells the dream."
            ),
        }
        parts.append(_frame9_hints.get(v9, _frame9_hints["daily_essential"]))
        flex9 = (plan.get("frame9_flex_summary_en") or "").strip()
        if flex9:
            parts.append(flex9)
        conv = (shot.get("conversion_story_lock") or "").strip()
        if conv:
            parts.append(conv)

    pillar = (shot.get("marketing_pillar") or "").strip()
    archetype = (shot.get("visual_archetype") or "").strip()
    scene_family = (shot.get("scene_family") or "").strip()
    if pillar:
        q = (shot.get("consumer_question") or "").strip()
        parts.append(
            f"ECOMMERCE STORY BEAT — {pillar}. Answer in the image: {q}. "
            f"Visual archetype: {archetype}. Scene family: {scene_family}. "
            "Must differ from other frames in camera angle, layout, and scene — not a slight rotation."
        )

    diversity = _safe_text(shot.get("diversity_lock"))
    if diversity:
        parts.append(f"Uniqueness requirement: {diversity}")

    action_lock = (shot.get("action_lock") or "").strip()
    if action_lock:
        parts.append(action_lock)
    creative_dir = (shot.get("creative_detail_direction_en") or "").strip()
    if creative_dir:
        parts.append(creative_dir)
    density_lock = (shot.get("composition_density_lock") or "").strip()
    if density_lock:
        parts.append(density_lock)
    contract = (shot.get("frame_contract") or "").strip()
    if contract == "fixed":
        if is_amazon and shot_idx == 1:
            parts.append(
                "FRAME CONTRACT — Fixed Amazon main white catalog. No marketing overlay text; "
                "unique camera vs other six frames."
            )
        elif is_amazon and shot_idx == 2:
            parts.append(
                "FRAME CONTRACT — Fixed Amazon core value hero; not white catalog duplicate."
            )
        else:
            parts.append(
                "FRAME CONTRACT — Fixed TK slot (hero or white background). "
                "Do not change the marketing role; only execute with unique camera vs other frames."
            )
    elif contract == "flex_variant":
        parts.append(
            "FRAME CONTRACT — Flex variant slot (frame 4 before/after or frame 5 variant): "
            "execute the assigned mandate only; do not switch to another frame's marketing role."
        )
    elif contract == "creative_detail":
        roster_actions = plan.get("detail_action_roster") or {}
        try:
            cur_i = int(shot.get("index") or 0)
        except (TypeError, ValueError):
            cur_i = 0
        if roster_actions and cur_i:
            others = [f"#{i}={c}" for i, c in sorted(roster_actions.items()) if i != cur_i]
            if others:
                parts.append(
                    "CREATIVE DETAIL — Action must differ from other detail frames: "
                    + ", ".join(others)
                )

    cast_gender = (plan.get("talent_cast_gender") or "").strip().lower()
    skin_preset = (plan.get("cast_skin_preset") or "caucasian").strip().lower()
    cosmetics_hint = (plan.get("cosmetics_cast_hint_en") or "").strip()
    if cast_gender == "female" and role in ("hero_hook", "pain_empathy", "usp_primary", "ease_objection", "lifestyle_payoff"):
        parts.append(
            "MODEL GENDER — Female-presenting adult models only; product is marketed to women. "
            "Forbidden: men, beards, or masculine faces wearing/applying this product."
        )
        if cosmetics_hint:
            parts.append(cosmetics_hint)
    elif cast_gender == "male" and role in ("hero_hook", "pain_empathy", "usp_primary", "ease_objection", "lifestyle_payoff"):
        parts.append(
            "MODEL GENDER — Male adult models only; product is men's grooming or menswear."
        )

    human_lock = (shot.get("human_model_lock") or shot.get("talent_profile_en") or "").strip()
    if human_lock:
        parts.append(human_lock if human_lock.startswith("HUMAN CAST") else f"HUMAN CAST — {human_lock}")
        roster = plan.get("talent_roster") or {}
        try:
            cur_idx = int(shot.get("index") or 0)
        except (TypeError, ValueError):
            cur_idx = 0
        if roster and cur_idx:
            others = [
                f"frame #{i} uses talent {tid}"
                for i, tid in sorted(roster.items())
                if i != cur_idx
            ]
            if others:
                tail = (
                    "Use distinct model identity per frame."
                    if skin_preset in ("caucasian", "black_only")
                    else "Vary skin tone across the set (light, medium, brown) when humans appear."
                )
                parts.append(
                    "Do not reuse the same face, body type, or skin tone as: "
                    + "; ".join(others[:8])
                    + f". {tail}"
                )
    elif plan.get("talent_roster"):
        if skin_preset == "black_only":
            parts.append(
                "If people or hands appear: Black / deep brown skin models only; unique identity per frame."
            )
        elif skin_preset == "caucasian":
            parts.append(
                "If people or hands appear: Caucasian / fair skin models only; unique identity per frame."
            )
        else:
            parts.append(
                "If this frame includes people or hands, use a unique model identity — "
                "never the default repeated AI face; diverse skin tones suitable for LATAM."
            )

    story_theme = (plan.get("listing_story_theme_en") or "").strip()
    if story_theme:
        parts.append(story_theme)
    color_mood = (plan.get("listing_color_mood_en") or "").strip()
    if color_mood:
        parts.append(f"Color mood for entire listing set: {color_mood}")

    for plan_cohesion_key in (
        "creative_set_cohesion_en",
        "creative_color_system_lock_en",
        "creative_scene_family_lock_en",
        "creative_camera_innovation_lock_en",
    ):
        block = (plan.get(plan_cohesion_key) or "").strip()
        if block:
            parts.append(block)

    prev_avoid = (plan.get("previous_batch_avoidance_en") or "").strip()
    if prev_avoid:
        parts.append(prev_avoid)

    budget_en = (plan.get("human_presence_budget_en") or "").strip()
    if budget_en:
        parts.append(budget_en)

    layout_lock = (plan.get("layout_diversity_lock_en") or "").strip()
    if layout_lock:
        parts.append(layout_lock)

    angle_lock = (plan.get("listing_angle_diversity_lock_en") or "").strip()
    if angle_lock:
        parts.append(angle_lock)

    story_arc = (plan.get("conversion_story_lock_en") or "").strip()
    if story_arc and role in (
        "pain_empathy",
        "trust_quality",
        "ease_objection",
        "value_stack",
        "lifestyle_payoff",
        "hero_hook",
        "usp_primary",
    ):
        parts.append(story_arc)

    usp_lock = (shot.get("usp_message_lock") or "").strip()
    if usp_lock:
        parts.append(usp_lock)
    layout_hint = (shot.get("on_image_text_layout_en") or "").strip()
    if layout_hint:
        parts.append(layout_hint)
    exclusive = (shot.get("exclusive_usp_en") or "").strip()
    if exclusive:
        parts.append(f"Exclusive angle (do not duplicate other frames): {exclusive}")

    roster_es = plan.get("listing_message_roster_es") or {}
    try:
        cur_idx = int(shot.get("index") or 0)
    except (TypeError, ValueError):
        cur_idx = 0
    if roster_es and cur_idx:
        others = [
            f"#{i} already uses «{roster_es[i]}»"
            for i in sorted(roster_es.keys())
            if i != cur_idx and roster_es.get(i)
        ]
        if others:
            parts.append(
                "Other frames' Spanish messages (do NOT repeat): " + "; ".join(others[:8]) + "."
            )

    for lock_key in (
        "material_story_lock",
        "story_beat_lock",
        "transformation_story_lock",
        "frame3_content_lock",
        "frame4_content_lock",
        "frame5_content_lock",
        "frame9_content_lock",
        "conversion_story_lock",
        "set_cohesion_lock_en",
    ):
        block = (shot.get(lock_key) or "").strip()
        if block:
            parts.append(block)

    cast_mode = (shot.get("human_cast_mode") or "").strip().lower()
    if cast_mode == "none":
        parts.append(
            "NO HUMAN — This frame must be product-only or environment-only; "
            "no face, no hands, no model silhouette."
        )
    elif cast_mode == "hands":
        parts.append(
            "HUMAN PRESENCE — Hands/forearms only; crop above wrists; no full face in frame."
        )
    elif cast_mode == "face":
        parts.append(
            "HUMAN PRESENCE — Face or skin crop allowed; avoid full-body duplicate of other frames."
        )

    batch_idx = plan.get("visual_batch_index")
    pack_name = (plan.get("visual_batch_pack_name") or "").strip()
    if pack_name is not None and batch_idx is not None:
        parts.append(
            f"Listing visual batch #{int(batch_idx) + 1} (pack: {pack_name}) — "
            "must look like a fresh creative direction, not a reshoot of the last batch."
        )

    parts.append("SCENE DIRECTION:")

    prompt_en = (shot.get("prompt_en") or "").strip()
    if prompt_en:
        parts.append(prompt_en)

    try:
        shot_idx = int(shot.get("index") or 0)
    except (TypeError, ValueError):
        shot_idx = 0
    skip_marketing_text = role == "white_bg_catalog" or shot_idx == 2

    if not skip_marketing_text:
        headline_es = (shot.get("headline_es") or "").strip()
        subhead_es = (shot.get("subhead_es") or "").strip()
        icon_bullets = shot.get("icon_bullets_es") or []
        if isinstance(icon_bullets, str):
            icon_bullets = [s.strip() for s in icon_bullets.split("|") if s.strip()]
        if headline_es:
            parts.append(f"On-image Spanish headline line 1 (Español México, SEO): {headline_es}")
        if subhead_es:
            parts.append(f"On-image Spanish headline line 2: {subhead_es}")
        if icon_bullets:
            parts.append(
                "On-image bottom ICON bullets (2-3 Spanish words each, simple circles): "
                + "; ".join(str(b) for b in icon_bullets[:3])
            )
        prompt_es = _safe_text(shot.get("prompt_es") or shot.get("key_message_es"))
        if prompt_es and not headline_es:
            parts.append(f"On-image marketing text in Spanish (Español México): {prompt_es}")
        elif prompt_es and headline_es and prompt_es != headline_es:
            parts.append(f"Additional short Spanish caption if needed: {prompt_es}")

    locale = plan.get("locale")
    if locale and str(locale).lower() not in ("user", "custom", "none", ""):
        parts.append(f"Market: TikTok Shop {locale} e-commerce listing image.")

    negative = _safe_text(shot.get("negative_extra") or plan.get("negative_prompt"))
    if negative:
        parts.append(f"Avoid: {negative}")

    return " ".join(parts)


SKU_ONLY_REFERENCE_GUARD = (
    "REFERENCE IMAGE RULE — The attached image is for PRODUCT PACKAGING / SKU identity ONLY "
    "(shape, label, colors, cap). Do NOT copy any person, face, skin tone, hairstyle, pose, "
    "or background scene from the reference. Generate a NEW human model exactly as described "
    "in HUMAN CAST below. If the reference shows a model, ignore that model entirely."
)


def is_reference_refusal_error(exc: BaseException) -> bool:
    """Grsai status=violation 但 error 是「请上传参考图」类拒答，不是色情/暴力审核。"""
    text = str(exc)
    lower = text.lower()
    needles = (
        "上传",
        "参考图",
        "参考照片",
        "原始参考",
        "实物参考",
        "实物",
        "没有可供",
        "无法保证包装",
        "无法读取",
        "reference photo",
        "original reference",
        "upload",
        "product image",
        "attach",
    )
    if any(n in text if ord(n[0]) > 127 else n in lower for n in needles):
        return True
    return False


def is_violation_error(exc: BaseException) -> bool:
    if is_reference_refusal_error(exc):
        return False
    text = str(exc).lower()
    return "violation" in text or "审核" in text or "violat" in text


def build_reference_forced_prompt(
    shot: dict,
    plan: dict,
    *,
    sku_only_person_guard: bool = False,
) -> str:
    """上游拒答缺图时：短、命令式英文 + 明确已附带参考图。"""
    model = plan.get("image_model")
    prefix = reference_prefix_for_model(model, has_reference=True)
    if sku_only_person_guard or _shot_needs_sku_only_reference_guard(shot):
        prefix = f"{prefix} {SKU_ONLY_REFERENCE_GUARD} "
    body = build_shot_generation_prompt(shot, plan, attach_reference=True)
    return prefix + body


def build_moderation_fallback_prompt(shot: dict, plan: dict, *, with_reference: bool = False) -> str:
    """真·内容审核失败时：短 prompt；若任务有参考图则仍附带 images 锁 SKU。"""
    if with_reference:
        return build_reference_forced_prompt(shot, plan)
    identity = (plan.get("identity_lock") or plan.get("product_identity") or "")[:500]
    role = shot.get("role") or "product"
    es = (shot.get("prompt_es") or "")[:60]
    parts = [
        "Professional e-commerce product photo, square 1:1, no people, no hands, no faces, no nudity.",
        "Single product only, clean commercial lighting, TikTok Shop safe content.",
        f"Product (same SKU): {identity}",
        f"Shot type: {role}.",
        (shot.get("prompt_en") or "")[:600],
    ]
    if es:
        parts.append(f"Spanish text on image: {es}")
    parts.append("Avoid: collage, duplicate angle, policy unsafe content.")
    return " ".join(p for p in parts if p)


def shot_uses_reference(shot: dict, plan: dict) -> bool:
    if plan.get("plan_template") == "reference_guided":
        return bool(shot.get("reference_attachment_indices"))
    mode = (shot.get("reference_mode") or plan.get("default_reference_mode") or "identity").lower()
    if mode in ("none", "false", "no", "0"):
        return False
    return mode in ("identity", "scene", "true", "yes", "1")
