from django.urls import path
from .views import BehaviorEventAPI, CatalystAPI, MindProfileAPI

urlpatterns = [
    path("event/",    BehaviorEventAPI.as_view(), name="behavior-event"),
    path("catalyst/", CatalystAPI.as_view(),      name="behavior-catalyst"),
    path("mind/",     MindProfileAPI.as_view(),   name="behavior-mind"),
]
