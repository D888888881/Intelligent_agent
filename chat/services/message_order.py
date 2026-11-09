"""对话消息展示顺序：严格按入库 id 升序（与真实发送顺序一致）。"""

from __future__ import annotations

from chat.models import Message


def normalize_message_order(messages: list[Message]) -> list[Message]:
    if not messages:
        return []
    return sorted(messages, key=lambda m: m.id)
