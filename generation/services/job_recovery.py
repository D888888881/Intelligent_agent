"""生图任务卡住检测：RUNNING 但 worker 未真正启动时自动重试派发。"""

import logging

from django.utils import timezone

from generation.models import GenerationJob

logger = logging.getLogger(__name__)


def refresh_generation_job_state(job: GenerationJob) -> GenerationJob:
    """派发恢复 + 单镜/整单状态对齐。"""
    job = maybe_recover_stuck_generation_job(job)
    from generation.services.job_reconcile import reconcile_generation_job

    return reconcile_generation_job(job)

_REDISPATCH_GRACE_SECONDS = 20
_MAX_REDISPATCH = 2


def maybe_recover_stuck_generation_job(job: GenerationJob) -> GenerationJob:
    """
    若任务已标记 RUNNING、策划已完成，但 run_generation_job 从未设置 started_at，
    则尝试重新派发（常见于 Celery 未启动或首次 delay 丢失）。
    """
    if job.status != GenerationJob.Status.RUNNING:
        return job
    if job.cancel_requested:
        return job
    if job.started_at:
        return job

    plan = job.plan_json or {}
    if plan.get("awaiting_generation_confirm"):
        return job
    shots = plan.get("shots") or []
    if not shots:
        return job

    from django.utils.dateparse import parse_datetime

    dispatched_raw = plan.get("_dispatched_at")
    ref = job.updated_at
    if dispatched_raw:
        dt = parse_datetime(dispatched_raw)
        if dt:
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.get_current_timezone())
            ref = dt
    age = (timezone.now() - ref).total_seconds()
    if age < _REDISPATCH_GRACE_SECONDS:
        return job

    attempts = int(plan.get("_dispatch_recovery") or 0)
    if attempts >= _MAX_REDISPATCH:
        job.status = GenerationJob.Status.FAILED
        job.error_message = (
            "生图 worker 未响应（.env 设 CELERY_TASK_ALWAYS_EAGER=True 后重启 Django；"
            "或运行 celery worker -Q image；或 GEN_FORCE_INPROCESS_DISPATCH=True）"
        )
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "error_message", "finished_at"])
        from generation.tasks import _update_assistant_message

        _update_assistant_message(job)
        from generation.services.dispatch import dispatch_next_for_user

        dispatch_next_for_user(job.user_id)
        logger.error("job=%s dispatch recovery exhausted, marked FAILED", job.id)
        return job

    plan = dict(plan)
    plan["_dispatch_recovery"] = attempts + 1
    job.plan_json = plan
    job.save(update_fields=["plan_json"])

    from generation.services.dispatch import _dispatch_task
    from generation.tasks import run_generation_job

    _dispatch_task(run_generation_job, job.id, prefer_inprocess=True)

    logger.warning(
        "job=%s redispatch run_generation_job attempt=%s age=%.0fs",
        job.id,
        attempts + 1,
        age,
    )
    return job
