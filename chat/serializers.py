from rest_framework import serializers

from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ("id", "role", "content", "metadata", "created_at")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        meta = dict(data.get("metadata") or {})
        if not meta.get("attachments") and meta.get("attachment_ids"):
            request = self.context.get("request")
            user_id = instance.conversation.user_id
            from uploads.models import Attachment

            attachments = []
            for att in Attachment.objects.filter(
                id__in=meta["attachment_ids"],
                user_id=user_id,
            ):
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
                data["metadata"] = meta
        if meta.get("generation_job_id") and not meta.get("generation_snapshot"):
            conv = instance.conversation
            if conv.shared_by_id:
                from chat.services.conversation_share import generation_job_snapshot_for_user

                snap = generation_job_snapshot_for_user(
                    int(meta["generation_job_id"]),
                    conv.shared_by_id,
                    self.context.get("request"),
                )
                if snap:
                    meta["generation_snapshot"] = snap
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
