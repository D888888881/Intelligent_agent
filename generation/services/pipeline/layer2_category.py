"""第二层：类目策略 Agent — 品类规则 + 营销策略 + 站点约束。"""

from __future__ import annotations

from generation.services.ecommerce_strategy import build_marketing_strategy
from generation.services.marketplace_profiles import MARKETPLACE_PROFILES, normalize_marketplace_id
from generation.services.pipeline.schemas import layer_snapshot
from generation.services.visual_batch_variance import _normalize_category_bucket, is_beauty_skincare_plan


def _visual_style_for_category(category_bucket: str) -> str:
    if category_bucket == "beauty_skincare":
        return "beauty_clean_premium"
    if not category_bucket:
        return "generic_ecommerce"
    return f"category_{category_bucket}"


def run_layer2_category_strategy(
    product_analysis: dict,
    user_prompt: str,
    *,
    marketplace_id: str | None,
) -> tuple[dict, dict]:
    mid = normalize_marketplace_id(marketplace_id)
    prof = MARKETPLACE_PROFILES[mid]
    category_bucket = _normalize_category_bucket(str(product_analysis.get("category") or ""))
    if not category_bucket and product_analysis:
        probe = {"product_analysis": product_analysis}
        if is_beauty_skincare_plan(probe):
            category_bucket = "beauty_skincare"

    marketing_strategy = build_marketing_strategy(product_analysis, user_prompt)

    category_strategy = {
        "marketplace_id": mid,
        "marketplace_label_zh": prof.get("label_zh"),
        "platform": prof.get("platform"),
        "plan_template": prof.get("plan_template"),
        "image_count": prof.get("image_count"),
        "locale": prof.get("locale"),
        "on_image_language": prof.get("on_image_language"),
        "category_bucket": category_bucket,
        "visual_style": _visual_style_for_category(category_bucket),
        "marketing_focus": (
            (marketing_strategy.get("conversion_story_zh") or "")[:200]
            or (marketing_strategy.get("product_summary_zh") or "")[:200]
        ),
        "ecommerce_strategy": marketing_strategy,
    }

    summary = {
        "marketplace_id": mid,
        "category_bucket": category_bucket,
        "visual_style": category_strategy["visual_style"],
        "shot_briefs": len(marketing_strategy.get("shot_briefs") or []),
        "core_usps": len(marketing_strategy.get("core_usps") or []),
    }
    return category_strategy, layer_snapshot("L2_category_strategy", summary=summary)
