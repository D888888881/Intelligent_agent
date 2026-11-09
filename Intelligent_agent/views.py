from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.static import serve as static_serve

BRAND_ICON_VERSION = "20260416"


def _serve_brand_file(request, filename, content_type: str):
    response = static_serve(request, filename, document_root=settings.BASE_DIR / "static")
    if response.status_code == 200:
        response["Content-Type"] = content_type
        response["Cache-Control"] = "public, max-age=3600"
    return response


def favicon_view(request):
    return _serve_brand_file(request, "favicon.ico", "image/x-icon")


def brand_icon_png_view(request):
    return _serve_brand_file(request, "favicon-64.png", "image/png")


def health_view(request):
    from django.db import connection

    try:
        connection.ensure_connection()
        db_ok = True
    except Exception as exc:
        db_ok = False
        db_err = str(exc)
    else:
        db_err = ""
    status = 200 if db_ok else 503
    return JsonResponse({"database": db_ok, "detail": db_err}, status=status)


def config_health_view(request):
    """供排查：是否已加载 .env 中的 API 配置（不返回密钥内容）。"""
    return JsonResponse(
        {
            "openai_configured": bool(settings.OPENAI_API_KEY),
            "openai_base_url": settings.OPENAI_BASE_URL or None,
            "openai_chat_model": settings.OPENAI_CHAT_MODEL,
            "openai_vision_model": settings.OPENAI_VISION_MODEL,
            "grsai_configured": bool(settings.GRSAI_API_KEY),
            "grsai_base_url": settings.GRSAI_BASE_URL,
        }
    )


def login_page_view(request):
    if request.user.is_authenticated:
        from django.shortcuts import redirect

        return redirect("/")
    return render(request, "login.html")


def register_page_view(request):
    if request.user.is_authenticated:
        from django.shortcuts import redirect

        return redirect("/")
    return render(request, "register.html")


@login_required(login_url="/login/")
def app_view(request):
    return render(
        request,
        "app.html",
        {
            "chat_initial_message_limit": settings.CHAT_MESSAGE_INITIAL_PAGE_SIZE,
            "chat_older_message_page_size": settings.CHAT_MESSAGE_PAGE_SIZE,
            "max_reference_images": settings.GEN_MAX_REFERENCE_IMAGES,
            "brand_icon_version": BRAND_ICON_VERSION,
        },
    )


def cached_media_serve(request, path):
    """用户上传与生图文件：允许浏览器私有缓存，切换会话时少重复下载。"""
    response = static_serve(request, path, document_root=settings.MEDIA_ROOT)
    if response.status_code == 200:
        response["Cache-Control"] = "private, max-age=604800, stale-while-revalidate=86400"
    return response
