from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.db.models import Q

from .models import Post, Comment, Like, Follow, Notification, Message, Conversation
from .serializers import (
    PostSerializer,
    PostCreateSerializer,
    CommentSerializer,
    FollowSerializer,
    NotificationSerializer,
    MessageSerializer,
    UserMiniSerializer,
    UserProfileSerializer,
)
from .services import create_notification

# ==========================================================
# POSTS
# ==========================================================
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import Post
from .serializers import PostSerializer, PostCreateSerializer

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import Post
from .serializers import PostSerializer, PostCreateSerializer

from django.db.models import Count, Exists, OuterRef

class PostAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Returns all posts or filtered by concept.
        Optional query param: ?concept_id=<id>
        Optional query param: ?matchmaking=true (surfaces weak concepts matched with expert peers)
        """
        concept_id = request.query_params.get("concept_id")
        matchmaking = request.query_params.get("matchmaking")

        qs = Post.objects.all().select_related("user", "concept").prefetch_related("comments__user").annotate(
            likes_count=Count("likes"),
            is_liked=Exists(
                Like.objects.filter(
                    post=OuterRef("pk"),
                    user=request.user
                )
            )
        )

        if concept_id:
            qs = qs.filter(concept_id=concept_id)

        posts = qs.order_by("-created_at")

        if matchmaking == "true":
            # 1. Fetch current user's low mastery concepts (readiness < 0.5)
            from progress.models import ConceptProgress
            weak_concept_ids = list(ConceptProgress.objects.filter(
                user=request.user,
                exam_readiness__lt=0.5
            ).values_list("concept_id", flat=True))

            if weak_concept_ids:
                # 2. Identify peer users who have high mastery in these weak concepts (readiness >= 0.8)
                strong_peer_user_ids = list(ConceptProgress.objects.filter(
                    concept_id__in=weak_concept_ids,
                    exam_readiness__gte=0.8
                ).values_list("user_id", flat=True))

                # 3. Annotate posts that match weak concepts AND are authored by strong peers
                from django.db.models import Case, When, Value, IntegerField
                posts = qs.annotate(
                    is_match=Case(
                        When(concept_id__in=weak_concept_ids, user_id__in=strong_peer_user_ids, then=Value(1)),
                        default=Value(0),
                        output_field=IntegerField()
                    )
                ).order_by("-is_match", "-created_at")

        following_ids = set(request.user.following.values_list("following_id", flat=True))
        data = PostSerializer(posts, many=True, context={"request": request, "following_ids": following_ids}).data

        return Response({"posts": data}, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Create a post with:
        - content: text
        - concept: optional concept ID
        - images: list of uploaded images
        - videos: list of video URLs
        - documents: list of uploaded files
        """
        serializer = PostCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        post = serializer.save()

        return Response(
            {
                "message": "Post created successfully",
                "data": PostSerializer(post, context={"request": request}).data,
            },
            status=status.HTTP_201_CREATED,
        )


class SinglePostAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, post_id):
        """
        Get a single post by ID
        """
        post = get_object_or_404(
            Post.objects.select_related("user", "concept").prefetch_related("comments__user"),
            id=post_id
        )
        following_ids = set(request.user.following.values_list("following_id", flat=True))
        return Response(
            PostSerializer(post, context={"request": request, "following_ids": following_ids}).data,
            status=status.HTTP_200_OK,
        )


# ==========================================================
# COMMENTS
# ==========================================================
class CommentAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)

        comment = Comment.objects.create(
            post=post,
            user=request.user,
            content=request.data.get("content", "")
        )

        if post.user != request.user:
            create_notification(
                user=post.user,
                triggered_by=request.user,
                type="comment",
                message=f"{request.user.username} commented on your post",
            )

        return Response(
            {"message": "Comment added", "data": CommentSerializer(comment,context={"request": request}).data},
            status=status.HTTP_201_CREATED,
        )


class CommentListAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, post_id):
        comments = Comment.objects.filter(post_id=post_id).select_related("user").order_by("-created_at")
        following_ids = set(request.user.following.values_list("following_id", flat=True))
        return Response(
            {
                "post": post_id,
                "comments": CommentSerializer(
                    comments,
                    many=True,
                    context={"request": request, "following_ids": following_ids}
                ).data
            },
            status=status.HTTP_200_OK
        )


# ==========================================================
# LIKE / UNLIKE
# ==========================================================
class LikeAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        like, created = Like.objects.get_or_create(post=post, user=request.user)

        if created and post.user != request.user:
            create_notification(
                user=post.user,
                triggered_by=request.user,
                type="like",
                message=f"{request.user.username} liked your post",
            )

        return Response({"message": "Post liked"}, status=status.HTTP_201_CREATED)

    def delete(self, request, post_id):
        Like.objects.filter(post_id=post_id, user=request.user).delete()
        return Response({"message": "Post unliked"}, status=status.HTTP_200_OK)


