"""
Django settings for Intelligent_agent project.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-e%(hvs3v0e=rd3#i_989pww1)1d#246jdhfq7i53u*b+!udtg#",
)
DEBUG = os.getenv("DEBUG", "True").lower() in ("1", "true", "yes")

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "accounts",
    "chat",
    "uploads",
    "generation",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "Intelligent_agent.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "Intelligent_agent.wsgi.application"
ASGI_APPLICATION = "Intelligent_agent.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "intelligent_agent"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "CONN_MAX_AGE": 60,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"

# Chat memory
CHAT_HISTORY_MAX_MESSAGES = int(os.getenv("CHAT_HISTORY_MAX_MESSAGES", "20"))

# Generation
GEN_DEFAULT_IMAGE_COUNT = int(os.getenv("GEN_DEFAULT_IMAGE_COUNT", "9"))
GEN_MAX_IMAGE_COUNT = int(os.getenv("GEN_MAX_IMAGE_COUNT", "12"))
GEN_MAX_REFERENCE_IMAGES = int(os.getenv("GEN_MAX_REFERENCE_IMAGES", "8"))
GEN_MAX_QUEUE_SIZE = int(os.getenv("GEN_MAX_QUEUE_SIZE", "50"))

# 单个会话消息分页（中间对话区，非左侧会话列表）
CHAT_MESSAGE_INITIAL_PAGE_SIZE = int(os.getenv("CHAT_MESSAGE_INITIAL_PAGE_SIZE", "10"))
CHAT_MESSAGE_PAGE_SIZE = int(os.getenv("CHAT_MESSAGE_PAGE_SIZE", "10"))
CHAT_MESSAGE_PAGE_MAX = int(os.getenv("CHAT_MESSAGE_PAGE_MAX", "50"))
CHAT_MESSAGE_ALL_MAX = int(os.getenv("CHAT_MESSAGE_ALL_MAX", "500"))

# OpenAI 兼容中转（对话 / 视觉策划）
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-6.1-terra")
OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4.1")
OPENAI_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "dall-e-3")
OPENAI_IMAGE_BACKEND = os.getenv("OPENAI_IMAGE_BACKEND", "grsai")

# Grsai 生图（nano-banana / gpt-image-2 系列）
GRSAI_BASE_URL = os.getenv("GRSAI_BASE_URL", "https://grsai.dakka.com.cn")
GRSAI_API_KEY = os.getenv("GRSAI_API_KEY", "")
GRSAI_IMAGE_MODEL = os.getenv("GRSAI_IMAGE_MODEL", "nano-banana-2")
GRSAI_IMAGE_SIZE = os.getenv("GRSAI_IMAGE_SIZE", "2K")
GRSAI_ASPECT_RATIO = os.getenv("GRSAI_ASPECT_RATIO", "1:1")
GRSAI_REPLY_TYPE = os.getenv("GRSAI_REPLY_TYPE", "async")
GRSAI_POLL_INTERVAL = float(os.getenv("GRSAI_POLL_INTERVAL", "5"))
GRSAI_POLL_TIMEOUT = int(os.getenv("GRSAI_POLL_TIMEOUT", "600"))
GRSAI_GPT_POLL_TIMEOUT = int(os.getenv("GRSAI_GPT_POLL_TIMEOUT", "900"))
# 单任务轮询绝对上限（秒），防止 progress 长期不变仍无限等待
GRSAI_POLL_MAX_SECONDS = int(os.getenv("GRSAI_POLL_MAX_SECONDS", "1200"))
# 生图单次请求最多附带几张参考图（多色号任务请靠识图+prompt；避免 8 张 base64 撑爆 Grsai）
GRSAI_MAX_REF_IMAGES_PER_REQUEST = int(os.getenv("GRSAI_MAX_REF_IMAGES_PER_REQUEST", "2"))
# 「多色号合集」镜头可附带更多参考图（仍建议 ≤4，避免 server_timeout）
GRSAI_MAX_REF_IMAGES_SHOWCASE = int(os.getenv("GRSAI_MAX_REF_IMAGES_SHOWCASE", "4"))
# 参考图传给 Grsai：auto=有公网地址用 URL，否则压缩 base64；url|base64 强制
GRSAI_REFERENCE_IMAGE_MODE = os.getenv("GRSAI_REFERENCE_IMAGE_MODE", "auto").strip().lower()
# 站点公网根 URL（无尾斜杠），供 Grsai 拉取 /media/…；本地开发可留空
PUBLIC_SITE_URL = (os.getenv("PUBLIC_SITE_URL") or "").strip().rstrip("/")
GRSAI_REF_MAX_EDGE = int(os.getenv("GRSAI_REF_MAX_EDGE", "1280"))
GRSAI_REF_MAX_BYTES = int(os.getenv("GRSAI_REF_MAX_BYTES", "850000"))
GRSAI_POST_READ_TIMEOUT = float(os.getenv("GRSAI_POST_READ_TIMEOUT", "300"))
GRSAI_PER_IMAGE_MAX_SECONDS = int(os.getenv("GRSAI_PER_IMAGE_MAX_SECONDS", "180"))
# 单张失败后额外重试次数（1 = 最多共 2 次尝试）
GRSAI_PER_IMAGE_RETRIES = int(os.getenv("GRSAI_PER_IMAGE_RETRIES", "1"))
# Grsai 任务成功后，从 CDN 拉取成片的重试（SSL 握手超时等多发生在此步，中转站仍显示生图成功）
GRSAI_RESULT_DOWNLOAD_RETRIES = int(os.getenv("GRSAI_RESULT_DOWNLOAD_RETRIES", "4"))
GRSAI_RESULT_DOWNLOAD_CONNECT = float(os.getenv("GRSAI_RESULT_DOWNLOAD_CONNECT", "45"))
GRSAI_RESULT_DOWNLOAD_READ = float(os.getenv("GRSAI_RESULT_DOWNLOAD_READ", "120"))
GRSAI_HTTP_RETRIES = int(os.getenv("GRSAI_HTTP_RETRIES", "3"))
# 套图任务结束后，对仍 FAILED 的镜头再跑一轮（网络偶发失败）
# 首轮九图跑完后，对仍失败的镜头再整轮补跑次数（不含首轮，例如 3 = 最多再补 3 轮）
GRSAI_JOB_FAILED_SHOT_RETRIES = int(os.getenv("GRSAI_JOB_FAILED_SHOT_RETRIES", "3"))
GRSAI_GPT_IMAGE_QUALITY = os.getenv("GRSAI_GPT_IMAGE_QUALITY", "auto")
GRSAI_GPT_ASPECT_RATIO = os.getenv("GRSAI_GPT_ASPECT_RATIO", "1024x1024")
GRSAI_GPT_BACKGROUND = os.getenv("GRSAI_GPT_BACKGROUND", "")

# Celery
CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
CELERY_TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "False").lower() in (
    "1",
    "true",
    "yes",
)
CELERY_TASK_ROUTES = {
    "generation.tasks.run_generation_job": {"queue": "image"},
    "generation.tasks.run_slot_refine_task": {"queue": "image"},
}
CELERY_WORKER_CONCURRENCY = int(os.getenv("CELERY_WORKER_CONCURRENCY", "4"))

def _build_csrf_trusted_origins():
    explicit = os.getenv("CSRF_TRUSTED_ORIGINS", "").strip()
    if explicit:
        return [o.strip() for o in explicit.split(",") if o.strip()]
    django_port = os.getenv("DJANGO_PORT", "8088")
    vite_port = os.getenv("VITE_DEV_PORT", "3000")
    hosts = ("127.0.0.1", "localhost")
    origins = []
    for host in hosts:
        origins.append(f"http://{host}:{django_port}")
        origins.append(f"http://{host}:{vite_port}")
    return origins


CSRF_TRUSTED_ORIGINS = _build_csrf_trusted_origins()
