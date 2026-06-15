from rest_framework.test import APITestCase
from django.test import override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken
from syllabus.models import Exam, Subject, Topic, Subtopic, Concept
from progress.models import UserGoal, DailyTarget, DailyDiaryEntry, ConceptProgress
from progress.services import ProgressService
from quiz.models import QuizSession, Question, QuizAnswer

User = get_user_model()

@override_settings(CACHES={
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
})
class GrowthOSTests(APITestCase):

    def setUp(self):
        # Create user
        self.user = User.objects.create_user(username="growth_user", password="password123")
        self.token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        # Create syllabus models
        self.exam = Exam.objects.create(name="Core placement exam", exam_type="placement", description="Exam description")
        self.subject = Subject.objects.create(exam=self.exam, name="Operating Systems")
        self.topic = Topic.objects.create(subject=self.subject, name="Process Management")
        self.subtopic = Subtopic.objects.create(topic=self.topic, name="CPU Scheduling")
        
        # Create 10 concepts for the exam
        self.concepts = []
        for i in range(10):
            concept = Concept.objects.create(
                subtopic=self.subtopic,
                name=f"Concept {i}",
                description=f"Concept {i} description"
            )
            self.concepts.append(concept)

    def test_admte_target_generation(self):
        # Setup goal: Target date is in 10 days, target growth is 100%
        today = timezone.localdate()
        target_date = today + timezone.timedelta(days=10)
        
        goal = UserGoal.objects.create(
            user=self.user,
            exam=self.exam,
            goal_name="Become Ready",
            target_date=target_date,
            available_hours_per_day=3.0
        )

        # Initially, 0 concepts completed.
        # ADMTE calculates: remaining growth = 100%. remaining days = 10.
        # target_growth = remaining_growth / remaining_days = 100 / 10 = 10.0% growth.
        target = ProgressService.generate_daily_target_for_today(self.user, date=today)
        self.assertEqual(target.target_growth, 10.0)
        self.assertEqual(target.completed_growth, 0.0)

        # Now, simulate a concept is mastered (exam_readiness = 0.8)
        # 1 concept out of 10 mastered -> 10% Daksh Score!
        ConceptProgress.objects.create(
            user=self.user,
            concept=self.concepts[0],
            exam_readiness=0.8,
            chapter_understanding=0.8,
            last_practiced=timezone.now()
        )

        # Re-fetch today's target after deleting (to simulate new generation)
        DailyTarget.objects.filter(user=self.user, date=today).delete()
        target2 = ProgressService.generate_daily_target_for_today(self.user, date=today)

        # Remaining growth: 100 - (0.8 / 10 * 100) = 100 - 8 = 92%
        # Remaining days = 10
        # Required growth = 92 / 10 = 9.2%
        self.assertEqual(target2.target_growth, 9.2)

    def test_quiz_session_updates_diary_and_growth(self):
        today = timezone.localdate()
        target_date = today + timezone.timedelta(days=10)
        
        # Setup Goal
        UserGoal.objects.create(
            user=self.user,
            exam=self.exam,
            goal_name="Crack Google",
            target_date=target_date
        )

        # Mock a QuizSession
        question = Question.objects.create(
            qid="q1",
            concept=self.concepts[0],
            header="Header",
            question_title="Title",
            question="Sample OS Question",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_option="A"
        )
        
        session = QuizSession.objects.create(
            user=self.user,
            score=1.0,
            total_questions=1,
            duration_seconds=120,
            completed_at=timezone.now()
        )
        session.questions.add(question)

        # Create QuizAnswer
        QuizAnswer.objects.create(
            session=session,
            question=question,
            is_correct=True,
            marked_option="A"
        )

        # Update progress with session
        cp = ProgressService.update_progress_with_session(self.user, session)
        
        # Verify diary entry is updated
        diary = DailyDiaryEntry.objects.get(user=self.user, date=today)
        self.assertEqual(diary.questions_solved, 1)
        self.assertEqual(diary.questions_correct, 1)
        self.assertEqual(diary.time_spent_seconds, 120)
        self.assertIn(self.concepts[0].id, diary.concepts_attempted)
        self.assertEqual(diary.knowledge_gain.get("Operating Systems"), 1)

        # Verify today's target completed_growth is updated
        target = DailyTarget.objects.get(user=self.user, date=today)
        
        # Old readiness was 0. New readiness is computed by:
        # cp.exam_readiness = round(0 * (1 - 0.35) + 1.0 * 0.35, 4) = 0.35
        # Growth increment = (0.35 / 10) * 100 = 3.5%
        self.assertEqual(target.completed_growth, 3.5)
        self.assertEqual(diary.daily_growth_percentage, 3.5)

    def test_streak_compliance_calculation(self):
        today = timezone.localdate()
        
        # Set up a fake DailyTarget for today, yesterday, and day before
        t_today = DailyTarget.objects.create(user=self.user, date=today, target_growth=1.0, completed_growth=0.9) # 90% compliance
        t_yesterday = DailyTarget.objects.create(user=self.user, date=today - timezone.timedelta(days=1), target_growth=1.0, completed_growth=0.8) # 80% compliance
        t_day_before = DailyTarget.objects.create(user=self.user, date=today - timezone.timedelta(days=2), target_growth=1.0, completed_growth=0.5) # 50% compliance

        # StreakStats API call
        url = reverse("streak-stats")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        data = response.data
        self.assertEqual(data["today_compliance"], 90.0)
        # growth_streak should be 2, because today and yesterday compliance are >= 80%, but day_before is 50%
        self.assertEqual(data["growth_streak"], 2)

    def test_caching_and_invalidation(self):
        from django.core.cache import cache
        cache.clear()
        
        today = timezone.localdate()
        # Set up a fake DailyTarget for today
        DailyTarget.objects.create(user=self.user, date=today, target_growth=1.0, completed_growth=0.9)
        
        url_stats = reverse("streak-stats")
        url_dash = reverse("dashboard")
        
        # 1. Fetch first time (cache miss, should populate cache)
        response1 = self.client.get(url_stats)
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response1.data["today_compliance"], 90.0)
        
        # Verify cached value exists
        cache_key = f"streak_stats_user_{self.user.id}"
        self.assertIsNotNone(cache.get(cache_key))
        
        # Modify the target directly in DB (without calling endpoints)
        DailyTarget.objects.filter(user=self.user, date=today).update(completed_growth=0.95)
        
        # 2. Fetch second time (should hit cache and return old value, 90.0)
        response2 = self.client.get(url_stats)
        self.assertEqual(response2.data["today_compliance"], 90.0)
        
        # 3. Call a modifying endpoint, e.g., logging revision, which should invalidate cache
        url_revision = reverse("daily-target-revision")
        response_rev = self.client.get(url_dash) # access dashboard to cache it too
        self.assertEqual(response_rev.status_code, 200)
        
        self.assertIsNotNone(cache.get(f"dashboard_data_user_{self.user.id}"))
        
        # Post revision time (logs 10 mins)
        response_post = self.client.post(url_revision, {"minutes": 10})
        self.assertEqual(response_post.status_code, 200)
        
        # Cache should now be invalidated/None
        self.assertIsNone(cache.get(cache_key))
        self.assertIsNone(cache.get(f"dashboard_data_user_{self.user.id}"))
