"""上传探针文件验证 COS 配置。"""

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "向 COS 写入并删除一个小文件，验证 SecretId/SecretKey/桶权限。"

    def handle(self, *args, **options):
        if not getattr(settings, "COS_USE_STORAGE", False):
            raise CommandError("请在 .env 中设置 COS_USE_STORAGE=true")

        name = "health/cos_probe.txt"
        body = b"cos-ok"
        try:
            saved = default_storage.save(name, ContentFile(body))
            url = default_storage.url(saved)
            default_storage.delete(saved)
        except Exception as exc:
            raise CommandError(f"COS 探针失败: {exc}") from exc

        self.stdout.write(self.style.SUCCESS(f"COS 正常，示例 URL: {url}"))