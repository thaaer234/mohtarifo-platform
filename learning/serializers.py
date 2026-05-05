from rest_framework import serializers

from .models import Course, CourseProgress, Lesson, LessonAttendance, OnlineLessonSession, Subject, Topic, Unit


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ["id", "name", "slug", "description"]


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = [
            "id",
            "title",
            "description",
            "lesson_type",
            "video_url",
            "duration_seconds",
            "is_free_preview",
            "sort_order",
        ]


class UnitSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)

    class Meta:
        model = Unit
        fields = ["id", "title", "description", "sort_order", "lessons"]


class CourseListSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True)
    lessons_count = serializers.IntegerField(read_only=True)
    questions_count = serializers.IntegerField(read_only=True)
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "subject",
            "status",
            "price_cents",
            "is_subscription_included",
            "lessons_count",
            "questions_count",
            "progress",
        ]

    def get_progress(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return 0
        progress = CourseProgress.objects.filter(user=request.user, course=obj).first()
        return float(progress.completion_percent) if progress else 0


class CourseDetailSerializer(CourseListSerializer):
    units = UnitSerializer(many=True, read_only=True)

    class Meta(CourseListSerializer.Meta):
        fields = CourseListSerializer.Meta.fields + ["units"]


class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = ["id", "name", "slug"]


class OnlineLessonSessionSerializer(serializers.ModelSerializer):
    lesson_title = serializers.CharField(source="lesson.title", read_only=True)
    course_title = serializers.CharField(source="lesson.unit.course.title", read_only=True)
    attendance_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = OnlineLessonSession
        fields = [
            "id",
            "title",
            "lesson",
            "lesson_title",
            "course_title",
            "starts_at",
            "ends_at",
            "meeting_url",
            "recording_url",
            "status",
            "capacity",
            "attendance_count",
        ]


class LessonAttendanceSerializer(serializers.ModelSerializer):
    session_title = serializers.CharField(source="session.title", read_only=True)

    class Meta:
        model = LessonAttendance
        fields = [
            "id",
            "session",
            "session_title",
            "status",
            "joined_at",
            "left_at",
            "watched_recording",
            "notes",
        ]
