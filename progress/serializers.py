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
