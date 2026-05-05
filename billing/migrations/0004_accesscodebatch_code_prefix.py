from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0003_institute_salescenter_codebatch_userdevice"),
    ]

    operations = [
        migrations.AddField(
            model_name="accesscodebatch",
            name="code_prefix",
            field=models.CharField(blank=True, max_length=24),
        ),
    ]
