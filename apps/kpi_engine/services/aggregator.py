from decimal import Decimal
from django.utils import timezone
from apps.financial_system.models import RevenueSnapshot
from apps.subscription_analytics.models import RecurringRevenueMetric
from ..models import KPIRecord

class KPIAggregationService:
    """
    Central brain collecting sub-module metrics into one accessible stream.
    Builds standard 'source of truth' records.
    """
    
    @classmethod
    def run_nightly_sync(cls):
        """Orchestrates cross-app retrieval to fill KPI store."""
        today = timezone.now().date()
        results = []
        
        # 1. Average Revenue Per User (ARPU)
        results.append(cls._calc_arpu(today))
        
        # 2. Lifetime Total Revenue Agg
        results.append(cls._calc_total_revenue(today))
        
        return results

    @classmethod
    def _calc_arpu(cls, snapshot_date):
        """Calculates current ARPU by comparing snapshot data."""
        try:
            # Fetch last generated analytics record
            rev = RecurringRevenueMetric.objects.filter(metric_date__lte=snapshot_date).first()
            snap = RevenueSnapshot.objects.filter(snapshot_date__lte=snapshot_date).first()
            
            if not rev or not snap or snap.active_customers_count == 0:
                val = Decimal('0.00')
            else:
                # Monthly revenue per active subscriber
                val = Decimal(rev.mrr_cents) / Decimal(snap.active_customers_count) / Decimal('100.0')
            
            record, _ = KPIRecord.objects.update_or_create(
                kpi_key='ARPU',
                record_date=snapshot_date,
                defaults={
                    'display_name': 'Average Revenue Per User',
                    'value': val,
                    'unit': 'USD'
                }
            )
            return record
        except Exception:
            return None

    @classmethod
    def _calc_total_revenue(cls, snapshot_date):
        from django.db.models import Sum
        total = RevenueSnapshot.objects.aggregate(total=Sum('gross_revenue_cents'))
        val_cents = total.get('total') or 0
        
        record, _ = KPIRecord.objects.update_or_create(
            kpi_key='TOTAL_GROSS',
            record_date=snapshot_date,
            defaults={
                'display_name': 'Total Lifetime Gross Revenue',
                'value': Decimal(val_cents) / Decimal('100.0'),
                'unit': 'USD'
            }
        )
        return record