# ==========================================================
# FOLLOW / UNFOLLOW
# ==========================================================
class FollowAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        if request.user.id == user_id:
            return Response({"detail": "Cannot follow yourself"}, status=status.HTTP_400_BAD_REQUEST)

        user_obj = get_object_or_404(User, id=user_id)
        follow, created = Follow.objects.get_or_create(follower=request.user, following=user_obj)

        if created:
            create_notification(
                user=follow.following,
                triggered_by=request.user,
                type="follow",
                message=f"{request.user.username} started following you",
            )

        return Response({"status": True, "following": True}, status=status.HTTP_201_CREATED)

    def delete(self, request, user_id):
        Follow.objects.filter(follower=request.user, following_id=user_id).delete()
        return Response({"status": True, "following": False}, status=status.HTTP_200_OK)


class FollowersListAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        followers = Follow.objects.filter(following_id=user_id).select_related("follower")
        data = [{"id": f.follower.id, "username": f.follower.username} for f in followers]
        return Response({"user": user_id, "followers": data}, status=status.HTTP_200_OK)


class FollowingListAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        following = Follow.objects.filter(follower_id=user_id).select_related("following")
        data = [{"id": f.following.id, "username": f.following.username} for f in following]
        return Response({"user": user_id, "following": data}, status=status.HTTP_200_OK)


# ==========================================================
# NOTIFICATIONS
# ==========================================================
class NotificationAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = Notification.objects.filter(user=request.user).order_by("-created_at")
        return Response({"user": request.user.id, "notifications": NotificationSerializer(items, many=True,context={"request": request}).data}, status=status.HTTP_200_OK)


class NotificationReadAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        notif_id = request.data.get("notification_id")
        Notification.objects.filter(id=notif_id, user=request.user).update(is_read=True)
        return Response({"message": "Notification marked as read"}, status=status.HTTP_200_OK)


# ==========================================================
# MESSAGING
# ==========================================================
class MessageAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        receiver = get_object_or_404(User, id=user_id)
        msg = Message.objects.create(sender=request.user, receiver=receiver, text=request.data.get("text", ""))

        # Create or update Conversation record to maintain the last message link
        user1, user2 = (request.user, receiver) if request.user.id < receiver.id else (receiver, request.user)
        convo, _ = Conversation.objects.get_or_create(user1=user1, user2=user2)
        convo.last_message = msg
        convo.save()

        create_notification(user=receiver, triggered_by=request.user, type="message", message=f"New message from {request.user.username}")

        return Response({"message": "Message sent", "data": MessageSerializer(msg,context={"request": request}).data}, status=status.HTTP_201_CREATED)


class ConversationAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        # order by created_at ascending (oldest -> newest)
        messages = Message.objects.filter(
            Q(sender=request.user, receiver_id=user_id) | Q(sender_id=user_id, receiver=request.user)
        ).order_by("created_at")

        return Response({"user": user_id, "messages": MessageSerializer(messages, many=True,context={"request": request}).data}, status=status.HTTP_200_OK)


class InboxAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Return the latest message for each conversation (other participant) using the Conversation model.
        Optimized to be database-level O(1) query per request rather than walking O(N) messages in python.
        """
        user = request.user
        convos = Conversation.objects.filter(
            Q(user1=user) | Q(user2=user)
        ).select_related(
            "user1", "user2", "last_message", "last_message__sender", "last_message__receiver"
        ).order_by("-updated_at")

        latest_messages = [c.last_message for c in convos if c.last_message]
        data = MessageSerializer(latest_messages, many=True, context={"request": request}).data

        return Response({"inbox": data}, status=status.HTTP_200_OK)


# ==========================================================
# USER PROFILE & SUGGESTIONS
# ==========================================================
class UserProfileAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        user_obj = get_object_or_404(User, id=user_id)
        data = UserProfileSerializer(user_obj.profile, context={"request": request}).data
        return Response(data, status=status.HTTP_200_OK)


class SuggestedUsersAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        following_ids_qs = Follow.objects.filter(follower=request.user).values_list("following_id", flat=True)
        following_ids = set(following_ids_qs)
        suggestions = User.objects.exclude(id__in=following_ids).exclude(id=request.user.id)[:10]
        return Response(
            {"suggestions": UserMiniSerializer(suggestions, many=True, context={"request": request, "following_ids": following_ids}).data},
            status=status.HTTP_200_OK
        )
