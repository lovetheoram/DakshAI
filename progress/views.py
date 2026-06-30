from django.core.cache import cache
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


class ConceptProgressAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, concept_id):
        concept = Concept.objects.get(id=concept_id)
        cp = ProgressService.get_or_create_concept_progress(request.user, concept)
        return Response(ConceptProgressSerializer(cp).data)


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


# ----------------------------------------------------
# Behavioral Growth OS Endpoints
# ----------------------------------------------------

def invalidate_growth_cache(user):
    cache.delete(f"dashboard_data_user_{user.id}")
    cache.delete(f"streak_stats_user_{user.id}")
    goal = UserGoal.objects.filter(user=user).first()
    if goal:
        cache.delete(f"user_{user.id}_exam_{goal.exam_id}_daksh_score")


class UserGoalAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        goal = UserGoal.objects.filter(user=request.user).first()
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

        goal, created = UserGoal.objects.update_or_create(
            user=user,
            exam=exam,
            defaults={
                "goal_name": goal_name,
                "target_date": target_date,
                "available_hours_per_day": float(available_hours_per_day)
            }
        )

        # Reset today's target to re-calculate based on new goal settings
        today = timezone.localdate()
        DailyTarget.objects.filter(user=user, date=today).delete()
        ProgressService.generate_daily_target_for_today(user, date=today)

        invalidate_growth_cache(user)

        return Response(UserGoalSerializer(goal).data)


class DailyTargetAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.localdate()
        target = ProgressService.generate_daily_target_for_today(request.user, date=today)
        return Response(DailyTargetSerializer(target).data)


class DailyTargetRevisionAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        minutes = request.data.get("minutes")
        if minutes is None:
            return Response({"detail": "minutes field is required"}, status=400)

        try:
            minutes = int(minutes)
        except ValueError:
            return Response({"detail": "minutes must be a valid integer"}, status=400)

        today = timezone.localdate()
        diary, _ = DailyDiaryEntry.objects.get_or_create(user=request.user, date=today)
        diary.time_spent_seconds += minutes * 60
        diary.revision_count += 1
        diary.save()

        # Add a small contribution of +0.10% growth per revision logged today to reward compliance
        target = ProgressService.generate_daily_target_for_today(request.user, date=today)
        target.completed_growth = round(target.completed_growth + 0.10, 4)
        if target.target_growth > 0:
            if target.completed_growth >= target.target_growth:
                target.is_completed = True
            else:
                target.is_completed = False
        else:
            target.is_completed = True
        target.save()

        diary.daily_growth_percentage = target.completed_growth
        diary.save()

        invalidate_growth_cache(request.user)

        return Response({
            "detail": f"Successfully logged {minutes} minutes of revision",
            "completed_growth": target.completed_growth,
            "target_growth": target.target_growth
        })


class DailyDiaryAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        entries = DailyDiaryEntry.objects.filter(user=request.user).order_by("-date")[:30]
        return Response(DailyDiaryEntrySerializer(entries, many=True).data)


class DailyDiaryEnergyAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        energy_score = request.data.get("energy_score")
        focus_score = request.data.get("focus_score")
        mood = request.data.get("mood", "neutral")

        today = timezone.localdate()
        diary, _ = DailyDiaryEntry.objects.get_or_create(user=request.user, date=today)
        if energy_score is not None:
            diary.energy_score = int(energy_score)
        if focus_score is not None:
            diary.focus_score = int(focus_score)
        if mood:
            diary.mood = str(mood)
        diary.save()

        invalidate_growth_cache(request.user)

        return Response(DailyDiaryEntrySerializer(diary).data)


class DailyTargetShareAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        today = timezone.localdate()
        target = ProgressService.generate_daily_target_for_today(request.user, date=today)
        diary, _ = DailyDiaryEntry.objects.get_or_create(user=request.user, date=today)

        # Get overall streak & Daksh score stats to include on the card
        goal = UserGoal.objects.filter(user=request.user).first()
        daksh_score = ProgressService.get_user_daksh_score(request.user, goal.exam) if goal else 0.0

        # Retrieve streak statistics (cached or calculated)
        cache_key = f"streak_stats_user_{request.user.id}"
        cached_stats = cache.get(cache_key)
        if cached_stats:
            streak = cached_stats.get("growth_streak", 0)
        else:
            # Simple fallback: retrieve streak stats directly
            targets = DailyTarget.objects.filter(user=request.user, date__gte=today - timezone.timedelta(days=30))
            targets_dict = {t.date: t for t in targets}
            streak = 0
            t_today = targets_dict.get(today)
            ratio_today = (t_today.completed_growth / t_today.target_growth) if (t_today and t_today.target_growth > 0) else 0.0
            start_check_from = today if ratio_today >= 0.8 else today - timezone.timedelta(days=1)
            check_date = start_check_from
            for _ in range(30):
                t = targets_dict.get(check_date)
                if t:
                    ratio = (t.completed_growth / t.target_growth) if t.target_growth > 0 else 1.0
                    if ratio >= 0.8:
                        streak += 1
                        check_date -= timezone.timedelta(days=1)
                    else:
                        break
                else:
                    break

        ratio = (target.completed_growth / target.target_growth * 100.0) if target.target_growth > 0 else 100.0
        content = (
            f"🚀 Growth Quota Update!\n"
            f"Today's Growth: +{target.completed_growth:.2f}% / +{target.target_growth:.2f}% ({ratio:.0f}% completed)\n"
            f"Solved: {diary.questions_solved} MCQs | Accuracy: {diary.accuracy * 100:.1f}%\n"
            f"Energy: {diary.energy_score}% | Focus: {diary.focus_score}% | Mood: {diary.mood.capitalize()}\n"
            f"Consistency: Measuring growth one percent at a time!"
        )

        post_metadata = {
            "completed_growth": float(target.completed_growth),
            "target_growth": float(target.target_growth),
            "questions_solved": int(diary.questions_solved),
            "accuracy": float(diary.accuracy),
            "energy_score": int(diary.energy_score),
            "focus_score": int(diary.focus_score),
            "streak": int(streak),
            "daksh_score": float(daksh_score)
        }

        from social.models import Post
        post = Post.objects.create(
            user=request.user,
            post_type="progress",
            content=content,
            post_metadata=post_metadata
        )
        invalidate_growth_cache(request.user)
        return Response({
            "detail": "Successfully shared growth progress to feed",
            "post_id": post.id,
            "post_content": content,
            "post_metadata": post_metadata
        })


class StreakStatsAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        cache_key = f"streak_stats_user_{user.id}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        today = timezone.localdate()

        # Overall Daksh Score & Prediction
        goal = UserGoal.objects.filter(user=user).first()
        if goal:
            daksh_score = ProgressService.get_user_daksh_score(user, goal.exam)
        else:
            daksh_score = 0.0

        # Pass daksh_score to get_prediction_days to avoid duplicate queries
        predicted_remaining_days, avg_growth = ProgressService.get_prediction_days(user, date=today, current_daksh=daksh_score)

        # Fetch targets in a single query to avoid N+1 queries in loops
        today_target = ProgressService.generate_daily_target_for_today(user, date=today)
        
        targets = DailyTarget.objects.filter(
            user=user,
            date__gte=today - timezone.timedelta(days=30)
        )
        targets_dict = {t.date: t for t in targets}

        # Calculate today compliance
        if today_target.target_growth > 0:
            today_compliance = min(100.0, round((today_target.completed_growth / today_target.target_growth) * 100.0, 2))
        else:
            today_compliance = 100.0

        # Calculate 7-day and 30-day average compliance
        past_7_days = [today - timezone.timedelta(days=i) for i in range(7)]
        past_30_days = [today - timezone.timedelta(days=i) for i in range(30)]

        def calc_avg_compliance(dates, current_target):
            ratios = []
            for d in dates:
                t = targets_dict.get(d)
                if t:
                    ratio = (t.completed_growth / t.target_growth) if t.target_growth > 0 else 1.0
                    ratios.append(min(1.0, ratio))
                else:
                    if d == today:
                        ratio = (current_target.completed_growth / current_target.target_growth) if current_target.target_growth > 0 else 1.0
                        ratios.append(min(1.0, ratio))
                    else:
                        ratios.append(0.0)
            return round((sum(ratios) / len(dates)) * 100.0, 2)

        week_compliance = calc_avg_compliance(past_7_days, today_target)
        month_compliance = calc_avg_compliance(past_30_days, today_target)

        # Calculate growth streak: consecutive days with compliance >= 80%
        streak = 0
        t_today = targets_dict.get(today)
        ratio_today = (t_today.completed_growth / t_today.target_growth) if (t_today and t_today.target_growth > 0) else 0.0

        # If today is >= 80%, start checking from today; otherwise check starting from yesterday
        start_check_from = today if ratio_today >= 0.8 else today - timezone.timedelta(days=1)

        check_date = start_check_from
        for _ in range(30):
            t = targets_dict.get(check_date)
            if t:
                ratio = (t.completed_growth / t.target_growth) if t.target_growth > 0 else 1.0
                if ratio >= 0.8:
                    streak += 1
                    check_date -= timezone.timedelta(days=1)
                else:
                    break
            else:
                break

        # If streak reached the 30-day boundary, query fallback on-demand for older targets
        if streak == 30:
            older_targets = DailyTarget.objects.filter(
                user=user,
                date__lt=today - timezone.timedelta(days=30),
                date__gte=today - timezone.timedelta(days=366)
            )
            for t in older_targets:
                targets_dict[t.date] = t
            for _ in range(335):
                t = targets_dict.get(check_date)
                if t:
                    ratio = (t.completed_growth / t.target_growth) if t.target_growth > 0 else 1.0
                    if ratio >= 0.8:
                        streak += 1
                        check_date -= timezone.timedelta(days=1)
                    else:
                        break
                else:
                    break

        # Calculate longest streak and total active days
        all_targets = DailyTarget.objects.filter(user=user).order_by('date')
        longest_streak = 0
        current_run = 0
        total_active_days = 0
        prev_date = None
        for t in all_targets:
            if t.completed_growth > 0:
                total_active_days += 1
                
            ratio = (t.completed_growth / t.target_growth) if t.target_growth > 0 else 1.0
            if ratio >= 0.8:
                if prev_date is None or (t.date - prev_date).days == 1:
                    current_run += 1
                else:
                    current_run = 1
                prev_date = t.date
                longest_streak = max(longest_streak, current_run)
            else:
                current_run = 0
                prev_date = None

        response_data = {
            "daksh_score": daksh_score,
            "predicted_remaining_days": predicted_remaining_days,
            "avg_growth": avg_growth,
            "today_compliance": today_compliance,
            "week_compliance": week_compliance,
            "month_compliance": month_compliance,
            "growth_streak": streak,
            "current_streak": streak,
            "longest_streak": longest_streak,
            "total_active_days": total_active_days
        }
        
        cache.set(cache_key, response_data, timeout=3600) # Cache for 1 hour
        return Response(response_data)


class BrainEngineAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        cache_key = f"dashboard_data_user_{user.id}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        today = timezone.localdate()
        
        goal = UserGoal.objects.filter(user=user).first()
        if not goal:
            exams = Exam.objects.all().values("id", "name")
            return Response({
                "goal": None,
                "exams": list(exams)
            })

        target = ProgressService.generate_daily_target_for_today(user, date=today)
        
        daksh_score = ProgressService.get_user_daksh_score(user, goal.exam)

        predicted_remaining_days, avg_growth = ProgressService.get_prediction_days(user, date=today, current_daksh=daksh_score)

        if target.target_growth > 0:
            today_compliance = min(100.0, round((target.completed_growth / target.target_growth) * 100.0, 2))
        else:
            today_compliance = 100.0

        # Fetch targets in a single query to avoid N+1 queries in loops
        targets = DailyTarget.objects.filter(
            user=user,
            date__gte=today - timezone.timedelta(days=30)
        )
        targets_dict = {t.date: t for t in targets}

        past_7_days = [today - timezone.timedelta(days=i) for i in range(7)]
        past_30_days = [today - timezone.timedelta(days=i) for i in range(30)]

        def calc_avg_compliance(dates, current_target):
            ratios = []
            for d in dates:
                t = targets_dict.get(d)
                if t:
                    ratio = (t.completed_growth / t.target_growth) if t.target_growth > 0 else 1.0
                    ratios.append(min(1.0, ratio))
                else:
                    if d == today:
                        ratio = (current_target.completed_growth / current_target.target_growth) if current_target.target_growth > 0 else 1.0
                        ratios.append(min(1.0, ratio))
                    else:
                        ratios.append(0.0)
            return round((sum(ratios) / len(dates)) * 100.0, 2)

        week_compliance = calc_avg_compliance(past_7_days, target)
        month_compliance = calc_avg_compliance(past_30_days, target)

        streak = 0
        t_today = targets_dict.get(today)
        ratio_today = (t_today.completed_growth / t_today.target_growth) if (t_today and t_today.target_growth > 0) else 0.0
        start_check_from = today if ratio_today >= 0.8 else today - timezone.timedelta(days=1)
        check_date = start_check_from
        for _ in range(30):
            t = targets_dict.get(check_date)
            if t:
                ratio = (t.completed_growth / t.target_growth) if t.target_growth > 0 else 1.0
                if ratio >= 0.8:
                    streak += 1
                    check_date -= timezone.timedelta(days=1)
                else:
                    break
            else:
                break

        # If streak reached the 30-day boundary, query fallback on-demand for older targets
        if streak == 30:
            older_targets = DailyTarget.objects.filter(
                user=user,
                date__lt=today - timezone.timedelta(days=30),
                date__gte=today - timezone.timedelta(days=366)
            )
            for t in older_targets:
                targets_dict[t.date] = t
            for _ in range(335):
                t = targets_dict.get(check_date)
                if t:
                    ratio = (t.completed_growth / t.target_growth) if t.target_growth > 0 else 1.0
                    if ratio >= 0.8:
                        streak += 1
                        check_date -= timezone.timedelta(days=1)
                    else:
                        break
                else:
                    break

        # Calculate longest streak and total active days
        all_targets = DailyTarget.objects.filter(user=user).order_by('date')
        longest_streak = 0
        current_run = 0
        total_active_days = 0
        prev_date = None
        for t in all_targets:
            if t.completed_growth > 0:
                total_active_days += 1
                
            ratio = (t.completed_growth / t.target_growth) if t.target_growth > 0 else 1.0
            if ratio >= 0.8:
                if prev_date is None or (t.date - prev_date).days == 1:
                    current_run += 1
                else:
                    current_run = 1
                prev_date = t.date
                longest_streak = max(longest_streak, current_run)
            else:
                current_run = 0
                prev_date = None

        streak_stats = {
            "daksh_score": daksh_score,
            "predicted_remaining_days": predicted_remaining_days,
            "avg_growth": avg_growth,
            "today_compliance": today_compliance,
            "week_compliance": week_compliance,
            "month_compliance": month_compliance,
            "growth_streak": streak,
            "current_streak": streak,
            "longest_streak": longest_streak,
            "total_active_days": total_active_days
        }

        # ── Mission Day ──────────────────────────────────────────────────
        mission_day = (today - goal.created_at.date()).days + 1

        # ── Prediction Engine (Ahead / Behind / On Track) ─────────────────
        days_remaining = (goal.target_date - today).days
        if days_remaining > 0:
            required_daily = round((100.0 - daksh_score) / days_remaining, 4)
        else:
            required_daily = round(100.0 - daksh_score, 4)

        avg_actual = avg_growth  # from get_prediction_days
        gap = avg_actual - required_daily

        if abs(gap) < 0.02:  # within 2% — on track
            pred_status = "on_track"
            pred_days_delta = 0
        elif gap > 0:
            pred_status = "ahead"
            # days saved = gap * days_remaining / required_daily
            pred_days_delta = int(round((gap / required_daily) * days_remaining)) if required_daily > 0 else 0
        else:
            pred_status = "behind"
            pred_days_delta = int(round((abs(gap) / required_daily) * days_remaining)) if required_daily > 0 else 0

        prediction = {
            "status": pred_status,
            "days_delta": pred_days_delta,
            "required_daily": required_daily,
            "actual_daily": round(avg_actual, 4),
            "need_extra": round(max(0.0, required_daily - avg_actual), 4),
        }

        # Calculate yesterday's growth
        yesterday_date = today - timezone.timedelta(days=1)
        yesterday_target = targets_dict.get(yesterday_date)
        yesterday_growth = yesterday_target.completed_growth if yesterday_target else 0.0

        # Calculate weekly average growth
        past_7_growths = []
        for d in past_7_days:
            t = targets_dict.get(d)
            if t:
                past_7_growths.append(t.completed_growth)
            else:
                past_7_growths.append(0.0)
        week_avg_growth = round(sum(past_7_growths) / 7.0, 4)

        # ── Brain State (5 psychological dimensions) ──────────────────────
        diary_entries = DailyDiaryEntry.objects.filter(user=user)
        diary_entries_7d = [d for d in diary_entries if (today - d.date).days < 7]
        targets_7d = [t for d, t in targets_dict.items() if (today - d).days < 7]
        recent_records = list(
            ProgressRecord.objects.filter(user=user).order_by("-created_at")[:10]
        )

        # Compute retention (memory decay ratio)
        all_cp = ConceptProgress.objects.filter(
            user=user, concept_id__in=ProgressService.get_exam_concept_ids(goal.exam.id)
        )
        total_raw = sum(cp.exam_readiness for cp in all_cp)
        total_decayed = sum(cp.get_mastery()[0] for cp in all_cp)
        memory_score = min(100.0, round((total_decayed / total_raw) * 100.0, 2)) if total_raw > 0 else 100.0

        # Accuracy from diary
        solved_entries = [d for d in diary_entries if d.questions_solved > 0]
        accuracy_score = round(
            (sum(d.accuracy for d in solved_entries) / len(solved_entries)) * 100.0, 2
        ) if solved_entries else 0.0

        # Focus from diary
        all_focus = [d.focus_score for d in diary_entries]
        focus_score = round(sum(all_focus) / len(all_focus), 2) if all_focus else 50.0

        # 5 cognitive dimensions
        knowledge_score = daksh_score
        retention_score = memory_score
        confidence_score = ProgressService.compute_confidence(user, recent_records=recent_records)
        momentum_score = ProgressService.compute_momentum(week_compliance, diary_entries_7d, targets_7d)
        discipline_score = ProgressService.compute_discipline(streak, month_compliance)

        brain_state = {
            "knowledge": knowledge_score,
            "retention": retention_score,
            "confidence": confidence_score,
            "momentum": momentum_score,
            "discipline": discipline_score,
        }

        # brain_stats — backward-compat alias (kept until all frontend migrated)
        brain_stats = {
            "knowledge": knowledge_score,
            "memory": retention_score,
            "accuracy": accuracy_score,
            "consistency": week_compliance,
            "focus": focus_score,
        }

        # ── Decay Alerts (top 2 concepts slipping below 70% of raw) ──────
        decay_alerts = []
        concept_ids = ProgressService.get_exam_concept_ids(goal.exam.id)
        progress_records = ConceptProgress.objects.filter(
            user=user, concept_id__in=concept_ids
        ).select_related("concept", "concept__subtopic")
        for cp in progress_records:
            raw = cp.exam_readiness
            if raw < 0.25:  # skip concepts barely started
                continue
            decayed, _ = cp.get_mastery()
            if decayed < raw * 0.70:  # dropped more than 30%
                retention_pct = round(decayed / raw * 100, 1) if raw > 0 else 0.0
                decay_alerts.append({
                    "concept_id": cp.concept_id,
                    "concept_name": cp.concept.name,
                    "retention_pct": retention_pct,
                    "subtopic_name": cp.concept.subtopic.name,
                })
        decay_alerts = sorted(decay_alerts, key=lambda x: x["retention_pct"])[:2]

        entries = DailyDiaryEntry.objects.filter(user=user).order_by("-date")[:30]
        diary_data = DailyDiaryEntrySerializer(entries, many=True).data

        # -------------------------------------------------------------------
        # Weekly data for the bar chart (Mon–Sun of current week)
        # -------------------------------------------------------------------
        DAY_LABELS = ["M", "T", "W", "T", "F", "S", "S"]
        # Find Monday of the current week
        today_weekday = today.weekday()  # 0=Mon, 6=Sun
        week_start = today - datetime.timedelta(days=today_weekday)
        weekly_data = []
        best_day = None
        best_day_val = -1.0
        for i, label in enumerate(DAY_LABELS):
            day_date = week_start + datetime.timedelta(days=i)
            t = targets_dict.get(day_date)
            val = round(t.completed_growth, 4) if t else 0.0
            weekly_data.append({"day": label, "value": val, "date": str(day_date)})
            if val > best_day_val:
                best_day_val = val
                best_day = day_date.strftime("%A")  # e.g. "Monday"

        # -------------------------------------------------------------------
        # Last active concept & recent concepts (from ProgressRecord history)
        # -------------------------------------------------------------------
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
                mastery = 0.0
                if cp_obj:
                    exam_m, chap_m = cp_obj.get_mastery()
                    mastery = round((exam_m + chap_m) / 2 * 100, 2)
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

        # -------------------------------------------------------------------
        # Dynamic achievements from real data
        # -------------------------------------------------------------------
        total_questions_solved = sum(d.questions_solved for d in diary_entries)
        avg_accuracy = brain_stats["accuracy"]
        achievements = []
        if streak >= 3:
            achievements.append({"emoji": "🔥", "label": f"{streak}d Streak", "unlocked": True})
        else:
            achievements.append({"emoji": "🔥", "label": "3d Streak", "unlocked": False})
        if total_questions_solved >= 100:
            achievements.append({"emoji": "🧠", "label": "100 Questions", "unlocked": True})
        elif total_questions_solved >= 50:
            achievements.append({"emoji": "🧠", "label": "50 Questions", "unlocked": True})
        else:
            achievements.append({"emoji": "🧠", "label": "100 Questions", "unlocked": False})
        if avg_accuracy >= 80:
            achievements.append({"emoji": "🎯", "label": "90% Accuracy", "unlocked": True})
        else:
            achievements.append({"emoji": "🎯", "label": "90% Accuracy", "unlocked": False})
        if week_compliance >= 80:
            achievements.append({"emoji": "⚡", "label": "Week On Fire", "unlocked": True})
        else:
            achievements.append({"emoji": "⚡", "label": "Week On Fire", "unlocked": False})
        if daksh_score >= 50:
            achievements.append({"emoji": "🏆", "label": "Half Ready", "unlocked": True})
        else:
            achievements.append({"emoji": "🏆", "label": "Half Ready", "unlocked": False})

        response_data = {
            "brain_engine_version": "2.0",
            "mission_day": mission_day,
            "goal": UserGoalSerializer(goal).data,
            "target": DailyTargetSerializer(target).data,
            "streak_stats": streak_stats,
            "prediction": prediction,
            "brain_state": brain_state,
            "brain_stats": brain_stats,        # backward-compat alias
            "decay_alerts": decay_alerts,
            "diary": diary_data,
            "today_growth": target.completed_growth,
            "target_growth": target.target_growth,
            "yesterday_growth": yesterday_growth,
            "week_avg_growth": week_avg_growth,
            "overall_score": daksh_score,
            "weekly_data": weekly_data,
            "best_day": best_day,
            "last_active_concept": last_active_concept,
            "recent_concepts": recent_concepts,
            "achievements": achievements
        }

        cache.set(cache_key, response_data, timeout=3600)
        return Response(response_data)
