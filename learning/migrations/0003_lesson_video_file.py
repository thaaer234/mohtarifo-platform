from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("learning", "0002_onlinelessonsession_lessonattendance"),
    ]

    operations = [
        migrations.AddField(
            model_name="lesson",
            name="video_file",
            field=models.FileField(blank=True, upload_to="protected/videos/"),
        ),
    ]
