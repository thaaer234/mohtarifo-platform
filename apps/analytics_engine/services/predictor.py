import math
from datetime import timedelta
from django.utils import timezone
from apps.financial_system.models import RevenueSnapshot
from ..models import ForecastProjections

class RevenueForecastingService:
    """
    Strategic predictive analytic unit applying trend velocity vectors 
    on past capture windows to establish future probable trajectories.
    """
    
    @classmethod
    def generate_simple_linear_forecast(cls, horizon_days=30):
        """
        Examines previous 30-day performance and extends linear vector 
        forward into upcoming horizon timeframe.
        """
        # Collect past 30 days of daily rollups
        lookback_date = timezone.now().date() - timedelta(days=30)
        historical = list(RevenueSnapshot.objects.filter(
            period='daily',
            snapshot_date__gte=lookback_date
        ).order_by('snapshot_date'))
        
        if len(historical) < 7:
            return None # Insufficient velocity vector depth for fidelity
            
        # Convert to generic sequence values
        y_vals = [h.gross_revenue_cents for h in historical]
        x_vals = list(range(len(y_vals)))
        
        n = len(x_vals)
        x_mean = sum(x_vals) / n
        y_mean = sum(y_vals) / n
        
        # Calculate linear slope
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, y_vals))
        denominator = sum((x - x_mean) ** 2 for x in x_vals)
        
        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator
            
        intercept = y_mean - (slope * x_mean)
        
        # Project the upcoming aggregate over the horizon period
        projected_sum = 0
        current_index = n # start projecting from step immediately next
        
        for i in range(horizon_days):
            future_index = current_index + i
            est_revenue = intercept + (slope * future_index)
            # Prevent mathematical negative projections
            projected_sum += max(0, est_revenue)
            
        # Derive conservative interval (+/- 15% band)
        min_interval = int(projected_sum * 0.85)
        max_interval = int(projected_sum * 1.15)
        
        # Persist strategic insight
        forecast = ForecastProjections.objects.create(
            horizon_days=horizon_days,
            projected_revenue_cents=int(projected_sum),
            confidence_interval_min_cents=min_interval,
            confidence_interval_max_cents=max_interval,
            model_type='simple_linear_trend'
        )
        
        return forecast
