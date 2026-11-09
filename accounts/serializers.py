from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import serializers

from Intelligent_agent.model_catalog import (
    chat_model_ids,
    image_model_ids,
    resolve_chat_model,
    resolve_image_model,
    resolve_vision_model,
    vision_model_ids,
)

from .models import UserProfile


class UserSerializer(serializers.ModelSerializer):
    default_image_count = serializers.SerializerMethodField()
    chat_model = serializers.SerializerMethodField()
    image_model = serializers.SerializerMethodField()
    vision_model = serializers.SerializerMethodField()
    approval_status = serializers.SerializerMethodField()
    real_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "is_superuser",
            "real_name",
            "default_image_count",
            "chat_model",
            "image_model",
            "vision_model",
            "approval_status",
        )

    def get_approval_status(self, obj):
        return self._profile(obj).approval_status

    def get_real_name(self, obj):
        return self._profile(obj).real_name or ""

    def _profile(self, obj):
        return UserProfile.objects.get_or_create(user=obj)[0]

    def get_default_image_count(self, obj):
        return self._profile(obj).default_image_count

    def get_chat_model(self, obj):
        profile = self._profile(obj)
        return resolve_chat_model(profile.preferred_chat_model or None)

    def get_image_model(self, obj):
        profile = self._profile(obj)
        return resolve_image_model(profile.preferred_image_model or None)

    def get_vision_model(self, obj):
        profile = self._profile(obj)
        return resolve_vision_model(profile.preferred_vision_model or None)


class PreferencesSerializer(serializers.Serializer):
    chat_model = serializers.CharField(required=False, allow_blank=True, max_length=64)
    image_model = serializers.CharField(required=False, allow_blank=True, max_length=64)
    vision_model = serializers.CharField(required=False, allow_blank=True, max_length=64)
    default_image_count = serializers.IntegerField(required=False, min_value=1, max_value=12)

    def validate_chat_model(self, value):
        if not value:
            return value
        if value not in chat_model_ids():
            raise serializers.ValidationError("不支持的对话模型")
        return value

    def validate_image_model(self, value):
        if not value:
            return value
        if value not in image_model_ids():
            raise serializers.ValidationError("不支持的生图模型")
        return value

    def validate_vision_model(self, value):
        if not value:
            return value
        if value not in vision_model_ids():
            raise serializers.ValidationError("不支持的识图模型")
        return value


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    real_name = serializers.CharField(max_length=64)
    password = serializers.CharField(write_only=True, min_length=6)

    def validate_real_name(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("请填写真实名称")
        return value

    def validate_username(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("请填写用户名")
        existing = User.objects.filter(username=value).first()
        if not existing:
            return value
        profile = UserProfile.objects.filter(user=existing).first()
        if profile and profile.approval_status == UserProfile.ApprovalStatus.REJECTED:
            return value
        raise serializers.ValidationError("用户名已存在")

    def create(self, validated_data):
        real_name = validated_data["real_name"]
        existing = User.objects.filter(username=validated_data["username"]).first()
        if existing:
            existing.set_password(validated_data["password"])
            existing.is_active = False
            existing.save(update_fields=["password", "is_active"])
            profile, _ = UserProfile.objects.get_or_create(user=existing)
            profile.approval_status = UserProfile.ApprovalStatus.PENDING
            profile.real_name = real_name
            profile.save(update_fields=["approval_status", "real_name"])
            return existing
        user = User.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
            is_active=False,
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.approval_status = UserProfile.ApprovalStatus.PENDING
        profile.real_name = real_name
        profile.save(update_fields=["approval_status", "real_name"])
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(
            username=attrs["username"],
            password=attrs["password"],
        )
        if not user:
            cred = User.objects.filter(username=attrs["username"]).first()
            if cred and cred.check_password(attrs["password"]):
                profile, _ = UserProfile.objects.get_or_create(user=cred)
                if profile.approval_status == UserProfile.ApprovalStatus.PENDING:
                    raise serializers.ValidationError("账号待管理员审批，通过后可登录")
                if profile.approval_status == UserProfile.ApprovalStatus.REJECTED:
                    raise serializers.ValidationError("注册申请已被拒绝，请联系超级管理员")
            raise serializers.ValidationError("用户名或密码错误")
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if not user.is_superuser and profile.approval_status != UserProfile.ApprovalStatus.APPROVED:
            if profile.approval_status == UserProfile.ApprovalStatus.PENDING:
                raise serializers.ValidationError("账号待管理员审批，通过后可登录")
            raise serializers.ValidationError("注册申请已被拒绝，请联系超级管理员")
        if not user.is_active:
            raise serializers.ValidationError("账号未启用，请联系超级管理员")
        attrs["user"] = user
        return attrs


class AdminPendingUserSerializer(serializers.ModelSerializer):
    approval_status = serializers.SerializerMethodField()
    real_name = serializers.SerializerMethodField()
    date_joined = serializers.DateTimeField(read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "real_name", "date_joined", "approval_status")

    def _profile(self, obj):
        return UserProfile.objects.get_or_create(user=obj)[0]

    def get_approval_status(self, obj):
        return self._profile(obj).approval_status

    def get_real_name(self, obj):
        return self._profile(obj).real_name or ""


class AdminUserSerializer(serializers.ModelSerializer):
    approval_status = serializers.SerializerMethodField()
    real_name = serializers.SerializerMethodField()
    default_image_count = serializers.SerializerMethodField()
    daily_image_quota = serializers.SerializerMethodField()
    date_joined = serializers.DateTimeField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "real_name",
            "is_active",
            "is_superuser",
            "date_joined",
            "approval_status",
            "default_image_count",
            "daily_image_quota",
        )

    def _profile(self, obj):
        return UserProfile.objects.get_or_create(user=obj)[0]

    def get_approval_status(self, obj):
        return self._profile(obj).approval_status

    def get_real_name(self, obj):
        return self._profile(obj).real_name or ""

    def get_default_image_count(self, obj):
        return self._profile(obj).default_image_count

    def get_daily_image_quota(self, obj):
        return self._profile(obj).daily_image_quota


class AdminUserUpdateSerializer(serializers.Serializer):
    real_name = serializers.CharField(required=False, allow_blank=True, max_length=64)
    is_active = serializers.BooleanField(required=False)
    approval_status = serializers.ChoiceField(
        required=False,
        choices=UserProfile.ApprovalStatus.choices,
    )
    daily_image_quota = serializers.IntegerField(required=False, min_value=0, max_value=100000)
    default_image_count = serializers.IntegerField(required=False, min_value=1, max_value=12)
