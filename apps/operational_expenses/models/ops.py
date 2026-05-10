from django.db import models
from apps.core_finance.models import FinancialTrackingModel

class OperationalExpense(FinancialTrackingModel):
    """ Tracking generic non-technical business overheads."""
    EXPENSE_TYPES = [
        ('staff', 'Salaries & Contractors'),
        ('marketing', 'Advertisements & Branding'),
        ('office', 'Facilities & Hardware'),
        ('ai', 'LLM API Costs / Intelligence'),
        ('other', 'General Operational')
    ]
    
    expense_type = models.CharField(max_length=30, choices=EXPENSE_TYPES, db_index=True)
    label = models.CharField(max_length=150)
    
    amount_cents = models.BigIntegerField()
    currency = models.CharField(max_length=3, default='USD')
    
    transaction_date = models.DateField()
    
    class Meta:
        ordering = ['-transaction_date']

class MonthlyBurnRateReport(FinancialTrackingModel):
    """ Point-in-time consolidate calculating exact overhead costs."""
    period_month = models.DateField(unique=True, db_index=True, help_text="Use first of month.")
    
    total_infra_burn_usd = models.DecimalField(max_digits=16, decimal_places=2)
    total_operational_burn_usd = models.DecimalField(max_digits=16, decimal_places=2)
    
    composite_burn_total_usd = models.DecimalField(max_digits=16, decimal_places=2)
    
    class Meta:
        ordering = ['-period_month']
