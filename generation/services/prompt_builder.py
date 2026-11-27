"""将策划 JSON 中的单镜头字段合成为发给 Grsai 的最终 prompt。"""

from generation.services.image_text_policy import on_image_text_mandate_for_plan
from generation.services.model_strategy import model_family, reference_prefix_for_model
from generation.services.product_sku_guard import build_sku_anchor_block
from generation.services.tk_mx_listing import WHITE_BG_SCENE_PROMPT_EN
from generation.services.variant_shots import white_bg_variant_lineup_en

FRAME4_PRIORITY_GOAL_EN = (
    "FRAME 4 PRIMARY GOAL — One photograph: unmistakable BEFORE→AFTER on the SAME efficacy as packaging "
    "and hero/frame-3 Spanish benefits (product_efficacy_anchor_en + frame4_authoritative_en). "
    "Model + correct application zone when required (body wash = shower skin+foam, not hair). "
    "Transformation subject ≥50% of frame. WRONG: wrong category compare, conditioner on body-wash SKU."
)


def _placeholder_on_image(text: str) -> bool:
    """内部占位编号，不能写进生图提示，否则会被画成标题。"""
    import re

    return bool(re.search(r"detalle propio|uso concreto|punto\s*\d+", text or "", re.I))


def _generic_selling_line(text: str) -> bool:
    import re

    return bool(
        re.search(
            r"detalle propio|uso concreto|punto\s*\d|formula estable|fórmula estable|"
            r"textura clara|acabado uniforme|calidad premium|f[aá]cil de usar",
            text or "",
            re.I,
        )
    )


def _core_function_prefix(plan: dict, shot: dict) -> str:
    """每张图开头只带一句功效；带字的图再加自己的一条卖点。"""
    from generation.services.product_usage_semantics import build_core_function_line_en

    analysis = plan.get("product_analysis") or {}
    user = (plan.get("user_prompt") or plan.get("subject_lock") or "")[:800]
    line = (build_core_function_line_en(analysis, user) or "").strip()
    if not line:
        line = (plan.get("listing_core_function_en") or "").strip()
    try:
        idx = int(shot.get("index") or 0)
    except (TypeError, ValueError):
        idx = 0
    if idx in (2, 4):
        return f"{line} No selling-point text on this image."
    headline = (shot.get("headline_es") or "").strip()
    if headline and not _placeholder_on_image(headline) and not _generic_selling_line(headline):
        return f"{line} THIS FRAME SELLING POINT — «{headline[:56]}» only."
    return line


def _listing_variant_count(plan: dict) -> int:
    analysis = plan.get("product_analysis") or {}
    variants = analysis.get("product_variants") or []
    count = len(variants) if isinstance(variants, list) else 0
    for raw in (plan.get("variant_count"), plan.get("reference_image_count")):
        try:
            count = max(count, int(raw or 0))
        except (TypeError, ValueError):
            continue
    return count


def _white_bg_lineup_prompt(shot: dict, plan: dict) -> str:
    count = _listing_variant_count(plan)
    if count <= 1:
        return ""
    try:
        idx = int(shot.get("index") or 0)
    except (TypeError, ValueError):
        idx = 0
    role = (shot.get("role") or "").strip()
    if idx == 2 or role == "white_bg_catalog":
        return white_bg_variant_lineup_en(count)
    return ""


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


