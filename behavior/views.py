from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import UserBehaviorEvent, UserMindProfile
from .serializers import UserBehaviorEventSerializer, UserMindProfileSerializer
from .services.event_processor import EventProcessor
from .services.catalyst_engine import CatalystEngine


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
