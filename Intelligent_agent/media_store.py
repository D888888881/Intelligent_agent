"""成片落盘：对象存储欠费或拒写时改存本地 media，避免整套被标成失败并反复重试。"""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.files.storage import FileSystemStorage

logger = logging.getLogger(__name__)


def is_object_storage_unavailable(exc: BaseException) -> bool:
    text = str(exc).lower()
    return any(
        key in text
        for key in (
            "putobject",
            "unavailableforlegalreasons",
            "account is arrears",
            "arrears",
            "insufficient balance",
        )
    )


def save_image_field(file_field, name: str, content) -> str:
    """写入 ImageField。对象存储不可用时落到 MEDIA_ROOT。返回 cos 或 local。"""
    try:
        file_field.save(name, content, save=False)
        return "cos"
    except Exception as exc:
        if not is_object_storage_unavailable(exc):
            raise
        logger.warning("对象存储写入失败，改存本地 media：%s", exc)
        if hasattr(content, "seek"):
            try:
                content.seek(0)
            except Exception:
                pass
        target = file_field.field.generate_filename(file_field.instance, name)
        local = FileSystemStorage(location=settings.MEDIA_ROOT, base_url=settings.MEDIA_URL)
        saved = local.save(target, content)
        file_field.name = saved
        file_field._committed = True
        return "local"
