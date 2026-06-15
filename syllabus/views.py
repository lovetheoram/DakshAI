from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from .models import Exam
from .serializers import ExamSerializer

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
        cache_key = f"syllabus_tree_anon_exam_{resolved_exam_id or 'all'}"
        static_data = cache.get(cache_key)

        if static_data is None:
            exams = Exam.objects.prefetch_related("subjects__topics__subtopics__concepts").all()
            if resolved_exam_id:
                exams = exams.filter(id=resolved_exam_id)
            # Serialize with context={"user": None} to get the static structure
            static_data = ExamSerializer(exams, many=True, context={"user": None}).data
            cache.set(cache_key, static_data, timeout=86400) # cache for 24 hours

        # For anonymous users, return the static structure directly
        if is_anonymous:
            return Response({"exams": static_data})

        # For logged-in users, dynamically overlay their progress
        import copy
        from rest_framework.fields import DateTimeField
        from progress.models import ConceptProgress

        datetime_field = DateTimeField()
        progress_records = ConceptProgress.objects.filter(user=request.user)
        progress_dict = {cp.concept_id: cp for cp in progress_records}

        exams_data = copy.deepcopy(static_data)
        for exam in exams_data:
            for subject in exam.get("subjects", []):
                for topic in subject.get("topics", []):
                    for subtopic in topic.get("subtopics", []):
                        for concept in subtopic.get("concepts", []):
                            concept_id = concept.get("id")
                            cp = progress_dict.get(concept_id)
                            if cp:
                                concept["mastery"] = list(cp.get_mastery())
                                concept["raw_mastry"] = [
                                    round(cp.exam_readiness, 4),
                                    round(cp.chapter_understanding, 4),
                                ]
                                concept["last_practiced"] = (
                                    datetime_field.to_representation(cp.last_practiced)
                                    if cp.last_practiced
                                    else None
                                )

        return Response({"exams": exams_data})

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