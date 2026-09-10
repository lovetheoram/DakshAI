from django.urls import path
from .views import SyllabusTreeView, ConceptListAPI, SubtopicConceptsView, ConceptDetailAPI, ConceptPYQListView

urlpatterns = [
    path("tree/", SyllabusTreeView.as_view(), name="syllabus-tree"),
    path("conceptlist/", ConceptListAPI.as_view()),
    path("concept/<int:concept_id>/", ConceptDetailAPI.as_view(), name="concept-detail"),
    path("concept/<int:concept_id>/pyqs/", ConceptPYQListView.as_view(), name="concept-pyqs"),
    path("subtopic/<int:subtopic_id>/concepts/", SubtopicConceptsView.as_view(), name="subtopic-concepts"),
]

