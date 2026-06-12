from rest_framework import serializers
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from .models import Post, Comment,  Follow, Notification, Message


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

    class Meta:
        model = UserProfile
        fields = [
            "user",
            "bio",
            "avatar",
        ]

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

    media = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "user",
            "post_type",
            "content",
            "media",
            "concept_id",
            "concept_name",
            "created_at",
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


from rest_framework import serializers
from .models import Post
from syllabus.models import Concept

class PostCreateSerializer(serializers.ModelSerializer):
    concept = serializers.PrimaryKeyRelatedField(
        queryset=Concept.objects.all(),
        required=False,
        allow_null=True
    )

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
        fields = ["content", "concept", "images", "videos", "documents"]

    def create(self, validated_data):
        user = self.context["request"].user
        media_list = []

        images = validated_data.pop("images", [])
        videos = validated_data.pop("videos", [])
        documents = validated_data.pop("documents", [])

        # Store images in media/posts/
        for img in images:
            path = f"posts/{img.name}"  # Folder inside MEDIA_ROOT
            saved_path = default_storage.save(path, img)  # Actually saves file
            media_list.append({"type": "image", "url": f"/media/{saved_path}"})

        # Videos are URLs
        for url in videos:
            media_list.append({"type": "video", "url": url})

        # Documents in media/posts/
        for doc in documents:
            path = f"posts/{doc.name}"
            saved_path = default_storage.save(path, doc)
            media_list.append({"type": "doc", "url": f"/media/{saved_path}"})

        # Determine post_type automatically
        if not media_list:
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
