from celery import shared_task
from django.conf import settings
from django.utils import timezone

from chat.models import Message
from generation.models import GeneratedImage, GenerationJob
from generation.services.dispatch import dispatch_next_for_user
from generation.services.image_gen import generate_image_file
from generation.services.model_strategy import model_family, tune_plan_for_image_model
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


def _update_assistant_message_after_plan(
    job: GenerationJob,
    plan: dict,
    *,
    awaiting_confirm: bool = False,
) -> None:
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
    need_confirm = bool(awaiting_confirm or plan.get("awaiting_generation_confirm"))
    if need_confirm:
        if summary:
            msg.content = (
                summary
                + "\n\n——\n确认策划无误后，点击下方 **「开始生图」**，或 **「仅优化卖点」** 后再生图。"
            )
        else:
            msg.content = f"已完成 {job.image_count} 条 Listing 主图策划，请确认后开始生图。"
    else:
        concept = (plan.get("creative_concept_label_zh") or plan.get("creative_concept_id") or "").strip()
        if concept:
            msg.content = (
                f"已采用套图创意「{concept}」，共 {job.image_count} 张，正在直接生图（未展开策划预览）…"
            )
        else:
            msg.content = f"策划已完成，共 {job.image_count} 张，正在直接生图…"
    meta = dict(msg.metadata or {})
    meta["generation_phase"] = "planned"
    meta["image_count"] = job.image_count
    meta["plan_ready"] = True
    meta["plan_preview_mode"] = need_confirm
    meta["awaiting_generation_confirm"] = need_confirm
    if summary:
        meta["planning_summary"] = summary
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
    plan = job.plan_json or {}
    awaiting = bool(plan.get("awaiting_generation_confirm")) and job.status == GenerationJob.Status.PENDING
    meta["awaiting_generation_confirm"] = awaiting
    meta["plan_preview_mode"] = awaiting
    if not awaiting:
        meta.pop("planning_summary", None)
        meta.pop("plan_ready", None)
    msg.metadata = meta
    msg.save(update_fields=["content", "metadata"])


