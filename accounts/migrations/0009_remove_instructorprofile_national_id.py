import re

from django.db import migrations


def sync_instructor_phones(apps, schema_editor):
    InstructorProfile = apps.get_model("accounts", "InstructorProfile")
    phone_re = re.compile(r"^09\d{8}$")
    for profile in InstructorProfile.objects.select_related("user").iterator():
        user = profile.user
        digits = re.sub(r"\D", "", profile.phone or "")
        if phone_re.fullmatch(digits):
            if profile.phone != digits:
                profile.phone = digits
                profile.save(update_fields=["phone"])
            continue
        username_digits = re.sub(r"\D", "", user.username or "")
        if phone_re.fullmatch(username_digits):
            profile.phone = username_digits
            profile.save(update_fields=["phone"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0008_instructorprofile_phone_national_id_force_password"),
    ]

    operations = [
        migrations.RunPython(sync_instructor_phones, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="instructorprofile",
            name="national_id",
        ),
    ]
