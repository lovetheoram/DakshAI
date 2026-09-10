

from django.db import models


class Exam(models.Model):
    EXAM_TYPE_CHOICES = [
        ("jee", "JEE Main"),
        ("neet", "NEET"),
        ("placement", "Placement Preparation"),
        ("pcs", "State PCS (BPSC, UPPCS, etc.)"),
    ]

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    exam_type = models.CharField(
        max_length=50,
        choices=EXAM_TYPE_CHOICES,
        default="jee",
        help_text="Determines which prompt module is used for AI generation"
    )

    def __str__(self):
        return self.name


class Subject(models.Model):
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name="subjects"
    )
    name = models.CharField(max_length=255)
    order = models.IntegerField(default=0)

    class Meta:
        unique_together = ("exam", "name")
        ordering = ["order"]

    def __str__(self):
        return self.name


class Topic(models.Model):
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="topics"
    )
    name = models.CharField(max_length=255)
    order = models.IntegerField(default=0)

    class Meta:
        unique_together = ("subject", "name")
        ordering = ["order"]

    def __str__(self):
        return self.name


class Subtopic(models.Model):
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name="subtopics"
    )
    name = models.CharField(max_length=255)
    order = models.IntegerField(default=0)

    class Meta:
        unique_together = ("topic", "name")
        ordering = ["order"]

    def __str__(self):
        return self.name


class Concept(models.Model):
    subtopic = models.ForeignKey(
        Subtopic,
        on_delete=models.CASCADE,
        related_name="concepts"
    )
    name = models.CharField(max_length=255)
    description = models.TextField()

    order = models.IntegerField(default=0)

    # Optional but useful for AI / SDQB
    ai_meta = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("subtopic", "name")
        ordering = ["order"]

    def __str__(self):
        return self.name


class PYQ(models.Model):
    concept = models.ForeignKey(
        Concept,
        on_delete=models.CASCADE,
        related_name="pyqs"
    )
    question_text = models.TextField()
    options = models.JSONField(default=list)
    correct_answer = models.CharField(max_length=255)
    explanation = models.TextField()

    # Exam source tracking
    exam_source = models.CharField(max_length=255)
    exam_year = models.IntegerField(null=True, blank=True)

    # Traceability & Provenance
    source_book = models.CharField(max_length=255, blank=True, default="Ghatnachakra Indian History 2025")
    source_page = models.IntegerField(null=True, blank=True)
    source_question_number = models.CharField(max_length=100, blank=True)

    # Structured "Alive Experience" Summary (keys: trend, pattern, trap, memory_hook)
    experiential_summary = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured dict with keys: trend, pattern, trap, memory_hook"
    )

    extraction_confidence = models.FloatField(null=True, blank=True, default=1.0)
    needs_review = models.BooleanField(default=False)
    content_hash = models.CharField(max_length=32, unique=True, null=True, blank=True)

    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"[{self.exam_source}] {self.question_text[:50]}..."


from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

@receiver([post_save, post_delete], sender=Exam)
@receiver([post_save, post_delete], sender=Subject)
@receiver([post_save, post_delete], sender=Topic)
@receiver([post_save, post_delete], sender=Subtopic)
@receiver([post_save, post_delete], sender=Concept)
@receiver([post_save, post_delete], sender=PYQ)
def clear_syllabus_cache(sender, **kwargs):
    cache.clear()

