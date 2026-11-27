"""套图创意引擎 MVP：Concept 选择 → 8 维矩阵 → History 避让 → 写入 plan。"""

from __future__ import annotations

from generation.services.creative_engine.cohesion import apply_creative_set_cohesion, build_conversion_story_lock_en
from generation.services.creative_engine.concepts import (
    CREATIVE_CONCEPTS,
    DIMENSION_KEYS,
    ZONE_FORBIDDEN_SCENE_SNIPPETS,
    ZONE_PREFERRED_CONCEPT,
    concept_by_id,
)
from generation.services.creative_engine.history import build_creative_history_avoid_en, load_creative_history
from generation.services.visual_batch_variance import is_beauty_skincare_plan


def _category_bucket(plan: dict) -> str:
    analysis = plan.get("product_analysis") or {}
    zone = (analysis.get("application_zone") or "").strip()
    if zone in ("hair", "oral", "skin_face", "body_hand", "body_bath"):
        return "beauty_skincare"
    cs = plan.get("category_strategy") or {}
    bucket = (cs.get("category_bucket") or "").strip()
    if bucket:
        return bucket
    if is_beauty_skincare_plan(plan):
        return "beauty_skincare"
    return "generic"


def _application_zone(plan: dict) -> str:
    return (plan.get("product_analysis") or {}).get("application_zone") or "generic"


def _score_concept(
    concept: dict,
    *,
    category: str,
    zone: str,
    success_ids: set[str],
    success_styles: set[str],
    attempt_ids: set[str],
) -> int:
    score = 100
    cid = concept["id"]
    style = (concept.get("dimensions") or {}).get("visual_style") or ""
    if cid in success_ids:
        return -1
    if cid in attempt_ids:
        score -= 45
    if style and style in success_styles:
        score -= 40
    aff = concept.get("category_affinity") or ()
    if category and category in aff:
        score += 25
    elif "generic" in aff:
        score += 5
    preferred = ZONE_PREFERRED_CONCEPT.get(zone) or []
    if cid in preferred:
        score += 35 - preferred.index(cid) * 5
    env = ((concept.get("dimensions") or {}).get("scene_environment") or "").lower()
    for bad in ZONE_FORBIDDEN_SCENE_SNIPPETS.get(zone, ()):
        if bad in env:
            score -= 50
    return score


def pick_creative_concept(
    plan: dict,
    *,
    batch_index: int,
    history: list[dict],
) -> dict:
    success_ids = {
        str(h.get("concept_id") or "")
        for h in history
        if h.get("concept_id") and h.get("record_type") == "success"
    }
    attempt_ids = {
        str(h.get("concept_id") or "")
        for h in history
        if h.get("concept_id") and h.get("record_type") == "attempt"
    }
    success_styles: set[str] = set()
    for h in history:
        if h.get("record_type") != "success":
            continue
        dims = h.get("dimensions") or {}
        if dims.get("visual_style"):
            success_styles.add(dims["visual_style"])
        elif h.get("visual_style"):
            success_styles.add(h["visual_style"])

    category = _category_bucket(plan)
    zone = _application_zone(plan)
    ranked: list[tuple[int, dict]] = []
    for c in CREATIVE_CONCEPTS:
        sc = _score_concept(
            c,
            category=category,
            zone=zone,
            success_ids=success_ids,
            success_styles=success_styles,
            attempt_ids=attempt_ids,
        )
        if sc >= 0:
            ranked.append((sc, c))

    if not ranked:
        ranked = [(0, CREATIVE_CONCEPTS[batch_index % len(CREATIVE_CONCEPTS)])]
    else:
        ranked.sort(key=lambda x: (-x[0], x[1]["id"]))
        # 批次轮转：同等分数下用 batch_index 错开首选
        offset = batch_index % min(3, len(ranked))
        ranked = ranked[offset:] + ranked[:offset]

    return ranked[0][1]


def _concept_mandate_en(concept: dict) -> str:
    dims = concept.get("dimensions") or {}
    lines = [
        f"CREATIVE SET LOCK — Concept «{concept.get('label_en')}» ({concept['id']}).",
        concept.get("story_theme_en") or "",
        "Eight-dimension matrix (entire set must obey):",
    ]
    for key in DIMENSION_KEYS:
        val = dims.get(key)
        if val:
            lines.append(f"  • {key}: {val}")
    lines.append(
        "Vary camera angles and staging frame-to-frame; keep color and scene STYLE cohesive across the set. "
        "Do NOT produce frames that only swap background hue with identical centered packshot pose."
    )
    return " ".join(lines)


