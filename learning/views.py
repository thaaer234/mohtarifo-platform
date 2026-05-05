from django.db.models import Count
from rest_framework import generics
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Course, LessonAttendance, OnlineLessonSession
from .serializers import (
    CourseDetailSerializer,
    CourseListSerializer,
    LessonAttendanceSerializer,
    OnlineLessonSessionSerializer,
)


class CourseListApiView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = CourseListSerializer

    def get_queryset(self):
        return (
            Course.objects.filter(status="published")
            .select_related("subject", "instructor")
            .annotate(lessons_count=Count("units__lessons", distinct=True), questions_count=Count("questions", distinct=True))
            .order_by("subject__name", "title")
        )


class CourseDetailApiView(generics.RetrieveAPIView):
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"
    serializer_class = CourseDetailSerializer

    def get_queryset(self):
        return (
            Course.objects.filter(status="published")
            .select_related("subject", "instructor")
            .prefetch_related("units__lessons")
            .annotate(lessons_count=Count("units__lessons", distinct=True), questions_count=Count("questions", distinct=True))
        )


class OnlineSessionListApiView(generics.ListAPIView):
    serializer_class = OnlineLessonSessionSerializer

    def get_queryset(self):
        return (
            OnlineLessonSession.objects.select_related("lesson", "lesson__unit", "lesson__unit__course")
            .annotate(attendance_count=Count("attendances", distinct=True))
            .order_by("starts_at")
        )


class MyAttendanceApiView(APIView):
    def get(self, request):
        if request.user.is_authenticated:
            qs = LessonAttendance.objects.filter(user=request.user)
        else:
            qs = LessonAttendance.objects.none()
        return Response(LessonAttendanceSerializer(qs.select_related("session"), many=True).data)

# Create your views here.
