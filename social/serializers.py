from rest_framework import serializers
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.db.models import Count, Q
from authapp.models import UserProfile
from syllabus.models import Concept
from .models import (
    Post,
    Comment,
    Follow,
    Notification,
    Message,
    Conversation,
    ActiveSession,
    MentorshipTicket,
    ReputationPoint,
    UserBlock,
    Community,
    CommunityMember,
    Activity,
    ActivityParticipant,
    Report,
)


# ---------------------------------------------------------
# USER MINI SERIALIZER
# ---------------------------------------------------------
class UserMiniSerializer(serializers.ModelSerializer):
    is_following = serializers.SerializerMethodField()
    is_self = serializers.SerializerMethodField()
    is_blocked = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    education_stage = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "display_name",
            "avatar",
            "education_stage",
            "is_following",
            "is_self",
            "is_blocked",
        ]

    def get_display_name(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.display_name if profile and profile.display_name else obj.username

    def get_avatar(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.avatar if profile else ""

    def get_education_stage(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.education_stage if profile else "class_11_12"

    def get_is_following(self, obj):
        request = self.context.get("request")
        if not request or not request.user or request.user.is_anonymous:
            return False
        following_ids = self.context.get("following_ids")
        if following_ids is not None:
            return obj.id in following_ids
        return request.user.following.filter(following_id=obj.id).exists()

    def get_is_self(self, obj):
        request = self.context.get("request")
        if not request or not request.user or request.user.is_anonymous:
            return False
        return request.user == obj

    def get_is_blocked(self, obj):
        request = self.context.get("request")
        if not request or not request.user or request.user.is_anonymous:
            return False
        blocked_ids = self.context.get("blocked_ids")
        if blocked_ids is not None:
            return obj.id in blocked_ids
        return UserBlock.objects.filter(blocker=request.user, blocked=obj).exists()


# ---------------------------------------------------------
# USER PROFILE SERIALIZER (with Age-Aware Safety & Privacy)
# ---------------------------------------------------------
class UserProfileSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer(read_only=True)
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    posts_count = serializers.SerializerMethodField()
    communities_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    is_self = serializers.SerializerMethodField()
    is_blocked = serializers.SerializerMethodField()
    privacy = serializers.SerializerMethodField()

    # Privacy filtered fields
    display_name = serializers.CharField(read_only=True)
    education_stage = serializers.CharField(read_only=True)
    institution_name = serializers.SerializerMethodField()
    grade_or_year = serializers.SerializerMethodField()
    location_city = serializers.SerializerMethodField()
    interests = serializers.SerializerMethodField()
    skills = serializers.SerializerMethodField()
    is_minor = serializers.BooleanField(read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "user",
            "display_name",
            "bio",
            "avatar",
            "education_stage",
            "institution_name",
            "grade_or_year",
            "location_city",
            "interests",
            "skills",
            "is_minor",
            "followers_count",
            "following_count",
            "posts_count",
            "communities_count",
            "is_following",
            "is_self",
            "is_blocked",
            "privacy",
        ]

    def _can_view_details(self, obj):
        request = self.context.get("request")
        if not request or not request.user or request.user.is_anonymous:
            return obj.get_privacy().get("profile_visibility") == "public"
        if request.user == obj.user:
            return True
        privacy = obj.get_privacy()
        vis = privacy.get("profile_visibility", "public")
        if vis == "private":
            return False
        if vis == "connections":
            return Follow.objects.filter(follower=request.user, following=obj.user).exists()
        return True

    def get_followers_count(self, obj):
        return obj.user.followers.count()

    def get_following_count(self, obj):
        return obj.user.following.count()

    def get_posts_count(self, obj):
        return Post.objects.filter(user=obj.user, moderation_status="approved").count()

    def get_communities_count(self, obj):
        return obj.user.community_memberships.count()

    def get_is_following(self, obj):
        request = self.context.get("request")
        if not request or not request.user or request.user.is_anonymous:
            return False
        return Follow.objects.filter(follower=request.user, following=obj.user).exists()

    def get_is_self(self, obj):
        request = self.context.get("request")
        if not request or not request.user or request.user.is_anonymous:
            return False
        return request.user == obj.user

    def get_is_blocked(self, obj):
        request = self.context.get("request")
        if not request or not request.user or request.user.is_anonymous:
            return False
        return UserBlock.objects.filter(blocker=request.user, blocked=obj.user).exists()

    def get_privacy(self, obj):
        request = self.context.get("request")
        if request and request.user == obj.user:
            return obj.get_privacy()
        return {"profile_visibility": obj.get_privacy().get("profile_visibility", "public")}

    def get_institution_name(self, obj):
        if not self._can_view_details(obj):
            return ""
        if not obj.get_privacy().get("show_institution", True):
            return ""
        return obj.institution_name

    def get_grade_or_year(self, obj):
        if not self._can_view_details(obj):
            return ""
        return obj.grade_or_year

    def get_location_city(self, obj):
        # Age-aware safety: Do not publicly expose city of minors
        if obj.is_minor:
            request = self.context.get("request")
            if not request or request.user != obj.user:
                return ""
        if not self._can_view_details(obj):
            return ""
        return obj.location_city

    def get_interests(self, obj):
        if not self._can_view_details(obj):
            return []
        return obj.interests if isinstance(obj.interests, list) else []

    def get_skills(self, obj):
        if not self._can_view_details(obj):
            return []
        return obj.skills if isinstance(obj.skills, list) else []


# ---------------------------------------------------------
# COMMUNITY SERIALIZERS
# ---------------------------------------------------------
class CommunityMiniSerializer(serializers.ModelSerializer):
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = Community
        fields = ["id", "name", "slug", "category", "avatar", "members_count", "visibility"]

    def get_members_count(self, obj):
        return obj.members.count()


class CommunitySerializer(serializers.ModelSerializer):
    creator = UserMiniSerializer(read_only=True)
    members_count = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    user_role = serializers.SerializerMethodField()

    class Meta:
        model = Community
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "category",
            "avatar",
            "banner",
            "creator",
            "is_verified",
            "visibility",
            "rules",
            "members_count",
            "is_member",
            "user_role",
            "created_at",
        ]

    def get_members_count(self, obj):
        return obj.members.count()

    def get_is_member(self, obj):
        request = self.context.get("request")
        if not request or not request.user or request.user.is_anonymous:
            return False
        return obj.members.filter(user=request.user).exists()

    def get_user_role(self, obj):
        request = self.context.get("request")
        if not request or not request.user or request.user.is_anonymous:
            return None
        membership = obj.members.filter(user=request.user).first()
        return membership.role if membership else None


class CommunityCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Community
        fields = ["name", "description", "category", "avatar", "banner", "visibility", "rules"]

    def create(self, validated_data):
        import re
        user = self.context["request"].user
        name = validated_data["name"].strip()
        slug = re.sub(r"[^\w-]", "", name.lower().replace(" ", "-"))[:110]
        # Ensure unique slug
        base_slug = slug
        count = 1
        while Community.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{count}"
            count += 1

        community = Community.objects.create(
            creator=user,
            slug=slug,
            **validated_data
        )
        # Creator automatically joins as Admin
        CommunityMember.objects.create(community=community, user=user, role="admin")
        return community


class CommunityMemberSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer(read_only=True)

    class Meta:
        model = CommunityMember
        fields = ["id", "user", "role", "joined_at"]


# ---------------------------------------------------------
# ACTIVITY / CHALLENGE SERIALIZERS
# ---------------------------------------------------------
class ActivitySerializer(serializers.ModelSerializer):
    creator = UserMiniSerializer(read_only=True)
    participants_count = serializers.SerializerMethodField()
    is_participating = serializers.SerializerMethodField()
    user_status = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "category",
            "banner",
            "creator",
            "start_date",
            "end_date",
            "status",
            "education_stage_filter",
            "rules",
            "outcomes_summary",
            "participants_count",
            "is_participating",
            "user_status",
            "created_at",
        ]

    def get_participants_count(self, obj):
        return obj.participants.count()

    def get_is_participating(self, obj):
        request = self.context.get("request")
        if not request or not request.user or request.user.is_anonymous:
            return False
        return obj.participants.filter(user=request.user).exists()

    def get_user_status(self, obj):
        request = self.context.get("request")
        if not request or not request.user or request.user.is_anonymous:
            return None
        part = obj.participants.filter(user=request.user).first()
        return part.status if part else None


class ActivityParticipantSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer(read_only=True)

    class Meta:
        model = ActivityParticipant
        fields = [
            "id",
            "user",
            "status",
            "submission_title",
            "submission_content",
            "submission_link",
            "submitted_at",
            "feedback",
            "created_at",
        ]


# ---------------------------------------------------------
# COMMENT SERIALIZER
# ---------------------------------------------------------
class CommentSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer(read_only=True)
    replies_count = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ["id", "post", "parent", "user", "content", "created_at", "replies_count", "is_owner"]

    def get_replies_count(self, obj):
        return getattr(obj, "replies_count_annotated", obj.replies.count())

    def get_is_owner(self, obj):
        request = self.context.get("request")
        return bool(request and request.user and request.user == obj.user)


# ---------------------------------------------------------
# POST SERIALIZERS
# ---------------------------------------------------------
class PostSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer(read_only=True)
    comments = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    likes_count = serializers.IntegerField(read_only=True)
    is_liked = serializers.BooleanField(read_only=True)
    is_owner = serializers.SerializerMethodField()

    community = CommunityMiniSerializer(read_only=True)
    activity_title = serializers.CharField(source="activity.title", read_only=True, default="")
    activity_slug = serializers.CharField(source="activity.slug", read_only=True, default="")

    concept_id = serializers.IntegerField(source="concept.id", read_only=True)
    concept_name = serializers.CharField(source="concept.name", read_only=True)
    subtopic_name = serializers.CharField(source="concept.subtopic.name", read_only=True, default="")
    topic_name = serializers.CharField(source="concept.subtopic.topic.name", read_only=True, default="")
    subject_name = serializers.CharField(source="concept.subtopic.topic.subject.name", read_only=True, default="")

    media = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "user",
            "title",
            "source",
            "content_type",
            "post_type",
            "content",
            "media",
            "concept_id",
            "concept_name",
            "subtopic_name",
            "topic_name",
            "subject_name",
            "community",
            "activity_title",
            "activity_slug",
            "grade_level",
            "relevance_score",
            "domain_tag",
            "tags",
            "visibility",
            "moderation_status",
            "created_at",
            "updated_at",
            "post_metadata",
            "comments",
            "comments_count",
            "likes_count",
            "is_liked",
            "is_owner",
        ]

    def get_is_owner(self, obj):
        request = self.context.get("request")
        return bool(request and request.user and request.user == obj.user)

    def get_comments(self, obj):
        top_comments = obj.comments.filter(parent__isnull=True).order_by("-created_at")[:5]
        return CommentSerializer(top_comments, many=True, context=self.context).data

    def get_comments_count(self, obj):
        return getattr(obj, "comments_count_annotated", obj.comments.count())

    def get_media(self, obj):
        request = self.context.get("request")
        result = []
        for m in (obj.media or []):
            url = m.get("url")
            if request and url and url.startswith("/"):
                url = request.build_absolute_uri(url)
            result.append({"type": m.get("type"), "url": url})
        return result


