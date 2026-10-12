from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import IntegrityError, models
from django.db.models import Count, Exists, OuterRef, Q, F
from django.contrib.auth.models import User
from django.core.cache import cache
from django.utils import timezone
from authapp.models import UserProfile

from .models import (
    Post,
    Comment,
    Like,
    Follow,
    Notification,
    Message,
    Conversation,
    UserBlock,
    Community,
    CommunityMember,
    Activity,
    ActivityParticipant,
    Report,
    ActiveSession,
    MentorshipTicket,
    ReputationPoint,
)
from .serializers import (
    PostSerializer,
    PostCreateSerializer,
    PostUpdateSerializer,
    CommentSerializer,
    FollowSerializer,
    NotificationSerializer,
    MessageSerializer,
    UserMiniSerializer,
    UserProfileSerializer,
    CommunitySerializer,
    CommunityCreateSerializer,
    CommunityMemberSerializer,
    ActivitySerializer,
    ActivityParticipantSerializer,
    ReportCreateSerializer,
    ReportSerializer,
    UserBlockSerializer,
    ActiveSessionSerializer,
    MentorshipTicketSerializer,
    ReputationPointSerializer,
)
from .services import create_notification


def get_blocked_user_ids(user):
    """Returns set of user IDs where user has blocked them or is blocked by them."""
    if not user or user.is_anonymous:
        return set()
    blocked_by_user = UserBlock.objects.filter(blocker=user).values_list("blocked_id", flat=True)
    blocking_user = UserBlock.objects.filter(blocked=user).values_list("blocker_id", flat=True)
    return set(blocked_by_user).union(set(blocking_user))


