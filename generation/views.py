import json

from django.conf import settings
from django.http import StreamingHttpResponse
from Intelligent_agent.renderers import EventStreamRenderer
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from chat.models import Conversation, Message
from generation.models import GeneratedImage, GenerationJob, SlotRefineCandidate
from generation.serializers import GenerationJobSerializer, SlotRefineCandidateSerializer
from generation.services.slot_refine import apply_slot_refine_candidate
from generation.tasks import run_slot_refine_task
from generation.services.intent import parse_image_count_from_prompt, resolve_generation_params
from generation.services.job_references import normalize_attachment_id_list
from generation.services.prepare import start_prepare_and_run_async
from Intelligent_agent.model_catalog import resolve_image_model, resolve_vision_model
from uploads.models import Attachment


class GenerationCreateView(APIView):
    def post(self, request):
        prompt = (request.data.get("prompt") or "").strip()
        if not prompt:
            return Response({"detail": "prompt 不能为空"}, status=400)

        try:
            image_count = int(request.data.get("image_count") or settings.GEN_DEFAULT_IMAGE_COUNT)
        except (TypeError, ValueError):
            image_count = settings.GEN_DEFAULT_IMAGE_COUNT
        plan_template = (request.data.get("plan_template") or "auto").strip()
        image_count, plan_template = resolve_generation_params(
            prompt,
            image_count=image_count,
            plan_template=plan_template,
        )

        conversation_id = request.data.get("conversation_id")
        conversation = None
        if conversation_id:
            conversation = get_object_or_404(
                Conversation,
                pk=conversation_id,
                user=request.user,
            )

        att_ids = normalize_attachment_id_list(request.data.get("attachment_ids"))
        legacy_id = request.data.get("attachment_id")
        if legacy_id and not att_ids:
            att_ids = normalize_attachment_id_list([legacy_id])
        att_ids = att_ids[: settings.GEN_MAX_REFERENCE_IMAGES]

        attachments = []
        if att_ids:
            by_id = {
                a.id: a
                for a in Attachment.objects.filter(pk__in=att_ids, user=request.user)
            }
            attachments = [by_id[i] for i in att_ids if i in by_id]
            if len(attachments) != len(att_ids):
                return Response({"detail": "部分参考图无效或无权访问"}, status=400)

        attachment = attachments[0] if attachments else None

        vision_model = resolve_vision_model(request.data.get("vision_model"))
        image_model = resolve_image_model(request.data.get("image_model"))
        ref_ids = [a.id for a in attachments]

        cast_skin = (request.data.get("cast_skin_preset") or "caucasian").strip().lower()
        if cast_skin not in ("caucasian", "diverse", "black_only"):
            cast_skin = "caucasian"

        job = GenerationJob.objects.create(
            user=request.user,
            conversation=conversation,
            prompt=prompt,
            reference_attachment=attachment,
            reference_attachment_ids=ref_ids,
            image_count=image_count,
            plan_json={
                "image_model": image_model,
                "reference_attachment_ids": ref_ids,
                "cast_skin_preset": cast_skin,
            },
            status=GenerationJob.Status.PENDING,
        )

        assistant_message = None
        user_message = None
        if conversation:
            user_meta = {}
            if attachments:
                user_meta["attachment_ids"] = ref_ids
                user_meta["attachments"] = [
                    {
                        "id": a.id,
                        "url": request.build_absolute_uri(a.file.url),
                        "name": a.original_name,
                    }
                    for a in attachments
                ]
            user_message = Message.objects.create(
                conversation=conversation,
                role=Message.Role.USER,
                content=prompt,
                metadata=user_meta,
            )
            assistant_message = Message.objects.create(
                conversation=conversation,
                role=Message.Role.ASSISTANT,
                content="正在分析参考图并策划套图…",
                metadata={
                    "generation_job_id": job.id,
                    "generation_phase": "pending",
                    "image_count": image_count,
                    "completed_count": 0,
                },
            )
            conversation.updated_at = timezone.now()
            if conversation.title == "新对话":
                conversation.title = prompt[:40] + ("…" if len(prompt) > 40 else "")
            conversation.save(update_fields=["title", "updated_at"])

        start_prepare_and_run_async(
            job.id,
            vision_model=vision_model,
            plan_template=plan_template,
        )

        job.refresh_from_db()
        data = GenerationJobSerializer(job, context={"request": request}).data
        data["dispatch"] = "accepted"
        if assistant_message:
            from chat.serializers import MessageSerializer

            ser_ctx = {"request": request}
            if user_message:
                data["user_message"] = MessageSerializer(user_message, context=ser_ctx).data
            data["assistant_message"] = MessageSerializer(assistant_message, context=ser_ctx).data
        return Response(data, status=status.HTTP_202_ACCEPTED)


class GenerationDetailView(APIView):
    def get(self, request, job_id):
        job = get_object_or_404(GenerationJob, pk=job_id, user=request.user)
        return Response(GenerationJobSerializer(job, context={"request": request}).data)


