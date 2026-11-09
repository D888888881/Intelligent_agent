from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.db.models import Q
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from Intelligent_agent.model_catalog import catalog_payload

from .models import UserProfile
from .permissions import IsSuperUser
from .serializers import (
    AdminPendingUserSerializer,
    AdminUserSerializer,
    AdminUserUpdateSerializer,
    LoginSerializer,
    PreferencesSerializer,
    RegisterSerializer,
    UserSerializer,
)


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "detail": "注册申请已提交，请等待超级管理员审批通过后再登录。",
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        return Response(UserSerializer(user).data)


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({"detail": "已退出"})


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ModelCatalogView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        profile = None
        if request.user.is_authenticated:
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return Response(catalog_payload(profile))


class PreferencesView(APIView):
    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return Response(catalog_payload(profile))

    def patch(self, request):
        serializer = PreferencesSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        data = serializer.validated_data
        if "chat_model" in data:
            profile.preferred_chat_model = data["chat_model"] or ""
        if "image_model" in data:
            profile.preferred_image_model = data["image_model"] or ""
        if "vision_model" in data:
            profile.preferred_vision_model = data["vision_model"] or ""
        if "default_image_count" in data:
            profile.default_image_count = data["default_image_count"]
        profile.save()
        return Response(
            {
                "user": UserSerializer(request.user).data,
                "catalog": catalog_payload(profile),
            }
        )


@ensure_csrf_cookie
def csrf_cookie_view(request):
    from django.http import JsonResponse

    return JsonResponse({"detail": "CSRF cookie set"})


class AdminPendingRegistrationsView(APIView):
    permission_classes = [IsSuperUser]

    def get(self, request):
        users = (
            User.objects.filter(profile__approval_status=UserProfile.ApprovalStatus.PENDING)
            .select_related("profile")
            .order_by("date_joined")
        )
        return Response(AdminPendingUserSerializer(users, many=True).data)


class AdminPendingCountView(APIView):
    permission_classes = [IsSuperUser]

    def get(self, request):
        count = User.objects.filter(profile__approval_status=UserProfile.ApprovalStatus.PENDING).count()
        return Response({"count": count})


class AdminRegistrationApproveView(APIView):
    permission_classes = [IsSuperUser]

    def post(self, request, user_id: int):
        user = User.objects.filter(pk=user_id).select_related("profile").first()
        if not user:
            return Response({"detail": "用户不存在"}, status=status.HTTP_404_NOT_FOUND)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if profile.approval_status != UserProfile.ApprovalStatus.PENDING:
            return Response({"detail": "该用户不在待审批状态"}, status=status.HTTP_400_BAD_REQUEST)
        user.is_active = True
        user.save(update_fields=["is_active"])
        profile.approval_status = UserProfile.ApprovalStatus.APPROVED
        profile.save(update_fields=["approval_status"])
        return Response(AdminUserSerializer(user).data)


class AdminRegistrationRejectView(APIView):
    permission_classes = [IsSuperUser]

    def post(self, request, user_id: int):
        user = User.objects.filter(pk=user_id).select_related("profile").first()
        if not user:
            return Response({"detail": "用户不存在"}, status=status.HTTP_404_NOT_FOUND)
        if user.is_superuser:
            return Response({"detail": "不能拒绝超级管理员"}, status=status.HTTP_400_BAD_REQUEST)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        user.is_active = False
        user.save(update_fields=["is_active"])
        profile.approval_status = UserProfile.ApprovalStatus.REJECTED
        profile.save(update_fields=["approval_status"])
        return Response(AdminUserSerializer(user).data)


class AdminUsersView(APIView):
    permission_classes = [IsSuperUser]

    def get(self, request):
        try:
            page = max(1, int(request.GET.get("page", 1)))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = int(request.GET.get("page_size", 10))
        except (TypeError, ValueError):
            page_size = 10
        page_size = min(50, max(1, page_size))

        q = (request.GET.get("q") or "").strip()
        active_filter = (request.GET.get("is_active") or "all").lower()

        qs = User.objects.select_related("profile").order_by("-date_joined")
        if q:
            qs = qs.filter(Q(username__icontains=q) | Q(profile__real_name__icontains=q))
        if active_filter == "true":
            qs = qs.filter(is_active=True)
        elif active_filter == "false":
            qs = qs.filter(is_active=False)

        total = qs.count()
        total_pages = max(1, (total + page_size - 1) // page_size)
        if page > total_pages:
            page = total_pages
        offset = (page - 1) * page_size
        users = qs[offset : offset + page_size]

        return Response(
            {
                "count": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "results": AdminUserSerializer(users, many=True).data,
            }
        )


class AdminUserDetailView(APIView):
    permission_classes = [IsSuperUser]

    def patch(self, request, user_id: int):
        user = User.objects.filter(pk=user_id).select_related("profile").first()
        if not user:
            return Response({"detail": "用户不存在"}, status=status.HTTP_404_NOT_FOUND)
        serializer = AdminUserUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        profile, _ = UserProfile.objects.get_or_create(user=user)

        if "is_active" in data and not user.is_superuser:
            user.is_active = data["is_active"]
            user.save(update_fields=["is_active"])
        elif "is_active" in data and user.is_superuser and not data["is_active"]:
            return Response({"detail": "不能禁用超级管理员"}, status=status.HTTP_400_BAD_REQUEST)

        if "approval_status" in data and not user.is_superuser:
            profile.approval_status = data["approval_status"]
            if data["approval_status"] == UserProfile.ApprovalStatus.APPROVED:
                user.is_active = True
                user.save(update_fields=["is_active"])
            elif data["approval_status"] in (
                UserProfile.ApprovalStatus.PENDING,
                UserProfile.ApprovalStatus.REJECTED,
            ):
                user.is_active = False
                user.save(update_fields=["is_active"])
            profile.save(update_fields=["approval_status"])

        profile_fields = []
        if "real_name" in data:
            profile.real_name = (data["real_name"] or "").strip()
            profile_fields.append("real_name")
        if "daily_image_quota" in data:
            profile.daily_image_quota = data["daily_image_quota"]
            profile_fields.append("daily_image_quota")
        if "default_image_count" in data:
            profile.default_image_count = data["default_image_count"]
            profile_fields.append("default_image_count")
        if profile_fields:
            profile.save(update_fields=profile_fields)

        user.refresh_from_db()
        return Response(AdminUserSerializer(user).data)
