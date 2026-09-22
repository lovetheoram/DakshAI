from django.core.cache import cache
from django.db import models
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
import datetime
from .models import ConceptProgress, ProgressRecord, SubtopicProgress, UserGoal, DailyTarget, DailyDiaryEntry
from .serializers import (
    ConceptProgressSerializer, ProgressRecordSerializer, SubtopicProgressSerializer,
    UserGoalSerializer, DailyTargetSerializer, DailyDiaryEntrySerializer
)
from .services import ProgressService
from syllabus.models import Concept, Subtopic, Exam

# Behavioral event tracking
try:
    from behavior.services.event_processor import EventProcessor as _EventProcessor
except Exception:
    _EventProcessor = None


def invalidate_growth_cache(user):
    cache.delete(f"dashboard_data_user_{user.id}")
    cache.delete(f"streak_stats_user_{user.id}")
    goal = ProgressService.get_active_goal(user)
    if goal:
        cache.delete(f"user_{user.id}_exam_{goal.exam_id}_daksh_score")


# ── Concept & Subtopic Progress ──────────────────────────────────────────────

class ConceptProgressAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, concept_id):
        concept = Concept.objects.get(id=concept_id)
        cp = ProgressService.get_or_create_concept_progress(request.user, concept)
        data = ConceptProgressSerializer(cp).data
        records = ProgressRecord.objects.filter(user=request.user, concept=concept)
        data["total_questions_solved"] = sum(r.main_total + r.sub_total for r in records)
        data["total_attempts"] = records.count()
        return Response(data)


class ConceptHistoryAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, concept_id):
        user = request.user
        records = ProgressRecord.objects.filter(user=user, concept_id=concept_id).order_by("created_at")
        record_list = ProgressRecordSerializer(records, many=True).data

        if records.exists():
            exam_scores = [r["main_correct"] / r["main_total"] if r["main_total"] else 0 for r in record_list]
            chapter_scores = [r["sub_correct"] / r["sub_total"] if r["sub_total"] else 0 for r in record_list]
            summary = {
                "total_attempts": len(records),
                "best_exam_score": max(exam_scores) if exam_scores else 0,
                "best_chapter_score": max(chapter_scores) if chapter_scores else 0,
                "average_exam_score": sum(exam_scores)/len(exam_scores) if exam_scores else 0,
                "average_chapter_score": sum(chapter_scores)/len(chapter_scores) if chapter_scores else 0,
            }
        else:
            summary = {
                "total_attempts": 0,
                "best_exam_score": 0,
                "best_chapter_score": 0,
                "average_exam_score": 0,
                "average_chapter_score": 0,
            }

        return Response({
            "concept_id": concept_id,
            "summary": summary,
            "records": record_list
        })


class SubtopicProgressAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, subtopic_id):
        subtopic = Subtopic.objects.get(id=subtopic_id)
        sp, _ = SubtopicProgress.objects.get_or_create(user=request.user, subtopic=subtopic)
        return Response(SubtopicProgressSerializer(sp).data)


# ── User Goal ────────────────────────────────────────────────────────────────

class UserGoalAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        goal = ProgressService.get_active_goal(request.user)
        if not goal:
            return Response({"detail": "No goal set yet"}, status=404)
        return Response(UserGoalSerializer(goal).data)

    def post(self, request):
        user = request.user
        exam_id = request.data.get("exam")
        goal_name = request.data.get("goal_name")
        target_date = request.data.get("target_date")
        available_hours_per_day = request.data.get("available_hours_per_day", 2.0)

        if not exam_id or not goal_name or not target_date:
            return Response({"detail": "exam, goal_name, and target_date are required fields"}, status=400)

        try:
            exam = Exam.objects.get(id=exam_id)
        except Exam.DoesNotExist:
            return Response({"detail": "Exam not found"}, status=404)

        # Deactivate any existing goals for this user/exam
        UserGoal.objects.filter(user=user, exam=exam).update(is_active=False)

        goal, created = UserGoal.objects.update_or_create(
            user=user,
            exam=exam,
            defaults={
                "goal_name": goal_name,
                "target_date": target_date,
                "available_hours_per_day": float(available_hours_per_day),
                "is_active": True,
            }
        )

        # Reset today's target to re-calculate based on new goal settings
        today = timezone.localdate()
        DailyTarget.objects.filter(user=user, date=today).delete()
        ProgressService.generate_daily_target_for_today(user, date=today)

        invalidate_growth_cache(user)

        # Fire behavioral event
        if _EventProcessor:
            _EventProcessor.log(user, "GOAL_SET", {
                "exam_name": exam.name,
                "target_date": str(target_date),
            })

        return Response(UserGoalSerializer(goal).data)


