"""DRF 渲染器扩展（SSE 等）。"""

from rest_framework.renderers import BaseRenderer


class EventStreamRenderer(BaseRenderer):
    """允许 EventSource 的 Accept: text/event-stream，避免 406 Not Acceptable。"""

    media_type = "text/event-stream"
    format = "event-stream"
    charset = None

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if data is None:
            return b""
        if isinstance(data, (bytes, bytearray)):
            return data
        return str(data).encode("utf-8")
