"""图 9 强转化收尾：轮换购买氛围（日常/送礼/家庭/值得购买/卖点总结），非单纯产品主体复刻。"""

from __future__ import annotations

FRAME_9_VARIANTS: list[dict] = [
    {
        "id": "daily_essential",
        "label_zh": "日常必备",
        "layout_subtype": "conversion_close",
        "action_code": "frame9_daily_essential",
        "mandate_en": (
            "FRAME 9 — CONVERSION CLOSE «daily essential»: show the product belongs in everyday Mexico life "
            "(morning counter, commute bag, desk, gym locker, kitchen shelf). "
            "Mood: reliable routine, always within reach — NOT a sterile packshot, NOT duplicate frame 1 hero layout. "
            "Product visible in a lived-in daily context that fills the frame, plus a large Spanish text panel."
        ),
        "cta_es_pool": ["Tu rutina diaria", "Imprescindible", "Cada día", "Uso diario fácil"],
        "scene_family": "daily_routine_payoff",
    },
    {
        "id": "gift_worthy",
        "label_zh": "送礼佳品",
        "layout_subtype": "conversion_close",
        "action_code": "frame9_gift_moment",
        "mandate_en": (
            "FRAME 9 — CONVERSION CLOSE «gift-worthy»: gifting atmosphere — ribbon, tissue, gift bag, "
            "hands exchanging or presenting box (cropped hands OK), warm premium light. "
            "Communicates 'perfect regalo' without covering SKU identity. "
            "NOT solo floating product on gradient; NOT same as frame 8 kit inventory layout."
        ),
        "cta_es_pool": ["Regalo perfecto", "Para regalar", "Detalle especial", "Ideal para regalar"],
        "scene_family": "gift_presentation_close",
    },
    {
        "id": "family_must_have",
        "label_zh": "家庭必备",
        "layout_subtype": "conversion_close",
        "action_code": "frame9_family_home",
        "mandate_en": (
            "FRAME 9 — CONVERSION CLOSE «family must-have»: shared home moment — dining table, sofa tray, "
            "kids' room shelf, or family bathroom hook; multiple subtle props implying household use. "
            "Warm domestic Mexico home; product ready for whole family; faces optional cropped/absent. "
            "NOT isolated product macro; NOT duplicate frame 6 trust still."
        ),
        "cta_es_pool": ["Para toda la familia", "En casa", "Hogar completo", "Familia feliz"],
        "scene_family": "household_essential_close",
    },
    {
        "id": "smart_buy",
        "label_zh": "值得购买",
        "layout_subtype": "conversion_close",
        "action_code": "frame9_smart_purchase",
        "mandate_en": (
            "FRAME 9 — CONVERSION CLOSE «worth buying»: confident purchase decision mood — "
            "tidy checkout moment, shopping tote beside product, price-value confidence (no fake price tags), "
            "premium but honest styling. Feels like 'good decision' not desperation discount. "
            "Product hero ~40% frame but scene tells 'vale la pena'."
        ),
        "cta_es_pool": ["Vale la pena", "Compra inteligente", "Mejor inversión", "Decisión fácil"],
        "scene_family": "purchase_confidence_close",
    },
    {
        "id": "benefit_summary",
        "label_zh": "卖点总结强转化",
        "layout_subtype": "benefit_summary",
        "action_code": "frame9_benefit_summary",
        "mandate_en": (
            "FRAME 9 — CONVERSION CLOSE «benefit summary»: filled closing scene plus a large Spanish text panel "
            "that explains THIS frame's one benefit (headline, two-line introduction, three proof lines). "
            "Product visible. NOT nine-grid collage; NOT repeating frame 1 headline verbatim."
        ),
        "cta_es_pool": ["Compra ya", "Pide el tuyo", "No te lo pierdas", "Listo para ti"],
        "scene_family": "benefit_summary_close",
    },
    {
        "id": "lifestyle_aspiration",
        "label_zh": "愿景生活收尾",
        "layout_subtype": "conversion_close",
        "action_code": "frame9_aspiration_payoff",
        "mandate_en": (
            "FRAME 9 — CONVERSION CLOSE «lifestyle aspiration»: post-use emotional payoff in Mexico context "
            "(balcony sunset, café terrace, park bench, open road) — buyer imagines life AFTER owning SKU. "
            "Product and setting both fill the frame; light and color stay in the set grade, not golden hour. "
            "Add this frame's large Spanish text panel. "
            "NOT duplicate frame 3 pain still; NOT frame 7 TikTok portrait pose."
        ),
        "cta_es_pool": ["Tu mejor versión", "Vive mejor", "Momento perfecto", "Empieza hoy"],
        "scene_family": "aspiration_payoff_close",
    },
]

VARIANT_BY_ID = {v["id"]: v for v in FRAME_9_VARIANTS}


def resolve_frame9_variant_index(plan: dict, *, job=None) -> int:
    batch = int(plan.get("visual_batch_index") or 0)
    if job:
        try:
            from generation.services.visual_batch_variance import resolve_visual_batch_index

            batch = resolve_visual_batch_index(job, product_analysis=plan.get("product_analysis"))
        except Exception:
            pass
    return (batch + 4) % len(FRAME_9_VARIANTS)


