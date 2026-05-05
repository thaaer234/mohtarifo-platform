from django.contrib import admin

from .models import Attempt, AttemptAnswer, Exam, ExamQuestion, Question, QuestionOption


class QuestionOptionInline(admin.TabularInline):
    model = QuestionOption
    extra = 4


class ExamQuestionInline(admin.TabularInline):
    model = ExamQuestion
    extra = 1
    autocomplete_fields = ("question",)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("short_body", "topic", "difficulty", "question_type", "status", "author")
    list_filter = ("difficulty", "question_type", "status", "topic")
    search_fields = ("body", "explanation", "topic__name")
    autocomplete_fields = ("course", "unit", "lesson", "topic", "author")
    inlines = [QuestionOptionInline]

    def short_body(self, obj):
        return obj.body[:70]

    short_body.short_description = "السؤال"


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "mode", "duration_minutes", "question_count", "status")
    list_filter = ("mode", "status", "course")
    search_fields = ("title", "description")
    autocomplete_fields = ("course", "unit", "lesson")
    inlines = [ExamQuestionInline]


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "exam", "status", "score", "max_score", "accuracy", "started_at", "submitted_at")
    list_filter = ("status", "exam")
    search_fields = ("user__username", "exam__title")


@admin.register(AttemptAnswer)
class AttemptAnswerAdmin(admin.ModelAdmin):
    list_display = ("attempt", "question", "selected_option", "is_correct", "time_seconds")
    list_filter = ("is_correct",)
    search_fields = ("attempt__user__username", "question__body")

# Register your models here.
