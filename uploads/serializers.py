from rest_framework import serializers

from Intelligent_agent.media_urls import resolve_media_file_url

from .models import Attachment


class AttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = (
            "id",
            "url",
            "original_name",
            "mime_type",
            "width",
            "height",
            "created_at",
        )

    def get_url(self, obj):
        return resolve_media_file_url(obj.file, self.context.get("request"))
