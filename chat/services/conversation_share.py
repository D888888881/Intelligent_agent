from __future__ import annotations

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from accounts.models import UserProfile
from chat.models import Conversation, Message
from uploads.models import Attachment


def sharer_display_name(user: User) -> str:
    profile = UserProfile.objects.filter(user=user).first()
    if profile and (profile.real_name or "").strip():
        return profile.real_name.strip()
    return user.username


def generation_job_snapshot_for_user(job_id: int, owner_id: int, request=None) -> dict | None:
    from generation.models import GenerationJob

    job = (
        GenerationJob.objects.filter(pk=job_id, user_id=owner_id)
        .prefetch_related("images")
        .first()
    )
    if not job:
        return None
    images = []
    for img in job.images.all().order_by("index"):
        if not img.file:
            continue
        url = img.file.url
        if request:
            url = request.build_absolute_uri(url)
        images.append(
            {
                "index": img.index,
                "url": url,
                "status": img.status,
                "prompt": img.prompt,
            }
        )
    return {
        "image_count": job.image_count,
        "status": job.status,
        "completed_count": job.completed_count,
        "images": images,
    }


def _snapshot_message_metadata(metadata: dict | None, sharer: User, request) -> dict:
    meta = dict(metadata or {})
    job_id = meta.get("generation_job_id")
    if job_id and not meta.get("generation_snapshot"):
        snap = generation_job_snapshot_for_user(int(job_id), sharer.id, request)
        if snap:
            meta["generation_snapshot"] = snap
            meta.pop("generation_job_id", None)
            meta.pop("generation_phase", None)
    ids = meta.get("attachment_ids") or []
    if ids and not meta.get("attachments"):
        attachments = []
        for att in Attachment.objects.filter(id__in=ids, user_id=sharer.id):
            url = att.file.url
            if request:
                url = request.build_absolute_uri(url)
            attachments.append(
                {
                    "id": att.id,
                    "url": url,
                    "name": att.original_name,
                }
            )
        if attachments:
            meta["attachments"] = attachments
    return meta


@transaction.atomic
def clone_conversation_for_share(
    source: Conversation,
    *,
    recipient: User,
    sharer: User,
    request=None,
) -> Conversation:
    label = sharer_display_name(sharer)
    now = timezone.now()
    target = Conversation.objects.create(
        user=recipient,
        title=source.title,
        summary=source.summary,
        shared_by=sharer,
        shared_by_label=label,
        shared_at=now,
        updated_at=now,
    )
    messages = Message.objects.filter(conversation=source).order_by("created_at")
    to_create = []
    for msg in messages:
        to_create.append(
            Message(
                conversation=target,
                role=msg.role,
                content=msg.content,
                metadata=_snapshot_message_metadata(msg.metadata, sharer, request),
                created_at=msg.created_at,
            )
        )
    if to_create:
        Message.objects.bulk_create(to_create)
    return target
