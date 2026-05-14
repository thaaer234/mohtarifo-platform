"""
معالج البيانات القديمة — يحوّل كل العمليات التاريخية إلى قيود محاسبية
يعمل كـ idempotent: آمن للتشغيل أكثر من مرة بدون تكرار القيود.
"""
import logging
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

logger = logging.getLogger('accounting_erp')


class LegacyAccountingTransformer:

    @classmethod
    def run_full_migration(cls, force_rebuild=False):
        """
        يُشغّل كامل خط أنابيب المعالجة للبيانات القديمة.
        force_rebuild=True → يحذف القيود التلقائية السابقة ويُعيد بناءها.
        """
        from apps.accounting_erp.models import JournalEntry

        if force_rebuild:
            deleted = JournalEntry.objects.filter(
                reference__startswith='CODE_'
            ).delete()[0]
            deleted += JournalEntry.objects.filter(
                reference__startswith='PAY_'
            ).delete()[0]
            deleted += JournalEntry.objects.filter(
                reference__startswith='GRANT_'
            ).delete()[0]
            logger.info(f"[ERP] force_rebuild: deleted {deleted} auto-vouchers")

        stats = {
            'students': 0,
            'instructors': 0,
            'courses': 0,
            'sales_centers': 0,
            'code_allocs': 0,
            'code_sales': 0,
            'payments': 0,
        }

        stats['students']      = cls._migrate_students()
        stats['instructors']   = cls._migrate_instructors()
        stats['courses']       = cls._migrate_courses()
        stats['sales_centers'] = cls._migrate_sales_centers()
        stats['code_allocs']   = cls._migrate_code_allocations()
        stats['code_sales']    = cls._migrate_code_sales()
        stats['payments']      = cls._migrate_direct_payments()

        summary = (
            f"[ERP Migration Done] "
            f"Students={stats['students']} | "
            f"Instructors={stats['instructors']} | "
            f"Courses={stats['courses']} | "
            f"Centers={stats['sales_centers']} | "
            f"CodeAllocs={stats['code_allocs']} | "
            f"CodeSales={stats['code_sales']} | "
            f"Payments={stats['payments']}"
        )
        logger.info(summary)
        return summary

    # ─────────────────────────────────────────────────────────────────────
    # خطوة 1: الطلاب — إنشاء مراكز تكلفة
    # ─────────────────────────────────────────────────────────────────────
    @classmethod
    def _migrate_students(cls):
        from accounts.models import StudentProfile
        from apps.accounting_erp.accounting_engine import post_student_registration
        count = 0
        for sp in StudentProfile.objects.select_related('user').iterator(chunk_size=500):
            try:
                post_student_registration(sp.user, sp)
                count += 1
            except Exception as e:
                logger.warning(f"[ERP] student {sp.user_id}: {e}")
        return count

    # ─────────────────────────────────────────────────────────────────────
    # خطوة 2: المدرسون — مراكز تكلفة
    # ─────────────────────────────────────────────────────────────────────
    @classmethod
    def _migrate_instructors(cls):
        from accounts.models import InstructorProfile
        from apps.accounting_erp.accounting_engine import post_instructor_registration
        count = 0
        for ip in InstructorProfile.objects.select_related('user').iterator(chunk_size=200):
            try:
                post_instructor_registration(ip.user, ip)
                count += 1
            except Exception as e:
                logger.warning(f"[ERP] instructor {ip.user_id}: {e}")
        return count

    # ─────────────────────────────────────────────────────────────────────
    # خطوة 3: الدورات — مراكز تكلفة
    # ─────────────────────────────────────────────────────────────────────
    @classmethod
    def _migrate_courses(cls):
        from learning.models import Course
        from apps.accounting_erp.accounting_engine import post_course_created
        count = 0
        for course in Course.objects.iterator(chunk_size=200):
            try:
                post_course_created(course)
                count += 1
            except Exception as e:
                logger.warning(f"[ERP] course {course.id}: {e}")
        return count

    # ─────────────────────────────────────────────────────────────────────
    # خطوة 4: مراكز البيع — مراكز تكلفة
    # ─────────────────────────────────────────────────────────────────────
    @classmethod
    def _migrate_sales_centers(cls):
        from billing.models import SalesCenter
        from apps.accounting_erp.accounting_engine import _get_or_create_cost_center
        count = 0
        for center in SalesCenter.objects.all():
            try:
                _get_or_create_cost_center(f"CEN-{center.id}", f"مركز: {center.name}")
                count += 1
            except Exception as e:
                logger.warning(f"[ERP] center {center.id}: {e}")
        return count

    # ─────────────────────────────────────────────────────────────────────
    # خطوة 5: تخصيص الأكواد للمراكز
    # ─────────────────────────────────────────────────────────────────────
    @classmethod
    def _migrate_code_allocations(cls):
        from billing.models import AccessCode
        from apps.accounting_erp.accounting_engine import post_access_code_allocated_to_center
        qs = AccessCode.objects.filter(
            sales_center__isnull=False
        ).select_related('course', 'package', 'sales_center')
        count = 0
        for code in qs.iterator(chunk_size=500):
            try:
                post_access_code_allocated_to_center(code)
                count += 1
            except Exception as e:
                logger.warning(f"[ERP] code alloc {code.id}: {e}")
        return count

    # ─────────────────────────────────────────────────────────────────────
    # خطوة 6: الأكواد المباعة أو المفعّلة
    # ─────────────────────────────────────────────────────────────────────
    @classmethod
    def _migrate_code_sales(cls):
        from billing.models import AccessCode
        from apps.accounting_erp.accounting_engine import post_access_code_sold
        qs = AccessCode.objects.filter(
            sale_status='sold'
        ).select_related(
            'course', 'course__instructor',
            'package', 'sales_center'
        ).prefetch_related('grants__user')
        count = 0
        for code in qs.iterator(chunk_size=500):
            try:
                post_access_code_sold(code)
                count += 1
            except Exception as e:
                logger.warning(f"[ERP] code sale {code.id}: {e}")

        # أيضاً: الأكواد التي استُرديت حتى لو لم تكن sold
        redeemed_qs = AccessCode.objects.filter(
            redeemed_count__gt=0, sale_status__in=['available', 'free']
        ).select_related('course', 'course__instructor', 'package', 'sales_center').prefetch_related('grants__user')
        for code in redeemed_qs.iterator(chunk_size=200):
            try:
                post_access_code_sold(code)
                count += 1
            except Exception as e:
                logger.warning(f"[ERP] code redeemed {code.id}: {e}")

        return count

    # ─────────────────────────────────────────────────────────────────────
    # خطوة 7: المدفوعات المباشرة
    # ─────────────────────────────────────────────────────────────────────
    @classmethod
    def _migrate_direct_payments(cls):
        from billing.models import Payment
        from apps.accounting_erp.accounting_engine import post_payment_created
        count = 0
        for pay in Payment.objects.filter(status='paid').iterator(chunk_size=500):
            try:
                post_payment_created(pay)
                count += 1
            except Exception as e:
                logger.warning(f"[ERP] payment {pay.id}: {e}")
        return count


# ─────────────────────────────────────────────────────────────────────────────
# Kept for backward compatibility
# ─────────────────────────────────────────────────────────────────────────────
class LegacyPaymentSelector:
    @staticmethod
    def get_access_code_sales_range(start_dt, end_dt):
        from billing.models import AccessCode
        return AccessCode.objects.filter(
            sale_status='sold',
            sold_at__gte=start_dt,
            sold_at__lte=end_dt,
        ).select_related('course', 'course__instructor', 'package', 'sales_center')
