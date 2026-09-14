from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.http import StreamingHttpResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken

from syllabus.models import Concept
from .serializers import QuestionSerializer, QuizAnswerReviewSerializer
from .services import QuizService

User = get_user_model()


def get_user_from_token(token):
    access = AccessToken(token)
    user_id = access["user_id"]
    return User.objects.get(id=user_id)


class StartQuizView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        concept_id = request.data.get("concept_id")
        num = int(request.data.get("num_questions", 10))
        quiz_type = request.data.get("quiz_type", "PYQS").upper()  # PYQS, FULL_EXAM, or LLM

        try:
            concept = Concept.objects.get(id=concept_id)
        except Concept.DoesNotExist:
            return Response({"detail": "Concept not found"}, status=404)

        if quiz_type == "PYQS":
            session, questions = QuizService.start_pyqs_quiz(
                user=request.user,
                concept=concept,
                num=num
            )
            return Response({
                "mode": "PYQS",
                "session_id": session.id,
                "total_questions": session.total_questions,
                "questions": QuestionSerializer(questions, many=True).data
            })

        if quiz_type == "FULL_EXAM":
            session, questions = QuizService.start_full_exam_quiz(
                user=request.user,
                concept=concept,
                num=num
            )
            return Response({
                "mode": "FULL_EXAM",
                "session_id": session.id,
                "total_questions": session.total_questions,
                "questions": QuestionSerializer(questions, many=True).data
            })

        # LLM Generated Stream
        return StreamingHttpResponse(
            QuizService.start_ai_quiz_stream(
                user=request.user,
                concept=concept,
                num=num
            ),
            content_type="text/event-stream"
        )


class StartQuizSSEView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        token = request.GET.get("token")
        if not token:
            return StreamingHttpResponse(status=401)

        try:
            user = get_user_from_token(token)
        except Exception:
            return StreamingHttpResponse(status=401)

        concept_id = request.GET.get("concept_id")
        num = int(request.GET.get("num_questions", 1))

        try:
            concept = Concept.objects.get(id=concept_id)
        except Concept.DoesNotExist:
            return StreamingHttpResponse(status=404)

        response = StreamingHttpResponse(
            QuizService.start_ai_quiz_stream(
                user=user,
                concept=concept,
                num=num
            ),
            content_type="text/event-stream"
        )

        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"

        return response


class SubmitQuizView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        session = QuizService.submit_quiz(
            user=request.user,
            session_id=request.data["session_id"],
            answers_payload=request.data.get("answers", []),
            duration_seconds=request.data.get("duration_seconds")
        )

        answers = QuizAnswerReviewSerializer(
            session.answers.all(), many=True
        ).data

        return Response({
            "session_id": session.id,
            "mode": session.mode,
            "score": session.score,
            "completed_at": session.completed_at,
            "duration_seconds": session.duration_seconds,
            "answers": answers
        })
