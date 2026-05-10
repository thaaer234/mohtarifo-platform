from django.db import models
from apps.core_finance.models import FinancialTrackingModel

class PaymentGatewayMetric(FinancialTrackingModel):
    """
    Evaluates daily conversion statistics partitioned per payment processor (Stripe, Zain Cash, etc.).
    """
    gateway_name = models.CharField(max_length=50, db_index=True)
    metric_date = models.DateField(db_index=True)
    
    successful_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    
    success_volume_cents = models.BigIntegerField(default=0)
    failed_volume_cents = models.BigIntegerField(default=0)
    
    class Meta:
        unique_together = ['gateway_name', 'metric_date']
        ordering = ['-metric_date']

class PaymentFailureReason(FinancialTrackingModel):
    """
    Categorized repository of decline mechanics (Insufficent funds, Card Declined, Expired, Timeout).
    """
    reason_slug = models.CharField(max_length=100, db_index=True)
    occurred_on = models.DateField(db_index=True)
    
    incident_count = models.IntegerField(default=1)
    
    class Meta:
        ordering = ['-occurred_on', '-incident_count']
