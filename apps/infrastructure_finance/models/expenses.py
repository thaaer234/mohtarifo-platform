from django.db import models
from apps.core_finance.models import FinancialTrackingModel

class InfrastructureExpense(FinancialTrackingModel):
    """ Categorized registry for computing recurring machine overhead costs."""
    CATEGORY_CHOICES = [
        ('hosting', 'VPS/Server Hosting'),
        ('cdn', 'Video CDN Network'),
        ('storage', 'S3 / Object Storage'),
        ('bandwidth', 'Bandwidth Overhead'),
        ('license', 'Software / SSL Licensing')
    ]
    
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, db_index=True)
    vendor_name = models.CharField(max_length=100, help_text="e.g. AWS, DigitalOcean, Bunny.net")
    
    monthly_cost_usd_cents = models.BigIntegerField()
    
    billing_cycle_start = models.DateField()
    is_recurring = models.BooleanField(default=True)
    
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['-billing_cycle_start']
        
    def __str__(self): return f"{self.vendor_name} - {self.category}"
