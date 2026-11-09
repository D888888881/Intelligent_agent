"""将策划 JSON 中的单镜头字段合成为发给 Grsai 的最终 prompt。"""

from generation.services.model_strategy import model_family, reference_prefix_for_model


def _shot_needs_sku_only_reference_guard(shot: dict) -> bool:
    cast_mode = (shot.get("human_cast_mode") or "").strip().lower()
    role = (shot.get("role") or "").strip()
    if cast_mode in ("full", "face") and role in (
        "pain_empathy",
        "lifestyle_payoff",
        "hero_hook",
    ):
        return True
    return cast_mode in ("full", "face", "hands") and bool(shot.get("human_model_lock"))


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

    quality = (plan.get("quality_prefix") or "").strip()
    if quality:
        parts.append(quality)

    identity_lock = (plan.get("identity_lock") or plan.get("product_identity") or plan.get("subject_lock") or "").strip()
    analysis = plan.get("product_analysis") or {}
    label_exact = (analysis.get("label_text_exact") or "").strip()
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

    if identity_lock:
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

    comp = (shot.get("composition_mandate") or "").strip()
    if comp:
        parts.append(comp)
    elif family == "gpt_image":
        parts.append(
            "Composition: product is the clear hero (≥50% visual weight), professional TikTok Shop layout, "
            "strong focal point, balanced typography space, not a duplicate angle of other listing shots."
        )

    role = (shot.get("role") or "").strip()
    if role == "usp_primary":
        parts.append(
            "Frame type: before/after transformation in ONE single photograph (not collage grid); "
            "show clear visual contrast between problem state and improved outcome."
        )
    elif role == "usp_secondary":
        parts.append(
            "Frame type: our SKU vs generic unbranded same-category product side-by-side in one shot; "
            "no competitor trademarks or real rival brand packaging."
        )
    elif role == "pain_empathy":
        parts.append("Frame type: before-use problem state; empathy scene, not a duplicate packshot.")

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

    diversity = (shot.get("diversity_lock") or "").strip()
    if diversity:
        parts.append(f"Uniqueness requirement: {diversity}")

    action_lock = (shot.get("action_lock") or "").strip()
    if action_lock:
        parts.append(action_lock)
    density_lock = (shot.get("composition_density_lock") or "").strip()
    if density_lock:
        parts.append(density_lock)
    contract = (shot.get("frame_contract") or "").strip()
    if contract == "fixed":
        parts.append(
            "FRAME CONTRACT — Fixed TK slot (hero, white background, before/after, or vs generic). "
            "Do not change the marketing role; only execute with unique camera vs other frames."
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
        "usp_primary",
    ):
        parts.append(story_arc)

    for lock_key in (
        "material_story_lock",
        "story_beat_lock",
        "transformation_story_lock",
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

    prompt_es = (shot.get("prompt_es") or "").strip()
    if prompt_es:
        parts.append(f"On-image marketing text in Spanish (Español México): {prompt_es}")

    locale = plan.get("locale")
    if locale:
        parts.append(f"Market: TikTok Shop {locale} e-commerce listing image.")

    negative = (shot.get("negative_extra") or plan.get("negative_prompt") or "").strip()
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
    mode = (shot.get("reference_mode") or plan.get("default_reference_mode") or "identity").lower()
    if mode in ("none", "false", "no", "0"):
        return False
    return mode in ("identity", "scene", "true", "yes", "1")
