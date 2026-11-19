"""步骤三：在已有 job 上重新分析卖点并更新策划（可选重新出图）。"""

from __future__ import annotations

from django.utils import timezone

from generation.models import GeneratedImage, GenerationJob
from generation.services.ecommerce_strategy import build_marketing_strategy
from generation.services.job_references import job_attachments
from generation.services.planner import analyze_product_for_plan, build_plan
from generation.services.prompt_builder import build_shot_generation_prompt
from generation.services.shot_plan import normalize_shot_list
from generation.services.tk_mx_listing import apply_tk_mx_listing_plan, format_step1_preview_markdown


def reoptimize_job_plan(
    job: GenerationJob,
    *,
    vision_model: str | None = None,
    regenerate_images: bool = False,
) -> dict:
    attachments = job_attachments(job)
    if not attachments:
        raise ValueError("缺少参考图，无法优化卖点")

    product_analysis = analyze_product_for_plan(
        attachments,
        job.prompt,
        vision_model=vision_model,
    )
    existing = job.plan_json or {}
    plan_template = existing.get("plan_template") or "auto"
    image_count = job.image_count or 9

    plan = build_plan(
        job.prompt,
        image_count,
        plan_template=plan_template,
        product_analysis=product_analysis,
        reference_attachment_count=len(attachments),
    )
    if existing.get("awaiting_generation_confirm"):
        plan["awaiting_generation_confirm"] = True
    plan["user_prompt"] = job.prompt
    plan["image_model"] = existing.get("image_model") or plan.get("image_model")
    plan["cast_skin_preset"] = existing.get("cast_skin_preset") or plan.get("cast_skin_preset")
    plan["visual_batch_index"] = existing.get("visual_batch_index", 0)

    from generation.services.listing_bundle import LISTING_PLAN_TEMPLATES

    if existing.get("marketplace_id"):
        from generation.services.marketplace_profiles import apply_marketplace_profile

        plan = apply_marketplace_profile(plan, existing.get("marketplace_id"))

    if plan.get("plan_template") in LISTING_PLAN_TEMPLATES:
        plan = apply_tk_mx_listing_plan(plan)
        from generation.services.action_planning import apply_action_planning

        plan = apply_action_planning(plan, job=job)
        from generation.services.ingredient_frame_policy import apply_ingredient_frame_policy

        plan = apply_ingredient_frame_policy(plan)
        plan["planning_summary"] = format_step1_preview_markdown(plan)
    elif plan.get("plan_template") == "reference_guided":
        from generation.services.reference_director import format_reference_guided_preview_markdown

        plan["planning_summary"] = format_reference_guided_preview_markdown(plan)

    shots = normalize_shot_list(plan.get("shots") or [], image_count, job.prompt)
    plan["shots"] = shots
    job.plan_json = plan
    job.image_count = len(shots) or image_count
    job.save(update_fields=["plan_json", "image_count"])

    for shot in shots:
        idx = int(shot.get("index", 0))
        if idx <= 0:
            continue
        gen_img, _ = GeneratedImage.objects.get_or_create(
            job=job,
            index=idx,
            defaults={"prompt": shot.get("prompt_en", job.prompt)},
        )
        final_prompt = build_shot_generation_prompt(shot, plan, attach_reference=True)
        gen_img.prompt = final_prompt
        if regenerate_images:
            gen_img.status = GeneratedImage.Status.PENDING
            gen_img.error_message = ""
            gen_img.save(update_fields=["prompt", "status", "error_message"])
        else:
            gen_img.save(update_fields=["prompt"])

    from generation.tasks import _update_assistant_message_after_plan

    awaiting = bool((job.plan_json or {}).get("awaiting_generation_confirm"))
    if job.conversation_id:
        _update_assistant_message_after_plan(job, plan, awaiting_confirm=awaiting)
    return plan
