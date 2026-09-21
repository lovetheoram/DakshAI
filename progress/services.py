from django.utils import timezone
from django.db import models, transaction
from django.db.models import Sum, Avg
from django.core.cache import cache
from .models import ConceptProgress, ProgressRecord, SubtopicProgress, UserGoal, DailyTarget, DailyDiaryEntry
from quiz.models import QuizSession, QuizAnswer
from syllabus.models import Concept, Exam


# ── Domain constant ──────────────────────────────────────────────────────────
# Exponential moving average smoothing factor for concept readiness.
# readiness_new = readiness_old × (1 - α) + session_score × α
# 0.35 means ~35% weight on new evidence, ~65% on historical.
# Retained because it is the single authoritative readiness update formula
# used in update_progress_with_session.
READINESS_ALPHA = 0.35

# Minimum number of calendar days with evidence to compute trajectory.
MIN_EVIDENCE_DAYS = 3


class ProgressService:

    # ── Exam concept IDs (cached) ────────────────────────────────────────────

    @staticmethod
    def get_exam_concept_ids(exam_id):
        cache_key = f"exam_{exam_id}_concept_ids"
        concept_ids = cache.get(cache_key)
        if concept_ids is None:
            concept_ids = list(Concept.objects.filter(
                subtopic__topic__subject__exam_id=exam_id
            ).values_list("id", flat=True))
            cache.set(cache_key, concept_ids, timeout=86400)
        return concept_ids

    # ── Daksh Score ──────────────────────────────────────────────────────────
    # Definition: percentage of complete exam syllabus represented by current
    # concept readiness.
    #   daksh_score = Σ(readiness of user's concepts) / total_concepts × 100
    # Missing progress rows count as 0 readiness.
    # Zero concepts in exam → None (unavailable).

    @staticmethod
    def get_user_daksh_score(user, exam):
        cache_key = f"user_{user.id}_exam_{exam.id}_daksh_score"
        daksh_score = cache.get(cache_key)
        if daksh_score is None:
            concept_ids = ProgressService.get_exam_concept_ids(exam.id)
            total_concepts = len(concept_ids)
            if total_concepts == 0:
                return None  # No denominator → unavailable
            progress_sum = ConceptProgress.objects.filter(
                user=user,
                concept_id__in=concept_ids
            ).aggregate(total=Sum('readiness'))['total'] or 0.0
            daksh_score = round((progress_sum / total_concepts) * 100.0, 4)
            cache.set(cache_key, daksh_score, timeout=None)
        else:
            daksh_score = float(daksh_score)
        return daksh_score

    # ── Get active goal ──────────────────────────────────────────────────────

    @staticmethod
    def get_active_goal(user):
        """Return the single active UserGoal, or None."""
        return UserGoal.objects.filter(user=user, is_active=True).first()

    # ── Concept progress helper ──────────────────────────────────────────────

    @staticmethod
    def get_or_create_concept_progress(user, concept):
        cp, _ = ConceptProgress.objects.get_or_create(user=user, concept=concept)
        return cp

    # ── Quiz session → progress update ───────────────────────────────────────
    # THE ONLY PLACE that writes ConceptProgress.readiness.

    @staticmethod
    def update_progress_with_session(user, session: QuizSession):
        """
        Updates ConceptProgress readiness via EMA, creates ProgressRecord,
        updates SubtopicProgress, and accumulates daily diary evidence.
        Atomic: all-or-nothing.
        """
        first_q = session.questions.first()
        if not first_q:
            return None

        concept = first_q.concept

        with transaction.atomic():
            cp = ProgressService.get_or_create_concept_progress(user, concept)

            # Fetch all answers for this session
            answers = QuizAnswer.objects.filter(session=session).select_related("question", "sub_question")

            main_correct = sum(1 for a in answers if a.question_id is not None and a.is_correct)
            main_total = sum(1 for a in answers if a.question_id is not None)
            sub_correct = sum(1 for a in answers if a.sub_question_id is not None and a.is_correct)
            sub_total = sum(1 for a in answers if a.sub_question_id is not None)

            # Unified session score (0..1)
            tot_correct = main_correct + sub_correct
            tot_questions = main_total + sub_total
            session_score = tot_correct / tot_questions if tot_questions else 0.0

            # ── Readiness update (EMA) ──
            old_readiness = cp.readiness
            cp.readiness = round(cp.readiness * (1 - READINESS_ALPHA) + session_score * READINESS_ALPHA, 4)
            cp.last_practiced = timezone.now()
            cp.save()

            # ── Readiness delta (SIGNED) ──
            new_readiness = cp.readiness
            delta_readiness = new_readiness - old_readiness  # signed, can be negative

            # ── ProgressRecord ──
            ProgressRecord.objects.create(
                user=user,
                concept=concept,
                quiz_session=session,
                score=session.score,
                correct_count=main_correct + sub_correct,
                wrong_count=(main_total - main_correct) + (sub_total - sub_correct),
                main_correct=main_correct,
                main_total=main_total,
                sub_correct=sub_correct,
                sub_total=sub_total
            )

            # ── SubtopicProgress ──
            SubtopicProgressService.update_from_concept(user, concept)

            # ── Daily diary evidence ──
            today = timezone.localdate()
            diary_entry, _ = DailyDiaryEntry.objects.get_or_create(user=user, date=today)

            # Convert concept-level delta to exam-level percentage points
            exam = concept.subtopic.topic.subject.exam
            concept_ids = ProgressService.get_exam_concept_ids(exam.id)
            total_concepts = len(concept_ids)

            if total_concepts > 0:
                growth_increment = round((delta_readiness / total_concepts) * 100.0, 4)
            else:
                growth_increment = 0.0

            # Concepts attempted
            if not diary_entry.concepts_attempted:
                diary_entry.concepts_attempted = []
            if concept.id not in diary_entry.concepts_attempted:
                diary_entry.concepts_attempted.append(concept.id)

            # Concepts completed (readiness crosses 0.7 threshold)
            if old_readiness < 0.7 and new_readiness >= 0.7:
                if not diary_entry.concepts_completed:
                    diary_entry.concepts_completed = []
                if concept.id not in diary_entry.concepts_completed:
                    diary_entry.concepts_completed.append(concept.id)

            # Accumulate evidence
            diary_entry.questions_solved += (main_total + sub_total)
            diary_entry.questions_correct += (main_correct + sub_correct)
            diary_entry.time_spent_seconds += session.duration_seconds or 0

            # Accumulate signed readiness delta
            diary_entry.readiness_delta = round(diary_entry.readiness_delta + growth_increment, 4)
            diary_entry.save()

        # ── Cache invalidation (outside transaction) ──
        daksh_cache_key = f"user_{user.id}_exam_{exam.id}_daksh_score"
        cache.delete(daksh_cache_key)
        cache.delete(f"dashboard_data_user_{user.id}")
        cache.delete(f"streak_stats_user_{user.id}")

        return cp

    # ── Daily target generation ──────────────────────────────────────────────

    @staticmethod
    def generate_daily_target_for_today(user, date=None):
        """
        Generate or retrieve today's DailyTarget.
        required_readiness_per_day = remaining_readiness / remaining_days
        Units: readiness percentage-points / calendar day
        """
        if date is None:
            date = timezone.localdate()

        target, created = DailyTarget.objects.get_or_create(user=user, date=date)
        if not created:
            return target

        goal = ProgressService.get_active_goal(user)
        if not goal:
            target.required_readiness_per_day = 0.0
            target.save()
            return target

        daksh_score = ProgressService.get_user_daksh_score(user, goal.exam)
        if daksh_score is None:
            target.required_readiness_per_day = 0.0
            target.save()
            return target

        remaining_readiness = max(0.0, 100.0 - daksh_score)
        remaining_days = (goal.target_date - date).days

        if remaining_days <= 0:
            # Target date has passed or is today — all remaining readiness needed now
            target.required_readiness_per_day = remaining_readiness
        elif remaining_readiness <= 0:
            # Already at 100% — nothing required
            target.required_readiness_per_day = 0.0
        else:
            target.required_readiness_per_day = round(remaining_readiness / remaining_days, 4)

        target.save()
        return target

    # ── Presence & Visit Streak ──────────────────────────────────────────────

    @staticmethod
    def record_presence(user):
        """
        Record that the user opened DakshAI today.
        Idempotent: multiple calls on the same day do not create duplicates
        and do not overwrite the first opened_at timestamp.
        """
        today = timezone.localdate()
        diary, created = DailyDiaryEntry.objects.get_or_create(user=user, date=today)
        if diary.opened_at is None:
            diary.opened_at = timezone.now()
            diary.save(update_fields=["opened_at"])
        return diary

    @staticmethod
    def get_visit_streak(user, today=None):
        """
        Count consecutive calendar days (up to and including today)
        where the user opened the app (opened_at IS NOT NULL).

        If today has not been opened yet, the streak continues from yesterday
        (but today doesn't count).
        """
        if today is None:
            today = timezone.localdate()

        # Fetch recent diary entries with presence, ordered by date descending
        entries = (
            DailyDiaryEntry.objects.filter(user=user, opened_at__isnull=False)
            .order_by("-date")
            .values_list("date", flat=True)[:366]
        )
        dates_set = set(entries)

        if not dates_set:
            return 0

        # Start from today if opened, otherwise from yesterday
        check_date = today if today in dates_set else today - timezone.timedelta(days=1)

        streak = 0
        while check_date in dates_set:
            streak += 1
            check_date -= timezone.timedelta(days=1)

        return streak

    @staticmethod
    def get_practice_streak(user, today=None):
        """
        Count consecutive calendar days (up to and including today)
        where the user solved practice questions (questions_solved > 0).

        If today has not had practice yet, the streak continues from yesterday
        (so the user still has today to keep their streak alive).
        """
        if today is None:
            today = timezone.localdate()

        entries = (
            DailyDiaryEntry.objects.filter(user=user, questions_solved__gt=0)
            .order_by("-date")
            .values_list("date", flat=True)[:366]
        )
        dates_set = set(entries)

        if not dates_set:
            return 0

        check_date = today if today in dates_set else today - timezone.timedelta(days=1)

        streak = 0
        while check_date in dates_set:
            streak += 1
            check_date -= timezone.timedelta(days=1)

        return streak

    # ── Revision time logging (no fake growth) ───────────────────────────────

    @staticmethod
    def log_revision_time(user, minutes):
        """
        Log revision time to daily diary without creating any readiness change.
        """
        today = timezone.localdate()
        diary, _ = DailyDiaryEntry.objects.get_or_create(user=user, date=today)
        diary.time_spent_seconds += minutes * 60
        diary.save(update_fields=["time_spent_seconds"])
        return diary

    # ── Authoritative Trajectory ─────────────────────────────────────────────

    @staticmethod
    def get_authoritative_trajectory(user, date=None):
        """
        Single Authoritative Trajectory & Prediction Service.

        required_daily: remaining_readiness / remaining_days
        actual_daily:   total net readiness movement / elapsed calendar days
                        (from first evidence date, NOT active-days-only)

        Both in units: readiness percentage-points / calendar day

        Gating: minimum MIN_EVIDENCE_DAYS calendar days with evidence required.
        """
        if date is None:
            date = timezone.localdate()

        units = {
            "daksh_score": "% current readiness",
            "required_daily": "readiness percentage-points / day",
            "actual_daily": "readiness percentage-points / day",
            "days_delta": "calendar days",
        }

        unavailable_base = {
            "daksh_score": None,
            "required_daily": None,
            "actual_daily": None,
            "status": "UNAVAILABLE",
            "status_reason": None,
            "days_delta": None,
            "projected_completion_date": None,
            "has_sufficient_history": False,
            "target_date": None,
            "days_remaining": None,
            "units": units,
        }

        goal = ProgressService.get_active_goal(user)
        if not goal:
            return {**unavailable_base, "status_reason": "NO_GOAL"}

        daksh_score = ProgressService.get_user_daksh_score(user, goal.exam)
        if daksh_score is None:
            return {
                **unavailable_base,
                "daksh_score": None,
                "status_reason": "NO_EXAM_CONCEPTS",
                "target_date": str(goal.target_date),
            }

        remaining_readiness = max(0.0, 100.0 - daksh_score)
        days_remaining = (goal.target_date - date).days

        # ── Edge case: already at 100% ──
        if remaining_readiness <= 0:
            return {
                "daksh_score": daksh_score,
                "required_daily": 0.0,
                "actual_daily": None,
                "status": "COMPLETE",
                "status_reason": "TARGET_REACHED",
                "days_delta": None,
                "projected_completion_date": None,
                "has_sufficient_history": True,
                "target_date": str(goal.target_date),
                "days_remaining": days_remaining,
                "units": units,
            }

        # ── Edge case: target date passed ──
        if days_remaining <= 0:
            return {
                "daksh_score": daksh_score,
                "required_daily": remaining_readiness,  # all remaining today
                "actual_daily": None,
                "status": "UNAVAILABLE",
                "status_reason": "TARGET_DATE_PASSED",
                "days_delta": None,
                "projected_completion_date": None,
                "has_sufficient_history": False,
                "target_date": str(goal.target_date),
                "days_remaining": days_remaining,
                "units": units,
            }

        required_daily = round(remaining_readiness / days_remaining, 4)

        # ── Actual pace: calendar-day-based ──
        # Find entries with real evidence (readiness_delta != 0 or questions_solved > 0)
        evidence_entries = list(
            DailyDiaryEntry.objects.filter(
                user=user,
                date__lte=date,
            ).filter(
                models.Q(questions_solved__gt=0) | models.Q(readiness_delta__gt=0) | models.Q(readiness_delta__lt=0)
            ).order_by("date")
            .values_list("date", "readiness_delta")
        )

        if len(evidence_entries) < MIN_EVIDENCE_DAYS:
            return {
                "daksh_score": daksh_score,
                "required_daily": required_daily,
                "actual_daily": None,
                "status": "UNAVAILABLE",
                "status_reason": "INSUFFICIENT_EVIDENCE",
                "days_delta": None,
                "projected_completion_date": None,
                "has_sufficient_history": False,
                "target_date": str(goal.target_date),
                "days_remaining": days_remaining,
                "units": units,
            }

        # Calendar-day pace: total net movement / elapsed calendar days
        first_evidence_date = evidence_entries[0][0]
        elapsed_calendar_days = (date - first_evidence_date).days
        if elapsed_calendar_days <= 0:
            elapsed_calendar_days = 1  # same day edge case

        total_net_movement = sum(delta for _, delta in evidence_entries)
        # If legacy diary entries didn't have readiness_delta populated,
        # but user has real verified readiness in daksh_score, use daksh_score
        if total_net_movement <= 0 and daksh_score is not None and daksh_score > 0:
            total_net_movement = daksh_score

        actual_daily = round(total_net_movement / elapsed_calendar_days, 4)

        if actual_daily <= 0:
            return {
                "daksh_score": daksh_score,
                "required_daily": required_daily,
                "actual_daily": actual_daily,
                "status": "BEHIND" if required_daily > 0 else "ON_TRACK",
                "status_reason": "ZERO_OR_NEGATIVE_PACE",
                "days_delta": None,
                "projected_completion_date": None,
                "has_sufficient_history": True,
                "target_date": str(goal.target_date),
                "days_remaining": days_remaining,
                "units": units,
            }

        # ── Projection ──
        projected_days_needed = int(round(remaining_readiness / actual_daily))
        # Protect against unrealistic overflow dates (> 3 years / 1095 days)
        if projected_days_needed > 1095:
            projected_date_obj = None
            days_delta = None
            status = "BEHIND"
        else:
            projected_date_obj = str(date + timezone.timedelta(days=projected_days_needed))
            gap = actual_daily - required_daily
            tolerance = 0.05 * required_daily if required_daily > 0 else 0.01
            if abs(gap) < tolerance:
                status = "ON_TRACK"
                days_delta = 0
            elif gap > 0:
                status = "AHEAD"
                days_delta = max(0, days_remaining - projected_days_needed)
            else:
                status = "BEHIND"
                days_delta = max(0, projected_days_needed - days_remaining)

        return {
            "daksh_score": daksh_score,
            "required_daily": required_daily,
            "actual_daily": actual_daily,
            "status": status,
            "status_reason": "VALID_TRAJECTORY",
            "days_delta": days_delta,
            "projected_completion_date": projected_date_obj,
            "has_sufficient_history": True,
            "target_date": str(goal.target_date),
            "days_remaining": days_remaining,
            "units": units,
        }


class SubtopicProgressService:

    @staticmethod
    def update_from_concept(user, concept: Concept):
        """
        Recalculate subtopic efficiency as direct average of concept readiness.
        No secondary smoothing.
        """
        subtopic = concept.subtopic

        result = ConceptProgress.objects.filter(
            user=user,
            concept__subtopic=subtopic
        ).aggregate(avg_readiness=Avg("readiness"))

        avg_readiness = result["avg_readiness"]
        if avg_readiness is None:
            return None

        sp, _ = SubtopicProgress.objects.get_or_create(
            user=user,
            subtopic=subtopic
        )
        sp.efficiency = round(avg_readiness, 4)
        sp.last_updated = timezone.now()
        sp.save()

        return sp
