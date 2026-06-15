from django.urls import path
from .views import (
    ConceptProgressAPI, ConceptHistoryAPI, SubtopicProgressAPI,
    UserGoalAPI, DailyTargetAPI, DailyTargetRevisionAPI,
    DailyDiaryAPI, DailyDiaryEnergyAPI, DailyTargetShareAPI, StreakStatsAPI,
    DashboardAPI
)

urlpatterns = [
    path("concept/<int:concept_id>/", ConceptProgressAPI.as_view(), name="concept-progress"),
    path("concept/<int:concept_id>/history/", ConceptHistoryAPI.as_view(), name="concept-history"),
    path("subtopic/<int:subtopic_id>/", SubtopicProgressAPI.as_view(), name="subtopic-progress"),
    path("goal/", UserGoalAPI.as_view(), name="user-goal"),
    path("dashboard/", DashboardAPI.as_view(), name="progress-dashboard"),
    path("daily-target/", DailyTargetAPI.as_view(), name="daily-target"),
    path("daily-target/revision/", DailyTargetRevisionAPI.as_view(), name="daily-target-revision"),
    path("daily-target/share/", DailyTargetShareAPI.as_view(), name="daily-target-share"),
    path("diary/", DailyDiaryAPI.as_view(), name="daily-diary"),
    path("diary/energy/", DailyDiaryEnergyAPI.as_view(), name="daily-diary-energy"),
    path("streak/", StreakStatsAPI.as_view(), name="streak-stats"),
]
