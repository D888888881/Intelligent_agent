"""图4 专用：从包装/卖点生成唯一「前后对比契约」，成图只用此契约（极简 prompt）。"""

from __future__ import annotations

from generation.services.product_usage_semantics import (
    FRAME4_MODEL_BY_ZONE,
    FRAME4_MODEL_MANDATE_BASE,
    ZONE_PROFILES,
    build_frame4_authoritative_en,
    normalize_product_usage_analysis,
    zone_requires_model,
)

HAIR_FRAME4_NEG = (
    "facial skincare before after, cheek skin glow, face serum, moisturizer on face, "
    "piel facial, skincare jar, glowing complexion compare, dull skin vs hydrated face"
)


def _contract_from_analysis(analysis: dict) -> dict:
    zone = (analysis.get("application_zone") or "generic").strip()
    profile = ZONE_PROFILES.get(zone, ZONE_PROFILES["generic"])
    needs_model = zone_requires_model(zone)
    subject = (analysis.get("transformation_subject_en") or "").strip()
    if zone == "hair" and not subject:
        subject = "hair strands only — NOT facial skin"
    return {
        "zone": zone,
        "zone_label_en": profile.get("label_en", zone),
        "comparison_subject_en": subject,
        "before_state_en": (analysis.get("before_use_state") or profile["before"]).strip(),
        "after_state_en": (analysis.get("after_use_state") or profile["after"]).strip(),
        "visual_direction_en": (analysis.get("before_after_visual_en") or profile["before_after_visual_en"]).strip(),
        "forbidden_en": profile["forbidden_en"],
        "requires_human_model": needs_model,
        "human_cast_hint_en": (
            "HAIR-ONLY cast: transformation on hair strands; not a facial skincare ad."
            if zone == "hair"
            else (
                "Photorealistic model; transformation on the correct application zone."
                if needs_model
                else "NO human model — object/surface transformation only."
            )
        ),
    }


def render_frame4_contract_prompt(contract: dict) -> str:
    c = contract or {}
    zone = c.get("zone") or ""
    lines = [
        "FRAME 4 — COMPARISON CONTRACT (ONLY instruction for this image).",
        f"Zone: {c.get('zone_label_en')} [{zone}]",
        f"Subject: {c.get('comparison_subject_en')}",
        f"Before → After: «{c.get('before_state_en')}» → «{c.get('after_state_en')}»",
        f"Visual: {c.get('visual_direction_en')}",
        f"Cast: {c.get('human_cast_hint_en')}",
        f"Forbidden: {c.get('forbidden_en')}",
        "Pure visual before/after; ZERO on-image text; hero SKU from reference visible.",
    ]
    if zone == "hair":
        lines.extend(
            [
                "MANDATORY: frizzy/dull HAIR vs smooth/shiny HAIR in ONE photo.",
                "THIS IS NOT SKINCARE — no cheek/face skin texture before-after, no facial serum glow, "
                "no piel radiante on face, no moisturizer demo on skin.",
            ]
        )
    elif zone == "body_bath":
        lines.append("MANDATORY: shower BODY skin + foam; NOT hair strand compare.")
    return " ".join(lines)


def build_frame4_comparison_contract(analysis: dict, user_prompt: str = "") -> dict:
    analysis = normalize_product_usage_analysis(dict(analysis or {}), user_prompt or "")
    return _contract_from_analysis(analysis)


def infer_zone_from_proven_listing_copy(plan: dict) -> str | None:
    """图1/图3 已上屏的西语卖点（用户已验证正确）优先于识图 application_zone。"""
    from generation.services.product_usage_semantics import (
        BODY_WASH_STRONG_KW,
        DEODORANT_KW,
        HAIR_STRONG_KW,
        NOT_BODY_WASH_KW,
        is_facial_exfoliation,
    )

    chunks: list[str] = []
    analysis = plan.get("product_analysis") or {}
    for key in ("spanish_headlines", "key_selling_points", "label_text_exact", "product_name_en"):
        val = analysis.get(key)
        if isinstance(val, list):
            chunks.extend(str(x) for x in val[:8])
        elif val:
            chunks.append(str(val))
    for shot in plan.get("shots") or []:
        try:
            idx = int(shot.get("index") or 0)
        except (TypeError, ValueError):
            continue
        if idx not in (1, 3, 6):
            continue
        for key in ("headline_es", "subhead_es", "prompt_es", "key_message_es"):
            t = (shot.get(key) or "").strip()
            if t:
                chunks.append(t)
        bullets = shot.get("icon_bullets_es") or []
        if isinstance(bullets, list):
            chunks.extend(str(b) for b in bullets[:4])
    blob = " ".join(chunks)
    if DEODORANT_KW.search(blob):
        return "body_deo"
    hair = bool(HAIR_STRONG_KW.search(blob))
    bath = bool(BODY_WASH_STRONG_KW.search(blob)) and not NOT_BODY_WASH_KW.search(blob)
    if hair and not bath:
        return "hair"
    if bath and not hair:
        return "body_bath"
    if hair:
        return "hair"
    if is_facial_exfoliation(blob):
        return "skin_face"
    return None


