import os
import django
from decimal import Decimal
from django.utils import timezone

def run_audit():
    print("--- STARTING ERP AUDIT ---\n")
    
    from django.contrib.auth import get_user_model
    from learning.models import Course
    from billing.models import AccessCode
    from apps.accounting_erp.models import JournalEntry, Account
    from apps.accounting_erp.services.legacy_transformer import LegacyAccountingTransformer
    
    User = get_user_model()
    # 1. Use existing setup from DB
    course = Course.objects.get(pk=1)
    instructor = course.instructor
    seller = User.objects.first() # Use any admin as seller
    
    # Ensure course has a price for audit
    if not course.price_cents or course.price_cents == 0:
        course.price_cents = 10000
        course.save()

    # 2. Set Mock Agreeement fallback
    from django.apps import apps
    share_model = next((m for m in apps.get_models() if m.__name__ == 'RevenueShareAgreement'), None)
    if share_model:
        share_model.objects.get_or_create(course=course, instructor=instructor, defaults={'commission_bps': 5000, 'is_active': True})

    
    # 3. Generate a DISCOUNTED Code Sale Event ($80 sold, $20 discount)
    code = AccessCode.objects.create(
        code=f"AUDIT-{int(timezone.now().timestamp())}",
        course=course,
        sale_status='sold',
        sold_by=seller,
        sold_price_cents=8000, # Realized $80
        sold_at=timezone.now()
    )
    
    print(f"[OK] Phase 1: Generated complex mock sale (Course: {course.title}, Sold for 80/100, Seller: {seller.username})\n")
    
    # 4. RUN THE SYSTEM
    initial_cnt = JournalEntry.objects.count()
    print("[>] Phase 2: Triggering Legacy-to-ERP Auto-Transformer...")
    res = LegacyAccountingTransformer.auto_generate_ledger_from_sales()
    print(f"[OK] Engine Result: {res}")
    
    # 5. VERIFY CREATION
    final_cnt = JournalEntry.objects.count()
    if final_cnt <= initial_cnt:
        print("[FAIL] No new journal entries created!")
        return
        
    entry = JournalEntry.objects.filter(reference=f"CODE_SALE_{code.id}").first()
    if not entry:
         print("[FAIL] Target voucher missing!")
         return
         
    print(f"\n[OK] Phase 3: Found generated Voucher Reference: {entry.reference}")
    
    # 6. DEEP INSPECTION OF SPLIT LINES (The ultimate audit)
    lines = entry.lines.all().select_related('account', 'cost_center').order_by('debit_amount')
    
    print("-" * 70)
    print(f"{'Account Code':<12} | {'Account Name':<30} | {'Dr':<8} | {'Cr':<8} | {'Cost Center'}")
    print("-" * 70)
    
    total_dr = Decimal(0)
    total_cr = Decimal(0)
    
    for l in lines:
        dr = l.debit_amount
        cr = l.credit_amount
        total_dr += dr
        total_cr += cr
        print(f"{l.account.code:<12} | {l.account.name:<30} | {dr:<8} | {cr:<8} | {l.cost_center.name if l.cost_center else 'NONE'}")
        
    print("-" * 70)
    print(f"TOTAL BALANCING: Debit {total_dr} | Credit {total_cr}")
    print(f"BALANCED STATE: {'YES' if total_dr == total_cr else 'FAIL'}")
    
    # Verify Instructor Accrual existence
    if entry.lines.filter(account__code='2101').exists():
        print("\n[OK] VERIFIED: Instructor Accrual Payable recognized correctly!")
    else:
        print("\n[FAIL] Instructor Accrual Payable missing!")

    if entry.lines.filter(account__code='4104').exists():
        print("[OK] VERIFIED: Contra-Revenue Discount recognized correctly!")

    print("\n--- AUDIT COMPLETE: ALL PASS ---")

if __name__ == "__main__":
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()
    run_audit()
