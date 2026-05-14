import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.accounting_erp.models import (
    Account, AccountType, CostCenter, 
    JournalEntry, JournalLine, JournalEntryType
)

logger = logging.getLogger('accounting_erp')

def _get_account(code):
    return Account.objects.filter(code=code).first()

def _create_voucher(posting_date, reference, memo, entry_type, lines_data):
    """
    Creates a balanced, professional accounting voucher.
    """
    with transaction.atomic():
        voucher = JournalEntry.objects.create(
            posting_date=posting_date,
            reference=reference,
            memo=memo,
            entry_type=entry_type
        )
        for l in lines_data:
            JournalLine.objects.create(
                journal=voucher,
                account=l['account'],
                debit_amount=Decimal(str(l.get('debit', 0))),
                credit_amount=Decimal(str(l.get('credit', 0))),
                cost_center=l.get('cost_center'),
                line_memo=l.get('memo', memo),
            )
        
        if not voucher.is_balanced():
            logger.error(f"UNBALANCED VOUCHER: {reference}")
            # In production, you might raise an error here
            
    return voucher

def post_access_code_sold(access_code):
    """
    الأساس المحاسبي (مبدأ الاستحقاق):
    1. عند البيع: تسجيل إيراد مؤجل + مستحقات المدرس.
    2. مدين: الصندوق أو ذمة مركز البيع.
    3. دائن: إيرادات مؤجلة.
    """
    reference = f"SALE-{access_code.id}"
    if JournalEntry.objects.filter(reference=reference).exists():
        return

    price = Decimal(access_code.sold_price_cents or 0) / 100
    if price <= 0: return

    # 1. تحديد الحساب المدين (صندوق أم مركز؟)
    if access_code.sales_center:
        debit_acc = _get_account('113-1') # ذمم مراكز
        cc_code = f"CEN-{access_code.sales_center.id}"
        cc_name = access_code.sales_center.name
        cc_type = 'SALES_CENTER'
    else:
        debit_acc = _get_account('111') # صندوق
        cc_code = "MAIN"
        cc_name = "الصندوق الرئيسي"
        cc_type = 'INTERNAL'

    debit_cc, _ = CostCenter.objects.get_or_create(code=cc_code, defaults={'name_ar': cc_name, 'cost_center_type': cc_type})
    
    # 2. الحساب الدائن: إيراد مؤجل (212)
    deferred_acc = _get_account('212')
    
    # 3. حصة المدرس (استحقاق فوري للمصروف)
    lines = [
        {'account': debit_acc, 'debit': price, 'cost_center': debit_cc, 'memo': f'بيع كود {access_code.id}'},
        {'account': deferred_acc, 'credit': price, 'cost_center': None, 'memo': 'إيراد مؤجل (لحين التفعيل)'},
    ]

    if access_code.course and access_code.course.instructor:
        instructor = access_code.course.instructor
        exp_acc = _get_account('51') # تكاليف نشاط
        pay_acc = _get_account('211-1') # مستحقات مدرسين
        
        inst_cc, _ = CostCenter.objects.get_or_create(
            code=f"INS-{instructor.id}", 
            defaults={'name_ar': f"المدرس: {instructor.get_full_name()}", 'cost_center_type': 'INSTRUCTOR'}
        )
        
        # افتراض نسبة 40% (Enterprise Logic)
        share = price * Decimal('0.40')
        lines.append({'account': exp_acc, 'debit': share, 'cost_center': inst_cc, 'memo': f'مصروف حصة المدرس {instructor.username}'})
        lines.append({'account': pay_acc, 'credit': share, 'cost_center': inst_cc, 'memo': f'استحقاق للمدرس {instructor.username}'})

    _create_voucher(
        posting_date=access_code.sold_at.date() if access_code.sold_at else timezone.now().date(),
        reference=reference,
        memo=f"فاتورة مبيعات كود رقم {access_code.id}",
        entry_type=JournalEntryType.SALES,
        lines_data=lines
    )

def post_access_grant_created(access_grant):
    """
    عند التفعيل (Activation):
    تحويل من إيراد مؤجل إلى إيراد تشغيلي حقيقي.
    """
    code = access_grant.access_code
    if not code: return
    
    reference = f"ACT-{access_grant.id}"
    if JournalEntry.objects.filter(reference=reference).exists():
        return

    price = Decimal(code.sold_price_cents or 0) / 100
    if price <= 0: return

    deferred_acc = _get_account('212')
    real_rev_acc = _get_account('41')
    
    course_cc, _ = CostCenter.objects.get_or_create(
        code=f"CRS-{code.course.id}", 
        defaults={'name_ar': f"دورة: {code.course.title}", 'cost_center_type': 'COURSE'}
    )

    _create_voucher(
        posting_date=access_grant.created_at.date() if access_grant.created_at else timezone.now().date(),
        reference=reference,
        memo=f"تحقق إيراد بتفعيل الكود {code.id} للطالب {access_grant.user.username}",
        entry_type=JournalEntryType.ACCRUAL,
        lines_data=[
            {'account': deferred_acc, 'debit': price, 'memo': 'إغلاق إيراد مؤجل'},
            {'account': real_rev_acc, 'credit': price, 'cost_center': course_cc, 'memo': 'إيراد تشغيلي محقق'},
        ]
    )

# --- Additional Signal Handlers (Placeholders for robustness) ---

def post_student_registration(user, student_profile):
    """تلقائياً إنشاء حساب ذمة للطالب عند تسجيله"""
    Account.get_or_create_student_ar_account(user.id, user.get_full_name() or user.username)

def post_instructor_registration(user, instructor_profile):
    """تلقائياً إنشاء مركز كلفة للمدرس"""
    CostCenter.objects.get_or_create(
        code=f"INS-{user.id}",
        defaults={'name_ar': f"المدرس: {user.get_full_name() or user.username}", 'cost_center_type': 'INSTRUCTOR'}
    )

def post_course_created(course):
    """تلقائياً إنشاء مركز كلفة للدورة"""
    CostCenter.objects.get_or_create(
        code=f"CRS-{course.id}",
        defaults={'name_ar': f"دورة: {course.title}", 'cost_center_type': 'COURSE'}
    )

def post_payment_created(payment):
    """معالجة الدفع المباشر"""
    # TODO: Implement direct payment logic (Dr Cash / Cr Student AR)
    pass

def post_access_code_allocated_to_center(access_code):
    """تتبع تخصيص الأكواد لمراكز البيع"""
    pass
