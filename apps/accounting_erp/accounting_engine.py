"""
محرك القيود المحاسبية المركزي
يتولد تلقائياً عند كل حدث في المنصة:
  - تسجيل طالب جديد
  - بيع كود وصول
  - استرداد كود (تفعيل)
  - إضافة دورة / مدرس
  - دفع مباشر (Payment)
"""
import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger('accounting_erp')

INSTRUCTOR_SHARE_DEFAULT_BPS = 4000   # 40 %
CENTER_SHARE_DEFAULT_BPS     = 1500   # 15 %


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_account(code):
    from apps.accounting_erp.models import Account
    try:
        return Account.objects.get(code=code)
    except Account.DoesNotExist:
        logger.warning(f"[ERP] Account {code} not found. Run bootstrap first.")
        return None


def _get_or_create_account(code, name, category, parent_code=None, is_group=False):
    from apps.accounting_erp.models import Account, AccountCategory
    parent = _get_account(parent_code) if parent_code else None
    obj, created = Account.objects.get_or_create(
        code=code,
        defaults={
            'name': name,
            'category': category,
            'parent': parent,
            'is_group': is_group,
        }
    )
    return obj


def _get_or_create_cost_center(code, name):
    from apps.accounting_erp.models import CostCenter
    cc, _ = CostCenter.objects.get_or_create(code=code, defaults={'name': name})
    return cc


