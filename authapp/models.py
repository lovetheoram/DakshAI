from django.db import models
from django.contrib.auth.models import User
from syllabus.models import Exam

class UserProfile(models.Model):
    EDUCATION_STAGES = (
        ("below_6", "Below Class 6"),
        ("class_6_10", "Classes 6 - 10"),
        ("class_11_12", "Classes 11 - 12"),
        ("jee", "JEE Preparation"),
        ("neet", "NEET Preparation"),
        ("college", "College / University"),
        ("placement", "Placements & Career Skills"),
        ("pcs", "State PCS & Civil Services"),
        ("other", "General / Lifelong Learning"),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=150, blank=True, default="")
    selected_exam = models.ForeignKey(
        Exam,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    bio = models.TextField(blank=True, default="")
    avatar = models.URLField(blank=True, default="")
    pcs_section = models.CharField(max_length=50, default="BPSC", blank=True)

    # Student Lifecycle & Education Context
    education_stage = models.CharField(
        max_length=30,
        choices=EDUCATION_STAGES,
        default="class_11_12",
        db_index=True
    )
    institution_name = models.CharField(max_length=200, blank=True, default="")
    grade_or_year = models.CharField(max_length=50, blank=True, default="")
    location_city = models.CharField(max_length=100, blank=True, default="")

    # Interests, Skills & Portfolio
    interests = models.JSONField(default=list, blank=True)
    skills = models.JSONField(default=list, blank=True)

    # Safety & Age-Aware Privacy
    is_minor = models.BooleanField(default=False, db_index=True)
    privacy_settings = models.JSONField(
        default=dict,
        blank=True,
        help_text="Dict with keys: profile_visibility ('public'|'connections'|'private'), show_learning_progress (bool), allow_messages_from ('everyone'|'followers'|'none')"
    )

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return self.user.username

    def get_privacy(self):
        defaults = {
            "profile_visibility": "public" if not self.is_minor else "connections",
            "show_learning_progress": False,  # Never expose private marks/readiness by default!
            "allow_messages_from": "everyone" if not self.is_minor else "followers",
            "show_institution": True,
        }
        if isinstance(self.privacy_settings, dict):
            defaults.update(self.privacy_settings)
        return defaults

