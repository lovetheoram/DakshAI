from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Exam
from .serializers import ExamSerializer

class SyllabusTreeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        exams = Exam.objects.prefetch_related("subjects__topics__subtopics__concepts").all()
        data = ExamSerializer(exams, many=True, context={"user": request.user}).data
        return Response({"exams": data})

from .models import Concept
from .serializers import ConceptMiniSerializer

class ConceptListAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Concept.objects.select_related(
            "subtopic__topic__subject__exam"
        )
        data = ConceptMiniSerializer(qs, many=True).data
        return Response(data)