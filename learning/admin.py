from django.contrib import admin

from .models import (
    Course,
    CourseProgress,
    Lesson,
    LessonAttendance,
    LessonProgress,
    OnlineLessonSession,
    Subject,
    Topic,
    Unit,
)


class UnitInline(admin.TabularInline):
    model = Unit
    extra = 1


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "subject", "instructor", "kind", "academic_track", "term", "status", "is_subscription_included", "published_at")
    list_filter = ("subject", "kind", "academic_track", "term", "status", "is_subscription_included")
    search_fields = ("title", "description", "instructor__username")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [UnitInline]


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "sort_order")
    list_filter = ("course",)
    search_fields = ("title", "course__title")
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "unit", "lesson_type", "has_protected_video", "duration_seconds", "is_free_preview", "sort_order")
    list_filter = ("lesson_type", "is_free_preview", "unit__course")
    search_fields = ("title", "description", "unit__title")

    def has_protected_video(self, obj):
        return bool(obj.video_file)

    has_protected_video.boolean = True
    has_protected_video.short_description = "فيديو محمي"


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("name", "subject", "course", "unit")
    list_filter = ("subject", "course")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "lesson", "watched_seconds", "completed_at", "updated_at")
    list_filter = ("completed_at",)
    search_fields = ("user__username", "lesson__title")


@admin.register(CourseProgress)
class CourseProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "completion_percent", "completed_lessons", "total_lessons")
    search_fields = ("user__username", "course__title")


@admin.register(OnlineLessonSession)
class OnlineLessonSessionAdmin(admin.ModelAdmin):
    list_display = ("title", "lesson", "starts_at", "ends_at", "status", "capacity")
    list_filter = ("status", "lesson__unit__course")
    search_fields = ("title", "lesson__title", "meeting_url")
    date_hierarchy = "starts_at"


@admin.register(LessonAttendance)
class LessonAttendanceAdmin(admin.ModelAdmin):
    list_display = ("user", "session", "status", "joined_at", "left_at", "watched_recording")
    list_filter = ("status", "watched_recording", "session__lesson__unit__course")
    search_fields = ("user__username", "user__email", "session__title")
