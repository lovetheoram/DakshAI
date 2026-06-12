from django.urls import path
from .views import ConceptProgressAPI, ConceptHistoryAPI, SubtopicProgressAPI

urlpatterns = [
    path("concept/<int:concept_id>/", ConceptProgressAPI.as_view(), name="concept-progress"),
    path("concept/<int:concept_id>/history/", ConceptHistoryAPI.as_view(), name="concept-history"),
    path("subtopic/<int:subtopic_id>/", SubtopicProgressAPI.as_view(), name="subtopic-progress"),
]
