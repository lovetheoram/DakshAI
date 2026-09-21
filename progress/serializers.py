from rest_framework import serializers
from .models import ConceptProgress, ProgressRecord, SubtopicProgress, UserGoal, DailyTarget, DailyDiaryEntry
from quiz.models import QuizAnswer
from quiz.serializers import QuizAnswerReviewSerializer


class ConceptProgressSerializer(serializers.ModelSerializer):
    readiness = serializers.FloatField(read_only=True)
    last_practiced = serializers.DateTimeField(read_only=True)
    mastery = serializers.SerializerMethodField()

    class Meta:
        model = ConceptProgress
        fields = [
            "user",
            "concept",
            "readiness",
            "mastery",
            "last_practiced",
        ]

    def get_mastery(self, obj):
        return obj.get_mastery() if obj else 0.0


class SubtopicProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubtopicProgress
        fields = ["user", "subtopic", "efficiency", "last_updated"]


class ProgressRecordSerializer(serializers.ModelSerializer):
    answers = serializers.SerializerMethodField()

    class Meta:
        model = ProgressRecord
        fields = [
            "id",
            "concept",
            "quiz_session",
            "score",
            "main_correct",
            "main_total",
            "sub_correct",
            "sub_total",
            "created_at",
            "answers",
        ]

    def get_answers(self, obj):
        session = obj.quiz_session
        answers = QuizAnswer.objects.filter(session=session)
        return QuizAnswerReviewSerializer(answers, many=True).data


class UserGoalSerializer(serializers.ModelSerializer):
    exam_name = serializers.CharField(source="exam.name", read_only=True)
    progress = serializers.SerializerMethodField()

    class Meta:
        model = UserGoal
        fields = [
            "id", "user", "exam", "exam_name", "goal_name",
            "target_date", "available_hours_per_day", "is_active",
            "created_at", "updated_at", "progress"
        ]
        read_only_fields = ["user", "created_at", "updated_at"]

    def get_progress(self, obj):
        from .services import ProgressService
        return ProgressService.get_user_daksh_score(obj.user, obj.exam)


class DailyTargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyTarget
        fields = [
            "id", "user", "date", "required_readiness_per_day",
        ]
        read_only_fields = ["user", "date"]


class DailyDiaryEntrySerializer(serializers.ModelSerializer):
    has_activity = serializers.SerializerMethodField()
    accuracy = serializers.SerializerMethodField()

    class Meta:
        model = DailyDiaryEntry
        fields = [
            "id", "user", "date", "opened_at",
            "concepts_attempted", "concepts_completed",
            "questions_solved", "questions_correct", "time_spent_seconds",
            "readiness_delta", "has_activity", "accuracy",
        ]
        read_only_fields = ["user", "date"]

    def get_has_activity(self, obj):
        return obj.questions_solved > 0

    def get_accuracy(self, obj):
        if obj.questions_solved > 0:
            return round(obj.questions_correct / obj.questions_solved, 4)
        return None
