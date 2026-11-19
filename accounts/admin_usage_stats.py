"""超级管理员：按日/周/月汇总用户套图任务、成图张数、模型用量。"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any

from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.utils import timezone

from generation.models import GeneratedImage, GenerationJob, SlotRefineCandidate
from Intelligent_agent.model_catalog import resolve_image_model


def _label_for_model(model_id: str, *, model_labels: dict[str, str]) -> str:
    mid = (model_id or "").strip() or "unknown"
    return model_labels.get(mid) or mid


def _resolve_image_model_key(plan: dict | None) -> str:
    plan = plan or {}
    mid = (plan.get("image_model") or "").strip()
    if not mid:
        return resolve_image_model(None)
    return resolve_image_model(mid)


def compute_time_range(period: str, anchor: date | None = None) -> tuple[datetime, datetime, str]:
    """返回 [start, end) 半开区间（timezone-aware，本地日历）。"""
    period = (period or "day").strip().lower()
    if period not in ("day", "week", "month"):
        period = "day"

    tz = timezone.get_current_timezone()
    if anchor is None:
        anchor = timezone.localdate()
    day_start = timezone.make_aware(datetime.combine(anchor, time.min), tz)

    if period == "day":
        start = day_start
        end = start + timedelta(days=1)
        label = anchor.isoformat()
    elif period == "week":
        # 周一为一周起点
        weekday = anchor.weekday()
        week_monday = anchor - timedelta(days=weekday)
        start = timezone.make_aware(datetime.combine(week_monday, time.min), tz)
        end = start + timedelta(days=7)
        label = f"{week_monday.isoformat()} ~ {(week_monday + timedelta(days=6)).isoformat()}"
    else:
        month_start = anchor.replace(day=1)
        start = timezone.make_aware(datetime.combine(month_start, time.min), tz)
        if month_start.month == 12:
            next_month = month_start.replace(year=month_start.year + 1, month=1)
        else:
            next_month = month_start.replace(month=month_start.month + 1)
        end = timezone.make_aware(datetime.combine(next_month, time.min), tz)
        label = month_start.strftime("%Y-%m")

    return start, end, label


def build_model_labels() -> dict[str, str]:
    from Intelligent_agent.model_catalog import CHAT_MODELS, IMAGE_MODELS, VISION_MODELS

    labels: dict[str, str] = {}
    for row in IMAGE_MODELS + VISION_MODELS + CHAT_MODELS:
        labels[row["id"]] = row.get("label") or row["id"]
    return labels


def compute_admin_usage_stats(
    *,
    period: str = "day",
    anchor: date | None = None,
    q: str = "",
    page: int = 1,
    page_size: int = 20,
    include_superusers: bool = True,
) -> dict[str, Any]:
    start, end, range_label = compute_time_range(period, anchor)
    model_labels = build_model_labels()

    user_qs = User.objects.select_related("profile").order_by("username")
    if q:
        user_qs = user_qs.filter(Q(username__icontains=q) | Q(profile__real_name__icontains=q))
    if not include_superusers:
        user_qs = user_qs.filter(is_superuser=False)

    scoped_user_ids = list(user_qs.values_list("id", flat=True))

    job_filter = Q(created_at__gte=start, created_at__lt=end)
    if scoped_user_ids:
        job_filter &= Q(user_id__in=scoped_user_ids)

    jobs_qs = GenerationJob.objects.filter(job_filter).only(
        "id", "user_id", "image_count", "completed_count", "status", "plan_json"
    )

    job_counts: dict[int, int] = defaultdict(int)
    images_from_job_counter: dict[int, int] = defaultdict(int)
    model_image_hits: dict[str, int] = defaultdict(int)
    model_job_hits: dict[str, int] = defaultdict(int)
    per_user_job_models: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    job_ids: list[int] = []
    for job in jobs_qs.iterator(chunk_size=200):
        job_ids.append(job.id)
        uid = job.user_id
        job_counts[uid] += 1
        mid = _resolve_image_model_key(job.plan_json)
        model_job_hits[mid] += 1
        per_user_job_models[uid][mid] += 1
        if job.status == GenerationJob.Status.SUCCEEDED:
            images_from_job_counter[uid] += int(job.completed_count or 0)

    img_qs = GeneratedImage.objects.filter(
        job_id__in=job_ids,
        status=GeneratedImage.Status.SUCCEEDED,
    ).select_related("job")
    image_counts: dict[int, int] = defaultdict(int)
    for row in img_qs.values("job__user_id").annotate(c=Count("id")):
        image_counts[row["job__user_id"]] = row["c"]

    # 以 GeneratedImage 成功数为准；若无记录则回退 job.completed_count
    for uid, cnt in images_from_job_counter.items():
        if image_counts.get(uid, 0) == 0 and cnt > 0:
            image_counts[uid] = cnt

    if job_ids:
        for img in img_qs.select_related("job").only("job_id", "job__plan_json").iterator(chunk_size=500):
            mid = _resolve_image_model_key(img.job.plan_json if img.job else {})
            model_image_hits[mid] += 1

    refine_q = SlotRefineCandidate.objects.filter(
        created_at__gte=start,
        created_at__lt=end,
        status__in=(SlotRefineCandidate.Status.SUCCEEDED, SlotRefineCandidate.Status.APPLIED),
    )
    if scoped_user_ids:
        refine_q = refine_q.filter(user_id__in=scoped_user_ids)
    refine_counts: dict[int, int] = defaultdict(int)
    refine_model_hits: dict[str, int] = defaultdict(int)
    per_user_refine_models: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in refine_q.values("user_id", "image_model"):
        refine_counts[row["user_id"]] += 1
        mid = (row["image_model"] or "").strip() or resolve_image_model(None)
        refine_model_hits[mid] += 1
        model_image_hits[mid] += 1
        per_user_refine_models[row["user_id"]][mid] += 1

    active_user_ids = set(job_counts) | set(image_counts) | set(refine_counts)

    if q:
        display_users = user_qs
    else:
        if not active_user_ids:
            display_users = User.objects.none()
        else:
            display_users = User.objects.filter(id__in=active_user_ids).select_related("profile").order_by(
                "username"
            )

    rows: list[dict[str, Any]] = []
    for user in display_users:
        uid = user.id
        profile = getattr(user, "profile", None)
        real_name = (profile.real_name if profile else "") or ""
        per_user_models: dict[str, int] = defaultdict(int)
        for mid, c in per_user_job_models.get(uid, {}).items():
            per_user_models[mid] += c
        for mid, c in per_user_refine_models.get(uid, {}).items():
            per_user_models[mid] += c

        model_breakdown = [
            {
                "model_id": mid,
                "label": _label_for_model(mid, model_labels=model_labels),
                "uses": per_user_models[mid],
            }
            for mid in sorted(per_user_models.keys(), key=lambda m: (-per_user_models[m], m))
        ]

        rows.append(
            {
                "user_id": uid,
                "username": user.username,
                "real_name": real_name,
                "is_superuser": user.is_superuser,
                "is_active": user.is_active,
                "job_count": job_counts.get(uid, 0),
                "images_succeeded": image_counts.get(uid, 0),
                "refine_images": refine_counts.get(uid, 0),
                "usage_count": job_counts.get(uid, 0) + refine_counts.get(uid, 0),
                "image_models": model_breakdown,
            }
        )

    rows.sort(key=lambda r: (-r["images_succeeded"], -r["job_count"], r["username"]))

    page_size = min(50, max(1, page_size))
    page = max(1, page)
    total_rows = len(rows)
    total_pages = max(1, (total_rows + page_size - 1) // page_size)
    if page > total_pages:
        page = total_pages
    offset = (page - 1) * page_size
    page_rows = rows[offset : offset + page_size]

    totals = {
        "users_with_activity": len(active_user_ids),
        "job_count": sum(job_counts.values()),
        "images_succeeded": sum(image_counts.values()),
        "refine_images": sum(refine_counts.values()),
        "usage_count": sum(job_counts.values()) + sum(refine_counts.values()),
    }

    model_totals = []
    all_model_ids = set(model_job_hits) | set(model_image_hits) | set(refine_model_hits)
    for mid in sorted(all_model_ids, key=lambda m: (-model_image_hits.get(m, 0), m)):
        model_totals.append(
            {
                "model_id": mid,
                "label": _label_for_model(mid, model_labels=model_labels),
                "job_count": model_job_hits.get(mid, 0),
                "image_generations": model_image_hits.get(mid, 0),
                "refine_generations": refine_model_hits.get(mid, 0),
            }
        )

    return {
        "period": period,
        "range_label": range_label,
        "range_start": start.isoformat(),
        "range_end": end.isoformat(),
        "timezone": str(settings.TIME_ZONE),
        "totals": totals,
        "model_totals": model_totals,
        "count": total_rows,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "results": page_rows,
    }
