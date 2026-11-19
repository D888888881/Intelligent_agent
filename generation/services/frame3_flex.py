"""图 3 灵活职能：批次轮换「卖点解决对比」或「产品细节特写」。"""

from __future__ import annotations

def _text_list(val) -> list[str]:
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    if isinstance(val, str) and val.strip():
        return [val.strip()]
    return []


FRAME_3_VARIANTS: list[dict] = [
    {
        "id": "benefit_solve_visual",
        "label_zh": "卖点·解决问题",
        "action_code": "frame3_benefit_solve",
        "density": "balanced",
        "human": "none",
        "archetype": "benefit_problem_solver",
        "scene_family": "visual_benefit_contrast",
        "mandate_en": (
            "FRAME 3 — Benefit contrast: ONE photograph showing the problem solved — comfort, storage, "
            "space-saving, smooth glide, durability, slimming effect, convenience, etc. (pick 1–2 that fit SKU). "
            "Use before/after metaphor OR side-by-side props WITHOUT text labels (no 使用前/使用后, no antes/después). "
            "Product clearly visible; empathy through scene, not grim clutter; differs from frame 4 pain-compare flex "
            "and frame 6 trust lifestyle scene."
        ),
    },
    {
        "id": "product_detail_macro",
        "label_zh": "产品细节特写",
        "action_code": "frame3_product_detail",
        "density": "minimal",
        "human": "none",
        "archetype": "sku_detail_hero",
        "scene_family": "macro_material_craft",
        "mandate_en": (
            "FRAME 3 — Product detail hero: material, texture, stitching/craft, ports/interfaces, authentic "
            "label/packaging zone, or controlled macro crop on the hero SKU. Sharp commercial clarity; "
            "neutral or soft context; NOT full vanity lifestyle like frame 6; NOT duplicate frame 2 white catalog; "
            "no face."
        ),
    },
    {
        "id": "ingredient_composition",
        "label_zh": "成分展示",
        "action_code": "frame3_ingredient_only",
        "density": "balanced",
        "human": "none",
        "archetype": "ingredient_full_bleed",
        "scene_family": "ingredient_still_life",
        "mandate_en": (
            "FRAME 3 — Ingredient composition ONLY: the full image is raw actives and textures (botanicals, "
            "vitamins, minerals, oils, water) filling the canvas. NO product bottle, NO packaging, NO SKU. "
            "Premium TikTok Shop ingredient story; single photo, not collage."
        ),
    },
]

VARIANT_BY_ID = {v["id"]: v for v in FRAME_3_VARIANTS}

_BENEFIT_KEYWORDS = (
    "comfortable", "comfort", "storage", "space-saving", "compact", "smooth", "durable", "durability",
    "slimming", "convenient", "easy", "收纳", "省空间", "舒适", "顺滑", "耐用", "显瘦", "方便",
)


def _last_frame3_variant_id(job, product_analysis: dict | None) -> str | None:
    """同 SKU 上一套成功任务的图 3 版式，用于强制 AB 交替。"""
    if not job:
        return None
    from generation.models import GenerationJob
    from generation.services.visual_batch_variance import product_fingerprint

    fp = product_fingerprint(job, product_analysis=product_analysis)
    prev = (
        GenerationJob.objects.filter(
            user_id=job.user_id,
            status=GenerationJob.Status.SUCCEEDED,
        )
        .exclude(pk=job.pk)
        .order_by("-finished_at")[:40]
    )
    for j in prev:
        if product_fingerprint(j) != fp:
            continue
        plan = j.plan_json or {}
        vid = plan.get("frame3_variant_id")
        if vid:
            return str(vid)
        detail_idx = 5 if (plan.get("plan_template") or "") == "amazon_listing_7" else 3
        for shot in plan.get("shots") or []:
            if int(shot.get("index") or 0) == detail_idx:
                return (shot.get("frame3_variant") or "") or None
    return None


