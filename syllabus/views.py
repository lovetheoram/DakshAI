from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from .models import Exam, Subtopic, Concept
from .serializers import ExamSerializer, ConceptSerializer, ConceptListSerializer
from progress.models import ConceptProgress

class SyllabusTreeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        is_anonymous = not hasattr(request, "user") or request.user is None or getattr(request.user, "is_anonymous", True)
        params = getattr(request, "query_params", getattr(request, "GET", {}))
        exam_id = params.get("exam_id")
        pcs_section = params.get("pcs_section")
        
        # Resolve which exam_id is being fetched.
        resolved_exam_id = exam_id
        if not resolved_exam_id and not is_anonymous:
            profile = getattr(request.user, "profile", None)
            if profile:
                if profile.selected_exam:
                    resolved_exam_id = str(profile.selected_exam.id)
                if not pcs_section and profile.pcs_section:
                    pcs_section = profile.pcs_section

        cache_key = f"syllabus_tree_exam_{resolved_exam_id or 'all'}_pcs_{pcs_section or 'default'}"
        static_data = cache.get(cache_key)

        if static_data is None:
            from .serializers import SubjectSerializer
            if resolved_exam_id:
                try:
                    target_exam = Exam.objects.prefetch_related("branches").get(id=resolved_exam_id)
                except Exam.DoesNotExist:
                    return Response({"exams": []})

                if target_exam.parent_exam:
                    parent_exam = target_exam.parent_exam
                    parent_subjects = list(parent_exam.subjects.prefetch_related("topics__subtopics").all())
                    child_subjects = list(target_exam.subjects.prefetch_related("topics__subtopics").all())
                    all_subjects = parent_subjects + child_subjects

                    exam_data = ExamSerializer(target_exam).data
                    exam_data["subjects"] = SubjectSerializer(all_subjects, many=True).data
                    static_data = [exam_data]
                else:
                    all_subjects = list(target_exam.subjects.prefetch_related("topics__subtopics").all())
                    if pcs_section:
                        branch_exam = target_exam.branches.filter(code__iexact=pcs_section).first()
                        if branch_exam:
                            all_subjects += list(branch_exam.subjects.prefetch_related("topics__subtopics").all())
                    
                    exam_data = ExamSerializer(target_exam).data
                    exam_data["subjects"] = SubjectSerializer(all_subjects, many=True).data
                    static_data = [exam_data]
            else:
                exams = Exam.objects.filter(parent_exam__isnull=True).prefetch_related("branches", "subjects__topics__subtopics")
                static_data = ExamSerializer(exams, many=True).data

            cache.set(cache_key, static_data, timeout=86400)

        return Response({"exams": static_data})


class SubtopicConceptsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, subtopic_id):
        try:
            subtopic = Subtopic.objects.get(id=subtopic_id)
        except Subtopic.DoesNotExist:
            return Response({"detail": "Subtopic not found"}, status=404)

        concepts = subtopic.concepts.prefetch_related("pyqs", "questions").all()

        # Build progress dict for the current user if logged in
        progress_dict = {}
        if request.user and not request.user.is_anonymous:
            progress_records = ConceptProgress.objects.filter(user=request.user, concept__in=concepts)
            progress_dict = {cp.concept_id: cp for cp in progress_records}

        serializer = ConceptListSerializer(
            concepts,
            many=True,
            context={"user": request.user, "progress_dict": progress_dict}
        )
        return Response(serializer.data)

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


class ConceptDetailAPI(APIView):
    permission_classes = [AllowAny]

    def get(self, request, concept_id):
        try:
            concept = Concept.objects.select_related(
                "subtopic__topic__subject"
            ).prefetch_related("pyqs", "questions").get(id=concept_id)
        except Concept.DoesNotExist:
            return Response({"detail": "Concept not found"}, status=404)

        progress_record = None
        if request.user and not request.user.is_anonymous:
            progress_record = ConceptProgress.objects.filter(
                user=request.user, concept=concept
            ).first()

        serializer = ConceptSerializer(
            concept,
            context={
                "user": request.user,
                "progress_dict": {concept.id: progress_record} if progress_record else {},
            },
        )
        data = serializer.data
        data["subtopic_id"] = concept.subtopic.id
        data["subtopic_name"] = concept.subtopic.name
        data["topic_name"] = concept.subtopic.topic.name
        data["subject_name"] = concept.subtopic.topic.subject.name
        return Response(data)


class ConceptPYQListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, concept_id):
        try:
            concept = Concept.objects.prefetch_related("pyqs").get(id=concept_id)
        except Concept.DoesNotExist:
            return Response({"detail": "Concept not found"}, status=404)

        from .serializers import PYQSerializer
        pyqs_data = PYQSerializer(concept.pyqs.all(), many=True).data

        return Response({
            "concept_id": concept.id,
            "concept_name": concept.name,
            "description": concept.description,
            "ai_meta": concept.ai_meta,
            "pyqs_count": len(pyqs_data),
            "pyqs": pyqs_data
        })


import os
import json
from .story_cheatsheet_engine import generate_vocal_learning_content

class VocalLearningScenesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        subject = request.query_params.get("subject", "AI Engineering")
        saved_file = os.path.join(os.path.dirname(__file__), "syllabus_list", "ai_engineering_vocal_scenes.json")
        if os.path.exists(saved_file):
            with open(saved_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return Response(data)
        
        pdf_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "docs", "AI_Engineering", "1787211765131.pdf")
        data = generate_vocal_learning_content(pdf_path, subject)
        return Response(data)

    def post(self, request):
        text_content = request.data.get("text_content", "")
        subject_name = request.data.get("subject_name", "General")
        data = generate_vocal_learning_content(text_content, subject_name)
        return Response(data)

