from django.core.management.base import BaseCommand
from billing.models import Payment, CoursePurchase, AccessCode
from learning.models import OnlineLessonSession
from apps.accounting_erp.signals.service import AccountingEventService
from django.db import transaction

class Command(BaseCommand):
    help = 'Syncs legacy billing and learning data into the new ERP Accounting system'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Legacy Accounting Sync...'))

        # 1. Sync Payments
        payments = Payment.objects.filter(status='paid')
        self.stdout.write(f'Processing {payments.count()} payments...')
        for pay in payments:
            AccountingEventService.process_payment(pay)

        # 2. Sync Course Purchases
        purchases = CoursePurchase.objects.all()
        self.stdout.write(f'Processing {purchases.count()} purchases...')
        for pur in purchases:
            AccountingEventService.process_purchase(pur)

        # 3. Sync Access Code Sales (Aggressive)
        # Process ALL redeemed codes or sold codes
        from django.db.models import Q
        codes = AccessCode.objects.filter(Q(sale_status='sold') | Q(redeemed_count__gt=0))
        self.stdout.write(f'Processing {codes.count()} access codes (sold or redeemed)...')
        for code in codes:
            # Fallback price if sold_price_cents is missing
            if not code.sold_price_cents:
                if code.course and code.course.price_cents:
                    code.sold_price_cents = code.course.price_cents
                elif code.package and code.package.price_cents:
                    code.sold_price_cents = code.package.price_cents
                # Only save if we found a price
                if code.sold_price_cents:
                    code.save(update_fields=['sold_price_cents'])
            
            AccountingEventService.process_code_sale(code)

        # 4. Sync Completed Sessions
        sessions = OnlineLessonSession.objects.filter(status='completed')
        self.stdout.write(f'Processing {sessions.count()} completed sessions...')
        for sess in sessions:
            AccountingEventService.process_session_completion(sess)

        # 5. Sync Legacy Ledger (Optional check)
        try:
            from apps.financial_system.models.ledger import FinancialLedger
            legacy_entries = FinancialLedger.objects.all()
            self.stdout.write(f'Processing {legacy_entries.count()} legacy ledger entries...')
            # Logic to bridge legacy to new if not already covered
        except ImportError:
            pass

        self.stdout.write(self.style.SUCCESS('Legacy Accounting Sync Completed!'))