class PostCreateSerializer(serializers.ModelSerializer):
    concept = serializers.PrimaryKeyRelatedField(
        queryset=Concept.objects.all(),
        required=False,
        allow_null=True
    )
    community = serializers.PrimaryKeyRelatedField(
        queryset=Community.objects.all(),
        required=False,
        allow_null=True
    )
    activity = serializers.PrimaryKeyRelatedField(
        queryset=Activity.objects.all(),
        required=False,
        allow_null=True
    )
    source = serializers.CharField(required=False, default="world")
    content_type = serializers.CharField(required=False, default="general")
    post_type = serializers.CharField(required=False, allow_blank=True)
    title = serializers.CharField(required=False, allow_blank=True, default="")
    grade_level = serializers.CharField(required=False, allow_blank=True)
    domain_tag = serializers.CharField(required=False, allow_blank=True)
    visibility = serializers.CharField(required=False, default="public")
    tags = serializers.ListField(child=serializers.CharField(), required=False, default=list)

    images = serializers.ListField(child=serializers.ImageField(), write_only=True, required=False)
    videos = serializers.ListField(child=serializers.URLField(), write_only=True, required=False)
    documents = serializers.ListField(child=serializers.FileField(), write_only=True, required=False)

    class Meta:
        model = Post
        fields = [
            "title",
            "content",
            "concept",
            "community",
            "activity",
            "source",
            "content_type",
            "post_type",
            "grade_level",
            "domain_tag",
            "visibility",
            "tags",
            "post_metadata",
            "images",
            "videos",
            "documents",
        ]

    def create(self, validated_data):
        user = self.context["request"].user
        media_list = []

        images = validated_data.pop("images", [])
        videos = validated_data.pop("videos", [])
        documents = validated_data.pop("documents", [])
        custom_post_type = validated_data.pop("post_type", None)

        for img in images:
            path = f"posts/{img.name}"
            saved_path = default_storage.save(path, img)
            media_list.append({"type": "image", "url": f"/media/{saved_path}"})

        for url in videos:
            media_list.append({"type": "video", "url": url})

        for doc in documents:
            path = f"posts/{doc.name}"
            saved_path = default_storage.save(path, doc)
            media_list.append({"type": "doc", "url": f"/media/{saved_path}"})

        concept = validated_data.get("concept")
        if concept and not validated_data.get("domain_tag"):
            try:
                exam = concept.subtopic.topic.subject.exam
                validated_data["domain_tag"] = exam.name
            except Exception:
                pass

        if not validated_data.get("domain_tag"):
            try:
                from progress.models import UserGoal
                active_goal = UserGoal.objects.filter(user=user).order_by("-updated_at").first()
                if active_goal and active_goal.exam:
                    validated_data["domain_tag"] = active_goal.exam.name
            except Exception:
                pass

        if custom_post_type:
            post_type = custom_post_type
        elif not media_list:
            post_type = "text"
        else:
            types = {m["type"] for m in media_list}
            post_type = "mixed" if len(types) > 1 else types.pop()

        return Post.objects.create(
            user=user,
            post_type=post_type,
            media=media_list,
            **validated_data
        )


class PostUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ["title", "content", "visibility", "tags", "post_metadata"]


# ---------------------------------------------------------
# REPORT & BLOCK SERIALIZERS
# ---------------------------------------------------------
class ReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ["target_type", "target_id", "reason", "details"]

    def create(self, validated_data):
        user = self.context["request"].user
        return Report.objects.create(reporter=user, **validated_data)


class ReportSerializer(serializers.ModelSerializer):
    reporter = UserMiniSerializer(read_only=True)

    class Meta:
        model = Report
        fields = ["id", "reporter", "target_type", "target_id", "reason", "details", "status", "action_taken", "created_at"]


class UserBlockSerializer(serializers.ModelSerializer):
    blocked_user = UserMiniSerializer(source="blocked", read_only=True)

    class Meta:
        model = UserBlock
        fields = ["id", "blocked_user", "created_at"]


# ---------------------------------------------------------
# FOLLOW, NOTIFICATION, MESSAGE SERIALIZERS
# ---------------------------------------------------------
class FollowSerializer(serializers.ModelSerializer):
    follower = UserMiniSerializer(read_only=True)
    following = UserMiniSerializer(read_only=True)

    class Meta:
        model = Follow
        fields = ["id", "follower", "following", "created_at"]


class NotificationSerializer(serializers.ModelSerializer):
    triggered_by = UserMiniSerializer(read_only=True)
    post_id = serializers.IntegerField(source="post.id", read_only=True, default=None)

    class Meta:
        model = Notification
        fields = ["id", "triggered_by", "post_id", "type", "message", "is_read", "created_at"]


