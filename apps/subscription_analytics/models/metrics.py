from django.db import models
from apps.core_finance.models import FinancialTrackingModel

class RecurringRevenueMetric(FinancialTrackingModel):
    """
    Daily tracking of Monthly Recurring Revenue (MRR) and Annual Recurring Revenue (ARR).
    Used heavily by growth forecasting charts.
    """
    metric_date = models.DateField(unique=True, db_index=True)
    
    mrr_cents = models.BigIntegerField(default=0)
    arr_cents = models.BigIntegerField(default=0)
    
    # Deltas compared to yesterday
    new_mrr_cents = models.BigIntegerField(default=0)
    churned_mrr_cents = models.BigIntegerField(default=0)
    expansion_mrr_cents = models.BigIntegerField(default=0)
    
    class Meta:
        ordering = ['-metric_date']

class SubscriptionSnapshot(FinancialTrackingModel):
    """
    Captures quantity statistics regarding active users versus canceled users.
    """
    snapshot_date = models.DateField(unique=True)
    
    total_active_subscriptions = models.IntegerField(default=0)
    new_subscriptions = models.IntegerField(default=0)
    canceled_subscriptions = models.IntegerField(default=0)
    
    # Calculated churn rate percentage (stored as e.g., 4.50 -> 450 integer scale)
    churn_rate_bps = models.IntegerField(default=0, help_text="Basis points (100 bps = 1%)")
    
    class Meta:
        ordering = ['-snapshot_date']
