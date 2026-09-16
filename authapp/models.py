from django.db import models
from django.contrib.auth.models import User
from syllabus.models import Exam

class UserProfile(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE,related_name="profile")
    selected_exam = models.ForeignKey(Exam,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    bio = models.TextField(blank=True)
    avatar = models.URLField(blank=True)
    pcs_section = models.CharField(max_length=50, default="BPSC", blank=True)

    def __str__(self):
        return self.user.username