def _listing_visual_cohesion_early_block(shot: dict, plan: dict) -> str:
    try:
        shot_ix = int(shot.get("index") or 0)
    except (TypeError, ValueError):
        shot_ix = 0
    tpl = (plan.get("plan_template") or "").strip()
    tk4 = tpl == "tk_mx_ecommerce_9" and shot_ix == 4
    tk2_white = tpl == "tk_mx_ecommerce_9" and shot_ix == 2

    plan_keys = (
        "listing_color_temperature_lock_en",
        "listing_design_system_en",
        "listing_unified_palette_en",
        "listing_background_variety_policy_en",
        "creative_set_cohesion_en",
        "creative_color_system_lock_en",
        "creative_scene_family_lock_en",
        "creative_background_variety_en",
        "listing_camera_mandate_strict_en",
        "listing_product_pose_diversity_en",
        "listing_conversion_master_en",
        "listing_usp_roster_en",
        "listing_matrix_obey_en",
        "listing_tk_matrix_obey_en",
        "listing_human_mandate_en",
        "product_usage_master_en",
        "listing_frame_focus_discipline_en",
        "listing_nine_frame_doctrine_zh",
        "creative_concept_mandate_en",
    )
    if tk4:
        plan_keys = tuple(
            k
            for k in plan_keys
            if k
            not in (
                "listing_conversion_master_en",
                "listing_usp_roster_en",
                "creative_concept_mandate_en",
                "creative_scene_family_lock_en",
                "creative_background_variety_en",
                "creative_set_cohesion_en",
                "listing_nine_frame_doctrine_zh",
            )
        )
    if tk2_white:
        plan_keys = tuple(
            k
            for k in plan_keys
            if k
            not in (
                "listing_product_pose_diversity_en",
                "listing_camera_mandate_strict_en",
                "listing_human_mandate_en",
            )
        )

    chunks: list[str] = []
    for key in plan_keys:
        block = (plan.get(key) or "").strip()
        if block:
            chunks.append(block)
    for key in (
        "listing_background_strategy_en",
        "listing_palette_lock_en",
        "hero_color_harmony_en",
        "frame_single_focus_en",
    ):
        block = (shot.get(key) or "").strip()
        if block:
            chunks.append(block)
    if chunks:
        mode = (plan.get("background_mode") or "random").strip().lower()
        theme = (plan.get("listing_theme_color_en") or "the packaging dominant color").strip()
        if mode == "solid_virtual":
            unity = (
                "LISTING VISUAL UNITY — One campaign, one theme color. "
                f"Except the white catalog frame, every background is a virtual solid/gradient in {theme}. "
                "Do not change hue between frames."
            )
        elif mode == "real_environment":
            unity = (
                "LISTING VISUAL UNITY — One campaign, one theme color. "
                f"Except the white catalog frame, every background is a real environment graded in {theme}. "
                "Do not change hue or location family between frames."
            )
        else:
            from generation.services.listing_visual_cohesion import _forbidden_drift

            unity = (
                "LISTING VISUAL UNITY — One campaign, one color grade. "
                f"Every frame, including lifestyle and closing frames, stays in {theme}. "
                f"{_forbidden_drift(theme)} "
                "Background type may change. Hue may not."
            )
        chunks.insert(0, unity)
    return " ".join(chunks)


def _angle_placement_priority_block(shot: dict, plan: dict, *, is_white_catalog: bool = False) -> str:
    """P0：机位/摆放 mandate 前置，优先于场景长文案。"""
    chunks: list[str] = []
    pose_div = (plan.get("listing_product_pose_diversity_en") or "").strip()
    if pose_div and not is_white_catalog:
        chunks.append(pose_div)
    pose = (shot.get("product_pose_lock_en") or "").strip()
    if pose:
        chunks.append(pose)
    elif is_white_catalog:
        chunks.append(
            "PRODUCT PHYSICAL POSE — Upright vertical front catalog on white (this index only)."
        )
    orient = (shot.get("orientation_lock") or "").strip()
    if orient:
        chunks.append(f"MANDATORY PRODUCT ORIENTATION — {orient}")
    mandate = (shot.get("composition_mandate") or "").strip()
    if mandate:
        chunks.append(mandate)
    placement = (shot.get("placement_lock") or "").strip()
    if placement:
        chunks.append(placement)
    mode = (shot.get("reference_mode") or plan.get("default_reference_mode") or "").lower()
    if mode == "identity":
        if is_white_catalog:
            chunks.append(
                "REFERENCE USE (WHITE CATALOG) — Lock SKU packaging/label/colors from attachment; "
                "REDRAW the product UPRIGHT vertical front-facing on pure #FFFFFF even if the upload is tilted or lying; "
                "ignore reference product rotation — compliance upright catalog pose ONLY (0° tilt)."
            )
        else:
            chunks.append(
                "REFERENCE USE — Attached image locks SKU packaging, label, colors only; "
                "do NOT copy its camera angle, crop, upright standing pose, or product rotation. "
                "Physical pack pose MUST follow PRODUCT PHYSICAL POSE above (tilt/recline/horizontal/top-down/worm's-eye)."
            )
    elif mode in ("none", "no", "false"):
        chunks.append(
            "NO REFERENCE IMAGE — Execute camera and placement mandates exactly; "
            "product graphics must match identity text below; "
            "same product category as plan anchor — never unrelated objects; unique vs other frames."
        )
    tier = (plan.get("shot_reference_tier_en") or "").strip()
    if tier and mode in ("none", "no", "identity"):
        pass  # tier is plan-level; angle lock below is enough
    if not is_white_catalog:
        angle_lock = (plan.get("listing_angle_diversity_lock_en") or "").strip()
        if angle_lock:
            chunks.append(angle_lock)
    return " ".join(chunks)


