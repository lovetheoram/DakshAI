from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from syllabus.models import Concept, Subtopic


class ConceptProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="progress")

    # separate metrics
    exam_readiness = models.FloatField(default=0.0)         # main questions
    chapter_understanding = models.FloatField(default=0.0) # sub-questions

    last_practiced = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "concept")

    def get_mastery(self, decay_rate=0.02):
        """
        Compute decayed mastery for both exam readiness and chapter understanding.
        Returns tuple (exam, understanding)
        """
        if self.last_practiced is None:
            return self.exam_readiness, self.chapter_understanding

        days = (timezone.now() - self.last_practiced).days
        if days <= 0:
            return self.exam_readiness, self.chapter_understanding

        exam = self.exam_readiness * ((1 - decay_rate) ** days)
        chapter = self.chapter_understanding * ((1 - decay_rate) ** days)
        return round(exam, 4), round(chapter, 4)


class SubtopicProgress(models.Model):
    """
    Tracks overall efficiency for a subtopic based on all its concepts.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subtopic = models.ForeignKey(Subtopic, on_delete=models.CASCADE, related_name="progress")

    efficiency = models.FloatField(default=0.0)  # 0..1
    raw_efficiency=models.FloatField(default=0.0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "subtopic")


class ProgressRecord(models.Model):
    """
    A history record for each quiz session (linked)
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE)
    quiz_session = models.ForeignKey(
        "quiz.QuizSession",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="progress_records"
    )
    score = models.FloatField()  # total session score (0..1)
    correct_count = models.IntegerField(default=0)
    wrong_count = models.IntegerField(default=0)

    main_correct = models.IntegerField(default=0)
    main_total = models.IntegerField(default=0)
    sub_correct = models.IntegerField(default=0)
    sub_total = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ("user", "concept", "quiz_session")

    def __str__(self):
        return f"{self.user} - {self.concept} - score={self.score}"