# ==========================================================
# POSTS & SOCIAL FEED
# ==========================================================
class PostAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Personalized & Discoverable social feed with deterministic ranking.
        Query params:
        - scope: "feed" | "my_world" | "wider_world" | "projects" | "questions" | "milestones"
        - content_type: "general" | "project" | "question" | "learning" | "strategy" | "discovery" | "opportunity" | "milestone"
        - community_id: <int>
        - activity_id: <int>
        - concept_id: <int>
        - author_id: <int>
        - search: <str>
        - page: <int> (default 1)
        - page_size: <int> (default 10)
        """
        scope = request.query_params.get("scope", "feed")
        content_type = request.query_params.get("content_type")
        community_id = request.query_params.get("community_id")
        activity_id = request.query_params.get("activity_id")
        concept_id = request.query_params.get("concept_id")
        author_id = request.query_params.get("author_id")
        search_query = request.query_params.get("search", "").strip()
        page = max(1, int(request.query_params.get("page", 1)))
        page_size = min(50, max(1, int(request.query_params.get("page_size", 10))))

        user = request.user
        following_ids = set(user.following.values_list("following_id", flat=True))
        blocked_ids = get_blocked_user_ids(user)

        qs = Post.objects.filter(moderation_status="approved").exclude(user_id__in=blocked_ids)

        qs = qs.select_related(
            "user", "user__profile", "community", "activity", "concept", "concept__subtopic", "concept__subtopic__topic", "concept__subtopic__topic__subject"
        ).prefetch_related("comments__user", "likes").annotate(
            likes_count=Count("likes", distinct=True),
            comments_count_annotated=Count("comments", filter=Q(comments__moderation_status="approved"), distinct=True),
            is_liked=Exists(
                Like.objects.filter(post=OuterRef("pk"), user=user)
            )
        )

        # Filters
        if author_id:
            qs = qs.filter(user_id=author_id)

        if community_id:
            qs = qs.filter(community_id=community_id)

        if activity_id:
            qs = qs.filter(activity_id=activity_id)

        if concept_id:
            qs = qs.filter(concept_id=concept_id)

        if content_type:
            qs = qs.filter(content_type=content_type)

        if search_query:
            qs = qs.filter(
                Q(title__icontains=search_query) |
                Q(content__icontains=search_query) |
                Q(domain_tag__icontains=search_query)
            )

        # Scope logic
        if scope == "projects":
            qs = qs.filter(content_type="project")
        elif scope == "questions":
            qs = qs.filter(content_type="question")
        elif scope == "milestones":
            qs = qs.filter(content_type="milestone")
        elif scope == "my_world":
            my_world_q = Q(user=user) | Q(user__in=following_ids)
            from progress.models import UserGoal
            active_goal = UserGoal.objects.filter(user=user).order_by("-updated_at").first()
            if active_goal and active_goal.exam:
                exam = active_goal.exam
                my_world_q = my_world_q | Q(domain_tag__icontains=exam.name) | Q(domain_tag__icontains=exam.exam_type)
            qs = qs.filter(my_world_q)
        elif scope == "wider_world":
            qs = qs.filter(community__isnull=True, concept__isnull=True)
        else:
            # Default "feed": show public posts, user's own posts, posts from followed users, and community posts user is a member of
            user_community_ids = list(CommunityMember.objects.filter(user=user).values_list("community_id", flat=True))
            feed_filter = (
                Q(visibility="public") |
                Q(user=user) |
                (Q(visibility="connections") & Q(user__in=following_ids)) |
                (Q(visibility="community") & Q(community_id__in=user_community_ids))
            )
            qs = qs.filter(feed_filter)

        # Deterministic ranking: posts are ordered by created_at descending with relevance score weighting
        posts_qs = qs.order_by("-relevance_score", "-created_at")

        # Pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size + 1
        page_items = list(posts_qs[start_idx:end_idx])

        has_more = len(page_items) > page_size
        posts = page_items[:page_size]

        context = {
            "request": request,
            "following_ids": following_ids,
            "blocked_ids": blocked_ids,
        }
        data = PostSerializer(posts, many=True, context=context).data

        return Response({
            "posts": data,
            "has_more": has_more,
            "page": page,
            "count": len(data),
        }, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = PostCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        post = serializer.save()

        # If post belongs to a community, notify community moderators
        if post.community:
            mods = CommunityMember.objects.filter(community=post.community, role__in=["admin", "moderator"]).exclude(user=request.user)
            for mod in mods:
                create_notification(
                    user=mod.user,
                    triggered_by=request.user,
                    post=post,
                    type="community",
                    message=f"{request.user.username} posted in {post.community.name}: '{post.title or post.content[:30]}'",
                )

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
        user = request.user
        blocked_ids = get_blocked_user_ids(user)
        post = get_object_or_404(
            Post.objects.select_related("user", "user__profile", "community", "activity", "concept")
            .prefetch_related("comments__user"),
            id=post_id,
            moderation_status="approved",
        )

        if post.user_id in blocked_ids:
            return Response({"detail": "Post not accessible"}, status=status.HTTP_403_FORBIDDEN)

        context = {
            "request": request,
            "following_ids": set(user.following.values_list("following_id", flat=True)),
            "blocked_ids": blocked_ids,
        }
        return Response(PostSerializer(post, context=context).data, status=status.HTTP_200_OK)

    def patch(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        if post.user != request.user:
            return Response({"detail": "Only the author can edit this post"}, status=status.HTTP_403_FORBIDDEN)

        serializer = PostUpdateSerializer(post, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_post = serializer.save()

        return Response({
            "message": "Post updated successfully",
            "data": PostSerializer(updated_post, context={"request": request}).data,
        }, status=status.HTTP_200_OK)

    def delete(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        if post.user != request.user and not request.user.is_staff:
            return Response({"detail": "Only the author can delete this post"}, status=status.HTTP_403_FORBIDDEN)

        post.delete()
        return Response({"message": "Post deleted successfully"}, status=status.HTTP_200_OK)


# ==========================================================
# COMMENTS
# ==========================================================
class CommentAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        blocked_ids = get_blocked_user_ids(request.user)
        if post.user_id in blocked_ids:
            return Response({"detail": "Cannot comment on this post"}, status=status.HTTP_403_FORBIDDEN)

        content = request.data.get("content", "").strip()
        if not content:
            return Response({"detail": "Comment content cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)

        parent_id = request.data.get("parent_id")
        parent = None
        if parent_id:
            parent = get_object_or_404(Comment, id=parent_id, post=post)

        comment = Comment.objects.create(
            post=post,
            user=request.user,
            parent=parent,
            content=content,
        )

        # Notify post author if not self
        if post.user != request.user and post.user_id not in blocked_ids:
            create_notification(
                user=post.user,
                triggered_by=request.user,
                post=post,
                type="comment",
                message=f"{request.user.username} commented on your post",
            )

        # If reply, notify parent comment author
        if parent and parent.user != request.user and parent.user != post.user and parent.user_id not in blocked_ids:
            create_notification(
                user=parent.user,
                triggered_by=request.user,
                post=post,
                type="reply",
                message=f"{request.user.username} replied to your comment",
            )

        return Response(
            {"message": "Comment added", "data": CommentSerializer(comment, context={"request": request}).data},
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request, post_id):
        comment_id = request.data.get("comment_id")
        if not comment_id:
            return Response({"detail": "comment_id required"}, status=status.HTTP_400_BAD_REQUEST)
        comment = get_object_or_404(Comment, id=comment_id, post_id=post_id)
        if comment.user != request.user and comment.post.user != request.user and not request.user.is_staff:
            return Response({"detail": "Not authorized to delete this comment"}, status=status.HTTP_403_FORBIDDEN)
        comment.delete()
        return Response({"message": "Comment deleted successfully"}, status=status.HTTP_200_OK)


class CommentListAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, post_id):
        blocked_ids = get_blocked_user_ids(request.user)
        comments = Comment.objects.filter(
            post_id=post_id,
            moderation_status="approved",
        ).exclude(user_id__in=blocked_ids).select_related("user", "user__profile").order_by("-created_at")

        context = {
            "request": request,
            "following_ids": set(request.user.following.values_list("following_id", flat=True)),
            "blocked_ids": blocked_ids,
        }
        return Response(
            {
                "post": post_id,
                "comments": CommentSerializer(comments, many=True, context=context).data,
            },
            status=status.HTTP_200_OK,
        )


# ==========================================================
# LIKES
# ==========================================================
class LikeAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        blocked_ids = get_blocked_user_ids(request.user)
        if post.user_id in blocked_ids:
            return Response({"detail": "Action prohibited"}, status=status.HTTP_403_FORBIDDEN)

        like, created = Like.objects.get_or_create(post=post, user=request.user)
        if created and post.user != request.user:
            create_notification(
                user=post.user,
                triggered_by=request.user,
                post=post,
                type="like",
                message=f"{request.user.username} liked your post",
            )
        return Response({"message": "Post liked", "status": True}, status=status.HTTP_201_CREATED)

    def delete(self, request, post_id):
        Like.objects.filter(post_id=post_id, user=request.user).delete()
        return Response({"message": "Post unliked", "status": False}, status=status.HTTP_200_OK)


# ==========================================================
# FOLLOW
# ==========================================================
class FollowAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        if request.user.id == user_id:
            return Response({"detail": "Cannot follow yourself"}, status=status.HTTP_400_BAD_REQUEST)

        blocked_ids = get_blocked_user_ids(request.user)
        if user_id in blocked_ids:
            return Response({"detail": "Cannot follow a blocked user"}, status=status.HTTP_403_FORBIDDEN)

        target_user = get_object_or_404(User, id=user_id)
        follow, created = Follow.objects.get_or_create(follower=request.user, following=target_user)

        if created:
            create_notification(
                user=target_user,
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
        blocked_ids = get_blocked_user_ids(request.user)
        followers = Follow.objects.filter(following_id=user_id).exclude(follower_id__in=blocked_ids).select_related("follower", "follower__profile")
        context = {"request": request, "following_ids": set(request.user.following.values_list("following_id", flat=True))}
        data = [UserMiniSerializer(f.follower, context=context).data for f in followers]
        return Response({"user": user_id, "followers": data}, status=status.HTTP_200_OK)


class FollowingListAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        blocked_ids = get_blocked_user_ids(request.user)
        following = Follow.objects.filter(follower_id=user_id).exclude(following_id__in=blocked_ids).select_related("following", "following__profile")
        context = {"request": request, "following_ids": set(request.user.following.values_list("following_id", flat=True))}
        data = [UserMiniSerializer(f.following, context=context).data for f in following]
        return Response({"user": user_id, "following": data}, status=status.HTTP_200_OK)


# ==========================================================
# BLOCK & SAFETY
# ==========================================================
class BlockUserAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        if request.user.id == user_id:
            return Response({"detail": "Cannot block yourself"}, status=status.HTTP_400_BAD_REQUEST)

        target = get_object_or_404(User, id=user_id)
        UserBlock.objects.get_or_create(blocker=request.user, blocked=target)

        # Break mutual follows
        Follow.objects.filter(follower=request.user, following=target).delete()
        Follow.objects.filter(follower=target, following=request.user).delete()

        return Response({"message": f"Successfully blocked {target.username}", "blocked": True}, status=status.HTTP_201_CREATED)

    def delete(self, request, user_id):
        UserBlock.objects.filter(blocker=request.user, blocked_id=user_id).delete()
        return Response({"message": "Successfully unblocked user", "blocked": False}, status=status.HTTP_200_OK)

    def get(self, request):
        blocked = UserBlock.objects.filter(blocker=request.user).select_related("blocked", "blocked__profile")
        data = UserBlockSerializer(blocked, many=True, context={"request": request}).data
        return Response({"blocked_users": data}, status=status.HTTP_200_OK)


# ==========================================================
# REPORTING & MODERATION
# ==========================================================
class ReportAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ReportCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        report = serializer.save()

        # Check threshold for automated safety flag
        threshold = 3
        count = Report.objects.filter(target_type=report.target_type, target_id=report.target_id, status="pending").count()
        if count >= threshold:
            if report.target_type == "post":
                Post.objects.filter(id=report.target_id).update(moderation_status="flagged")
            elif report.target_type == "comment":
                Comment.objects.filter(id=report.target_id).update(moderation_status="flagged")

        return Response({"message": "Report submitted for review. Thank you for keeping our community safe.", "report_id": report.id}, status=status.HTTP_201_CREATED)


# ==========================================================
# COMMUNITIES (Circles / Guilds)
# ==========================================================
class CommunityAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List communities with category filter, search, and pagination."""
        category = request.query_params.get("category")
        search_query = request.query_params.get("search", "").strip()

        qs = Community.objects.all().select_related("creator").prefetch_related("members")
        if category:
            qs = qs.filter(category__iexact=category)
        if search_query:
            qs = qs.filter(Q(name__icontains=search_query) | Q(description__icontains=search_query))

        communities = qs.order_by("-created_at")
        data = CommunitySerializer(communities, many=True, context={"request": request}).data
        return Response({"communities": data}, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = CommunityCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        community = serializer.save()
        return Response(
            {"message": "Community created successfully", "community": CommunitySerializer(community, context={"request": request}).data},
            status=status.HTTP_201_CREATED
        )


class CommunityDetailAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug_or_id):
        if str(slug_or_id).isdigit():
            community = get_object_or_404(Community, id=int(slug_or_id))
        else:
            community = get_object_or_404(Community, slug=slug_or_id)

        data = CommunitySerializer(community, context={"request": request}).data
        # Include top active members
        members = community.members.select_related("user", "user__profile").order_by("-joined_at")[:12]
        data["recent_members"] = CommunityMemberSerializer(members, many=True, context={"request": request}).data

        return Response(data, status=status.HTTP_200_OK)


class CommunityMembershipAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, community_id):
        community = get_object_or_404(Community, id=community_id)
        member, created = CommunityMember.objects.get_or_create(community=community, user=request.user)
        return Response({"status": True, "is_member": True, "message": f"Joined {community.name}"}, status=status.HTTP_201_CREATED)

    def delete(self, request, community_id):
        community = get_object_or_404(Community, id=community_id)
        if community.creator == request.user:
            return Response({"detail": "Community creator cannot leave their own community"}, status=status.HTTP_400_BAD_REQUEST)
        CommunityMember.objects.filter(community=community, user=request.user).delete()
        return Response({"status": True, "is_member": False, "message": f"Left {community.name}"}, status=status.HTTP_200_OK)


# ==========================================================
# ACTIVITIES & CHALLENGES
# ==========================================================
class ActivityAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        category = request.query_params.get("category")
        status_val = request.query_params.get("status")
        stage = request.query_params.get("stage")

        qs = Activity.objects.all().select_related("creator").prefetch_related("participants")
        if category:
            qs = qs.filter(category__iexact=category)
        if status_val:
            qs = qs.filter(status=status_val)
        if stage and stage != "all":
            qs = qs.filter(Q(education_stage_filter="all") | Q(education_stage_filter__iexact=stage))

        activities = qs.order_by("-created_at")
        data = ActivitySerializer(activities, many=True, context={"request": request}).data
        return Response({"activities": data}, status=status.HTTP_200_OK)

    def post(self, request):
        title = request.data.get("title", "").strip()
        description = request.data.get("description", "").strip()
        if not title or not description:
            return Response({"detail": "Title and description required"}, status=status.HTTP_400_BAD_REQUEST)

        import re
        slug = re.sub(r"[^\w-]", "", title.lower().replace(" ", "-"))[:200]
        base_slug = slug
        count = 1
        while Activity.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{count}"
            count += 1

        activity = Activity.objects.create(
            title=title,
            slug=slug,
            description=description,
            category=request.data.get("category", "Challenge"),
            banner=request.data.get("banner", ""),
            creator=request.user,
            rules=request.data.get("rules", ""),
            education_stage_filter=request.data.get("education_stage_filter", "all"),
            status=request.data.get("status", "active"),
        )
        return Response(ActivitySerializer(activity, context={"request": request}).data, status=status.HTTP_201_CREATED)


class ActivityDetailAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug_or_id):
        if str(slug_or_id).isdigit():
            activity = get_object_or_404(Activity, id=int(slug_or_id))
        else:
            activity = get_object_or_404(Activity, slug=slug_or_id)

        data = ActivitySerializer(activity, context={"request": request}).data
        # Recent submissions/participants
        submissions = activity.participants.select_related("user", "user__profile").order_by("-submitted_at")[:10]
        data["recent_participants"] = ActivityParticipantSerializer(submissions, many=True, context={"request": request}).data
        return Response(data, status=status.HTTP_200_OK)


class ActivityParticipateAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, activity_id):
        activity = get_object_or_404(Activity, id=activity_id)
        action = request.data.get("action", "register") # "register" | "submit"

        participant, _ = ActivityParticipant.objects.get_or_create(activity=activity, user=request.user)

        if action == "submit":
            participant.submission_title = request.data.get("submission_title", "")
            participant.submission_content = request.data.get("submission_content", "")
            participant.submission_link = request.data.get("submission_link", "")
            participant.submitted_at = timezone.now()
            participant.status = "submitted"
            participant.save()

            # Award reputation points for completing an activity
            ReputationPoint.objects.create(
                user=request.user,
                points=25,
                reason=f"Participated in challenge: {activity.title}"
            )
            return Response({"message": "Submission received!", "participant": ActivityParticipantSerializer(participant, context={"request": request}).data})

        return Response({"message": "Registered for challenge", "participant": ActivityParticipantSerializer(participant, context={"request": request}).data})


