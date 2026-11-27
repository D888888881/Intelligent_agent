import io
import json
import zipfile

from django.conf import settings
from django.http import HttpResponse, StreamingHttpResponse
from Intelligent_agent.renderers import EventStreamRenderer
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from chat.models import Conversation, Message
from generation.models import GeneratedImage, GenerationJob, SlotRefineCandidate
from generation.renderers import GenerationDownloadRenderersMixin
from generation.serializers import GenerationJobSerializer, SlotRefineCandidateSerializer
from generation.services.slot_refine import apply_slot_refine_candidate
from generation.services.dispatch import dispatch_slot_refine
from generation.services.intent import parse_image_count_from_prompt, resolve_generation_params
from generation.services.job_references import normalize_attachment_id_list
from generation.services.prepare import start_prepare_and_run_async
from Intelligent_agent.media_urls import resolve_media_file_url
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
        att_ids_preview = normalize_attachment_id_list(request.data.get("attachment_ids"))
        legacy_id = request.data.get("attachment_id")
        if legacy_id and not att_ids_preview:
            att_ids_preview = normalize_attachment_id_list([legacy_id])
        conversation_id = request.data.get("conversation_id")
        conversation = None
        if conversation_id:
            conversation = get_object_or_404(
                Conversation,
                pk=conversation_id,
                user=request.user,
            )

        from generation.services.marketplace_profiles import (
            coerce_generation_for_marketplace,
            resolve_effective_marketplace_id,
        )

        marketplace_id = resolve_effective_marketplace_id(
            request_marketplace=request.data.get("marketplace_id"),
            conversation=conversation,
            user=request.user,
        )
        image_count, plan_template = resolve_generation_params(
            prompt,
            image_count=image_count,
            plan_template=plan_template,
            reference_attachment_count=len(att_ids_preview),
            marketplace_id=marketplace_id,
        )
        image_count, plan_template = coerce_generation_for_marketplace(
            marketplace_id, plan_template, image_count
        )

        att_ids = att_ids_preview
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
        background_mode = (request.data.get("background_mode") or "random").strip().lower()
        if background_mode not in ("random", "solid_virtual", "real_environment"):
            background_mode = "random"
        # 默认直接生图；仅当 plan_preview_only=true（前端勾选「策划预览模式」）时先策划再确认
        plan_preview_only = bool(request.data.get("plan_preview_only"))
        reuse_creative = (request.data.get("reuse_creative_concept_id") or "").strip()

        from generation.services.aspect_ratio import resolve_aspect_ratio

        aspect_ratio = resolve_aspect_ratio(request.data.get("aspect_ratio"))

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
                "background_mode": background_mode,
                "plan_template": plan_template,
                "marketplace_id": marketplace_id,
                "aspect_ratio": aspect_ratio,
                **({"reuse_creative_concept_id": reuse_creative} if reuse_creative else {}),
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
                        "url": resolve_media_file_url(a.file, request),
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
            run_after_prepare=not plan_preview_only,
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
        job = get_object_or_404(
            GenerationJob.objects.prefetch_related("images"),
            pk=job_id,
            user=request.user,
        )
        from generation.services.job_recovery import refresh_generation_job_state

        job = refresh_generation_job_state(job)
        return Response(GenerationJobSerializer(job, context={"request": request}).data)


