"""Amazon 7 图专用 flex：固定规格/盒内，图4 痛点对比↔场景代入，图5 承接九图 frame3 细节轮换。"""

from __future__ import annotations

from generation.services.frame3_flex import apply_frame3_flex_variant
from generation.services.ecommerce_strategy import _fallback_before_after
from generation.services.frame4_flex import (
    FRAME_4_AMAZON_SCENE_VARIANT,
    FRAME_4_MANDATE_EN,
    FRAME_4_NO_COMPARE_TEXT,
)
from generation.services.frame5_flex import FRAME_5_VARIANTS


def _text_list(val) -> list[str]:
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    if isinstance(val, str) and val.strip():
        return [val.strip()]
    return []


def _shot_at_index(plan: dict, index: int) -> dict | None:
    for shot in plan.get("shots") or []:
        if int(shot.get("index") or 0) == index:
            return shot
    return None


def _last_frame4_amazon_variant(job, product_analysis) -> str | None:
    if not job:
        return None
    try:
        from generation.models import GenerationJob
        from generation.services.job_references import product_fingerprint
    except Exception:
        return None

    fp = product_fingerprint(job, product_analysis=product_analysis)
    prev = (
        GenerationJob.objects.filter(user_id=job.user_id, status=GenerationJob.Status.SUCCEEDED)
        .exclude(pk=job.pk)
        .order_by("-finished_at")[:40]
    )
    for j in prev:
        if product_fingerprint(j, product_analysis=product_analysis) != fp:
            continue
        pj = j.plan_json or {}
        if (pj.get("plan_template") or "") != "amazon_listing_7":
            continue
        vid = pj.get("frame4_variant_id")
        if vid:
            return str(vid)
        s4 = _shot_at_index(pj, 4)
        if s4:
            return (s4.get("frame4_variant") or s4.get("layout_subtype") or "") or None
    return None


def resolve_frame4_amazon_variant_id(plan: dict, *, job=None) -> str:
    """图 4：使用前→使用后（纯视觉）与真实生活场景代入轮流。"""
    batch = int(plan.get("visual_batch_index") or 0)
    if job:
        try:
            from generation.services.visual_batch_variance import resolve_visual_batch_index

            batch = resolve_visual_batch_index(job, product_analysis=plan.get("product_analysis"))
        except Exception:
            pass
    last = _last_frame4_amazon_variant(job, plan.get("product_analysis")) if job else None
    if last == "before_after_visual":
        return "scene_immersion"
    if last == "scene_immersion":
        return "before_after_visual"
    return "before_after_visual" if batch % 2 == 0 else "scene_immersion"


def _scene_geo_lock(plan: dict) -> str:
    geo = (plan.get("scene_geo_en") or plan.get("scene_geo_adj_en") or "local marketplace").strip()
    adj = (plan.get("scene_geo_adj_en") or geo).strip()
    return (
        f"FRAME 4 — Real-life usage scene: hero SKU in an authentic {adj} daily environment "
        f"({geo} home, bathroom, kitchen, bedroom, office, or outdoor context as fits category). "
        "Natural light, believable props, product readable; builds purchase代入感. "
        "NOT clinical white macro; NOT before/after split; no dominant full face."
    )