def _create_voucher(posting_date, reference, memo, lines_data):
    """
    lines_data: list of dicts with keys:
        account, debit, credit, cost_center (optional), memo (optional)
    """
    from apps.accounting_erp.models import JournalEntry, JournalLine
    from decimal import Decimal

    total_dr = sum(Decimal(str(l.get('debit', 0))) for l in lines_data)
    total_cr = sum(Decimal(str(l.get('credit', 0))) for l in lines_data)

    if abs(total_dr - total_cr) > Decimal('0.01'):
        logger.error(f"[ERP] Unbalanced voucher {reference}: Dr={total_dr} Cr={total_cr}")
        return None

    try:
        with transaction.atomic():
            voucher = JournalEntry.objects.create(
                posting_date=posting_date,
                reference=reference,
                memo=memo,
            )
            for l in lines_data:
                acc = l.get('account')
                if acc is None:
                    continue
                JournalLine.objects.create(
                    journal=voucher,
                    account=acc,
                    debit_amount=Decimal(str(l.get('debit', 0))),
                    credit_amount=Decimal(str(l.get('credit', 0))),
                    cost_center=l.get('cost_center'),
                    line_memo=l.get('memo', ''),
                )
        return voucher
    except Exception as e:
        logger.exception(f"[ERP] Failed to create voucher {reference}: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API — called by signals or manually
# ─────────────────────────────────────────────────────────────────────────────

def post_student_registration(user, student_profile=None):
    """
    حدث: تسجيل طالب جديد
    قيد: إنشاء مركز تكلفة خاص بالطالب في دليل الحسابات
    لا توجد حركة نقدية — فقط تهيئة البُعد المحاسبي
    """
    name = user.get_full_name() or user.username
    code = f"STD-{user.id}"
    cc = _get_or_create_cost_center(code, f"طالب: {name}")
    logger.info(f"[ERP] Student cost-center created/verified: {code} | {name}")
    return cc


def post_instructor_registration(user, instructor_profile=None):
    """
    حدث: إضافة مدرس
    قيد: إنشاء مركز تكلفة + حساب مستحقات خاص
    """
    name = user.get_full_name() or user.username
    _get_or_create_cost_center(f"INS-{user.id}", f"مدرس: {name}")
    logger.info(f"[ERP] Instructor cost-center created: INS-{user.id} | {name}")


def post_course_created(course):
    """
    حدث: إضافة دورة جديدة
    قيد: إنشاء مركز تكلفة للدورة
    """
    cc = _get_or_create_cost_center(f"CRS-{course.id}", f"دورة: {course.title[:60]}")
    logger.info(f"[ERP] Course cost-center created: CRS-{course.id}")
    return cc


def post_access_code_allocated_to_center(access_code):
    """
    حدث: تخصيص كود للمركز (إنشاء كود مرتبط بمركز بيع)
    قيد محاسبي:
        مدين  1201 ذمم مراكز بيع مدينة
        دائن  2102 إيرادات مؤجلة
    """
    reference = f"CODE_ALLOC_{access_code.id}"
    from apps.accounting_erp.models import JournalEntry
    if JournalEntry.objects.filter(reference=reference).exists():
        return  # already posted

    # Resolve amount
    price_cents = 0
    if access_code.course:
        price_cents = access_code.course.price_cents or 0
    elif access_code.package:
        price_cents = access_code.package.price_cents or 0

    if price_cents <= 0:
        return

    amount = Decimal(price_cents) / Decimal('100')

    recv_acc  = _get_or_create_account('1201', 'ذمم مراكز بيع مدينة', 'asset', '11')
    defer_acc = _get_or_create_account('2102', 'إيرادات مؤجلة', 'liability', '21')
    if not recv_acc or not defer_acc:
        return

    center = access_code.sales_center
    cc = _get_or_create_cost_center(f"CEN-{center.id}", f"مركز: {center.name}")
    item = access_code.course.title if access_code.course else (access_code.package.name if access_code.package else "بند")

    _create_voucher(
        posting_date=access_code.created_at.date() if hasattr(access_code.created_at, 'date') else timezone.now().date(),
        reference=reference,
        memo=f"تخصيص كود عهدة للمركز ({item})",
        lines_data=[
            {'account': recv_acc,  'debit':  amount, 'credit': 0, 'cost_center': cc, 'memo': 'عهدة كود مطبوع للمركز'},
            {'account': defer_acc, 'debit': 0, 'credit': amount,  'cost_center': cc, 'memo': 'إيراد مؤجل معلق'},
        ]
    )


def post_access_code_sold(access_code):
    """
    حدث: بيع كود (sale_status = 'sold')
    قيد محاسبي:
        مدين  1101 الصندوق الرئيسي       (المبلغ المحصّل)
        دائن  4101 مبيعات كورسات مباشرة  (الإيراد المحقق)
        ——— تسوية عهدة المركز (إن وُجد) ———
        مدين  2102 إيرادات مؤجلة
        دائن  1201 ذمم مراكز بيع مدينة
        ——— حصة المدرس ———
        مدين  5101 حصة المدرسين
        دائن  2101 مستحقات مدرسين
    """
    reference = f"CODE_SALE_{access_code.id}"
    from apps.accounting_erp.models import JournalEntry, AccountCategory
    if JournalEntry.objects.filter(reference=reference).exists():
        return

    # Resolve item
    price_cents = 0
    course = access_code.course
    package = access_code.package

    if course:
        price_cents = access_code.sold_price_cents or course.price_cents or 0
    elif package:
        price_cents = access_code.sold_price_cents or package.price_cents or 0
    else:
        price_cents = access_code.sold_price_cents or 0

    if price_cents <= 0:
        return

    realized = Decimal(price_cents) / Decimal('100')
    posting_date = (access_code.sold_at.date() if access_code.sold_at else timezone.now().date())

    # Core accounts
    cash_acc    = _get_or_create_account('1101', 'الصندوق الرئيسي (كاش)', 'asset', '11')
    rev_acc     = _get_or_create_account('4101', 'مبيعات الكورسات المباشرة', 'revenue', '41')
    recv_acc    = _get_or_create_account('1201', 'ذمم مراكز بيع مدينة', 'asset', '11')
    defer_acc   = _get_or_create_account('2102', 'إيرادات مؤجلة', 'liability', '21')
    exp_inst    = _get_or_create_account('5101', 'حصة المدرسين من المبيعات', 'expense', '51')
    liab_inst   = _get_or_create_account('2101', 'مستحقات المدرسين (أمانات)', 'liability', '21')

    item_name = course.title if course else (package.name if package else "بند")

    # Build lines
    lines = []

    # 1. Cash in
    std_cc = None
    grant = access_code.grants.select_related('user').first() if hasattr(access_code, 'grants') else None
    if grant and grant.user:
        std_cc = _get_or_create_cost_center(f"STD-{grant.user.id}", f"طالب: {grant.user.get_full_name() or grant.user.username}")
    elif access_code.assigned_student_name:
        std_cc = _get_or_create_cost_center(f"RAWSTD-{access_code.id}", f"طالب (يدوي): {access_code.assigned_student_name}")

    lines.append({'account': cash_acc, 'debit': realized, 'credit': 0, 'cost_center': std_cc, 'memo': 'استلام نقدية البيع'})

    # 2. Revenue recognition
    crs_cc = None
    if course:
        crs_cc = _get_or_create_cost_center(f"CRS-{course.id}", f"دورة: {course.title[:60]}")
    lines.append({'account': rev_acc, 'debit': 0, 'credit': realized, 'cost_center': crs_cc, 'memo': 'تحقيق الإيراد'})

    # 3. Settle center consignment if existed
    if access_code.sales_center:
        alloc_ref = f"CODE_ALLOC_{access_code.id}"
        if JournalEntry.objects.filter(reference=alloc_ref).exists():
            base_cents = (course.price_cents if course else (package.price_cents if package else 0)) or 0
            base_amt = Decimal(base_cents) / Decimal('100')
            center_cc = _get_or_create_cost_center(f"CEN-{access_code.sales_center.id}", f"مركز: {access_code.sales_center.name}")
            lines.append({'account': defer_acc, 'debit': base_amt,  'credit': 0,        'memo': 'تصفية إيراد مؤجل'})
            lines.append({'account': recv_acc,  'debit': 0,         'credit': base_amt, 'cost_center': center_cc, 'memo': 'تسوية عهدة المركز'})

    # 4. Instructor share accrual
    if course and course.instructor:
        bps = _resolve_instructor_bps(course)
        inst_amt = (realized * Decimal(str(bps))) / Decimal('10000')
        if inst_amt > 0:
            inst_cc = _get_or_create_cost_center(f"INS-{course.instructor.id}", f"مدرس: {course.instructor.get_full_name() or course.instructor.username}")
            lines.append({'account': exp_inst,  'debit': inst_amt, 'credit': 0,        'cost_center': inst_cc, 'memo': 'عبء عمولة مدرس'})
            lines.append({'account': liab_inst, 'debit': 0,       'credit': inst_amt, 'cost_center': inst_cc, 'memo': 'استحقاق أمانة مدرس'})

    _create_voucher(posting_date=posting_date, reference=reference,
                    memo=f"بيع نهائي: {item_name}", lines_data=lines)


def post_access_grant_created(access_grant):
    """
    حدث: استرداد كود (طالب فعّل الكود)
    إذا لم يكن البيع قد سُجّل → يُسجّل الآن
    """
    code = access_grant.access_code
    if code and code.sale_status != 'sold':
        # نتعامل معه كبيع مؤجل التسجيل
        reference = f"CODE_SALE_{code.id}"
        from apps.accounting_erp.models import JournalEntry
        if not JournalEntry.objects.filter(reference=reference).exists():
            post_access_code_sold(code)


def post_payment_created(payment):
    """
    حدث: إنشاء Payment مباشر (Stripe أو يدوي)
    قيد:
        مدين  1101 الصندوق / البنك
        دائن  4101 الإيرادات
    """
    if payment.status != 'paid':
        return

    reference = f"PAY_{payment.id}"
    from apps.accounting_erp.models import JournalEntry
    if JournalEntry.objects.filter(reference=reference).exists():
        return

    amount = Decimal(payment.amount_cents) / Decimal('100')
    if amount <= 0:
        return

    cash_acc = _get_or_create_account('1101', 'الصندوق الرئيسي (كاش)', 'asset', '11')
    rev_acc  = _get_or_create_account('4101', 'مبيعات الكورسات المباشرة', 'revenue', '41')

    _create_voucher(
        posting_date=payment.created_at.date() if hasattr(payment.created_at, 'date') else timezone.now().date(),
        reference=reference,
        memo=f"دفع مباشر #{payment.id}",
        lines_data=[
            {'account': cash_acc, 'debit': amount, 'credit': 0,      'memo': 'استلام دفع'},
            {'account': rev_acc,  'debit': 0,      'credit': amount,  'memo': 'إيراد مبيعات'},
        ]
    )


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_instructor_bps(course):
    """يحل نسبة حصة المدرس بالـ BPS (نقطة أساس) حسب الاتفاقية أو الافتراضي"""
    try:
        from django.apps import apps
        ShareModel = next((m for m in apps.get_models() if m.__name__ == 'RevenueShareAgreement'), None)
        if ShareModel:
            agree = ShareModel.objects.filter(
                course=course, instructor=course.instructor, is_active=True
            ).first()
            if agree and agree.commission_bps:
                return agree.commission_bps
    except Exception:
        pass
    return INSTRUCTOR_SHARE_DEFAULT_BPS
