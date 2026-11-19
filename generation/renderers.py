"""二进制下载等非 JSON 响应渲染器。"""

from rest_framework.renderers import BaseRenderer, JSONRenderer


class ZipFileRenderer(BaseRenderer):
    media_type = "application/zip"
    format = "zip"
    charset = None
    render_style = "binary"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if data is None:
            return b""
        if isinstance(data, (bytes, bytearray)):
            return bytes(data)
        if isinstance(data, memoryview):
            return data.tobytes()
        return bytes(data)


class GenerationDownloadRenderersMixin:
    renderer_classes = [ZipFileRenderer, JSONRenderer]