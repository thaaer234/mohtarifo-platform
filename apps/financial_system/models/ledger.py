from django.db import models
from django.conf import settings
from apps.core_finance.models import FinancialTrackingModel

class FinancialLedger(FinancialTrackingModel):
    """
    The immutable atomic record of financial movement within the system.
    Maps safely to external business events like purchase, refund, payout.
    """
    ENTRY_TYPES = [
        ('revenue', 'Revenue Inbound'),
        ('refund', 'Refund Outbound'),
        ('payout', 'Instructor Payout'),
        ('expense', 'Operational Expense'),
    ]
    
    entry_type = models.CharField(max_length=30, choices=ENTRY_TYPES, db_index=True)
    amount_cents = models.BigIntegerField(help_text="Amount in smallest currency unit (cents/piasters). Positive for inflow, negative for outflow.")
    currency = models.CharField(max_length=10, default='USD')
    
    # Safe decoupling via logical references
    external_reference_id = models.CharField(max_length=255, blank=True, null=True, db_index=True, help_text="Reference to billing.Payment.id or similar external PK.")
    external_source = models.CharField(max_length=50, blank=True, null=True, help_text="Source app/table name e.g. billing.Payment")
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='financial_ledger_entries'
    )
    
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Financial Ledger Entry"
        verbose_name_plural = "Financial Ledger"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['entry_type', 'created_at']),
            models.Index(fields=['external_source', 'external_reference_id']),
        ]

    def __str__(self):
        return f"{self.entry_type.upper()} | {self.amount_cents/100} {self.currency}"
