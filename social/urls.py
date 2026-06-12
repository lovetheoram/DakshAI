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
    NotificationAPI,
    NotificationReadAPI,
    MessageAPI,
    ConversationAPI,
    InboxAPI,
    UserProfileAPI,
    SuggestedUsersAPI,
)

urlpatterns = [

    # ======================================================
    # POSTS
    # ======================================================
    path("posts/", PostAPI.as_view(), name="post-list-create"),
    path("posts/<int:post_id>/", SinglePostAPI.as_view(), name="post-detail"),

    # ======================================================
    # COMMENTS (nested under posts)
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
    # FOLLOW
    # POST   → follow
    # DELETE → unfollow
    # ======================================================
    path("users/<int:user_id>/follow/", FollowAPI.as_view(), name="user-follow"),

    path("users/<int:user_id>/followers/", FollowersListAPI.as_view(), name="followers-list"),
    path("users/<int:user_id>/following/", FollowingListAPI.as_view(), name="following-list"),

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
    # USER
    # ======================================================
    path("users/<int:user_id>/profile/", UserProfileAPI.as_view(), name="user-profile"),
    path("users/suggested/", SuggestedUsersAPI.as_view(), name="suggested-users"),
]
