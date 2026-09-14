from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from syllabus.models import Exam, Concept, Subtopic


class ConceptProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="progress")

    # Single unified Concept Readiness metric (built by LLM & PYQ practice)
    readiness = models.FloatField(default=0.0)

    last_practiced = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "concept")

    def get_mastery(self, decay_rate=0.02):
        """
        Compute decayed concept mastery (0.0 to 1.0) based on time elapsed since last practice.
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
    
    # 50/50 Dual Criteria for Daily Completion
    study_checked_in = models.BooleanField(default=False)
    completed_correct_questions = models.IntegerField(default=0)
    target_correct_questions = models.IntegerField(default=20)
    
    target_growth = models.FloatField(default=100.0)  # Total 100%
    completed_growth = models.FloatField(default=0.0)  # In percentage (0..100)
    is_completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "date")

    @property
    def completion_percentage(self):
        checkin_score = 50.0 if self.study_checked_in else 0.0
        questions_score = min(50.0, (self.completed_correct_questions / self.target_correct_questions) * 50.0) if self.target_correct_questions > 0 else 50.0
        return round(checkin_score + questions_score, 1)

    def calculate_completion(self):
        pct = self.completion_percentage
        self.completed_growth = pct
        self.is_completed = (pct >= 100.0)
        return pct

    def __str__(self):
        return f"{self.user.username} - {self.date} - Progress: {self.completion_percentage}%"



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
