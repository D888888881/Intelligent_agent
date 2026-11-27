"""TK 九图 index 6：使用功效 / 带给用户的好处（非图4前后对比、非图7种草）。"""

from __future__ import annotations

FRAME6_USAGE_BENEFIT_EN = (
    "FRAME 6 — USAGE BENEFIT (TK index 6): Show what the product gives the user in real daily life — "
    "the felt payoff after use (fresh, soft, clean, confident, comfortable — match product_analysis after_use_state). "
    "Model allowed: relatable half-body/3/4 or candid face using or enjoying the product in authentic Mexico context. "
    "MANDATORY large Spanish text panel ON THE IMAGE: headline, two-line introduction, and three proof lines. "
    "NOT frame-4 before/after split lighting; NOT frame-7 TikTok crowd UGC clone; NOT white catalog."
)

FRAME6_NEGATIVE_EXTRA = (
    "frame 4 before after split, antes después layout, pure trust still-life with no benefit text, "
    "no readable Spanish typography"
)

_FRAME6_DEODORANT_EN = (
    "FRAME 6 — DEODORANT USAGE BENEFIT: raised arm, product on the UNDERARM only. "
    "Show fresh protected underarm confidence — NOT facial skincare, NOT cream on cheeks or forehead, "
    "NOT face mist. Spanish headline must speak to underarm freshness (axila), not generic «cuida tu piel» as face care."
)

_FRAME6_DEODORANT_HEADLINES_ES = (
    "Axila fresca todo el día",
    "Protección bajo la axila",
    "Fresco al vestirte",
    "Confianza al salir",
    "Sin marcas en la ropa",
)


def _headline_speaks_underarm_benefit(text: str) -> bool:
    import re

    return bool(
        re.search(
            r"axila|desodorante|antitranspirante|underarm|armpit|sudor|olor|fresco|protección",
            (text or ""),
            re.I,
        )
    )


def _looks_like_face_skincare_headline(text: str) -> bool:
    import re

    t = (text or "").strip().lower()
    if not t:
        return False
    if _headline_speaks_underarm_benefit(t):
        return False
    return bool(
        re.search(
            r"\bpiel\b|rostro|mejilla|facial|serum|crema facial|glowing|hidrat|suaviza|alisa",
            t,
            re.I,
        )
    )


def apply_tk_frame6_benefit(plan: dict) -> dict:
    if (plan.get("plan_template") or "") != "tk_mx_ecommerce_9":
        return plan

    from generation.services.product_usage_semantics import (
        ZONE_PROFILES,
        application_target_en,
        reconcile_application_zone,
    )

    user = (plan.get("user_prompt") or plan.get("subject_lock") or "")[:800]
    analysis = dict(plan.get("product_analysis") or {})
    zone = reconcile_application_zone(analysis, user)
    analysis["application_zone"] = zone
    plan["product_analysis"] = analysis
    profile = ZONE_PROFILES.get(zone, ZONE_PROFILES["generic"])
    after = (analysis.get("after_use_state") or profile.get("after") or "feel the benefit every day")[:120]

    benefit_es = ""
    usps = analysis.get("key_selling_points") or []
    if usps:
        benefit_es = str(usps[0])[:50]
    if zone == "body_deo":
        pool = list(_FRAME6_DEODORANT_HEADLINES_ES)
        spanish = analysis.get("spanish_headlines") or []
        if isinstance(spanish, list):
            for line in spanish:
                s = str(line).strip()
                if s and not _looks_like_face_skincare_headline(s):
                    benefit_es = s[:48]
                    break
        if not benefit_es or _looks_like_face_skincare_headline(benefit_es):
            nonce = hash((analysis.get("label_text_exact") or "", plan.get("listing_variation_nonce") or 0))
            benefit_es = pool[abs(nonce) % len(pool)]
    if not benefit_es:
        benefit_es = "Bienestar diario"

    target = application_target_en(zone, analysis)

    for shot in plan.get("shots") or []:
        try:
            idx = int(shot.get("index") or 0)
        except (TypeError, ValueError):
            continue
        if idx != 6:
            continue
        role = (shot.get("role") or "").strip()
        if role != "trust_quality":
            shot["role"] = "trust_quality"

        shot["marketing_pillar"] = "使用功效"
        shot["consumer_question"] = "用了之后，生活/身体/状态带来什么具体好处？"
        if zone == "body_deo":
            shot["frame6_benefit_lock_en"] = (
                f"{_FRAME6_DEODORANT_EN} {target} Visualize payoff: {after}."
            )
            shot["human_cast_mode"] = "full"
            shot["human_cast_mandatory"] = True
            shot["human_cast_encourage_en"] = (
                "Frame 6 deodorant — torso, raised arm, stick or roll-on on the UNDERARM; "
                "face optional, product never on the face."
            )
        else:
            shot["frame6_benefit_lock_en"] = (
                f"{FRAME6_USAGE_BENEFIT_EN} {target} Visualize payoff: {after}."
            )
            shot["human_cast_mode"] = shot.get("human_cast_mode") or "face"
            shot.setdefault(
                "human_cast_encourage_en",
                "Frame 6 — model may show face or half-body enjoying/using product; product visible.",
            )
        hl = (shot.get("headline_es") or "").strip()
        if zone == "body_deo":
            if not _headline_speaks_underarm_benefit(hl) or _looks_like_face_skincare_headline(hl):
                shot["headline_es"] = benefit_es[:48]
        elif not hl:
            shot["headline_es"] = benefit_es[:48]
        if not (shot.get("assigned_primary_message_es") or "").strip():
            shot["assigned_primary_message_es"] = shot["headline_es"]
        from generation.services.listing_tk_frame_role import MEDIUM_RICH_LAYOUT_EN

        if not (shot.get("subhead_es") or "").strip():
            shot["subhead_es"] = ""
        if not shot.get("icon_bullets_es"):
            shot["icon_bullets_es"] = []
        shot["on_image_text_required_en"] = (
            f"MANDATORY RICH TYPOGRAPHY — Headline «{shot['headline_es']}»; "
            f"Subhead «{shot.get('subhead_es')}»; icons {shot['icon_bullets_es']}. "
            f"{MEDIUM_RICH_LAYOUT_EN}"
        )
        shot["on_image_text_non_negotiable_en"] = shot["on_image_text_required_en"]
        shot["product_usage_frame_lock_en"] = (
            f"{target} FRAME 6 USAGE BENEFIT — {profile['in_use_en']} "
            f"Forbidden: {profile['forbidden_en']}."
        )
        extra = (shot.get("negative_extra") or "").strip()
        if zone == "body_deo":
            shot["negative_extra"] = (
                f"{extra}, face cream on cheeks, facial mist, spraying the face, skincare glow on face"
            ).strip(", ")
        else:
            shot["negative_extra"] = f"{extra}, {FRAME6_NEGATIVE_EXTRA}".strip(", ")

    return plan