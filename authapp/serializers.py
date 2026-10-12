from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from syllabus.models import Exam
from .models import UserProfile

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    exam_type = serializers.CharField()
    pcs_section = serializers.CharField(required=False, default="BPSC")

    class Meta:
        model = User
        fields = ["username", "email", "password", "exam_type", "pcs_section"]

    def create(self, validated_data):
        exam_type = validated_data.pop("exam_type")
        pcs_section = validated_data.pop("pcs_section", "BPSC") or "BPSC"
        clean_username = validated_data["username"].strip().lower()

        user = User.objects.create_user(
            username=clean_username,
            email=validated_data["email"].strip().lower(),
            password=validated_data["password"],
        )
        exam = Exam.objects.filter(exam_type=exam_type).first()
        if not exam:
            exam = Exam.objects.first()
        if exam:
            user.profile.selected_exam = exam
            user.profile.pcs_section = pcs_section
            user.profile.save()

            # Goal is set by the Welcomer upon first login with user's real target date and promise.

        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        raw_username = data.get("username", "").strip().lower()
        password = data.get("password", "")

        # Lookup user case-insensitively
        try:
            target_user = User.objects.get(username__iexact=raw_username)
            user = authenticate(username=target_user.username, password=password)
        except User.DoesNotExist:
            user = None

        if not user:
            raise serializers.ValidationError("Invalid credentials")
        data["user"] = user
        return data


class UserSerializer(serializers.ModelSerializer):
    selected_exam = serializers.SerializerMethodField()
    pcs_section = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    education_stage = serializers.SerializerMethodField()
    institution_name = serializers.SerializerMethodField()
    grade_or_year = serializers.SerializerMethodField()
    location_city = serializers.SerializerMethodField()
    interests = serializers.SerializerMethodField()
    skills = serializers.SerializerMethodField()
    is_minor = serializers.SerializerMethodField()
    privacy_settings = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "display_name",
            "bio",
            "avatar",
            "selected_exam",
            "pcs_section",
            "education_stage",
            "institution_name",
            "grade_or_year",
            "location_city",
            "interests",
            "skills",
            "is_minor",
            "privacy_settings",
        ]

    def get_pcs_section(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.pcs_section if profile else "BPSC"

    def get_display_name(self, obj):
        profile = getattr(obj, "profile", None)
        return (profile.display_name if profile and profile.display_name else obj.username)

    def get_bio(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.bio if profile else ""

    def get_avatar(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.avatar if profile else ""

    def get_education_stage(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.education_stage if profile else "class_11_12"

    def get_institution_name(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.institution_name if profile else ""

    def get_grade_or_year(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.grade_or_year if profile else ""

    def get_location_city(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.location_city if profile else ""

    def get_interests(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.interests if profile and isinstance(profile.interests, list) else []

    def get_skills(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.skills if profile and isinstance(profile.skills, list) else []

    def get_is_minor(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.is_minor if profile else False

    def get_privacy_settings(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.get_privacy() if profile else {}

    def get_selected_exam(self, obj):
        profile = getattr(obj, "profile", None)
        if not profile or not profile.selected_exam:
            return None

        return {
            "id": profile.selected_exam.id,
            "name": profile.selected_exam.name,
            "exam_type": profile.selected_exam.exam_type
        }


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "username",
            "email",
            "display_name",
            "bio",
            "avatar",
            "education_stage",
            "institution_name",
            "grade_or_year",
            "location_city",
            "interests",
            "skills",
            "is_minor",
            "privacy_settings",
            "pcs_section",
        ]