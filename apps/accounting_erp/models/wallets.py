from django.db import models
from django.conf import settings
from decimal import Decimal
import uuid

class WalletType(models.TextChoices):
    STUDENT = 'STUDENT', 'طالب'
    TEACHER = 'TEACHER', 'مدرس'
    CENTER = 'CENTER', 'مركز'

class Wallet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner_type = models.CharField(max_length=20, choices=WalletType.choices)
    
    # Links to entities
    student = models.OneToOneField('accounts.StudentProfile', on_delete=models.CASCADE, null=True, blank=True, related_name='wallet')
    instructor = models.OneToOneField('accounts.InstructorProfile', on_delete=models.CASCADE, null=True, blank=True, related_name='wallet')
    sales_center = models.OneToOneField('billing.SalesCenter', on_delete=models.CASCADE, null=True, blank=True, related_name='wallet')
    
    balance = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    pending_balance = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), help_text="Balances not yet available for withdrawal")
    frozen_balance = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), help_text="Balances locked due to disputes or audits")
    
    currency = models.CharField(max_length=10, default='SYP')
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        owner = self.student or self.instructor or self.sales_center
        return f"Wallet: {owner} ({self.balance})"

    @property
    def withdrawable_balance(self):
        return self.balance - self.frozen_balance

class WalletTransaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    transaction_type = models.CharField(max_length=50) # 'credit', 'debit'
    
    source_event = models.CharField(max_length=100) # 'course_purchase', 'session_payout', etc.
    reference_id = models.CharField(max_length=100, blank=True, null=True)
    
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    balance_before = models.DecimalField(max_digits=18, decimal_places=2)
    balance_after = models.DecimalField(max_digits=18, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.wallet} | {self.amount} ({self.transaction_type})"