def apply_frame4_comparison_contract(plan: dict) -> dict:
    from generation.services.listing_bundle import is_listing_ecommerce_plan

    if not is_listing_ecommerce_plan(plan):
        return plan
    if (plan.get("plan_template") or "") != "tk_mx_ecommerce_9":
        return plan

    user = (plan.get("user_prompt") or plan.get("subject_lock") or "")[:800]
    analysis = dict(plan.get("product_analysis") or {})
    proven = infer_zone_from_proven_listing_copy(plan)
    if proven:
        analysis["application_zone"] = proven
    analysis = normalize_product_usage_analysis(analysis, user)
    plan["product_analysis"] = analysis
    contract = _contract_from_analysis(analysis)
    zone = contract["zone"]
    profile = ZONE_PROFILES.get(zone, ZONE_PROFILES["generic"])
    contract["authoritative_en"] = build_frame4_authoritative_en(analysis, profile)

    plan["frame4_comparison_contract"] = contract
    plan["frame4_comparison_contract_en"] = render_frame4_contract_prompt(contract)

    for shot in plan.get("shots") or []:
        if int(shot.get("index") or 0) != 4:
            continue
        shot["frame4_comparison_contract_en"] = plan["frame4_comparison_contract_en"]
        shot["frame4_authoritative_en"] = contract["authoritative_en"][:1600]
        shot["frame4_visual_split_en"] = contract["visual_direction_en"]
        shot["product_usage_frame_lock_en"] = plan["frame4_comparison_contract_en"]
        shot["conversion_visual_lock_en"] = plan["frame4_comparison_contract_en"]
        shot["transformation_story_lock"] = plan["frame4_comparison_contract_en"]
        shot["frame4_no_text_lock_en"] = "INDEX 4 — no overlay text."
        shot.pop("frame4_content_lock", None)
        shot.pop("frame4_efficacy_anchor_en", None)
        shot.pop("prompt_en", None)

        needs = contract["requires_human_model"]
        shot["human_cast_mandatory"] = needs
        if needs and zone == "hair":
            shot["human_cast_mode"] = "hair"
            shot["human_cast_hair_en"] = (
                "HAIR CAST — 3/4 back/side view; before→after ON HAIR STRANDS; "
                "not facial skincare cheeks."
            )
            detail = FRAME4_MODEL_BY_ZONE["hair"]
            shot["human_cast_mandatory_en"] = f"{FRAME4_MODEL_MANDATE_BASE} {detail}"
            shot["frame4_model_lock_en"] = shot["human_cast_mandatory_en"]
        elif needs:
            if zone == "hand_wash":
                shot["human_cast_mode"] = "hands"
            else:
                shot["human_cast_mode"] = "full" if zone in ("body_bath", "body_deo", "nail_fungus") else "face"
            detail = FRAME4_MODEL_BY_ZONE.get(zone, FRAME4_MODEL_BY_ZONE["generic"])
            shot["human_cast_mandatory_en"] = f"{FRAME4_MODEL_MANDATE_BASE} {detail}"
            shot["frame4_model_lock_en"] = shot["human_cast_mandatory_en"]
        else:
            shot["human_cast_mode"] = "none"

        extra = (shot.get("negative_extra") or "").strip()
        if zone == "hair":
            shot["negative_extra"] = f"{extra}, {HAIR_FRAME4_NEG}".strip(", ")
        elif zone == "nail_fungus":
            shot["negative_extra"] = (
                f"{extra}, face cream, facial mist, hair application, cure claim, guaranteed fungus removal"
            ).strip(", ")
        elif zone == "body_deo":
            shot["negative_extra"] = (
                f"{extra}, face cream, cheek application, facial mist, spraying the face"
            ).strip(", ")
        elif zone == "body_bath":
            shot["negative_extra"] = (
                f"{extra}, frizzy hair transformation, hair strand before after"
            ).strip(", ")
        elif zone == "hand_wash":
            shot["negative_extra"] = (
                f"{extra}, stretched bottle, melted pump, redesigned label"
            ).strip(", ")
        if zone == "hair":
            scene4 = "Hair-care bathroom/vanity — transformation subject is hair ONLY. Nozzle never points at the face."
        elif zone == "nail_fungus":
            scene4 = "Hand or foot close-up — product touches the NAIL plate only. Not the face, not the hair."
        elif zone == "hand_wash":
            scene4 = (
                "Sink close-up. Left: germ specks on the hands. Right: those specks are gone. "
                "Bottle outline, pump, cap, and label match the reference on both halves."
            )
        elif zone == "body_deo":
            scene4 = "Bathroom or bedroom — product touches the UNDERARM only, never the face."
        else:
            scene4 = f"Scene for {profile['label_en']} only."
        shot["frame4_scene_lock_en"] = scene4
    return plan