"""生图任务与单镜状态对齐：修复 worker 中断后残留的 running。"""

from __future__ import annotations

import logging

from django.utils import timezone

from generation.models import GeneratedImage, GenerationJob

logger = logging.getLogger(__name__)


def _stall_seconds(job: GenerationJob) -> float:
    """只在 worker 真正消失很久后才收束。不能用整单已用时间去判末镜失败。"""
    del job
    return 3600.0


def _promote_running_with_file(job: GenerationJob) -> int:
    fixed = 0
    for img in job.images.filter(status=GeneratedImage.Status.RUNNING):
        if img.file:
            img.status = GeneratedImage.Status.SUCCEEDED
            img.error_message = ""
            img.save(update_fields=["status", "error_message"])
            fixed += 1
    if fixed:
        logger.info("job=%s promoted %s RUNNING->SUCCEEDED (file present)", job.id, fixed)
    return fixed


def _promote_failed_with_file(job: GenerationJob) -> int:
    """中转站已成功但状态未及时写入时，刷新/轮询应对齐。"""
    fixed = 0
    for img in job.images.filter(status=GeneratedImage.Status.FAILED):
        if img.file:
            img.status = GeneratedImage.Status.SUCCEEDED
            img.error_message = ""
            img.save(update_fields=["status", "error_message"])
            fixed += 1
    if fixed:
        logger.info("job=%s promoted %s FAILED->SUCCEEDED (file present)", job.id, fixed)
    return fixed


def _fail_stale_running(job: GenerationJob, *, reason: str) -> int:
    age = timezone.now() - (job.started_at or job.created_at)
    if age.total_seconds() < _stall_seconds(job):
        return 0
    failed = 0
    for img in job.images.filter(status=GeneratedImage.Status.RUNNING):
        if img.file:
            continue
        img.status = GeneratedImage.Status.FAILED
        img.error_message = reason
        img.save(update_fields=["status", "error_message"])
        failed += 1
    if failed:
        logger.warning("job=%s marked %s stale RUNNING as FAILED", job.id, failed)
    return failed


def _finalize_running_job_if_idle(job: GenerationJob) -> bool:
    """无进行中的镜头时收束任务（worker 未执行收尾时）。"""
    if job.status != GenerationJob.Status.RUNNING:
        return False
    if job.images.filter(
        status__in=(GeneratedImage.Status.RUNNING, GeneratedImage.Status.PENDING)
    ).exists():
        return False

    succeeded = job.images.filter(status=GeneratedImage.Status.SUCCEEDED).count()
    failed = job.images.filter(status=GeneratedImage.Status.FAILED).count()
    job.completed_count = succeeded
    job.finished_at = timezone.now()

    if succeeded <= 0:
        job.status = GenerationJob.Status.FAILED
        if not job.error_message:
            job.error_message = "全部镜头生成失败"
    else:
        job.status = GenerationJob.Status.SUCCEEDED
        if failed > 0:
            job.error_message = f"{failed} 张失败"
        elif not job.error_message:
            job.error_message = ""

    job.save(
        update_fields=["status", "completed_count", "error_message", "finished_at"]
    )
    from generation.tasks import _update_assistant_message

    _update_assistant_message(job)
    from generation.services.dispatch import dispatch_next_for_user

    dispatch_next_for_user(job.user_id)
    logger.info(
        "job=%s finalized via reconcile succeeded=%s failed=%s",
        job.id,
        succeeded,
        failed,
    )
    return True


def reconcile_generation_job(job: GenerationJob) -> GenerationJob:
    """读取/轮询时修复卡住单镜并尝试收束整单。"""
    job = GenerationJob.objects.select_related("conversation").get(pk=job.pk)

    _promote_running_with_file(job)
    _promote_failed_with_file(job)

    terminal = job.status in (
        GenerationJob.Status.SUCCEEDED,
        GenerationJob.Status.FAILED,
        GenerationJob.Status.CANCELLED,
    )
    if terminal:
        grace_s = 600.0
        finished = job.finished_at
        age = (timezone.now() - finished).total_seconds() if finished else 0.0
        for img in job.images.filter(status=GeneratedImage.Status.RUNNING):
            if img.file:
                img.status = GeneratedImage.Status.SUCCEEDED
                img.error_message = ""
                img.save(update_fields=["status", "error_message"])
            elif age >= grace_s:
                img.status = GeneratedImage.Status.FAILED
                img.error_message = img.error_message or "任务已结束但该镜未落盘"
                img.save(update_fields=["status", "error_message"])
        new_count = job.images.filter(status=GeneratedImage.Status.SUCCEEDED).count()
        if new_count != job.completed_count:
            job.completed_count = new_count
            job.save(update_fields=["completed_count"])
        return job

    _fail_stale_running(
        job,
        reason="单镜超时或 worker 中断（可对该镜做局部重试）",
    )
    _finalize_running_job_if_idle(job)
    job.refresh_from_db()
    new_count = job.images.filter(status=GeneratedImage.Status.SUCCEEDED).count()
    if new_count != job.completed_count:
        job.completed_count = new_count
        job.save(update_fields=["completed_count"])
    return job