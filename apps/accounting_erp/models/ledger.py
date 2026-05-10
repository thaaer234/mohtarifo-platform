from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from decimal import Decimal
import uuid
from .chart import Account, CostCenter

class JournalEntry(models.Model):
    """
    A complete financial transaction voucher containing balanced debit/credit lines.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    posting_date = models.DateField(help_text="Date this transaction was incurred (Accrual basis)")
    reference = models.CharField(max_length=100, blank=True, help_text="Invoice #, Payment Ref, etc.")
    memo = models.TextField(blank=True, help_text="General narrative description")
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def clean(self):
        # Future-proofing: Will ensure overall balanced ledger check on save calls
        pass

    def __str__(self):
        return f"Voucher {self.reference or str(self.id)[:8]} | {self.posting_date}"

class JournalLine(models.Model):
    """
    Individual granular entry line within a Journal Voucher.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    journal = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='ledger_lines')
    cost_center = models.ForeignKey(CostCenter, on_delete=models.SET_NULL, null=True, blank=True)
    
    debit_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    credit_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    
    line_memo = models.CharField(max_length=200, blank=True)
    
    def clean(self):
        if self.account.is_group:
            raise ValidationError("Cannot post direct transactions to a 'Group' type account category. Select a leaf account.")
        if self.debit_amount > 0 and self.credit_amount > 0:
            raise ValidationError("Single line cannot contain both Debit and Credit. Use two separate lines.")

    def __str__(self):
        act_str = "Dr" if self.debit_amount > 0 else "Cr"
        val = self.debit_amount if self.debit_amount > 0 else self.credit_amount
        return f"{self.account.name} | {act_str} {val}"
