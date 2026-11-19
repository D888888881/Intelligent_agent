import logging

import threading



from django.conf import settings

from django.utils import timezone



from generation.models import GeneratedImage, GenerationJob

from generation.services.dispatch import enqueue_or_run

from generation.services.listing_bundle import LISTING_PLAN_TEMPLATES

from generation.services.pipeline import run_generic_pipeline, run_listing_pipeline

from generation.services.planner import analyze_product_for_plan



logger = logging.getLogger(__name__)





def _job_should_abort(job_id: int) -> bool:

    row = GenerationJob.objects.filter(pk=job_id).values_list(

        "cancel_requested", "status"

    ).first()

    if not row:

        return True

    cancel_requested, status = row

    return bool(cancel_requested) or status == GenerationJob.Status.CANCELLED





def _finalize_cancelled_job(job: GenerationJob) -> None:

    if job.status == GenerationJob.Status.CANCELLED:

        return

    job.status = GenerationJob.Status.CANCELLED

    if not job.finished_at:

        job.finished_at = timezone.now()

    if not job.error_message:

        job.error_message = "用户已取消任务"

    job.save(update_fields=["status", "finished_at", "error_message"])

    from generation.tasks import _update_assistant_message



    _update_assistant_message(job)





def _resolve_effective_template(plan_template: str, existing_plan: dict) -> str:

    effective = (plan_template or existing_plan.get("plan_template") or "auto").strip()

    return effective





def _is_listing_job(effective_template: str, existing_plan: dict) -> bool:
    tpl = effective_template
    if tpl in LISTING_PLAN_TEMPLATES:
        return True
    stored = (existing_plan.get("plan_template") or "").strip()
    return stored in LISTING_PLAN_TEMPLATES





def prepare_and_run_job(

    job_id: int,

    *,

    vision_model: str | None = None,

    plan_template: str = "auto",

    run_after_prepare: bool = True,

) -> None:

    job = None

    try:

        job = GenerationJob.objects.select_related("reference_attachment", "user").get(pk=job_id)

        if _job_should_abort(job_id):

            _finalize_cancelled_job(job)

            return

        from generation.services.job_references import job_attachments



        attachments = job_attachments(job)

        existing_plan = job.plan_json or {}

        image_count = job.image_count

        effective_template = _resolve_effective_template(plan_template, existing_plan)



        if _is_listing_job(effective_template, existing_plan):

            plan, image_count, _pipeline = run_listing_pipeline(

                job,

                attachments=attachments,

                existing_plan=existing_plan,

                effective_template=effective_template,

                image_count=image_count,

                vision_model=vision_model,

                run_after_prepare=run_after_prepare,

            )

        else:

            product_analysis = {}

            if attachments:

                vision_prompt = job.prompt

                if effective_template == "reference_guided" or (

                    existing_plan.get("plan_template") == "reference_guided"

                ):

                    vision_prompt = (

                        f"{job.prompt}\n\n"

                        "[系统提示] 参考图导演模式：请描述每张上传图（按顺序）是产品 SKU、版式/首图、模特场景、尺码表或其他，"

                        "并提取产品 identity；若有多 SKU 再建立 product_variants。"

                    ).strip()

                elif len(attachments) > 1:

                    vision_prompt = (

                        f"{job.prompt}\n\n"

                        "[系统提示] 用户上传了多张参考图，可能为多色口红/多配色鞋/多色内衣或吊带等，"

                        "请为每个可售款式+颜色建立 product_variants。"

                    ).strip()

                product_analysis = analyze_product_for_plan(

                    attachments,

                    vision_prompt,

                    vision_model=vision_model,

                )

                if _job_should_abort(job_id):

                    job.refresh_from_db()

                    _finalize_cancelled_job(job)

                    return



            plan, image_count, _pipeline = run_generic_pipeline(

                job,

                attachments=attachments,

                existing_plan=existing_plan,

                effective_template=effective_template,

                image_count=image_count,

                product_analysis=product_analysis,

                run_after_prepare=run_after_prepare,

            )



        if _job_should_abort(job_id):

            job.refresh_from_db()

            _finalize_cancelled_job(job)

            return



        shots = plan.get("shots") or []

        ref_ids = plan.get("reference_attachment_ids") or [a.id for a in attachments]

        tpl = plan.get("plan_template") or effective_template
        if tpl in LISTING_PLAN_TEMPLATES:
            from generation.services.tk_mx_listing import format_step1_preview_markdown

            plan["planning_summary"] = format_step1_preview_markdown(plan)
        elif tpl == "reference_guided":
            from generation.services.reference_director import format_reference_guided_preview_markdown

            plan["planning_summary"] = format_reference_guided_preview_markdown(plan)

        job.plan_json = plan

        job.image_count = image_count

        save_fields = ["plan_json", "image_count"]

        if ref_ids:

            job.reference_attachment_ids = ref_ids

            save_fields.append("reference_attachment_ids")

        job.save(update_fields=save_fields)



        for shot in shots:

            GeneratedImage.objects.get_or_create(

                job=job,

                index=int(shot["index"]),

                defaults={

                    "prompt": shot.get("prompt_en", job.prompt),

                    "status": GeneratedImage.Status.PENDING,

                },

            )



        from generation.tasks import _update_assistant_message_after_plan



        _update_assistant_message_after_plan(

            job,

            plan,

            awaiting_confirm=not run_after_prepare,

        )



        if run_after_prepare:

            if _job_should_abort(job_id):

                job.refresh_from_db()

                _finalize_cancelled_job(job)

                return

            enqueue_or_run(job)

            job.refresh_from_db()

            from generation.tasks import _update_assistant_message



            _update_assistant_message(job)

        else:

            job.status = GenerationJob.Status.PENDING

            job.save(update_fields=["status"])

    except GenerationJob.DoesNotExist:

        return

    except Exception as exc:

        logger.exception("prepare_and_run_job failed job=%s", job_id)

        if job is None:

            return

        job.status = GenerationJob.Status.FAILED

        job.error_message = str(exc)[:2000]

        job.finished_at = timezone.now()

        job.save(update_fields=["status", "error_message", "finished_at"])

        from generation.tasks import _update_assistant_message



        _update_assistant_message(job)





def start_prepare_and_run_async(

    job_id: int,

    *,

    vision_model: str | None = None,

    plan_template: str = "auto",

    run_after_prepare: bool = True,

) -> None:

    threading.Thread(

        target=prepare_and_run_job,

        kwargs={

            "job_id": job_id,

            "vision_model": vision_model,

            "plan_template": plan_template,

            "run_after_prepare": run_after_prepare,

        },

        daemon=True,

    ).start()

