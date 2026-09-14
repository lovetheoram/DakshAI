from django.contrib import admin
from .models import Exam, Subject, Topic, Subtopic, Concept, PYQ


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "exam_type", "description")
    list_filter = ("exam_type",)
    search_fields = ("name", "description")


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "exam", "order")
    list_filter = ("exam",)
    search_fields = ("name",)


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "subject", "order")
    list_filter = ("subject__exam", "subject")
    search_fields = ("name",)


@admin.register(Subtopic)
class SubtopicAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "topic", "order")
    list_filter = ("topic__subject__exam", "topic__subject")
    search_fields = ("name",)


@admin.register(Concept)
class ConceptAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "subtopic", "order")
    list_filter = ("subtopic__topic__subject__exam", "subtopic__topic__subject")
    search_fields = ("name", "description")


@admin.register(PYQ)
class PYQAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "exam_source",
        "exam_year",
        "concept",
        "source_book",
        "source_page",
        "source_question_number",
        "extraction_confidence",
        "needs_review",
    )
    list_filter = ("exam_source", "exam_year", "needs_review", "source_book")
    search_fields = ("question_text", "explanation", "source_book", "exam_source")
    ordering = ("-exam_year", "id")
