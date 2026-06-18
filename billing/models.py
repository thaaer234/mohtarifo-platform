from django.conf import settings
from django.db import models
from django.utils import timezone

from learning.models import Course, Lesson


class Institute(models.Model):
    name = models.CharField(max_length=160, unique=True)
    contact_name = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    logo = models.ImageField(upload_to="institutes/logos/", null=True, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "معهد"
        verbose_name_plural = "المعاهد"
        ordering = ["name"]

    def __str__(self):
        return self.name


class SalesCenter(models.Model):
    name = models.CharField(max_length=160)
    institute = models.ForeignKey(Institute, on_delete=models.SET_NULL, related_name="sales_centers", null=True, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    address = models.CharField(max_length=255, blank=True)
    
    # Collection tracking fields
    collected_amount_syp = models.PositiveIntegerField(default=0, verbose_name="المبالغ المحصلة (ل.س)")
    is_settled = models.BooleanField(default=False, verbose_name="تمت التسوية")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "مركز بيع"
        verbose_name_plural = "مراكز البيع"
        ordering = ["name"]

    def __str__(self):
        return self.name


class AccessCodeBatch(models.Model):
    name = models.CharField(max_length=160)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="code_batches", null=True, blank=True)
    package = models.ForeignKey("CoursePackage", on_delete=models.CASCADE, related_name="code_batches", null=True, blank=True)
    institute = models.ForeignKey(Institute, on_delete=models.SET_NULL, related_name="code_batches", null=True, blank=True)
    sales_center = models.ForeignKey(SalesCenter, on_delete=models.SET_NULL, related_name="code_batches", null=True, blank=True)
    allocated_count = models.PositiveIntegerField(default=0)
    free_count = models.PositiveIntegerField(default=0)
    code_prefix = models.CharField(max_length=24, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "دفعة أكواد"
        verbose_name_plural = "دفعات الأكواد"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def target_title(self):
        if self.course:
            return self.course.title
        if self.package:
            return self.package.name
        return self.name

    @property
    def redeemed_count(self):
        return self.codes.filter(redeemed_count__gt=0).count()

    @property
    def sold_count(self):
        return self.codes.filter(sale_status="sold").count()


class AccessCodePrintLog(models.Model):
    batch = models.ForeignKey(AccessCodeBatch, on_delete=models.CASCADE, related_name="print_logs")
    printed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="access_code_prints", null=True, blank=True)
    cards_count = models.PositiveIntegerField(default=0)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "سجل طباعة أكواد"
        verbose_name_plural = "سجلات طباعة الأكواد"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.batch} - {self.cards_count}"


class Plan(models.Model):
    name = models.CharField(max_length=120)
    code = models.SlugField(unique=True)
    billing_period = models.CharField(max_length=40)
    price_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=10, default="USD")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "خطة اشتراك"
        verbose_name_plural = "خطط الاشتراك"

    def __str__(self):
        return self.name


