from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.db.models import Q

from .models import Post, Comment, Like, Follow, Notification, Message
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
        """
        concept_id = request.query_params.get("concept_id")

        qs = Post.objects.all().select_related("user", "concept").annotate(
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
        data = PostSerializer(posts, many=True, context={"request": request}).data

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
            Post.objects.select_related("user", "concept"),
            id=post_id
        )
        return Response(
            PostSerializer(post, context={"request": request}).data,
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
        comments = Comment.objects.filter(post_id=post_id).order_by("-created_at")
        return Response({"post": post_id, "comments": CommentSerializer(comments, many=True,context={"request": request}).data}, status=status.HTTP_200_OK)


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
        Return the latest message for each conversation (other participant).
        This implementation is DB-agnostic: it walks messages ordered by -created_at
        and picks the first message seen per conversation partner.
        """
        msgs = Message.objects.filter(Q(sender=request.user) | Q(receiver=request.user)).order_by("-created_at")
        seen = {}
        latest_per_convo = []

        for m in msgs:
            # other participant (the user that is not request.user)
            other = m.receiver if m.sender_id == request.user.id else m.sender
            if other and other.id not in seen:
                seen[other.id] = True
                latest_per_convo.append(m)

        return Response({"inbox": MessageSerializer(latest_per_convo, many=True,context={"request": request}).data}, status=status.HTTP_200_OK)


# ==========================================================
# USER PROFILE & SUGGESTIONS
# ==========================================================
class UserProfileAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        user_obj = get_object_or_404(User, id=user_id)
        data = UserProfileSerializer(user_obj, context={"request": request}).data
        return Response(data, status=status.HTTP_200_OK)


class SuggestedUsersAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        following_ids = Follow.objects.filter(follower=request.user).values_list("following_id", flat=True)
        suggestions = User.objects.exclude(id__in=following_ids).exclude(id=request.user.id)[:10]
        return Response({"suggestions": UserMiniSerializer(suggestions, many=True).data}, status=status.HTTP_200_OK)
