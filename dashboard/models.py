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


class WhatsAppMessageLog(models.Model):
    phone = models.CharField(max_length=40, db_index=True, verbose_name="رقم الهاتف")
    raw_text_hash = models.CharField(max_length=64, db_index=True, blank=True, null=True, verbose_name="هاش النص الخام")
    sent_text = models.TextField(verbose_name="النص المرسل")
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name="وقت الإرسال")

    class Meta:
        verbose_name = "سجل إرسال واتساب"
        verbose_name_plural = "سجلات إرسال الواتساب"
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.phone} - {self.sent_at.strftime('%Y-%m-%d %H:%M')}"


class NotebookProduct(models.Model):
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="notebook_products",
        verbose_name="المدرس",
    )
    course = models.ForeignKey(
        "learning.Course",
        on_delete=models.SET_NULL,
        related_name="notebook_products",
        null=True,
        blank=True,
        verbose_name="الدورة المرتبطة",
    )
    title = models.CharField(max_length=180, verbose_name="اسم النوطة")
    description = models.TextField(blank=True, verbose_name="الوصف")
    material_summary = models.TextField(blank=True, verbose_name="شرح وملخص المادة ومحتوياتها")
    free_quizzes_overview = models.TextField(blank=True, verbose_name="الاختبارات والأسئلة المجانية الملحقة بالنوطة")
    cover = models.ImageField(upload_to="notebooks/covers/", blank=True, null=True, verbose_name="صورة الغلاف")
    price_syp = models.PositiveIntegerField(verbose_name="السعر بالليرة السورية")
    pages_count = models.PositiveIntegerField(default=0, verbose_name="عدد الصفحات")
    stock = models.PositiveIntegerField(default=0, verbose_name="المخزون")
    is_active = models.BooleanField(default=True, verbose_name="متاحة في السوق")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "نوطة"
        verbose_name_plural = "سوق النوط"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def is_available(self):
        return self.is_active and self.stock > 0


class NotebookOrder(models.Model):
    STATUS_CHOICES = [
        ("pending", "بانتظار التأكيد"),
        ("confirmed", "تم التأكيد"),
        ("preparing", "قيد التجهيز"),
        ("out_for_delivery", "خرجت للتوصيل"),
        ("delivered", "تم التسليم"),
        ("cancelled", "ملغى"),
    ]

    product = models.ForeignKey(NotebookProduct, on_delete=models.PROTECT, related_name="orders", verbose_name="النوطة")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="notebook_orders", verbose_name="الطالب")
    recipient_name = models.CharField(max_length=160, verbose_name="اسم المستلم")
    phone = models.CharField(max_length=40, verbose_name="رقم الهاتف")
    governorate = models.CharField(max_length=80, verbose_name="المحافظة")
    address = models.TextField(verbose_name="العنوان التفصيلي")
    location_latitude = models.DecimalField(max_digits=9, decimal_places=6, verbose_name="خط العرض")
    location_longitude = models.DecimalField(max_digits=9, decimal_places=6, verbose_name="خط الطول")
    quantity = models.PositiveIntegerField(default=1, verbose_name="الكمية")
    unit_price_syp = models.PositiveIntegerField(verbose_name="سعر الوحدة عند الطلب")
    PAYMENT_METHOD_CHOICES = [
        ("cod", "الدفع عند الاستلام"),
        ("shamcash", "شام كاش (Sham Cash)"),
    ]

    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default="cod", verbose_name="طريقة الدفع")
    payment_reference = models.CharField(max_length=120, blank=True, verbose_name="مرجع الدفع أو رقم الحوالة")
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default="pending", verbose_name="حالة الطلب")
    delivery_scheduled_at = models.DateTimeField(null=True, blank=True, verbose_name="موعد التسليم المحدد من المنصة")
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_notebook_deliveries",
        verbose_name="مندوب التوصيل المكلف"
    )
    driver_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="خط عرض السائق اللحظي")
    driver_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="خط طول السائق اللحظي")
    driver_heading = models.FloatField(null=True, blank=True, verbose_name="زاوية اتجاه السائق (Heading)")
    driver_speed = models.FloatField(null=True, blank=True, verbose_name="سرعة السائق (كم/سا)")
    driver_updated_at = models.DateTimeField(null=True, blank=True, verbose_name="وقت آخر تحديث لإحداثيات السائق")
    admin_notes = models.TextField(blank=True, verbose_name="ملاحظات الإدارة")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "طلب نوطة"
        verbose_name_plural = "طلبات توصيل النوط"
        ordering = ["-created_at"]

    def __str__(self):
        return f"طلب #{self.pk} - {self.product.title}"

    @property
    def total_syp(self):
        return self.unit_price_syp * self.quantity

    @property
    def maps_url(self):
        return f"https://www.google.com/maps?q={self.location_latitude},{self.location_longitude}"
