from django.contrib import admin

from .models import StudyPlan, StudyPlanItem, TopicPerformance


class StudyPlanItemInline(admin.TabularInline):
    model = StudyPlanItem
    extra = 1


@admin.register(TopicPerformance)
class TopicPerformanceAdmin(admin.ModelAdmin):
    list_display = ("user", "topic", "accuracy", "avg_time_seconds", "mastery_score", "last_practiced_at")
    list_filter = ("topic",)
    search_fields = ("user__username", "topic__name")


@admin.register(StudyPlan)
class StudyPlanAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "starts_at", "ends_at", "status")
    list_filter = ("status",)
    search_fields = ("title", "user__username")
    inlines = [StudyPlanItemInline]

# Register your models here.
