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
            # Phase 1: RESOLVE BASIC ATTRIBUTES
            item_name = "مادة"
            item_price_cents = 0
            course_ref = None
            if code.course:
                item_name = code.course.title
                item_price_cents = code.course.price_cents or 0
                course_ref = code.course
            elif code.package:
                item_name = code.package.name
                item_price_cents = code.package.price_cents or 0

            base_price_dec = Decimal(item_price_cents) / Decimal('100.0')
            if base_price_dec <= 0: continue
            
            # ------------------------------------------------------------
            # EVENT A: CODE ALLOCATION TO CENTER (INVENTORY/DEFERRED)
            # ------------------------------------------------------------
            if code.sales_center:
                alloc_tag = f"CODE_ALLOC_{code.id}"
                if not JournalEntry.objects.filter(reference=alloc_tag).exists():
                    # Lookup/Create center-specific cost center
                    center_cost, _ = CostCenter.objects.get_or_create(
                        code=f"CEN-{code.sales_center.id}",
                        defaults={'name': f"مركز: {code.sales_center.name}"}
                    )
                    
                    # Define required accounts
                    # 1201: Accounts Receivable / Center Consignment
                    recv_acc, _ = Account.objects.get_or_create(code='1201', defaults={'name': 'ذمم مراكز بيع مدينة', 'category': AccountCategory.ASSET, 'parent': Account.objects.get(code='1')})
                    # 2102: Deferred Revenue
                    def_acc, _ = Account.objects.get_or_create(code='2102', defaults={'name': 'إيرادات مؤجلة (اشتراكات)', 'category': AccountCategory.LIABILITY, 'parent': Account.objects.get(code='2')})
                    
                    v_alloc = JournalEntry.objects.create(
                        posting_date=code.created_at.date(),
                        reference=alloc_tag,
                        memo=f"تخصيص كود عهدة للمركز ({item_name})"
                    )
                    # Debit Center Receivable
                    JournalLine.objects.create(journal=v_alloc, account=recv_acc, debit_amount=base_price_dec, cost_center=center_cost, line_memo="عهدة كود مطبوع للمركز")
                    # Credit Deferred Rev
                    JournalLine.objects.create(journal=v_alloc, account=def_acc, credit_amount=base_price_dec, cost_center=center_cost, line_memo="إيراد مؤجل معلق")
                    created_count += 1

            # ------------------------------------------------------------
            # EVENT B: FINAL ACTIVATION/SALE (REALIZE REVENUE & SPLIT)
            # ------------------------------------------------------------
            if code.sale_status == 'sold' or code.redeemed_count > 0:
                sell_tag = f"CODE_SALE_{code.id}"
                if not JournalEntry.objects.filter(reference=sell_tag).exists():
                    
                    realized_cents = code.sold_price_cents or item_price_cents
                    realized_dec = Decimal(realized_cents) / Decimal('100.0')
                    
                    # Prepare course-specific center
                    crs_cost = None
                    if course_ref:
                        crs_cost, _ = CostCenter.objects.get_or_create(code=f"CRS-{course_ref.id}", defaults={'name': f"دورة: {item_name[:60]}"})
                    
                    v_sell = JournalEntry.objects.create(
                        posting_date=code.sold_at.date() if code.sold_at else timezone.now().date(),
                        reference=sell_tag,
                        memo=f"تفعيل وبيع نهائي: {item_name}"
                    )
                    
                    # If had a center before, resolve the allocation chain!
                    if code.sales_center:
                        recv_acc, _ = Account.objects.get_or_create(code='1201', defaults={'name': 'ذمم مراكز بيع مدينة', 'category': AccountCategory.ASSET})
                        def_acc, _ = Account.objects.get_or_create(code='2102', defaults={'name': 'إيرادات مؤجلة (اشتراكات)', 'category': AccountCategory.LIABILITY})
                        
                        # Debit Deferred (Reverse the liability)
                        JournalLine.objects.create(journal=v_sell, account=def_acc, debit_amount=base_price_dec, line_memo="تصفية الإيراد المؤجل عند البيع")
                        # Credit Center Receivable (Settled)
                        JournalLine.objects.create(journal=v_sell, account=recv_acc, credit_amount=base_price_dec, line_memo="تسوية عهدة المركز عند البيع")

                    # CORE SALES LEGS
                    # Debit CASH (Actual received)
                    JournalLine.objects.create(journal=v_sell, account=cash_acc, debit_amount=realized_dec, line_memo="استلام نقدية البيع النهائي")
                    # Credit REVENUE (Earned!)
                    JournalLine.objects.create(journal=v_sell, account=revenue_acc, credit_amount=realized_dec, cost_center=crs_cost, line_memo="تحقيق الإيراد الفعلي")

                    # --- INSTRUCTOR SHARE SPLIT (Dynamic Accrual) ---
                    if course_ref and course_ref.instructor:
                        from django.apps import apps
                        share_model = next((m for m in apps.get_models() if m.__name__ == 'RevenueShareAgreement'), None)
                        bps = 5000
                        if share_model:
                            agree = share_model.objects.filter(course=course_ref, instructor=course_ref.instructor, is_active=True).first()
                            if agree: bps = agree.commission_bps or 5000
                        
                        inst_amt = (realized_dec * Decimal(str(bps))) / Decimal('10000')
                        if inst_amt > 0:
                            inst_cost, _ = CostCenter.objects.get_or_create(code=f"INS-{course_ref.instructor.id}", defaults={'name': f"مدرس: {course_ref.instructor.username}"})
                            exp_i, _ = Account.objects.get_or_create(code='5101', defaults={'name': 'حصة المدرسين', 'category': AccountCategory.EXPENSE, 'parent': Account.objects.get(code='51')})
                            lia_i, _ = Account.objects.get_or_create(code='2101', defaults={'name': 'مستحقات مدرسين', 'category': AccountCategory.LIABILITY, 'parent': Account.objects.get(code='21')})
                            
                            JournalLine.objects.create(journal=v_sell, account=exp_i, debit_amount=inst_amt, cost_center=inst_cost, line_memo="عبء عمولة مدرس")
                            JournalLine.objects.create(journal=v_sell, account=lia_i, credit_amount=inst_amt, cost_center=inst_cost, line_memo="استحقاق أمانة مدرس")

                    created_count += 1



            
        return f"Success. Generated {created_count} Balanced Accounting Vouchers automatically."