def apply_amazon_specs_frame(plan: dict) -> dict:
    shot = _shot_at_index(plan, 3)
    if not shot or (shot.get("role") or "") != "usp_secondary":
        return plan
    variant = next((v for v in FRAME_5_VARIANTS if v["id"] == "specs_features"), None)
    if not variant:
        return plan

    vid = "specs_features"
    plan["frame5_variant_index"] = 0
    plan["frame5_variant_id"] = vid
    plan["frame5_variant_label_zh"] = variant["label_zh"]

    shot["frame5_variant"] = vid
    shot["layout_subtype"] = vid
    shot["frame_contract"] = "flex_variant"
    shot["action_code"] = variant["action_code"]
    shot["human_cast_mode"] = "none"
    shot["visual_archetype"] = variant["archetype"]
    shot["scene_family"] = variant["scene_family"]
    mandate = variant["mandate_en"].replace("FRAME 5", "AMAZON FRAME 3")
    existing = (shot.get("composition_mandate") or "").strip()
    shot["composition_mandate"] = f"{existing} {mandate}".strip() if existing else mandate
    shot["frame5_content_lock"] = (
        "FRAME 3 (Amazon) — Specs & dimensions with minimal on-image labels per marketplace language."
    )
    shot.setdefault("marketing_pillar", "规格参数")
    shot["consumer_question"] = "尺寸、容量、颜色等规格是否清晰？"
    shot["diversity_lock"] = (
        "Amazon frame 3 — fixed specs callouts; differs from frame 1 white and frame 2 value hero."
    )
    plan["frame5_flex_summary_en"] = (
        "Amazon frame 3 is fixed to specs & attributes (size, capacity, color, dimensions)."
    )
    plan["shots"] = plan.get("shots") or []
    return plan


def apply_amazon_kit_frame(plan: dict) -> dict:
    shot = _shot_at_index(plan, 7)
    if not shot or (shot.get("role") or "") != "value_stack":
        return plan
    variant = next((v for v in FRAME_5_VARIANTS if v["id"] == "kit_contents"), None)
    if not variant:
        return plan

    vid = "kit_contents"
    shot["frame5_variant"] = vid
    shot["layout_subtype"] = vid
    shot["action_code"] = variant["action_code"]
    shot["human_cast_mode"] = "none"
    shot["visual_archetype"] = variant["archetype"]
    shot["scene_family"] = variant["scene_family"]
    mandate = variant["mandate_en"].replace("FRAME 5", "AMAZON FRAME 7")
    existing = (shot.get("composition_mandate") or "").strip()
    shot["composition_mandate"] = f"{existing} {mandate}".strip() if existing else mandate
    analysis = plan.get("product_analysis") or {}
    includes = _text_list(analysis.get("package_includes"))
    if includes:
        shot["frame7_content_lock"] = (
            "KIT CONTENTS — Include: " + "; ".join(includes[:8])
        )
    shot.setdefault("marketing_pillar", "包装配件")
    shot["consumer_question"] = "盒子里有什么、配件是否齐全？"
    shot["diversity_lock"] = "Amazon frame 7 — what's-in-the-box layout; lists all included items."
    plan["amazon_kit_summary_en"] = "Amazon frame 7 is fixed to kit / package contents display."
    plan["shots"] = plan.get("shots") or []
    return plan


def apply_amazon_feature_demo_frame(plan: dict) -> dict:
    shot = _shot_at_index(plan, 6)
    if not shot or (shot.get("role") or "") != "ease_objection":
        return plan
    lang = (plan.get("on_image_language") or "English").strip()
    lock = (
        "AMAZON FRAME 6 — Feature demonstration: show the product actively proving its core function "
        "(pour, spray, apply, open, assemble, power-on, output visible) in ONE photograph. "
        "Hands or cropped user allowed; clear cause→effect read at mobile size. "
        f"Short {lang} callouts (2–5 words) optional. NOT idle packshot; NOT TikTok portrait crowd scene."
    )
    existing = (shot.get("composition_mandate") or "").strip()
    shot["composition_mandate"] = f"{existing} {lock}".strip() if existing else lock
    shot["feature_demo_lock_en"] = lock
    shot.setdefault("human_cast_mode", "hands")
    shot.setdefault("marketing_pillar", "功能演示")
    shot["consumer_question"] = "功能/效果能否被直观看到？"
    plan["amazon_feature_demo_summary_en"] = "Amazon frame 6 demonstrates product function in active use."
    plan["shots"] = plan.get("shots") or []
    return plan


