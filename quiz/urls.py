from django.urls import path
from .views import StartQuizView, SubmitQuizView,StartQuizSSEView

urlpatterns = [
    path("start/", StartQuizView.as_view(), name="quiz-start"),
    path("submit/", SubmitQuizView.as_view(), name="quiz-submit"),
    path("startAI/",StartQuizSSEView.as_view())
]
