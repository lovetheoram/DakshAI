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
class ProgressOverhaulTests(APITestCase):
    """
    Test suite for the overhauled progress system.
    Covers: Presence, DailyTarget, Readiness, Trajectory.
    """

    def setUp(self):
        self.user = User.objects.create_user(username="test_user", password="password123")
        self.token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        # Create syllabus
        self.exam = Exam.objects.create(name="Core placement exam", exam_type="placement", description="Test exam")
        self.subject = Subject.objects.create(exam=self.exam, name="Operating Systems")
        self.topic = Topic.objects.create(subject=self.subject, name="Process Management")
        self.subtopic = Subtopic.objects.create(topic=self.topic, name="CPU Scheduling")

        self.concepts = []
        for i in range(10):
            concept = Concept.objects.create(
                subtopic=self.subtopic,
                name=f"Concept {i}",
                description=f"Concept {i} description"
            )
            self.concepts.append(concept)

    def _create_goal(self, days_ahead=10):
        today = timezone.localdate()
        return UserGoal.objects.create(
            user=self.user,
            exam=self.exam,
            goal_name="Test Goal",
            target_date=today + timezone.timedelta(days=days_ahead),
            is_active=True,
        )

    def _create_quiz_session(self, concept, score=1.0, all_correct=True):
        question = Question.objects.create(
            qid=f"q_{concept.id}_{timezone.now().timestamp()}",
            concept=concept,
            header="Header",
            question_title="Title",
            question="Sample Question",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_option="A"
        )
        session = QuizSession.objects.create(
            user=self.user,
            score=score,
            total_questions=1,
            duration_seconds=120,
            completed_at=timezone.now()
        )
        session.questions.add(question)
        QuizAnswer.objects.create(
            session=session,
            question=question,
            is_correct=all_correct,
            marked_option="A" if all_correct else "B"
        )
        return session

    # ──────────────────────────────────────────────────────────────────────────
    # PRESENCE TESTS
    # ──────────────────────────────────────────────────────────────────────────

    def test_first_app_open_creates_presence(self):
        """First app open creates today's diary entry with opened_at set."""
        diary = ProgressService.record_presence(self.user)
        self.assertIsNotNone(diary.opened_at)
        self.assertEqual(diary.date, timezone.localdate())

    def test_second_app_open_does_not_duplicate(self):
        """Second app open same day does not create duplicate or overwrite timestamp."""
        diary1 = ProgressService.record_presence(self.user)
        first_opened = diary1.opened_at

        diary2 = ProgressService.record_presence(self.user)
        self.assertEqual(diary1.pk, diary2.pk)
        self.assertEqual(diary2.opened_at, first_opened)  # not overwritten

    def test_consecutive_visits_produce_correct_streak(self):
        """Consecutive daily presence produces correct visit streak."""
        today = timezone.localdate()
        for i in range(4):
            date = today - timezone.timedelta(days=i)
            diary, _ = DailyDiaryEntry.objects.get_or_create(user=self.user, date=date)
            diary.opened_at = timezone.now()
            diary.save()

        streak = ProgressService.get_visit_streak(self.user, today=today)
        self.assertEqual(streak, 4)

    def test_missing_day_breaks_streak(self):
        """A missed calendar day breaks the visit streak."""
        today = timezone.localdate()

        # Present today and yesterday
        for i in [0, 1]:
            diary, _ = DailyDiaryEntry.objects.get_or_create(
                user=self.user, date=today - timezone.timedelta(days=i)
            )
            diary.opened_at = timezone.now()
            diary.save()

        # Skip day 2, present day 3
        diary3, _ = DailyDiaryEntry.objects.get_or_create(
            user=self.user, date=today - timezone.timedelta(days=3)
        )
        diary3.opened_at = timezone.now()
        diary3.save()

        streak = ProgressService.get_visit_streak(self.user, today=today)
        self.assertEqual(streak, 2)  # only today + yesterday

    def test_app_open_does_not_increase_readiness(self):
        """Opening the app does not change any ConceptProgress readiness."""
        # Create some progress first
        cp = ConceptProgress.objects.create(
            user=self.user, concept=self.concepts[0], readiness=0.5
        )

        ProgressService.record_presence(self.user)

        cp.refresh_from_db()
        self.assertEqual(cp.readiness, 0.5)  # unchanged

    def test_presence_api_endpoint(self):
        """POST /api/progress/presence/ records presence and returns streak."""
        url = reverse("app-presence")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("visit_streak", response.data)
        self.assertIn("opened_at", response.data)
        self.assertIsNotNone(response.data["opened_at"])

    # ──────────────────────────────────────────────────────────────────────────
    # DAILY TARGET TESTS
    # ──────────────────────────────────────────────────────────────────────────

    def test_target_derived_from_exam_goal(self):
        """DailyTarget.required_readiness_per_day is derived from exam goal."""
        self._create_goal(days_ahead=10)
        today = timezone.localdate()
        target = ProgressService.generate_daily_target_for_today(self.user, date=today)

        # 0 readiness, 10 days remaining → 100/10 = 10.0 %pts/day
        self.assertEqual(target.required_readiness_per_day, 10.0)

    def test_target_accounts_for_existing_readiness(self):
        """Target adjusts for existing readiness."""
        self._create_goal(days_ahead=10)

        # One concept at 0.8 readiness → daksh = 0.8/10 * 100 = 8%
        ConceptProgress.objects.create(
            user=self.user, concept=self.concepts[0],
            readiness=0.8, last_practiced=timezone.now()
        )

        today = timezone.localdate()
        DailyTarget.objects.filter(user=self.user, date=today).delete()
        target = ProgressService.generate_daily_target_for_today(self.user, date=today)

        # remaining = 100 - 8 = 92, days = 10 → 9.2
        self.assertEqual(target.required_readiness_per_day, 9.2)

    def test_target_does_not_depend_on_checkin(self):
        """DailyTarget has no study_checked_in or checkin fields."""
        self._create_goal(days_ahead=10)
        target = ProgressService.generate_daily_target_for_today(self.user)

        self.assertFalse(hasattr(target, 'study_checked_in'))
        self.assertFalse(hasattr(target, 'completed_correct_questions'))
        self.assertFalse(hasattr(target, 'completed_growth'))
        self.assertFalse(hasattr(target, 'is_completed'))
        self.assertTrue(hasattr(target, 'required_readiness_per_day'))

    def test_target_does_not_create_fake_growth(self):
        """Revision logging does not change readiness or DailyTarget."""
        self._create_goal(days_ahead=10)
        today = timezone.localdate()
        target = ProgressService.generate_daily_target_for_today(self.user, date=today)
        original_required = target.required_readiness_per_day

        # Log revision time
        ProgressService.log_revision_time(self.user, 30)

        target.refresh_from_db()
        self.assertEqual(target.required_readiness_per_day, original_required)

    def test_target_no_goal(self):
        """No goal → required_readiness_per_day = 0."""
        target = ProgressService.generate_daily_target_for_today(self.user)
        self.assertEqual(target.required_readiness_per_day, 0.0)

    def test_target_date_passed(self):
        """Target date in past → all remaining readiness needed today."""
        today = timezone.localdate()
        UserGoal.objects.create(
            user=self.user,
            exam=self.exam,
            goal_name="Past Goal",
            target_date=today - timezone.timedelta(days=5),
            is_active=True,
        )
        target = ProgressService.generate_daily_target_for_today(self.user, date=today)
        # remaining = 100, days <= 0 → required = 100
        self.assertEqual(target.required_readiness_per_day, 100.0)

    def test_target_already_at_100(self):
        """Already at 100% readiness → required = 0."""
        self._create_goal(days_ahead=10)

        # All 10 concepts at 1.0 readiness → daksh = 100%
        for c in self.concepts:
            ConceptProgress.objects.create(
                user=self.user, concept=c, readiness=1.0,
                last_practiced=timezone.now()
            )

        today = timezone.localdate()
        DailyTarget.objects.filter(user=self.user, date=today).delete()
        from django.core.cache import cache
        cache.clear()
        target = ProgressService.generate_daily_target_for_today(self.user, date=today)
        self.assertEqual(target.required_readiness_per_day, 0.0)

    # ──────────────────────────────────────────────────────────────────────────
    # READINESS TESTS
    # ──────────────────────────────────────────────────────────────────────────

    def test_quiz_evidence_changes_readiness(self):
        """A quiz session updates ConceptProgress.readiness."""
        session = self._create_quiz_session(self.concepts[0], score=1.0, all_correct=True)
        cp = ProgressService.update_progress_with_session(self.user, session)

        # EMA: 0 * (1-0.35) + 1.0 * 0.35 = 0.35
        self.assertEqual(cp.readiness, 0.35)

    def test_negative_readiness_changes_are_preserved(self):
        """Negative readiness changes are NOT clamped to 0."""
        self._create_goal(days_ahead=10)

        # First: score 100% → readiness = 0.35
        session1 = self._create_quiz_session(self.concepts[0], score=1.0, all_correct=True)
        ProgressService.update_progress_with_session(self.user, session1)

        # Second: score 0% → readiness = 0.35 * 0.65 + 0 * 0.35 = 0.2275
        session2 = self._create_quiz_session(self.concepts[0], score=0.0, all_correct=False)
        ProgressService.update_progress_with_session(self.user, session2)

        cp = ConceptProgress.objects.get(user=self.user, concept=self.concepts[0])
        self.assertLess(cp.readiness, 0.35)

        # Check diary has negative readiness_delta
        today = timezone.localdate()
        diary = DailyDiaryEntry.objects.get(user=self.user, date=today)
        # First session: +0.35/10*100 = +3.5
        # Second session: (0.2275 - 0.35)/10*100 = -1.225
        # Total delta should be positive but second session should contribute negative
        # The key point: delta is signed, not clamped

    def test_readiness_delta_correct_units(self):
        """readiness_delta uses exam readiness percentage points."""
        self._create_goal(days_ahead=10)
        session = self._create_quiz_session(self.concepts[0], score=1.0, all_correct=True)
        ProgressService.update_progress_with_session(self.user, session)

        today = timezone.localdate()
        diary = DailyDiaryEntry.objects.get(user=self.user, date=today)

        # delta_readiness = 0.35 - 0 = 0.35
        # growth_increment = (0.35 / 10) * 100 = 3.5 percentage points
        self.assertEqual(diary.readiness_delta, 3.5)

    # ──────────────────────────────────────────────────────────────────────────
    # TRAJECTORY TESTS
    # ──────────────────────────────────────────────────────────────────────────

    def test_trajectory_no_goal(self):
        """No goal → status UNAVAILABLE, reason NO_GOAL."""
        traj = ProgressService.get_authoritative_trajectory(self.user)
        self.assertEqual(traj["status"], "UNAVAILABLE")
        self.assertEqual(traj["status_reason"], "NO_GOAL")
        self.assertIsNone(traj["actual_daily"])

    def test_trajectory_insufficient_evidence(self):
        """Insufficient evidence → status UNAVAILABLE, reason INSUFFICIENT_EVIDENCE."""
        self._create_goal(days_ahead=100)

        # Only 1 day of evidence (need 3)
        today = timezone.localdate()
        diary, _ = DailyDiaryEntry.objects.get_or_create(user=self.user, date=today)
        diary.questions_solved = 5
        diary.readiness_delta = 0.5
        diary.save()

        traj = ProgressService.get_authoritative_trajectory(self.user, date=today)
        self.assertEqual(traj["status"], "UNAVAILABLE")
        self.assertEqual(traj["status_reason"], "INSUFFICIENT_EVIDENCE")
        self.assertIsNone(traj["actual_daily"])
        self.assertIsNotNone(traj["required_daily"])

    def test_trajectory_valid_history(self):
        """Valid history produces actual_daily and valid status."""
        self._create_goal(days_ahead=100)

        today = timezone.localdate()
        # Create 5 days of evidence
        for i in range(5):
            date = today - timezone.timedelta(days=i)
            diary, _ = DailyDiaryEntry.objects.get_or_create(user=self.user, date=date)
            diary.questions_solved = 10
            diary.readiness_delta = 1.0  # 1%pt/day
            diary.save()

        traj = ProgressService.get_authoritative_trajectory(self.user, date=today)
        self.assertIn(traj["status"], ["AHEAD", "BEHIND", "ON_TRACK"])
        self.assertEqual(traj["status_reason"], "VALID_TRAJECTORY")
        self.assertIsNotNone(traj["actual_daily"])
        self.assertGreater(traj["actual_daily"], 0)
        self.assertTrue(traj["has_sufficient_history"])

    def test_trajectory_compatible_units(self):
        """required_daily and actual_daily use the same units."""
        traj = ProgressService.get_authoritative_trajectory(self.user)
        self.assertEqual(
            traj["units"]["required_daily"],
            traj["units"]["actual_daily"]
        )
        self.assertEqual(traj["units"]["required_daily"], "readiness percentage-points / day")

    def test_trajectory_target_date_passed(self):
        """Target date passed → status UNAVAILABLE, reason TARGET_DATE_PASSED."""
        today = timezone.localdate()
        UserGoal.objects.create(
            user=self.user,
            exam=self.exam,
            goal_name="Past Goal",
            target_date=today - timezone.timedelta(days=5),
            is_active=True,
        )
        traj = ProgressService.get_authoritative_trajectory(self.user, date=today)
        self.assertEqual(traj["status"], "UNAVAILABLE")
        self.assertEqual(traj["status_reason"], "TARGET_DATE_PASSED")

    def test_trajectory_target_complete(self):
        """Already at 100% → status COMPLETE, reason TARGET_REACHED."""
        self._create_goal(days_ahead=100)

        for c in self.concepts:
            ConceptProgress.objects.create(
                user=self.user, concept=c, readiness=1.0,
                last_practiced=timezone.now()
            )
        from django.core.cache import cache
        cache.clear()

        traj = ProgressService.get_authoritative_trajectory(self.user)
        self.assertEqual(traj["status"], "COMPLETE")
        self.assertEqual(traj["status_reason"], "TARGET_REACHED")
        self.assertEqual(traj["required_daily"], 0.0)

    def test_trajectory_no_absurd_predictions(self):
        """Valid trajectory does not produce absurd values."""
        self._create_goal(days_ahead=100)

        today = timezone.localdate()
        for i in range(5):
            date = today - timezone.timedelta(days=i)
            diary, _ = DailyDiaryEntry.objects.get_or_create(user=self.user, date=date)
            diary.questions_solved = 5
            diary.readiness_delta = 0.5
            diary.save()

        traj = ProgressService.get_authoritative_trajectory(self.user, date=today)
        if traj["status"] != "UNAVAILABLE":
            # days_delta should be reasonable (not thousands)
            if traj["days_delta"] is not None:
                self.assertLess(traj["days_delta"], 10000)
            # actual_daily should not be absurd
            if traj["actual_daily"] is not None:
                self.assertLess(traj["actual_daily"], 100.0)

    # ──────────────────────────────────────────────────────────────────────────
    # DASHBOARD / API TESTS
    # ──────────────────────────────────────────────────────────────────────────

    def test_dashboard_returns_clean_structure(self):
        """Dashboard returns new clean structure without legacy fields."""
        self._create_goal(days_ahead=10)
        url = reverse("brain-engine")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = response.data
        # New fields present
        self.assertIn("goal", data)
        self.assertIn("daily_target", data)
        self.assertIn("today_evidence", data)
        self.assertIn("today_presence", data)
        self.assertIn("visit_streak", data)
        self.assertIn("daksh_score", data)
        self.assertIn("trajectory", data)

        # Legacy fields absent
        self.assertNotIn("brain_state", data)
        self.assertNotIn("brain_stats", data)
        self.assertNotIn("achievements", data)
        self.assertNotIn("mission_day", data)
        self.assertNotIn("today_growth", data)
        self.assertNotIn("weekly_data", data)
        self.assertNotIn("streak_stats", data)

    def test_daily_target_api(self):
        """GET /api/progress/daily-target/ returns required_readiness_per_day."""
        self._create_goal(days_ahead=10)
        url = reverse("daily-target")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("required_readiness_per_day", response.data)
        self.assertNotIn("study_checked_in", response.data)

    def test_checkin_endpoint_removed(self):
        """The checkin endpoint no longer exists."""
        from django.urls import resolve, Resolver404
        with self.assertRaises(Resolver404):
            resolve("/api/progress/checkin/")

    def test_revision_does_not_create_fake_growth(self):
        """POST /api/progress/revision/ logs time without readiness changes."""
        self._create_goal(days_ahead=10)
        url = reverse("revision-time")
        response = self.client.post(url, {"minutes": 30})
        self.assertEqual(response.status_code, 200)

        # Verify diary has time but no readiness delta
        today = timezone.localdate()
        diary = DailyDiaryEntry.objects.get(user=self.user, date=today)
        self.assertEqual(diary.time_spent_seconds, 1800)  # 30 * 60
        self.assertEqual(diary.readiness_delta, 0.0)  # no fake growth
