"""
CatalystEngine — selects the most relevant CatalystMessage for a user
based on their current UserMindProfile and recent event history.

Priority order:
  1. Recent high-signal event (break return, repeated failure, mastery)
  2. Current mind state
  3. Fallback to GENERIC_INSIGHT
"""

from django.utils.timezone import now
from datetime import timedelta


class CatalystEngine:

    @staticmethod
    def get_catalyst_for_user(user):
        """
        Returns a dict describing the current Catalyst message for this user.
        Never raises — always returns a safe fallback.
        """
        from behavior.models import UserMindProfile, UserBehaviorEvent, CatalystMessage

        try:
            profile = UserMindProfile.objects.filter(user=user).first()

            if not profile:
                return CatalystEngine._build_response(
                    CatalystEngine._pick("FIRST_LOGIN"),
                    "FIRST_LOGIN",
                    {}
                )

            # Determine trigger + context
            trigger, context = CatalystEngine._resolve_trigger(profile, user)
            msg = CatalystEngine._pick(trigger)

            if not msg:
                msg = CatalystEngine._pick("GENERIC_INSIGHT")

            return CatalystEngine._build_response(msg, trigger, context, profile)

        except Exception:
            return {
                "trigger": "GENERIC_INSIGHT",
                "title": "Observation.",
                "body": "Consistency beats intensity. One focused session every day builds more knowledge than five exhausting ones per week.",
                "cta_text": "Begin Session",
                "cta_action": "navigate:/learn",
                "mind_state": "on_track",
                "momentum": "steady",
                "fear_areas": [],
                "context": {},
            }

    @staticmethod
    def _resolve_trigger(profile, user):
        """Returns (trigger_string, context_dict) based on highest-priority signal."""
        from behavior.models import UserBehaviorEvent

        context = {}

        # ── 1. Return after break ──────────────────────────────────────────
        if profile.last_active:
            days_away = (now() - profile.last_active).days
            if days_away >= 3:
                context["days_away"] = days_away
                return "RETURN_AFTER_BREAK", context

        # ── 2. Recent repeated failure ─────────────────────────────────────
        repeat_fail = UserBehaviorEvent.objects.filter(
            user=user,
            event_type="QUIZ_FAILED_REPEAT",
            created_at__gte=now() - timedelta(days=3)
        ).order_by("-created_at").first()
        if repeat_fail:
            context["concept_name"] = repeat_fail.metadata.get("concept_name", "")
            context["concept_id"]   = repeat_fail.metadata.get("concept_id", "")
            return "QUIZ_FAILED_REPEAT", context

        # ── 3. Recent concept mastery ──────────────────────────────────────
        mastery_event = UserBehaviorEvent.objects.filter(
            user=user,
            event_type="CONCEPT_MASTERED",
            created_at__gte=now() - timedelta(days=1)
        ).order_by("-created_at").first()
        if mastery_event:
            context["concept_name"] = mastery_event.metadata.get("concept_name", "")
            context["subject"]      = mastery_event.metadata.get("subject_name", "")
            return "CONCEPT_MASTERED", context

        # ── 4. Low energy reported today ───────────────────────────────────
        low_energy = UserBehaviorEvent.objects.filter(
            user=user,
            event_type="ENERGY_REPORTED",
            created_at__gte=now() - timedelta(hours=24)
        ).order_by("-created_at").first()
        if low_energy and low_energy.metadata.get("energy", 100) < 35:
            return "LOW_ENERGY", context

        # ── 5. Mind state fallback ─────────────────────────────────────────
        state_trigger_map = {
            "at_risk":             "AT_RISK",
            "thriving":            "THRIVING",
            "needs_encouragement": "MOMENTUM_FALLING",
            "needs_challenge":     "THRIVING",
            "on_track":            "GENERIC_INSIGHT",
        }
        return state_trigger_map.get(profile.current_state, "GENERIC_INSIGHT"), context

    @staticmethod
    def _pick(trigger):
        """Pick a CatalystMessage for the given trigger, weighted random."""
        from behavior.models import CatalystMessage
        import random
        msgs = list(CatalystMessage.objects.filter(trigger=trigger))
        if not msgs:
            return None
        # Weighted random selection
        weights = [m.weight for m in msgs]
        return random.choices(msgs, weights=weights, k=1)[0]

    @staticmethod
    def _build_response(msg, trigger, context, profile=None):
        if not msg:
            return {
                "trigger": trigger,
                "title": "Observation.",
                "body": "Consistency beats intensity. One focused session every day builds more knowledge than five exhausting ones per week.",
                "cta_text": "Begin Session",
                "cta_action": "navigate:/learn",
                "mind_state": "on_track",
                "momentum": "steady",
                "fear_areas": [],
                "context": context,
            }
        return {
            "trigger": trigger,
            "title": msg.title,
            "body": msg.body,
            "cta_text": msg.cta_text,
            "cta_action": msg.cta_action,
            "mind_state": profile.current_state if profile else "on_track",
            "momentum": profile.momentum_direction if profile else "steady",
            "fear_areas": profile.fear_areas if profile else [],
            "context": context,
        }
