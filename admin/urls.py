from django.urls import path
# from .views import GenerateConceptPipeline
from .views import GenerateConceptMeta,GenerateConceptQuestions

urlpatterns= [
    # path("create_formulas/",GenerateConceptPipeline.as_view()),
    path("generate-meta/",GenerateConceptMeta.as_view()),
    path("generate-questions/",GenerateConceptQuestions.as_view())
]