class GenerationDownloadAllView(GenerationDownloadRenderersMixin, APIView):
    """将套图成片打包为 ZIP（同源下载，避免 COS 跨域导致 download 无效）。"""

    def finalize_response(self, request, response, *args, **kwargs):
        if isinstance(response, HttpResponse):
            return response
        return super().finalize_response(request, response, *args, **kwargs)

    def get(self, request, job_id):
        job = get_object_or_404(GenerationJob, pk=job_id, user=request.user)
        from generation.services.job_recovery import refresh_generation_job_state

        job = refresh_generation_job_state(job)
        images = (
            job.images.filter(status=GeneratedImage.Status.SUCCEEDED)
            .exclude(file="")
            .order_by("index")
        )
        if not images.exists():
            return Response({"detail": "暂无可下载的成片"}, status=status.HTTP_400_BAD_REQUEST)

        buf = io.BytesIO()
        added = 0
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for img in images:
                ext = ".png"
                if img.file and img.file.name and "." in img.file.name:
                    ext = "." + img.file.name.rsplit(".", 1)[-1].lower()
                arcname = f"job{job_id}_slot{img.index}{ext}"
                try:
                    with img.file.open("rb") as fh:
                        zf.writestr(arcname, fh.read())
                        added += 1
                except OSError:
                    continue
        if added <= 0:
            return Response(
                {"detail": "读取图片文件失败，请稍后重试"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        payload = buf.getvalue()
        response = HttpResponse(payload, content_type="application/zip")
        response["Content-Disposition"] = (
            f'attachment; filename="generation_{job_id}_{added}images.zip"'
        )
        response["Content-Length"] = str(len(payload))
        return response


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
            GenerationJob.Status.RUNNING,
        ):
            job.status = GenerationJob.Status.CANCELLED
            job.finished_at = timezone.now()
            if not job.error_message:
                job.error_message = "用户已取消任务"
        job.save()
        from generation.services.dispatch import dispatch_next_for_user
        from generation.tasks import _update_assistant_message

        _update_assistant_message(job)
        dispatch_next_for_user(job.user_id)
        return Response(GenerationJobSerializer(job, context={"request": request}).data)


def _sse_payload_gallery_incomplete(job: GenerationJob, payload: dict) -> bool:
    """序列化结果里仍有镜头无 URL（含 failed 待 promote）时勿过早结束 SSE。"""
    total = int(job.image_count or 0)
    if total <= 0:
        return False
    terminal = job.status in (
        GenerationJob.Status.SUCCEEDED,
        GenerationJob.Status.FAILED,
        GenerationJob.Status.CANCELLED,
    )
    by_index = {int(im.get("index") or 0): im for im in (payload.get("images") or [])}
    for i in range(1, total + 1):
        im = by_index.get(i)
        if not im:
            return True
        st = (im.get("status") or "").lower()
        if st in ("running", "pending"):
            return True
        if im.get("url"):
            continue
        if st == "succeeded":
            return True
        if st == "failed" and terminal:
            return True
    return False


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
            stream_job = job
            while True:
                stream_job.refresh_from_db()
                from generation.services.job_recovery import refresh_generation_job_state

                stream_job = refresh_generation_job_state(stream_job)
                payload = GenerationJobSerializer(stream_job, context={"request": request}).data
                images = payload.get("images") or []
                url_sig = "|".join(
                    f"{img.get('index')}:{img.get('status')}:{bool(img.get('url'))}"
                    for img in images
                )
                signature = f"{stream_job.status}:{stream_job.completed_count}:{url_sig}"
                if signature != last_signature:
                    last_signature = signature
                    idle_ticks = 0
                    line = json.dumps({"type": "progress", "job": payload}, ensure_ascii=False)
                    yield f"data: {line}\n\n"
                else:
                    idle_ticks += 1
                    if idle_ticks % 15 == 0:
                        yield ": keepalive\n\n"

                if stream_job.status in (
                    GenerationJob.Status.SUCCEEDED,
                    GenerationJob.Status.FAILED,
                    GenerationJob.Status.CANCELLED,
                ):
                    pending_slots = stream_job.images.filter(
                        status__in=(
                            GeneratedImage.Status.PENDING,
                            GeneratedImage.Status.RUNNING,
                        )
                    ).exists()
                    out_of_sync_failed = stream_job.images.filter(
                        status=GeneratedImage.Status.FAILED
                    ).exclude(file="").exists()
                    gallery_lagging = _sse_payload_gallery_incomplete(stream_job, payload)
                    if (
                        (pending_slots or out_of_sync_failed or gallery_lagging)
                        and idle_ticks < 180
                    ):
                        time.sleep(1)
                        continue
                    line = json.dumps({"type": "progress", "job": payload}, ensure_ascii=False)
                    yield f"data: {line}\n\n"
                    yield "data: {\"type\":\"done\"}\n\n"
                    break
                time.sleep(1)

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class GenerationConfirmRunView(APIView):
    """策划预览确认后开始生图。"""

    def post(self, request, job_id):
        job = get_object_or_404(GenerationJob, pk=job_id, user=request.user)
        plan = job.plan_json or {}
        if not plan.get("awaiting_generation_confirm"):
            return Response({"detail": "该任务无需确认或已开始生图"}, status=status.HTTP_400_BAD_REQUEST)
        plan = dict(plan)
        plan.pop("awaiting_generation_confirm", None)
        plan.pop("plan_ready", None)
        from generation.services.listing_bundle import is_listing_ecommerce_plan
        from generation.services.listing_run_prepare import prepare_listing_plan_for_generation

        if is_listing_ecommerce_plan(plan):
            plan = prepare_listing_plan_for_generation(plan, job=job)
        job.plan_json = plan
        job.save(update_fields=["plan_json"])
        from generation.services.dispatch import enqueue_or_run

        enqueue_or_run(job)
        job.refresh_from_db()
        if job.conversation_id:
            msg = (
                Message.objects.filter(
                    conversation_id=job.conversation_id,
                    role=Message.Role.ASSISTANT,
                    metadata__generation_job_id=job.id,
                )
                .order_by("-id")
                .first()
            )
            if msg:
                meta = dict(msg.metadata or {})
                meta["awaiting_generation_confirm"] = False
                meta["plan_preview_mode"] = False
                meta.pop("planning_summary", None)
                meta.pop("plan_ready", None)
                msg.metadata = meta
                msg.save(update_fields=["metadata"])
        from generation.tasks import _update_assistant_message

        _update_assistant_message(job)
        return Response(GenerationJobSerializer(job, context={"request": request}).data)


class GenerationRetrategyView(APIView):
    """步骤三：重新分析卖点并更新策划文案。"""

    def post(self, request, job_id):
        job = get_object_or_404(GenerationJob, pk=job_id, user=request.user)
        if job.status == GenerationJob.Status.RUNNING:
            return Response({"detail": "任务正在生图，请稍后再优化卖点"}, status=status.HTTP_400_BAD_REQUEST)
        regenerate_images = bool(request.data.get("regenerate_images"))
        vision_model = resolve_vision_model(request.data.get("vision_model"))
        try:
            from generation.services.plan_restrategy import reoptimize_job_plan

            plan = reoptimize_job_plan(
                job,
                vision_model=vision_model,
                regenerate_images=regenerate_images,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        job.refresh_from_db()
        if regenerate_images:
            from generation.services.dispatch import enqueue_or_run

            enqueue_or_run(job)
        return Response(
            {
                "job": GenerationJobSerializer(job, context={"request": request}).data,
                "planning_summary": plan.get("planning_summary") or "",
            }
        )


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

        ref_mode = (request.data.get("reference_mode") or "dual").strip().lower()
        if ref_mode not in ("dual", "upload_only"):
            ref_mode = "dual"

        ref_attachment = None
        ref_ids: list[int] = []
        if ref_mode == "upload_only":
            from django.conf import settings

            from generation.services.job_references import normalize_attachment_id_list
            from uploads.models import Attachment

            raw_ids = request.data.get("reference_attachment_ids")
            if raw_ids is None:
                raw_ids = request.data.get("reference_attachment_id")
            ref_ids = normalize_attachment_id_list(raw_ids)[: settings.GEN_MAX_REFERENCE_IMAGES]
            if not ref_ids:
                return Response({"detail": "请上传并选择参考图"}, status=400)
            found = {
                a.id: a
                for a in Attachment.objects.filter(pk__in=ref_ids, user=request.user)
            }
            ordered = [found[i] for i in ref_ids if found.get(i) and found[i].file]
            if len(ordered) != len(ref_ids):
                return Response({"detail": "参考图无效或无权访问"}, status=400)
            ref_attachment = ordered[0]
            ref_ids = [a.id for a in ordered]
        else:
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
            reference_mode=ref_mode,
            reference_attachment=ref_attachment,
            reference_attachment_ids=ref_ids,
            status=SlotRefineCandidate.Status.PENDING,
        )
        dispatch_slot_refine(candidate.id)
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
