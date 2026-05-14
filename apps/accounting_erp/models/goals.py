from django.db import models
from django.utils import timezone
from decimal import Decimal

class FinancialGoal(models.Model):
    title = models.CharField(max_length=255)
    target_amount = models.DecimalField(max_digits=18, decimal_places=2)
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    
    def get_progress_percent(self):
        from .ledger import JournalLine, Account
        from .chart import AccountType
        
        # Calculate revenue during the goal period
        revenue_total = JournalLine.objects.filter(
            account__account_type=AccountType.REVENUE,
            journal__posting_date__gte=self.start_date,
            journal__posting_date__lte=self.end_date
        ).aggregate(total=models.Sum('credit_amount'))['total'] or Decimal('0.00')
        
        if self.target_amount <= 0: return 0
        return min(round((revenue_total / self.target_amount) * 100, 1), 100)

    def __str__(self):
        return f"{self.title} ({self.get_progress_percent()}%)"

    class Meta:
        verbose_name = "Financial Goal"
        verbose_name_plural = "Financial Goals"
