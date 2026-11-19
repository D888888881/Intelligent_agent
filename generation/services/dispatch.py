import logging

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from generation.models import GenerationJob

logger = logging.getLogger(__name__)


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
        if user_has_running_job(job.user_id, exclude_job_id=job.id):
            job.status = GenerationJob.Status.QUEUED
            job.save(update_fields=["status"])
            return "queued"
        job.status = GenerationJob.Status.RUNNING
        plan = dict(job.plan_json or {})
        plan["_dispatched_at"] = timezone.now().isoformat()
        job.plan_json = plan
        job.save(update_fields=["status", "plan_json"])

    from generation.tasks import run_generation_job

    _dispatch_task(run_generation_job, job.id)
    return "running"


def _celery_workers_responding() -> bool:
    """Broker 可达但无 worker 时 delay 会入队却永不执行，需回退到进程内线程。"""
    try:
        from celery import current_app

        inspect = current_app.control.inspect(timeout=0.8)
        if inspect is None:
            return False
        ping = inspect.ping()
        return bool(ping)
    except Exception:
        return False


def _image_queue_has_consumer() -> bool:
    """run_generation_job 路由到 image 队列；默认 celery worker 不消费该队列。"""
    try:
        from celery import current_app

        inspect = current_app.control.inspect(timeout=1.0)
        if inspect is None:
            return False
        active_queues = inspect.active_queues()
        if not active_queues:
            return False
        for worker_queues in active_queues.values():
            if not worker_queues:
                continue
            for q in worker_queues:
                if not isinstance(q, dict):
                    continue
                if q.get("name") == "image":
                    return True
        return False
    except Exception:
        return False


def _use_inprocess_generation_dispatch(*, prefer_inprocess: bool = False) -> bool:
    if prefer_inprocess or settings.CELERY_TASK_ALWAYS_EAGER:
        return True
    if getattr(settings, "GEN_FORCE_INPROCESS_DISPATCH", False):
        return True
    if not _celery_workers_responding():
        return True
    if not _image_queue_has_consumer():
        return True
    return False


def _dispatch_task(task, job_id: int, *, prefer_inprocess: bool = False):
    """开发环境 eager 时在后台线程执行，避免阻塞 HTTP 请求。"""

    def _run_in_thread():
        import threading

        def _run():
            try:
                task.apply(args=(job_id,))
            except Exception:
                logger.exception("in-process generation task failed job=%s", job_id)

        threading.Thread(target=_run, daemon=True).start()

    if _use_inprocess_generation_dispatch(prefer_inprocess=prefer_inprocess):
        if not (prefer_inprocess or settings.CELERY_TASK_ALWAYS_EAGER):
            logger.warning(
                "run_generation_job in-process for job=%s "
                "(no image-queue worker or Celery unavailable)",
                job_id,
            )
        _run_in_thread()
        return
    try:
        task.delay(job_id)
    except Exception as exc:
        logger.warning(
            "Celery delay failed job=%s (%s), fallback to in-process thread",
            job_id,
            exc,
        )
        _run_in_thread()


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
