from rest_framework import serializers
from .models import ConceptProgress, ProgressRecord, SubtopicProgress
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
    completion_percentage = serializers.ReadOnlyField()
    checked_in_today = serializers.BooleanField(source="study_checked_in", read_only=True)
    checkin_growth = serializers.SerializerMethodField()
    questions_growth = serializers.SerializerMethodField()

    class Meta:
        model = DailyTarget
        fields = [
            "id", "user", "date", "study_checked_in", "checked_in_today",
            "completed_correct_questions", "target_correct_questions",
            "checkin_growth", "questions_growth",
            "completion_percentage", "target_growth", "completed_growth", "is_completed"
        ]
        read_only_fields = ["user", "date", "is_completed", "completion_percentage"]

    def get_checkin_growth(self, obj):
        return 50.0 if obj.study_checked_in else 0.0

    def get_questions_growth(self, obj):
        if obj.target_correct_questions <= 0:
            return 50.0
        return round(min(50.0, (obj.completed_correct_questions / obj.target_correct_questions) * 50.0), 1)


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

