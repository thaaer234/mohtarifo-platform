from django.conf import settings
from django.db import models


class Subject(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "مادة"
        verbose_name_plural = "المواد"

    def __str__(self):
        return self.name


class Course(models.Model):
    KIND_CHOICES = [
        ("intensive", "مكثفة"),
        ("curriculum", "منهاج"),
        ("semester", "فصل"),
        ("foundation", "تأسيس"),
        ("material", "مادة"),
        ("exam_camp", "معسكر امتحاني"),
    ]

    TRACK_CHOICES = [
        ("scientific", "علمي"),
        ("literary", "أدبي"),
        ("ninth", "تاسع"),
        ("general", "مشترك"),
    ]

    TERM_CHOICES = [
        ("full", "كامل"),
        ("first", "الفصل الأول"),
        ("second", "الفصل الثاني"),
        ("summer", "صيفي"),
    ]

    STATUS_CHOICES = [
        ("draft", "مسودة"),
        ("review", "قيد المراجعة"),
        ("published", "منشورة"),
        ("archived", "مؤرشفة"),
    ]

    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="courses")
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="courses")
    kind = models.CharField(max_length=24, choices=KIND_CHOICES, default="intensive")
    academic_track = models.CharField(max_length=24, choices=TRACK_CHOICES, default="scientific")
    term = models.CharField(max_length=24, choices=TERM_CHOICES, default="full")
    title = models.CharField(max_length=180)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    cover = models.ImageField(upload_to="courses/covers/", blank=True)
    teacher_photo = models.ImageField(upload_to="courses/teachers/", blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    price_cents = models.PositiveIntegerField(null=True, blank=True)
    is_subscription_included = models.BooleanField(default=True)
    discount_end_date = models.DateTimeField(null=True, blank=True, help_text="تاريخ انتهاء العرض (إن وجد)")
    students_enrolled = models.PositiveIntegerField(default=0, help_text="لغرض الدليل الاجتماعي (Social Proof)")
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=5.0)
    pdf_file = models.FileField(upload_to="courses/pdfs/", blank=True, null=True, help_text="ملف الـ PDF الخاص بالدورة كاملة")
    allow_pdf_download = models.BooleanField(default=False, help_text="هل يسمح للطالب بتنزيل ملف الـ PDF؟")
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "دورة"
        verbose_name_plural = "الدورات"
        indexes = [
            models.Index(fields=["subject", "status"]),
            models.Index(fields=["kind", "academic_track", "status"]),
        ]

    def __str__(self):
        instructor = self.instructor.get_full_name() or self.instructor.username
        return f"{self.title} - {instructor}"

    @property
    def instructor_cover_static_path(self):
        from django.contrib.staticfiles import finders
        instructor_name = (self.instructor.get_full_name() or self.instructor.username).strip()
        target_path = f"dashboard/course-covers/{instructor_name}.png"
        # Safely check if file actually exists in static collections BEFORE generating static URL
        # to prevent CompressedManifestStaticFilesStorage from crashing with ValueError.
        if finders.find(target_path):
            return target_path
        return "dashboard/course-covers/default_cover.png"

    @property
    def price_display(self):
        if not self.price_cents:
            return ""
        amount = self.price_cents / 100
        if amount.is_integer():
            return f"{int(amount):,}"
        return f"{amount:,.2f}"

    @property
    def total_lessons_count(self):
        return sum(unit.lessons.count() for unit in self.units.all())


class Unit(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="units")
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "وحدة"
        verbose_name_plural = "الوحدات"
        ordering = ["course", "sort_order"]
        indexes = [models.Index(fields=["course", "sort_order"])]

    def __str__(self):
        return f"{self.course.title} - {self.title}"

    @property
    def total_duration(self):
        total_seconds = sum(lesson.duration_seconds or 0 for lesson in self.lessons.all())
        if not total_seconds:
            return ""
        minutes = total_seconds // 60
        if minutes >= 60:
            hours = minutes // 60
            minutes = minutes % 60
            if minutes:
                return f"{hours} ساعة و {minutes} دقيقة"
            return f"{hours} ساعة"
        return f"{minutes} دقيقة"


