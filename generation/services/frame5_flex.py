"""图 5 灵活职能：按批次在品类对比 / 规格功能 / 步骤 / 套装 / 核心功能间轮换。"""

from __future__ import annotations

from generation.services.ecommerce_strategy import _fallback_category_compare

FRAME_5_VARIANTS: list[dict] = [
    {
        "id": "category_compare",
        "label_zh": "品类对比",
        "action_code": "frame5_vs_generic",
        "density": "balanced",
        "human": "none",
        "archetype": "same_category_product_comparison",
        "scene_family": "side_by_side_vs_generic",
        "mandate_en": (
            "FRAME 5 — Category comparison: our branded hero SKU vs plain unbranded SAME product category only "
            "(e.g. another plain toothpaste tube if hero is toothpaste — NEVER unrelated kitchen gadgets or electronics) "
            "in ONE photograph, side-by-side on shared surface and lighting; our product looks premium, "
            "generic looks dull; highlight visual advantages; NO real competitor logos or trademarks; "
            "NOT a multi-panel collage."
        ),
    },
    {
        "id": "specs_features",
        "label_zh": "规格与属性",
        "action_code": "frame5_specs_features",
        "density": "balanced",
        "human": "none",
        "archetype": "specs_callout_single_photo",
        "scene_family": "infographic_product_hero",
        "mandate_en": (
            "FRAME 5 — Specs & attributes: ONE clean 1:1 photo showing size, capacity, color variants, "
            "or key dimensions with minimal Spanish callout labels (short es-MX words, mobile legible); "
            "hero SKU visible; NOT a white catalog clone of index 2; NOT dense text wall."
        ),
    },
    {
        "id": "kit_contents",
        "label_zh": "套装内容",
        "action_code": "frame5_kit_contents",
        "density": "rich",
        "human": "none",
        "archetype": "whats_in_the_box",
        "scene_family": "kit_layout_angled",
        "mandate_en": (
            "FRAME 5 — Kit contents: display package_includes items in one angled or shelf layout; "
            "quantity and gift pieces readable; warm premium styling; differs from index 8 value narrative "
            "(this frame lists WHAT is included, not only price/value)."
        ),
    },
    {
        "id": "usage_steps",
        "label_zh": "使用步骤",
        "action_code": "frame5_usage_steps",
        "density": "balanced",
        "human": "none",
        "archetype": "simple_steps_sequence",
        "scene_family": "step_flow_single_image",
        "mandate_en": (
            "FRAME 5 — In use: one real use moment that fills the frame (cropped hands OK, no face). "
            "Do not draw a numbered step chart. Add this frame's large Spanish text panel. "
            "NOT duplicate frame 7 TikTok portrait."
        ),
    },
    {
        "id": "core_functions",
        "label_zh": "核心功能",
        "action_code": "frame5_core_functions",
        "density": "balanced",
        "human": "none",
        "archetype": "function_highlights",
        "scene_family": "feature_callout_hero",
        "mandate_en": (
            "FRAME 5 — Core functions: one hero product in a filled scene, plus this frame's large "
            "Spanish text panel explaining the one benefit; not the same layout as index 1 hero."
        ),
    },
    {
        "id": "ingredient_composition",
        "label_zh": "成分展示",
        "action_code": "frame5_ingredient_only",
        "density": "balanced",
        "human": "none",
        "archetype": "ingredient_full_bleed",
        "scene_family": "ingredient_still_life",
        "mandate_en": (
            "FRAME 5 — Ingredient composition ONLY: entire frame filled with actives and textures; "
            "NO product bottle, NO packaging, NO SKU; minimal on-image tags per marketplace language."
        ),
    },
]

VARIANT_BY_ID = {v["id"]: v for v in FRAME_5_VARIANTS}


def _active_frame5_variants(plan: dict) -> list[dict]:
    from generation.services.ingredient_frame_policy import listing_has_ingredient_story

    if listing_has_ingredient_story(plan):
        return FRAME_5_VARIANTS
    return [v for v in FRAME_5_VARIANTS if v["id"] != "ingredient_composition"]


def resolve_frame5_variant_index(plan: dict, *, job=None) -> int:
    batch = int(plan.get("visual_batch_index") or 0)
    if job:
        try:
            from generation.services.visual_batch_variance import resolve_visual_batch_index

            batch = resolve_visual_batch_index(job, product_analysis=plan.get("product_analysis"))
        except Exception:
            pass
    variants = _active_frame5_variants(plan)
    return (batch + 2) % max(1, len(variants))


def _text_list(val) -> list[str]:
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    if isinstance(val, str) and val.strip():
        return [val.strip()]
    return []


