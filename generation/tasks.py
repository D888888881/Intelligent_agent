from celery import shared_task
from django.conf import settings
from django.utils import timezone

from chat.models import Message
from generation.models import GeneratedImage, GenerationJob
from generation.services.dispatch import dispatch_next_for_user
from generation.services.image_gen import generate_image_file
from generation.services.model_strategy import model_family
import logging

from generation.services.shot_plan import normalize_shot_list

logger = logging.getLogger(__name__)
from generation.services.prompt_builder import (
    build_moderation_fallback_prompt,
    build_reference_forced_prompt,
    build_shot_generation_prompt,
    is_reference_refusal_error,
    is_violation_error,
    shot_uses_reference,
)


def _assistant_status_text(job: GenerationJob) -> str:
    if job.status == GenerationJob.Status.QUEUED:
        return "排队等待生图…"
    if job.status == GenerationJob.Status.RUNNING:
        if job.completed_count <= 0:
            return f"正在生成图片…（0/{job.image_count}）"
        return f"正在生成图片…（{job.completed_count}/{job.image_count}）"
    if job.status == GenerationJob.Status.SUCCEEDED:
        if job.error_message:
            return f"已完成 {job.completed_count}/{job.image_count} 张（{job.error_message}）"
        return f"已完成 {job.image_count} 张套图。"
    if job.status == GenerationJob.Status.FAILED:
        base = f"生成失败（{job.completed_count}/{job.image_count}）"
        if job.error_message:
            return f"{base}：{job.error_message}"
        return base + "：未知错误"
    if job.status == GenerationJob.Status.CANCELLED:
        return "已取消生成。"
    return "正在分析参考图并策划套图…"


def _update_assistant_message_after_plan(job: GenerationJob, plan: dict) -> None:
    if not job.conversation_id:
        return
    msg = (
        Message.objects.filter(
            conversation_id=job.conversation_id,
            role=Message.Role.ASSISTANT,
            metadata__generation_job_id=job.id,
        )
        .order_by("-id")
        .first()
    )
    if not msg:
        return
    summary = (plan.get("planning_summary") or "").strip()
    if summary:
        msg.content = summary + "\n\n开始逐张生成高清电商图…"
    else:
        msg.content = f"已完成 {job.image_count} 条镜头策划，开始逐张生成…"
    meta = dict(msg.metadata or {})
    meta["generation_phase"] = "planned"
    meta["image_count"] = job.image_count
    meta["plan_ready"] = True
    msg.metadata = meta
    msg.save(update_fields=["content", "metadata"])


def _update_assistant_message(job: GenerationJob) -> None:
    if not job.conversation_id:
        return
    msg = (
        Message.objects.filter(
            conversation_id=job.conversation_id,
            role=Message.Role.ASSISTANT,
            metadata__generation_job_id=job.id,
        )
        .order_by("-id")
        .first()
    )
    if not msg:
        return
    msg.content = _assistant_status_text(job)
    meta = dict(msg.metadata or {})
    meta["generation_phase"] = job.status
    meta["completed_count"] = job.completed_count
    meta["image_count"] = job.image_count
    msg.metadata = meta
    msg.save(update_fields=["content", "metadata"])


def _resolve_reference_attachment(job, shot, plan, image_model):
    use_ref = shot_uses_reference(shot, plan)
    ref_att = job.reference_attachment if use_ref else None
    if job.reference_attachment and model_family(image_model) == "gpt_image":
        ref_att = job.reference_attachment
    return ref_att


def _fallback_reference_for_retry(job, reference_attachment, reference_images):
    if reference_images:
        return None, list(reference_images)
    att = reference_attachment or (job.reference_attachment if job else None)
    return att, None


def _generate_shot_with_optional_violation_retry(
    *,
    prompt,
    shot,
    plan,
    index,
    job,
    reference_attachment,
    reference_images,
    aspect_ratio,
    image_model,
):
    ref = reference_attachment or job.reference_attachment
    has_refs = bool(reference_images) or bool(ref)

    def _call(p, attachment, ref_images=None):
        if ref_images:
            return generate_image_file(
                p,
                index,
                job.id,
                reference_images=ref_images,
                aspect_ratio=aspect_ratio,
                image_model=image_model,
            )
        return generate_image_file(
            p,
            index,
            job.id,
            reference_attachment=attachment,
            aspect_ratio=aspect_ratio,
            image_model=image_model,
        )

    imgs = reference_images
    try:
        return _call(prompt, reference_attachment, imgs)
    except Exception as exc:
        if is_reference_refusal_error(exc):
            att_fb, imgs_fb = _fallback_reference_for_retry(
                job, reference_attachment, imgs or reference_images
            )
            if att_fb or imgs_fb:
                forced = build_reference_forced_prompt(shot, plan)
                if imgs_fb:
                    return _call(forced, None, imgs_fb)
                return _call(forced, att_fb)
            raise
        if is_violation_error(exc):
            gpt = model_family(image_model) == "gpt_image"
            use_ref_in_fallback = bool(
                has_refs or (gpt and job.reference_attachment)
            )
            safe_prompt = build_moderation_fallback_prompt(
                shot,
                plan,
                with_reference=use_ref_in_fallback and gpt,
            )
            att_fb, imgs_fb = _fallback_reference_for_retry(
                job, reference_attachment, imgs
            )
            if imgs_fb:
                return _call(safe_prompt, None, imgs_fb)
            return _call(
                safe_prompt,
                att_fb if gpt else None,
            )
        raise


