from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from authapp.models import UserProfile
from social.models import (
    Post,
    Comment,
    Like,
    Follow,
    UserBlock,
    Community,
    CommunityMember,
    Activity,
    ActivityParticipant,
    Report,
    Message,
    Conversation,
)


class SocialPlatformCoreTests(APITestCase):
    def setUp(self):
        # 1. Adult Student User
        self.user_adult = User.objects.create_user(username="adult_dev", email="adult@example.com", password="password123")
        self.profile_adult = self.user_adult.profile
        self.profile_adult.display_name = "Adult Engineer"
        self.profile_adult.education_stage = "college"
        self.profile_adult.institution_name = "IIT Delhi"
        self.profile_adult.location_city = "New Delhi"
        self.profile_adult.interests = ["Robotics", "Open Source", "AI"]
        self.profile_adult.skills = ["Python", "Rust"]
        self.profile_adult.is_minor = False
        self.profile_adult.privacy_settings = {"profile_visibility": "public", "show_learning_progress": False}
        self.profile_adult.save()

        # 2. Minor Student User (Class 9)
        self.user_minor = User.objects.create_user(username="minor_student", email="minor@example.com", password="password123")
        self.profile_minor = self.user_minor.profile
        self.profile_minor.display_name = "Young Explorer"
        self.profile_minor.education_stage = "class_6_10"
        self.profile_minor.institution_name = "Delhi Public School"
        self.profile_minor.location_city = "Jaipur"
        self.profile_minor.interests = ["Astronomy", "Math"]
        self.profile_minor.skills = ["Scratch", "Algebra"]
        self.profile_minor.is_minor = True
        self.profile_minor.privacy_settings = {"profile_visibility": "connections", "show_learning_progress": False, "allow_messages_from": "followers"}
        self.profile_minor.save()

        # 3. Third peer user
        self.user_peer = User.objects.create_user(username="peer_learner", email="peer@example.com", password="password123")
        self.profile_peer = self.user_peer.profile
        self.profile_peer.display_name = "Peer Student"
        self.profile_peer.education_stage = "class_11_12"
        self.profile_peer.save()

    # -------------------------------------------------------------
    # A. PROFILE UPDATES & AGE-AWARE PRIVACY
    # -------------------------------------------------------------
    def test_update_profile_and_education_stage(self):
        self.client.force_authenticate(self.user_adult)
        payload = {
            "display_name": "Senior Fullstack",
            "bio": "Passionate about building collaborative educational spaces.",
            "education_stage": "placement",
            "institution_name": "NIT Trichy",
            "interests": ["Fullstack", "Distributed Systems"],
            "skills": ["Django", "React", "PostgreSQL"],
            "privacy_settings": {
                "profile_visibility": "public",
                "show_learning_progress": False,
                "allow_messages_from": "everyone"
            }
        }
        res = self.client.patch("/auth/profile/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["display_name"], "Senior Fullstack")
        self.assertEqual(res.data["education_stage"], "placement")
        self.assertEqual(res.data["interests"], ["Fullstack", "Distributed Systems"])

    def test_minor_privacy_safeguards_in_profile_view(self):
        # When unauthenticated or non-connection views minor profile, city is omitted for safety
        self.client.force_authenticate(self.user_adult)
        res = self.client.get(f"/api/social/users/{self.user_minor.id}/profile/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Location city MUST be stripped for minors when viewed by others
        self.assertEqual(res.data["location_city"], "")

    # -------------------------------------------------------------
    # B. POST CRUD, TYPES & PERMISSIONS
    # -------------------------------------------------------------
    def test_create_project_and_question_posts(self):
        self.client.force_authenticate(self.user_adult)

        # Create Project Showcase
        res = self.client.post("/api/social/posts/", {
            "title": "Autonomous Mars Rover Simulator",
            "content": "Built a physics-based rover simulation in Python with terrain navigation.",
            "content_type": "project",
            "visibility": "public",
            "tags": ["Python", "Simulation", "Space"],
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["data"]["title"], "Autonomous Mars Rover Simulator")
        self.assertEqual(res.data["data"]["content_type"], "project")
        post_id = res.data["data"]["id"]

        # Edit post by owner
        res_edit = self.client.patch(f"/api/social/posts/{post_id}/", {
            "title": "Autonomous Mars Rover Simulator v2"
        }, format="json")
        self.assertEqual(res_edit.status_code, status.HTTP_200_OK)
        self.assertEqual(res_edit.data["data"]["title"], "Autonomous Mars Rover Simulator v2")

        # Edit by unauthorized user must be rejected
        self.client.force_authenticate(self.user_minor)
        res_unauth = self.client.patch(f"/api/social/posts/{post_id}/", {"title": "Hacked Title"}, format="json")
        self.assertEqual(res_unauth.status_code, status.HTTP_403_FORBIDDEN)

        # Delete by owner
        self.client.force_authenticate(self.user_adult)
        res_del = self.client.delete(f"/api/social/posts/{post_id}/")
        self.assertEqual(res_del.status_code, status.HTTP_200_OK)
        self.assertFalse(Post.objects.filter(id=post_id).exists())

    # -------------------------------------------------------------
    # C. COMMENTS & REPLIES
    # -------------------------------------------------------------
    def test_comments_and_threaded_replies(self):
        self.client.force_authenticate(self.user_adult)
        post = Post.objects.create(user=self.user_adult, title="Help with Thermodynamics", content="How does entropy relate to microscopic states?", content_type="question")

        # Peer comments
        self.client.force_authenticate(self.user_peer)
        res_c = self.client.post(f"/api/social/posts/{post.id}/comments/", {
            "content": "Think about Boltzmann's formula: S = k ln(Omega)."
        }, format="json")
        self.assertEqual(res_c.status_code, status.HTTP_201_CREATED)
        comment_id = res_c.data["data"]["id"]

        # Minor replies to peer's comment
        self.client.force_authenticate(self.user_minor)
        res_reply = self.client.post(f"/api/social/posts/{post.id}/comments/", {
            "content": "Does Omega represent the number of microstates?",
            "parent_id": comment_id,
        }, format="json")
        self.assertEqual(res_reply.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_reply.data["data"]["parent"], comment_id)

    # -------------------------------------------------------------
    # D. SOCIAL RELATIONSHIPS & BLOCKING
    # -------------------------------------------------------------
    def test_follow_and_blocking_enforcement(self):
        self.client.force_authenticate(self.user_adult)
        # Follow peer
        res_f = self.client.post(f"/api/social/users/{self.user_peer.id}/follow/")
        self.assertEqual(res_f.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Follow.objects.filter(follower=self.user_adult, following=self.user_peer).exists())

        # Block peer
        res_b = self.client.post(f"/api/social/users/{self.user_peer.id}/block/")
        self.assertEqual(res_b.status_code, status.HTTP_201_CREATED)
        self.assertTrue(UserBlock.objects.filter(blocker=self.user_adult, blocked=self.user_peer).exists())

        # Follow relationship must be automatically severed
        self.assertFalse(Follow.objects.filter(follower=self.user_adult, following=self.user_peer).exists())

        # Peer's posts must now be hidden from adult's feed
        peer_post = Post.objects.create(user=self.user_peer, title="Blocked post", content="Should not see this")
        feed_res = self.client.get("/api/social/posts/")
        post_ids = [p["id"] for p in feed_res.data["posts"]]
        self.assertNotIn(peer_post.id, post_ids)

        # Unblock peer
        res_ub = self.client.delete(f"/api/social/users/{self.user_peer.id}/block/")
        self.assertEqual(res_ub.status_code, status.HTTP_200_OK)
        self.assertFalse(UserBlock.objects.filter(blocker=self.user_adult, blocked=self.user_peer).exists())

    # -------------------------------------------------------------
    # E. COMMUNITIES (CIRCLES)
    # -------------------------------------------------------------
    def test_community_lifecycle_and_membership(self):
        self.client.force_authenticate(self.user_adult)

        # Create Community
        res_create = self.client.post("/api/social/communities/", {
            "name": "Robotics & Hardware Guild",
            "description": "Collaborative circle for building robotics, IoT and embedded systems projects.",
            "category": "Robotics & Hardware",
            "visibility": "public",
            "rules": "Be constructive, share open source schematics."
        }, format="json")
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)
        comm_id = res_create.data["community"]["id"]

        # Creator is automatically admin member
        self.assertTrue(CommunityMember.objects.filter(community_id=comm_id, user=self.user_adult, role="admin").exists())

        # Peer joins community
        self.client.force_authenticate(self.user_peer)
        res_join = self.client.post(f"/api/social/communities/{comm_id}/membership/")
        self.assertEqual(res_join.status_code, status.HTTP_201_CREATED)
        self.assertTrue(CommunityMember.objects.filter(community_id=comm_id, user=self.user_peer).exists())

        # Peer posts to community
        res_post = self.client.post("/api/social/posts/", {
            "title": "ESP32 Sensor Node Build",
            "content": "Shared telemetry code for solar-powered ESP32.",
            "content_type": "project",
            "community": comm_id,
        }, format="json")
        self.assertEqual(res_post.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_post.data["data"]["community"]["id"], comm_id)

    # -------------------------------------------------------------
    # F. ACTIVITIES & CHALLENGES
    # -------------------------------------------------------------
    def test_activity_challenge_participation(self):
        self.client.force_authenticate(self.user_adult)

        # Create challenge
        activity = Activity.objects.create(
            title="Clean Energy Innovation Sprint",
            slug="clean-energy-innovation-sprint",
            description="Design an innovative solar or wind concept for student campuses.",
            category="Project Sprint",
            creator=self.user_adult,
            status="active"
        )

        # Minor student registers and submits
        self.client.force_authenticate(self.user_minor)
        res_reg = self.client.post(f"/api/social/activities/{activity.id}/participate/", {"action": "register"}, format="json")
        self.assertEqual(res_reg.status_code, status.HTTP_200_OK)

        res_sub = self.client.post(f"/api/social/activities/{activity.id}/participate/", {
            "action": "submit",
            "submission_title": "Mini Solar Tracker",
            "submission_content": "Uses LDR sensors and Arduino to rotate mini solar panels toward sunlight.",
            "submission_link": "https://github.com/example/solar-tracker"
        }, format="json")
        self.assertEqual(res_sub.status_code, status.HTTP_200_OK)
        self.assertEqual(res_sub.data["participant"]["status"], "submitted")

    # -------------------------------------------------------------
    # G. UNIFIED DISCOVERY & SEARCH
    # -------------------------------------------------------------
    def test_unified_discovery_endpoint(self):
        self.client.force_authenticate(self.user_adult)

        # Seed discovery content
        Post.objects.create(user=self.user_adult, title="Open Source Physics Engine", content="Showcase", content_type="project")
        Post.objects.create(user=self.user_peer, title="How do transistors work?", content="Question", content_type="question")

        res_disc = self.client.get("/api/social/discover/")
        self.assertEqual(res_disc.status_code, status.HTTP_200_OK)
        self.assertIn("projects", res_disc.data)
        self.assertIn("questions", res_disc.data)
        self.assertIn("people", res_disc.data)
        self.assertIn("communities", res_disc.data)
        self.assertIn("activities", res_disc.data)

        # Search endpoint
        res_search = self.client.get("/api/social/search/?q=Physics")
        self.assertEqual(res_search.status_code, status.HTTP_200_OK)
        self.assertIn("posts", res_search.data)
        self.assertIn("people", res_search.data)

    # -------------------------------------------------------------
    # H. CONTENT REPORTING & ABUSE PREVENTION
    # -------------------------------------------------------------
    def test_report_abusive_content(self):
        self.client.force_authenticate(self.user_adult)
        abusive_post = Post.objects.create(user=self.user_peer, title="Spam Link", content="Click here for free coins")

        res_rep = self.client.post("/api/social/reports/", {
            "target_type": "post",
            "target_id": abusive_post.id,
            "reason": "Spam or scam links",
            "details": "User is posting automated spam."
        }, format="json")
        self.assertEqual(res_rep.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Report.objects.filter(target_id=abusive_post.id).exists())
