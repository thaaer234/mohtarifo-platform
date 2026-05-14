from django.db import models
from django.conf import settings
from decimal import Decimal
import uuid

class VoucherType(models.TextChoices):
    INVOICE = 'INV', 'فاتورة مبيعات (Invoice)'
    RECEIPT = 'REC', 'سند قبض (Receipt)'
    PAYMENT = 'PAY', 'سند صرف (Payment)'
    REFUND = 'REF', 'سند استرداد (Refund)'
    CREDIT_NOTE = 'CN', 'إشعار دائن (Credit Note)'
    DEBIT_NOTE = 'DN', 'إشعار مدين (Debit Note)'
    SETTLEMENT = 'SET', 'تسوية مدرس (Settlement)'

class Voucher(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    voucher_type = models.CharField(max_length=10, choices=VoucherType.choices)
    number = models.CharField(max_length=50, unique=True) # e.g. INV-2026-00001
    
    date = models.DateField()
    
    # Links to participants
    student = models.ForeignKey('accounts.StudentProfile', on_delete=models.SET_NULL, null=True, blank=True)
    instructor = models.ForeignKey('accounts.InstructorProfile', on_delete=models.SET_NULL, null=True, blank=True)
    sales_center = models.ForeignKey('billing.SalesCenter', on_delete=models.SET_NULL, null=True, blank=True)
    
    total_amount = models.DecimalField(max_digits=18, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    net_amount = models.DecimalField(max_digits=18, decimal_places=2)
    
    status = models.CharField(max_length=20, default='draft') # draft, posted, voided
    
    # Accounting link
    journal_entry = models.OneToOneField('accounting_erp.JournalEntry', on_delete=models.SET_NULL, null=True, blank=True, related_name='voucher')
    
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-number']

    def __str__(self):
        return f"{self.number} | {self.total_amount}"

class VoucherItem(models.Model):
    voucher = models.ForeignKey(Voucher, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1.00'))
    unit_price = models.DecimalField(max_digits=18, decimal_places=2)
    total_price = models.DecimalField(max_digits=18, decimal_places=2)
    
    # Context link
    course = models.ForeignKey('learning.Course', on_delete=models.SET_NULL, null=True, blank=True)
    session = models.ForeignKey('learning.OnlineLessonSession', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.description} ({self.total_price})"
