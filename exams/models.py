from django.conf import settings
from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from learning.models import Course, Lesson, Topic, Unit


class Question(models.Model):
    TYPE_CHOICES = [
        ("mcq", "اختيار من متعدد"),
        ("true_false", "صح / خطأ"),
    ]
    DIFFICULTY_CHOICES = [
        ("easy", "سهل"),
        ("medium", "متوسط"),
        ("hard", "صعب"),
    ]
    STATUS_CHOICES = [
        ("draft", "مسودة"),
        ("published", "منشور"),
        ("archived", "مؤرشف"),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="questions", null=True, blank=True)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="questions", null=True, blank=True)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="questions", null=True, blank=True)
    topic = models.ForeignKey(Topic, on_delete=models.PROTECT, related_name="questions")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="questions")
    question_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="mcq")
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default="medium")
    body = models.TextField()
    explanation = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "سؤال"
        verbose_name_plural = "بنك الأسئلة"
        indexes = [models.Index(fields=["topic", "difficulty", "question_type"])]

    def __str__(self):
        return self.body[:80]


class QuestionOption(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    body = models.TextField()
    is_correct = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "خيار سؤال"
        verbose_name_plural = "خيارات الأسئلة"
        ordering = ["sort_order"]

    def __str__(self):
        return self.body[:80]


class Exam(models.Model):
    MODE_CHOICES = [
        ("fixed", "ثابت"),
        ("random", "عشوائي"),
    ]
    STATUS_CHOICES = [
        ("draft", "مسودة"),
        ("published", "منشور"),
        ("archived", "مؤرشف"),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="exams")
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="exams", null=True, blank=True)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="exams", null=True, blank=True)
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default="fixed")
    duration_minutes = models.PositiveIntegerField(default=20)
    question_count = models.PositiveIntegerField(default=10)
    shuffle_questions = models.BooleanField(default=True)
    shuffle_options = models.BooleanField(default=True)
    show_solutions_after_submit = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    questions = models.ManyToManyField(Question, through="ExamQuestion", related_name="exams")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "امتحان"
        verbose_name_plural = "الامتحانات"

    def __str__(self):
        return self.title


class ExamQuestion(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="exam_questions")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="exam_questions")
    points = models.PositiveIntegerField(default=1)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "سؤال امتحان"
        verbose_name_plural = "أسئلة الامتحانات"
        ordering = ["sort_order"]


class Attempt(models.Model):
    STATUS_CHOICES = [
        ("in_progress", "قيد الحل"),
        ("submitted", "مسلّم"),
        ("expired", "منتهي"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attempts")
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="attempts")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="in_progress")
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    score = models.PositiveIntegerField(default=0)
    max_score = models.PositiveIntegerField(default=0)
    accuracy = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    total_time_seconds = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "محاولة"
        verbose_name_plural = "محاولات الامتحانات"
        indexes = [models.Index(fields=["user", "exam", "created_at"])]

    def __str__(self):
        return f"{self.user} - {self.exam}"

    @property
    def score_percentage(self):
        if self.accuracy is not None:
            return float(self.accuracy)
        if self.max_score > 0:
            return (self.score / self.max_score) * 100
        return 0



class AttemptAnswer(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name="attempt_answers")
    selected_option = models.ForeignKey(QuestionOption, on_delete=models.PROTECT, null=True, blank=True)
    selected_value = models.CharField(max_length=255, blank=True)
    is_correct = models.BooleanField(default=False)
    time_seconds = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "إجابة محاولة"
        verbose_name_plural = "إجابات المحاولات"

# Create your models here.
