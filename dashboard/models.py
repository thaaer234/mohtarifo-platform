from django.conf import settings
from django.db import models


class CatalogSection(models.Model):
    label = models.CharField(max_length=120)
    kind = models.CharField(max_length=24)
    track = models.CharField(max_length=24)
    sort_order = models.PositiveIntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "فلتر كتالوج"
        verbose_name_plural = "فلاتر الكتالوج"
        ordering = ["sort_order", "label"]
        constraints = [
            models.UniqueConstraint(fields=["kind", "track"], name="unique_catalog_kind_track")
        ]

    def __str__(self):
        return self.label


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
