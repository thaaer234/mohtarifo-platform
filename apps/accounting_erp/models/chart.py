from django.db import models
from django.db.models import Sum
from decimal import Decimal
import uuid

class AccountType(models.TextChoices):
    ASSET = 'ASSET', 'أصول (Assets)'
    LIABILITY = 'LIABILITY', 'خصوم (Liabilities)'
    EQUITY = 'EQUITY', 'حقوق ملكية (Equity)'
    REVENUE = 'REVENUE', 'إيرادات (Revenue)'
    EXPENSE = 'EXPENSE', 'مصروفات (Expense)'

class Account(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    
    code = models.CharField(max_length=20, unique=True, verbose_name="كود الحساب")
    name = models.CharField(max_length=200, verbose_name="الاسم (EN)")
    name_ar = models.CharField(max_length=200, blank=True, verbose_name="الاسم (AR)")
    account_type = models.CharField(max_length=20, choices=AccountType.choices, default=AccountType.ASSET, verbose_name="نوع الحساب")
    
    is_group = models.BooleanField(default=False, verbose_name="حساب رئيسي (مجلد)")
    is_active = models.BooleanField(default=True, verbose_name="نشط")

    # Metadata for automatic linking
    is_student_account = models.BooleanField(default=False)
    student_id = models.IntegerField(null=True, blank=True)
    
    is_course_account = models.BooleanField(default=False)
    course_id = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['code']
        verbose_name = "حساب"
        verbose_name_plural = "دليل الحسابات"

    def __str__(self):
        return f"{self.code} - {self.display_name}"

    @property
    def display_name(self):
        return self.name_ar if self.name_ar else self.name

    def get_balance(self, start_date=None, end_date=None):
        from .ledger import JournalLine
        lines = JournalLine.objects.filter(account=self)
        if start_date: lines = lines.filter(journal__posting_date__gte=start_date)
        if end_date: lines = lines.filter(journal__posting_date__lte=end_date)
        
        agg = lines.aggregate(dr=Sum('debit_amount'), cr=Sum('credit_amount'))
        dr = agg['dr'] or Decimal('0.00')
        cr = agg['cr'] or Decimal('0.00')
        
        if self.account_type in [AccountType.ASSET, AccountType.EXPENSE]:
            return dr - cr
        return cr - dr

    def get_rollup_balance(self, start_date=None, end_date=None):
        total = self.get_balance(start_date, end_date)
        for child in self.children.all():
            total += child.get_rollup_balance(start_date, end_date)
        return total

    @classmethod
    def get_or_create_student_ar_account(cls, user_id, user_name):
        parent_ar = cls.objects.filter(code='113').first() # Receivables
        code = f"113-{user_id}"
        obj, created = cls.objects.get_or_create(
            code=code,
            defaults={
                'name': f"AR Student: {user_id}",
                'name_ar': f"ذمة الطالب: {user_name}",
                'account_type': AccountType.ASSET,
                'parent': parent_ar,
                'is_student_account': True,
                'student_id': user_id
            }
        )
        return obj

class CostCenter(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, unique=True, verbose_name="الكود")
    name = models.CharField(max_length=100, verbose_name="الاسم")
    name_ar = models.CharField(max_length=100, blank=True, verbose_name="الاسم (AR)")
    
    cost_center_type = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} | {self.name_ar or self.name}"