class MessageSerializer(serializers.ModelSerializer):
    sender = UserMiniSerializer(read_only=True)
    receiver = UserMiniSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ["id", "sender", "receiver", "text", "created_at"]


# ---------------------------------------------------------
# ACTIVE SESSION, MENTORSHIP, REPUTATION SERIALIZERS
# ---------------------------------------------------------
class ActiveSessionSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer(read_only=True)
    concept_name = serializers.CharField(source="concept.name", read_only=True)
    concept_id = serializers.IntegerField(source="concept.id", read_only=True)

    class Meta:
        model = ActiveSession
        fields = ["id", "user", "concept_id", "concept_name", "status", "last_action_at"]


class MentorshipTicketSerializer(serializers.ModelSerializer):
    apprentice = UserMiniSerializer(read_only=True)
    mentor = UserMiniSerializer(read_only=True)
    concept_name = serializers.CharField(source="concept.name", read_only=True)
    concept_id = serializers.IntegerField(source="concept.id", read_only=True)

    class Meta:
        model = MentorshipTicket
        fields = ["id", "apprentice", "mentor", "concept_id", "concept_name", "status", "created_at"]


class ReputationPointSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer(read_only=True)

    class Meta:
        model = ReputationPoint
        fields = ["id", "user", "points", "reason", "created_at"]
