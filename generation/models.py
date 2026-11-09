from django.conf import settings
from django.db import models


def generated_image_path(instance, filename):
    return f"generated/{instance.job.user_id}/{instance.job_id}/{filename}"


def slot_refine_candidate_path(instance, filename):
    return f"refine_candidates/{instance.user_id}/{instance.job_id}/{filename}"


class GenerationJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="generation_jobs",
    )
    conversation = models.ForeignKey(
        "chat.Conversation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generation_jobs",
    )
    prompt = models.TextField()
    reference_attachment = models.ForeignKey(
        "uploads.Attachment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    reference_attachment_ids = models.JSONField(default=list, blank=True)
    image_count = models.PositiveSmallIntegerField(default=9)
    completed_count = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    plan_json = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default="")
    cancel_requested = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
        ]


class GeneratedImage(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    job = models.ForeignKey(
        GenerationJob,
        on_delete=models.CASCADE,
        related_name="images",
    )
    index = models.PositiveSmallIntegerField()
    prompt = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    file = models.ImageField(upload_to=generated_image_path, blank=True)
    error_message = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["index"]
        unique_together = [("job", "index")]


class SlotRefineCandidate(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        APPLIED = "applied", "Applied"
        DISCARDED = "discarded", "Discarded"

    job = models.ForeignKey(
        GenerationJob,
        on_delete=models.CASCADE,
        related_name="refine_candidates",
    )
    slot_index = models.PositiveSmallIntegerField()
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="slot_refine_candidates",
    )
    prompt = models.TextField()
    image_model = models.CharField(max_length=64, blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    file = models.ImageField(upload_to=slot_refine_candidate_path, blank=True)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
