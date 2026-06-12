from rest_framework import serializers
from .models import Question, SubQuestion, QuizSession, QuizAnswer


# ---------------- QUESTIONS ----------------

class SubQuestionSerializer(serializers.ModelSerializer):
    sub_id = serializers.ReadOnlyField()

    class Meta:
        model = SubQuestion
        fields = [
            "sub_id",
            "type",
            "question",
            "option_a",
            "option_b",
            "option_c",
            "option_d",
        ]


class QuestionSerializer(serializers.ModelSerializer):
    sub_questions = SubQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = [
            "qid",
            "header",
            "question_title",
            "question",
            "option_a",
            "option_b",
            "option_c",
            "option_d",
            "source",
            "sub_questions",
        ]


# ---------------- ANSWER INPUT ----------------

class QuizAnswerInSerializer(serializers.Serializer):
    question_id = serializers.CharField()
    sub_question_type = serializers.ChoiceField(
        choices=["comfort", "grounding", "precursor"],
        required=False
    )
    marked_option = serializers.ChoiceField(
        choices=["A", "B", "C", "D"]
    )


# ---------------- ANSWER REVIEW ----------------

from rest_framework import serializers
from .models import QuizAnswer, Question, SubQuestion

class QuizAnswerReviewSerializer(serializers.ModelSerializer):
    question_id = serializers.SerializerMethodField()
    sub_question_type = serializers.SerializerMethodField()
    correct_option = serializers.SerializerMethodField()
    question_text = serializers.SerializerMethodField()
    options = serializers.SerializerMethodField()

    class Meta:
        model = QuizAnswer
        fields = [
            "question_id",
            "sub_question_type",
            "marked_option",
            "correct_option",
            "is_correct",
            "question_text",
            "options",
        ]

    def get_question_id(self, obj):
        return (
            obj.question.qid
            if obj.question
            else obj.sub_question.parent.qid
        )

    def get_sub_question_type(self, obj):
        return obj.sub_question.type if obj.sub_question else None

    def get_correct_option(self, obj):
        return (
            obj.sub_question.correct_option
            if obj.sub_question
            else obj.question.correct_option
        )

    def get_question_text(self, obj):
        if obj.sub_question:
            return obj.sub_question.question
        return obj.question.question

    def get_options(self, obj):
        if obj.sub_question:
            return obj.sub_question.options_dict()
        return obj.question.options_dict()
