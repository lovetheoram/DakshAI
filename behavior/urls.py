from django.urls import path
from .views import BehaviorEventAPI, CatalystAPI, InterventionAPI, MindProfileAPI

urlpatterns = [
    path("event/",                 BehaviorEventAPI.as_view(), name="behavior-event"),
    path("catalyst/",              CatalystAPI.as_view(),      name="behavior-catalyst"),
    path("catalyst/intervention/", InterventionAPI.as_view(),  name="behavior-intervention"),
    path("mind/",                  MindProfileAPI.as_view(),   name="behavior-mind"),
]
