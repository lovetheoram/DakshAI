from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from .models import Exam, Subtopic, Concept
from .serializers import ExamSerializer, ConceptSerializer
from progress.models import ConceptProgress

class SyllabusTreeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        is_anonymous = request.user is None or request.user.is_anonymous
        exam_id = request.query_params.get("exam_id")
        
        # Resolve which exam_id is being fetched.
        # If exam_id is not specified in query params and user is logged in, filter by their profile selected_exam.
        resolved_exam_id = exam_id
        if not resolved_exam_id and not is_anonymous:
            profile = getattr(request.user, "profile", None)
            if profile and profile.selected_exam:
                resolved_exam_id = str(profile.selected_exam.id)

        # Retrieve the static, progress-free syllabus tree from the cache
        cache_key = f"syllabus_tree_exam_{resolved_exam_id or 'all'}"
        static_data = cache.get(cache_key)

        if static_data is None:
            # We do not prefetch concepts as they are fetched dynamically per subtopic now
            exams = Exam.objects.prefetch_related("subjects__topics__subtopics").all()
            if resolved_exam_id:
                exams = exams.filter(id=resolved_exam_id)
            static_data = ExamSerializer(exams, many=True).data
            cache.set(cache_key, static_data, timeout=86400) # cache for 24 hours

        return Response({"exams": static_data})


class SubtopicConceptsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, subtopic_id):
        try:
            subtopic = Subtopic.objects.get(id=subtopic_id)
        except Subtopic.DoesNotExist:
            return Response({"detail": "Subtopic not found"}, status=404)

        concepts = subtopic.concepts.all()

        # Build progress dict for the current user if logged in
        progress_dict = {}
        if request.user and not request.user.is_anonymous:
            progress_records = ConceptProgress.objects.filter(user=request.user, concept__in=concepts)
            progress_dict = {cp.concept_id: cp for cp in progress_records}

        serializer = ConceptSerializer(
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