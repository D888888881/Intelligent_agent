"""五层 Agent 编排：产品理解 → 类目策略 → 身份规划 → 套图创意 → 生图准备。"""

from __future__ import annotations

from generation.services.listing_bundle import LISTING_PLAN_TEMPLATES
from generation.services.marketplace_profiles import apply_marketplace_profile
from generation.services.pipeline.layer1_product import run_layer1_product_understanding
from generation.services.pipeline.layer2_category import run_layer2_category_strategy
from generation.services.pipeline.layer3_identity import run_layer3_identity_planning
from generation.services.pipeline.layer3_5_action import run_layer3_5_action_planning
from generation.services.pipeline.layer4_creative import run_layer4_bundle_creative
from generation.services.pipeline.layer5_generation import run_layer5_generation_prepare
from generation.services.pipeline.schemas import PIPELINE_SCHEMA_VERSION
from generation.services.planner import build_plan
from generation.services.variant_shots import apply_multi_reference_listing_rules


def _resolve_listing_template(effective_template: str, category_strategy: dict) -> str:
    tpl = (effective_template or "auto").strip()
    if tpl in LISTING_PLAN_TEMPLATES:
        return tpl
    if tpl in ("auto", "generic", ""):
        return category_strategy.get("plan_template") or "tk_mx_ecommerce_9"
    return category_strategy.get("plan_template") or tpl


def run_listing_pipeline(
    job,
    *,
    attachments,
    existing_plan: dict,
    effective_template: str,
    image_count: int,
    vision_model: str | None,
    run_after_prepare: bool,
) -> tuple[dict, int, dict]:
    pipeline: dict = {"version": PIPELINE_SCHEMA_VERSION, "layers": {}}

    product_analysis, l1 = run_layer1_product_understanding(
        attachments,
        job.prompt,
        plan_template=effective_template,
        vision_model=vision_model,
        multi_reference=len(attachments) > 1,
    )
    pipeline["layers"]["L1"] = l1

    marketplace_id = existing_plan.get("marketplace_id") or (job.plan_json or {}).get("marketplace_id")
    category_strategy, l2 = run_layer2_category_strategy(
        product_analysis,
        job.prompt,
        marketplace_id=marketplace_id,
    )
    pipeline["layers"]["L2"] = l2
    marketing_strategy = category_strategy.get("ecommerce_strategy") or {}

    listing_tpl = _resolve_listing_template(effective_template, category_strategy)
    plan, l3 = run_layer3_identity_planning(
        user_prompt=job.prompt,
        image_count=image_count,
        plan_template=listing_tpl,
        product_analysis=product_analysis,
        marketing_strategy=marketing_strategy,
        reference_attachment_count=len(attachments),
    )
    pipeline["layers"]["L3"] = l3

    preset_skin = (existing_plan.get("cast_skin_preset") or "caucasian").strip().lower()
    if preset_skin not in ("caucasian", "diverse", "black_only"):
        preset_skin = "caucasian"
    plan["cast_skin_preset"] = preset_skin
    plan["category_strategy"] = {
        k: v for k, v in category_strategy.items() if k != "ecommerce_strategy"
    }

    if marketplace_id:
        plan = apply_marketplace_profile(plan, marketplace_id)

    from generation.services.aspect_ratio import merge_user_aspect_into_plan

    plan = merge_user_aspect_into_plan(plan, existing_plan)

    plan, l4 = run_layer4_bundle_creative(plan, job=job)
    pipeline["layers"]["L4"] = l4
    # 人物预算在 L4 写完后再填动作，避免 G05 落到 human=none 的镜
    plan, l35 = run_layer3_5_action_planning(plan, job=job)
    pipeline["layers"]["L3_5"] = l35
    from generation.services.ingredient_frame_policy import apply_ingredient_frame_policy

    plan = apply_ingredient_frame_policy(plan)

    if not run_after_prepare:
        plan["awaiting_generation_confirm"] = True
        plan["plan_ready"] = True

    ids = [a.id for a in attachments]
    if ids:
        plan["reference_attachment_ids"] = ids

    selected_image_model = existing_plan.get("image_model")
    plan, image_count, l5 = run_layer5_generation_prepare(
        plan,
        job=job,
        product_analysis=product_analysis,
        selected_image_model=selected_image_model,
        attachments=attachments,
        user_prompt=job.prompt,
        image_count=image_count,
    )
    pipeline["layers"]["L5"] = l5
    plan["agent_pipeline"] = pipeline
    return plan, image_count, pipeline


