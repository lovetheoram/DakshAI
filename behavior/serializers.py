from rest_framework import serializers
from .models import UserBehaviorEvent, UserMindProfile, CatalystMessage, UserStateSnapshot


class UserBehaviorEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserBehaviorEvent
        fields = ["id", "event_type", "metadata", "created_at"]
        read_only_fields = ["id", "created_at"]


class UserMindProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserMindProfile
        fields = [
            "confidence_score", "momentum_score", "momentum_direction",
            "current_state", "fear_areas", "strength_areas", "avoidance_pattern",
            "best_study_hour", "avg_session_length", "last_active", "last_computed",
        ]


class CatalystMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CatalystMessage
        fields = ["id", "trigger", "title", "body", "cta_text", "cta_action", "weight"]
