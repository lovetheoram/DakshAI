from django.utils import timezone
from .models import ConceptProgress, ProgressRecord, SubtopicProgress
from quiz.models import QuizSession, QuizAnswer
from syllabus.models import Concept


class ProgressService:

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
        and updates SubtopicProgress based on concepts.
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
        print(user,"    .............  ",concept)
        SubtopicProgressService.update_from_concept(user, concept)

        return cp


# class SubtopicProgressService:

#     @staticmethod
#     def update_from_concept(user, concept: Concept):
#         """
#         Recalculate subtopic efficiency whenever a concept changes.
#         """
#         subtopic = concept.subtopic
#         concept_progresses = ConceptProgress.objects.filter(
#             user=user,
#             concept__subtopic=subtopic
#         )

#         if not concept_progresses.exists():
#             return None

#         total_weight = 0
#         weighted_score = 0
#         for cp in concept_progresses:
#             weight = 1.0  # can adjust later if concepts have weights
#             weighted_score += cp.chapter_understanding * weight
#             total_weight += weight

#         raw_efficiency = weighted_score / total_weight if total_weight else 0

#         sp, _ = SubtopicProgress.objects.get_or_create(user=user, subtopic=subtopic)

#         # smoothing
#         alpha = 0.3
#         sp.efficiency = round(sp.efficiency * (1 - alpha) + raw_efficiency * alpha, 4)
#         sp.last_updated = timezone.now()
#         sp.save()

#         return sp
    
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



