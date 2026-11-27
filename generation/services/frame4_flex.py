"""图 4 痛点对比：固定「使用前→使用后」纯视觉单图，画面禁止对比文字。"""



from __future__ import annotations



FRAME_4_NO_COMPARE_TEXT = (

    "FORBIDDEN ON IMAGE — Any comparison typography: no 'before', 'after', 'antes', 'después', "

    "no 使用前, 使用后, 对比, no arrows with words, no split labels, no Spanish comparison captions. "

    "Tell the story purely through lighting, color, product state, composition, and subject contrast."

)



FRAME_4_VARIANT_ID = "before_after_visual"

FRAME_4_LABEL_ZH = "使用前→使用后（纯视觉）"

FRAME_4_AMAZON_SCENE_VARIANT = {
    "id": "scene_immersion",
    "label_zh": "场景代入",
}



def _frame4_mandate_en(analysis: dict, *, needs_model: bool) -> str:
    zone = (analysis.get("application_zone") or "generic").strip()
    subject = (analysis.get("transformation_subject_en") or analysis.get("application_zone_en") or zone).strip()
    model_line = (
        "Include a photorealistic person showing the transformation on the correct application zone."
        if needs_model
        else "NO human model — transform the object/surface the product cleans or treats."
    )
    return (
        "FRAME 4 — Pain-point before/after in ONE photograph (not collage grid). "
        f"Comparison subject for THIS SKU: {subject}. "
        f"{model_line} "
        "Obey frame4_authoritative_en / product_usage_frame_lock on this shot — derived from vision product analysis, "
        "NOT generic skincare if the product is hair care. "
        "THE SAME hero SKU from reference must be visible. "
        "Transformation subject must dominate the frame. "
        "NO generic-vs-hero product comparison (frame 5). "
        + FRAME_4_NO_COMPARE_TEXT
    )


# 兼容 Amazon / 导出脚本
FRAME_4_VISUAL_SPLIT_EN = (
    "REQUIRED BEFORE/AFTER — Show transformation on the application zone from product vision analysis "
    "(hair strands, shower skin, smile, surface cleaned, etc.) — NOT a wrong body part."
)
FRAME_4_MANDATE_EN = (
    "FRAME 4 — before/after visual contrast; obey product_analysis frame4_authoritative_en for this SKU."
)


# 兼容预览文案查找

VARIANT_BY_ID = {
    FRAME_4_VARIANT_ID: {
        "id": FRAME_4_VARIANT_ID,
        "label_zh": FRAME_4_LABEL_ZH,
    },
    FRAME_4_AMAZON_SCENE_VARIANT["id"]: FRAME_4_AMAZON_SCENE_VARIANT,
}





def _text_list(val) -> list[str]:

    if isinstance(val, list):

        return [str(x).strip() for x in val if str(x).strip()]

    if isinstance(val, str) and val.strip():

        return [val.strip()]

    return []





