from django.db import models
from django.contrib.auth.models import User
from syllabus.models import Concept

# ==========================================================
# POST
# ==========================================================


from django.db import models
from django.contrib.auth.models import User
from syllabus.models import Concept

class Post(models.Model):
    POST_TYPES = (
        ("text", "Text"),
        ("image", "Image"),
        ("video", "Video"),
        ("doc", "Document"),
        ("mixed", "Mixed"),
        ("progress", "Progress Update"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    post_type = models.CharField(max_length=10, choices=POST_TYPES, default="text", db_index=True)
    content = models.TextField(blank=True)
    media = models.JSONField(default=list, blank=True)  # [{"type": "image/video/doc", "url": "..."}]
    concept = models.ForeignKey(Concept, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    post_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

# ==========================================================
# COMMENT
# ==========================================================
class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"{self.user.username}: {self.content[:20]}"


# ==========================================================
# LIKE
# ==========================================================
class Like(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("post", "user")

    def __str__(self):
        return f"{self.user.username} liked {self.post.id}"


# ==========================================================
# FOLLOW
# ==========================================================
class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name="following")
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name="followers")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("follower", "following")

    def __str__(self):
        return f"{self.follower.username} → {self.following.username}"


# ==========================================================
# NOTIFICATIONS
# ==========================================================
class Notification(models.Model):
    NOTI_TYPES = (
        ("like", "Like"),
        ("comment", "Comment"),
        ("follow", "Follow"),
        ("post", "Post"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    triggered_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="triggered_notifications"
    )

    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, null=True, blank=True
    )

    type = models.CharField(max_length=20, choices=NOTI_TYPES)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"{self.type} → {self.user.username}"



# ==========================================================
# CONVERSATIONS
# ==========================================================
class Conversation(models.Model):
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conversations_1")
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conversations_2")
    last_message = models.ForeignKey("Message", on_delete=models.SET_NULL, null=True, blank=True, related_name="last_message_conversations")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user1", "user2")

    def __str__(self):
        return f"Chat between {self.user1.username} & {self.user2.username}"


# ==========================================================
# MESSAGES
# ==========================================================
class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_messages")
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender.username} → {self.receiver.username}"
