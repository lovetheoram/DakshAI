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

            # Auto-create default UserGoal so new users are NOT prompted for exam twice
            try:
                from progress.models import UserGoal
                import datetime
                target_date = datetime.date.today() + datetime.timedelta(days=180)
                UserGoal.objects.get_or_create(
                    user=user,
                    exam=exam,
                    defaults={
                        "goal_name": f"Crack {exam.name}",
                        "target_date": target_date,
                        "available_hours_per_day": 2.0,
                    }
                )
            except Exception as e:
                print("Failed auto-creating goal on register:", e)

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

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "selected_exam",
            "pcs_section"
        ]

    def get_pcs_section(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.pcs_section if profile else "BPSC"

    def get_selected_exam(self, obj):
        profile = getattr(obj, "profile", None)

        if not profile or not profile.selected_exam:
            return None

        return {
            "id": profile.selected_exam.id,
            "name": profile.selected_exam.name,
            "exam_type": profile.selected_exam.exam_type
        }