def _reconcile_concept_with_product_zone(plan: dict, concept: dict) -> dict:
    zone = _application_zone(plan)
    if zone == "generic":
        return concept
    env = ((concept.get("dimensions") or {}).get("scene_environment") or "").lower()
    forbidden = ZONE_FORBIDDEN_SCENE_SNIPPETS.get(zone, ())
    if any(bad in env for bad in forbidden):
        concept = dict(concept)
        dims = dict(concept.get("dimensions") or {})
        alt = concept_by_id("bathroom_wellness")
        if alt and zone in ("hair", "oral", "skin_face", "body_hand"):
            dims.update(alt.get("dimensions") or {})
            concept["dimensions"] = dims
            concept["story_theme_en"] = alt.get("story_theme_en") or concept.get("story_theme_en")
            concept["color_mood_en"] = alt.get("color_mood_en") or concept.get("color_mood_en")
    return concept


def _apply_shot_concept_hints(plan: dict, concept: dict) -> None:
    hero = concept.get("hero_mandate_en") or ""
    for shot in plan.get("shots") or []:
        role = (shot.get("role") or "").strip()
        idx = int(shot.get("index") or 0)
        if role == "hero_hook" and hero:
            shot["creative_concept_hero_lock"] = hero
            prev = (shot.get("hero_visual_impact_lock") or "").strip()
            shot["hero_visual_impact_lock"] = f"{prev} {hero}".strip() if prev else hero
        if role == "white_bg_catalog":
            shot.setdefault(
                "set_cohesion_lock_en",
                "White catalog: compliant flat white; shadow tint and edge light must match the set color system.",
            )
            continue
        cohesion = (
            "Per-frame background TYPE may change (solid, studio, interior, outdoor, fictional) "
            "within the locked scene family; keep palette cohesive; innovate camera for this SKU."
        )
        shot["set_cohesion_lock_en"] = cohesion
        if idx > 2:
            shot.setdefault(
                "creative_detail_direction_en",
                (concept.get("story_theme_en") or "")[:400],
            )


def apply_creative_engine(plan: dict, *, job) -> dict:
    """在 visual_batch / flex 之前调用。"""
    batch_index = int(plan.get("visual_batch_index") or 0)
    analysis = plan.get("product_analysis") or {}
    history = load_creative_history(job, product_analysis=analysis)

    reuse_id = (
        (plan.get("reuse_creative_concept_id") or "")
        or ((job.plan_json or {}).get("reuse_creative_concept_id") or "")
    ).strip()
    concept = concept_by_id(reuse_id) if reuse_id else None
    if not concept:
        concept = pick_creative_concept(plan, batch_index=batch_index, history=history)
    concept = _reconcile_concept_with_product_zone(plan, concept)

    plan["creative_concept_id"] = concept["id"]
    plan["creative_concept_label_zh"] = concept["label_zh"]
    plan["creative_concept_label_en"] = concept["label_en"]
    plan["creative_dimension_matrix"] = dict(concept.get("dimensions") or {})
    plan["creative_concept_pack_name"] = concept.get("generic_pack_name") or ""
    plan["listing_story_theme_en"] = (concept.get("story_theme_en") or "").strip()
    plan["listing_color_mood_en"] = (concept.get("color_mood_en") or "").strip()
    plan["creative_concept_mandate_en"] = _concept_mandate_en(concept)
    plan = apply_creative_set_cohesion(plan, concept)
    avoid = build_creative_history_avoid_en(history)
    plan["creative_history_avoid_en"] = avoid
    if avoid:
        prev = (plan.get("previous_batch_avoidance_en") or "").strip()
        plan["previous_batch_avoidance_en"] = f"{prev} {avoid}".strip() if prev else avoid

    if plan.get("listing_story_theme_en"):
        plan["conversion_story_lock_en"] = build_conversion_story_lock_en(plan)

    plan["creative_history"] = history
    _apply_shot_concept_hints(plan, concept)
    return plan


def finalize_creative_set_record(plan: dict) -> dict:
    """生图策划完成后写入 creative_set，供下一批 History 读取。"""
    concept = concept_by_id(plan.get("creative_concept_id") or "")
    plan["creative_set"] = {
        "concept_id": plan.get("creative_concept_id"),
        "label_zh": plan.get("creative_concept_label_zh"),
        "label_en": plan.get("creative_concept_label_en") or (concept or {}).get("label_en"),
        "dimensions": plan.get("creative_dimension_matrix") or {},
        "pack_name": plan.get("visual_batch_pack_name") or "",
        "batch_index": plan.get("visual_batch_index"),
        "frame_variants": {
            "frame3": plan.get("frame3_variant_id"),
            "frame4": plan.get("frame4_variant_id"),
            "frame5": plan.get("frame5_variant_id"),
            "frame9": plan.get("frame9_variant_id"),
        },
    }
    return plan
