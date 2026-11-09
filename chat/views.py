import json

from django.contrib.auth.models import User
from django.db.models import BooleanField, Case, Q, Value, When
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from Intelligent_agent.renderers import EventStreamRenderer
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import UserProfile
from chat.models import Conversation, Message
from chat.services.conversation_share import clone_conversation_for_share, sharer_display_name
from chat.serializers import (
    ConversationDetailSerializer,
    ConversationSerializer,
    MessageSerializer,
)
from Intelligent_agent.model_catalog import resolve_chat_model, resolve_vision_model

from chat.services.llm import stream_chat_reply
from chat.services.memory import build_chat_messages
from chat.services.message_pagination import (
    paginate_all_conversation_messages,
    paginate_conversation_messages,
)


def conversation_list_queryset(user):
    return (
        Conversation.objects.filter(user=user)
        .annotate(
            _pin_rank=Case(
                When(pinned_at__isnull=False, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
        )
        .order_by("-_pin_rank", "-pinned_at", "-updated_at")
    )


class ConversationListCreateView(APIView):
    def get(self, request):
        qs = conversation_list_queryset(request.user)[:100]
        return Response(ConversationSerializer(qs, many=True).data)

    def post(self, request):
        title = request.data.get("title") or "新对话"
        conv = Conversation.objects.create(user=request.user, title=title[:200])
        return Response(ConversationSerializer(conv).data, status=status.HTTP_201_CREATED)


class ConversationDetailView(APIView):
    def get(self, request, pk):
        conv = get_object_or_404(Conversation, pk=pk, user=request.user)
        all_messages = request.query_params.get("all_messages", "").lower() in (
            "1",
            "true",
            "yes",
        )
        if all_messages:
            page = paginate_all_conversation_messages(conv)
        else:
            before_id = request.query_params.get("before_id")
            limit = request.query_params.get("limit")
            page = paginate_conversation_messages(
                conv,
                limit=limit,
                before_id=int(before_id) if before_id else None,
            )
        data = ConversationDetailSerializer(
            conv,
            context={"request": request, "message_page": page},
        ).data
        return Response(data)

    def patch(self, request, pk):
        conv = get_object_or_404(Conversation, pk=pk, user=request.user)
        update_fields = []
        if "title" in request.data:
            title = request.data.get("title")
            if title is not None:
                conv.title = str(title).strip()[:200] or conv.title
                update_fields.append("title")
        if "pinned" in request.data:
            if request.data.get("pinned"):
                conv.pinned_at = timezone.now()
            else:
                conv.pinned_at = None
            update_fields.append("pinned_at")
        if update_fields:
            update_fields.append("updated_at")
            conv.save(update_fields=update_fields)
        return Response(ConversationSerializer(conv).data)

    def delete(self, request, pk):
        conv = get_object_or_404(Conversation, pk=pk, user=request.user)
        conv.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MessageListView(APIView):
    def get(self, request, pk):
        conv = get_object_or_404(Conversation, pk=pk, user=request.user)
        before_id = request.query_params.get("before_id")
        limit = request.query_params.get("limit")
        page = paginate_conversation_messages(
            conv,
            limit=limit,
            before_id=int(before_id) if before_id else None,
        )
        return Response(
            {
                "messages": MessageSerializer(page["messages"], many=True).data,
                "message_pagination": {
                    "has_more_older": page["has_more_older"],
                    "oldest_message_id": page["oldest_message_id"],
                    "newest_message_id": page["newest_message_id"],
                    "limit": page["limit"],
                },
            }
        )


class ChatStreamView(APIView):
    renderer_classes = [EventStreamRenderer]

    def finalize_response(self, request, response, *args, **kwargs):
        if isinstance(response, StreamingHttpResponse):
            return response
        return super().finalize_response(request, response, *args, **kwargs)

    def post(self, request, pk):
        conv = get_object_or_404(Conversation, pk=pk, user=request.user)
        content = (request.data.get("content") or "").strip()
        if not content:
            return Response({"detail": "消息不能为空"}, status=status.HTTP_400_BAD_REQUEST)

        attachment_ids = request.data.get("attachment_ids") or []
        from generation.services.intent import wants_image_refine

        if attachment_ids and wants_image_refine(content):
            return Response(
                {
                    "detail": (
                        "检测到「重塑/优化图片」需求，应走生图任务而非文字分析。"
                        "请刷新页面后：上传原图，只发送简短指令（勿粘贴 5S 长文），例如："
                        "「人物太假，帮我重塑这张图片」。"
                    ),
                    "code": "use_image_generation",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        chat_model = resolve_chat_model(request.data.get("chat_model"))
        vision_model = resolve_vision_model(request.data.get("vision_model"))
        use_vision = bool(attachment_ids)
        model_for_llm = vision_model if use_vision else chat_model
        metadata = {
            "attachment_ids": attachment_ids,
            "chat_model": chat_model,
            "vision_model": vision_model if use_vision else "",
        }

        Message.objects.create(
            conversation=conv,
            role=Message.Role.USER,
            content=content,
            metadata=metadata,
        )
        if conv.title == "新对话":
            conv.title = content[:40] + ("…" if len(content) > 40 else "")
            conv.save(update_fields=["title", "updated_at"])
        else:
            conv.updated_at = timezone.now()
            conv.save(update_fields=["updated_at"])

        llm_messages = build_chat_messages(conv, vision_mode=use_vision)

        def event_stream():
            full = []
            try:
                for piece in stream_chat_reply(llm_messages, chat_model=model_for_llm):
                    full.append(piece)
                    payload = json.dumps({"type": "token", "content": piece}, ensure_ascii=False)
                    yield f"data: {payload}\n\n"
            except Exception as exc:
                err = json.dumps({"type": "error", "content": str(exc)}, ensure_ascii=False)
                yield f"data: {err}\n\n"
                return

            assistant_text = "".join(full)
            msg = Message.objects.create(
                conversation=conv,
                role=Message.Role.ASSISTANT,
                content=assistant_text,
                metadata={},
            )
            done = json.dumps(
                {
                    "type": "done",
                    "message": MessageSerializer(msg).data,
                },
                ensure_ascii=False,
            )
            yield f"data: {done}\n\n"

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class ShareableUsersView(APIView):
    """可分享目标：已审批通过的其它用户。"""

    def get(self, request):
        q = (request.GET.get("q") or "").strip()
        qs = (
            User.objects.filter(is_active=True, profile__approval_status=UserProfile.ApprovalStatus.APPROVED)
            .exclude(pk=request.user.pk)
            .select_related("profile")
            .order_by("username")
        )
        if q:
            qs = qs.filter(Q(username__icontains=q) | Q(profile__real_name__icontains=q))
        results = []
        for user in qs[:80]:
            profile = getattr(user, "profile", None)
            real_name = (profile.real_name if profile else "") or ""
            results.append(
                {
                    "id": user.id,
                    "username": user.username,
                    "real_name": real_name,
                    "display_name": real_name.strip() or user.username,
                }
            )
        return Response(results)


class ConversationShareView(APIView):
    def post(self, request, pk):
        source = get_object_or_404(Conversation, pk=pk, user=request.user)
        if source.shared_by_id:
            return Response(
                {"detail": "此对话为他人分享，不能再次分享"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            target_user_id = int(request.data.get("user_id"))
        except (TypeError, ValueError):
            return Response({"detail": "请选择要分享的用户"}, status=status.HTTP_400_BAD_REQUEST)
        if target_user_id == request.user.id:
            return Response({"detail": "不能分享给自己"}, status=status.HTTP_400_BAD_REQUEST)

        recipient = User.objects.filter(pk=target_user_id).select_related("profile").first()
        if not recipient:
            return Response({"detail": "用户不存在"}, status=status.HTTP_404_NOT_FOUND)
        profile = getattr(recipient, "profile", None)
        if not recipient.is_active:
            return Response({"detail": "对方账号未启用"}, status=status.HTTP_400_BAD_REQUEST)
        if not profile or profile.approval_status != UserProfile.ApprovalStatus.APPROVED:
            return Response({"detail": "对方账号未通过审批"}, status=status.HTTP_400_BAD_REQUEST)

        if not Message.objects.filter(conversation=source).exists():
            return Response({"detail": "当前对话还没有消息，无法分享"}, status=status.HTTP_400_BAD_REQUEST)

        clone = clone_conversation_for_share(
            source,
            recipient=recipient,
            sharer=request.user,
            request=request,
        )
        recipient_label = sharer_display_name(recipient)
        return Response(
            {
                "detail": f"已将当前对话分享给 {recipient_label}",
                "shared_with": {
                    "id": recipient.id,
                    "username": recipient.username,
                    "display_name": recipient_label,
                },
                "conversation": ConversationSerializer(clone).data,
            },
            status=status.HTTP_201_CREATED,
        )
