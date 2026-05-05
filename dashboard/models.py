from django.conf import settings
from django.db import models


class StudentNotification(models.Model):
    TYPE_CHOICES = [
        ("access", "Access"),
        ("attendance", "Attendance"),
        ("lesson", "Lesson"),
        ("system", "System"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_notifications")
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="system")
    title = models.CharField(max_length=160)
    body = models.TextField()
    url = models.CharField(max_length=255, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "إشعار طالب"
        verbose_name_plural = "إشعارات الطلاب"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
