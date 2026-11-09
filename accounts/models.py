from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    class ApprovalStatus(models.TextChoices):
        PENDING = "pending", "待审批"
        APPROVED = "approved", "已通过"
        REJECTED = "rejected", "已拒绝"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    approval_status = models.CharField(
        max_length=16,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.APPROVED,
    )
    real_name = models.CharField(max_length=64, blank=True, default="")
    default_image_count = models.PositiveSmallIntegerField(default=9)
    daily_image_quota = models.PositiveIntegerField(default=200)
    preferred_chat_model = models.CharField(max_length=64, blank=True, default="")
    preferred_image_model = models.CharField(max_length=64, blank=True, default="")
    preferred_vision_model = models.CharField(max_length=64, blank=True, default="")

    def __str__(self) -> str:
        return f"Profile({self.user.username})"
