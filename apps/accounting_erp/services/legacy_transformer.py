import os
import django
from decimal import Decimal
from django.utils import timezone
from .chart_seeder import seed_enterprise_coa
from ..models import Account, Wallet, WalletType, CommissionRule, JournalEntry
from billing.models import AccessCode, SalesCenter
from accounts.models import InstructorProfile

def run_migration():
    print("Starting Enterprise Accounting Migration...")
    
    # 1. Seed COA
    print("--- Seeding COA ---")
    created = seed_enterprise_coa()
    print(f"Created {created} new accounts.")
    
    # 2. Create Global Commission Rules
    print("--- Creating Default Commission Rules ---")
    CommissionRule.objects.get_or_create(
        name="القاعدة الافتراضية للمنصة",
        defaults={
            'priority': 0,
            'instructor_share': Decimal('0.4000'),
            'platform_share': Decimal('0.4500'),
            'center_share': Decimal('0.1500')
        }
    )
    
    # 3. Initialize Wallets
    print("--- Initializing Wallets ---")
    for instructor in InstructorProfile.objects.all():
        Wallet.objects.get_or_create(instructor=instructor, defaults={'owner_type': WalletType.TEACHER})
    
    for center in SalesCenter.objects.all():
        Wallet.objects.get_or_create(sales_center=center, defaults={'owner_type': WalletType.CENTER})
        
    # 4. Migrate Historical Sales
    print("--- Migrating Historical Sales ---")
    from .accounting_engine import AccountingEngine
    
    sold_codes = AccessCode.objects.filter(sale_status='sold').select_related('course', 'sales_center')
    migrated_count = 0
    
    for code in sold_codes:
        ref = f"AC-{code.id}"
        if not JournalEntry.objects.filter(source_id=ref).exists():
            try:
                amount = (code.sold_price_cents or 0) / 100
                if amount > 0:
                    AccountingEngine.record_sale(
                        amount=amount,
                        student=code.sold_by, # Note: sold_by is user, might need student profile lookup
                        course=code.course,
                        sales_center=code.sales_center,
                        reference=ref
                    )
                    migrated_count += 1
            except Exception as e:
                print(f"Error migrating code {code.id}: {e}")
                
    print(f"Migration completed. Total sales migrated: {migrated_count}")

if __name__ == "__main__":
    run_migration()
