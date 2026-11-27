"""确认生图 / Celery 开跑前：重新套用套图规则（人物、卖点、机位、SKU）。"""

from __future__ import annotations

from generation.services.camera_diversity import apply_camera_diversity
from generation.services.listing_bundle import is_listing_ecommerce_plan
from generation.services.listing_conversion_story import apply_listing_conversion_story
from generation.services.listing_frame_focus import apply_listing_frame_focus
from generation.services.listing_human_cast import apply_mandated_human_casts
from generation.services.listing_usp_distribution import apply_listing_usp_distribution
from generation.services.listing_visual_cohesion import (
    apply_listing_visual_cohesion,
    ensure_listing_variation,
)
from generation.services.product_sku_guard import apply_product_sku_guard
from generation.services.product_usage_semantics import apply_product_usage_locks
from generation.services.listing_shot_roles import enforce_tk_mx_shot_roles
from generation.services.tk_mx_listing import apply_tk_mx_listing_plan


def _apply_tk_flex_variants(plan: dict, *, job=None) -> dict:
    tpl = (plan.get("plan_template") or "").strip()
    if tpl != "tk_mx_ecommerce_9":
        return plan
    plan = enforce_tk_mx_shot_roles(plan)
    from generation.services.frame3_flex import apply_frame3_flex_variant
    from generation.services.frame4_flex import apply_frame4_flex_variant
    from generation.services.frame5_flex import apply_frame5_flex_variant
    from generation.services.frame9_conversion import apply_frame9_conversion_variant

    plan = apply_frame3_flex_variant(plan, job=job)
    plan = apply_frame4_flex_variant(plan, job=job)
    plan = apply_frame5_flex_variant(plan, job=job)
    plan = apply_frame9_conversion_variant(plan, job=job)
    return plan


def prepare_listing_plan_for_generation(plan: dict, *, job=None) -> dict:
    """套图任务在 RUNNING 前刷新策划，避免确认后仍用陈旧 shot 字段。"""
    if not is_listing_ecommerce_plan(plan):
        return plan

    plan = dict(plan)
    if job is not None:
        from generation.services.job_references import job_attachments
        from generation.services.product_usage_semantics import attach_package_hints

        plan["product_analysis"] = attach_package_hints(
            plan.get("product_analysis") or {},
            job_attachments(job),
        )
    plan = ensure_listing_variation(plan)
    plan = apply_tk_mx_listing_plan(plan)
    plan = apply_product_usage_locks(plan)
    plan = _apply_tk_flex_variants(plan, job=job)
    plan = apply_listing_conversion_story(plan)
    plan = apply_listing_frame_focus(plan)
    plan = apply_mandated_human_casts(plan)
    plan = apply_listing_visual_cohesion(plan)
    plan = apply_camera_diversity(plan, merge=True)
    plan = apply_listing_usp_distribution(plan)
    plan = apply_tk_mx_listing_plan(plan)
    plan = apply_mandated_human_casts(plan)
    plan = apply_listing_frame_focus(plan)
    plan = apply_product_sku_guard(plan)
    plan = _apply_tk_flex_variants(plan, job=job)
    plan = apply_product_usage_locks(plan)
    plan = apply_listing_usp_distribution(plan)
    plan = apply_mandated_human_casts(plan)
    if (plan.get("plan_template") or "") == "tk_mx_ecommerce_9":
        from generation.services.listing_frame6_benefit import apply_tk_frame6_benefit
        from generation.services.listing_tk_frame_role import apply_tk_frame_role_preambles
        from generation.services.tk_mx_listing import reassert_tk_mx_invariants

        plan = apply_tk_frame_role_preambles(plan)
        plan = apply_tk_frame6_benefit(plan)
        plan = reassert_tk_mx_invariants(plan)
        from generation.services.tk_mx_listing import reassert_white_bg_catalog_shots

        plan = reassert_white_bg_catalog_shots(plan)
        plan = apply_listing_usp_distribution(plan)
        plan = apply_tk_frame_role_preambles(plan)
        plan = apply_mandated_human_casts(plan)
        plan = reassert_white_bg_catalog_shots(plan)
        from generation.services.product_usage_semantics import finalize_frame4_product_truth

        plan = finalize_frame4_product_truth(plan)
    from generation.services.job_references import job_attachment_ids
    from generation.services.variant_shots import apply_multi_reference_listing_rules

    attachment_count = len(job_attachment_ids(job)) if job is not None else 0
    if attachment_count <= 1:
        attachment_count = len(plan.get("reference_attachment_ids") or [])
    if attachment_count <= 1:
        variants = (plan.get("product_analysis") or {}).get("product_variants") or []
        if isinstance(variants, list):
            attachment_count = len(variants)
    if attachment_count > 1:
        plan = apply_multi_reference_listing_rules(plan, attachment_count)
    plan["listing_generation_enforced"] = True
    return plan