def _build_frame2_variant_lineup_prompt(plan: dict) -> str:
    """白底多款：短提示放在最前，避免被 8000 字截断后只剩「居中一个商品」。"""
    count = _listing_variant_count(plan)
    prefix = _core_function_prefix(plan, {"index": 2})
    return (
        f"{prefix} "
        f"WHITE CATALOG. One photograph on pure #FFFFFF. No text, no icons, no people. "
        f"Draw all {count} attached reference products in one horizontal row, left to right, "
        "in the same order as the attached images. "
        "Each item keeps the color and pattern of its own photo. "
        "Do not keep only the first color. Do not recolor the others to match the first. "
        "Front view, even light, soft shadow, every item fully visible, not overlapping. "
        "Not a panel collage. Not a before-and-after. Not a hair photo. "
        "If the references are scarves or clothing, show every color of that item."
    )


# 每个品类只留自己的对比词。第 4 张提示里一旦出现其他品类的词，就整段退回这一张单。
_FRAME4_SIGNATURES: dict[str, tuple[str, ...]] = {
    "hair": ("frizzy", "hair strand"),
    "body_bath": ("body wash", "body skin", "shower gel"),
    "hand_wash": ("hand wash", "germ speck"),
    "home_clean": ("toilet",),
    "body_deo": ("underarm",),
    "nail_fungus": ("nail plate",),
    "oral": ("teeth",),
    "skin_face": ("facial skin",),
    "wearable": ("scarf",),
    "body_hand": ("lotion",),
}


def _frame4_card_text(zone: str, *, spray: bool, exfoliation: bool = False, body_scrub: bool = False) -> str:
    """第 4 张只允许一个对比主体。"""
    if zone == "hair":
        spray_line = " The nozzle points at the hair." if spray else ""
        return (
            "ONE photo of the attached product."
            " COMPARISON SUBJECT: the hair strands."
            " The action smooths the hair and controls frizz."
            " LEFT: frizzy dull hair."
            " RIGHT: the same hair smooth and shiny."
            " UNCHANGED: the package shape."
            f"{spray_line}"
            " No text on image."
        )
    if zone == "body_bath":
        return (
            "ONE photo of the attached product."
            " COMPARISON SUBJECT: body skin in the shower."
            " LEFT: dull body skin."
            " RIGHT: the same skin with cleansing foam."
            " UNCHANGED: the wall, the tiles, the floor, and the bottle shape."
            " No text on image."
        )
    if zone == "hand_wash":
        return (
            "ONE photo of the attached product."
            " COMPARISON SUBJECT: the hands."
            " LEFT: many small germ specks on the hands."
            " RIGHT: the same hands with those specks gone."
            " UNCHANGED: the bottle shape."
            " No text on image."
        )
    if zone == "nail_fungus":
        return (
            "ONE photo of the attached product."
            " COMPARISON SUBJECT: the nail plate."
            " LEFT: a yellowed stained nail."
            " RIGHT: the same nail looking clearer and more cared for."
            " UNCHANGED: the package shape."
            " No text on image."
        )
    if zone == "body_deo":
        return (
            "ONE photo of the attached product."
            " COMPARISON SUBJECT: the underarm."
            " LEFT: the underarm before use."
            " RIGHT: the same underarm after the product is applied."
            " UNCHANGED: the package shape."
            " No text on image."
        )
    if zone == "wearable":
        return (
            "ONE photo of the attached product."
            " COMPARISON SUBJECT: wearing this scarf."
            " LEFT: the outfit without the scarf."
            " RIGHT: the same outfit wearing this scarf."
            " UNCHANGED: the package colors and the person's hair."
            " No text on image."
        )
    if zone == "skin_face":
        if exfoliation:
            return (
                "ONE photo of the attached product."
                " COMPARISON SUBJECT: the face."
                " The action is gentle exfoliation of the facial surface."
                " LEFT: dull facial skin."
                " RIGHT: the same face smoother and more luminous."
                " UNCHANGED: the package shape."
                " No text on image."
            )
        return (
            "ONE photo of the attached product."
            " COMPARISON SUBJECT: facial skin."
            " LEFT: dull facial skin."
            " RIGHT: the same facial skin looking fresher."
            " UNCHANGED: the package shape."
            " No text on image."
        )
    if zone == "oral":
        return (
            "ONE photo of the attached product."
            " COMPARISON SUBJECT: the teeth."
            " LEFT: dull teeth."
            " RIGHT: the same teeth looking cleaner."
            " UNCHANGED: the package shape."
            " No text on image."
        )
    if zone == "body_hand":
        return (
            "ONE photo of the attached product."
            " COMPARISON SUBJECT: skin with this lotion."
            " LEFT: dry skin."
            " RIGHT: the same skin looking softer."
            " UNCHANGED: the package shape."
            " No text on image."
        )
    if zone == "home_clean":
        return (
            "ONE photo of the attached product."
            " COMPARISON SUBJECT: the fixture this cleaner treats."
            " LEFT: that fixture before cleaning."
            " RIGHT: the same fixture after cleaning."
            " UNCHANGED: the bottle shape."
            " No text on image."
        )
    if body_scrub:
        return (
            "ONE photo of the attached product."
            " COMPARISON SUBJECT: body skin."
            " The action is exfoliating the body surface."
            " LEFT: dull body skin."
            " RIGHT: the same body skin smoother."
            " UNCHANGED: the package shape."
            " No text on image."
        )
    return (
        "ONE photo of the attached product."
        " COMPARISON SUBJECT: the result named on the package."
        " LEFT: that result before this product is used."
        " RIGHT: the same subject after this product is used."
        " UNCHANGED: the package shape."
        " No text on image."
    )


