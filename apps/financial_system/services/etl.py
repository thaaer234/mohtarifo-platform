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
            for payment in legacy_payments:
                # Skip if already exists to ensure immutability and idempotence
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
                        description=f"Payment Sync Ref: {payment.provider_payment_id}",
                        created_at=payment.created_at
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
