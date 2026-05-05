from django.db.models import Avg, Count
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from exams.models import Attempt
from learning.models import CourseProgress, LessonProgress

from .models import StudyPlan, TopicPerformance
from .serializers import StudyPlanSerializer, TopicPerformanceSerializer


class StudentDashboardApiView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        accuracy = Attempt.objects.filter(user=user, accuracy__isnull=False).aggregate(value=Avg("accuracy"))["value"] or 0
        completed_lessons = LessonProgress.objects.filter(user=user, completed_at__isnull=False).count()
        total_courses = CourseProgress.objects.filter(user=user).count()

        return Response(
            {
                "metrics": [
                    {"label": "الدقة العامة", "value": f"{round(float(accuracy), 1)}%", "progress": float(accuracy)},
                    {"label": "الدروس المكتملة", "value": str(completed_lessons), "progress": 60},
                    {"label": "المواد النشطة", "value": str(total_courses), "progress": 40},
                ],
                "recommendation": {
                    "title": "راجع قوانين النهايات ثم حل 15 سؤالًا",
                    "reason": "ظهرت أخطاء متكررة في أسئلة النهايات المركبة.",
                },
            }
        )


class AnalyticsSummaryApiView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = TopicPerformance.objects.filter(user=request.user).select_related("topic")
        user_attempts = Attempt.objects.filter(user=request.user)
        return Response(
            {
                "weak_topics": TopicPerformanceSerializer(qs.order_by("accuracy")[:10], many=True).data,
                "attempts_count": user_attempts.count(),
                "average_accuracy": user_attempts.aggregate(value=Avg("accuracy"))["value"],
            }
        )


class StudyPlanApiView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = StudyPlan.objects.filter(user=request.user).prefetch_related("items").order_by("-created_at")
        plan = qs.first()
        return Response(StudyPlanSerializer(plan).data if plan else None)

# Create your views here.
