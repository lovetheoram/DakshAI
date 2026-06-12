from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from syllabus.models import Exam
from .models import UserProfile

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    exam_id= serializers.IntegerField()
    class Meta:
        model = User
        fields = ["username", "email", "password", "exam_id"]

    def create(self, validated_data):
        exam_id = validated_data.pop("exam_id")
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )
        user.profile.selected_exam_id=exam_id
        user.profile.save()
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        user = authenticate(
            username=data.get("username"), password=data.get("password")
        )
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        data["user"] = user
        return data


# class UserSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = User
#         fields = ["id", "username", "email"]

class UserSerializer(serializers.ModelSerializer):

    selected_exam = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "selected_exam"
        ]

    def get_selected_exam(self, obj):
        profile = getattr(obj, "profile", None)

        if not profile or not profile.selected_exam:
            return None

        return {
            "id": profile.selected_exam.id,
            "name": profile.selected_exam.name
        }