"""对话消息分页：默认最近 N 条，before_id 向上加载更早。"""

from django.conf import settings

from chat.models import Message
from chat.services.message_order import normalize_message_order

DEFAULT_MESSAGE_PAGE_SIZE = int(getattr(settings, "CHAT_MESSAGE_PAGE_SIZE", 10))
INITIAL_MESSAGE_PAGE_SIZE = int(getattr(settings, "CHAT_MESSAGE_INITIAL_PAGE_SIZE", 10))
MAX_MESSAGE_PAGE_SIZE = int(getattr(settings, "CHAT_MESSAGE_PAGE_MAX", 50))
MAX_ALL_MESSAGES = int(getattr(settings, "CHAT_MESSAGE_ALL_MAX", 500))


def paginate_all_conversation_messages(conversation) -> dict:
    """单次返回整段对话（按 id 升序），避免分页合并导致前端顺序错乱。"""
    msgs = list(conversation.messages.order_by("id")[:MAX_ALL_MESSAGES])
    msgs = normalize_message_order(msgs)
    oldest_id = msgs[0].id if msgs else None
    newest_id = msgs[-1].id if msgs else None
    truncated = conversation.messages.count() > MAX_ALL_MESSAGES
    return {
        "messages": msgs,
        "has_more_older": False,
        "has_more_truncated": truncated,
        "oldest_message_id": oldest_id,
        "newest_message_id": newest_id,
        "limit": len(msgs),
    }


def resolve_message_limit(*, limit=None, before_id=None) -> int:
    """未传 limit 时：首屏用 INITIAL，向上翻页用 PAGE_SIZE。"""
    if limit is not None and str(limit).strip() != "":
        return limit
    if before_id is not None:
        return DEFAULT_MESSAGE_PAGE_SIZE
    return INITIAL_MESSAGE_PAGE_SIZE


def paginate_conversation_messages(
    conversation,
    *,
    limit: int | None = None,
    before_id: int | None = None,
) -> dict:
    limit = resolve_message_limit(limit=limit, before_id=before_id)
    try:
        limit = max(1, min(int(limit), MAX_MESSAGE_PAGE_SIZE))
    except (TypeError, ValueError):
        limit = INITIAL_MESSAGE_PAGE_SIZE if before_id is None else DEFAULT_MESSAGE_PAGE_SIZE

    qs = conversation.messages.order_by("-id")
    if before_id is not None:
        try:
            qs = qs.filter(id__lt=int(before_id))
        except (TypeError, ValueError):
            pass

    batch_desc = list(qs[: limit + 1])
    has_more_older = len(batch_desc) > limit
    if has_more_older:
        batch_desc = batch_desc[:limit]
    batch_desc.reverse()
    messages = normalize_message_order(batch_desc)
    oldest_id = messages[0].id if messages else None
    newest_id = messages[-1].id if messages else None
    return {
        "messages": messages,
        "has_more_older": has_more_older,
        "oldest_message_id": oldest_id,
        "newest_message_id": newest_id,
        "limit": limit,
    }
