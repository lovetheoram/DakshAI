from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from syllabus.models import Exam, Concept, Subtopic


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


class UserGoal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    goal_name = models.CharField(max_length=255)
    target_date = models.DateField()
    available_hours_per_day = models.FloatField(default=2.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "exam")

    def __str__(self):
        return f"{self.user.username} - {self.goal_name}"


class DailyTarget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    target_growth = models.FloatField(default=0.83)  # in percentage, e.g. 0.83 for 0.83%
    completed_growth = models.FloatField(default=0.0)  # in percentage, e.g. 0.35 for 0.35%
    is_completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "date")

    def __str__(self):
        return f"{self.user.username} - {self.date} - Growth: {self.completed_growth}/{self.target_growth}%"


class DailyDiaryEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    concepts_attempted = models.JSONField(default=list, blank=True)
    concepts_completed = models.JSONField(default=list, blank=True)
    questions_solved = models.IntegerField(default=0)
    questions_correct = models.IntegerField(default=0)
    time_spent_seconds = models.IntegerField(default=0)
    revision_count = models.IntegerField(default=0)
    energy_score = models.IntegerField(default=50)  # scale 1-100
    focus_score = models.IntegerField(default=50)  # scale 1-100
    mood = models.CharField(max_length=50, default="neutral")
    knowledge_gain = models.JSONField(default=dict, blank=True)
    accuracy = models.FloatField(default=0.0)
    daily_growth_percentage = models.FloatField(default=0.0)

    class Meta:
        unique_together = ("user", "date")

    def __str__(self):
        return f"{self.user.username} - {self.date} - Energy: {self.energy_score}"
