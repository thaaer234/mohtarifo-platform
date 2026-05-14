"""
إشارات Django — الربط الفوري بين أحداث المنصة والنظام المحاسبي

كل حدث هنا يُطلق توليد قيد محاسبي تلقائي بدون أي تدخل يدوي.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger('accounting_erp')


# ─────────────────────────────────────────────────────────────────────────────
# طالب جديد
# ─────────────────────────────────────────────────────────────────────────────
@receiver(post_save, sender='accounts.StudentProfile')
def on_student_profile_saved(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        from apps.accounting_erp.accounting_engine import post_student_registration
        post_student_registration(user=instance.user, student_profile=instance)
    except Exception as e:
        logger.exception(f"[ERP Signal] student_profile: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# مدرس جديد
# ─────────────────────────────────────────────────────────────────────────────
@receiver(post_save, sender='accounts.InstructorProfile')
def on_instructor_profile_saved(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        from apps.accounting_erp.accounting_engine import post_instructor_registration
        post_instructor_registration(user=instance.user, instructor_profile=instance)
    except Exception as e:
        logger.exception(f"[ERP Signal] instructor_profile: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# دورة جديدة
# ─────────────────────────────────────────────────────────────────────────────
@receiver(post_save, sender='learning.Course')
def on_course_saved(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        from apps.accounting_erp.accounting_engine import post_course_created
        post_course_created(instance)
    except Exception as e:
        logger.exception(f"[ERP Signal] course created: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# كود وصول جديد — تخصيص لمركز بيع
# ─────────────────────────────────────────────────────────────────────────────
@receiver(post_save, sender='billing.AccessCode')
def on_access_code_saved(sender, instance, created, **kwargs):
    try:
        from apps.accounting_erp.accounting_engine import (
            post_access_code_allocated_to_center,
            post_access_code_sold,
        )
        if created and instance.sales_center:
            post_access_code_allocated_to_center(instance)

        # إذا أُنشئ الكود مباشرة كـ sold أو تم تحديث حالته إلى sold
        if instance.sale_status == 'sold':
            post_access_code_sold(instance)

    except Exception as e:
        logger.exception(f"[ERP Signal] access_code: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# تفعيل كود (AccessGrant) — الطالب يستخدم الكود
# ─────────────────────────────────────────────────────────────────────────────
@receiver(post_save, sender='billing.AccessGrant')
def on_access_grant_created(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        from apps.accounting_erp.accounting_engine import post_access_grant_created
        post_access_grant_created(instance)
    except Exception as e:
        logger.exception(f"[ERP Signal] access_grant: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# دفع مباشر (Payment)
# ─────────────────────────────────────────────────────────────────────────────
@receiver(post_save, sender='billing.Payment')
def on_payment_saved(sender, instance, created, **kwargs):
    if instance.status != 'paid':
        return
    try:
        from apps.accounting_erp.accounting_engine import post_payment_created
        post_payment_created(instance)
    except Exception as e:
        logger.exception(f"[ERP Signal] payment: {e}")
