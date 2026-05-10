from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from apps.infrastructure_finance.models import InfrastructureExpense
from ..models import OperationalExpense, MonthlyBurnRateReport

class BurnRateOrchestrator:
    """
    Consolidates infrastructure and high-level human ops pooling into 
    unified monthly intelligence checkpoints for CFO visibility.
    """
    
    @classmethod
    def calculate_monthly_reconciliation(cls, run_date=None):
        """
        Generates current unified checkpoint by merging disjoint pool streams.
        """
        if run_date is None:
            run_date = timezone.now().date()
            
        # Normalized date targeting start of current month
        target_month = run_date.replace(day=1)
        
        # Pool A: Infrastructure monthly sums (Cents -> Dollars)
        infra_cents = InfrastructureExpense.objects.filter(
            is_recurring=True
        ).aggregate(s=Sum('monthly_cost_usd_cents'))['s'] or 0
        infra_usd = Decimal(infra_cents) / Decimal('100.0')
        
        # Pool B: Explicit Operational Expenses documented for timeframe
        ops_cents = OperationalExpense.objects.filter(
            transaction_date__year=target_month.year,
            transaction_date__month=target_month.month
        ).aggregate(s=Sum('amount_cents'))['s'] or 0
        ops_usd = Decimal(ops_cents) / Decimal('100.0')
        
        composite = infra_usd + ops_usd
        
        # Atomic Registry update
        report, _ = MonthlyBurnRateReport.objects.update_or_create(
            period_month=target_month,
            defaults={
                'total_infra_burn_usd': infra_usd,
                'total_operational_burn_usd': ops_usd,
                'composite_burn_total_usd': composite
            }
        )
        return report
