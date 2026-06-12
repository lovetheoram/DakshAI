# from rest_framework.views import APIView
# from rest_framework.permissions import IsAuthenticated
# from rest_framework.response import Response

# from syllabus.models import Concept
# from .services import QuizService
# from .serializers import (
#     QuestionSerializer,
#     QuizAnswerReviewSerializer
# )


# class StartQuizView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         concept_id = request.data.get("concept_id")
#         num = int(request.data.get("num_questions", 10))
#         quiz_type = request.data.get("quiz_type", "PYQS")

#         concept = Concept.objects.get(id=concept_id)

#         session, questions = QuizService.start_quiz(
#             user=request.user,
#             concept=concept,
#             num=num,
#             quiz_type=quiz_type
#         )

#         return Response({
#             "session_id": session.id,
#             "quiz_type": quiz_type,
#             "total_questions": session.total_questions,
#             "questions": QuestionSerializer(questions, many=True).data
#         })


# class SubmitQuizView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         session = QuizService.submit_quiz(
#             user=request.user,
#             session_id=request.data["session_id"],
#             answers_payload=request.data.get("answers", []),
#             duration_seconds=request.data.get("duration_seconds")
#         )

#         answers = QuizAnswerReviewSerializer(
#             session.answers.all(),
#             many=True
#         ).data

#         return Response({
#             "session_id": session.id,
#             "score": session.score,
#             "completed_at": session.completed_at,
#             "duration_seconds": session.duration_seconds,
#             "answers": answers
#         })




from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import StreamingHttpResponse

from syllabus.models import Concept
# from .services import QuizService
from .serializers import QuestionSerializer, QuizAnswerReviewSerializer
from .services import QuizService

class StartQuizView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        concept_id = request.data.get("concept_id")
        num = int(request.data.get("num_questions", 10))
        quiz_type = request.data.get("quiz_type", "PYQS").upper()

        concept = Concept.objects.get(id=concept_id)

        # PYQS → normal response
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

        # AI → STREAM
        return StreamingHttpResponse(
            QuizService.start_ai_quiz_stream(
                user=request.user,
                concept=concept,
                num=num
            ),
            content_type="text/event-stream"
        )

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
            "score": session.score,
            "completed_at": session.completed_at,
            "duration_seconds": session.duration_seconds,
            "answers": answers
        })



from django.http import StreamingHttpResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model

User = get_user_model()

def get_user_from_token(token):
    access = AccessToken(token)      # validates + decodes
    user_id = access["user_id"]      # comes from SimpleJWT
    return User.objects.get(id=user_id)
class StartQuizSSEView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        token = request.GET.get("token")
        if not token:
            return StreamingHttpResponse(status=401)

        try:
            access = AccessToken(token)
            user_id = access["user_id"]
            user = User.objects.get(id=user_id)
        except Exception as e:
            return StreamingHttpResponse(status=401)

        concept_id = request.GET.get("concept_id")
        num = int(request.GET.get("num_questions", 1))

        concept = Concept.objects.get(id=concept_id)

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
