"""
EventProcessor — logs behavioral events and triggers MindEngine recompute.

Usage (anywhere in the backend):
    from behavior.services.event_processor import EventProcessor
    EventProcessor.log(user, "QUIZ_PASSED", {"concept_id": 42, "score": 85})
"""

from behavior.models import UserBehaviorEvent
from behavior.services.mind_engine import MindEngine


class EventProcessor:

    @staticmethod
    def log(user, event_type, metadata=None):
        """
        Persist a behavioral event and trigger a mind profile recompute.
        Always safe to call — catches and swallows all exceptions so it
        never breaks the calling view.
        """
        try:
            UserBehaviorEvent.objects.create(
                user=user,
                event_type=event_type,
                metadata=metadata or {}
            )
            # Synchronous recompute — fast for small datasets
            MindEngine.recompute(user)
        except Exception:
            pass  # Behavioral logging must never crash the app
