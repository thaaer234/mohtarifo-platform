from django.db import models
from apps.core_finance.models import FinancialTrackingModel

class ForecastProjections(FinancialTrackingModel):
    """
    Stores calculated anticipated earnings using exponential smoothing or linear velocity.
    Allows comparison between 'Goal' and 'Expected trajectory'.
    """
    FORECAST_HORIZONS = [
        (30, '30 Days Projection'),
        (90, '90 Days Projection (Quarterly)'),
        (365, '1 Year Projection')
    ]
    
    calculated_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    horizon_days = models.IntegerField(choices=FORECAST_HORIZONS, default=30)
    
    projected_revenue_cents = models.BigIntegerField()
    
    confidence_interval_min_cents = models.BigIntegerField()
    confidence_interval_max_cents = models.BigIntegerField()
    
    model_type = models.CharField(max_length=50, default='linear_regression_simple')
    
    class Meta:
        ordering = ['-calculated_at']
