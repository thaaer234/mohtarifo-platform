from django.utils import timezone
from django.db import transaction
from ..models import FinancialLedger, RevenueSnapshot
from ..selectors.legacy_adapters import LegacyPaymentSelector

class LedgerSyncService:
    """
    Orchestrates synchronization between legacy payment source and isolated financial ledger.
    Designed for background job execution.
    """
    
    @classmethod
    def sync_missing_payments(cls, lookback_days=2):
        """
        Pulls recent successful payments and populates them as Ledger entries 
        if not already existing, preventing duplication.
        """
        now = timezone.now()
        start = now - timezone.timedelta(days=lookback_days)
        
        legacy_payments = LegacyPaymentSelector.get_successful_payments_range(start, now)
        
        synced_count = 0
        
        with transaction.atomic():
            # A. Digital Wire Ingest
            for payment in legacy_payments:
                exists = FinancialLedger.objects.filter(
                    external_reference_id=str(payment.id),
                    external_source='billing.Payment'
                ).exists()
                
                if not exists:
                    FinancialLedger.objects.create(
                        entry_type='revenue',
                        amount_cents=payment.amount_cents,
                        currency=payment.currency,
                        external_reference_id=str(payment.id),
                        external_source='billing.Payment',
                        user=payment.user,
                        description=f"Digital Payment: {payment.provider_payment_id or payment.id}",
                        created_at=payment.created_at
                    )
                    synced_count += 1

            # B. Access Code Sale Ingest
            legacy_codes = LegacyPaymentSelector.get_access_code_sales_range(start, now)
            for code in legacy_codes:
                exists = FinancialLedger.objects.filter(
                    external_reference_id=str(code.id),
                    external_source='billing.AccessCode'
                ).exists()
                
                if not exists:
                    # Fallback fallback price detection logic mirrored from core
                    amt = code.sold_price_cents
                    if amt is None:
                         if code.course: amt = code.course.price_cents
                         elif code.package: amt = code.package.price_cents
                         
                    FinancialLedger.objects.create(
                        entry_type='revenue',
                        amount_cents=amt or 0,
                        currency='SYP', # Access codes natively priced in SYP generally in system
                        external_reference_id=str(code.id),
                        external_source='billing.AccessCode',
                        user=code.sold_by, # Attributing to operator who registered sale
                        description=f"Access Code Sold: {code.code}",
                        created_at=code.sold_at or code.created_at
                    )
                    synced_count += 1
                    
        return synced_count

class AnalyticsRollupService:
    """
    Aggregates processed ledger entries into optimized RevenueSnapshot objects.
    """
    @classmethod
    def generate_daily_snapshot(cls, snapshot_date):
        """Computes and stores single day analytic data for fast reporting."""
        from django.db.models import Sum, Count
        
        ledger_qs = FinancialLedger.objects.filter(
            created_at__date=snapshot_date
        )
        
        # Calculate metrics via isolated DB aggregation
        metrics = ledger_qs.aggregate(
            gross=Sum('amount_cents'),
            count=Count('id'),
            users=Count('user', distinct=True)
        )
        
        gross = metrics.get('gross') or 0
        count = metrics.get('count') or 0
        users = metrics.get('users') or 0
        
        # Upsert pattern to maintain one accurate record per date
        snapshot, created = RevenueSnapshot.objects.update_or_create(
            period='daily',
            snapshot_date=snapshot_date,
            defaults={
                'gross_revenue_cents': gross,
                'net_revenue_cents': gross, # Add subtraction logic for actual expenses/payouts later
                'transaction_count': count,
                'active_customers_count': users
            }
        )
        return snapshot
