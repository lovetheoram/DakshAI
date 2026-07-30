from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import UserBehaviorEvent, UserMindProfile, CatalystMessage
from .serializers import UserBehaviorEventSerializer, UserMindProfileSerializer
from .services.event_processor import EventProcessor
from .services.catalyst_engine import CatalystEngine

import random


class BehaviorEventAPI(APIView):
    """
    POST /api/behavior/event/
    Logs a single behavioral event from the frontend EventTracker.
    Fire-and-forget: always returns 200 even on internal error.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        event_type = request.data.get("event_type", "")
        metadata   = request.data.get("metadata", {})

        # Validate event_type is one we know about
        valid_types = [et[0] for et in UserBehaviorEvent.EVENT_TYPES]
        if event_type not in valid_types:
            return Response(
                {"detail": f"Unknown event_type: {event_type}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        EventProcessor.log(request.user, event_type, metadata)
        return Response({"status": "logged"}, status=status.HTTP_200_OK)


class CatalystAPI(APIView):
    """
    GET /api/behavior/catalyst/
    Returns the most relevant Catalyst (Daksh) message for this user right now.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = CatalystEngine.get_catalyst_for_user(request.user)
        return Response(data)


class InterventionAPI(APIView):
    """
    GET /api/behavior/catalyst/intervention/?trigger=CURIOSITY_PROMPT&tone=mentor

    Phase 5 endpoint: returns a tone-matched CatalystMessage for a given action trigger.
    Called by the frontend OIDPI loop after PriorityEngine selects a winner.

    Lookup priority:
      1. Exact trigger + tone match
      2. trigger + tone='any'
      3. trigger only (any tone)
      4. GENERIC_INSIGHT fallback
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        trigger = request.query_params.get("trigger", "")
        tone    = request.query_params.get("tone", "any")

        if not trigger:
            return Response({"detail": "trigger param required"}, status=400)

        # Priority 1: exact match
        msgs = list(CatalystMessage.objects.filter(trigger=trigger, tone=tone))

        # Priority 2: any-tone variant of the same trigger
        if not msgs:
            msgs = list(CatalystMessage.objects.filter(trigger=trigger, tone="any"))

        # Priority 3: any message for this trigger
        if not msgs:
            msgs = list(CatalystMessage.objects.filter(trigger=trigger))

        # Priority 4: generic fallback
        if not msgs:
            msgs = list(CatalystMessage.objects.filter(trigger="GENERIC_INSIGHT"))

        if not msgs:
            return Response({
                "trigger": trigger,
                "tone": tone,
                "title": "Observation.",
                "body": "Consistency beats intensity. One focused session builds more knowledge than five exhausting ones.",
                "cta_text": "Begin Session",
                "cta_action": "navigate:/learn",
            })

        # Weighted random selection
        weights = [m.weight for m in msgs]
        msg = random.choices(msgs, weights=weights, k=1)[0]

        return Response({
            "trigger": trigger,
            "tone": tone,
            "title": msg.title,
            "body": msg.body,
            "cta_text": msg.cta_text,
            "cta_action": msg.cta_action,
        })


class MindProfileAPI(APIView):
    """
    GET /api/behavior/mind/
    Returns the current UserMindProfile for this user (debug / admin use).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = UserMindProfile.objects.filter(user=request.user).first()
        if not profile:
            return Response({"detail": "No mind profile computed yet."}, status=404)
        return Response(UserMindProfileSerializer(profile).data)
