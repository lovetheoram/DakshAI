from django.urls import path
from .views import SyllabusTreeView, ConceptListAPI, SubtopicConceptsView

urlpatterns = [
    path("tree/", SyllabusTreeView.as_view(), name="syllabus-tree"),
    path("conceptlist/", ConceptListAPI.as_view()),
    path("subtopic/<int:subtopic_id>/concepts/", SubtopicConceptsView.as_view(), name="subtopic-concepts"),
]