def apply_frame4_flex_variant(plan: dict, *, job=None) -> dict:

    from generation.services.listing_bundle import is_listing_ecommerce_plan

    if not is_listing_ecommerce_plan(plan):

        return plan



    shots = plan.get("shots") or []

    shot4 = None

    for shot in shots:

        if int(shot.get("index") or 0) == 4:

            shot4 = shot

            break

    if not shot4:
        return plan
    tpl = (plan.get("plan_template") or "").strip()
    if tpl == "tk_mx_ecommerce_9":
        shot4["role"] = "usp_primary"
    role4 = (shot4.get("role") or "").strip()
    if role4 != "usp_primary":
        return plan



    plan["frame4_variant_index"] = 0

    plan["frame4_variant_id"] = FRAME_4_VARIANT_ID

    plan["frame4_variant_label_zh"] = FRAME_4_LABEL_ZH



    shot4["frame4_variant"] = FRAME_4_VARIANT_ID

    shot4["layout_subtype"] = FRAME_4_VARIANT_ID

    shot4["frame_contract"] = "flex_variant"

    shot4["action_code"] = "frame4_before_after_visual"

    from generation.services.product_usage_semantics import apply_product_usage_locks

    apply_product_usage_locks(plan)
    analysis = plan.get("product_analysis") or {}
    zone = (analysis.get("application_zone") or "").strip()
    from generation.services.product_usage_semantics import zone_requires_model

    needs_model = zone_requires_model(zone)
    mandate = _frame4_mandate_en(analysis, needs_model=needs_model)
    shot4["human_cast_mandatory"] = needs_model
    if needs_model and not (shot4.get("human_cast_mandatory_en") or "").strip():
        shot4["human_cast_mode"] = "full" if zone == "body_bath" else "face"
        from generation.services.product_usage_semantics import (
            FRAME4_MODEL_BY_ZONE,
            FRAME4_MODEL_MANDATE_BASE,
        )

        z = zone or "generic"
        shot4["human_cast_mandatory_en"] = (
            f"{FRAME4_MODEL_MANDATE_BASE} {FRAME4_MODEL_BY_ZONE.get(z, FRAME4_MODEL_BY_ZONE['generic'])}"
        )
    elif not needs_model:
        shot4["human_cast_mode"] = "none"

    shot4["visual_archetype"] = "pain_before_after_single_photo"

    shot4["scene_family"] = "transformation_visual_only"

    auth = (analysis.get("frame4_authoritative_en") or shot4.get("frame4_authoritative_en") or "").strip()
    split_hint = (shot4.get("frame4_visual_split_en") or analysis.get("frame4_visual_split_en") or "").strip()
    shot4["frame_single_focus_en"] = f"{auth or split_hint} {FRAME_4_NO_COMPARE_TEXT}".strip()

    existing = (shot4.get("composition_mandate") or "").strip()
    shot4["composition_mandate"] = f"{existing} {mandate}".strip() if existing else mandate

    batch_name = plan.get("visual_batch_pack_name") or "default"
    shot4["action_lock"] = (
        f"FRAME 4 — before/after visual only ({FRAME_4_LABEL_ZH}), batch '{batch_name}'. {mandate}"
    )



    usps = _text_list(analysis.get("key_selling_points"))

    usp_fallback = usps[0] if usps else "core benefit"

    usage_lock = (shot4.get("product_usage_frame_lock_en") or "").strip()
    if not usage_lock:
        from generation.services.product_usage_semantics import apply_product_usage_locks

        apply_product_usage_locks(plan)
        usage_lock = (shot4.get("product_usage_frame_lock_en") or "").strip()

    split_en = (shot4.get("frame4_visual_split_en") or analysis.get("frame4_visual_split_en") or "").strip()
    if split_en:
        shot4["frame4_visual_split_en"] = split_en

    anchor = (
        analysis.get("product_efficacy_anchor_en") or shot4.get("frame4_efficacy_anchor_en") or ""
    ).strip()
    auth_line = (analysis.get("frame4_authoritative_en") or shot4.get("frame4_authoritative_en") or "").strip()
    if anchor or auth_line:
        shot4["frame_single_focus_en"] = f"{anchor} {auth_line} {FRAME_4_NO_COMPARE_TEXT}".strip()
    elif split_en:
        shot4["frame_single_focus_en"] = f"{split_en} {FRAME_4_NO_COMPARE_TEXT}"

    shot4.pop("frame4_content_lock", None)

    if tpl == "tk_mx_ecommerce_9":
        shot4["prompt_en"] = (
            f"{anchor} {auth_line} {mandate} {usage_lock}".strip()[:2200]
        )

    shot4["transformation_story_lock"] = (
        f"{anchor} {auth_line} {FRAME_4_NO_COMPARE_TEXT}".strip()
        or (
            "PAIN TRANSFORMATION BEAT — Single-frame before→after visual contrast for core USP; "
            + FRAME_4_NO_COMPARE_TEXT
        )
    )



    shot4["composition_density_lock"] = (

        "COMPOSITION DENSITY — Balanced: clear pain/transformation read at mobile thumbnail."

    )



    shot4.setdefault("marketing_pillar", "核心卖点")

    if not (shot4.get("consumer_question") or "").strip():

        shot4["consumer_question"] = "用了以后改善有多明显？（纯画面，无对比字）"



    shot4["diversity_lock"] = (

        "Frame 4 — before/after visual only; zero comparison captions; "

        "camera and product rotation must differ from frames 1/2/5."

    )



    neg_extra = (shot4.get("negative_extra") or "").strip()

    shot4["negative_extra"] = (

        f"{neg_extra}, antes después text, before after labels, 使用前 使用后, comparison arrows with words, "

        "split-screen text banners, generic product beside hero SKU, competitor comparison layout, "
        "plain trust lifestyle only, frame 6 duplicate bathroom scene, no visible before after contrast, "
        "single packshot only, no split lighting, no transformation subject, benefit headline layout like frame 6"
    ).strip(", ")
    shot4["frame4_output_contract_en"] = (
        "OUTPUT CONTRACT — Index 4 must show visible before/after on application zone in ONE photo; "
        "otherwise reject and regenerate mentally toward split contrast."
    )



    plan["frame4_flex_summary_en"] = (

        f"Frame 4 is fixed to before/after visual ({FRAME_4_LABEL_ZH}); "

        "never render before/after wording; never generic-vs-hero product compare on this frame."

    )

    plan["shots"] = shots

    return plan

