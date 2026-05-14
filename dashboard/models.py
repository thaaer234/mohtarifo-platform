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


class WhatsAppTemplate(models.Model):
    title = models.CharField(max_length=100, verbose_name="اسم القالب")
    content = models.TextField(verbose_name="محتوى الرسالة")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "قالب واتساب"
        verbose_name_plural = "قوالب الواتساب"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class OTPVerificationLog(models.Model):
    PURPOSE_CHOICES = [
        ("register", "إنشاء حساب"),
        ("login", "تسجيل دخول"),
        ("reset_password", "استعادة كلمة المرور"),
    ]
    
    phone = models.CharField(max_length=40, verbose_name="رقم الهاتف")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="المستخدم")
    code = models.CharField(max_length=10, verbose_name="الرمز")
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, verbose_name="الغرض")
    is_verified = models.BooleanField(default=False, verbose_name="تم التحقق؟")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="عنوان IP")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="وقت الإرسال")
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name="وقت التحقق")

    class Meta:
        verbose_name = "سجل رمز التحقق"
        verbose_name_plural = "سجلات رموز التحقق"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.phone} - {self.get_purpose_display()}"
