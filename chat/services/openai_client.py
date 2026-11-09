from django.conf import settings


def is_chat_configured() -> bool:
    return bool(settings.OPENAI_API_KEY)


def get_openai_client():
    from openai import OpenAI

    kwargs = {"api_key": settings.OPENAI_API_KEY}
    base_url = (settings.OPENAI_BASE_URL or "").strip()
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)
