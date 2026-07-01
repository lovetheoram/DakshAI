from django.utils import timezone
from django.db import models
from django.db.models import Sum
from django.core.cache import cache
from .models import ConceptProgress, ProgressRecord, SubtopicProgress, UserGoal, DailyTarget, DailyDiaryEntry
from quiz.models import QuizSession, QuizAnswer
from syllabus.models import Concept, Exam


class ProgressService:

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

    @staticmethod
    def get_user_daksh_score(user, exam):
        cache_key = f"user_{user.id}_exam_{exam.id}_daksh_score"
        daksh_score = cache.get(cache_key)
        if daksh_score is None:
            concept_ids = ProgressService.get_exam_concept_ids(exam.id)
            total_concepts = len(concept_ids)
            if total_concepts > 0:
                progress_sum = ConceptProgress.objects.filter(
                    user=user,
                    concept_id__in=concept_ids
                ).aggregate(total=Sum('exam_readiness'))['total'] or 0.0
                daksh_score = round((progress_sum / total_concepts) * 100.0, 4)
            else:
                daksh_score = 0.0
            cache.set(cache_key, daksh_score, timeout=None)
        else:
            daksh_score = float(daksh_score)
        return daksh_score

    @staticmethod
    def get_or_create_concept_progress(user, concept):
        cp, _ = ConceptProgress.objects.get_or_create(user=user, concept=concept)
        return cp

    @staticmethod
    def get_or_create_subtopic_progress(user, subtopic):
        sp, _ = SubtopicProgress.objects.get_or_create(user=user, subtopic=subtopic)
        return sp

    @staticmethod
    def update_progress_with_session(user, session: QuizSession):
        """
        Updates ConceptProgress for both exam readiness (main questions)
        and chapter understanding (sub-questions), creates ProgressRecord,
        updates SubtopicProgress based on concepts, and overlay mathematical growth metrics.
        """
        # for simplicity, assume quiz session covers one concept
        concept = session.questions.first().concept
        cp = ProgressService.get_or_create_concept_progress(user, concept)

        # fetch all answers for this session
        answers = QuizAnswer.objects.filter(session=session).select_related("question", "sub_question")

        main_correct = sum(1 for a in answers if a.question_id is not None and a.is_correct)
        main_total = sum(1 for a in answers if a.question_id is not None)

        sub_correct = sum(1 for a in answers if a.sub_question_id is not None and a.is_correct)
        sub_total = sum(1 for a in answers if a.sub_question_id is not None)

        # compute scores 0..1
        exam_score = main_correct / main_total if main_total else 0
        chapter_score = sub_correct / sub_total if sub_total else 0

        # save old exam readiness to calculate growth delta
        old_readiness = cp.exam_readiness

        # smoothing with alpha
        alpha = 0.35
        cp.exam_readiness = round(cp.exam_readiness * (1 - alpha) + exam_score * alpha, 4)
        cp.chapter_understanding = round(cp.chapter_understanding * (1 - alpha) + chapter_score * alpha, 4)
        cp.last_practiced = timezone.now()
        cp.save()

        # create ProgressRecord
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

        # update subtopic efficiency
        SubtopicProgressService.update_from_concept(user, concept)

        # ----------------------------------------------------
        # Behavioral Growth OS Mathematical Engine
        # ----------------------------------------------------
        today = timezone.localdate()
        target = ProgressService.generate_daily_target_for_today(user, date=today)
        diary_entry, _ = DailyDiaryEntry.objects.get_or_create(user=user, date=today)

        # calculate delta growth
        new_readiness = cp.exam_readiness
        delta_readiness = max(0.0, new_readiness - old_readiness)

        exam = concept.subtopic.topic.subject.exam
        concept_ids = ProgressService.get_exam_concept_ids(exam.id)
        total_concepts = len(concept_ids)

        if total_concepts > 0:
            growth_increment = round((delta_readiness / total_concepts) * 100.0, 4)
        else:
            growth_increment = 0.0

        # update diary telemetry
        if not diary_entry.concepts_attempted:
            diary_entry.concepts_attempted = []
        if concept.id not in diary_entry.concepts_attempted:
            diary_entry.concepts_attempted.append(concept.id)

        if old_readiness < 0.7 and new_readiness >= 0.7:
            if not diary_entry.concepts_completed:
                diary_entry.concepts_completed = []
            if concept.id not in diary_entry.concepts_completed:
                diary_entry.concepts_completed.append(concept.id)

        diary_entry.questions_solved += (main_total + sub_total)
        diary_entry.questions_correct += (main_correct + sub_correct)
        diary_entry.time_spent_seconds += session.duration_seconds or 0
        if diary_entry.questions_solved > 0:
            diary_entry.accuracy = round(diary_entry.questions_correct / diary_entry.questions_solved, 4)
        else:
            diary_entry.accuracy = 0.0

        # track knowledge gain by subject
        subject_name = concept.subtopic.topic.subject.name
        if not diary_entry.knowledge_gain:
            diary_entry.knowledge_gain = {}
        diary_entry.knowledge_gain[subject_name] = diary_entry.knowledge_gain.get(subject_name, 0) + 1

        diary_entry.save()

        # Update DailyTarget
        target.completed_growth = round(target.completed_growth + growth_increment, 4)
        if target.target_growth > 0:
            if target.completed_growth >= target.target_growth:
                target.is_completed = True
            else:
                target.is_completed = False
        else:
            target.is_completed = True
        target.save()

        # Sync diary's growth percentage with the completed growth
        diary_entry.daily_growth_percentage = target.completed_growth
        diary_entry.save()

        # Increment cached daksh score in-memory
        daksh_cache_key = f"user_{user.id}_exam_{exam.id}_daksh_score"
        current_daksh = cache.get(daksh_cache_key)
        if current_daksh is not None:
            new_daksh = round(min(100.0, float(current_daksh) + growth_increment), 4)
            cache.set(daksh_cache_key, new_daksh, timeout=None)

        # Invalidate dashboard and streak stats cache
        cache.delete(f"dashboard_data_user_{user.id}")
        cache.delete(f"streak_stats_user_{user.id}")

        return cp

    @staticmethod
    def generate_daily_target_for_today(user, date=None):
        if date is None:
            date = timezone.localdate()

        target, created = DailyTarget.objects.get_or_create(user=user, date=date)
        if not created:
            return target

        goal = UserGoal.objects.filter(user=user).first()
        if not goal:
            # default fallback if no goal is set
            target.target_growth = 0.83
            target.save()
            return target

        remaining_days = (goal.target_date - date).days
        if remaining_days <= 0:
            remaining_days = 1

        # calculate current readiness across all concepts in the goal's exam
        current_daksh = ProgressService.get_user_daksh_score(user, goal.exam)

        remaining_growth = max(0.0, 100.0 - current_daksh)
        required_growth = round(remaining_growth / remaining_days, 4)

        if remaining_growth > 0:
            target.target_growth = max(0.1, required_growth)
        else:
            target.target_growth = 0.0

        target.save()
        return target

    @staticmethod
    def get_prediction_days(user, date=None, current_daksh=None):
        if date is None:
            date = timezone.localdate()

        goal = UserGoal.objects.filter(user=user).first()
        if not goal:
            return 0, 0.83

        if current_daksh is None:
            current_daksh = ProgressService.get_user_daksh_score(user, goal.exam)

        remaining_growth = max(0.0, 100.0 - current_daksh)

        # average growth based on last 7 diary entries with growth > 0
        recent_entries = DailyDiaryEntry.objects.filter(user=user, daily_growth_percentage__gt=0.0).order_by('-date')[:7]
        growths = [e.daily_growth_percentage for e in recent_entries]

        if growths:
            avg_growth = sum(growths) / len(growths)
        else:
            remaining_days = (goal.target_date - date).days
            if remaining_days > 0:
                avg_growth = remaining_growth / remaining_days
            else:
                avg_growth = 0.83

        if avg_growth <= 0:
            avg_growth = 0.83

        predicted_remaining_days = int(round(remaining_growth / avg_growth))
        return predicted_remaining_days, round(avg_growth, 4)

    @staticmethod
    def compute_confidence(user, recent_records=None):
        """
        Confidence = weighted accuracy trend over recent quiz sessions.
        Recent sessions are weighted 3×, oldest 1×, intermediate 2×.
        New users with < 3 sessions default to 50 (neutral).
        """
        if recent_records is None:
            recent_records = list(
                ProgressRecord.objects.filter(user=user)
                .order_by("-created_at")[:10]
            )
        if len(recent_records) < 3:
            return 50.0

        # Assign weights: newest = 3, then 2, then 1 for the rest
        weighted_sum = 0.0
        total_weight = 0.0
        for i, rec in enumerate(recent_records):
            weight = 3.0 if i == 0 else (2.0 if i == 1 else 1.0)
            accuracy = (rec.correct_count / (rec.correct_count + rec.wrong_count)
                        if (rec.correct_count + rec.wrong_count) > 0 else 0.0)
            weighted_sum += accuracy * weight
            total_weight += weight

        return round((weighted_sum / total_weight) * 100.0, 2) if total_weight > 0 else 50.0

    @staticmethod
    def compute_momentum(week_compliance, diary_entries_7d, targets_7d):
        """
        Momentum = composite of 5 behavioral signals over the past 7 days.
          - 7d compliance rate:       30%
          - avg focus score:          20%
          - growth velocity:          20%  (days where completed_growth > 0)
          - revision frequency:       15%  (days with revision_count > 0)
          - session completion rate:  15%  (days with questions_solved > 0)
        All sub-scores are 0-100; result is 0-100.
        """
        # 7d compliance (already computed, 0-100)
        compliance_score = min(100.0, week_compliance)

        # Avg focus from diary
        focus_scores = [d.focus_score for d in diary_entries_7d]
        avg_focus = (sum(focus_scores) / len(focus_scores)) if focus_scores else 50.0

        # Growth velocity: % of 7 days where any growth occurred
        active_growth_days = sum(1 for t in targets_7d if t.completed_growth > 0)
        growth_velocity = (active_growth_days / 7.0) * 100.0

        # Revision frequency: % of 7 days where revision logged
        revision_days = sum(1 for d in diary_entries_7d if d.revision_count > 0)
        revision_score = (revision_days / 7.0) * 100.0

        # Session completion: % of 7 days where questions solved
        session_days = sum(1 for d in diary_entries_7d if d.questions_solved > 0)
        session_score = (session_days / 7.0) * 100.0

        momentum = (
            compliance_score  * 0.30 +
            avg_focus         * 0.20 +
            growth_velocity   * 0.20 +
            revision_score    * 0.15 +
            session_score     * 0.15
        )
        return round(momentum, 2)

    @staticmethod
    def compute_discipline(current_streak, month_compliance):
        """
        Discipline = streak commitment (70%) + monthly consistency (30%).
        Streak is normalized against a 30-day benchmark.
        """
        streak_score = min(1.0, current_streak / 30.0) * 100.0
        discipline = streak_score * 0.70 + month_compliance * 0.30
        return round(discipline, 2)