# ── Daily Target ─────────────────────────────────────────────────────────────

class DailyTargetAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.localdate()
        target = ProgressService.generate_daily_target_for_today(request.user, date=today)
        return Response(DailyTargetSerializer(target).data)


# ── App Presence (automatic, no user interaction required) ───────────────────

class AppPresenceAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        diary = ProgressService.record_presence(request.user)
        return Response({
            "date": str(diary.date),
            "opened_at": diary.opened_at.isoformat() if diary.opened_at else None,
            "visit_streak": ProgressService.get_visit_streak(request.user),
        })


# ── Revision Time Logger (no fake growth) ────────────────────────────────────

class RevisionTimeAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        minutes = request.data.get("minutes")
        if minutes is None:
            return Response({"detail": "minutes field is required"}, status=400)

        try:
            minutes = int(minutes)
        except ValueError:
            return Response({"detail": "minutes must be a valid integer"}, status=400)

        if minutes <= 0:
            return Response({"detail": "minutes must be positive"}, status=400)

        diary = ProgressService.log_revision_time(request.user, minutes)
        invalidate_growth_cache(request.user)

        return Response({
            "detail": f"Successfully logged {minutes} minutes of revision",
            "time_spent_seconds": diary.time_spent_seconds,
        })


# ── Daily Diary ──────────────────────────────────────────────────────────────

class DailyDiaryAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        entries = DailyDiaryEntry.objects.filter(user=request.user).order_by("-date")[:30]
        return Response(DailyDiaryEntrySerializer(entries, many=True).data)


# ── Streak Stats ─────────────────────────────────────────────────────────────

class StreakStatsAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        cache_key = f"streak_stats_user_{user.id}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        goal = ProgressService.get_active_goal(user)
        daksh_score = ProgressService.get_user_daksh_score(user, goal.exam) if goal else None

        today = timezone.localdate()
        trajectory = ProgressService.get_authoritative_trajectory(user, date=today)
        visit_streak = ProgressService.get_visit_streak(user, today=today)
        practice_streak = ProgressService.get_practice_streak(user, today=today)

        # Total active days (days with any study evidence)
        total_active_days = DailyDiaryEntry.objects.filter(
            user=user, questions_solved__gt=0
        ).count()

        # Active days this week
        today_weekday = today.weekday()
        week_start = today - datetime.timedelta(days=today_weekday)
        active_days_this_week = DailyDiaryEntry.objects.filter(
            user=user,
            date__gte=week_start,
            date__lte=today,
            questions_solved__gt=0
        ).count()

        response_data = {
            "daksh_score": daksh_score,
            "visit_streak": visit_streak,
            "practice_streak": practice_streak,
            "current_streak": practice_streak,
            "growth_streak": practice_streak,
            "total_active_days": total_active_days,
            "active_days_this_week": active_days_this_week,
            "trajectory": trajectory,
        }

        cache.set(cache_key, response_data, timeout=3600)
        return Response(response_data)


# ── Brain Engine (Dashboard) ─────────────────────────────────────────────────

