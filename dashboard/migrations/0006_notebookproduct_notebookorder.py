from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("dashboard", "0005_whatsappmessagelog"),
        ("learning", "0014_course_custom_expense_syp_course_hosting_months_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="NotebookProduct",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180, verbose_name="اسم النوطة")),
                ("description", models.TextField(blank=True, verbose_name="الوصف")),
                ("cover", models.ImageField(blank=True, null=True, upload_to="notebooks/covers/", verbose_name="صورة الغلاف")),
                ("price_syp", models.PositiveIntegerField(verbose_name="السعر بالليرة السورية")),
                ("pages_count", models.PositiveIntegerField(default=0, verbose_name="عدد الصفحات")),
                ("stock", models.PositiveIntegerField(default=0, verbose_name="المخزون")),
                ("is_active", models.BooleanField(default=True, verbose_name="متاحة في السوق")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("course", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="notebook_products", to="learning.course", verbose_name="الدورة المرتبطة")),
                ("instructor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="notebook_products", to=settings.AUTH_USER_MODEL, verbose_name="المدرس")),
            ],
            options={"verbose_name": "نوطة", "verbose_name_plural": "سوق النوط", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="NotebookOrder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("recipient_name", models.CharField(max_length=160, verbose_name="اسم المستلم")),
                ("phone", models.CharField(max_length=40, verbose_name="رقم الهاتف")),
                ("governorate", models.CharField(max_length=80, verbose_name="المحافظة")),
                ("address", models.TextField(verbose_name="العنوان التفصيلي")),
                ("location_latitude", models.DecimalField(decimal_places=6, max_digits=9, verbose_name="خط العرض")),
                ("location_longitude", models.DecimalField(decimal_places=6, max_digits=9, verbose_name="خط الطول")),
                ("quantity", models.PositiveIntegerField(default=1, verbose_name="الكمية")),
                ("unit_price_syp", models.PositiveIntegerField(verbose_name="سعر الوحدة عند الطلب")),
                ("status", models.CharField(choices=[("pending", "بانتظار التأكيد"), ("confirmed", "تم التأكيد"), ("preparing", "قيد التجهيز"), ("out_for_delivery", "خرجت للتوصيل"), ("delivered", "تم التسليم"), ("cancelled", "ملغى")], default="pending", max_length=24, verbose_name="حالة الطلب")),
                ("delivery_scheduled_at", models.DateTimeField(blank=True, null=True, verbose_name="موعد التسليم المحدد من المنصة")),
                ("admin_notes", models.TextField(blank=True, verbose_name="ملاحظات الإدارة")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="orders", to="dashboard.notebookproduct", verbose_name="النوطة")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="notebook_orders", to=settings.AUTH_USER_MODEL, verbose_name="الطالب")),
            ],
            options={"verbose_name": "طلب نوطة", "verbose_name_plural": "طلبات توصيل النوط", "ordering": ["-created_at"]},
        ),
    ]
