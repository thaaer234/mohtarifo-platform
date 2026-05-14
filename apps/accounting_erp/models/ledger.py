from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from decimal import Decimal
import uuid
from .chart import Account, CostCenter

class JournalEntryType(models.TextChoices):
    MANUAL = 'MANUAL', 'يدوي (Manual)'
    RECEIPT = 'RECEIPT', 'سند قبض (Receipt)'
    PAYMENT = 'PAYMENT', 'سند صرف (Payment)'
    SALES = 'SALES', 'فاتورة مبيعات (Sales)'
    ACCRUAL = 'ACCRUAL', 'قيد استحقاق (Accrual)'
    ADJUSTMENT = 'ADJUSTMENT', 'قيد تسوية (Adjustment)'
    CLOSING = 'CLOSING', 'قيد إغلاق (Closing)'

class JournalEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    posting_date = models.DateField(verbose_name="تاريخ القيد")
    reference = models.CharField(max_length=100, unique=True, verbose_name="المرجع / رقم السند")
    memo = models.TextField(blank=True, verbose_name="البيان / الوصف")
    entry_type = models.CharField(max_length=20, choices=JournalEntryType.choices, default=JournalEntryType.MANUAL)
    
    source_event = models.CharField(max_length=100, blank=True, null=True, help_text="Event that triggered this entry")
    source_id = models.CharField(max_length=100, blank=True, null=True)
    
    is_posted = models.BooleanField(default=True)
    is_voided = models.BooleanField(default=False)
    void_reason = models.TextField(blank=True, null=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "قيد يومية"
        verbose_name_plural = "قيود اليومية"
        ordering = ['-posting_date', '-created_at']

    def __str__(self):
        return f"{self.reference} | {self.posting_date}"

    def get_total_debit(self):
        return self.lines.aggregate(total=models.Sum('debit_amount'))['total'] or Decimal('0.00')

    def get_total_credit(self):
        return self.lines.aggregate(total=models.Sum('credit_amount'))['total'] or Decimal('0.00')

    def is_balanced(self):
        return abs(self.get_total_debit() - self.get_total_credit()) < Decimal('0.01')

    def clean(self):
        if not self.is_balanced() and self.is_posted:
            raise ValidationError("القيد غير متوازن (المدين لا يساوي الدائن).")

class JournalLine(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    journal = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='ledger_lines')
    cost_center = models.ForeignKey(CostCenter, on_delete=models.SET_NULL, null=True, blank=True)
    
    debit_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    credit_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    
    line_memo = models.CharField(max_length=500, blank=True)
    
    # Audit tracking
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.account.is_group:
            raise ValidationError(f"لا يمكن إضافة قيد لحساب رئيسي: {self.account.display_name}")
        if self.debit_amount > 0 and self.credit_amount > 0:
            raise ValidationError("لا يمكن وضع مبلغ في المدين والدائن معاً في نفس السطر.")

    def __str__(self):
        act = "Dr" if self.debit_amount > 0 else "Cr"
        val = self.debit_amount if self.debit_amount > 0 else self.credit_amount
        return f"{self.account.display_name} | {act} {val}"
