from django.db import models
from decimal import Decimal

class CommissionRule(models.Model):
    name = models.CharField(max_length=200)
    
    # Priority: higher number = higher priority
    priority = models.IntegerField(default=0)
    
    # Scopes
    instructor = models.ForeignKey('accounts.InstructorProfile', on_delete=models.CASCADE, null=True, blank=True)
    course = models.ForeignKey('learning.Course', on_delete=models.CASCADE, null=True, blank=True)
    sales_center = models.ForeignKey('billing.SalesCenter', on_delete=models.CASCADE, null=True, blank=True)
    academic_branch = models.ForeignKey('accounts.AcademicBranch', on_delete=models.CASCADE, null=True, blank=True)
    
    # Percentages (0.0 to 1.0)
    instructor_share = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.4000'))
    platform_share = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.4500'))
    center_share = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.1500'))
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', '-created_at']

    def __str__(self):
        return f"{self.name} (P:{self.priority})"
