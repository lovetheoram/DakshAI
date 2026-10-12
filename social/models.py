from django.db import models
from django.contrib.auth.models import User
from syllabus.models import Concept

# ==========================================================
# USER BLOCK (Safety & Moderation)
# ==========================================================
class UserBlock(models.Model):
    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blocked_users")
    blocked = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blocked_by_users")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["blocker", "blocked"], name="unique_user_block")
        ]

    def __str__(self):
        return f"{self.blocker.username} blocked {self.blocked.username}"


# ==========================================================
# COMMUNITY (Circles / Guilds / Interest Spaces)
# ==========================================================
class Community(models.Model):
    VISIBILITY_CHOICES = (
        ("public", "Public"),
        ("restricted", "Restricted / Invite-only"),
    )

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True, default="")
    category = models.CharField(max_length=50, default="General", db_index=True)
    avatar = models.URLField(blank=True, default="")
    banner = models.URLField(blank=True, default="")
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_communities")
    is_verified = models.BooleanField(default=False)
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default="public")
    rules = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class CommunityMember(models.Model):
    ROLE_CHOICES = (
        ("admin", "Admin"),
        ("moderator", "Moderator"),
        ("member", "Member"),
    )

    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="community_memberships")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="member")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["community", "user"], name="unique_community_member")
        ]

    def __str__(self):
        return f"{self.user.username} in {self.community.name} ({self.role})"


# ==========================================================
# ACTIVITY & CHALLENGES (Project Sprints, Hackathons, Quests)
# ==========================================================
class Activity(models.Model):
    STATUS_CHOICES = (
        ("upcoming", "Upcoming"),
        ("active", "Active"),
        ("completed", "Completed"),
    )

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField()
    category = models.CharField(max_length=50, default="Challenge", db_index=True)
    banner = models.URLField(blank=True, default="")
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_activities")
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active", db_index=True)
    education_stage_filter = models.CharField(max_length=50, blank=True, default="all")
    rules = models.TextField(blank=True, default="")
    outcomes_summary = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class ActivityParticipant(models.Model):
    STATUS_CHOICES = (
        ("registered", "Registered"),
        ("submitted", "Submitted"),
        ("completed", "Completed"),
        ("awarded", "Awarded"),
    )

    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="activity_participations")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="registered")
    submission_title = models.CharField(max_length=200, blank=True, default="")
    submission_content = models.TextField(blank=True, default="")
    submission_link = models.URLField(blank=True, default="")
    submitted_at = models.DateTimeField(null=True, blank=True)
    feedback = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["activity", "user"], name="unique_activity_participant")
        ]

    def __str__(self):
        return f"{self.user.username} in {self.activity.title} ({self.status})"


# ==========================================================
# POST
# ==========================================================
class Post(models.Model):
    SOURCE_CHOICES = (
        ("concept", "Concept Page"),
        ("quiz", "Quiz Result"),
        ("world", "World Page"),
        ("community", "Community"),
        ("activity", "Activity"),
    )

    CONTENT_TYPES = (
        ("learning", "Learning Insight"),
        ("strategy", "Quiz Strategy"),
        ("general", "General Reflection"),
        ("project", "Project Showcase"),
        ("question", "Question / Help"),
        ("discovery", "Discovery"),
        ("opportunity", "Opportunity"),
        ("milestone", "Milestone / Achievement"),
    )

    MODERATION_CHOICES = (
        ("approved", "Approved"),
        ("flagged", "Flagged"),
        ("hidden", "Hidden"),
    )

    VISIBILITY_CHOICES = (
        ("public", "Public"),
        ("connections", "Connections Only"),
        ("community", "Community Members"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    title = models.CharField(max_length=255, blank=True, default="")
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="world", db_index=True)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES, default="general", db_index=True)
    post_type = models.CharField(max_length=20, default="text", db_index=True)
    content = models.TextField(blank=True)
    media = models.JSONField(default=list, blank=True)  # [{"type": "image/video/doc", "url": "..."}]
    concept = models.ForeignKey(Concept, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts", db_index=True)
    community = models.ForeignKey(Community, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts", db_index=True)
    activity = models.ForeignKey(Activity, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts", db_index=True)
    grade_level = models.IntegerField(null=True, blank=True, db_index=True)
    relevance_score = models.IntegerField(default=0, db_index=True)
    domain_tag = models.CharField(max_length=50, blank=True, default="", db_index=True)
    tags = models.JSONField(default=list, blank=True)
    moderation_status = models.CharField(max_length=20, choices=MODERATION_CHOICES, default="approved", db_index=True)
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default="public", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    post_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["source", "created_at"]),
            models.Index(fields=["content_type", "created_at"]),
            models.Index(fields=["domain_tag", "created_at"]),
            models.Index(fields=["moderation_status", "created_at"]),
            models.Index(fields=["visibility", "created_at"]),
        ]

    def __str__(self):
        return f"Post #{self.id} by {self.user.username} ({self.content_type})"


# ==========================================================
# COMMENT
# ==========================================================
class Comment(models.Model):
    MODERATION_CHOICES = (
        ("approved", "Approved"),
        ("flagged", "Flagged"),
        ("hidden", "Hidden"),
    )

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    moderation_status = models.CharField(max_length=20, choices=MODERATION_CHOICES, default="approved", db_index=True)
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
        constraints = [
            models.UniqueConstraint(fields=["post", "user"], name="unique_post_like")
        ]

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
        constraints = [
            models.UniqueConstraint(fields=["follower", "following"], name="unique_user_follow")
        ]

    def __str__(self):
        return f"{self.follower.username} → {self.following.username}"


# ==========================================================
# NOTIFICATIONS
# ==========================================================
class Notification(models.Model):
    NOTI_TYPES = (
        ("like", "Like"),
        ("comment", "Comment"),
        ("reply", "Reply"),
        ("follow", "Follow"),
        ("post", "Post"),
        ("mention", "Mention"),
        ("community", "Community"),
        ("activity", "Activity"),
        ("moderation", "Moderation"),
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
# CONVERSATIONS & MESSAGES
# ==========================================================
class Conversation(models.Model):
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conversations_1")
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conversations_2")
    last_message = models.ForeignKey("Message", on_delete=models.SET_NULL, null=True, blank=True, related_name="last_message_conversations")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user1", "user2"], name="unique_conversation_pair")
        ]

    def __str__(self):
        return f"Chat between {self.user1.username} & {self.user2.username}"


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
        ("project", "Working on Project"),
        ("community", "Exploring Community"),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="active_session")
    concept = models.ForeignKey(Concept, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
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
# REPUTATION POINT (Peer & Tutor status ledger)
# ==========================================================
class ReputationPoint(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reputation")
    points = models.IntegerField()
    reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}: +{self.points} pts ({self.reason})"


# ==========================================================
# REPORT & CONTENT MODERATION
# ==========================================================
class Report(models.Model):
    TARGET_TYPE_CHOICES = (
        ("post", "Post"),
        ("comment", "Comment"),
        ("user", "User Profile"),
        ("community", "Community"),
    )

    STATUS_CHOICES = (
        ("pending", "Pending Review"),
        ("reviewed", "Reviewed"),
        ("resolved", "Resolved"),
        ("dismissed", "Dismissed"),
    )

    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="submitted_reports")
    target_type = models.CharField(max_length=20, choices=TARGET_TYPE_CHOICES)
    target_id = models.IntegerField(db_index=True)
    reason = models.CharField(max_length=100)
    details = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True)
    action_taken = models.CharField(max_length=100, blank=True, default="")
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="moderated_reports")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Report #{self.id} on {self.target_type}:{self.target_id} by {self.reporter.username}"
