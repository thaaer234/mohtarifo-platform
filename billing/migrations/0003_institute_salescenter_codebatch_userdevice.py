from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("learning", "0002_onlinelessonsession_lessonattendance"),
        ("billing", "0002_accesscode_accessgrant"),
    ]

    operations = [
        migrations.CreateModel(
            name="Institute",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160, unique=True)),
                ("contact_name", models.CharField(blank=True, max_length=120)),
                ("phone", models.CharField(blank=True, max_length=40)),
                ("notes", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "معهد",
                "verbose_name_plural": "المعاهد",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="SalesCenter",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160)),
                ("phone", models.CharField(blank=True, max_length=40)),
                ("address", models.CharField(blank=True, max_length=255)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("institute", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sales_centers", to="billing.institute")),
            ],
            options={
                "verbose_name": "مركز بيع",
                "verbose_name_plural": "مراكز البيع",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="AccessCodeBatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160)),
                ("allocated_count", models.PositiveIntegerField(default=0)),
                ("free_count", models.PositiveIntegerField(default=0)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="code_batches", to="learning.course")),
                ("institute", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="code_batches", to="billing.institute")),
                ("sales_center", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="code_batches", to="billing.salescenter")),
            ],
            options={
                "verbose_name": "دفعة أكواد",
                "verbose_name_plural": "دفعات الأكواد",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="UserDevice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fingerprint", models.CharField(max_length=128)),
                ("label", models.CharField(blank=True, max_length=120)),
                ("user_agent", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("first_seen_at", models.DateTimeField(auto_now_add=True)),
                ("last_seen_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="devices", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "جهاز طالب",
                "verbose_name_plural": "أجهزة الطلاب",
                "unique_together": {("user", "fingerprint")},
            },
        ),
        migrations.AddField(
            model_name="accesscode",
            name="assigned_student_name",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="accesscode",
            name="assigned_student_phone",
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AddField(
            model_name="accesscode",
            name="batch",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="codes", to="billing.accesscodebatch"),
        ),
        migrations.AddField(
            model_name="accesscode",
            name="institute",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="access_codes", to="billing.institute"),
        ),
        migrations.AddField(
            model_name="accesscode",
            name="is_free_code",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="accesscode",
            name="sale_status",
            field=models.CharField(choices=[("available", "Available"), ("reserved", "Reserved"), ("sold", "Sold"), ("free", "Free")], default="available", max_length=20),
        ),
        migrations.AddField(
            model_name="accesscode",
            name="sales_center",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="access_codes", to="billing.salescenter"),
        ),
        migrations.AddField(
            model_name="accessgrant",
            name="device_fingerprint",
            field=models.CharField(blank=True, max_length=128),
        ),
    ]