def _resolve_reference_attachment(job, shot, plan, image_model):
    use_ref = shot_uses_reference(shot, plan)
    if not use_ref:
        return None
    return job.reference_attachment if use_ref else None


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

    from generation.services.model_strategy import resolve_reference_purpose

    ref_purpose = resolve_reference_purpose(shot, plan)

    def _call(p, attachment, ref_images=None):
        if ref_images:
            return generate_image_file(
                p,
                index,
                job.id,
                reference_images=ref_images,
                aspect_ratio=aspect_ratio,
                image_model=image_model,
                reference_purpose=ref_purpose,
            )
        return generate_image_file(
            p,
            index,
            job.id,
            reference_attachment=attachment,
            aspect_ratio=aspect_ratio,
            image_model=image_model,
            reference_purpose=ref_purpose,
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


def _remember_open_relay_task(open_tasks: dict, index: int, exc: BaseException) -> None:
    task_id = getattr(exc, "task_id", "") or ""
    image_url = getattr(exc, "image_url", "") or ""
    if task_id or image_url:
        open_tasks[index] = {"task_id": task_id, "image_url": image_url}


def _save_generated_bytes(job, gen_img, raw: bytes, index: int) -> None:
    from django.core.files.base import ContentFile

    from Intelligent_agent.media_store import save_image_field

    content_file = ContentFile(raw, name=f"job{job.id}_{index}.png")
    save_image_field(gen_img.file, content_file.name, content_file)
    gen_img.status = GeneratedImage.Status.SUCCEEDED
    gen_img.error_message = ""
    gen_img.save()
    job.completed_count = job.images.filter(status=GeneratedImage.Status.SUCCEEDED).count()
    job.save(update_fields=["completed_count"])
    _update_assistant_message(job)


def _recover_deferred_timeout_shots(
    job,
    shots,
    plan,
    aspect_fn,
    image_model,
    deferred_timeouts: dict,
    open_tasks: dict,
) -> None:
    """第 9 张跑完后：只回收 1–7 因本地轮询超时挂起的中转站任务。"""
    if not deferred_timeouts:
        return
    from generation.services.grsai import recover_deferred_task_bytes

    by_index = {int(s.get("index") or 0): s for s in shots}
    for index in sorted(list(deferred_timeouts.keys())):
        if index > 7:
            deferred_timeouts.pop(index, None)
            continue
        info = deferred_timeouts.pop(index)
        task_id = (info.get("task_id") or "").strip()
        if not task_id:
            continue
        gen_img = job.images.filter(index=index).first()
        if not gen_img or (gen_img.status == GeneratedImage.Status.SUCCEEDED and gen_img.file):
            continue
        logger.info("job=%s recover deferred timeout shot=%s task=%s", job.id, index, task_id)
        gen_img.status = GeneratedImage.Status.RUNNING
        gen_img.error_message = ""
        gen_img.save(update_fields=["status", "error_message"])
        try:
            raw = recover_deferred_task_bytes(
                task_id,
                image_url=info.get("image_url") or "",
                model=image_model,
            )
            _save_generated_bytes(job, gen_img, raw, index)
            continue
        except Exception as exc:
            logger.warning(
                "job=%s deferred recover failed shot=%s task=%s: %s",
                job.id,
                index,
                task_id,
                exc,
            )
        shot = by_index.get(index)
        if not shot:
            gen_img.status = GeneratedImage.Status.FAILED
            gen_img.error_message = "超时回收失败且缺少镜头策划"
            gen_img.save(update_fields=["status", "error_message"])
            continue
        _run_one_shot(
            job,
            shot,
            plan,
            aspect_fn(shot),
            image_model,
            open_tasks,
            deferred_timeouts=None,
            allow_defer_timeout=False,
        )


def _run_one_shot(
    job,
    shot,
    plan,
    aspect_ratio,
    image_model,
    open_tasks: dict | None = None,
    deferred_timeouts: dict | None = None,
    allow_defer_timeout: bool = True,
) -> tuple[bool, str]:
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
        if open_tasks is not None:
            open_tasks.pop(index, None)
        return True, ""

    pending = (open_tasks or {}).get(index) or {}
    if pending.get("task_id") or pending.get("image_url"):
        from generation.services.grsai import fetch_submitted_image

        gen_img.status = GeneratedImage.Status.RUNNING
        gen_img.error_message = ""
        gen_img.save(update_fields=["status", "error_message"])
        try:
            raw = fetch_submitted_image(
                pending.get("task_id") or "",
                image_url=pending.get("image_url") or "",
                model=image_model,
                max_seconds=120,
            )
            _save_generated_bytes(job, gen_img, raw, index)
            if open_tasks is not None:
                open_tasks.pop(index, None)
            return True, ""
        except Exception as exc:
            if open_tasks is not None:
                _remember_open_relay_task(open_tasks, index, exc)
            gen_img.status = GeneratedImage.Status.FAILED
            gen_img.error_message = str(exc)
            gen_img.save(update_fields=["status", "error_message"])
            _update_assistant_message(job)
            return False, str(exc)

    job.refresh_from_db(fields=["cancel_requested", "status"])
    if job.cancel_requested or job.status == GenerationJob.Status.CANCELLED:
        return False, "用户已取消任务"

    gen_img.status = GeneratedImage.Status.RUNNING
    gen_img.error_message = ""
    gen_img.save(update_fields=["status", "error_message"])

    from generation.services.job_references import reference_image_payloads_for_shot

    ref_att = _resolve_reference_attachment(job, shot, plan, image_model)
    if shot_uses_reference(shot, plan):
        ref_payloads = reference_image_payloads_for_shot(job, shot)
    else:
        ref_payloads = []
    use_multi = len(ref_payloads) > 0
    if index == 4 and (plan.get("plan_template") or "") == "tk_mx_ecommerce_9":
        from generation.services.listing_frame4_contract import apply_frame4_comparison_contract

        plan = apply_frame4_comparison_contract(plan)
        for s in plan.get("shots") or []:
            if int(s.get("index") or 0) == 4:
                shot = s
                break
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
        from Intelligent_agent.media_store import save_image_field

        save_image_field(gen_img.file, content_file.name, content_file)
        gen_img.status = GeneratedImage.Status.SUCCEEDED
        gen_img.error_message = ""
        gen_img.save()
        job.completed_count = job.images.filter(
            status=GeneratedImage.Status.SUCCEEDED
        ).count()
        job.save(update_fields=["completed_count"])
        _update_assistant_message(job)
        if open_tasks is not None:
            open_tasks.pop(index, None)
        return True, ""
    except Exception as exc:
        err = str(exc)
        from generation.services.grsai import (
            GrsaiRemoteTaskError,
            is_deferrable_shot_index,
            is_per_shot_poll_timeout,
        )

        task_id = getattr(exc, "task_id", "") or ""
        if (
            allow_defer_timeout
            and deferred_timeouts is not None
            and is_deferrable_shot_index(index)
            and is_per_shot_poll_timeout(exc)
            and task_id
        ):
            deferred_timeouts[index] = {
                "task_id": task_id,
                "image_url": getattr(exc, "image_url", "") or "",
            }
            gen_img.status = GeneratedImage.Status.FAILED
            gen_img.error_message = f"单张超时待回收 task={task_id}"
            gen_img.save(update_fields=["status", "error_message"])
            _update_assistant_message(job)
            logger.info(
                "job=%s shot=%s poll timeout — defer task=%s, continue pipeline",
                job.id,
                index,
                task_id,
            )
            return False, err
        if open_tasks is not None and not (
            isinstance(exc, GrsaiRemoteTaskError) and is_per_shot_poll_timeout(exc)
        ):
            _remember_open_relay_task(open_tasks, index, exc)
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

    job.refresh_from_db(fields=["cancel_requested", "status"])
    if job.cancel_requested or job.status == GenerationJob.Status.CANCELLED:
        job.status = GenerationJob.Status.CANCELLED
        if not job.finished_at:
            job.finished_at = timezone.now()
        job.save(update_fields=["status", "finished_at"])
        dispatch_next_for_user(job.user_id)
        return

    if not job.started_at:
        job.started_at = timezone.now()
        job.status = GenerationJob.Status.RUNNING
        job.save(update_fields=["started_at", "status"])
        _update_assistant_message(job)

    plan = job.plan_json or {}
    from generation.services.listing_bundle import is_listing_ecommerce_plan
    from generation.services.listing_run_prepare import prepare_listing_plan_for_generation

    if is_listing_ecommerce_plan(plan):
        plan = prepare_listing_plan_for_generation(plan, job=job)
    image_model = plan.get("image_model") or None
    has_ref = bool(job.reference_attachment_id) or bool(job.reference_attachment_ids)
    if plan.get("shots"):
        plan = tune_plan_for_image_model(plan, image_model, has_reference=has_ref)
        if is_listing_ecommerce_plan(plan):
            from generation.services.product_usage_semantics import finalize_frame4_product_truth

            plan = finalize_frame4_product_truth(plan)
        job.plan_json = plan
        job.save(update_fields=["plan_json"])

    shots = normalize_shot_list(
        plan.get("shots") or [],
        job.image_count,
        job.prompt,
    )
    shots = sorted(shots, key=lambda s: int(s.get("index") or 0))
    aspect_ratio = plan.get("aspect_ratio", "1:1")

    def _aspect_for_shot(shot: dict) -> str:
        try:
            idx = int(shot.get("index") or 0)
        except (TypeError, ValueError):
            idx = 0
        from generation.services.listing_bundle import is_listing_ecommerce_plan

        from generation.services.aspect_ratio import is_square_aspect

        if (
            idx == 1
            and is_listing_ecommerce_plan(plan)
            and is_square_aspect(aspect_ratio)
        ):
            px = shot.get("hero_output_size") or plan.get("tk_mx_hero_output_pixels")
            if px:
                try:
                    px = int(px)
                    return f"{px}x{px}"
                except (TypeError, ValueError):
                    pass
        return aspect_ratio
    failed_count = 0
    last_error = ""
    open_tasks: dict[int, dict] = {}
    deferred_timeouts: dict[int, dict] = {}

    for shot in shots:
        if job.cancel_requested:
            break
        job.refresh_from_db(fields=["cancel_requested"])
        if job.cancel_requested:
            break
        ok, err = _run_one_shot(
            job,
            shot,
            plan,
            _aspect_for_shot(shot),
            image_model,
            open_tasks,
            deferred_timeouts,
        )
        if not ok:
            idx = int(shot.get("index") or 0)
            if idx not in deferred_timeouts:
                failed_count += 1
            last_error = err or last_error

    if deferred_timeouts and not job.cancel_requested:
        _recover_deferred_timeout_shots(
            job,
            shots,
            plan,
            _aspect_for_shot,
            image_model,
            deferred_timeouts,
            open_tasks,
        )
        job.refresh_from_db(fields=["completed_count"])
        failed_count = job.images.filter(status=GeneratedImage.Status.FAILED).count()

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
        failed_indices -= set(deferred_timeouts.keys())
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
            ok, err = _run_one_shot(
                job,
                shot,
                plan,
                _aspect_for_shot(shot),
                image_model,
                open_tasks,
                deferred_timeouts,
                allow_defer_timeout=False,
            )
            if ok:
                failed_count = max(0, failed_count - 1)
            elif err:
                last_error = err
            from Intelligent_agent.media_store import is_object_storage_unavailable

            if is_object_storage_unavailable(Exception(err or last_error)):
                logger.warning("job=%s 对象存储不可用，停止整套重试", job.id)
                break
        if is_object_storage_unavailable(Exception(last_error)):
            break
        if not job.images.filter(status=GeneratedImage.Status.FAILED).exists():
            break

    if job.cancel_requested:
        job.status = GenerationJob.Status.CANCELLED
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "finished_at"])
        dispatch_next_for_user(job.user_id)
        return

    for img in job.images.filter(status=GeneratedImage.Status.RUNNING):
        if img.file:
            img.status = GeneratedImage.Status.SUCCEEDED
            img.error_message = ""
            img.save(update_fields=["status", "error_message"])
        else:
            img.status = GeneratedImage.Status.FAILED
            img.error_message = img.error_message or "生成未完成（worker 中断）"
            img.save(update_fields=["status", "error_message"])
    for img in job.images.filter(status=GeneratedImage.Status.FAILED):
        if img.file:
            img.status = GeneratedImage.Status.SUCCEEDED
            img.error_message = ""
            img.save(update_fields=["status", "error_message"])

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
    job.refresh_from_db()
    job.completed_count = job.images.filter(status=GeneratedImage.Status.SUCCEEDED).count()
    if job.completed_count >= job.image_count and job.status == GenerationJob.Status.SUCCEEDED:
        job.error_message = ""
        job.save(update_fields=["completed_count", "error_message"])
    _update_assistant_message(job)
    dispatch_next_for_user(job.user_id)


@shared_task(bind=True, max_retries=0)
def run_slot_refine_task(self, candidate_id: int):
    from generation.services.slot_refine import run_slot_refine_candidate

    run_slot_refine_candidate(candidate_id)