def _run_one_shot(job, shot, plan, aspect_ratio, image_model) -> tuple[bool, str]:
    """生成单张，返回 (是否成功, 错误信息)。"""
    index = int(shot.get("index", 0))
    if index <= 0:
        return True, ""

    gen_img, _ = GeneratedImage.objects.get_or_create(
        job=job,
        index=index,
        defaults={
            "prompt": shot.get("prompt_en", job.prompt),
            "status": GeneratedImage.Status.PENDING,
        },
    )
    if gen_img.status == GeneratedImage.Status.SUCCEEDED and gen_img.file:
        return True, ""

    gen_img.status = GeneratedImage.Status.RUNNING
    gen_img.error_message = ""
    gen_img.save(update_fields=["status", "error_message"])

    from generation.services.job_references import reference_image_payloads_for_shot

    ref_payloads = reference_image_payloads_for_shot(job, shot)
    ref_att = _resolve_reference_attachment(job, shot, plan, image_model)
    use_multi = len(ref_payloads) > 0
    prompt = build_shot_generation_prompt(
        shot, plan, attach_reference=bool(use_multi or ref_att)
    )
    gen_img.prompt = prompt
    gen_img.save(update_fields=["prompt"])

    try:
        content_file = _generate_shot_with_optional_violation_retry(
            prompt=prompt,
            shot=shot,
            plan=plan,
            index=index,
            job=job,
            reference_attachment=ref_att if not use_multi else None,
            reference_images=ref_payloads if use_multi else None,
            aspect_ratio=aspect_ratio,
            image_model=image_model,
        )
        gen_img.file.save(content_file.name, content_file, save=False)
        gen_img.status = GeneratedImage.Status.SUCCEEDED
        gen_img.error_message = ""
        gen_img.save()
        job.completed_count = job.images.filter(
            status=GeneratedImage.Status.SUCCEEDED
        ).count()
        job.save(update_fields=["completed_count"])
        _update_assistant_message(job)
        return True, ""
    except Exception as exc:
        err = str(exc)
        gen_img.status = GeneratedImage.Status.FAILED
        gen_img.error_message = err
        gen_img.save(update_fields=["status", "error_message"])
        _update_assistant_message(job)
        return False, err


@shared_task(bind=True, max_retries=0)
def run_generation_job(self, job_id: int):
    try:
        job = GenerationJob.objects.select_related("user", "reference_attachment").get(pk=job_id)
    except GenerationJob.DoesNotExist:
        return

    if job.status not in (
        GenerationJob.Status.RUNNING,
        GenerationJob.Status.PENDING,
    ):
        return

    if not job.started_at:
        job.started_at = timezone.now()
        job.status = GenerationJob.Status.RUNNING
        job.save(update_fields=["started_at", "status"])
        _update_assistant_message(job)

    plan = job.plan_json or {}
    shots = normalize_shot_list(
        plan.get("shots") or [],
        job.image_count,
        job.prompt,
    )
    shots = sorted(shots, key=lambda s: int(s.get("index") or 0))
    aspect_ratio = plan.get("aspect_ratio", "1:1")
    image_model = plan.get("image_model") or None
    failed_count = 0
    last_error = ""

    for shot in shots:
        if job.cancel_requested:
            break
        job.refresh_from_db(fields=["cancel_requested"])
        if job.cancel_requested:
            break
        ok, err = _run_one_shot(job, shot, plan, aspect_ratio, image_model)
        if not ok:
            failed_count += 1
            last_error = err or last_error

    extra_passes = max(0, int(getattr(settings, "GRSAI_JOB_FAILED_SHOT_RETRIES", 3)))
    for pass_no in range(extra_passes):
        if job.cancel_requested:
            break
        job.refresh_from_db(fields=["cancel_requested"])
        if job.cancel_requested:
            break
        failed_indices = set(
            job.images.filter(status=GeneratedImage.Status.FAILED).values_list("index", flat=True)
        )
        if not failed_indices:
            break
        logger.info(
            "job=%s retry failed shots pass=%s/%s indices=%s",
            job.id,
            pass_no + 1,
            extra_passes,
            sorted(failed_indices),
        )
        retry_shots = [s for s in shots if int(s.get("index", 0)) in failed_indices]
        for shot in retry_shots:
            if job.cancel_requested:
                break
            job.refresh_from_db(fields=["cancel_requested"])
            if job.cancel_requested:
                break
            ok, err = _run_one_shot(job, shot, plan, aspect_ratio, image_model)
            if ok:
                failed_count = max(0, failed_count - 1)
            elif err:
                last_error = err
        if not job.images.filter(status=GeneratedImage.Status.FAILED).exists():
            break

    if job.cancel_requested:
        job.status = GenerationJob.Status.CANCELLED
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "finished_at"])
        dispatch_next_for_user(job.user_id)
        return

    job.refresh_from_db(fields=["completed_count"])
    failed_count = job.images.filter(status=GeneratedImage.Status.FAILED).count()

    job.finished_at = timezone.now()
    if job.completed_count <= 0:
        job.status = GenerationJob.Status.FAILED
        job.error_message = last_error or "全部镜头生成失败"
        job.save(update_fields=["status", "error_message", "finished_at"])
    else:
        job.status = GenerationJob.Status.SUCCEEDED
        if failed_count > 0:
            job.error_message = f"{failed_count} 张失败"
            if last_error:
                job.error_message += f"（最近错误：{last_error[:200]}）"
        else:
            job.error_message = ""
        job.save(update_fields=["status", "error_message", "finished_at"])
    _update_assistant_message(job)
    dispatch_next_for_user(job.user_id)


@shared_task(bind=True, max_retries=0)
def run_slot_refine_task(self, candidate_id: int):
    from generation.services.slot_refine import run_slot_refine_candidate

    run_slot_refine_candidate(candidate_id)
