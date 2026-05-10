from django.db import models
from apps.core_finance.models import FinancialTrackingModel

class VideoSystemSnapshot(FinancialTrackingModel):
    """ Aggregated counters detailing static volume of content delivered."""
    capture_date = models.DateField(unique=True, db_index=True)
    
    total_video_count = models.IntegerField(default=0)
    total_storage_gb = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    total_duration_minutes = models.BigIntegerField(default=0)
    
    class Meta:
        ordering = ['-capture_date']

class VideoCalculatedUnitCost(FinancialTrackingModel):
    """ Pre-computed outcomes derived by blending infra-costs with snapshots."""
    snapshot = models.ForeignKey(VideoSystemSnapshot, on_delete=models.CASCADE)
    
    cost_per_gb_cents = models.DecimalField(max_digits=12, decimal_places=4)
    cost_per_video_cents = models.DecimalField(max_digits=12, decimal_places=4)
    cost_per_minute_cents = models.DecimalField(max_digits=12, decimal_places=4)
    
    total_monthly_infrastructure_burn_cents = models.BigIntegerField()
    
    class Meta:
        ordering = ['-created_at']
