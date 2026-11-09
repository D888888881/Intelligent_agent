from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from django.urls import re_path

from Intelligent_agent.views import (
    app_view,
    brand_icon_png_view,
    cached_media_serve,
    config_health_view,
    favicon_view,
    health_view,
    login_page_view,
    register_page_view,
)

urlpatterns = [
    path("favicon.ico", favicon_view),
    path("brand-icon.png", brand_icon_png_view),
    path("admin/", admin.site.urls),
    path("health/", health_view),
    path("health/config/", config_health_view),
    path("login/", login_page_view, name="login-page"),
    path("register/", register_page_view, name="register-page"),
    path("", app_view, name="app"),
    path("api/auth/", include("accounts.urls")),
    path("api/chat/", include("chat.urls")),
    path("api/uploads/", include("uploads.urls")),
    path("api/generations/", include("generation.urls")),
]

if settings.DEBUG:
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", cached_media_serve),
    ]
