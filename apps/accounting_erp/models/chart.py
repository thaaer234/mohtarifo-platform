from django.db import models
import uuid

class AccountCategory(models.TextChoices):
    ASSET = 'asset', 'الأصول (Assets)'
    LIABILITY = 'liability', 'الالتزامات (Liabilities)'
    EQUITY = 'equity', 'حقوق الملكية (Equity)'
    REVENUE = 'revenue', 'الإيرادات (Revenue)'
    EXPENSE = 'expense', 'المصروفات (Expense)'

class Account(models.Model):
    """
    Hierarchical Chart of Accounts (CoA) supporting standard accounting hierarchies.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    
    code = models.CharField(max_length=20, unique=True, help_text="Standard Accounting Code e.g. 1101")
    name = models.CharField(max_length=100, help_text="Arabic/English Name of Account")
    category = models.CharField(max_length=20, choices=AccountCategory.choices)
    
    is_group = models.BooleanField(default=False, help_text="If True, serves as parent category folder only and cannot hold transactions directly.")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['code']
        verbose_name = "حساب محاسبي"

    def __str__(self):
        return f"{self.code} - {self.name}"

class CostCenter(models.Model):
    """
    Enables multi-dimensional expense/revenue tracking e.g. By Course, By Center.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    
    def __str__(self):
        return f"{self.code} | {self.name}"