def resolve_frame3_variant_index(plan: dict, *, job=None) -> int:
    """
    图 3 两版式轮换：
    - 第 1 套默认「卖点·解决问题」(index 0)
    - 同 SKU 连续生图时与上一套成功任务 **强制交替**（避免批次号卡住时永远卡在特写）
  """
    analysis = plan.get("product_analysis") or {}
    batch = int(plan.get("visual_batch_index") or 0)
    if job:
        try:
            from generation.services.visual_batch_variance import resolve_visual_batch_index

            batch = resolve_visual_batch_index(job, product_analysis=analysis)
            plan["visual_batch_index"] = batch
        except Exception:
            pass

    from generation.services.ingredient_frame_policy import listing_has_ingredient_story

    variant_count = len(FRAME_3_VARIANTS) if listing_has_ingredient_story(plan) else 2

    last_vid = _last_frame3_variant_id(job, analysis) if job else None
    if variant_count >= 3:
        order = ("benefit_solve_visual", "product_detail_macro", "ingredient_composition")
        if last_vid in order:
            return (order.index(last_vid) + 1) % variant_count
        return batch % variant_count
    if last_vid == "product_detail_macro":
        return 0
    if last_vid == "benefit_solve_visual":
        return 1
    return batch % variant_count


def _build_benefit_context(analysis: dict, user_prompt: str) -> str:
    pains = _text_list(analysis.get("pain_points"))
    usps = _text_list(analysis.get("key_selling_points"))
    motivations = _text_list(analysis.get("purchase_motivations"))
    picked: list[str] = []
    blob = " ".join(pains + usps + motivations + [user_prompt[:400]]).lower()
    for kw in _BENEFIT_KEYWORDS:
        if kw.lower() in blob and kw not in picked:
            picked.append(kw)
    for u in usps[:4]:
        if u not in picked:
            picked.append(u[:80])
    if not picked:
        picked = ["comfort", "convenience", "quality"]
    return (
        "Visualize benefits solved: "
        + "; ".join(picked[:5])
        + ". Show outcome or contrast props only — no comparison captions on image."
    )


def _build_ingredient_context(analysis: dict) -> str:
    ings = _text_list(analysis.get("key_ingredients")) or _text_list(analysis.get("ingredients"))
    if ings:
        return (
            "Ingredient hero still-life — feature: "
            + "; ".join(ings[:6])
            + ". Full frame ingredients only; zero product packaging in shot."
        )
    return (
        "Ingredient hero still-life — botanical actives, water, vitamins, oils by category; "
        "full frame, no product bottle."
    )


def _build_detail_context(analysis: dict) -> str:
    texture = (
        (analysis.get("material_texture_en") or analysis.get("texture_description") or "")
    ).strip()
    visual = (analysis.get("visual_identity") or "")[:320]
    raw_label = analysis.get("label_text_exact")
    if isinstance(raw_label, (list, tuple)):
        label = " | ".join(str(x) for x in raw_label if x)[:200]
    else:
        label = (raw_label or "")[:200]
    parts = []
    if texture:
        parts.append(f"Material/texture: {texture}")
    if visual:
        parts.append(f"Visual identity: {visual}")
    if label:
        parts.append(f"Label zone fidelity: {label}")
    if not parts:
        parts.append("Show packaging structure, surface finish, seam, cap, weave, or port detail.")
    return "Detail focus — " + " ".join(parts)[:900]


