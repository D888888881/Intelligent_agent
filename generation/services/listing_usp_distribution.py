"""九图卖点互不重复 + 适量西语卖点文案（突出重点，非纯视觉）。"""

from __future__ import annotations

# 每镜允许的图上文案密度
TEXT_DENSITY_BY_INDEX: dict[int, str] = {
    1: "rich",  # 双行标题 + 3 icon，视觉冲击优先
    2: "none",  # 纯白底：无任何营销文案
    3: "light",
    4: "light",
    5: "medium",
    6: "light",
    7: "light",
    8: "medium",
    9: "medium",
}

TYPOGRAPHY_MANDATE_EN = (
    "ON-IMAGE TYPOGRAPHY — Index 1: bold Spanish headline + icons BUT visual scroll-stop impact is primary. "
    "Index 2: ZERO added marketing text (white catalog — packaging label from product only). "
    "Frames 3–9: short Spanish (México) selling messages (2–6 words focal lines). "
    "No Chinese except exact packaging from reference. No English marketing. "
    "No paragraph walls — mobile TikTok legibility."
)

USP_DIVERSITY_LOCK_EN = (
    "USP DIVERSITY — All 9 frames carry DIFFERENT primary selling angles. "
    "Never repeat the same benefit headline, icon bullet, or callout wording across frames."
)


def _text_list(val) -> list[str]:
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    if isinstance(val, str) and val.strip():
        return [val.strip()]
    return []


def _locale_default_pool(locale: str) -> list[str]:
    loc = (locale or "es-MX").lower()
    if loc.startswith("pt"):
        return [
            "Qualidade premium",
            "Fácil de usar",
            "Resultado visível",
            "Para o dia a dia",
            "Vale a pena",
        ]
    if loc.startswith("de"):
        return [
            "Premium-Qualität",
            "Einfach zu nutzen",
            "Sichtbares Ergebnis",
            "Für jeden Tag",
            "Lohnt sich",
        ]
    if loc.startswith("en"):
        return [
            "Premium quality",
            "Easy to use",
            "Visible results",
            "Everyday essential",
            "Worth it",
        ]
    return [
        "Calidad premium",
        "Fácil de usar",
        "Resultado visible",
        "Para tu día",
        "Vale la pena",
    ]


def _marketing_text_pool(plan: dict, analysis: dict, usps_cn: list[str]) -> list[str]:
    locale = (plan.get("locale") or analysis.get("locale") or "es-MX").lower()
    keys = ["spanish_headlines", "spanish_callouts", "key_selling_points_es"]
    if locale.startswith("pt"):
        keys = [
            "portuguese_headlines",
            "portuguese_callouts",
            "key_selling_points_pt",
            *keys,
        ]
    elif locale.startswith("en"):
        keys = ["english_headlines", "english_callouts", "key_selling_points_en", *keys]
    elif locale.startswith("de"):
        keys = ["german_headlines", "german_callouts", "key_selling_points_de", *keys]
    pool: list[str] = []
    for key in keys:
        pool.extend(_text_list(analysis.get(key)))
    for u in usps_cn:
        if u and u not in pool:
            pool.append(u[:48])
    if not pool:
        pool = _locale_default_pool(locale)
    return pool


def _benefit_from_pains(pains: list[str]) -> list[str]:
    out: list[str] = []
    for p in pains[:4]:
        p = p[:60]
        out.append(f"Sin {p}" if len(p) < 20 else f"Resuelve: {p}")
    return out


_FRAME9_TEXT_HINTS: dict[str, str] = {
    "daily_essential": "Spanish CTA + daily-life props; product embedded in routine scene.",
    "gift_worthy": "Spanish gift CTA + ribbon/bag/hands presenting.",
    "family_must_have": "Spanish family CTA + shared home staging.",
    "smart_buy": "Spanish worth-buying CTA + confident purchase mood.",
    "benefit_summary": "3–4 unique Spanish advantage bullets + visible product; closing slide.",
    "lifestyle_aspiration": "Spanish aspiration CTA + scenic environment payoff.",
}


def _pick_unique(pool: list[str], used: set[str], idx: int, fallback: str) -> str:
    for i in range(len(pool)):
        candidate = pool[(idx + i) % len(pool)]
        key = candidate.lower()[:32]
        if key not in used:
            used.add(key)
            return candidate
    used.add(fallback.lower()[:32])
    return fallback


