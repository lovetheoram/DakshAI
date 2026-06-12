from django.urls import path
from .views import SyllabusTreeView,ConceptListAPI

urlpatterns = [
    path("tree/", SyllabusTreeView.as_view(), name="syllabus-tree"),
    path("conceptlist/", ConceptListAPI.as_view()),

]
