from django.db import models
from apps.core_finance.models import FinancialTrackingModel

class RevenueSnapshot(FinancialTrackingModel):
    """
    High-performance aggregation container calculated nightly.
    Pre-computed analytics to serve lightning fast charts.
    """
    PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    
    period = models.CharField(max_length=20, choices=PERIOD_CHOICES, default='daily')
    snapshot_date = models.DateField(db_index=True)
    
    gross_revenue_cents = models.BigIntegerField(default=0)
    net_revenue_cents = models.BigIntegerField(default=0)
    refund_total_cents = models.BigIntegerField(default=0)
    
    transaction_count = models.IntegerField(default=0)
    active_customers_count = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ['period', 'snapshot_date']
        ordering = ['-snapshot_date']

class CashFlowRecord(FinancialTrackingModel):
    """
    Direct record of available cash balance tracking daily summaries.
    """
    record_date = models.DateField(unique=True, db_index=True)
    
    opening_balance_cents = models.BigIntegerField(default=0)
    inflows_cents = models.BigIntegerField(default=0)
    outflows_cents = models.BigIntegerField(default=0)
    closing_balance_cents = models.BigIntegerField(default=0)
    
    class Meta:
        ordering = ['-record_date']
