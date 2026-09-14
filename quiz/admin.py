from django.contrib import admin
from .models import Question, SubQuestion, QuizSession, QuizAnswer


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("qid", "header", "concept", "source", "mode", "created_at")
    list_filter = ("source", "mode", "concept__subtopic__topic__subject__exam")
    search_fields = ("qid", "header", "question", "explanation")


@admin.register(SubQuestion)
class SubQuestionAdmin(admin.ModelAdmin):
    list_display = ("sub_id", "type", "parent", "concept")
    list_filter = ("type",)
    search_fields = ("question",)


@admin.register(QuizSession)
class QuizSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "mode", "total_questions", "score", "created_at", "completed_at")
    list_filter = ("mode", "created_at")
    search_fields = ("user__username",)


@admin.register(QuizAnswer)
class QuizAnswerAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "question", "sub_question", "marked_option", "is_correct", "created_at")
    list_filter = ("is_correct", "marked_option")