def _message_for_frame(
    index: int,
    role: str,
    *,
    es_pool: list[str],
    usps_cn: list[str],
    pains: list[str],
    trust: list[str],
    used: set[str],
) -> tuple[str, str, str]:
    """返回 (exclusive_usp_en, primary_message_es, text_layout_hint_en)."""
    fb = es_pool[index % len(es_pool)] if es_pool else "Calidad"

    if index == 1:
        h = _pick_unique(es_pool, used, 0, "Tu mejor opción")
        bullets = []
        for bi in range(3):
            bullets.append(_pick_unique(es_pool, used, bi + 1, f"Beneficio {bi + 1}"))
        en = (
            f"Hero scroll-stopper: {h}; icon bullets: {', '.join(bullets)}. "
            "Visual punch (contrast, depth, lighting, color) dominates thumbnail."
        )
        return (
            en,
            h,
            "MAX visual impact for TikTok feed + two-line Spanish headline + 3 icon bullets; product hero 40–52% frame.",
        )

    if index == 2:
        return (
            "White catalog — no marketing copy",
            "",
            "NO on-image marketing text — product on pure white only; factory packaging print allowed.",
        )

    if role == "pain_empathy":
        v3 = "product_detail_macro"  # caller sets via shot - check shot
        es = _pick_unique(es_pool, used, index, fb)
        en = f"Frame 3 benefit/detail angle: {es}"
        return en, es, "One short Spanish callout (2–5 words) OR minimal label near macro detail."

    if role == "usp_primary":
        es = _pick_unique(es_pool, used, index, "Resultado visible")
        en = f"Transformation benefit (no antes/después words): {es}"
        return (
            en,
            es,
            "ONE bold Spanish benefit line (2–4 words) allowed — NOT before/after comparison labels.",
        )

    if role == "usp_secondary":
        es = _pick_unique(es_pool, used, index + 3, fb)
        en = f"Secondary info frame: {es}"
        return (
            en,
            es,
            "1–3 short Spanish tags or step numbers as required by frame-5 variant; keep scannable.",
        )

    if role == "trust_quality":
        t = trust[0] if trust else _pick_unique(es_pool, used, index, "Confianza real")
        used.add(t.lower()[:32])
        trust_es = t if any(c.isascii() for c in t) else _pick_unique(es_pool, used, index, "Calidad real")
        return (
            f"Trust signal: {trust_es}",
            trust_es[:40],
            "One subtle Spanish trust line (2–5 words) integrated in scene, not a text wall.",
        )

    if role == "ease_objection":
        es = _pick_unique(es_pool, used, index + 2, "Hecho para ti")
        return (
            f"Social proof audience: {es}",
            es,
            "Optional short UGC-style Spanish sticker (2–4 words) e.g. community vibe — subtle.",
        )

    if role == "value_stack":
        es = _pick_unique(es_pool, used, index + 1, "Gran valor")
        return (
            f"Value/kit message: {es}",
            es,
            "Short Spanish qty/value callouts near kit items (2 words each).",
        )

    es = _pick_unique(es_pool, used, index, fb)
    return f"Frame {index} message: {es}", es, "One short Spanish callout (2–5 words)."


