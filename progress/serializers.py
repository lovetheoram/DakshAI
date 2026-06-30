from rest_framework import serializers
from .models import ConceptProgress, ProgressRecord, SubtopicProgress
from quiz.models import QuizAnswer
from quiz.serializers import QuizAnswerReviewSerializer
class ConceptProgressSerializer(serializers.ModelSerializer):
    exam_readiness = serializers.FloatField(read_only=True)
    chapter_understanding = serializers.FloatField(read_only=True)
    last_practiced = serializers.DateTimeField(read_only=True)

    class Meta:
        model = ConceptProgress
        fields = ["user", "concept", "exam_readiness", "chapter_understanding", "last_practiced"]


class SubtopicProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubtopicProgress
        fields = ["user", "subtopic", "efficiency", "last_updated"]


# class ProgressRecordSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = ProgressRecord
#         fields = [
#             "id", "concept", "quiz_session", "score", "correct_count", "wrong_count",
#             "main_correct", "main_total", "sub_correct", "sub_total", "created_at"
#         ]


from rest_framework import serializers

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
            "answers",  # add answers here
        ]

    def get_answers(self, obj):
        # Get all quiz answers for this progress record's session
        session = obj.quiz_session
        answers = QuizAnswer.objects.filter(session=session)
        return QuizAnswerReviewSerializer(answers, many=True).data


from .models import UserGoal, DailyTarget, DailyDiaryEntry

class UserGoalSerializer(serializers.ModelSerializer):
    exam_name = serializers.CharField(source="exam.name", read_only=True)
    progress = serializers.SerializerMethodField()

    class Meta:
        model = UserGoal
        fields = [
            "id", "user", "exam", "exam_name", "goal_name",
            "target_date", "available_hours_per_day", "created_at", "updated_at",
            "progress"
        ]
        read_only_fields = ["user", "created_at", "updated_at"]

    def get_progress(self, obj):
        from .services import ProgressService
        return ProgressService.get_user_daksh_score(obj.user, obj.exam)


class DailyTargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyTarget
        fields = [
            "id", "user", "date", "target_growth", "completed_growth", "is_completed"
        ]
        read_only_fields = ["user", "date", "is_completed"]


class DailyDiaryEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyDiaryEntry
        fields = [
            "id", "user", "date", "concepts_attempted", "concepts_completed",
            "questions_solved", "questions_correct", "time_spent_seconds",
            "revision_count", "energy_score", "focus_score", "mood",
            "knowledge_gain", "accuracy", "daily_growth_percentage"
        ]
        read_only_fields = ["user", "date"]

