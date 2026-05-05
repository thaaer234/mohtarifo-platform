from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="studentprofile",
            name="governorate",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="studentprofile",
            name="phone",
            field=models.CharField(blank=True, max_length=40),
        ),
    ]
