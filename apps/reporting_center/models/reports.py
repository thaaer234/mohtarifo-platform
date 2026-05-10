from django.db import models
from django.conf import settings
from apps.core_finance.models import FinancialTrackingModel

class GeneratedReport(FinancialTrackingModel):
    """
    Main registry keeping track of files requested by administrators.
    Includes status tracking for large asynchronous generational jobs.
    """
    REPORT_TYPES = [
        ('financial_summary', 'Financial Comprehensive Summary'),
        ('instructor_payouts', 'Instructor Payout Matrix'),
        ('subscription_churn', 'Subscription Retention Audit'),
    ]
    
    FORMAT_CHOICES = [
        ('xlsx', 'Excel Spreadsheet'),
        ('pdf', 'PDF Document'),
        ('csv', 'Comma Separated Values'),
    ]

    report_type = models.CharField(max_length=50, choices=REPORT_TYPES)
    output_format = models.CharField(max_length=10, choices=FORMAT_CHOICES, default='xlsx')
    
    status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Queued'),
        ('processing', 'In Progress'),
        ('completed', 'Completed Success'),
        ('failed', 'Generation Failure')
    ])
    
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    # Store as standard file path
    file_asset = models.FileField(upload_to='financial_reports/%Y/%m/', null=True, blank=True)
    
    # Range contextual info
    filters_json = models.JSONField(default=dict, blank=True)
    
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
