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
    SOURCE_CHOICES = (
        ("concept", "Concept Page"),
        ("quiz", "Quiz Result"),
        ("world", "World Page"),
    )

    CONTENT_TYPES = (
        ("learning", "Learning Insight"),
        ("strategy", "Quiz Strategy"),
        ("general", "General Reflection"),
        ("project", "Project Showcase"),
        ("question", "Question / Help"),
        ("discovery", "Discovery"),
        ("opportunity", "Opportunity"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="world", db_index=True)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES, default="general", db_index=True)
    post_type = models.CharField(max_length=20, default="text", db_index=True)
    content = models.TextField(blank=True)
    media = models.JSONField(default=list, blank=True)  # [{"type": "image/video/doc", "url": "..."}]
    concept = models.ForeignKey(Concept, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts", db_index=True)
    grade_level = models.IntegerField(null=True, blank=True, db_index=True)
    relevance_score = models.IntegerField(default=0, db_index=True)
    domain_tag = models.CharField(max_length=50, blank=True, default="", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    post_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["source", "created_at"]),
            models.Index(fields=["content_type", "created_at"]),
            models.Index(fields=["domain_tag", "created_at"]),
        ]

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
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
    )
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name="following")
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name="followers")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="accepted", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("follower", "following")

    def __str__(self):
        return f"{self.follower.username} → {self.following.username} ({self.status})"


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


# ==========================================================
# ACTIVE SESSION (Cost-efficient Presence status)
# ==========================================================
class ActiveSession(models.Model):
    STATUS_CHOICES = (
        ("reading", "Reading notes"),
        ("quiz", "Solving Quiz"),
        ("revision", "Revising concept"),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="active_session")
    concept = models.ForeignKey(Concept, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES)
    last_action_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}: {self.status}"


# ==========================================================
# MENTORSHIP TICKET (Help Queue)
# ==========================================================
class MentorshipTicket(models.Model):
    STATUS_CHOICES = (
        ("open", "Open"),
        ("active", "Active Match"),
        ("resolved", "Resolved"),
    )
    apprentice = models.ForeignKey(User, on_delete=models.CASCADE, related_name="apprentice_tickets")
    mentor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="mentor_tickets")
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="open")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ticket {self.id}: {self.concept.name} ({self.status})"


# ==========================================================
# REPUTATION POINT (Tutor status ledger)
# ==========================================================
class ReputationPoint(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reputation")
    points = models.IntegerField()
    reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}: +{self.points} pts ({self.reason})"
