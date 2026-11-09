"""页面可选模型列表（可在 settings 中扩展）。"""

from django.conf import settings


CHAT_MODELS = [
    {"id": "gpt-6.1-terra", "label": "GPT 6.1 Terra"},
    {"id": "gpt-4.1", "label": "GPT-4.1"},
    {"id": "gpt-4o", "label": "GPT-4o"},
    {"id": "gpt-4o-mini", "label": "GPT-4o Mini"},
    {"id": "deepseek-chat", "label": "DeepSeek Chat"},
]

VISION_MODELS = [
    {"id": "gpt-4.1", "label": "GPT-4.1（识图默认）"},
    {"id": "gpt-4o", "label": "GPT-4o"},
    {"id": "gpt-4o-mini", "label": "GPT-4o Mini"},
]

IMAGE_MODELS = [
    {"id": "nano-banana-2", "label": "Nano Banana 2", "group": "nano-banana"},
    {"id": "nano-banana-2-cl", "label": "Nano Banana 2 CL", "group": "nano-banana"},
    {"id": "nano-banana-2-2k-cl", "label": "Nano Banana 2 2K CL", "group": "nano-banana"},
    {"id": "nano-banana-pro", "label": "Nano Banana Pro", "group": "nano-banana"},
    {"id": "nano-banana-fast", "label": "Nano Banana Fast", "group": "nano-banana"},
    {"id": "gpt-image-2", "label": "GPT Image 2", "group": "gpt-image"},
    {"id": "gpt-image-2.5", "label": "GPT Image 2.5", "group": "gpt-image"},
    {"id": "gpt-image-2-vip", "label": "GPT Image 2 VIP", "group": "gpt-image"},
    {"id": "gpt-image-2.5-flare", "label": "GPT Image 2.5 Flare", "group": "gpt-image"},
    {"id": "gpt-image-2.5-sunburst", "label": "GPT Image 2.5 Sunburst", "group": "gpt-image"},
]


def chat_model_ids() -> set[str]:
    return {m["id"] for m in CHAT_MODELS}


def image_model_ids() -> set[str]:
    return {m["id"] for m in IMAGE_MODELS}


def vision_model_ids() -> set[str]:
    return {m["id"] for m in VISION_MODELS}


def resolve_chat_model(model_id: str | None) -> str:
    mid = (model_id or "").strip() or settings.OPENAI_CHAT_MODEL
    if mid in chat_model_ids():
        return mid
    return settings.OPENAI_CHAT_MODEL


def resolve_image_model(model_id: str | None) -> str:
    mid = (model_id or "").strip() or settings.GRSAI_IMAGE_MODEL
    if mid in image_model_ids():
        return mid
    return settings.GRSAI_IMAGE_MODEL


def resolve_vision_model(model_id: str | None) -> str:
    mid = (model_id or "").strip() or settings.OPENAI_VISION_MODEL
    if mid in vision_model_ids():
        return mid
    return settings.OPENAI_VISION_MODEL


def catalog_payload(profile=None) -> dict:
    chat_default = settings.OPENAI_CHAT_MODEL
    image_default = settings.GRSAI_IMAGE_MODEL
    vision_default = settings.OPENAI_VISION_MODEL
    if profile:
        if profile.preferred_chat_model:
            chat_default = resolve_chat_model(profile.preferred_chat_model)
        if profile.preferred_image_model:
            image_default = resolve_image_model(profile.preferred_image_model)
        if profile.preferred_vision_model:
            vision_default = resolve_vision_model(profile.preferred_vision_model)

    return {
        "chat_models": CHAT_MODELS,
        "image_models": IMAGE_MODELS,
        "vision_models": VISION_MODELS,
        "defaults": {
            "chat_model": chat_default,
            "image_model": image_default,
            "vision_model": vision_default,
        },
    }
