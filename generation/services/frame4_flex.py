"""图 4 痛点对比：固定「使用前→使用后」纯视觉单图，画面禁止对比文字。"""



from __future__ import annotations



from generation.services.ecommerce_strategy import _fallback_before_after



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



FRAME_4_MANDATE_EN = (

    "FRAME 4 — Pain-point before/after in ONE photograph (not collage grid): "

    "clear visual contrast between problem state and improved outcome; hero SKU prominent. "

    "Use split lighting, color grade, skin/texture/product state, or left-right visual weight — "

    "NO portrait faces as default. NO generic-vs-hero product comparison (that belongs on frame 5 when rotated). "

    + FRAME_4_NO_COMPARE_TEXT

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

    if not shot4 or (shot4.get("role") or "") != "usp_primary":

        return plan



    plan["frame4_variant_index"] = 0

    plan["frame4_variant_id"] = FRAME_4_VARIANT_ID

    plan["frame4_variant_label_zh"] = FRAME_4_LABEL_ZH



    shot4["frame4_variant"] = FRAME_4_VARIANT_ID

    shot4["layout_subtype"] = FRAME_4_VARIANT_ID

    shot4["frame_contract"] = "flex_variant"

    shot4["action_code"] = "frame4_before_after_visual"

    shot4.setdefault("human_cast_mode", "none")

    shot4["visual_archetype"] = "pain_before_after_single_photo"

    shot4["scene_family"] = "transformation_visual_only"



    existing = (shot4.get("composition_mandate") or "").strip()

    shot4["composition_mandate"] = (

        f"{existing} {FRAME_4_MANDATE_EN}".strip() if existing else FRAME_4_MANDATE_EN

    )



    batch_name = plan.get("visual_batch_pack_name") or "default"

    shot4["action_lock"] = (

        f"FRAME 4 — before/after visual only ({FRAME_4_LABEL_ZH}), batch '{batch_name}'. "

        f"{FRAME_4_MANDATE_EN}"

    )



    analysis = plan.get("product_analysis") or {}

    usps = _text_list(analysis.get("key_selling_points"))

    usp_fallback = usps[0] if usps else "core benefit"

    ctx = _fallback_before_after(analysis, usp_fallback)

    if ctx:

        shot4["frame4_content_lock"] = f"FRAME 4 CONTENT — {ctx}"



    shot4["transformation_story_lock"] = (

        "PAIN TRANSFORMATION BEAT — Single-frame before→after visual contrast for core USP; "

        "NOT generic-product vs our-SKU layout; "

        "ONE short Spanish benefit line (2–4 words) allowed if NOT antes/después/before/after wording. "

        + FRAME_4_NO_COMPARE_TEXT

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

        "split-screen text banners, generic product beside hero SKU, competitor comparison layout"

    ).strip(", ")



    plan["frame4_flex_summary_en"] = (

        f"Frame 4 is fixed to before/after visual ({FRAME_4_LABEL_ZH}); "

        "never render before/after wording; never generic-vs-hero product compare on this frame."

    )

    plan["shots"] = shots

    return plan