def _build_variant_context(variant_id: str, analysis: dict, usp_fallback: str) -> str:
    if variant_id == "category_compare":
        return _fallback_category_compare(analysis, usp_fallback)

    usps = _text_list(analysis.get("key_selling_points"))
    usp_txt = "; ".join(usps[:5]) if usps else usp_fallback
    colors = _text_list(analysis.get("primary_colors"))
    includes = _text_list(analysis.get("package_includes"))
    scenarios = _text_list(analysis.get("usage_scenarios"))

    if variant_id == "specs_features":
        color_txt = ", ".join(colors[:4]) if colors else "visible product colors from label"
        return (
            f"Show tangible specs: capacity/size feel, {color_txt}, dimensions cues; "
            f"supporting USPs: {usp_txt}."
        )
    if variant_id == "kit_contents":
        kit = "; ".join(includes[:8]) if includes else "all items visible on packaging"
        return f"Kit must show: {kit}."
    if variant_id == "usage_steps":
        return (
            "Show one real in-use action that matches this product. "
            "Do not print Step 1, Step 2, Paso 1, or a numbered tutorial. "
            "The only on-image words are this frame's selling line."
        )
    if variant_id == "core_functions":
        return f"Visualize core functions: {usp_txt}."
    if variant_id == "ingredient_composition":
        ings = _text_list(analysis.get("key_ingredients")) or _text_list(analysis.get("ingredients"))
        if ings:
            return (
                "Full-frame ingredient still-life only — highlight: "
                + "; ".join(ings[:6])
                + ". NO product bottle in frame."
            )
        return "Full-frame ingredient still-life only; NO product bottle in frame."
    return ""


def apply_frame5_flex_variant(plan: dict, *, job=None) -> dict:
    from generation.services.listing_bundle import is_listing_ecommerce_plan

    if not is_listing_ecommerce_plan(plan):
        return plan

    shots = plan.get("shots") or []
    shot5 = None
    for shot in shots:
        if int(shot.get("index") or 0) == 5:
            shot5 = shot
            break
    if not shot5 or (shot5.get("role") or "") != "usp_secondary":
        return plan

    variants = _active_frame5_variants(plan)
    vi = resolve_frame5_variant_index(plan, job=job)
    variant = variants[vi]
    vid = variant["id"]

    plan["frame5_variant_index"] = vi
    plan["frame5_variant_id"] = vid
    plan["frame5_variant_label_zh"] = variant["label_zh"]

    shot5["frame5_variant"] = vid
    shot5["layout_subtype"] = vid
    shot5["frame_contract"] = "flex_variant"
    shot5["action_code"] = variant["action_code"]
    shot5["human_cast_mode"] = "none"
    shot5["visual_archetype"] = variant["archetype"]
    shot5["scene_family"] = variant["scene_family"]
    shot5["content_density"] = variant.get("density", "balanced")

    mandate = variant["mandate_en"]
    existing = (shot5.get("composition_mandate") or "").strip()
    shot5["composition_mandate"] = f"{existing} {mandate}".strip() if existing else mandate

    batch_name = plan.get("visual_batch_pack_name") or "default"
    shot5["action_lock"] = (
        f"FRAME 5 FLEX — variant '{vid}' ({variant['label_zh']}), batch '{batch_name}'. "
        f"{variant['mandate_en']}"
    )

    analysis = plan.get("product_analysis") or {}
    usps = _text_list(analysis.get("key_selling_points"))
    usp_fallback = usps[1] if len(usps) > 1 else (usps[0] if usps else "quality")
    ctx = _build_variant_context(vid, analysis, usp_fallback)
    if ctx:
        shot5["frame5_content_lock"] = f"FRAME 5 CONTENT — {ctx}"

    if vid == "ingredient_composition":
        shot5["primary_action_id"] = "B07"
        shot5["ingredient_composition_only"] = True

    if vid != "category_compare":
        pe = shot5.get("prompt_en") or ""
        if "Comparison context:" in pe:
            shot5["prompt_en"] = pe.split(" Comparison context:")[0].strip()

    density = variant.get("density", "balanced")
    if density == "rich":
        shot5["composition_density_lock"] = (
            "COMPOSITION DENSITY — Rich: multiple props/SKU units allowed."
        )
    elif density == "minimal":
        shot5["composition_density_lock"] = (
            "COMPOSITION DENSITY — Fill the frame with the product, the setting, and this frame's text panel."
        )
    else:
        shot5["composition_density_lock"] = (
            "COMPOSITION DENSITY — Balanced hero plus context."
        )

    pillar_map = {
        "category_compare": ("次要卖点", "比同类型普通产品好在哪里？"),
        "specs_features": ("规格参数", "尺寸、容量、颜色我看得到吗？"),
        "kit_contents": ("套装清单", "盒子里具体有什么？"),
        "usage_steps": ("使用步骤", "怎么用、几步搞定？"),
        "core_functions": ("核心功能", "最核心的功能是什么？"),
        "ingredient_composition": ("核心成分", "成分是否天然、整图展示成分细节？"),
    }
    pillar, question = pillar_map.get(vid, ("图5职能", ""))
    shot5.setdefault("marketing_pillar", pillar)
    if not (shot5.get("consumer_question") or "").strip():
        shot5["consumer_question"] = question

    d_lock = (
        f"Frame 5 variant '{vid}' — rotates per listing batch; must differ from index 2 white catalog "
        "and index 8 value stack layout."
    )
    shot5["diversity_lock"] = d_lock

    plan["frame5_flex_summary_en"] = (
        f"Listing frame 5 uses variant '{vid}' ({variant['label_zh']}) for this batch; "
        "other batches may rotate to category compare, specs, kit, steps, or core functions."
    )
    plan["shots"] = shots
    return plan
