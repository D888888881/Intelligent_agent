from PIL import Image
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Attachment
from .serializers import AttachmentSerializer

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


class UploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"detail": "请上传 file 字段"}, status=400)
        if file_obj.size > MAX_UPLOAD_BYTES:
            return Response({"detail": "文件不能超过 10MB"}, status=400)

        try:
            file_obj.seek(0)
            with Image.open(file_obj) as img:
                width, height = img.size
        except Exception:
            return Response({"detail": "仅支持有效图片文件"}, status=400)

        file_obj.seek(0)
        attachment = Attachment.objects.create(
            user=request.user,
            file=file_obj,
            original_name=file_obj.name,
            mime_type=file_obj.content_type or "",
            width=width,
            height=height,
        )
        return Response(
            AttachmentSerializer(attachment, context={"request": request}).data,
            status=201,
        )
