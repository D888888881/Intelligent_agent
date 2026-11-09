import logging

from chat.services.openai_client import get_openai_client, is_chat_configured
from django.conf import settings

logger = logging.getLogger(__name__)


def stream_chat_reply(messages, chat_model: str | None = None):
    """流式生成 assistant 文本。"""
    if is_chat_configured():
        yield from _stream_openai(messages, chat_model=chat_model)
    else:
        yield from _stream_mock(messages)


def _extract_chunk_text(chunk) -> str | None:
    choices = getattr(chunk, "choices", None) or []
    if not choices:
        return None
    choice = choices[0]
    delta = getattr(choice, "delta", None)
    if delta is None:
        return None
    content = getattr(delta, "content", None)
    if content:
        return content
    return None


def _stream_openai(messages, chat_model: str | None = None):
    from Intelligent_agent.model_catalog import resolve_chat_model

    client = get_openai_client()
    model = resolve_chat_model(chat_model)
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
    )

    yielded_any = False
    for chunk in stream:
        piece = _extract_chunk_text(chunk)
        if piece:
            yielded_any = True
            yield piece

    if not yielded_any:
        logger.warning("流式响应无内容，回退为非流式请求 model=%s", model)
        yield from _non_stream_fallback(client, model, messages)


def _non_stream_fallback(client, model, messages):
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=False,
    )
    choices = getattr(resp, "choices", None) or []
    if not choices:
        raise RuntimeError("模型未返回任何内容（choices 为空）")
    message = choices[0].message
    text = (getattr(message, "content", None) or "").strip()
    if not text:
        raise RuntimeError("模型返回空文本")
    step = max(1, len(text) // 30)
    for i in range(0, len(text), step):
        yield text[i : i + step]


def _stream_mock(messages):
    last_user = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user = m.get("content", "")
            break
    text = (
        f"（演示模式：未读到 OPENAI_API_KEY）已收到：「{last_user[:200]}」。"
        "请确认项目根目录 .env 已配置 OPENAI_API_KEY、OPENAI_BASE_URL，并重启 Django "
        "（PyCharm 运行请把工作目录设为项目根目录，或使用 scripts/runserver.ps1）。"
    )
    step = max(1, len(text) // 20)
    for i in range(0, len(text), step):
        yield text[i : i + step]
