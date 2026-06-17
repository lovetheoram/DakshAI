from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
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

        ratio = (target.completed_growth / target.target_growth * 100.0) if target.target_growth > 0 else 100.0
        content = (
            f"🚀 Growth Quota Update!\n"
            f"Today's Growth: +{target.completed_growth:.2f}% / +{target.target_growth:.2f}% ({ratio:.0f}% completed)\n"
            f"Solved: {diary.questions_solved} MCQs | Accuracy: {diary.accuracy * 100:.1f}%\n"
            f"Energy: {diary.energy_score}% | Focus: {diary.focus_score}% | Mood: {diary.mood.capitalize()}\n"
            f"Consistency: Measuring growth one percent at a time!"
        )

        from social.models import Post
        post = Post.objects.create(
            user=request.user,
            post_type="text",
            content=content
        )
        invalidate_growth_cache(request.user)
        return Response({
            "detail": "Successfully shared growth progress to feed",
            "post_id": post.id,
            "post_content": content
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

        response_data = {
            "daksh_score": daksh_score,
            "predicted_remaining_days": predicted_remaining_days,
            "avg_growth": avg_growth,
            "today_compliance": today_compliance,
            "week_compliance": week_compliance,
            "month_compliance": month_compliance,
            "growth_streak": streak
        }
        
        cache.set(cache_key, response_data, timeout=3600) # Cache for 1 hour
        return Response(response_data)


class DashboardAPI(APIView):
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

        streak_stats = {
            "daksh_score": daksh_score,
            "predicted_remaining_days": predicted_remaining_days,
            "avg_growth": avg_growth,
            "today_compliance": today_compliance,
            "week_compliance": week_compliance,
            "month_compliance": month_compliance,
            "growth_streak": streak
        }

        entries = DailyDiaryEntry.objects.filter(user=user).order_by("-date")[:30]
        diary_data = DailyDiaryEntrySerializer(entries, many=True).data

        response_data = {
            "goal": UserGoalSerializer(goal).data,
            "target": DailyTargetSerializer(target).data,
            "streak_stats": streak_stats,
            "diary": diary_data
        }
        
        cache.set(cache_key, response_data, timeout=3600) # Cache for 1 hour
        return Response(response_data)
