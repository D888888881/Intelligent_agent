from django.conf import settings
from django.db import models


def upload_to_user(instance, filename):
    return f"uploads/{instance.user_id}/{filename}"


class Attachment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file = models.ImageField(upload_to=upload_to_user)
    original_name = models.CharField(max_length=255, blank=True, default="")
    mime_type = models.CharField(max_length=100, blank=True, default="")
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Attachment({self.id}, {self.user.username})"