class BrainEngineAPI(APIView):
    """
    Single dashboard endpoint. Returns only trustworthy, evidence-based data.
    Every number returned is explainable in one sentence.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        cache_key = f"dashboard_data_user_{user.id}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        today = timezone.localdate()

        goal = ProgressService.get_active_goal(user)
        if not goal:
            exams = Exam.objects.all().values("id", "name")
            return Response({
                "goal": None,
                "exams": list(exams)
            })

        # ── Core metrics ──
        target = ProgressService.generate_daily_target_for_today(user, date=today)
        daksh_score = ProgressService.get_user_daksh_score(user, goal.exam)
        trajectory = ProgressService.get_authoritative_trajectory(user, date=today)
        visit_streak = ProgressService.get_visit_streak(user, today=today)
        practice_streak = ProgressService.get_practice_streak(user, today=today)

        # ── Today's evidence ──
        today_diary, _ = DailyDiaryEntry.objects.get_or_create(user=user, date=today)
        today_evidence = {
            "questions_solved": today_diary.questions_solved,
            "questions_correct": today_diary.questions_correct,
            "time_spent_seconds": today_diary.time_spent_seconds,
            "readiness_delta": today_diary.readiness_delta,
            "has_activity": today_diary.questions_solved > 0,
            "accuracy": round(today_diary.questions_correct / today_diary.questions_solved, 4) if today_diary.questions_solved > 0 else None,
            "active_minutes": today_diary.time_spent_seconds // 60,
        }

        # ── Today presence ──
        today_presence = today_diary.opened_at is not None

        # ── Decay Alerts (top 2 concepts slipping below 70% of raw) ──
        decay_alerts = []
        concept_ids = ProgressService.get_exam_concept_ids(goal.exam.id)
        progress_records = ConceptProgress.objects.filter(
            user=user, concept_id__in=concept_ids
        ).select_related("concept", "concept__subtopic")
        for cp in progress_records:
            raw = cp.readiness
            if raw < 0.25:  # skip concepts barely started
                continue
            decayed = cp.get_mastery()
            if decayed < raw * 0.70:  # dropped more than 30%
                retention_pct = round(decayed / raw * 100, 1) if raw > 0 else 0.0
                decay_alerts.append({
                    "concept_id": cp.concept_id,
                    "concept_name": cp.concept.name,
                    "retention_pct": retention_pct,
                    "subtopic_name": cp.concept.subtopic.name,
                })
        decay_alerts = sorted(decay_alerts, key=lambda x: x["retention_pct"])[:2]

        # ── Last active concept & recent concepts ──
        recent_records = (
            ProgressRecord.objects
            .filter(user=user, concept__subtopic__topic__subject__exam=goal.exam)
            .select_related("concept", "concept__subtopic")
            .order_by("-created_at")
        )

        seen_concepts = {}
        for rec in recent_records:
            cid = rec.concept.id
            if cid not in seen_concepts:
                cp_obj = ConceptProgress.objects.filter(user=user, concept=rec.concept).first()
                mastery = round(cp_obj.get_mastery() * 100, 2) if cp_obj else 0.0
                seen_concepts[cid] = {
                    "id": cid,
                    "name": rec.concept.name,
                    "mastery": mastery,
                    "subtopic_name": rec.concept.subtopic.name,
                    "last_practiced": rec.created_at.isoformat()
                }
            if len(seen_concepts) >= 5:
                break

        concept_list = list(seen_concepts.values())
        last_active_concept = concept_list[0] if concept_list else None
        recent_concepts = concept_list[1:5] if len(concept_list) > 1 else []

        # ── Exam coverage stats ──
        total_concepts = len(concept_ids)
        concepts_mastered_count = ConceptProgress.objects.filter(
            user=user, concept_id__in=concept_ids, readiness__gte=0.5
        ).count()

        # ── Retention score (decayed/raw ratio across all practiced concepts) ──
        all_cp = ConceptProgress.objects.filter(
            user=user, concept_id__in=concept_ids
        )
        total_raw = sum(cp.readiness for cp in all_cp)
        total_decayed = sum(cp.get_mastery() for cp in all_cp)
        retention_score = round((total_decayed / total_raw) * 100.0, 2) if total_raw > 0 else None

        # ── Recent quiz accuracy (weighted, from last 10 sessions) ──
        recent_quiz_records = list(
            ProgressRecord.objects.filter(user=user)
            .order_by("-created_at")[:10]
        )
        if len(recent_quiz_records) >= 3:
            total_correct = sum(r.correct_count for r in recent_quiz_records)
            total_answered = sum(r.correct_count + r.wrong_count for r in recent_quiz_records)
            quiz_accuracy = round((total_correct / total_answered) * 100.0, 2) if total_answered > 0 else None
        else:
            quiz_accuracy = None

        # ── Diary history for charts ──
        diary_entries = DailyDiaryEntry.objects.filter(user=user).order_by("-date")[:14]
        diary_data = DailyDiaryEntrySerializer(diary_entries, many=True).data

        # ── Total questions solved (all time) ──
        total_questions_solved = DailyDiaryEntry.objects.filter(
            user=user
        ).aggregate(total=models.Sum("questions_solved"))["total"] or 0

        # ── Active days this week ──
        today_weekday = today.weekday()
        week_start = today - datetime.timedelta(days=today_weekday)
        active_days_this_week = DailyDiaryEntry.objects.filter(
            user=user,
            date__gte=week_start,
            date__lte=today,
            questions_solved__gt=0
        ).count()

        # ── Subject breakdown & Bottleneck diagnostic ──
        subject_breakdown = []
        bottleneck = None
        if goal and goal.exam:
            subjects = goal.exam.subjects.prefetch_related("topics__subtopics__concepts").all()
            lowest_subj = None
            lowest_subj_pct = 101

            for s in subjects:
                s_concepts = list(Concept.objects.filter(subtopic__topic__subject=s))
                total_s = len(s_concepts)
                if total_s > 0:
                    c_ids = [c.id for c in s_concepts]
                    cps = list(ConceptProgress.objects.filter(user=user, concept_id__in=c_ids))
                    mastered = sum(1 for cp in cps if cp.readiness >= 0.5)
                    pct = round((mastered / total_s) * 100)
                else:
                    pct = 0

                status = "READY" if pct >= 70 else ("DEVELOPING" if pct >= 40 else "UNSTABLE")
                subject_breakdown.append({
                    "id": s.id,
                    "name": s.name,
                    "readiness_pct": pct,
                    "status": status,
                    "total_concepts": total_s
                })

                if pct < lowest_subj_pct:
                    lowest_subj_pct = pct
                    lowest_subj = s

            if lowest_subj:
                subtopics = Subtopic.objects.filter(topic__subject=lowest_subj).prefetch_related("concepts")
                lowest_st = None
                lowest_st_low_count = -1
                candidate_concept = None

                for st in subtopics:
                    st_concepts = list(st.concepts.all())
                    if not st_concepts:
                        continue
                    st_c_ids = [c.id for c in st_concepts]
                    st_cps = {cp.concept_id: cp for cp in ConceptProgress.objects.filter(user=user, concept_id__in=st_c_ids)}
                    low_count = sum(1 for c in st_concepts if st_cps.get(c.id) is None or st_cps[c.id].readiness < 0.4)
                    if low_count > lowest_st_low_count:
                        lowest_st_low_count = low_count
                        lowest_st = st
                        for c in st_concepts:
                            if st_cps.get(c.id) is None or st_cps[c.id].readiness < 0.4:
                                candidate_concept = c
                                break

                if lowest_st:
                    count_display = lowest_st_low_count if lowest_st_low_count > 0 else len(lowest_st.concepts.all())
                    bottleneck = {
                        "subject_name": lowest_subj.name,
                        "subtopic_id": lowest_st.id,
                        "subtopic_name": lowest_st.name,
                        "low_readiness_count": count_display,
                        "reason": f"{count_display} concepts have low readiness and recent practice hasn't moved them." if count_display > 0 else f"Initial practice needed in {lowest_st.name}.",
                        "action_concept_id": candidate_concept.id if candidate_concept else (lowest_st.concepts.first().id if lowest_st.concepts.exists() else None),
                        "action_concept_name": candidate_concept.name if candidate_concept else (lowest_st.concepts.first().name if lowest_st.concepts.exists() else lowest_st.name),
                    }

        # ── Build response ──
        response_data = {
            "goal": UserGoalSerializer(goal).data,
            "daily_target": DailyTargetSerializer(target).data,
            "today_evidence": today_evidence,
            "today_presence": today_presence,
            "visit_streak": visit_streak,
            "practice_streak": practice_streak,
            "streak_stats": {
                "visit_streak": visit_streak,
                "practice_streak": practice_streak,
                "current_streak": practice_streak,
                "growth_streak": practice_streak,
                "total_active_days": DailyDiaryEntry.objects.filter(user=user, questions_solved__gt=0).count(),
                "active_days_this_week": active_days_this_week,
            },
            "daksh_score": daksh_score,
            "trajectory": trajectory,
            "prediction": trajectory,
            "subject_breakdown": subject_breakdown,
            "bottleneck": bottleneck,
            "decay_alerts": decay_alerts,
            "last_active_concept": last_active_concept,
            "recent_concepts": recent_concepts,
            "concepts_mastered_count": concepts_mastered_count,
            "total_concepts_in_exam": total_concepts,
            "retention_score": retention_score,
            "quiz_accuracy": quiz_accuracy,
            "diary": diary_data,
            "total_questions_solved": total_questions_solved,
            "active_days_this_week": active_days_this_week,
        }

        cache.set(cache_key, response_data, timeout=3600)
        return Response(response_data)


# ── Galaxy (Knowledge Galaxy) ────────────────────────────────────────────────

class GalaxyAPI(APIView):
    """Lightweight endpoint returning subtopic-level progress for the Knowledge Galaxy."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        goal = ProgressService.get_active_goal(user)
        if not goal:
            return Response({"subjects": [], "total_concepts": 0, "mastered_count": 0})

        subjects_data = []
        subjects = goal.exam.subjects.prefetch_related(
            "topics__subtopics"
        ).all()

        for subject in subjects:
            subtopics_data = []
            for topic in subject.topics.all():
                for st in topic.subtopics.all():
                    sp = SubtopicProgress.objects.filter(
                        user=user, subtopic=st
                    ).first()
                    subtopics_data.append({
                        "id": st.id,
                        "name": st.name,
                        "efficiency": round(sp.efficiency, 2) if sp else 0.0,
                    })
            subjects_data.append({
                "name": subject.name,
                "subtopics": subtopics_data,
            })

        concept_ids = ProgressService.get_exam_concept_ids(goal.exam.id)
        mastered_count = ConceptProgress.objects.filter(
            user=user,
            concept_id__in=concept_ids,
            readiness__gte=0.5
        ).count()

        return Response({
            "subjects": subjects_data,
            "total_concepts": len(concept_ids),
            "mastered_count": mastered_count,
        })
