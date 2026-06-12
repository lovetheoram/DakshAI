from django.db import models
from syllabus.models import Concept
from django.contrib.auth.models import User

class BaseQuestion(models.Model):
    question = models.TextField()
    option_a = models.TextField()
    option_b = models.TextField()
    option_c = models.TextField()
    option_d = models.TextField()
    correct_option = models.CharField(
        max_length=1,
        choices=[('A','A'), ('B','B'), ('C','C'), ('D','D')]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    def options_dict(self):
        return {
            "A": self.option_a,
            "B": self.option_b,
            "C": self.option_c,
            "D": self.option_d,
        }


class Question(BaseQuestion):
    qid = models.CharField(max_length=100, unique=True, primary_key=True)
    header = models.CharField(max_length=255)
    question_title = models.CharField(max_length=100)
    concept = models.ForeignKey(
        Concept,
        on_delete=models.CASCADE,
        related_name="questions"
    )
    explanation = models.TextField(blank=True)

    SOURCE_CHOICES = [('PYQS', 'Past Question'), ('NEW', 'AI Generated')]
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='PYQS')
    class Meta:
        indexes = [
            models.Index(fields=["concept", "source"]),
        ]

    def __str__(self):
        return f"{self.header}"


class SubQuestion(BaseQuestion):
    parent = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="sub_questions"
    )
    TYPE_CHOICES = [('comfort', 'Comfort'), ('grounding', 'Grounding'), ('precursor', 'Precursor')]
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    concept = models.ForeignKey(
        Concept,
        on_delete=models.CASCADE,
        related_name="sub_questions"
    )

    @property
    def sub_id(self):
        mapping = {'comfort': 'a', 'grounding': 'b', 'precursor': 'c'}
        return f"{self.parent.qid}-{mapping[self.type]}"

    def __str__(self):
        return f"{self.sub_id} ({self.type})"


class QuizSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    questions = models.ManyToManyField(Question, related_name="sessions")

    total_questions = models.IntegerField()
    score = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"QuizSession {self.id} - {self.user}"


class QuizAnswer(models.Model):
    session = models.ForeignKey(
        QuizSession,
        on_delete=models.CASCADE,
        related_name="answers"
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    sub_question = models.ForeignKey(
        SubQuestion,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    marked_option = models.CharField(
        max_length=1,
        choices=[('A','A'), ('B','B'), ('C','C'), ('D','D')]
    )
    is_correct = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "question", "sub_question"],
                name="unique_answer_per_item"
            )
        ]