def _text_list(val) -> list[str]:
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    if isinstance(val, str) and val.strip():
        return [val.strip()]
    return []


def _unused_usp_bullets(plan: dict, analysis: dict) -> list[str]:
    roster = plan.get("listing_message_roster_es") or {}
    used = {str(v).lower()[:32] for v in roster.values() if v}
    pool: list[str] = []
    for key in ("key_selling_points", "spanish_callouts", "purchase_motivations"):
        pool.extend(_text_list(analysis.get(key)))
    out: list[str] = []
    for s in pool:
        if s.lower()[:32] not in used:
            out.append(s[:40])
        if len(out) >= 4:
            break
    return out or ["Cierre claro", "Motivo real", "Eleccion concreta"]


def apply_frame9_conversion_variant(plan: dict, *, job=None) -> dict:
    from generation.services.listing_bundle import is_listing_ecommerce_plan, listing_payoff_shot_index

    if not is_listing_ecommerce_plan(plan):
        return plan

    payoff_idx = listing_payoff_shot_index(plan)
    shots = plan.get("shots") or []
    shot9 = None
    for shot in shots:
        if int(shot.get("index") or 0) == payoff_idx:
            shot9 = shot
            break
    if not shot9 or (shot9.get("role") or "") != "lifestyle_payoff":
        return plan

    vi = resolve_frame9_variant_index(plan, job=job)
    variant = FRAME_9_VARIANTS[vi]
    vid = variant["id"]

    plan["frame9_variant_index"] = vi
    plan["frame9_variant_id"] = vid
    plan["frame9_variant_label_zh"] = variant["label_zh"]

    shot9["frame9_variant"] = vid
    shot9["layout_subtype"] = variant.get("layout_subtype", "conversion_close")
    shot9["frame_contract"] = "creative_detail"
    shot9["action_code"] = variant["action_code"]
    shot9["visual_archetype"] = f"conversion_close_{vid}"
    shot9["scene_family"] = variant["scene_family"]
    shot9.setdefault("human_cast_mode", "none")

    mandate = variant["mandate_en"]
    existing = (shot9.get("composition_mandate") or "").strip()
    shot9["composition_mandate"] = f"{existing} {mandate}".strip() if existing else mandate

    batch_name = plan.get("visual_batch_pack_name") or "default"
    shot9["action_lock"] = (
        f"FRAME 9 CONVERSION — variant '{vid}' ({variant['label_zh']}), batch '{batch_name}'. "
        f"{mandate} Product must be readable but scene/mood drives purchase intent."
    )

    analysis = plan.get("product_analysis") or {}
    after = (analysis.get("after_use_state") or "").strip()[:200]
    cta_pool = variant["cta_es_pool"]
    cta = cta_pool[vi % len(cta_pool)]

    if vid == "benefit_summary":
        bullets = _unused_usp_bullets(plan, analysis)
        shot9["frame9_content_lock"] = (
            "FRAME 9 CONTENT — Closing benefit summary bullets (Spanish, unique vs frames 1–8): "
            + " | ".join(bullets[:4])
            + (f". After-use mood: {after}" if after else "")
        )
        shot9["icon_bullets_es"] = bullets[:4]
    else:
        shot9["frame9_content_lock"] = (
            f"FRAME 9 CONTENT — Conversion atmosphere «{vid}»; CTA tone: {cta}. "
            + (f"Post-use aspiration: {after}" if after else "Emphasize purchase-ready mood, not catalog clone.")
        )

    shot9["conversion_story_lock"] = (
        f"CONVERSION CLOSE — Create '{variant['label_zh']}' purchase atmosphere; "
        "worth buying / daily / gift / family essential angles; do NOT default to lone product packshot."
    )

    if not (shot9.get("key_message_es") or "").strip():
        shot9["key_message_es"] = cta
    shot9["conversion_cta_es"] = cta

    shot9.setdefault("marketing_pillar", "强转化收尾")
    if not (shot9.get("consumer_question") or "").strip():
        shot9["consumer_question"] = (
            "值得买吗？适合日常/送礼/家人吗？（营造购买氛围，而非再一次纯产品特写）"
        )

    shot9["diversity_lock"] = (
        f"Frame 9 '{vid}' — conversion mood scene; differs from frame 1 hero and frame 7 social proof; "
        "embed product in purchase/lifestyle narrative."
    )

    neg = (shot9.get("negative_extra") or "").strip()
    shot9["negative_extra"] = (
        f"{neg}, lone packshot on empty gradient, duplicate frame 1 hero layout, "
        "product only floating with no purchase context, sterile white catalog repeat"
    ).strip(", ")

    plan["frame9_flex_summary_en"] = (
        f"Frame 9 closes with '{vid}' ({variant['label_zh']}) — purchase atmosphere first, "
        "product support second; rotate variants across listing batches."
    )
    plan["shots"] = shots
    return plan