def run_generic_pipeline(
    job,
    *,
    attachments,
    existing_plan: dict,
    effective_template: str,
    image_count: int,
    product_analysis: dict,
    run_after_prepare: bool,
) -> tuple[dict, int, dict]:
    """非 Listing 套图：L1 + 单层 build_plan + L5 轻量准备。"""
    pipeline: dict = {"version": PIPELINE_SCHEMA_VERSION, "layers": {}}
    from generation.services.pipeline.schemas import layer_snapshot

    pipeline["layers"]["L1"] = layer_snapshot(
        "L1_product_understanding",
        summary={"has_analysis": bool(product_analysis), "mode": "reused"},
    )
    pipeline["layers"]["L2"] = layer_snapshot("L2_category_strategy", status="skip", summary={"reason": "non_listing"})
    pipeline["layers"]["L3"] = layer_snapshot("L3_identity_planning", status="skip", summary={"reason": "non_listing"})

    plan = build_plan(
        job.prompt,
        image_count,
        plan_template=effective_template,
        product_analysis=product_analysis,
        reference_attachment_count=len(attachments),
    )
    plan["user_prompt"] = job.prompt
    preset_skin = (existing_plan.get("cast_skin_preset") or "caucasian").strip().lower()
    if preset_skin not in ("caucasian", "diverse", "black_only"):
        preset_skin = "caucasian"
    plan["cast_skin_preset"] = preset_skin

    from generation.services.aspect_ratio import merge_user_aspect_into_plan

    plan = merge_user_aspect_into_plan(plan, existing_plan)

    tpl = plan.get("plan_template") or effective_template
    if tpl in ("reference_guided", "photo_refine"):
        if tpl == "reference_guided":
            from generation.services.shot_plan import normalize_shot_list

            plan["shots"] = normalize_shot_list(plan.get("shots") or [], job.image_count, job.prompt)
        pipeline["layers"]["L3_5"] = layer_snapshot(
            "L3_5_action_planning", status="skip", summary={"reason": tpl}
        )
    else:
        plan = apply_multi_reference_listing_rules(plan, len(attachments))
        plan, l35 = run_layer3_5_action_planning(plan, job=job)
        pipeline["layers"]["L3_5"] = l35
        from generation.services.action_planning.preview_zh import format_action_preview_markdown

        action_md = format_action_preview_markdown(plan)
        if action_md:
            prev = (plan.get("planning_summary") or "").strip()
            plan["planning_summary"] = f"{prev}\n\n{action_md}".strip() if prev else action_md

    if not run_after_prepare:
        plan["awaiting_generation_confirm"] = True
        plan["plan_ready"] = True

    ids = [a.id for a in attachments]
    if ids:
        plan["reference_attachment_ids"] = ids

    plan, image_count, l5 = run_layer5_generation_prepare(
        plan,
        job=job,
        product_analysis=product_analysis,
        selected_image_model=existing_plan.get("image_model"),
        attachments=attachments,
        user_prompt=job.prompt,
        image_count=image_count,
    )
    pipeline["layers"]["L4"] = layer_snapshot("L4_bundle_creative", status="skip", summary={"reason": "non_listing"})
    pipeline["layers"]["L5"] = l5
    plan["agent_pipeline"] = pipeline
    return plan, image_count, pipeline
