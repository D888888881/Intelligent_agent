from django.conf import settings
from rest_framework import serializers

from Intelligent_agent.media_urls import resolve_media_file_url

from generation.models import GeneratedImage, GenerationJob, SlotRefineCandidate


class GeneratedImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = GeneratedImage
        fields = ("index", "status", "prompt", "url", "error_message")

    def get_url(self, obj):
        return resolve_media_file_url(obj.file, self.context.get("request"))

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.file and (data.get("status") or "") == GeneratedImage.Status.FAILED:
            data["status"] = GeneratedImage.Status.SUCCEEDED
            data["error_message"] = ""
        return data


class GenerationJobSerializer(serializers.ModelSerializer):
    images = GeneratedImageSerializer(many=True, read_only=True)
    queue_position = serializers.SerializerMethodField()
    image_model = serializers.SerializerMethodField()

    class Meta:
        model = GenerationJob
        fields = (
            "id",
            "conversation",
            "prompt",
            "image_count",
            "completed_count",
            "status",
            "plan_json",
            "image_model",
            "error_message",
            "created_at",
            "started_at",
            "finished_at",
            "images",
            "queue_position",
        )

    def get_image_model(self, obj):
        plan = obj.plan_json or {}
        return plan.get("image_model") or settings.GRSAI_IMAGE_MODEL

    def get_queue_position(self, obj):
        from generation.services.dispatch import queue_position

        return queue_position(obj)


class SlotRefineCandidateSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    product_reference_url = serializers.SerializerMethodField()

    class Meta:
        model = SlotRefineCandidate
        fields = (
            "id",
            "job",
            "slot_index",
            "prompt",
            "image_model",
            "reference_mode",
            "status",
            "url",
            "product_reference_url",
            "error_message",
            "created_at",
        )
        read_only_fields = fields

    def get_url(self, obj):
        return resolve_media_file_url(obj.file, self.context.get("request"))

    def get_product_reference_url(self, obj):
        att = obj.reference_attachment if (obj.reference_mode or "") == "upload_only" else None
        if not att:
            att = obj.job.reference_attachment
        if not att or not att.file:
            return None
        return resolve_media_file_url(att.file, self.context.get("request"))
