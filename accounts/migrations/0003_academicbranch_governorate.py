from django.db import migrations, models


def seed_options(apps, schema_editor):
    AcademicBranch = apps.get_model("accounts", "AcademicBranch")
    Governorate = apps.get_model("accounts", "Governorate")
    branches = [
        "بكالوريا علمي",
        "بكالوريا أدبي",
        "بكالوريا تجارة",
        "بكالوريا شرعي",
        "تاسع",
    ]
    governorates = [
        "دمشق",
        "ريف دمشق",
        "حلب",
        "حمص",
        "حماة",
        "اللاذقية",
        "طرطوس",
        "إدلب",
        "درعا",
        "السويداء",
        "القنيطرة",
        "دير الزور",
        "الرقة",
        "الحسكة",
    ]
    for index, name in enumerate(branches, start=1):
        AcademicBranch.objects.get_or_create(name=name, defaults={"sort_order": index})
    for index, name in enumerate(governorates, start=1):
        Governorate.objects.get_or_create(name=name, defaults={"sort_order": index})


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_studentprofile_governorate_phone"),
    ]

    operations = [
        migrations.CreateModel(
            name="AcademicBranch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=80, unique=True)),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
            ],
            options={
                "verbose_name": "فرع دراسي",
                "verbose_name_plural": "الفروع الدراسية",
                "ordering": ["sort_order", "name"],
            },
        ),
        migrations.CreateModel(
            name="Governorate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=80, unique=True)),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
            ],
            options={
                "verbose_name": "محافظة",
                "verbose_name_plural": "المحافظات",
                "ordering": ["sort_order", "name"],
            },
        ),
        migrations.RunPython(seed_options, migrations.RunPython.noop),
    ]