class SubtopicProgressService:

    @staticmethod
    def update_from_concept(user, concept: Concept):
        """
        Recalculate subtopic efficiency whenever a concept changes.
        """
        subtopic = concept.subtopic
        concept_progresses = ConceptProgress.objects.filter(
            user=user,
            concept__subtopic=subtopic
        )

        if not concept_progresses.exists():
            return None

        raw_sum = 0.0
        mastery_sum = 0.0
        total_weight = 0.0

        for cp in concept_progresses:
            weight = 1.0

            # -------- RAW (from DB) --------
            raw_avg = (
                cp.exam_readiness +
                cp.chapter_understanding
            ) / 2

            # -------- MASTERY (time-decayed) --------
            mastery_exam, mastery_chapter = cp.get_mastery()
            mastery_avg = (
                mastery_exam +
                mastery_chapter
            ) / 2

            raw_sum += raw_avg * weight
            mastery_sum += mastery_avg * weight
            total_weight += weight

        raw_efficiency = raw_sum / total_weight if total_weight else 0.0
        mastery_efficiency = mastery_sum / total_weight if total_weight else 0.0

        sp, _ = SubtopicProgress.objects.get_or_create(
            user=user,
            subtopic=subtopic
        )

        # smoothing ONLY on mastery (time-based)
        alpha = 0.3
        sp.raw_efficiency = round(raw_efficiency, 4)
        sp.efficiency = round(
            sp.efficiency * (1 - alpha) + mastery_efficiency * alpha,
            4
        )

        sp.last_updated = timezone.now()
        sp.save()

        return sp
