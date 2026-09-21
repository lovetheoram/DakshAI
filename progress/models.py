from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from syllabus.models import Exam, Concept, Subtopic


class ConceptProgress(models.Model):
    """
    Single authoritative readiness metric per concept per user.
    Readiness is 0.0–1.0, updated ONLY by ProgressService.update_progress_with_session
    via EMA smoothing (α=0.35).
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="progress")

    # Single unified Concept Readiness metric (built by quiz practice)
    readiness = models.FloatField(default=0.0)

    last_practiced = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "concept"], name="unique_user_concept_progress")
        ]

    def get_mastery(self, decay_rate=0.02):
        """
        Compute decayed concept mastery (0.0 to 1.0) based on time elapsed since last practice.
        Models memory decay: mastery = readiness × (1 - decay_rate)^days
        """
        if self.last_practiced is None:
            return self.readiness

        days = (timezone.now() - self.last_practiced).days
        if days <= 0:
            return self.readiness

        mastery = self.readiness * ((1 - decay_rate) ** days)
        return round(mastery, 4)


class SubtopicProgress(models.Model):
    """
    Tracks overall efficiency for a subtopic based on all its concepts.
    efficiency = simple average of concept readiness values (no secondary smoothing).
    Persisted for Galaxy page performance.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subtopic = models.ForeignKey(Subtopic, on_delete=models.CASCADE, related_name="progress")

    efficiency = models.FloatField(default=0.0)  # 0..1, direct average of concept readiness
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "subtopic"], name="unique_user_subtopic_progress")
        ]


class ProgressRecord(models.Model):
    """
    A history record for each quiz session — real evidence of learning.
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
    correct_count = models.PositiveIntegerField(default=0)
    wrong_count = models.PositiveIntegerField(default=0)

    main_correct = models.PositiveIntegerField(default=0)
    main_total = models.PositiveIntegerField(default=0)
    sub_correct = models.PositiveIntegerField(default=0)
    sub_total = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "concept", "quiz_session"],
                name="unique_user_concept_session_record"
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.concept} - score={self.score}"


class UserGoal(models.Model):
    """
    Defines the learner's exam target — the destination.
    One active goal per user per exam.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    goal_name = models.CharField(max_length=255)
    target_date = models.DateField()
    available_hours_per_day = models.FloatField(default=2.0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "exam"], name="unique_user_exam_goal")
        ]

    def __str__(self):
        return f"{self.user.username} - {self.goal_name}"


class DailyTarget(models.Model):
    """
    What must happen today, given the learner's exam target and current position.

    required_readiness_per_day = remaining_readiness / remaining_days
    Units: readiness percentage-points / calendar day

    This is NOT a reward system, NOT a checklist, NOT proof of study.
    It connects current readiness → required daily progress → today's target.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.localdate)
    required_readiness_per_day = models.FloatField(default=0.0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "date"], name="unique_daily_target")
        ]

    def __str__(self):
        return f"{self.user.username} - {self.date} - required: {self.required_readiness_per_day}%pts/day"


class DailyDiaryEntry(models.Model):
    """
    Aggregated daily evidence of what the learner actually did.

    opened_at: When the learner first opened DakshAI today (presence).
    Remaining fields: real quiz/practice evidence accumulated through the day.

    readiness_delta: SIGNED net change in exam readiness percentage points today.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.localdate)
    opened_at = models.DateTimeField(null=True, blank=True)

    # Real evidence from quiz/practice sessions
    concepts_attempted = models.JSONField(default=list, blank=True)
    concepts_completed = models.JSONField(default=list, blank=True)
    questions_solved = models.PositiveIntegerField(default=0)
    questions_correct = models.PositiveIntegerField(default=0)
    time_spent_seconds = models.PositiveIntegerField(default=0)

    # Signed net readiness change: exam readiness percentage points gained/lost today
    readiness_delta = models.FloatField(default=0.0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "date"], name="unique_daily_diary")
        ]

    def __str__(self):
        present = "present" if self.opened_at else "absent"
        return f"{self.user.username} - {self.date} - {present} - Δ{self.readiness_delta:+.4f}%pts"


# Cache invalidation signal — clear Daksh score cache when ConceptProgress changes
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache


@receiver([post_save, post_delete], sender=ConceptProgress)
def clear_daksh_score_cache(sender, instance, **kwargs):
    try:
        exam_id = instance.concept.subtopic.topic.subject.exam_id
        cache_key = f"user_{instance.user_id}_exam_{exam_id}_daksh_score"
        cache.delete(cache_key)
    except Exception:
        pass
