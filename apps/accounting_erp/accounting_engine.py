"""
محرك القيود المطور — يتبع نمط المشروع القديم (Enterprise Pattern)
"""
import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.accounting_erp.models import Account, AccountCategory, CostCenter, JournalEntry, JournalLine

logger = logging.getLogger('accounting_erp')

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_account(code):
    try:
        return Account.objects.get(code=code)
    except Account.DoesNotExist:
        return None

def _get_or_create_cost_center(code, name, cc_type='GENERAL'):
    cc, _ = CostCenter.objects.get_or_create(
        code=code, 
        defaults={'name': name, 'cost_center_type': cc_type}
    )
    return cc

def _create_voucher(posting_date, reference, memo, lines_data):
    total_dr = sum(Decimal(str(l.get('debit', 0))) for l in lines_data)
    total_cr = sum(Decimal(str(l.get('credit', 0))) for l in lines_data)

    if abs(total_dr - total_cr) > Decimal('0.01'):
        logger.error(f"[ERP] Unbalanced: {reference} Dr={total_dr} Cr={total_cr}")
        return None

    with transaction.atomic():
        voucher = JournalEntry.objects.create(
            posting_date=posting_date,
            reference=reference,
            memo=memo,
        )
        for l in lines_data:
            JournalLine.objects.create(
                journal=voucher,
                account=l['account'],
                debit_amount=Decimal(str(l.get('debit', 0))),
                credit_amount=Decimal(str(l.get('credit', 0))),
                cost_center=l.get('cost_center'),
                line_memo=l.get('memo', ''),
            )
    return voucher

# ─────────────────────────────────────────────────────────────────────────────
# API
# ─────────────────────────────────────────────────────────────────────────────

def post_student_registration(user, student_profile=None):
    """مثل النظام القديم: إنشاء حساب ذمم خاص بالطالب ومركز تكلفة"""
    # 1. حساب الذمم (AR Account)
    acc = Account.get_or_create_student_ar_account(user)
    # 2. مركز التكلفة
    cc, _ = CostCenter.objects.get_or_create(
        code=f"STD-{user.id}", 
        defaults={'name': user.get_full_name() or user.username, 'cost_center_type': 'STUDENT'}
    )
    return acc, cc

def post_instructor_registration(user, instructor_profile=None):
    cc, _ = CostCenter.objects.get_or_create(
        code=f"INS-{user.id}",
        defaults={'name': user.get_full_name() or user.username, 'cost_center_type': 'INSTRUCTOR'}
    )
    return cc

def post_course_created(course):
    cc, _ = CostCenter.objects.get_or_create(
        code=f"CRS-{course.id}", 
        defaults={'name': course.title, 'cost_center_type': 'COURSE'}
    )
    return cc

def post_access_code_allocated_to_center(access_code):
    """
    قيد تخصيص كود للمركز (نمط المشروع القديم):
    مدين ذمم مراكز / دائن إيراد مؤجل
    """
    reference = f"ALLOC-{access_code.id}"
    if JournalEntry.objects.filter(reference=reference).exists():
        return

    price_cents = (access_code.course.price_cents if access_code.course else (access_code.package.price_cents if access_code.package else 0)) or 0
    amount = Decimal(price_cents) / Decimal('100')
    if amount <= 0: return

    recv_acc = _get_account('1201')
    defer_acc = _get_account('2102')
    
    center_cc, _ = CostCenter.objects.get_or_create(
        code=f"CEN-{access_code.sales_center.id}",
        defaults={'name': access_code.sales_center.name, 'cost_center_type': 'SALES_CENTER'}
    )

    _create_voucher(
        posting_date=access_code.created_at.date() if hasattr(access_code.created_at, 'date') else timezone.now().date(),
        reference=reference,
        memo=f"تخصيص كود عهدة للمركز: {access_code.sales_center.name}",
        lines_data=[
            {'account': recv_acc, 'debit': amount, 'cost_center': center_cc, 'memo': 'عهدة كود للمركز'},
            {'account': defer_acc, 'credit': amount, 'cost_center': center_cc, 'memo': 'إيراد مؤجل'},
        ]
    )

def post_access_code_sold(access_code):
    """
    قيد البيع التفصيلي (نمط المشروع القديم):
    - مدين: الصندوق (1101)
    - دائن: إيرادات المبيعات (4101)
    - مع ربط مركز التكلفة للطالب والدورة
    """
    reference = f"SALE-{access_code.id}"
    if JournalEntry.objects.filter(reference=reference).exists():
        return

    price_cents = access_code.sold_price_cents or (access_code.course.price_cents if access_code.course else 0)
    amount = Decimal(price_cents) / Decimal('100')
    if amount <= 0: return

    cash_acc = _get_account('1101')
    rev_acc = _get_account('4101')
    
    # تحصيل مراكز التكلفة
    course_cc = None
    if access_code.course:
        course_cc = post_course_created(access_code.course)
    
    std_cc = None
    grant = access_code.grants.first()
    if grant and grant.user:
        _, std_cc = post_student_registration(grant.user)

    lines = [
        {'account': cash_acc, 'debit': amount, 'cost_center': std_cc, 'memo': 'تحصيل نقدي'},
        {'account': rev_acc,  'credit': amount, 'cost_center': course_cc, 'memo': f'إيراد دورة: {access_code.course.title if access_code.course else ""}'},
    ]

    # إضافة حصة المدرس (إذا وُجد)
    if access_code.course and access_code.course.instructor:
        exp_inst = _get_account('5101')
        liab_inst = _get_account('2101')
        inst_cc, _ = CostCenter.objects.get_or_create(
            code=f"INS-{access_code.course.instructor.id}",
            defaults={'name': access_code.course.instructor.get_full_name(), 'cost_center_type': 'INSTRUCTOR'}
        )
        # افتراض نسبة 40% (أو حسب العقد)
        share = amount * Decimal('0.40')
        lines.append({'account': exp_inst, 'debit': share, 'cost_center': inst_cc, 'memo': 'مصروف حصة مدرس'})
        lines.append({'account': liab_inst, 'credit': share, 'cost_center': inst_cc, 'memo': 'استحقاق مدرس'})

    _create_voucher(
        posting_date=access_code.sold_at.date() if access_code.sold_at else timezone.now().date(),
        reference=reference,
        memo=f"بيع كود رقم {access_code.id}",
        lines_data=lines
    )

def post_payment_created(payment):
    """قيد دفع مباشر"""
    reference = f"PAY-{payment.id}"
    if JournalEntry.objects.filter(reference=reference).exists():
        return

    amount = Decimal(payment.amount_cents) / Decimal('100')
    if amount <= 0: return

    cash_acc = _get_account('1101')
    rev_acc = _get_account('4101')

    _create_voucher(
        posting_date=payment.created_at.date() if hasattr(payment.created_at, 'date') else timezone.now().date(),
        reference=reference,
        memo=f"دفع مباشر #{payment.id}",
        lines_data=[
            {'account': cash_acc, 'debit': amount, 'memo': 'تحصيل دفع مباشر'},
            {'account': rev_acc, 'credit': amount, 'memo': 'إيراد مبيعات'},
        ]
    )

def post_access_grant_created(access_grant):
    """استرداد كود"""
    code = access_grant.access_code
    if code and code.sale_status != 'sold':
        post_access_code_sold(code)
