from django.urls import path
from .views import (
    PostAPI,
    SinglePostAPI,
    CommentAPI,
    CommentListAPI,
    LikeAPI,
    FollowAPI,
    FollowersListAPI,
    FollowingListAPI,
    BlockUserAPI,
    ReportAPI,
    CommunityAPI,
    CommunityDetailAPI,
    CommunityMembershipAPI,
    ActivityAPI,
    ActivityDetailAPI,
    ActivityParticipateAPI,
    DiscoverAPI,
    SearchAPI,
    NotificationAPI,
    NotificationReadAPI,
    MessageAPI,
    ConversationAPI,
    InboxAPI,
    UserProfileAPI,
    SuggestedUsersAPI,
    LobbyAPI,
    SessionPingAPI,
    MentorshipTicketAPI,
    MentorshipActionAPI,
    ConceptSparksAPI,
    ProgressInsightsAPI,
)

urlpatterns = [
    # Concept Sparks & Insights (Deterministic Recommendations)
    path("concept-sparks/", ConceptSparksAPI.as_view(), name="concept-sparks-query"),
    path("concept-sparks/<int:concept_id>/", ConceptSparksAPI.as_view(), name="concept-sparks"),
    path("insights/", ProgressInsightsAPI.as_view(), name="progress-insights"),

    # ======================================================
    # DISCOVERY & SEARCH
    # ======================================================
    path("discover/", DiscoverAPI.as_view(), name="social-discover"),
    path("search/", SearchAPI.as_view(), name="social-search"),

    # ======================================================
    # POSTS (CRUD)
    # ======================================================
    path("posts/", PostAPI.as_view(), name="post-list-create"),
    path("posts/<int:post_id>/", SinglePostAPI.as_view(), name="post-detail"),

    # ======================================================
    # COMMENTS (nested under posts, supports replies & deletion)
    # ======================================================
    path("posts/<int:post_id>/comments/", CommentAPI.as_view(), name="comment-create"),
    path("posts/<int:post_id>/comments/list/", CommentListAPI.as_view(), name="comment-list"),

    # ======================================================
    # LIKES (single endpoint, method-based)
    # POST   → like
    # DELETE → unlike
    # ======================================================
    path("posts/<int:post_id>/like/", LikeAPI.as_view(), name="post-like"),

    # ======================================================
    # COMMUNITIES (Circles / Guilds)
    # ======================================================
    path("communities/", CommunityAPI.as_view(), name="community-list-create"),
    path("communities/<str:slug_or_id>/", CommunityDetailAPI.as_view(), name="community-detail"),
    path("communities/<int:community_id>/membership/", CommunityMembershipAPI.as_view(), name="community-membership"),

    # ======================================================
    # ACTIVITIES & CHALLENGES
    # ======================================================
    path("activities/", ActivityAPI.as_view(), name="activity-list-create"),
    path("activities/<str:slug_or_id>/", ActivityDetailAPI.as_view(), name="activity-detail"),
    path("activities/<int:activity_id>/participate/", ActivityParticipateAPI.as_view(), name="activity-participate"),

    # ======================================================
    # FOLLOW, BLOCK & RELATIONSHIPS
    # ======================================================
    path("users/<int:user_id>/follow/", FollowAPI.as_view(), name="user-follow"),
    path("users/<int:user_id>/followers/", FollowersListAPI.as_view(), name="followers-list"),
    path("users/<int:user_id>/following/", FollowingListAPI.as_view(), name="following-list"),
    path("users/<int:user_id>/block/", BlockUserAPI.as_view(), name="user-block"),
    path("users/blocked/", BlockUserAPI.as_view(), name="user-blocked-list"),

    # ======================================================
    # SAFETY & REPORTING
    # ======================================================
    path("reports/", ReportAPI.as_view(), name="social-reports"),

    # ======================================================
    # NOTIFICATIONS
    # ======================================================
    path("notifications/", NotificationAPI.as_view(), name="notifications"),
    path("notifications/read/", NotificationReadAPI.as_view(), name="notification-read"),

    # ======================================================
    # MESSAGING
    # ======================================================
    path("messages/inbox/", InboxAPI.as_view(), name="inbox"),
    path("messages/<int:user_id>/", ConversationAPI.as_view(), name="conversation"),
    path("messages/<int:user_id>/send/", MessageAPI.as_view(), name="message-send"),

    # ======================================================
    # USER PROFILES
    # ======================================================
    path("users/<int:user_id>/profile/", UserProfileAPI.as_view(), name="user-profile"),
    path("users/suggested/", SuggestedUsersAPI.as_view(), name="suggested-users"),

    # ======================================================
    # MULTIPLAYER LEARNING WORLD (DakshAI Social v4)
    # ======================================================
    path("lobby/", LobbyAPI.as_view(), name="multiplayer-lobby"),
    path("session/ping/", SessionPingAPI.as_view(), name="session-ping"),
    path("exchange/tickets/", MentorshipTicketAPI.as_view(), name="mentorship-tickets"),
    path("exchange/tickets/<int:ticket_id>/action/", MentorshipActionAPI.as_view(), name="mentorship-ticket-action"),
]