def _frame4_prompt_is_single_subject(zone: str, text: str) -> bool:
    low = (text or "").lower()
    for other, signatures in _FRAME4_SIGNATURES.items():
        if other == zone:
            continue
        if any(signature in low for signature in signatures):
            return False
    return True


def _build_frame4_isolated_prompt(shot: dict, plan: dict, *, attach_reference: bool = False) -> str:
    """图4：只有一个对比主体。混入其他品类的词时，退回这张单。"""
    from generation.services.listing_frame4_contract import apply_frame4_comparison_contract

    plan = apply_frame4_comparison_contract(dict(plan))
    contract = plan.get("frame4_comparison_contract") or {}
    zone = (contract.get("zone") or "").strip() or "generic"
    analysis = plan.get("product_analysis") or {}
    blob = " ".join(
        str(analysis.get(k) or "")
        for k in (
            "product_name_en",
            "product_name_es",
            "product_name_zh",
            "label_text_exact",
            "primary_function",
            "upload_name_hint",
            "package_ocr_text",
        )
    )
    low = blob.lower()
    spray = zone == "hair" and any(w in low or w in blob for w in ("spray", "aerosol", "bruma", "mist", "喷雾"))
    from generation.services.product_usage_semantics import is_body_scrub, is_facial_exfoliation

    user = (plan.get("user_prompt") or plan.get("subject_lock") or "")[:800]
    evidence = " ".join(
        [
            blob,
            " ".join(str(x) for x in (analysis.get("spanish_headlines") or [])[:8]),
            " ".join(str(x) for x in (analysis.get("key_selling_points") or [])[:8]),
            user,
        ]
    )
    card = _frame4_card_text(
        zone,
        spray=spray,
        exfoliation=zone == "skin_face" and is_facial_exfoliation(evidence),
        body_scrub=zone == "generic" and is_body_scrub(evidence),
    )
    shape = ""
    if attach_reference:
        shape = (
            " PACKAGE SHAPE LOCK — Copy the reference package outline, cap, label, colors, and proportions."
        )
    clean = f"{_core_function_prefix(plan, shot)} {card}{shape}"
    parts = [card]
    if shape:
        parts.append(shape.strip())
    style_lock = (plan.get("listing_style_lock_en") or "").strip()
    if style_lock:
        parts.append(style_lock)
    design = (plan.get("listing_design_system_en") or "").strip()
    if design:
        parts.append("Same campaign background as the set. No marketing type on this frame.")
    full = f"{_core_function_prefix(plan, shot)} " + " ".join(parts)
    if not _frame4_prompt_is_single_subject(zone, full):
        full = clean
    return _guard_contact_prompt(zone, full, clean)


_FACE_CONTACT_MARKERS = (
    "cheek",
    "forehead",
    "facial skin",
    "face cream",
    "on the face",
    "facial serum",
)
_UNDERARM_CONTACT_MARKERS = ("underarm", "armpit", "axila")


def _guard_contact_prompt(zone: str, text: str, clean: str) -> str:
    low = (text or "").lower()
    if zone == "body_deo" and any(marker in low for marker in _FACE_CONTACT_MARKERS):
        return clean
    if zone == "skin_face" and any(marker in low for marker in _UNDERARM_CONTACT_MARKERS):
        return clean
    return text


