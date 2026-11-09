import logging
import threading

from django.conf import settings
from django.utils import timezone

from generation.models import GeneratedImage, GenerationJob
from generation.services.dispatch import enqueue_or_run
from Intelligent_agent.model_catalog import resolve_image_model
from generation.services.model_strategy import tune_plan_for_image_model
from generation.services.planner import analyze_product_for_plan, build_plan

logger = logging.getLogger(__name__)


from generation.services.shot_plan import normalize_shot_list


def prepare_and_run_job(
    job_id: int,
    *,
    vision_model: str | None = None,
    plan_template: str = "auto",
) -> None:
    job = None
    try:
        job = GenerationJob.objects.select_related("reference_attachment", "user").get(pk=job_id)
        if job.cancel_requested or job.status == GenerationJob.Status.CANCELLED:
            return
        from generation.services.job_references import job_attachments
        from generation.services.variant_shots import assign_shot_variants
        from generation.services.detail_shot_diversity import apply_detail_shot_diversity
        from generation.services.talent_diversity import apply_talent_diversity, resolve_talent_rotation_index
        attachments = job_attachments(job)
        product_analysis = {}
        if attachments:
            vision_prompt = job.prompt
            if attachments and len(attachments) > 1:
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
        attachment = attachments[0] if attachments else job.reference_attachment

        image_count = job.image_count
        existing_plan = job.plan_json or {}
        selected_image_model = existing_plan.get("image_model") or settings.GRSAI_IMAGE_MODEL
        selected_image_model = resolve_image_model(selected_image_model)

        plan = build_plan(
            job.prompt,
            image_count,
            reference_summary="",
            plan_template=plan_template,
            product_analysis=product_analysis,
        )
        plan["user_prompt"] = job.prompt
        preset_skin = (existing_plan.get("cast_skin_preset") or "caucasian").strip().lower()
        if preset_skin not in ("caucasian", "diverse", "black_only"):
            preset_skin = "caucasian"
        plan["cast_skin_preset"] = preset_skin
        from generation.services.visual_batch_variance import resolve_visual_batch_index

        plan["visual_batch_index"] = resolve_visual_batch_index(
            job, product_analysis=product_analysis
        )
        plan["image_model"] = selected_image_model
        plan = tune_plan_for_image_model(
            plan,
            selected_image_model,
            has_reference=bool(attachments or attachment),
        )
        ids = [a.id for a in attachments]
        if ids:
            plan["reference_attachment_ids"] = ids
        shots = plan.get("shots") or []
        shots = normalize_shot_list(shots, job.image_count, job.prompt)
        plan = assign_shot_variants(plan)
        plan = apply_detail_shot_diversity(plan, job=job)
        batch_idx = int(plan.get("visual_batch_index") or 0)
        conv_rot = resolve_talent_rotation_index(job)
        talent_rot = (batch_idx + conv_rot) % max(1, 12)
        plan = apply_talent_diversity(plan, rotation_index=talent_rot)
        shots = plan.get("shots") or []
        plan["shots"] = shots
        if shots:
            image_count = len(shots)

        job.plan_json = plan
        job.image_count = image_count
        save_fields = ["plan_json", "image_count"]
        if ids:
            job.reference_attachment_ids = ids
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

        _update_assistant_message_after_plan(job, plan)

        enqueue_or_run(job)
        job.refresh_from_db()
        from generation.tasks import _update_assistant_message

        _update_assistant_message(job)
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
) -> None:
    threading.Thread(
        target=prepare_and_run_job,
        kwargs={
            "job_id": job_id,
            "vision_model": vision_model,
            "plan_template": plan_template,
        },
        daemon=True,
    ).start()