class Lesson(models.Model):
    TYPE_CHOICES = [
        ("video", "فيديو"),
        ("pdf", "ملف PDF"),
        ("quiz", "اختبار"),
        ("mixed", "مختلط"),
    ]

    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    lesson_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="video")
    video_url = models.URLField(blank=True)
    video_file = models.FileField(upload_to="protected/videos/", blank=True)
    pdf_file = models.FileField(upload_to="lessons/pdfs/", blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    is_free_preview = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "درس"
        verbose_name_plural = "الدروس"
        ordering = ["unit", "sort_order"]
        indexes = [models.Index(fields=["unit", "sort_order"])]

    def __str__(self):
        return self.title

    @property
    def duration(self):
        if not self.duration_seconds:
            return ""
        minutes = self.duration_seconds // 60
        seconds = self.duration_seconds % 60
        if minutes >= 60:
            hours = minutes // 60
            minutes = minutes % 60
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    def save(self, *args, **kwargs):
        if self.lesson_type == "video" and self.video_url and not self.duration_seconds:
            fetched_duration = fetch_bunny_video_duration(self.video_url)
            if fetched_duration:
                self.duration_seconds = fetched_duration
        super().save(*args, **kwargs)


def fetch_bunny_video_duration(video_url):
    import os
    import requests
    from urllib.parse import urlparse
    
    api_key = os.environ.get("BUNNY_STREAM_API_KEY", "").strip() or os.environ.get("BUNNY_STREAM_TOKEN_KEY", "").strip()
    if not api_key or "mediadelivery.net" not in video_url:
        return None
        
    try:
        parsed = urlparse(video_url)
        path_parts = [p for p in parsed.path.split("/") if p]
        library_id = ""
        video_id = ""
        
        # Paths can be: /play/library_id/video_id or /embed/library_id/video_id
        if len(path_parts) >= 3:
            library_id = path_parts[1]
            video_id = path_parts[2]
        elif len(path_parts) == 2:
            library_id = path_parts[0]
            video_id = path_parts[1]
            
        if library_id and video_id:
            url = f"https://video.bunnycdn.com/library/{library_id}/videos/{video_id}"
            headers = {
                "accept": "application/json",
                "AccessKey": api_key
            }
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get("length")  # length is in seconds
            else:
                print(f"Bunny API returned status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Error fetching Bunny video duration: {e}")
    return None



class Topic(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="topics")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="topics", null=True, blank=True)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="topics", null=True, blank=True)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="topics", null=True, blank=True)
    name = models.CharField(max_length=140)
    slug = models.SlugField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "موضوع"
        verbose_name_plural = "الموضوعات"
        unique_together = [("subject", "slug")]

    def __str__(self):
        return self.name


class LessonProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lesson_progress")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="progress")
    watched_seconds = models.PositiveIntegerField(default=0)
    last_position_seconds = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "تقدم درس"
        verbose_name_plural = "تقدم الدروس"
        unique_together = [("user", "lesson")]


class CourseProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="course_progress")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="progress")
    completion_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    completed_lessons = models.PositiveIntegerField(default=0)
    total_lessons = models.PositiveIntegerField(default=0)
    last_activity_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "تقدم دورة"
        verbose_name_plural = "تقدم الدورات"
        unique_together = [("user", "course")]

class OnlineLessonSession(models.Model):
    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("live", "Live"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="online_sessions")
    title = models.CharField(max_length=180)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    meeting_url = models.URLField(blank=True)
    recording_url = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="scheduled")
    capacity = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "جلسة درس أونلاين"
        verbose_name_plural = "جلسات الدروس الأونلاين"
        ordering = ["starts_at"]

    def __str__(self):
        return self.title


class LessonAttendance(models.Model):
    STATUS_CHOICES = [
        ("registered", "Registered"),
        ("attended", "Attended"),
        ("missed", "Missed"),
        ("excused", "Excused"),
    ]

    session = models.ForeignKey(OnlineLessonSession, on_delete=models.CASCADE, related_name="attendances")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lesson_attendances")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="registered")
    joined_at = models.DateTimeField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True)
    watched_recording = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "حضور طالب"
        verbose_name_plural = "حضور الطلاب"
        unique_together = [("session", "user")]

    def __str__(self):
        return f"{self.user} - {self.session}"

class Certificate(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="certificates")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="certificates")
    certificate_id = models.CharField(max_length=50, unique=True, blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "شهادة"
        verbose_name_plural = "الشهادات"
        unique_together = [("user", "course")]

    def save(self, *args, **kwargs):
        if not self.certificate_id:
            import uuid
            self.certificate_id = str(uuid.uuid4()).split('-')[0].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"شهادة: {self.user.get_full_name()} - {self.course.title}"
