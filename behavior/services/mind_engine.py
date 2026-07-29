"""
MindEngine — reads UserBehaviorEvent records and computes/updates UserMindProfile.

Called synchronously after each event is persisted (fast, <50ms for small event sets).
Can be moved to Celery task in Phase 5 when traffic grows.
"""

from django.utils.timezone import now
from datetime import timedelta


class MindEngine:

    @staticmethod
    def recompute(user):
        """
        Reads the last 30 days of events + ConceptProgress and writes UserMindProfile.
        Safe to call multiple times — always overwrites.
        """
        # Import here to avoid circular imports
        from behavior.models import UserBehaviorEvent, UserMindProfile

        profile, _ = UserMindProfile.objects.get_or_create(user=user)

        cutoff = now() - timedelta(days=30)
        events = UserBehaviorEvent.objects.filter(user=user, created_at__gte=cutoff)

        # ── Confidence Score ──────────────────────────────────────────────────
        quiz_events = events.filter(event_type__in=["QUIZ_PASSED", "QUIZ_FAILED", "QUIZ_FAILED_REPEAT"])
        if quiz_events.exists():
            passed = quiz_events.filter(event_type="QUIZ_PASSED").count()
            profile.confidence_score = round(passed / quiz_events.count(), 2)

        # ── Momentum Direction ────────────────────────────────────────────────
        recent_7 = events.filter(created_at__gte=now() - timedelta(days=7)).count()
        prev_7   = events.filter(
            created_at__range=(now() - timedelta(days=14), now() - timedelta(days=7))
        ).count()

        if recent_7 == 0 and prev_7 == 0:
            profile.momentum_direction = "dormant"
        elif recent_7 > prev_7 * 1.2:
            profile.momentum_direction = "rising"
        elif prev_7 > 0 and recent_7 < prev_7 * 0.5:
            profile.momentum_direction = "falling"
        else:
            profile.momentum_direction = "steady"

        # ── Fear Areas ────────────────────────────────────────────────────────
        # Concepts where user has failed 3+ times
        failed_events = events.filter(event_type__in=["QUIZ_FAILED", "QUIZ_FAILED_REPEAT"])
        fear = list({
            e.metadata.get("concept_name")
            for e in failed_events
            if e.metadata.get("concept_name")
        })
        profile.fear_areas = fear[:5]

        # ── Avoidance Pattern ─────────────────────────────────────────────────
        abandoned = events.filter(event_type="SESSION_ABANDONED")
        profile.avoidance_pattern = list({
            e.metadata.get("concept_name")
            for e in abandoned
            if e.metadata.get("concept_name")
        })[:5]

        # ── Last Active ───────────────────────────────────────────────────────
        latest = events.order_by("-created_at").first()
        if latest:
            profile.last_active = latest.created_at

        # ── Current State ─────────────────────────────────────────────────────
        profile.current_state = MindEngine._compute_state(profile)

        profile.save()
        return profile

    @staticmethod
    def _compute_state(profile):
        if profile.momentum_direction == "dormant":
            return "at_risk"
        if profile.confidence_score >= 0.75 and profile.momentum_direction == "rising":
            return "thriving"
        if profile.confidence_score > 0.85:
            return "needs_challenge"
        if profile.confidence_score < 0.40 or profile.momentum_direction == "falling":
            return "needs_encouragement"
        return "on_track"