class GenerationCancelView(APIView):
    def post(self, request, job_id):
        job = get_object_or_404(GenerationJob, pk=job_id, user=request.user)
        if job.status in (
            GenerationJob.Status.SUCCEEDED,
            GenerationJob.Status.FAILED,
            GenerationJob.Status.CANCELLED,
        ):
            return Response({"detail": "任务已结束"}, status=400)
        job.cancel_requested = True
        if job.status in (
            GenerationJob.Status.QUEUED,
            GenerationJob.Status.PENDING,
        ):
            job.status = GenerationJob.Status.CANCELLED
            job.finished_at = timezone.now()
            if not job.error_message:
                job.error_message = "用户已取消任务"
        job.save()
        from generation.tasks import _update_assistant_message

        _update_assistant_message(job)
        return Response(GenerationJobSerializer(job, context={"request": request}).data)


class GenerationStreamView(APIView):
    renderer_classes = [EventStreamRenderer]

    def finalize_response(self, request, response, *args, **kwargs):
        if isinstance(response, StreamingHttpResponse):
            return response
        return super().finalize_response(request, response, *args, **kwargs)

    def get(self, request, job_id):
        job = get_object_or_404(GenerationJob, pk=job_id, user=request.user)

        def event_stream():
            import time

            last_signature = ""
            idle_ticks = 0
            while True:
                job.refresh_from_db()
                payload = GenerationJobSerializer(job, context={"request": request}).data
                images = payload.get("images") or []
                url_sig = "|".join(
                    f"{img.get('index')}:{img.get('status')}:{bool(img.get('url'))}"
                    for img in images
                )
                signature = f"{job.status}:{job.completed_count}:{url_sig}"
                if signature != last_signature:
                    last_signature = signature
                    idle_ticks = 0
                    line = json.dumps({"type": "progress", "job": payload}, ensure_ascii=False)
                    yield f"data: {line}\n\n"
                else:
                    idle_ticks += 1
                    if idle_ticks % 15 == 0:
                        yield ": keepalive\n\n"

                if job.status in (
                    GenerationJob.Status.SUCCEEDED,
                    GenerationJob.Status.FAILED,
                    GenerationJob.Status.CANCELLED,
                ):
                    line = json.dumps({"type": "progress", "job": payload}, ensure_ascii=False)
                    yield f"data: {line}\n\n"
                    yield "data: {\"type\":\"done\"}\n\n"
                    break
                time.sleep(1)

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class SlotRefineCreateView(APIView):
    """对套图某一槽位发起修复（商品原图 + 当前成图双参考）。"""

    def post(self, request, job_id, index):
        job = get_object_or_404(GenerationJob, pk=job_id, user=request.user)
        try:
            slot_index = int(index)
        except (TypeError, ValueError):
            return Response({"detail": "无效的槽位序号"}, status=400)
        prompt = (request.data.get("prompt") or "").strip()
        if not prompt:
            return Response({"detail": "请填写修复说明"}, status=400)

        gen_img = GeneratedImage.objects.filter(job=job, index=slot_index).first()
        if not gen_img or not gen_img.file:
            return Response({"detail": "该槽位还没有可修复的成图"}, status=400)
        from generation.services.job_references import job_attachment_ids

        if not job_attachment_ids(job):
            return Response({"detail": "该任务缺少商品原图，无法修复"}, status=400)

        image_model = resolve_image_model(request.data.get("image_model"))

        candidate = SlotRefineCandidate.objects.create(
            job=job,
            slot_index=slot_index,
            user=request.user,
            prompt=prompt[:4000],
            image_model=image_model,
            status=SlotRefineCandidate.Status.PENDING,
        )
        run_slot_refine_task.delay(candidate.id)
        data = SlotRefineCandidateSerializer(candidate, context={"request": request}).data
        return Response(data, status=status.HTTP_202_ACCEPTED)


class SlotRefineCandidateDetailView(APIView):
    def get(self, request, candidate_id):
        candidate = get_object_or_404(
            SlotRefineCandidate,
            pk=candidate_id,
            user=request.user,
        )
        return Response(
            SlotRefineCandidateSerializer(candidate, context={"request": request}).data
        )


class SlotRefineCandidateApplyView(APIView):
    def post(self, request, candidate_id):
        candidate = get_object_or_404(
            SlotRefineCandidate,
            pk=candidate_id,
            user=request.user,
        )
        if candidate.status != SlotRefineCandidate.Status.SUCCEEDED:
            return Response({"detail": "候选图尚未就绪"}, status=400)
        try:
            apply_slot_refine_candidate(candidate)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        job = candidate.job
        job.refresh_from_db()
        return Response(
            {
                "candidate": SlotRefineCandidateSerializer(
                    candidate, context={"request": request}
                ).data,
                "job": GenerationJobSerializer(job, context={"request": request}).data,
            }
        )


class SlotRefineCandidateDiscardView(APIView):
    def post(self, request, candidate_id):
        candidate = get_object_or_404(
            SlotRefineCandidate,
            pk=candidate_id,
            user=request.user,
        )
        if candidate.status == SlotRefineCandidate.Status.APPLIED:
            return Response({"detail": "已替换的候选无法丢弃"}, status=400)
        candidate.status = SlotRefineCandidate.Status.DISCARDED
        candidate.save(update_fields=["status"])
        return Response(
            SlotRefineCandidateSerializer(candidate, context={"request": request}).data
        )
