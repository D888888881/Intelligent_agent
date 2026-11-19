from rest_framework import serializers

from Intelligent_agent.media_urls import resolve_media_file_url

from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ("id", "role", "content", "metadata", "created_at")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        meta = dict(data.get("metadata") or {})
        if meta.get("attachment_ids"):
            request = self.context.get("request")
            user_id = instance.conversation.user_id
            from uploads.models import Attachment

            attachments = []
            for att in Attachment.objects.filter(
                id__in=meta["attachment_ids"],
                user_id=user_id,
            ):
                url = resolve_media_file_url(att.file, request)
                attachments.append(
                    {
                        "id": att.id,
                        "url": url,
                        "name": att.original_name,
                    }
                )
            if attachments:
                meta["attachments"] = attachments
                data["metadata"] = meta
        job_id = meta.get("generation_job_id")
        if job_id and instance.role == Message.Role.ASSISTANT:
            from generation.models import GenerationJob
            from generation.services.dispatch import queue_position
            from generation.tasks import _assistant_status_text

            conv = instance.conversation
            job = GenerationJob.objects.filter(
                pk=int(job_id), conversation_id=conv.id
            ).first()
            if not job and conv.shared_by_id:
                job = GenerationJob.objects.filter(
                    pk=int(job_id), user_id=conv.shared_by_id
                ).first()

            if job:
                from generation.services.job_recovery import refresh_generation_job_state

                job = refresh_generation_job_state(job)
                data["content"] = _assistant_status_text(job)
                meta["generation_phase"] = job.status
                meta["completed_count"] = job.completed_count
                meta["image_count"] = job.image_count
                plan = job.plan_json or {}
                awaiting = bool(plan.get("awaiting_generation_confirm")) and (
                    job.status == GenerationJob.Status.PENDING
                )
                meta["awaiting_generation_confirm"] = awaiting
                meta["plan_preview_mode"] = awaiting
                if job.status == GenerationJob.Status.QUEUED:
                    qp = queue_position(job)
                    if qp is not None:
                        meta["queue_position"] = qp
                else:
                    meta.pop("queue_position", None)

                # 仅分享会话嵌入静态 snapshot；本人的任务始终走 generation_job_id 轮询（含下载、局部修复）
                if conv.shared_by_id:
                    from chat.services.conversation_share import (
                        generation_job_snapshot_for_user,
                    )

                    owner_id = job.user_id
                    snap = generation_job_snapshot_for_user(
                        job.id, owner_id, self.context.get("request")
                    )
                    if snap:
                        meta["generation_snapshot"] = snap
                else:
                    meta.pop("generation_snapshot", None)

                data["metadata"] = meta
        return data


class ConversationSerializer(serializers.ModelSerializer):
    shared_by_label = serializers.CharField(read_only=True)
    is_shared = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = (
            "id",
            "title",
            "summary",
            "pinned_at",
            "marketplace_id",
            "created_at",
            "updated_at",
            "shared_by_label",
            "is_shared",
        )

    def get_is_shared(self, obj) -> bool:
        return bool(obj.shared_by_id)


class ConversationDetailSerializer(serializers.ModelSerializer):
    messages = serializers.SerializerMethodField()
    message_pagination = serializers.SerializerMethodField()
    shared_by_label = serializers.CharField(read_only=True)
    is_shared = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = (
            "id",
            "title",
            "summary",
            "pinned_at",
            "marketplace_id",
            "created_at",
            "updated_at",
            "shared_by_label",
            "is_shared",
            "messages",
            "message_pagination",
        )

    def get_messages(self, obj):
        page = self.context.get("message_page")
        if page is None:
            return []
        return MessageSerializer(page["messages"], many=True).data

    def get_is_shared(self, obj) -> bool:
        return bool(obj.shared_by_id)

    def get_message_pagination(self, obj):
        page = self.context.get("message_page")
        if not page:
            return {
                "has_more_older": False,
                "oldest_message_id": None,
                "newest_message_id": None,
                "limit": 0,
            }
        return {
            "has_more_older": page["has_more_older"],
            "oldest_message_id": page["oldest_message_id"],
            "newest_message_id": page["newest_message_id"],
            "limit": page["limit"],
        }
