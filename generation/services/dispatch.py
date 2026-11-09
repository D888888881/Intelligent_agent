from django.conf import settings
from django.db import transaction
from django.db.models import Q

from generation.models import GenerationJob


def count_global_queued() -> int:
    return GenerationJob.objects.filter(
        status__in=[GenerationJob.Status.PENDING, GenerationJob.Status.QUEUED]
    ).count()


def user_has_running_job(user_id: int, exclude_job_id: int | None = None) -> bool:
    qs = GenerationJob.objects.filter(
        user_id=user_id,
        status=GenerationJob.Status.RUNNING,
    )
    if exclude_job_id:
        qs = qs.exclude(pk=exclude_job_id)
    return qs.exists()


def enqueue_or_run(job: GenerationJob) -> str:
    """
    每用户同时仅一个 RUNNING；否则标记 QUEUED。
    返回 queued | running
    """
    if count_global_queued() > settings.GEN_MAX_QUEUE_SIZE:
        job.status = GenerationJob.Status.FAILED
        job.error_message = "系统队列已满，请稍后再试"
        job.save(update_fields=["status", "error_message"])
        return "failed"

    with transaction.atomic():
        job = GenerationJob.objects.select_for_update().get(pk=job.pk)
        if user_has_running_job(job.user_id):
            job.status = GenerationJob.Status.QUEUED
            job.save(update_fields=["status"])
            return "queued"
        job.status = GenerationJob.Status.RUNNING
        job.save(update_fields=["status"])

    from generation.tasks import run_generation_job

    _dispatch_task(run_generation_job, job.id)
    return "running"


def _dispatch_task(task, job_id: int):
    """开发环境 eager 时在后台线程执行，避免阻塞 HTTP 请求。"""
    if settings.CELERY_TASK_ALWAYS_EAGER:
        import threading

        threading.Thread(
            target=lambda: task.apply(args=(job_id,)),
            daemon=True,
        ).start()
    else:
        task.delay(job_id)


def dispatch_next_for_user(user_id: int):
    if user_has_running_job(user_id):
        return
    next_job = (
        GenerationJob.objects.filter(
            user_id=user_id,
            status=GenerationJob.Status.QUEUED,
        )
        .order_by("created_at")
        .first()
    )
    if not next_job:
        return
    next_job.status = GenerationJob.Status.RUNNING
    next_job.save(update_fields=["status"])
    from generation.tasks import run_generation_job

    _dispatch_task(run_generation_job, next_job.id)


def queue_position(job: GenerationJob) -> int | None:
    if job.status != GenerationJob.Status.QUEUED:
        return None
    ahead = (
        GenerationJob.objects.filter(status=GenerationJob.Status.QUEUED)
        .filter(
            Q(created_at__lt=job.created_at)
            | Q(created_at=job.created_at, pk__lt=job.pk)
        )
        .count()
    )
    return ahead + 1
