from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from syllabus.models import Exam, Subject, Topic, Subtopic, Concept
from quiz.models import Question, QuizSession, QuizAnswer
from social.models import Post, Comment, Like, Follow, Notification, Message

class FullAppAPIIntegrationTestCase(APITestCase):
    def setUp(self):
        # 1. Create dummy syllabus tree data
        self.exam = Exam.objects.create(
            name="JEE Main Test",
            description="Test JEE Main exam syllabus"
        )
        self.subject = Subject.objects.create(
            exam=self.exam,
            name="Mathematics",
            order=0
        )
        self.topic = Topic.objects.create(
            subject=self.subject,
            name="Algebra",
            order=0
        )
        self.subtopic = Subtopic.objects.create(
            topic=self.topic,
            name="Sets, Relations and Functions",
            order=0
        )
        self.concept = Concept.objects.create(
            subtopic=self.subtopic,
            name="Sets and their representation",
            description="Formal definition of a set, roster/builder representations",
            order=0
        )

        # 2. Create a primary test user
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="password123"
        )
        self.user.profile.selected_exam = self.exam
        self.user.profile.save()
        
        # 3. Create another test user for social testing
        self.other_user = User.objects.create_user(
            username="otheruser",
            email="otheruser@example.com",
            password="password123"
        )
        self.other_user.profile.selected_exam = self.exam
        self.other_user.profile.save()

        # 4. Create dummy questions for the concept
        self.question1 = Question.objects.create(
            qid="Q-SETS-001",
            header="Set Cardinality",
            question_title="Cardinality of power set",
            concept=self.concept,
            question="If a set A has 3 elements, what is the cardinality of its power set P(A)?",
            option_a="3",
            option_b="6",
            option_c="8",
            option_d="9",
            correct_option="C",
            source="PYQS"
        )

        self.question2 = Question.objects.create(
            qid="Q-SETS-002",
            header="Empty Set",
            question_title="Cardinality of empty set",
            concept=self.concept,
            question="What is the number of elements in the empty set?",
            option_a="0",
            option_b="1",
            option_c="2",
            option_d="None of the above",
            correct_option="A",
            source="PYQS"
        )

    def get_auth_headers(self, user):
        response = self.client.post("/auth/login/", {
            "username": user.username,
            "password": "password123"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        access_token = response.data["tokens"]["access"]
        return {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}

    def test_authentication_endpoints(self):
        # Test Registration
        response = self.client.post("/auth/register/", {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "password123",
            "exam_type": self.exam.exam_type
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("user", response.data)
        self.assertIn("tokens", response.data)

        # Test Login
        response = self.client.post("/auth/login/", {
            "username": "testuser",
            "password": "password123"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("tokens", response.data)
        access_token = response.data["tokens"]["access"]
        refresh_token = response.data["tokens"]["refresh"]

        # Test Profile
        headers = {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}
        response = self.client.get("/auth/profile/", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "testuser")

        # Test Token Refresh
        response = self.client.post("/auth/refresh/", {
            "refresh": refresh_token
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

        # Test Logout
        response = self.client.post("/auth/logout/", {
            "refresh": refresh_token
        }, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Logged out successfully", response.data["message"])

    def test_syllabus_endpoints(self):
        headers = self.get_auth_headers(self.user)

        # Test Syllabus Tree API
        response = self.client.get("/api/syllabus/tree/", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("exams", response.data)
        self.assertEqual(len(response.data["exams"]), 1)
        self.assertEqual(response.data["exams"][0]["name"], "JEE Main Test")

        # Test Concept List API
        response = self.client.get("/api/syllabus/conceptlist/", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Sets and their representation")

    def test_quiz_and_progress_endpoints(self):
        headers = self.get_auth_headers(self.user)

        # 1. Start Quiz API (PYQS mode)
        response = self.client.post("/api/quiz/start/", {
            "concept_id": self.concept.id,
            "num_questions": 2,
            "quiz_type": "PYQS"
        }, format="json", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("session_id", response.data)
        self.assertEqual(response.data["total_questions"], 2)
        session_id = response.data["session_id"]

        # 2. Submit Quiz API
        response = self.client.post("/api/quiz/submit/", {
            "session_id": session_id,
            "duration_seconds": 150,
            "answers": [
                {"question_id": self.question1.qid, "marked_option": "C"},  # Correct
                {"question_id": self.question2.qid, "marked_option": "B"}   # Incorrect
            ]
        }, format="json", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("score", response.data)
        self.assertEqual(response.data["score"], 0.5)

        # 3. Concept Progress API
        response = self.client.get(f"/api/progress/concept/{self.concept.id}/", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("concept", response.data)

        # 4. Concept History API
        response = self.client.get(f"/api/progress/concept/{self.concept.id}/history/", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["summary"]["total_attempts"], 1)

        # 5. Subtopic Progress API
        response = self.client.get(f"/api/progress/subtopic/{self.subtopic.id}/", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("subtopic", response.data)

    def test_social_endpoints(self):
        headers = self.get_auth_headers(self.user)
        other_headers = self.get_auth_headers(self.other_user)

        # 1. Create a Post
        response = self.client.post("/api/social/posts/", {
            "content": "Exploring sets relations and functions today!",
            "concept": self.concept.id
        }, format="json", **headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("data", response.data)
        post_id = response.data["data"]["id"]

        # 2. List posts
        response = self.client.get("/api/social/posts/", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["posts"]), 1)

        # 3. Like a post (from other_user)
        response = self.client.post(f"/api/social/posts/{post_id}/like/", **other_headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 4. Unlike a post (from other_user)
        response = self.client.delete(f"/api/social/posts/{post_id}/like/", **other_headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 5. Add Comment (from other_user)
        response = self.client.post(f"/api/social/posts/{post_id}/comments/", {
            "content": "Nice progress!"
        }, format="json", **other_headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 6. List comments
        response = self.client.get(f"/api/social/posts/{post_id}/comments/list/", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["comments"]), 1)
        self.assertEqual(response.data["comments"][0]["content"], "Nice progress!")

        # 7. Follow user
        response = self.client.post(f"/api/social/users/{self.other_user.id}/follow/", **headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["following"])

        # 8. List followers and following
        response = self.client.get(f"/api/social/users/{self.other_user.id}/followers/", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["followers"]), 1)
        self.assertEqual(response.data["followers"][0]["username"], "testuser")

        response = self.client.get(f"/api/social/users/{self.user.id}/following/", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["following"]), 1)
        self.assertEqual(response.data["following"][0]["username"], "otheruser")

        # 9. Send a direct message
        response = self.client.post(f"/api/social/messages/{self.other_user.id}/send/", {
            "text": "Hi otheruser, how's your prep going?"
        }, format="json", **headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 10. Get conversation messages
        response = self.client.get(f"/api/social/messages/{self.other_user.id}/", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["messages"]), 1)
        self.assertEqual(response.data["messages"][0]["text"], "Hi otheruser, how's your prep going?")

        # 11. Inbox API
        response = self.client.get("/api/social/messages/inbox/", **other_headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["inbox"]), 1)

        # 12. User Profile API
        response = self.client.get(f"/api/social/users/{self.user.id}/profile/", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["username"], "testuser")

        # 13. Suggested Users API
        response = self.client.get("/api/social/users/suggested/", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["suggestions"]), 0)  # already following other_user

        # 14. Notifications list
        response = self.client.get("/api/social/notifications/", **other_headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data["notifications"]), 0)
        noti_id = response.data["notifications"][0]["id"]

        # 15. Mark notification as read
        response = self.client.post("/api/social/notifications/read/", {
            "notification_id": noti_id
        }, format="json", **other_headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