class Subscription(models.Model):
    STATUS_CHOICES = [
        ("active", "نشط"),
        ("past_due", "متأخر"),
        ("canceled", "ملغى"),
        ("expired", "منتهي"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    provider = models.CharField(max_length=40, default="stripe")
    provider_subscription_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    starts_at = models.DateTimeField()
    renews_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "اشتراك"
        verbose_name_plural = "الاشتراكات"


class Payment(models.Model):
    STATUS_CHOICES = [
        ("pending", "قيد الانتظار"),
        ("paid", "مدفوع"),
        ("failed", "فشل"),
        ("refunded", "مسترد"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments")
    provider = models.CharField(max_length=40, default="stripe")
    provider_payment_id = models.CharField(max_length=255, blank=True)
    amount_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=10, default="USD")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "دفعة"
        verbose_name_plural = "الدفعات"


class CoursePurchase(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="course_purchases")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="purchases")
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "شراء مادة"
        verbose_name_plural = "مشتريات المواد"
        unique_together = [("user", "course")]


class Coupon(models.Model):
    code = models.CharField(max_length=80, unique=True)
    discount_percent = models.PositiveIntegerField(null=True, blank=True)
    discount_cents = models.PositiveIntegerField(null=True, blank=True)
    max_redemptions = models.PositiveIntegerField(null=True, blank=True)
    redeemed_count = models.PositiveIntegerField(default=0)
    starts_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "كوبون"
        verbose_name_plural = "الكوبونات"

    def __str__(self):
        return self.code


class CoursePackage(models.Model):
    TRACK_CHOICES = [
        ("custom", "مخصصة"),
        ("scientific", "علمي"),
        ("literary", "أدبي"),
        ("ninth", "تاسع"),
    ]

    name = models.CharField(max_length=160)
    code = models.SlugField(unique=True)
    package_track = models.CharField(max_length=24, choices=TRACK_CHOICES, default="custom")
    auto_include_shared = models.BooleanField(default=True)
    courses = models.ManyToManyField(Course, related_name="billing_packages")
    price_cents = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "باقة دورات"
        verbose_name_plural = "باقات الدورات"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def eligible_courses_queryset(self):
        courses = Course.objects.filter(status="published")
        if self.package_track == "custom":
            return self.courses.filter(status="published")
        if self.package_track in {"scientific", "literary"} and self.auto_include_shared:
            return courses.filter(models.Q(academic_track=self.package_track) | models.Q(academic_track="general"))
        return courses.filter(academic_track=self.package_track)


class AccessCode(models.Model):
    ACCESS_TYPE_CHOICES = [
        ("course", "Course"),
        ("lesson", "Lesson"),
        ("subscription", "Subscription"),
        ("package", "Package"),
    ]
    STATUS_CHOICES = [
        ("active", "Active"),
        ("disabled", "Disabled"),
        ("expired", "Expired"),
    ]
    SALE_STATUS_CHOICES = [
        ("available", "Available"),
        ("reserved", "Reserved"),
        ("sold", "Sold"),
        ("free", "Free"),
    ]

    code = models.CharField(max_length=80, unique=True)
    access_type = models.CharField(max_length=20, choices=ACCESS_TYPE_CHOICES, default="course")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="access_codes", null=True, blank=True)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="access_codes", null=True, blank=True)
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, related_name="access_codes", null=True, blank=True)
    package = models.ForeignKey(CoursePackage, on_delete=models.SET_NULL, related_name="access_codes", null=True, blank=True)
    batch = models.ForeignKey(AccessCodeBatch, on_delete=models.SET_NULL, related_name="codes", null=True, blank=True)
    institute = models.ForeignKey(Institute, on_delete=models.SET_NULL, related_name="access_codes", null=True, blank=True)
    sales_center = models.ForeignKey(SalesCenter, on_delete=models.SET_NULL, related_name="access_codes", null=True, blank=True)
    assigned_student_name = models.CharField(max_length=160, blank=True)
    assigned_student_phone = models.CharField(max_length=40, blank=True)
    sale_status = models.CharField(max_length=20, choices=SALE_STATUS_CHOICES, default="available")
    sold_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="sold_access_codes", null=True, blank=True)
    sold_at = models.DateTimeField(null=True, blank=True)
    sold_price_cents = models.PositiveIntegerField(null=True, blank=True)
    price_reason = models.CharField(max_length=255, blank=True)
    is_free_code = models.BooleanField(default=False)
    max_redemptions = models.PositiveIntegerField(default=1)
    redeemed_count = models.PositiveIntegerField(default=0)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "كود وصول"
        verbose_name_plural = "أكواد الوصول"

    def __str__(self):
        return self.code

    def is_redeemable(self, now):
        if self.status != "active":
            return False, "الكود غير نشط."
        if self.valid_from and now < self.valid_from:
            return False, "الكود غير متاح بعد."
        if self.valid_until and now > self.valid_until:
            return False, "انتهت صلاحية الكود."
        if self.redeemed_count >= self.max_redemptions:
            return False, "تم استخدام الكود بالكامل."
        return True, ""


