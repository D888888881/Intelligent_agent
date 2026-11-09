from django.conf import settings

from chat.models import Message
from chat.services.vision import FIVE_S_CHAT_SYSTEM, build_user_content
from uploads.models import Attachment


def _attachments_for_message(msg: Message, user_id: int):
    ids = (msg.metadata or {}).get("attachment_ids") or []
    if not ids:
        return []
    return list(
        Attachment.objects.filter(user_id=user_id, pk__in=ids).order_by("pk")
    )


def build_chat_messages(conversation, system_extra: str = "", *, vision_mode: bool = False):
    """组装发给 LLM 的消息列表（含记忆窗口；含历史图片 metadata）。"""
    limit = settings.CHAT_HISTORY_MAX_MESSAGES
    qs = conversation.messages.exclude(role=Message.Role.SYSTEM).order_by("-created_at")[:limit]
    history = list(reversed(list(qs)))

    system_parts = [
        "你是智能助手，可回答问题，也可根据用户上传的图片进行分析。",
        "若用户上传图片并要求优化/修图/去 AI 感/更真实，应走生图任务而非仅文字建议；"
        "若用户只要文字分析，请明确说「仅分析」。",
    ]
    if conversation.summary:
        system_parts.append(f"会话摘要：{conversation.summary}")
    if vision_mode:
        system_parts.append(FIVE_S_CHAT_SYSTEM)
    if system_extra:
        system_parts.append(system_extra)

    messages = [{"role": "system", "content": "\n".join(system_parts)}]
    user_id = conversation.user_id

    for msg in history:
        if msg.role == Message.Role.USER:
            attachments = _attachments_for_message(msg, user_id)
            content = build_user_content(msg.content, attachments)
        else:
            content = msg.content
        messages.append({"role": msg.role, "content": content})
    return messages


def conversation_has_images(conversation) -> bool:
    limit = settings.CHAT_HISTORY_MAX_MESSAGES
    qs = conversation.messages.filter(role=Message.Role.USER).order_by("-created_at")[:limit]
    for msg in qs:
        if (msg.metadata or {}).get("attachment_ids"):
            return True
    return False
