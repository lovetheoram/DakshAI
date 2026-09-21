from django.urls import path
from .views import (
    ConceptProgressAPI, ConceptHistoryAPI, SubtopicProgressAPI,
    UserGoalAPI, DailyTargetAPI, AppPresenceAPI, RevisionTimeAPI,
    DailyDiaryAPI, StreakStatsAPI,
    BrainEngineAPI, GalaxyAPI
)

urlpatterns = [
    path("concept/<int:concept_id>/", ConceptProgressAPI.as_view(), name="concept-progress"),
    path("concept/<int:concept_id>/history/", ConceptHistoryAPI.as_view(), name="concept-history"),
    path("subtopic/<int:subtopic_id>/", SubtopicProgressAPI.as_view(), name="subtopic-progress"),
    path("goal/", UserGoalAPI.as_view(), name="user-goal"),
    path("dashboard/", BrainEngineAPI.as_view(), name="brain-engine"),
    path("daily-target/", DailyTargetAPI.as_view(), name="daily-target"),
    path("presence/", AppPresenceAPI.as_view(), name="app-presence"),
    path("revision/", RevisionTimeAPI.as_view(), name="revision-time"),
    path("diary/", DailyDiaryAPI.as_view(), name="daily-diary"),
    path("streak/", StreakStatsAPI.as_view(), name="streak-stats"),
    path("galaxy/", GalaxyAPI.as_view(), name="galaxy"),
]