def _frame6_contact_prompt(shot: dict, plan: dict) -> str:
    """图6：除臭只写腋下，面部护肤只写脸。精华质地不决定涂抹位置。"""
    from generation.services.product_usage_semantics import reconcile_application_zone

    analysis = dict(plan.get("product_analysis") or {})
    user = (plan.get("user_prompt") or plan.get("subject_lock") or "")[:800]
    zone = reconcile_application_zone(analysis, user)
    headline = (shot.get("headline_es") or "").strip()[:56]
    if zone == "body_deo":
        if not headline or not any(
            w in headline.lower() for w in ("axila", "odor", "fresh", "fresco", "protección", "protection")
        ):
            headline = "Odor protection all day"
        card = (
            "ONE photo of this deodorant on the underarm only. "
            "Raised arm. The product touches the underarm. "
            "No other benefit line."
        )
    elif zone == "generic":
        from generation.services.product_usage_semantics import is_body_scrub

        evidence = " ".join(
            [
                str(analysis.get("label_text_exact") or ""),
                str(analysis.get("product_name_en") or ""),
                str(analysis.get("primary_function") or ""),
                user,
            ]
        )
        headline = ""
        if is_body_scrub(evidence):
            card = (
                "ONE photo. The action is exfoliating body skin. "
                "The product touches body skin. "
                "The result is smoother body skin."
            )
        else:
            card = (
                "ONE photo. Read the words printed on the attached package. "
                "Show that product's own result. "
                "The headline copies one claim printed on the package."
            )
    else:
        from generation.services.product_usage_semantics import is_facial_exfoliation

        evidence = " ".join(
            [
                " ".join(str(analysis.get(k) or "") for k in (
                    "label_text_exact",
                    "product_name_en",
                    "product_name_es",
                    "primary_function",
                )),
                " ".join(str(x) for x in (analysis.get("spanish_headlines") or [])[:8]),
                user,
            ]
        )
        if is_facial_exfoliation(evidence):
            card = (
                "ONE photo. The action is gentle exfoliation on the face. "
                "The product touches facial skin. "
                "The result is smoother, more luminous skin. "
                "No other benefit line."
            )
        else:
            if not headline:
                headline = "Cuidado en el rostro"
            card = (
                "ONE photo of this skincare product on the face. "
                "The product touches facial skin. "
                "No other benefit line."
            )
    shot_for_prefix = dict(shot)
    shot_for_prefix["headline_es"] = headline
    clean = f"{_core_function_prefix(plan, shot_for_prefix)} {card}"
    return _guard_contact_prompt(zone, clean, clean)


