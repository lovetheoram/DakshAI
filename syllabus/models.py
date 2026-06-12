

from django.db import models


class Exam(models.Model):
    EXAM_TYPE_CHOICES = [
        ("jee", "JEE Main"),
        ("neet", "NEET"),
        ("placement", "Placement Preparation"),
        
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