class AccessGrant(models.Model):
    SOURCE_CHOICES = [
        ("code", "Code"),
        ("purchase", "Purchase"),
        ("admin", "Admin"),
        ("subscription", "Subscription"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="access_grants")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="access_grants", null=True, blank=True)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="access_grants", null=True, blank=True)
    access_code = models.ForeignKey(AccessCode, on_delete=models.SET_NULL, related_name="grants", null=True, blank=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="code")
    device_fingerprint = models.CharField(max_length=128, blank=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    print_password = models.CharField(max_length=40, blank=True, verbose_name="كلمة مرور الطباعة")
    print_quota = models.PositiveIntegerField(default=2, verbose_name="الحد الأقصى للطباعة")
    main_pdf_printed = models.PositiveIntegerField(default=0, verbose_name="مرات طباعة ملف المادة")
    file1_printed = models.PositiveIntegerField(default=0, verbose_name="مرات طباعة الملف الإضافي 1")
    file2_printed = models.PositiveIntegerField(default=0, verbose_name="مرات طباعة الملف الإضافي 2")

    class Meta:
        verbose_name = "صلاحية وصول"
        verbose_name_plural = "صلاحيات الوصول"
        constraints = [
            models.UniqueConstraint(fields=["user", "course", "lesson"], name="unique_user_course_lesson_access")
        ]

    def __str__(self):
        target = self.course or self.lesson
        return f"{self.user} -> {target}"

    @property
    def print_remaining(self):
        return max(0, self.print_quota - self.main_pdf_printed)

    @property
    def file1_remaining(self):
        return max(0, self.print_quota - self.file1_printed)

    @property
    def file2_remaining(self):
        return max(0, self.print_quota - self.file2_printed)

    view_counter = models.PositiveIntegerField(default=0, verbose_name="عدد مرات فتح PDF")

    def save(self, *args, **kwargs):
        if not self.print_password:
            import random
            import string
            self.print_password = "".join(random.choices(string.digits, k=6))
        super().save(*args, **kwargs)


class UserDevice(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="devices")
    fingerprint = models.CharField(max_length=128)
    label = models.CharField(max_length=120, blank=True)
    user_agent = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "جهاز طالب"
        verbose_name_plural = "أجهزة الطلاب"
        unique_together = [("user", "fingerprint")]

    def __str__(self):
        return f"{self.user} - {self.label or self.fingerprint[:12]}"


class DiscountRule(models.Model):
    TRACK_CHOICES = [
        ("all", "كافة الفروع"),
        ("scientific", "علمي"),
        ("literary", "أدبي"),
        ("ninth", "تاسع"),
        ("general", "مشترك"),
    ]
    name = models.CharField(max_length=160, verbose_name="اسم الحسم")
    starts_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ البدء")
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الانتهاء")
    discount_percent = models.PositiveIntegerField(default=0, verbose_name="نسبة الحسم (%)")
    discount_amount_syp = models.PositiveIntegerField(default=0, verbose_name="قيمة الحسم بالليرة (ل.س)")
    academic_track = models.CharField(max_length=24, choices=TRACK_CHOICES, default="all", verbose_name="الفرع المستهدف")
    is_active = models.BooleanField(default=True, verbose_name="نشط")

    class Meta:
        verbose_name = "قاعدة حسم"
        verbose_name_plural = "قواعد الحسومات"
        ordering = ["-id"]

    def __str__(self):
        if self.discount_amount_syp > 0:
            return f"{self.name} ({self.discount_amount_syp} ل.س)"
        return f"{self.name} ({self.discount_percent}%)"


class BillingSetting(models.Model):
    name = models.CharField(max_length=80, unique=True, verbose_name="اسم الإعداد")
    key = models.CharField(max_length=80, unique=True, verbose_name="مفتاح الإعداد")
    value_numeric = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, verbose_name="القيمة العددية")
    label = models.CharField(max_length=120, blank=True, verbose_name="العنوان بالعربي")

    class Meta:
        verbose_name = "إعداد مالي"
        verbose_name_plural = "الإعدادات المالية"

    def __str__(self):
        return f"{self.label or self.name}: {self.value_numeric}"


class PlatformExpense(models.Model):
    title = models.CharField(max_length=255, verbose_name="عنوان المصروف")
    amount_syp = models.PositiveIntegerField(default=0, verbose_name="المبلغ بالليرة السورية")
    amount_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, verbose_name="المبلغ بالدولار")
    course = models.ForeignKey(
        'learning.Course', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="platform_expenses", 
        verbose_name="الدورة المرتبطة"
    )
    expense_type = models.CharField(
        max_length=20, 
        choices=[('general', 'عام'), ('printing', 'طباعة')], 
        default='general', 
        verbose_name="نوع المصروف"
    )
    status = models.CharField(
        max_length=20, 
        choices=[('pending', 'قيد الانتظار / لم يدفع'), ('paid', 'تم الصرف / مخرّج')], 
        default='paid', 
        verbose_name="حالة المصروف"
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name="تاريخ التسجيل")

    class Meta:
        verbose_name = "مصروف تشغيلي"
        verbose_name_plural = "المصاريف التشغيلية"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title}: {self.amount_syp} ل.س / {self.amount_usd} $"

