from django.db import transaction
from decimal import Decimal
from django.utils import timezone
from apps.accounting_erp.models import Account, JournalEntry, JournalLine, CostCenter
from billing.models import Payment, AccessCode
from apps.financial_system.selectors.legacy_adapters import LegacyPaymentSelector

class LegacyAccountingTransformer:
    """
    Converts raw legacy instrument logs into fully balanced structured Accounting Vouchers.
    """
    
    @classmethod
    @transaction.atomic
    def auto_generate_ledger_from_sales(cls):
        """ Main Orchestrator pulling historical sales and generating missing entries. """
        
        # Retrieve primary accounting hooks
        try:
            cash_acc = Account.objects.get(code='1101') 
            revenue_acc = Account.objects.get(code='4101')
            # Ensure Discount account exists on the fly
            op_rev = Account.objects.get(code='41')
            from apps.accounting_erp.models import AccountCategory
            disc_acc, _ = Account.objects.get_or_create(
                code='4104', 
                defaults={'name': 'حسومات مبيعات مسموح بها', 'category': AccountCategory.REVENUE, 'parent': op_rev}
            )
        except Account.DoesNotExist:
            return "ERROR: Standard Chart of Accounts required hooks not found. Run seed first."
            
        end_dt = timezone.now()
        start_dt = end_dt - timezone.timedelta(days=90)
        
        codes = LegacyPaymentSelector.get_access_code_sales_range(start_dt, end_dt)
        created_count = 0
        
        for code in codes:
            ref_tag = f"CODE_SALE_{code.id}"
            if JournalEntry.objects.filter(reference=ref_tag).exists():
                continue
                
            # Resolve Reference Item (Course/Package)
            item_name = "Unspecified"
            item_base_price = 0
            course_ref = None
            
            if code.course:
                item_name = code.course.title
                item_base_price = code.course.price_cents or 0
                course_ref = code.course
            elif code.package:
                item_name = code.package.name
                item_base_price = code.package.price_cents or 0

                
            # 1. Resolve Course Cost Center (Direct association as requested)
            cost_ctr = None
            if course_ref:
                cost_ctr, _ = CostCenter.objects.get_or_create(
                    code=f"CRS-{course_ref.id}",
                    defaults={'name': f"دورة: {item_name[:60]}"}
                )
            
            # 2. Accrual Math: Realized Price vs Original Price
            realized_price_cents = code.sold_price_cents or item_base_price
            discount_cents = item_base_price - realized_price_cents if item_base_price > realized_price_cents else 0
            
            amt_cash = Decimal(realized_price_cents) / Decimal('100.0')
            amt_gross = Decimal(item_base_price) / Decimal('100.0')
            amt_disc = Decimal(discount_cents) / Decimal('100.0')
            
            if amt_gross <= 0: continue # Edge case safe exit

            entry_date = code.sold_at.date() if code.sold_at else (code.created_at.date() if code.created_at else timezone.now().date())
            
            voucher = JournalEntry.objects.create(
                posting_date=entry_date,
                reference=ref_tag,
                memo=f"قيد مبيعات تلقائي: {item_name}"
            )
            
            # 3. Resolve Instructor/Branch context
            branch_ctr = None
            if code.sold_by:
                branch_ctr, _ = CostCenter.objects.get_or_create(
                    code=f"BRN-{code.sold_by.id}",
                    defaults={'name': f"فرع/بائع: {code.sold_by.get_full_name() or code.sold_by.username}"}
                )
            
            instructor_ctr = None
            instructor_ref = None
            if course_ref and course_ref.instructor:
                instructor_ref = course_ref.instructor
                instructor_ctr, _ = CostCenter.objects.get_or_create(
                    code=f"INS-{instructor_ref.id}",
                    defaults={'name': f"مدرس: {instructor_ref.get_full_name() or instructor_ref.username}"}
                )
            
            # LEG 1: Debit Cash (Real cash actually taken) -> Tagged to receiving branch!
            JournalLine.objects.create(
                journal=voucher, account=cash_acc,
                debit_amount=amt_cash, line_memo="تحصيل قيمة البيع",
                cost_center=branch_ctr
            )
            
            # LEG 2: Debit Discount (If applicable)
            if amt_disc > 0:
                JournalLine.objects.create(
                    journal=voucher, account=disc_acc,
                    debit_amount=amt_disc, line_memo=f"حسم ممنوح ({item_name})",
                    cost_center=cost_ctr
                )
                
            # LEG 3: Credit GROSS Revenue (Tied to Course)
            JournalLine.objects.create(
                journal=voucher, account=revenue_acc,
                credit_amount=amt_gross, line_memo="إثبات إيراد الكورس الإجمالي",
                cost_center=cost_ctr
            )
            
            # --- ACCRUAL PHASE 2: INSTRUCTOR SHARE INJECTION ---
            if instructor_ref and amt_gross > 0:
                # Lookup dynamic platform share BPS (Basis points)
                from django.apps import apps
                share_model = next((m for m in apps.get_models() if m.__name__ == 'RevenueShareAgreement'), None)
                
                bps = 5000 # Default fallback 50% if no agreement found
                if share_model:
                    agree = share_model.objects.filter(course=course_ref, instructor=instructor_ref, is_active=True).first()
                    if agree:
                        bps = agree.commission_bps or 5000
                
                # Calculate instructor dollar amount from NET realized or GROSS?
                # Conventionally on platform net realized.
                inst_amt = (amt_cash * Decimal(str(bps))) / Decimal('10000')
                
                if inst_amt > 0:
                    # Lookup necessary liability & expense accounts
                    exp_inst_acc, _ = Account.objects.get_or_create(code='5101', defaults={'name': 'حصة المدرسين من المبيعات', 'category': AccountCategory.EXPENSE, 'parent': Account.objects.get(code='51')})
                    liab_inst_acc, _ = Account.objects.get_or_create(code='2101', defaults={'name': 'مستحقات المدرسين (أمانات)', 'category': AccountCategory.LIABILITY, 'parent': Account.objects.get(code='21')})
                    
                    # LEG 4: Debit Expense (Accrue direct instructor cost tied to that Specific Instructor)
                    JournalLine.objects.create(
                        journal=voucher, account=exp_inst_acc,
                        debit_amount=inst_amt, line_memo=f"استحقاق عمولة مدرس: {instructor_ref.username}",
                        cost_center=instructor_ctr
                    )
                    
                    # LEG 5: Credit Payable (Recognize money we OWE them now)
                    JournalLine.objects.create(
                        journal=voucher, account=liab_inst_acc,
                        credit_amount=inst_amt, line_memo=f"أمانة مستحقة للمدرس عن بيع {item_name}",
                        cost_center=instructor_ctr
                    )
            
            created_count += 1


            
        return f"Success. Generated {created_count} Balanced Accounting Vouchers automatically."
