
from threading import Thread
from rest_framework.views import APIView
from rest_framework.response import Response
from syllabus.models import Concept
from .tasks import generate_meta_task


class GenerateConceptMeta(APIView):

    def post(self, request):

        concept_id = request.data.get("concept_id")
        chapter = request.data.get("chapter")

        # Start background thread
        Thread(
            target=generate_meta_task,
            args=(concept_id, chapter),
            daemon=True
        ).start()

        return Response({
            "message": "Meta generation started"
        })
    

from threading import Thread
from rest_framework.views import APIView
from rest_framework.response import Response
from .tasks import generate_questions_task


class GenerateConceptQuestions(APIView):

    def post(self, request):

        concept_id = request.data.get("concept_id")

        Thread(
            target=generate_questions_task,
            args=(concept_id,),
            daemon=True
        ).start()

        return Response({
            "message": "Question generation started"
        })