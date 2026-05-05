# Generated manually to add the Certificate model that already exists in learning.models.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("learning", "0005_course_discount_end_date_course_rating_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Certificate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("certificate_id", models.CharField(blank=True, max_length=50, unique=True)),
                ("issued_at", models.DateTimeField(auto_now_add=True)),
                (
                    "course",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="certificates", to="learning.course"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="certificates", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "verbose_name": "ط´ظ‡ط§ط¯ط©",
                "verbose_name_plural": "ط§ظ„ط´ظ‡ط§ط¯ط§طھ",
                "unique_together": {("user", "course")},
            },
        ),
    ]
