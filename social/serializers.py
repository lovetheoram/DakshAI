from rest_framework import serializers
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from .models import Post, Comment, Follow, Notification, Message, ActiveSession, MentorshipTicket, ReputationPoint
from syllabus.models import Concept


# ---------------------------------------------------------
# USER MINI SERIALIZER
# ---------------------------------------------------------
class UserMiniSerializer(serializers.ModelSerializer):
    is_following = serializers.SerializerMethodField()
    is_self = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "is_following", "is_self"]

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

# ---------------------------------------------------------
# USER PROFILE SERIALIZER (for profile page & suggestions)
# ---------------------------------------------------------

from rest_framework import serializers
from authapp.models import UserProfile

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer(read_only=True)
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    is_self = serializers.SerializerMethodField()
    is_private = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "user",
            "bio",
            "avatar",
            "followers_count",
            "following_count",
            "is_following",
            "is_self",
            "is_private",
        ]

    def get_followers_count(self, obj):
        return obj.user.followers.count()

    def get_following_count(self, obj):
        return obj.user.following.count()

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

    def get_is_private(self, obj):
        return getattr(obj, "is_private", False)

# ---------------------------------------------------------
# COMMENT SERIALIZER
# ---------------------------------------------------------
class CommentSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer()

    class Meta:
        model = Comment
        fields = ["id", "user", "content", "created_at"]


# ---------------------------------------------------------
# POST SERIALIZER
# ---------------------------------------------------------

class PostSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer(read_only=True)
    comments = CommentSerializer(many=True, read_only=True)

    likes_count = serializers.IntegerField(read_only=True)
    is_liked = serializers.BooleanField(read_only=True)

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
            "grade_level",
            "relevance_score",
            "domain_tag",
            "created_at",
            "post_metadata",
            "comments",
            "likes_count",
            "is_liked",
        ]

    def get_media(self, obj):
        """
        Convert relative media URLs -> absolute URLs
        """
        request = self.context.get("request")
        result = []

        for m in obj.media:
            url = m.get("url")

            # Convert only if relative
            if request and url and url.startswith("/"):
                url = request.build_absolute_uri(url)

            result.append({
                "type": m.get("type"),
                "url": url
            })

        return result


class PostCreateSerializer(serializers.ModelSerializer):
    concept = serializers.PrimaryKeyRelatedField(
        queryset=Concept.objects.all(),
        required=False,
        allow_null=True
    )
    source = serializers.CharField(required=False, default="world")
    content_type = serializers.CharField(required=False, default="general")
    post_type = serializers.CharField(required=False, allow_blank=True)
    grade_level = serializers.CharField(required=False, allow_blank=True)
    domain_tag = serializers.CharField(required=False, allow_blank=True)

    # Media inputs
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False
    )
    videos = serializers.ListField(
        child=serializers.URLField(),
        write_only=True,
        required=False
    )
    documents = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Post
        fields = ["content", "concept", "source", "content_type", "post_type", "grade_level", "domain_tag", "post_metadata", "images", "videos", "documents"]

    def create(self, validated_data):
        user = self.context["request"].user
        media_list = []

        images = validated_data.pop("images", [])
        videos = validated_data.pop("videos", [])
        documents = validated_data.pop("documents", [])
        custom_post_type = validated_data.pop("post_type", None)

        # Store images in media/posts/
        for img in images:
            path = f"posts/{img.name}"
            saved_path = default_storage.save(path, img)
            media_list.append({"type": "image", "url": f"/media/{saved_path}"})

        # Videos are URLs
        for url in videos:
            media_list.append({"type": "video", "url": url})

        # Documents in media/posts/
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


# ---------------------------------------------------------
# FOLLOW SERIALIZER
# ---------------------------------------------------------
class FollowSerializer(serializers.ModelSerializer):
    follower = UserMiniSerializer()
    following = UserMiniSerializer()

    class Meta:
        model = Follow
        fields = ["id", "follower", "following", "created_at"]


# ---------------------------------------------------------
# NOTIFICATION SERIALIZER
# ---------------------------------------------------------
class NotificationSerializer(serializers.ModelSerializer):
    triggered_by = UserMiniSerializer()

    class Meta:
        model = Notification
        fields = ["id", "triggered_by", "type", "message", "is_read", "created_at"]


# ---------------------------------------------------------
# MESSAGE SERIALIZER
# ---------------------------------------------------------
class MessageSerializer(serializers.ModelSerializer):
    sender = UserMiniSerializer()
    receiver = UserMiniSerializer()

    class Meta:
        model = Message
        fields = ["id", "sender", "receiver", "text", "created_at"]


# ---------------------------------------------------------
# ACTIVE SESSION SERIALIZER
# ---------------------------------------------------------
class ActiveSessionSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer(read_only=True)
    concept_name = serializers.CharField(source="concept.name", read_only=True)
    concept_id = serializers.IntegerField(source="concept.id", read_only=True)

    class Meta:
        model = ActiveSession
        fields = ["id", "user", "concept_id", "concept_name", "status", "last_action_at"]


# ---------------------------------------------------------
# MENTORSHIP TICKET SERIALIZER
# ---------------------------------------------------------
class MentorshipTicketSerializer(serializers.ModelSerializer):
    apprentice = UserMiniSerializer(read_only=True)
    mentor = UserMiniSerializer(read_only=True)
    concept_name = serializers.CharField(source="concept.name", read_only=True)
    concept_id = serializers.IntegerField(source="concept.id", read_only=True)

    class Meta:
        model = MentorshipTicket
        fields = ["id", "apprentice", "mentor", "concept_id", "concept_name", "status", "created_at"]


# ---------------------------------------------------------
# REPUTATION POINT SERIALIZER
# ---------------------------------------------------------
class ReputationPointSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer(read_only=True)

    class Meta:
        model = ReputationPoint
        fields = ["id", "user", "points", "reason", "created_at"]
