from django.db import models
from apps.core_finance.models import FinancialTrackingModel

class KPIRecord(FinancialTrackingModel):
    """
    Generic Key Performance Indicator time-series container.
    Allows arbitrary creation of metrics like ARPU, CAC, LTV without migrations.
    """
    kpi_key = models.CharField(max_length=100, db_index=True, help_text="Machine key e.g. 'ARPU', 'NET_PROFIT', 'CHURN_RATE'")
    display_name = models.CharField(max_length=200)
    
    value = models.DecimalField(max_digits=20, decimal_places=4)
    record_date = models.DateField(db_index=True)
    
    unit = models.CharField(max_length=20, default='USD', choices=[
        ('USD', 'United States Dollar'),
        ('PERCENT', 'Percentage'),
        ('COUNT', 'Raw Count'),
        ('RATIO', 'Ratio')
    ])

    class Meta:
        unique_together = ['kpi_key', 'record_date']
        ordering = ['-record_date']
        
class KPIBenchmark(FinancialTrackingModel):
    """Stores specific target ranges for KPI evaluations (Green/Yellow/Red)."""
    kpi_key = models.CharField(max_length=100, unique=True)
    target_value = models.DecimalField(max_digits=20, decimal_places=4)
    warning_threshold = models.DecimalField(max_digits=20, decimal_places=4, help_text="Below this is yellow warning zone.")
    critical_threshold = models.DecimalField(max_digits=20, decimal_places=4, help_text="Below this is red critical zone.")
