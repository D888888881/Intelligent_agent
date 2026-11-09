from django.conf import settings
from rest_framework import serializers

from generation.models import GeneratedImage, GenerationJob, SlotRefineCandidate


class GeneratedImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = GeneratedImage
        fields = ("index", "status", "prompt", "url", "error_message")

    def get_url(self, obj):
        if not obj.file:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url


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
            "status",
            "url",
            "product_reference_url",
            "error_message",
            "created_at",
        )
        read_only_fields = fields

    def get_url(self, obj):
        if not obj.file:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url

    def get_product_reference_url(self, obj):
        att = obj.job.reference_attachment
        if not att or not att.file:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(att.file.url)
        return att.file.url
