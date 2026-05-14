from django.db import models
from django.db.models import Sum, Q
from decimal import Decimal
import uuid

class AccountCategory(models.TextChoices):
    ASSET = 'ASSET', 'الأصول (Assets)'
    LIABILITY = 'LIABILITY', 'الالتزامات (Liabilities)'
    EQUITY = 'EQUITY', 'حقوق الملكية (Equity)'
    REVENUE = 'REVENUE', 'الإيرادات (Revenue)'
    EXPENSE = 'EXPENSE', 'المصروفات (Expenses)'

class Account(models.Model):
    """
    هيكل دليل الحسابات (CoA) المطور ليدعم التقارير التفصيلية ومراكز التكلفة.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    
    code = models.CharField(max_length=20, unique=True, verbose_name="كود الحساب")
    name = models.CharField(max_length=200, verbose_name="اسم الحساب (EN)")
    name_ar = models.CharField(max_length=200, blank=True, verbose_name="اسم الحساب (AR)")
    category = models.CharField(max_length=20, choices=AccountCategory.choices, verbose_name="الفئة")
    
    is_group = models.BooleanField(default=False, help_text="إذا كان صحيحاً، يعمل كمجلد للفئات ولا يقبل قيوداً مباشرة.")
    is_active = models.BooleanField(default=True, verbose_name="نشط")

    # حقول إضافية للربط مع المنصة (مثل النظام القديم)
    is_course_account = models.BooleanField(default=False, verbose_name="حساب دورة")
    course_name = models.CharField(max_length=200, blank=True, verbose_name="اسم الدورة")
    is_student_account = models.BooleanField(default=False, verbose_name="حساب طالب")
    student_name = models.CharField(max_length=200, blank=True, verbose_name="اسم الطالب")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['code']
        verbose_name = "حساب محاسبي"
        verbose_name_plural = "دليل الحسابات"

    def __str__(self):
        return f"{self.code} - {self.name_ar if self.name_ar else self.name}"

    @property
    def display_name(self):
        return self.name_ar if self.name_ar else self.name

    def get_debit_balance(self):
        return self.ledger_lines.aggregate(total=Sum('debit_amount'))['total'] or Decimal('0.00')

    def get_credit_balance(self):
        return self.ledger_lines.aggregate(total=Sum('credit_amount'))['total'] or Decimal('0.00')

    def get_net_balance(self):
        dr = self.get_debit_balance()
        cr = self.get_credit_balance()
        if self.category in [AccountCategory.ASSET, AccountCategory.EXPENSE]:
            return dr - cr
        else:
            return cr - dr

    def get_rollup_balance(self):
        """الرصيد التراكمي للحساب وفروعه"""
        total = self.get_net_balance()
        for child in self.children.all():
            total += child.get_rollup_balance()
        return total

    # ─────────────────────────────────────────────────────────────────────
    # وظائف البذر التلقائي (مثل النظام القديم)
    # ─────────────────────────────────────────────────────────────────────
    
    @classmethod
    def get_or_create_student_ar_account(cls, student_user):
        """إنشاء أو جلب حساب ذمم الطالب: 1202-StudentID"""
        parent_ar = cls.objects.filter(code='1201').first() # ذمم مدينة
        name = student_user.get_full_name() or student_user.username
        code = f"1202-{student_user.id}"
        
        obj, created = cls.objects.get_or_create(
            code=code,
            defaults={
                'name': f"AR - {student_user.username}",
                'name_ar': f"ذمة الطالب: {name}",
                'category': AccountCategory.ASSET,
                'parent': parent_ar,
                'is_student_account': True,
                'student_name': name,
            }
        )
        return obj


class CostCenter(models.Model):
    """
    مراكز التكلفة لتتبع الأرباح والخسائر لكل دورة أو مركز مبيعات أو مدرس.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name="اسم مركز التكلفة")
    code = models.CharField(max_length=20, unique=True, verbose_name="الكود")
    
    # حقول إضافية للتحليل (مثل النظام القديم)
    cost_center_type = models.CharField(max_length=50, blank=True, verbose_name="النوع")
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.code} | {self.name}"

    def get_total_revenue(self, start_date=None, end_date=None):
        from .ledger import JournalLine
        qs = JournalLine.objects.filter(cost_center=self, account__category=AccountCategory.REVENUE)
        if start_date: qs = qs.filter(journal__posting_date__gte=start_date)
        if end_date: qs = qs.filter(journal__posting_date__lte=end_date)
        return qs.aggregate(total=Sum('credit_amount'))['total'] or Decimal('0.00')

    def get_total_expenses(self, start_date=None, end_date=None):
        from .ledger import JournalLine
        qs = JournalLine.objects.filter(cost_center=self, account__category=AccountCategory.EXPENSE)
        if start_date: qs = qs.filter(journal__posting_date__gte=start_date)
        if end_date: qs = qs.filter(journal__posting_date__lte=end_date)
        return qs.aggregate(total=Sum('debit_amount'))['total'] or Decimal('0.00')

    def get_net_profit(self, start_date=None, end_date=None):
        return self.get_total_revenue(start_date, end_date) - self.get_total_expenses(start_date, end_date)
