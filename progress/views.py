from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import ConceptProgress, ProgressRecord, SubtopicProgress
from .serializers import ConceptProgressSerializer, ProgressRecordSerializer, SubtopicProgressSerializer
from .services import ProgressService
from syllabus.models import Concept, Subtopic


class ConceptProgressAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, concept_id):
        concept = Concept.objects.get(id=concept_id)
        cp = ProgressService.get_or_create_concept_progress(request.user, concept)
        return Response(ConceptProgressSerializer(cp).data)




class ConceptHistoryAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, concept_id):
        user = request.user
        records = ProgressRecord.objects.filter(user=user, concept_id=concept_id).order_by("created_at")
        record_list = ProgressRecordSerializer(records, many=True).data

        if records.exists():
            exam_scores = [r["main_correct"] / r["main_total"] if r["main_total"] else 0 for r in record_list]
            chapter_scores = [r["sub_correct"] / r["sub_total"] if r["sub_total"] else 0 for r in record_list]
            summary = {
                "total_attempts": len(records),
                "best_exam_score": max(exam_scores) if exam_scores else 0,
                "best_chapter_score": max(chapter_scores) if chapter_scores else 0,
                "average_exam_score": sum(exam_scores)/len(exam_scores) if exam_scores else 0,
                "average_chapter_score": sum(chapter_scores)/len(chapter_scores) if chapter_scores else 0,
            }
        else:
            summary = {
                "total_attempts": 0,
                "best_exam_score": 0,
                "best_chapter_score": 0,
                "average_exam_score": 0,
                "average_chapter_score": 0,
            }

        return Response({
            "concept_id": concept_id,
            "summary": summary,
            "records": record_list
        })


class SubtopicProgressAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, subtopic_id):
        subtopic = Subtopic.objects.get(id=subtopic_id)
        sp, _ = SubtopicProgress.objects.get_or_create(user=request.user, subtopic=subtopic)
        return Response(SubtopicProgressSerializer(sp).data)
