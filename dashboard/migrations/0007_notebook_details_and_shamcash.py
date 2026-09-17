from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("dashboard", "0006_notebookproduct_notebookorder"),
    ]

    operations = [
        migrations.AddField(
            model_name="notebookproduct",
            name="material_summary",
            field=models.TextField(blank=True, verbose_name="شرح وملخص المادة ومحتوياتها"),
        ),
        migrations.AddField(
            model_name="notebookproduct",
            name="free_quizzes_overview",
            field=models.TextField(blank=True, verbose_name="الاختبارات والأسئلة المجانية الملحقة بالنوطة"),
        ),
        migrations.AddField(
            model_name="notebookorder",
            name="payment_method",
            field=models.CharField(
                choices=[("cod", "الدفع عند الاستلام"), ("shamcash", "شام كاش (Sham Cash)")],
                default="cod",
                max_length=20,
                verbose_name="طريقة الدفع",
            ),
        ),
        migrations.AddField(
            model_name="notebookorder",
            name="payment_reference",
            field=models.CharField(blank=True, max_length=120, verbose_name="مرجع الدفع أو رقم الحوالة"),
        ),
    ]
