from django.db import models
from django.contrib.auth.models import User


# =============================================================
# 1. Universal Behavioral Event Log
# =============================================================
class UserBehaviorEvent(models.Model):
    EVENT_TYPES = [
        # Learning
        ("CONCEPT_STARTED",       "Concept Started"),
        ("CONCEPT_COMPLETED",     "Concept Completed"),
        ("SESSION_ABANDONED",     "Session Abandoned"),
        # Quiz
        ("QUIZ_STARTED",          "Quiz Started"),
        ("QUIZ_PASSED",           "Quiz Passed"),
        ("QUIZ_FAILED",           "Quiz Failed"),
        ("QUIZ_FAILED_REPEAT",    "Quiz Failed Repeat"),
        # Behavioral
        ("RETURN_AFTER_BREAK",    "Return After Break"),
        ("GOAL_SET",              "Goal Set"),
        ("ENERGY_REPORTED",       "Energy Reported"),
        # Milestone
        ("STREAK_MILESTONE",      "Streak Milestone"),
        ("CONCEPT_MASTERED",      "Concept Mastered"),
        ("IDENTITY_UNLOCKED",     "Identity Unlocked"),
        # Onboarding
        ("ONBOARDING_COMPLETED",  "Onboarding Completed"),
    ]

    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name="behavior_events")
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, db_index=True)
    metadata   = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "event_type", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user.username} → {self.event_type} @ {self.created_at:%Y-%m-%d %H:%M}"


# =============================================================
# 2. Living User Mind Profile
# =============================================================
class UserMindProfile(models.Model):
    MOMENTUM_CHOICES = [
        ("rising",  "Rising"),
        ("steady",  "Steady"),
        ("falling", "Falling"),
        ("dormant", "Dormant"),
    ]
    STATE_CHOICES = [
        ("thriving",            "Thriving"),
        ("on_track",            "On Track"),
        ("needs_encouragement", "Needs Encouragement"),
        ("needs_challenge",     "Needs Challenge"),
        ("at_risk",             "At Risk"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="mind_profile")

    # Computed scores (0.0 – 1.0)
    confidence_score   = models.FloatField(default=0.5)
    momentum_score     = models.FloatField(default=0.5)

    # Qualitative states
    momentum_direction = models.CharField(max_length=10, choices=MOMENTUM_CHOICES, default="steady")
    current_state      = models.CharField(max_length=25, choices=STATE_CHOICES, default="on_track")

    # Pattern arrays — JSON lists of concept / subject names
    fear_areas         = models.JSONField(default=list, blank=True)   # repeated failures
    strength_areas     = models.JSONField(default=list, blank=True)   # high mastery
    avoidance_pattern  = models.JSONField(default=list, blank=True)   # abandoned concepts

    # Timing intelligence
    best_study_hour    = models.IntegerField(null=True, blank=True)   # 0–23 UTC
    avg_session_length = models.IntegerField(default=0)               # in minutes

    # Meta
    last_active        = models.DateTimeField(null=True, blank=True)
    last_computed      = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} — {self.current_state} / {self.momentum_direction}"


# =============================================================
# 3. Pre-authored Catalyst (Daksh) Messages
# =============================================================
class CatalystMessage(models.Model):
    TRIGGER_CHOICES = [
        # ── Phase 4 — state-based triggers (unchanged) ──────────────────────
        ("FIRST_LOGIN",          "First Login"),
        ("RETURN_AFTER_BREAK",   "Return After Break"),
        ("GOAL_SET",             "Goal Just Set"),
        ("QUIZ_FAILED_REPEAT",   "Repeated Quiz Failure"),
        ("QUIZ_PERFECT",         "Perfect Quiz Score"),
        ("CONCEPT_MASTERED",     "Concept Mastered"),
        ("STREAK_MILESTONE",     "Streak Milestone"),
        ("IDENTITY_UNLOCKED",    "Identity Title Unlocked"),
        ("LOW_ENERGY",           "Low Energy Reported"),
        ("MOMENTUM_FALLING",     "Momentum Falling"),
        ("DAILY_TARGET_HIT",     "Daily Target Hit"),
        ("THRIVING",             "User Thriving"),
        ("AT_RISK",              "User At Risk"),
        ("GENERIC_INSIGHT",      "Generic Insight"),
        # ── Phase 5 — OIDPI action-type triggers (new) ───────────────────────
        ("CURIOSITY_PROMPT",     "Curiosity — Ask before Notes"),
        ("DIRECT_CHALLENGE",     "Challenge — Skip to Test"),
        ("ENCOURAGEMENT",        "Encourage — Fear Area Support"),
        ("CELEBRATION",          "Celebrate — Milestone"),
        ("FOCUSED_EXPLAIN",      "Explain — Repeated Failure"),
        ("REFLECTION_PROMPT",    "Reflect — Long Session / Drift"),
        ("PREDICTION_NARRATIVE", "Predict — Growth Story"),
        ("IDENTITY_ARRIVAL",     "Identity — Mood Arrival Ritual"),
    ]

    # Tone maps to InterventionEngine's adaptive tone selector
    TONE_CHOICES = [
        ("mentor",     "Mentor — warm, patient, no pressure"),
        ("challenger", "Challenger — direct, sharp, playful"),
        ("companion",  "Companion — curious, gentle, exploratory"),
        ("any",        "Any — tone-agnostic, works for all"),
    ]

    trigger     = models.CharField(max_length=30, choices=TRIGGER_CHOICES, db_index=True)
    tone        = models.CharField(max_length=12, choices=TONE_CHOICES, default="any", db_index=True)
    title       = models.CharField(max_length=120)   # short headline, e.g. "Signal received."
    body        = models.TextField()                  # Daksh message — may contain {placeholders}
    cta_text    = models.CharField(max_length=60, blank=True)   # e.g. "Begin Mission"
    cta_action  = models.CharField(max_length=100, blank=True)  # e.g. "navigate:/learn"
    weight      = models.IntegerField(default=1)      # higher = shown more often

    class Meta:
        ordering = ["-weight"]
        indexes = [
            models.Index(fields=["trigger", "tone"]),
        ]

    def __str__(self):
        return f"[{self.trigger}][{self.tone}] {self.title}"


# =============================================================
# 4. Periodic Mind Snapshots (for trend analysis)
# =============================================================
class UserStateSnapshot(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name="state_snapshots")
    snapshot   = models.JSONField()            # full mind profile captured at this moment
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} snapshot @ {self.created_at:%Y-%m-%d}"