def apply_frame3_flex_variant(
    plan: dict,
    *,
    job=None,
    shot_index: int = 3,
    marketing_index: int | None = None,
) -> dict:
    from generation.services.listing_bundle import is_listing_ecommerce_plan

    if not is_listing_ecommerce_plan(plan):
        return plan

    m_idx = marketing_index if marketing_index is not None else shot_index

    shots = plan.get("shots") or []
    shot3 = None
    for shot in shots:
        if int(shot.get("index") or 0) == shot_index:
            shot3 = shot
            break
    if not shot3 or (shot3.get("role") or "") != "pain_empathy":
        return plan

    vi = resolve_frame3_variant_index(plan, job=job)
    variant = FRAME_3_VARIANTS[vi]
    vid = variant["id"]
    if job:
        plan["frame3_rotation_reason"] = (
            "alternate_from_previous" if _last_frame3_variant_id(job, plan.get("product_analysis")) else "batch_parity"
        )

    plan["frame3_variant_index"] = vi
    plan["frame3_variant_id"] = vid
    plan["frame3_variant_label_zh"] = variant["label_zh"]

    shot3["frame3_variant"] = vid
    shot3["layout_subtype"] = vid
    shot3["frame_contract"] = "creative_detail"
    shot3["action_code"] = variant["action_code"]
    shot3.setdefault("human_cast_mode", "none")
    shot3["visual_archetype"] = variant["archetype"]
    shot3["scene_family"] = variant["scene_family"]
    shot3["content_density"] = variant.get("density", "balanced")

    mandate = variant["mandate_en"]
    existing = (shot3.get("composition_mandate") or "").strip()
    shot3["composition_mandate"] = f"{existing} {mandate}".strip() if existing else mandate

    batch_name = plan.get("visual_batch_pack_name") or "default"
    shot3["action_lock"] = (
        f"FRAME {m_idx} FLEX — variant '{vid}' ({variant['label_zh']}), batch '{batch_name}'. "
        f"{variant['mandate_en']}"
    )

    analysis = plan.get("product_analysis") or {}
    user_prompt = (plan.get("user_prompt") or "")[:800]
    if vid == "benefit_solve_visual":
        ctx = _build_benefit_context(analysis, user_prompt)
        shot3["frame3_content_lock"] = f"FRAME 3 CONTENT — {ctx}"
        shot3["story_beat_lock"] = (
            "BENEFIT SOLVE BEAT — Show comfort/storage/space/smooth/durable/slimming/convenience "
            "visually; no grim pain clutter; no comparison typography."
        )
        cam = (shot3.get("camera_angle_code") or "").lower()
        if "macro" in cam:
            shot3.pop("camera_angle_code", None)
            shot3.pop("orientation_lock", None)
    elif vid == "ingredient_composition":
        ctx = _build_ingredient_context(analysis)
        shot3["frame3_content_lock"] = f"FRAME 3 CONTENT — {ctx}"
        shot3["primary_action_id"] = "B07"
        shot3["story_beat_lock"] = (
            "INGREDIENT BEAT — Entire frame is ingredient still-life; NO product unit in frame."
        )
        shot3["ingredient_composition_only"] = True
    else:
        ctx = _build_detail_context(analysis)
        shot3["frame3_content_lock"] = f"FRAME 3 CONTENT — {ctx}"
        shot3["story_beat_lock"] = (
            "DETAIL BEAT — Macro or near-macro on material, texture, craft, interface, label, or packaging; "
            "SKU accurate; generous clarity at mobile size."
        )

    density = variant.get("density", "balanced")
    if density == "minimal":
        shot3["composition_density_lock"] = (
            "COMPOSITION DENSITY — Minimal: 1–2 elements, generous negative space."
        )
    elif density == "rich":
        shot3["composition_density_lock"] = (
            "COMPOSITION DENSITY — Rich: multiple props allowed."
        )
    else:
        shot3["composition_density_lock"] = (
            "COMPOSITION DENSITY — Balanced hero plus context."
        )

    shot3.setdefault("marketing_pillar", "卖点呈现")
    if not (shot3.get("consumer_question") or "").strip():
        q = (
            "舒适、收纳、省空间等问题解决了吗？"
            if vid == "benefit_solve_visual"
            else "核心成分是什么、是否天然可信？"
            if vid == "ingredient_composition"
            else "材质、做工、细节经得起细看吗？"
        )
        shot3["consumer_question"] = q

    if vid == "benefit_solve_visual":
        shot3["diversity_lock"] = (
            f"Frame 3 '{vid}' — benefit-solve lifestyle scene; NOT macro product detail; "
            "unique vs frames 2 white catalog and frame 6 trust room."
        )
        neg_macro = "macro-only product crop, texture extreme close-up, label macro duplicate"
        shot3["negative_extra"] = f"{shot3.get('negative_extra') or ''}, {neg_macro}".strip(", ")
    elif vid == "ingredient_composition":
        shot3["diversity_lock"] = (
            f"Frame 3 '{vid}' — full-bleed ingredients; NO product bottle; unique vs frames 1–2 packshots."
        )
        shot3["negative_extra"] = (
            f"{shot3.get('negative_extra') or ''}, product bottle, packaging, SKU packshot"
        ).strip(", ")
    else:
        shot3["diversity_lock"] = (
            f"Frame 3 '{vid}' — craft/detail macro; unique vs frames 2,4,6."
        )

    neg_extra = (shot3.get("negative_extra") or "").strip()
    shot3["negative_extra"] = (
        f"{neg_extra}, grim hoarder clutter as old pain frame, duplicate frame 6 lifestyle room, "
        "duplicate frame 2 white seamless, antes después labels"
    ).strip(", ")

    summaries = {
        "benefit_solve_visual": "benefit-solve contrast",
        "product_detail_macro": "product detail macro",
        "ingredient_composition": "full-frame ingredients only (no SKU)",
    }
    plan["frame3_flex_summary_en"] = (
        f"Frame {m_idx} uses '{vid}' ({variant['label_zh']}) this batch — {summaries.get(vid, vid)}."
    )
    plan["shots"] = shots
    return plan
