from django.conf import settings
from django.db import models


class AcademicBranch(models.Model):
    name = models.CharField(max_length=80, unique=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "فرع دراسي"
        verbose_name_plural = "الفروع الدراسية"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Governorate(models.Model):
    name = models.CharField(max_length=80, unique=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "محافظة"
        verbose_name_plural = "المحافظات"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class StudentProfile(models.Model):
    GENDER_CHOICES = [
        ("male", "ذكر"),
        ("female", "أنثى"),
        ("unknown", "غير محدد"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_profile")
    grade = models.CharField(max_length=80, default="الثالث الثانوي")
    track = models.CharField(max_length=80, blank=True)
    governorate = models.CharField(max_length=80, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default="unknown", verbose_name="الجنس")
    target_exam_date = models.DateField(null=True, blank=True)
    current_level = models.CharField(max_length=80, blank=True)
    xp = models.PositiveIntegerField(default=0)
    level = models.PositiveIntegerField(default=1)
    streak_days = models.PositiveIntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to="students/avatars/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "ملف طالب"
        verbose_name_plural = "ملفات الطلاب"

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - طالب"


class InstructorProfile(models.Model):
    STATUS_CHOICES = [
        ("pending", "قيد المراجعة"),
        ("active", "نشط"),
        ("suspended", "موقوف"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="instructor_profile")
    phone = models.CharField(max_length=40, blank=True, verbose_name="رقم الهاتف")
    national_id = models.CharField(max_length=40, blank=True, unique=True, null=True, verbose_name="رقم الهوية")
    specialty = models.CharField(max_length=120)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to="instructors/avatars/", blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    force_password_change = models.BooleanField(default=True, verbose_name="إجبار تغيير كلمة المرور", help_text="إذا كان صحيحاً، سيطلب من المدرس تغيير كلمة المرور عند أول دخول")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "ملف مدرس"
        verbose_name_plural = "ملفات المدرسين"

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.specialty}"

# Create your models here.