def apply_listing_usp_distribution(plan: dict) -> dict:
    from generation.services.listing_bundle import is_listing_ecommerce_plan, listing_image_count

    if not is_listing_ecommerce_plan(plan):
        return plan

    analysis = plan.get("product_analysis") or {}
    usps_cn = _text_list(analysis.get("key_selling_points"))
    pains = _text_list(analysis.get("pain_points"))
    trust = _text_list(analysis.get("trust_signals"))
    es_pool = _marketing_text_pool(plan, analysis, usps_cn)
    es_pool.extend(_benefit_from_pains(pains))
    # 去重保序
    seen: set[str] = set()
    deduped: list[str] = []
    for s in es_pool:
        k = s.lower()[:40]
        if k in seen:
            continue
        seen.add(k)
        deduped.append(s)
    es_pool = deduped

    used_keys: set[str] = set()
    roster_es: dict[int, str] = {}
    roster_en: dict[int, str] = {}

    for shot in plan.get("shots") or []:
        try:
            index = int(shot.get("index") or 0)
        except (TypeError, ValueError):
            continue
        role = (shot.get("role") or "").strip()

        if index == 3 and (shot.get("frame3_variant") or "") == "product_detail_macro":
            role = "pain_empathy_detail"

        if index == 2 or role == "white_bg_catalog":
            shot["on_image_text_density"] = "none"
            shot["assigned_primary_message_es"] = ""
            shot["exclusive_usp_en"] = "Compliance white background — zero overlay text"
            shot["on_image_text_layout_en"] = (
                "No headlines, captions, icons, or callouts — SKU on #FFFFFF seamless only."
            )
            shot["key_message_es"] = ""
            shot["prompt_es"] = ""
            shot["headline_es"] = ""
            shot["subhead_es"] = ""
            shot["icon_bullets_es"] = []
            shot["usp_message_lock"] = (
                "INDEX 2 TEXT LOCK — Do not add any marketing typography; packaging label from product only."
            )
            roster_es[index] = "(sin texto)"
            roster_en[index] = "white_bg_no_text"
            continue

        if role == "lifestyle_payoff":
            v9 = (shot.get("frame9_variant") or "daily_essential").strip()
            cta = (shot.get("conversion_cta_es") or "").strip()
            es = cta if cta else _pick_unique(es_pool, used_keys, index + 4, "Compra ya")
            exclusive_en = (
                f"Frame 9 conversion close «{v9}» — purchase atmosphere, not packshot-only hero"
            )
            hint = _FRAME9_TEXT_HINTS.get(v9, _FRAME9_TEXT_HINTS["daily_essential"])
        elif role == "pain_empathy_detail":
            es = _pick_unique(es_pool, used_keys, index, "Detalle premium")
            exclusive_en = f"Craft/detail story: {es}"
            hint = "One Spanish craft keyword (Material / Calidad / Diseño) near macro."
        else:
            exclusive_en, es, hint = _message_for_frame(
                index,
                role,
                es_pool=es_pool,
                usps_cn=usps_cn,
                pains=pains,
                trust=trust,
                used=used_keys,
            )

        shot["exclusive_usp_en"] = exclusive_en
        shot["assigned_primary_message_es"] = es
        shot["on_image_text_layout_en"] = hint
        shot.setdefault("key_message_es", es)
        if not (shot.get("prompt_es") or "").strip():
            shot["prompt_es"] = es

        density = TEXT_DENSITY_BY_INDEX.get(index, "light")
        shot["on_image_text_density"] = density

        if index == 1:
            from generation.services.tk_mx_listing import HERO_VISUAL_IMPACT_EN

            shot["hero_visual_impact_lock"] = HERO_VISUAL_IMPACT_EN
            shot.setdefault("headline_es", es)
            if not shot.get("subhead_es") and len(es_pool) > 1:
                sub = es_pool[1] if es_pool[1].lower()[:32] not in used_keys else es_pool[0]
                shot["subhead_es"] = sub[:50]
            bullets = shot.get("icon_bullets_es") or []
            if not bullets:
                shot["icon_bullets_es"] = [
                    _pick_unique(es_pool, used_keys, index + i, f"Punto {i}")[:24]
                    for i in range(1, 4)
                ]

        roster_es[index] = es
        roster_en[index] = exclusive_en

        lock = (shot.get("diversity_lock") or "").strip()
        shot["diversity_lock"] = (
            f"{lock} USP exclusivity — this frame owns: '{es}'; "
            "do not repeat other frames' callouts."
        ).strip()

        shot["usp_message_lock"] = (
            f"USP MESSAGE LOCK — Primary Spanish line for this frame only: «{es}». "
            f"{hint} Typography must be readable and dominant vs background."
        )

    plan["listing_message_roster_es"] = roster_es
    plan["listing_message_roster_en"] = roster_en
    n_frames = listing_image_count(plan)
    plan["listing_usp_diversity_lock_en"] = (
        f"USP DIVERSITY — All {n_frames} frames carry DIFFERENT primary selling angles. "
        "Never repeat the same benefit headline, icon bullet, or callout wording across frames."
    )
    plan["on_image_text_density_mandate_en"] = (
        plan.get("listing_typography_mandate_en") or TYPOGRAPHY_MANDATE_EN
    )
    plan["shots"] = plan.get("shots") or []
    return plan
