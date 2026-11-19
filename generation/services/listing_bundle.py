"""电商 Listing 套图（TK 九图 / Amazon 七图）共用判断与索引。"""

from __future__ import annotations

LISTING_PLAN_TEMPLATES = frozenset({"tk_mx_ecommerce_9", "amazon_listing_7"})


def is_listing_ecommerce_plan(plan: dict | None) -> bool:
    if not plan:
        return False
    return (plan.get("plan_template") or "").strip() in LISTING_PLAN_TEMPLATES


def listing_image_count(plan: dict | None) -> int:
    tpl = (plan or {}).get("plan_template") or ""
    if tpl == "amazon_listing_7":
        return 7
    if tpl == "tk_mx_ecommerce_9":
        return 9
    return int((plan or {}).get("image_count") or 0)


def listing_payoff_shot_index(plan: dict | None) -> int:
    if (plan or {}).get("plan_template") == "amazon_listing_7":
        return 0
    return 9


def listing_creative_detail_indices(plan: dict | None) -> tuple[int, ...]:
    if (plan or {}).get("plan_template") == "amazon_listing_7":
        return (4, 5, 6)
    return (3, 6, 7, 8, 9)


# Amazon 七图槽位 ← 九图营销 brief 序号（build_marketing_strategy 仍产出 9 条）
_AMAZON_STRATEGY_BRIEF_BY_SHOT: dict[int, int] = {
    1: 2,
    2: 1,
    3: 5,
    4: 4,
    5: 3,
    6: 7,
    7: 8,
}


def strategy_brief_index_for_shot(plan: dict, shot_index: int) -> int:
    if (plan.get("plan_template") or "") == "amazon_listing_7":
        return _AMAZON_STRATEGY_BRIEF_BY_SHOT.get(int(shot_index), shot_index)
    return shot_index


def listing_creative_detail_specs(plan: dict | None) -> dict:
    from generation.services.shot_diversity_constants import (
        AMAZON_CREATIVE_DETAIL_SPECS,
        CREATIVE_DETAIL_SPECS,
    )

    if (plan or {}).get("plan_template") == "amazon_listing_7":
        return AMAZON_CREATIVE_DETAIL_SPECS
    return CREATIVE_DETAIL_SPECS
