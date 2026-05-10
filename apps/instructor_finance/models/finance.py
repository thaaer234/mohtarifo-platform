from django.db import models
from django.conf import settings
from apps.core_finance.models import FinancialTrackingModel
from learning.models import Course

class RevenueShareAgreement(FinancialTrackingModel):
    """
    Defines legal commission logic for specific instructors or standard defaults.
    """
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='revenue_agreements')
    
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, help_text="Leave blank for default shared logic.")
    
    commission_bps = models.IntegerField(default=3000, help_text="Basis points payout to instructor (e.g., 3000 = 30%)")
    
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['instructor', 'course']

class InstructorCommission(FinancialTrackingModel):
    """
    Atomic record showing how much an instructor earned from a single system event.
    """
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # References to system event causing earning
    ledger_entry = models.ForeignKey('financial_system.FinancialLedger', on_delete=models.CASCADE, null=True, blank=True)
    
    gross_amount_cents = models.BigIntegerField(help_text="Total collected amount before split")
    instructor_share_cents = models.BigIntegerField(help_text="Earnings credited to instructor account")
    
    status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pending Payout'),
        ('locked', 'Clawback Protection Window'),
        ('paid', 'Paid to Instructor'),
        ('reversed', 'Reversed due to Refund')
    ])

class InstructorPayout(FinancialTrackingModel):
    """
    Historical ledger showing actual outgoing movement of capital to an instructor's bank/wallet.
    """
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    payout_cents = models.BigIntegerField()
    payout_date = models.DateField(db_index=True)
    
    status = models.CharField(max_length=20, default='processed', choices=[
        ('requested', 'Requested'),
        ('processed', 'Completed Successfully'),
        ('failed', 'Failed Processing')
    ])
    
    reference_id = models.CharField(max_length=255, blank=True, help_text="Bank transaction ID or Provider tracking string")
