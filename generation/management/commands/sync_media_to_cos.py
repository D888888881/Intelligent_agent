"""将本地 media/ 下已有文件同步到 COS（不删本地）。"""

from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "把 MEDIA_ROOT 内文件上传到 COS，便于历史图片走对象存储直链。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="只统计文件数，不上传",
        )

    def handle(self, *args, **options):
        if not getattr(settings, "COS_USE_STORAGE", False):
            raise CommandError("请先开启 COS_USE_STORAGE")

        root: Path = settings.MEDIA_ROOT
        if not root.is_dir():
            raise CommandError(f"本地目录不存在: {root}")

        files = [p for p in root.rglob("*") if p.is_file()]
        self.stdout.write(f"共 {len(files)} 个本地文件")

        if options["dry_run"]:
            return

        uploaded = 0
        skipped = 0
        for path in files:
            rel = path.relative_to(root).as_posix()
            if default_storage.exists(rel):
                skipped += 1
                continue
            with path.open("rb") as fh:
                default_storage.save(rel, ContentFile(fh.read()))
            uploaded += 1

        self.stdout.write(self.style.SUCCESS(f"上传 {uploaded} 个，COS 已存在跳过 {skipped} 个"))