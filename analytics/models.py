from django.conf import settings
from django.db import models

from exams.models import Attempt, Exam
from learning.models import Lesson, Topic


class TopicPerformance(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="topic_performance")
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="performance")
    attempts_count = models.PositiveIntegerField(default=0)
    correct_count = models.PositiveIntegerField(default=0)
    wrong_count = models.PositiveIntegerField(default=0)
    accuracy = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    avg_time_seconds = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    mastery_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    last_practiced_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "أداء موضوع"
        verbose_name_plural = "أداء الموضوعات"
        unique_together = [("user", "topic")]

    def __str__(self):
        return f"{self.user} - {self.topic}"


class StudyPlan(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="study_plans")
    source_attempt = models.ForeignKey(Attempt, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=180)
    starts_at = models.DateField()
    ends_at = models.DateField()
    status = models.CharField(max_length=30, default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "خطة دراسة"
        verbose_name_plural = "خطط الدراسة"

    def __str__(self):
        return self.title


class StudyPlanItem(models.Model):
    TYPE_CHOICES = [
        ("lesson", "درس"),
        ("quiz", "اختبار قصير"),
        ("exam", "امتحان"),
        ("review", "مراجعة"),
    ]

    study_plan = models.ForeignKey(StudyPlan, on_delete=models.CASCADE, related_name="items")
    item_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True, blank=True)
    exam = models.ForeignKey(Exam, on_delete=models.SET_NULL, null=True, blank=True)
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=180)
    due_date = models.DateField()
    estimated_minutes = models.PositiveIntegerField(default=30)
    completed_at = models.DateTimeField(null=True, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "مهمة خطة"
        verbose_name_plural = "مهام خطط الدراسة"
        ordering = ["due_date", "sort_order"]


class LandingVisit(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="landing_visits")
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    device_type = models.CharField(max_length=20, default="unknown", db_index=True) # mobile, tablet, pc, bot
    os_family = models.CharField(max_length=50, null=True, blank=True)
    browser_family = models.CharField(max_length=50, null=True, blank=True)
    visited_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ["-visited_at"]
        verbose_name = "زيارة للواجهة"
        verbose_name_plural = "زيارات الواجهة"

    def __str__(self):
        return f"{self.device_type} view at {self.visited_at}"