# ==========================================================
# UNIFIED DISCOVERY & SEARCH
# ==========================================================
class DiscoverAPI(APIView):
    """
    Unified Social Discovery Engine.
    Exposes talent, projects, questions, communities, activities, and interests.
    Zero fake stories. Deterministic and privacy-filtered.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        stage = request.query_params.get("stage")
        blocked_ids = get_blocked_user_ids(user)
        following_ids = set(user.following.values_list("following_id", flat=True))

        context = {
            "request": request,
            "following_ids": following_ids,
            "blocked_ids": blocked_ids,
        }

        # 1. Featured Projects
        projects_qs = Post.objects.filter(
            content_type="project",
            visibility="public",
            moderation_status="approved",
        ).exclude(user_id__in=blocked_ids).select_related("user", "user__profile")[:6]
        projects_data = PostSerializer(projects_qs, many=True, context=context).data

        # 2. Open Questions Needing Answers
        questions_qs = Post.objects.filter(
            content_type="question",
            visibility="public",
            moderation_status="approved",
        ).exclude(user_id__in=blocked_ids).select_related("user", "user__profile")[:6]
        questions_data = PostSerializer(questions_qs, many=True, context=context).data

        # 3. People to Discover (Curiosity & Shared Interests)
        people_qs = User.objects.exclude(id=user.id).exclude(id__in=following_ids).exclude(id__in=blocked_ids).select_related("profile")
        if stage:
            people_qs = people_qs.filter(profile__education_stage=stage)

        # Filter out private profiles from discovery
        people_qs = people_qs.filter(
            Q(profile__isnull=True) |
            ~Q(profile__privacy_settings__profile_visibility="private")
        )[:8]
        people_data = UserMiniSerializer(people_qs, many=True, context=context).data

        # 4. Featured Communities
        communities_qs = Community.objects.all().select_related("creator")[:6]
        communities_data = CommunitySerializer(communities_qs, many=True, context=context).data

        # 5. Active Challenges & Sprints
        activities_qs = Activity.objects.filter(status="active").select_related("creator")[:6]
        activities_data = ActivitySerializer(activities_qs, many=True, context=context).data

        return Response({
            "projects": projects_data,
            "questions": questions_data,
            "people": people_data,
            "communities": communities_data,
            "activities": activities_data,
        }, status=status.HTTP_200_OK)


class SearchAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if not q or len(q) < 2:
            return Response({"people": [], "posts": [], "communities": []}, status=status.HTTP_200_OK)

        user = request.user
        blocked_ids = get_blocked_user_ids(user)
        following_ids = set(user.following.values_list("following_id", flat=True))
        context = {"request": request, "following_ids": following_ids, "blocked_ids": blocked_ids}

        # People search (safely exclude private & blocked accounts)
        people = User.objects.filter(
            Q(username__icontains=q) | Q(profile__display_name__icontains=q) | Q(profile__interests__icontains=q) | Q(profile__skills__icontains=q)
        ).exclude(id=user.id).exclude(id__in=blocked_ids).filter(
            Q(profile__isnull=True) | ~Q(profile__privacy_settings__profile_visibility="private")
        )[:10]

        # Post search
        posts = Post.objects.filter(
            Q(title__icontains=q) | Q(content__icontains=q) | Q(domain_tag__icontains=q),
            visibility="public",
            moderation_status="approved",
        ).exclude(user_id__in=blocked_ids).select_related("user", "user__profile")[:10]

        # Communities search
        communities = Community.objects.filter(
            Q(name__icontains=q) | Q(description__icontains=q) | Q(category__icontains=q)
        )[:6]

        return Response({
            "query": q,
            "people": UserMiniSerializer(people, many=True, context=context).data,
            "posts": PostSerializer(posts, many=True, context=context).data,
            "communities": CommunitySerializer(communities, many=True, context=context).data,
        }, status=status.HTTP_200_OK)


# ==========================================================
# NOTIFICATIONS
# ==========================================================
class NotificationAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = Notification.objects.filter(user=request.user).select_related("triggered_by", "triggered_by__profile", "post").order_by("-created_at")[:50]
        return Response({
            "user": request.user.id,
            "notifications": NotificationSerializer(items, many=True, context={"request": request}).data,
            "unread_count": Notification.objects.filter(user=request.user, is_read=False).count()
        }, status=status.HTTP_200_OK)


class NotificationReadAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        notif_id = request.data.get("notification_id")
        if notif_id:
            Notification.objects.filter(id=notif_id, user=request.user).update(is_read=True)
        else:
            Notification.objects.filter(user=request.user).update(is_read=True)
        return Response({"message": "Notifications marked as read"}, status=status.HTTP_200_OK)


# ==========================================================
# MESSAGING (with Age-Aware Safety Restrictions)
# ==========================================================
class MessageAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        receiver = get_object_or_404(User, id=user_id)
        if request.user.id == receiver.id:
            return Response({"detail": "Cannot message yourself"}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Block check
        blocked_ids = get_blocked_user_ids(request.user)
        if receiver.id in blocked_ids:
            return Response({"detail": "Messaging is not permitted between these accounts"}, status=status.HTTP_403_FORBIDDEN)

        # 2. Age-aware protection: if receiver is a minor or sender is minor, enforce mutual connection or messaging permissions
        receiver_profile = getattr(receiver, "profile", None)
        sender_profile = getattr(request.user, "profile", None)

        receiver_msg_perm = receiver_profile.get_privacy().get("allow_messages_from", "everyone") if receiver_profile else "everyone"

        if receiver_msg_perm == "none":
            return Response({"detail": "This user has disabled direct messages"}, status=status.HTTP_403_FORBIDDEN)

        if receiver_msg_perm == "followers":
            is_follower = Follow.objects.filter(follower=request.user, following=receiver).exists()
            if not is_follower:
                return Response({"detail": "This user only accepts messages from their followers"}, status=status.HTTP_403_FORBIDDEN)

        # Minor safety safeguard: A minor cannot receive unsolicited messages from non-connections
        if receiver_profile and receiver_profile.is_minor:
            is_mutual = Follow.objects.filter(follower=request.user, following=receiver).exists() and Follow.objects.filter(follower=receiver, following=request.user).exists()
            if not is_mutual:
                return Response({"detail": "This student account only accepts messages from confirmed mutual peers"}, status=status.HTTP_403_FORBIDDEN)

        text = request.data.get("text", "").strip()
        if not text:
            return Response({"detail": "Message text cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)

        msg = Message.objects.create(sender=request.user, receiver=receiver, text=text)

        user1, user2 = (request.user, receiver) if request.user.id < receiver.id else (receiver, request.user)
        convo, _ = Conversation.objects.get_or_create(user1=user1, user2=user2)
        convo.last_message = msg
        convo.save()

        create_notification(user=receiver, triggered_by=request.user, type="message", message=f"New message from {request.user.username}")
        return Response({"message": "Message sent", "data": MessageSerializer(msg, context={"request": request}).data}, status=status.HTTP_201_CREATED)


class ConversationAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        blocked_ids = get_blocked_user_ids(request.user)
        if user_id in blocked_ids:
            return Response({"detail": "Chat is unavailable with blocked user"}, status=status.HTTP_403_FORBIDDEN)

        messages = Message.objects.filter(
            Q(sender=request.user, receiver_id=user_id) | Q(sender_id=user_id, receiver=request.user)
        ).select_related("sender", "receiver").order_by("created_at")

        return Response({"user": user_id, "messages": MessageSerializer(messages, many=True, context={"request": request}).data}, status=status.HTTP_200_OK)


class InboxAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        blocked_ids = get_blocked_user_ids(user)

        convos = Conversation.objects.filter(
            Q(user1=user) | Q(user2=user)
        ).exclude(
            Q(user1__in=blocked_ids) | Q(user2__in=blocked_ids)
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
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        user_obj = get_object_or_404(User, id=user_id)
        profile_obj, _ = UserProfile.objects.get_or_create(user=user_obj)

        following_ids = set()
        blocked_ids = set()
        if request.user and not request.user.is_anonymous:
            following_ids = set(request.user.following.values_list("following_id", flat=True))
            blocked_ids = get_blocked_user_ids(request.user)

        context = {
            "request": request,
            "following_ids": following_ids,
            "blocked_ids": blocked_ids,
        }
        data = UserProfileSerializer(profile_obj, context=context).data
        return Response(data, status=status.HTTP_200_OK)


class SuggestedUsersAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        following_ids = set(user.following.values_list("following_id", flat=True))
        blocked_ids = get_blocked_user_ids(user)

        suggestions = User.objects.exclude(id__in=following_ids).exclude(id=user.id).exclude(id__in=blocked_ids).select_related("profile")
        # Exclude private accounts
        suggestions = suggestions.filter(
            Q(profile__isnull=True) | ~Q(profile__privacy_settings__profile_visibility="private")
        )[:10]

        context = {
            "request": request,
            "following_ids": following_ids,
            "blocked_ids": blocked_ids,
        }
        return Response(
            {"suggestions": UserMiniSerializer(suggestions, many=True, context=context).data},
            status=status.HTTP_200_OK
        )


# ==========================================================
# MULTIPLAYER LEARNING WORLD & ACTIVE SESSIONS
# ==========================================================
class LobbyAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cache_key = "multiplayer_lobby_data"
        lobby_data = cache.get(cache_key)

        if lobby_data is None:
            threshold = timezone.now() - timezone.timedelta(minutes=30)
            active_sessions = ActiveSession.objects.filter(last_action_at__gte=threshold).select_related("user", "concept__subtopic__topic__subject")
            total_online = active_sessions.count()

            by_subject = {}
            active_sprints = {}
            for sess in active_sessions:
                if sess.concept and sess.concept.subtopic and sess.concept.subtopic.topic and sess.concept.subtopic.topic.subject:
                    sub_name = sess.concept.subtopic.topic.subject.name
                    by_subject[sub_name] = by_subject.get(sub_name, 0) + 1
                    concept_name = sess.concept.name
                    active_sprints[concept_name] = active_sprints.get(concept_name, 0) + 1

            formatted_sprints = [{"concept_name": name, "count": cnt} for name, cnt in active_sprints.items()]
            leaderboard_qs = ReputationPoint.objects.values("user__id", "user__username").annotate(
                total_points=models.Sum("points")
            ).order_by("-total_points")[:5]

            leaderboard = [
                {"id": item["user__id"], "username": item["user__username"], "points": item["total_points"]}
                for item in leaderboard_qs
            ]

            lobby_data = {
                "total_online": total_online,
                "by_subject": by_subject,
                "active_sprints": formatted_sprints[:5],
                "leaderboard": leaderboard,
            }
            cache.set(cache_key, lobby_data, timeout=180)

        my_session = ActiveSession.objects.filter(user=request.user).first()
        my_session_data = ActiveSessionSerializer(my_session, context={"request": request}).data if my_session else None
        open_tickets_count = MentorshipTicket.objects.filter(status="open").count()

        return Response({
            "lobby": lobby_data,
            "my_session": my_session_data,
            "open_tickets_count": open_tickets_count
        })


class SessionPingAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        status_val = request.data.get("status")
        concept_id = request.data.get("concept_id")

        if not status_val:
            ActiveSession.objects.filter(user=user).delete()
            cache.delete("multiplayer_lobby_data")
            return Response({"message": "Session cleared"}, status=status.HTTP_200_OK)

        from syllabus.models import Concept
        concept = get_object_or_404(Concept, id=concept_id) if concept_id else None

        try:
            active_sess, _ = ActiveSession.objects.update_or_create(
                user=user,
                defaults={
                    "status": status_val,
                    "concept": concept,
                    "last_action_at": timezone.now()
                }
            )
        except IntegrityError:
            ActiveSession.objects.filter(user=user).update(
                status=status_val,
                concept=concept,
                last_action_at=timezone.now()
            )
            active_sess = ActiveSession.objects.get(user=user)

        cache.delete("multiplayer_lobby_data")
        return Response(ActiveSessionSerializer(active_sess, context={"request": request}).data)


class MentorshipTicketAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        eligible = request.query_params.get("eligible")
        qs = MentorshipTicket.objects.filter(status="open").select_related("apprentice", "concept")

        if eligible == "true":
            from progress.models import ConceptProgress
            mastered_concepts = ConceptProgress.objects.filter(
                user=request.user,
                readiness__gte=0.70
            ).values_list("concept_id", flat=True)
            qs = qs.filter(concept_id__in=mastered_concepts)

        tickets = qs.order_by("-created_at")
        return Response(MentorshipTicketSerializer(tickets, many=True, context={"request": request}).data)

    def post(self, request):
        concept_id = request.data.get("concept_id")
        if not concept_id:
            return Response({"detail": "concept_id required"}, status=400)

        from syllabus.models import Concept
        concept = get_object_or_404(Concept, id=concept_id)

        ticket, _ = MentorshipTicket.objects.get_or_create(
            apprentice=request.user,
            concept=concept,
            status="open"
        )
        return Response(MentorshipTicketSerializer(ticket, context={"request": request}).data, status=status.HTTP_201_CREATED)


class MentorshipActionAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ticket_id):
        action = request.data.get("action")
        ticket = get_object_or_404(MentorshipTicket, id=ticket_id)

        if action == "accept":
            if ticket.apprentice == request.user:
                return Response({"detail": "Cannot mentor yourself"}, status=400)
            if ticket.status != "open":
                return Response({"detail": "Ticket already taken"}, status=400)

            ticket.mentor = request.user
            ticket.status = "active"
            ticket.save()

            create_notification(
                user=ticket.apprentice,
                triggered_by=request.user,
                type="post",
                message=f"🎓 {request.user.username} accepted your help ticket for {ticket.concept.name}!",
            )

            user1, user2 = (ticket.apprentice, request.user) if ticket.apprentice.id < request.user.id else (request.user, ticket.apprentice)
            Conversation.objects.get_or_create(user1=user1, user2=user2)
            return Response(MentorshipTicketSerializer(ticket, context={"request": request}).data)

        elif action == "resolve":
            if ticket.mentor != request.user:
                return Response({"detail": "Only the mentor can resolve this ticket"}, status=400)
            if ticket.status != "active":
                return Response({"detail": "Ticket is not active"}, status=400)

            ticket.status = "resolved"
            ticket.save()

            ReputationPoint.objects.create(
                user=request.user,
                points=15,
                reason=f"Mentored peer on {ticket.concept.name}"
            )

            create_notification(
                user=ticket.apprentice,
                triggered_by=request.user,
                type="post",
                message=f"🏆 Mentorship resolved! {request.user.username} gained +15 reputation.",
            )
            return Response(MentorshipTicketSerializer(ticket, context={"request": request}).data)

        return Response({"detail": "Invalid action"}, status=400)


# ==========================================================
# CONCEPT SPARKS & DETERMINISTIC INSIGHTS
# ==========================================================
class ConceptSparksAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, concept_id=None):
        if not concept_id:
            concept_id = request.query_params.get("concept_id")

        sparks_qs = Post.objects.filter(moderation_status="approved").select_related("user", "concept").prefetch_related("comments__user").annotate(
            likes_count=Count("likes"),
            is_liked=Exists(
                Like.objects.filter(post=OuterRef("pk"), user=request.user)
            )
        )

        if concept_id:
            sparks_qs = sparks_qs.filter(concept_id=concept_id)

        sparks = sparks_qs.order_by("-relevance_score", "-created_at")[:10]
        serialized_sparks = PostSerializer(sparks, many=True, context={"request": request}).data

        opportunities = [
            {
                "id": 1,
                "title": "National Math & Science Olympiad 2026",
                "category": "Olympiad",
                "deadline": "Registration closes soon",
                "tag": "Mathematics & Physics"
            },
            {
                "id": 2,
                "title": "Global Student Robotics Hackathon",
                "category": "Competition",
                "deadline": "Open to School & College",
                "tag": "Hardware & Code"
            }
        ]

        return Response({
            "concept_id": concept_id,
            "sparks": serialized_sparks,
            "opportunities": opportunities,
            "total_sparks": sparks.count()
        })


class ProgressInsightsAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from progress.models import ConceptProgress, StudyLog
        from django.db.models import Avg

        user_progress = ConceptProgress.objects.filter(user=request.user)
        total_concepts = user_progress.count()
        mastered_concepts = user_progress.filter(readiness__gte=0.8).count()
        avg_readiness = user_progress.aggregate(Avg("readiness"))["readiness__avg"] or 0.0

        logs = StudyLog.objects.filter(user=request.user)
        total_minutes = sum(log.duration_minutes for log in logs)

        velocity_text = f"You have mastered {mastered_concepts} of {total_concepts} topics with {int(avg_readiness * 100)}% readiness score."
        if avg_readiness >= 0.7:
            insight_hint = "High concept retention rate! Focus on challenge problems and projects."
        elif avg_readiness >= 0.4:
            insight_hint = "Steady momentum! Review your incorrect quiz attempts to unlock mastery."
        else:
            insight_hint = "Starting strong! Practice short daily retrieval sessions to build long-term retention."

        return Response({
            "total_concepts": total_concepts,
            "mastered_concepts": mastered_concepts,
            "avg_readiness_percentage": round(avg_readiness * 100, 1),
            "total_study_minutes": total_minutes,
            "velocity_text": velocity_text,
            "insight_hint": insight_hint,
        })