def _apply_frame4_before_after(shot4: dict, plan: dict) -> None:
    from generation.services.frame4_flex import FRAME_4_LABEL_ZH, FRAME_4_VARIANT_ID

    shot4["role"] = "usp_primary"
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
    analysis = plan.get("product_analysis") or {}
    usps = _text_list(analysis.get("key_selling_points"))
    usp_fallback = usps[0] if usps else "core benefit"
    ctx = _fallback_before_after(analysis, usp_fallback)
    if ctx:
        shot4["frame4_content_lock"] = f"FRAME 4 CONTENT — {ctx}"
    shot4["transformation_story_lock"] = (
        "PAIN TRANSFORMATION BEAT — Single-frame before→after visual contrast; "
        + FRAME_4_NO_COMPARE_TEXT
    )
    plan["frame4_variant_id"] = FRAME_4_VARIANT_ID
    plan["frame4_variant_label_zh"] = FRAME_4_LABEL_ZH
    plan["frame4_flex_summary_en"] = (
        f"Amazon frame 4 — before/after visual ({FRAME_4_LABEL_ZH}); no comparison typography."
    )


def _apply_frame4_scene(shot4: dict, plan: dict) -> None:
    vid = FRAME_4_AMAZON_SCENE_VARIANT["id"]
    shot4["role"] = "trust_quality"
    shot4["frame4_variant"] = vid
    shot4["layout_subtype"] = vid
    shot4["frame_contract"] = "creative_detail"
    shot4["action_code"] = "amazon_frame4_scene_immersion"
    shot4.setdefault("human_cast_mode", "none")
    shot4["visual_archetype"] = "real_life_trust_context"
    shot4["scene_family"] = "marketplace_daily_environment"
    lock = _scene_geo_lock(plan)
    existing = (shot4.get("composition_mandate") or "").strip()
    shot4["composition_mandate"] = f"{existing} {lock}".strip() if existing else lock
    shot4["story_beat_lock"] = (
        "SCENE IMMERSION BEAT — Authentic usage context; product naturally placed; NO before/after layout."
    )
    plan["frame4_variant_id"] = vid
    plan["frame4_variant_label_zh"] = FRAME_4_AMAZON_SCENE_VARIANT["label_zh"]
    plan["frame4_flex_summary_en"] = (
        "Amazon frame 4 — real-life scene immersion for purchase代入; not before/after this batch."
    )


def apply_amazon_frame4_dual_variant(plan: dict, *, job=None) -> dict:
    from generation.services.listing_bundle import is_listing_ecommerce_plan

    if not is_listing_ecommerce_plan(plan) or (plan.get("plan_template") or "") != "amazon_listing_7":
        return plan

    shot4 = _shot_at_index(plan, 4)
    if not shot4:
        return plan

    vid = resolve_frame4_amazon_variant_id(plan, job=job)
    if job:
        plan["frame4_rotation_reason"] = (
            "alternate_from_previous" if _last_frame4_amazon_variant(job, plan.get("product_analysis")) else "batch_parity"
        )

    if vid == "before_after_visual":
        _apply_frame4_before_after(shot4, plan)
    else:
        _apply_frame4_scene(shot4, plan)

    shot4["diversity_lock"] = (
        f"Amazon frame 4 variant '{vid}' — must differ from frames 1–3 and 5–7."
    )
    plan["shots"] = plan.get("shots") or []
    return plan


def apply_amazon_listing_flex(plan: dict, *, job=None) -> dict:
    """在 TK 九图 flex 分支之外调用。"""
    from generation.services.visual_batch_variance import apply_visual_batch_variance

    plan = apply_visual_batch_variance(plan, job=job)
    plan = apply_amazon_specs_frame(plan)
    plan = apply_amazon_frame4_dual_variant(plan, job=job)
    plan = apply_frame3_flex_variant(plan, job=job, shot_index=5, marketing_index=5)
    plan = apply_amazon_feature_demo_frame(plan)
    plan = apply_amazon_kit_frame(plan)
    return plan