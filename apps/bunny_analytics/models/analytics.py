from django.db import models
from decimal import Decimal
from apps.core_finance.models import FinancialTrackingModel

class BunnyRateConfiguration(FinancialTrackingModel):
    """ Admin-configured operational unit pricing applied to calculations."""
    monthly_vps_cost_cents = models.BigIntegerField(default=5000, help_text="External server costs")
    
    price_per_gb_storage = models.DecimalField(max_digits=10, decimal_places=5, default=0.01)
    price_per_gb_bandwidth = models.DecimalField(max_digits=10, decimal_places=5, default=0.005)
    
    encoding_per_min = models.DecimalField(max_digits=10, decimal_places=5, default=0.001)
    
    is_active = models.BooleanField(default=True)

    def __str__(self): return f"Rate Plan #{self.id}"

class BunnyVideoAnalytics(FinancialTrackingModel):
    """ Tracks telemetry fed directly from external Bunny.net video APIs."""
    bunny_id = models.CharField(max_length=200, unique=True, db_index=True)
    title = models.CharField(max_length=255, blank=True)
    
    storage_size_bytes = models.BigIntegerField(default=0)
    bandwidth_used_bytes = models.BigIntegerField(default=0)
    duration_seconds = models.IntegerField(default=0)
    total_views = models.BigIntegerField(default=0)
    
    # Calculated Outputs per specific logic
    calculated_total_cost_usd = models.DecimalField(max_digits=16, decimal_places=6, default=0)
    
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-calculated_total_cost_usd']

    @property
    def size_gb(self):
        return Decimal(self.storage_size_bytes) / Decimal(1024**3)
        
    @property
    def bw_gb(self):
        return Decimal(self.bandwidth_used_bytes) / Decimal(1024**3)

class BunnyPlatformReport(FinancialTrackingModel):
    """ Top-level aggregate monthly check consolidating total overhead burn."""
    period = models.DateField(unique=True)
    
    total_aggregate_cost_usd = models.DecimalField(max_digits=14, decimal_places=2)
    total_storage_used_gb = models.DecimalField(max_digits=14, decimal_places=2)
    total_bandwidth_used_gb = models.DecimalField(max_digits=14, decimal_places=2)
    
    class Meta:
        ordering = ['-period']
