from django.db import models
from apps.core_finance.models import FinancialTrackingModel

class ExchangeProvider(FinancialTrackingModel):
    """ Registry of source providers feeding live conversion data feeds."""
    name = models.CharField(max_length=50, unique=True)
    api_key = models.CharField(max_length=255, blank=True, null=True)
    is_enabled = models.BooleanField(default=True)
    priority = models.IntegerField(default=1, help_text="Lower value takes precedence if parallel sources provide values.")
    
    def __str__(self): return self.name

class ExchangeRate(FinancialTrackingModel):
    """ Represents point-in-time valuation connecting base-quote pairs."""
    base_currency = models.CharField(max_length=3, default='USD', db_index=True)
    quote_currency = models.CharField(max_length=3, default='SYP', db_index=True)
    
    rate = models.DecimalField(max_digits=20, decimal_places=6)
    
    provider = models.ForeignKey(ExchangeProvider, on_delete=models.SET_NULL, null=True, blank=True)
    is_manual_override = models.BooleanField(default=False)
    
    valid_from = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-valid_from']
        get_latest_by = 'valid_from'
        indexes = [
            models.Index(fields=['base_currency', 'quote_currency', 'valid_from'])
        ]

    def __str__(self):
        return f"1 {self.base_currency} = {self.rate} {self.quote_currency}"
