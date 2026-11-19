"""解析用户可见的图片 URL：COS 上线后旧文件可能仍在本地 media/。"""

from django.conf import settings


def resolve_media_file_url(file_field, request=None) -> str | None:
    if not file_field:
        return None
    name = (file_field.name or "").lstrip("/")
    if not name:
        return None

    if getattr(settings, "COS_USE_STORAGE", False):
        local = settings.MEDIA_ROOT / name
        if local.is_file():
            rel = f"/media/{name}"
            if request is not None:
                return request.build_absolute_uri(rel)
            base = (getattr(settings, "PUBLIC_SITE_URL", None) or "").strip().rstrip("/")
            if base:
                return f"{base}{rel}"
            return rel

    url = file_field.url
    if request is not None and url.startswith("/"):
        return request.build_absolute_uri(url)
    if request is not None and not (url.startswith("http://") or url.startswith("https://")):
        return request.build_absolute_uri(url)
    return url