def build_shot_generation_prompt(shot: dict, plan: dict, *, attach_reference: bool = False) -> str:
    try:
        _gate_idx = int(shot.get("index") or 0)
    except (TypeError, ValueError):
        _gate_idx = 0
    if (plan.get("plan_template") or "") == "tk_mx_ecommerce_9" and _gate_idx == 4:
        return _build_frame4_isolated_prompt(shot, plan, attach_reference=attach_reference)
    if (plan.get("plan_template") or "") == "tk_mx_ecommerce_9" and _gate_idx == 6:
        from generation.services.product_usage_semantics import reconcile_application_zone

        _zone6 = reconcile_application_zone(
            plan.get("product_analysis") or {},
            (plan.get("user_prompt") or plan.get("subject_lock") or "")[:800],
        )
        if _zone6 in ("body_deo", "skin_face", "generic"):
            return _frame6_contact_prompt(shot, plan)
    if _gate_idx == 2 and _listing_variant_count(plan) > 1:
        return _build_frame2_variant_lineup_prompt(plan)

    parts: list[str] = [_core_function_prefix(plan, shot)]
    style_lock = (plan.get("listing_style_lock_en") or shot.get("set_style_lock_en") or "").strip()
    if style_lock and (plan.get("plan_template") or "") in ("tk_mx_ecommerce_9", "amazon_listing_7"):
        parts.append(style_lock)
    design_lock = (plan.get("listing_design_system_en") or "").strip()
    if design_lock and (plan.get("plan_template") or "") in ("tk_mx_ecommerce_9", "amazon_listing_7"):
        parts.append(design_lock)
    role_supremacy = (shot.get("tk_frame_role_supremacy_en") or shot.get("tk_frame_role_preamble_en") or "").strip()
    if role_supremacy:
        parts.append(role_supremacy)

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

    try:
        _idx_top = int(shot.get("index") or 0)
    except (TypeError, ValueError):
        _idx_top = 0
    tpl_top = (plan.get("plan_template") or "").strip()
    if tpl_top == "tk_mx_ecommerce_9":
        if _idx_top == 4:
            efficacy = (
                (shot.get("frame4_efficacy_anchor_en") or "").strip()
                or (plan.get("listing_product_efficacy_anchor_en") or "").strip()
                or ((plan.get("product_analysis") or {}).get("product_efficacy_anchor_en") or "").strip()
            )
            auth4_top = (
                (shot.get("frame4_authoritative_en") or "").strip()
                or ((plan.get("product_analysis") or {}).get("frame4_authoritative_en") or "").strip()
            )
            if efficacy:
                parts.append(efficacy)
            if auth4_top:
                parts.append(auth4_top)
            parts.append(FRAME4_PRIORITY_GOAL_EN)
            sp = (shot.get("frame4_visual_split_en") or "").strip()
            if sp:
                parts.append(sp)
        elif _idx_top not in (2, 4):
            typo_pri = (shot.get("on_image_text_non_negotiable_en") or "").strip()
            if typo_pri:
                parts.append(typo_pri)

    cohesion_early = _listing_visual_cohesion_early_block(shot, plan)
    try:
        _focus_idx = int(shot.get("index") or 0)
    except (TypeError, ValueError):
        _focus_idx = 0
    _single_focus = (shot.get("frame_single_focus_en") or "").strip()
    _detail_macro = (shot.get("frame3_variant") or "") == "product_detail_macro"
    if _single_focus:
        parts.append(_single_focus)

    if cohesion_early and plan.get("plan_template") != "reference_guided":
        parts.append(cohesion_early)

    try:
        shot_idx_early = int(shot.get("index") or 0)
    except (TypeError, ValueError):
        shot_idx_early = 0
    role_early = (shot.get("role") or "").strip()
    is_white_catalog = role_early == "white_bg_catalog" or shot_idx_early == 2

    parts.append(on_image_text_mandate_for_plan(plan))
    typo = _safe_text(plan.get("on_image_text_density_mandate_en"))
    skip_typo_global = is_white_catalog or shot_idx_early == 4
    if typo and not skip_typo_global:
        parts.append(typo)
    if shot_idx_early == 4 and (plan.get("plan_template") or "") == "tk_mx_ecommerce_9":
        parts.append(
            "TK FRAME 4 OUTPUT TYPE — Fixed: single-photo before→after visual contrast ONLY; "
            "not trust lifestyle, not category compare, not hero headline layout."
        )
    usp_div = _safe_text(plan.get("listing_usp_diversity_lock_en"))
    if usp_div and not is_white_catalog and shot_idx_early not in (2, 4):
        parts.append(usp_div)

    priority_angle = _angle_placement_priority_block(shot, plan, is_white_catalog=is_white_catalog)
    if priority_angle:
        parts.append(priority_angle)

    parts.append(build_sku_anchor_block(plan, shot))

    lineup_prompt = _white_bg_lineup_prompt(shot, plan) if is_white_catalog else ""
    if is_white_catalog:
        parts.append(lineup_prompt or WHITE_BG_SCENE_PROMPT_EN)
        parts.append(
            "FRAME ROLE LOCK — This is index-2 compliance catalog ONLY. "
            "Ignore any other-frame marketing, hero, or comparison instructions."
        )

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
    family = (plan.get("variant_family_lock_en") or "").strip()
    if family and _listing_variant_count(plan) > 1:
        parts.append(family)
    is_showcase = bool(lineup_prompt) or (
        (shot.get("role") or "") == "multi_variant_showcase" and bool(shot.get("use_all_reference_images"))
    )

    if is_showcase and isinstance(variants, list) and len(variants) > 1:
        catalog = (shot.get("multi_variant_catalog_en") or plan.get("variants_catalog_en") or "").strip()
        parts.append(
            "MULTI-VARIANT SHOWCASE — One photograph showing every style of THIS product together. "
            "Single real photo, not a collage grid with panels or contact sheet. "
            "Each unit matches its own reference; do not duplicate one style and do not switch to another product category."
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
        if is_white_catalog:
            parts.append(f"MANDATORY WHITE-CATALOG ORIENTATION — {orient}")
        else:
            parts.append(
                "MANDATORY PRODUCT ORIENTATION (override reference photo pose — rotate product accordingly): "
                f"{orient}"
            )

    roster = plan.get("camera_roster") or {}
    try:
        cur_idx = int(shot.get("index") or 0)
    except (TypeError, ValueError):
        cur_idx = 0
    if roster and cur_idx and not is_white_catalog:
        others = [f"#{i} uses {roster[i]}" for i in sorted(roster.keys()) if i != cur_idx]
        if others:
            parts.append(
                "Angle diversity lock — other frames already use these orientations; "
                f"this frame must differ: {'; '.join(others)}."
            )
    pose_roster = plan.get("listing_product_pose_roster") or {}
    if pose_roster and cur_idx and not is_white_catalog:
        others_pose = [
            f"#{i} pose: {pose_roster[i][:70]}"
            for i in sorted(pose_roster.keys())
            if i != cur_idx and pose_roster.get(i)
        ]
        if others_pose:
            parts.append(
                "Product physical pose roster — do NOT repeat these staging types: "
                + "; ".join(others_pose[:8])
                + "."
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
    if product_action and not is_white_catalog:
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
        if (
            not is_amazon
            and shot_idx == 4
            and (plan.get("plan_template") or "") == "tk_mx_ecommerce_9"
        ):
            parts.append(
                "Frame type: TK INDEX 4 — mandatory before→after use transformation in ONE photo "
                "(visual contrast ONLY — zero overlay marketing text; no antes/después comparison labels)."
            )
            auth4 = (shot.get("frame4_authoritative_en") or "").strip()
            if not auth4:
                auth4 = ((plan.get("product_analysis") or {}).get("frame4_authoritative_en") or "").strip()
            if auth4:
                parts.append(auth4)
            split4 = (shot.get("frame4_visual_split_en") or "").strip()
            if not split4:
                split4 = ((plan.get("product_analysis") or {}).get("frame4_visual_split_en") or "").strip()
            if split4:
                parts.append(split4)
            subj = (shot.get("frame4_subject_lock_en") or "").strip()
            scene4 = (shot.get("frame4_scene_lock_en") or "").strip()
            if subj:
                parts.append(subj)
            if scene4:
                parts.append(scene4)
        elif is_amazon and shot_idx == 4 and (shot.get("frame4_variant") or "") == "scene_immersion":
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
                "Frame type: one in-use moment matching the product; no numbered step chart, no Step 1 / Step 2 text."
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
        elif shot_idx == 6 and tpl_top == "tk_mx_ecommerce_9":
            ben = (shot.get("frame6_benefit_lock_en") or "").strip()
            parts.append(
                "Frame type: TK INDEX 6 — usage benefit: what the user gains after using the product; "
                "model allowed; mandatory Spanish benefit headline on image; NOT frame-4 before/after split."
            )
            if ben:
                parts.append(ben)
        else:
            parts.append(
                "Frame type: usage benefit — payoff after use with mandatory Spanish headline; model allowed."
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
    _minimal_story = _detail_macro or (shot.get("frame3_variant") or "") == "ingredient_composition"
    if pillar and not is_white_catalog and not _minimal_story and shot_idx != 4:
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
    if creative_dir and shot_idx == 4:
        creative_dir = ""
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
    if not plan.get("listing_unified_palette_en"):
        color_mood = (plan.get("listing_color_mood_en") or "").strip()
        if color_mood:
            parts.append(f"Color mood for entire listing set: {color_mood}")

    for plan_cohesion_key in ("creative_camera_innovation_lock_en",):
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

    story_arc = (plan.get("conversion_story_lock_en") or "").strip()
    if story_arc and role in (
        "pain_empathy",
        "trust_quality",
        "ease_objection",
        "value_stack",
        "lifestyle_payoff",
        "hero_hook",
    ) and shot_idx != 4:
        parts.append(story_arc)

    usp_lock = (shot.get("usp_message_lock") or "").strip()
    if (
        usp_lock
        and not _placeholder_on_image(usp_lock)
        and not is_white_catalog
        and shot_idx != 4
        and not _detail_macro
    ):
        parts.append(usp_lock)
    required_txt = (shot.get("on_image_text_required_en") or "").strip()
    if (
        required_txt
        and not _placeholder_on_image(required_txt)
        and shot_idx not in (2, 4)
        and not is_white_catalog
    ):
        parts.append(required_txt)
    layout_hint = (shot.get("on_image_text_layout_en") or "").strip()
    if layout_hint and shot_idx not in (2, 4):
        parts.append(layout_hint)
    exclusive = (shot.get("exclusive_usp_en") or "").strip()
    if exclusive and not is_white_catalog and not _placeholder_on_image(exclusive):
        parts.append(f"Exclusive angle (do not duplicate other frames): {exclusive}")

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
        "hero_sku_mandatory_en",
        "frame4_efficacy_anchor_en",
        "conversion_visual_lock_en",
        "human_cast_mandatory_en",
        "human_cast_encourage_en",
        "product_usage_frame_lock_en",
        "product_usage_zone_en",
        "frame4_subject_lock_en",
        "frame4_scene_lock_en",
        "frame4_visual_split_en",
        "frame4_no_text_lock_en",
        "on_image_text_required_en",
        "on_image_text_non_negotiable_en",
        "frame6_benefit_lock_en",
        "frame4_model_lock_en",
        "tk_frame_role_preamble_en",
        "tk_frame_role_supremacy_en",
    ):
        if shot_idx == 4 and lock_key in (
            "conversion_visual_lock_en",
            "frame4_efficacy_anchor_en",
            "product_usage_frame_lock_en",
            "frame4_visual_split_en",
            "transformation_story_lock",
            "frame4_content_lock",
        ):
            continue
        block = (shot.get(lock_key) or "").strip()
        if block:
            parts.append(block)

    hair_en = (shot.get("human_cast_hair_en") or "").strip()
    body_en = (shot.get("human_cast_body_en") or "").strip()
    if hair_en:
        parts.append(hair_en)
    if body_en:
        parts.append(body_en)

    cast_mode = (shot.get("human_cast_mode") or "").strip().lower()
    mandatory_human = (shot.get("human_cast_mandatory_en") or "").strip()
    must_model = mandatory_human or shot.get("human_cast_mandatory")
    if mandatory_human:
        parts.append(mandatory_human)
    elif cast_mode == "hair" and not hair_en:
        parts.append(
            "HAIR VISIBLE — Show hair transformation in frame (strands/back of head); "
            "not product-only still life without transformation subject."
        )
    elif cast_mode in ("full", "face") or (shot_idx in (4, 7) and must_model):
        parts.append(
            "HUMAN REQUIRED — Include a photorealistic person as specified; "
            "face or upper body visible; product in use; do NOT omit the model."
        )
    elif cast_mode == "hands":
        parts.append(
            "HUMAN PRESENCE — Hands/forearms only; crop above wrists; no full face in frame."
        )
    elif cast_mode in ("hair", "body"):
        pass
    elif cast_mode == "none" and not must_model:
        parts.append(
            "NO HUMAN — This frame must be product-only or environment-only; "
            "no face, no hands, no model silhouette."
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
    tpl_scene = (plan.get("plan_template") or "").strip()
    if is_white_catalog:
        parts.append(_white_bg_lineup_prompt(shot, plan) or WHITE_BG_SCENE_PROMPT_EN)
    elif shot_idx == 4 and tpl_scene == "tk_mx_ecommerce_9":
        scene4 = " ".join(
            x
            for x in (
                shot.get("frame4_efficacy_anchor_en"),
                plan.get("listing_product_efficacy_anchor_en"),
                shot.get("frame4_authoritative_en"),
                (plan.get("product_analysis") or {}).get("frame4_authoritative_en"),
                shot.get("product_usage_frame_lock_en"),
                shot.get("frame4_subject_lock_en"),
                shot.get("frame4_scene_lock_en"),
                shot.get("frame4_model_lock_en"),
            )
            if (x or "").strip()
        )[:2400]
        parts.append(scene4 or FRAME4_PRIORITY_GOAL_EN)
    elif prompt_en:
        parts.append(prompt_en)

    try:
        shot_idx = int(shot.get("index") or 0)
    except (TypeError, ValueError):
        shot_idx = 0
    skip_marketing_text = (
        role == "white_bg_catalog"
        or shot_idx in (2, 4)
        or is_white_catalog
    )

    if not skip_marketing_text:
        headline_es = (shot.get("headline_es") or "").strip()
        subhead_es = (shot.get("subhead_es") or "").strip()
        icon_bullets = shot.get("icon_bullets_es") or []
        if isinstance(icon_bullets, str):
            icon_bullets = [s.strip() for s in icon_bullets.split("|") if s.strip()]
        if headline_es and not _placeholder_on_image(headline_es) and not _generic_selling_line(headline_es):
            parts.append(
                "Designed Spanish title for THIS frame only. Render THIS set's TITLE TREATMENT exactly: "
                "color block when that treatment is named, thin line only when that treatment is named. "
                f"Bold headline: {headline_es}."
            )
        elif headline_es:
            headline_es = ""
        if subhead_es and not _placeholder_on_image(subhead_es) and not _generic_selling_line(subhead_es):
            parts.append(
                "Two-line introduction under the headline, explaining that same benefit: "
                f"{subhead_es}"
            )
        icon_bullets = [
            b for b in icon_bullets
            if not _placeholder_on_image(str(b)) and not _generic_selling_line(str(b))
        ]
        if icon_bullets:
            parts.append(
                "Three proof lines under the introduction, still about that same benefit: "
                + "; ".join(str(b) for b in icon_bullets[:3])
            )
        parts.append(
            "SCENE — fill the rest of the frame edge to edge: foreground, the product, and a background "
            "with several related props. Keep every surface and prop in the set theme color. "
            "No wide empty margin and no tiny corner label. Do not recolor this one image."
        )
        prompt_es = _safe_text(shot.get("prompt_es") or shot.get("key_message_es"))
        if _placeholder_on_image(prompt_es):
            prompt_es = ""
        if prompt_es and not headline_es:
            parts.append(f"On-image marketing text in Spanish (Español México): {prompt_es}")
        elif not headline_es and not prompt_es:
            fallback_es = (shot.get("assigned_primary_message_es") or "").strip()
            if fallback_es and not _placeholder_on_image(fallback_es):
                parts.append(
                    f"MANDATORY render on-image Spanish text (Español México): «{fallback_es}» — "
                    "large, high-contrast, readable at mobile size."
                )
            else:
                parts.append(
                    "ON-IMAGE SPANISH — Read the words printed on THIS product in the reference photo. "
                    "Write one Mexican Spanish headline for the benefit the buyer actually wants, "
                    "a two-line reason under it, and three short proof lines about that same benefit. "
                    "Use only words a shopper would understand. Do not invent a numbered code as the title."
                )
    elif shot_idx == 4:
        no4 = (shot.get("frame4_no_text_lock_en") or "").strip()
        if no4:
            parts.append(no4)

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
