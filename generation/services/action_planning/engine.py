"""L3.5 动作规划：冻结 role，只写 primary_action_id / product_action_lock_en。"""

from __future__ import annotations

from generation.services.action_planning.catalog import (
    ACTION_CATALOG_VERSION,
    BEAUTY_POOL_IDS,
    GENERIC_ACTION_IDS,
    action_by_id,
    display_label_zh,
)
from generation.services.action_planning.role_allow import allowed_action_ids_for_shot
from generation.services.beauty_personal_care import plan_uses_beauty_action_pool


SKIP_TEMPLATES = frozenset({"reference_guided", "photo_refine"})


def _category_is_beauty(plan: dict) -> bool:
    cs = plan.get("category_strategy") or {}
    bucket = (cs.get("category_bucket") or "").strip()
    if bucket == "beauty_skincare":
        return True
    return plan_uses_beauty_action_pool(plan)


def resolve_action_plugin(plan: dict) -> tuple[str, tuple[str, ...]]:
    if _category_is_beauty(plan):
        return "beauty_skincare", BEAUTY_POOL_IDS
    return "generic", GENERIC_ACTION_IDS


def _human_ok(shot: dict) -> bool:
    mode = (shot.get("human_cast_mode") or "").strip().lower()
    if mode in ("none", "no", "product"):
        return False
    return True


def _pick_id(
    candidates: list[str],
    *,
    used: set[str],
    rotation: int,
) -> str | None:
    if not candidates:
        return None
    unused = [a for a in candidates if a not in used]
    pool = unused or candidates
    return pool[rotation % len(pool)]


def apply_action_planning(plan: dict, *, job=None) -> dict:
    """在 L3（及 Listing L4）之后调用；不改 role。"""
    tpl = (plan.get("plan_template") or "").strip()
    if tpl in SKIP_TEMPLATES:
        plan["action_planning_scope"] = "skip"
        plan["action_planning"] = {
            "version": ACTION_CATALOG_VERSION,
            "scope": "skip",
            "plugin": None,
            "reason": tpl,
        }
        return plan

    plugin, plugin_ids = resolve_action_plugin(plan)
    beauty = plugin == "beauty_skincare"
    batch_index = int(plan.get("visual_batch_index") or 0)
    used: set[str] = set()
    roster: list[dict] = []

    shots = plan.get("shots") or []
    for i, shot in enumerate(shots):
        try:
            idx = int(shot.get("index") or (i + 1))
        except (TypeError, ValueError):
            idx = i + 1
        from generation.services.ingredient_frame_policy import shot_is_ingredient_composition_frame

        if shot_is_ingredient_composition_frame(shot):
            used.add("B07")
            meta = action_by_id("B07") or {}
            shot["primary_action_id"] = "B07"
            shot["action_master_zh"] = display_label_zh("B07", beauty=beauty)
            shot["action_tier"] = meta.get("tier") or "safe"
            shot["product_action_lock_en"] = (meta.get("lock_en") or "").strip()
            shot["ingredient_composition_only"] = True
            from generation.services.ingredient_frame_policy import build_ingredient_frame_lock_en

            shot["ingredient_frame_lock_en"] = build_ingredient_frame_lock_en(plan)
            roster.append(
                {
                    "index": idx,
                    "role": (shot.get("role") or ""),
                    "action_id": "B07",
                    "label_zh": shot["action_master_zh"],
                    "tier": shot["action_tier"],
                }
            )
            continue
        allowed = allowed_action_ids_for_shot(shot, plugin_ids=plugin_ids, shot_ordinal=idx)
        human_ok = _human_ok(shot)
        candidates: list[str] = []
        for aid in allowed:
            meta = action_by_id(aid)
            if not meta:
                continue
            if meta.get("requires_human") and not human_ok:
                continue
            candidates.append(aid)
        if not candidates:
            # 人物被禁时回退非人物动作
            for aid in allowed:
                meta = action_by_id(aid)
                if meta and not meta.get("requires_human"):
                    candidates.append(aid)
        if not candidates:
            candidates = [a for a in plugin_ids if not (action_by_id(a) or {}).get("requires_human")]
        if not candidates:
            candidates = list(plugin_ids)

        picked = _pick_id(candidates, used=used, rotation=batch_index + idx)
        if not picked:
            continue
        used.add(picked)
        meta = action_by_id(picked) or {}
        lock = (meta.get("lock_en") or "").strip()
        shot["primary_action_id"] = picked
        shot["action_master_zh"] = display_label_zh(picked, beauty=beauty)
        shot["action_tier"] = meta.get("tier") or "safe"
        shot["product_action_lock_en"] = lock
        if picked == "B07":
            from generation.services.ingredient_frame_policy import build_ingredient_frame_lock_en

            shot["ingredient_composition_only"] = True
            shot["ingredient_frame_lock_en"] = build_ingredient_frame_lock_en(plan)
        roster.append(
            {
                "index": idx,
                "role": (shot.get("role") or ""),
                "action_id": picked,
                "label_zh": shot["action_master_zh"],
                "tier": shot["action_tier"],
            }
        )

    others = [f"#{r['index']}={r['action_id']}" for r in roster]
    if others:
        plan["action_set_diversity_en"] = (
            "SET ACTION DISTRIBUTION — Each frame uses a distinct product-action master "
            f"({', '.join(others)}). Do not repeat the same product pose/action across frames."
        )

    plan["action_planning_scope"] = "fill"
    plan["action_planning"] = {
        "version": ACTION_CATALOG_VERSION,
        "scope": "fill",
        "plugin": plugin,
        "beauty_increment": beauty,
        "roster": roster,
    }
    return plan
