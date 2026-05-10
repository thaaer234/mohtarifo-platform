import tablib
from django.core.files.base import ContentFile
from django.utils import timezone
from apps.financial_system.models import RevenueSnapshot
from ..models import GeneratedReport

class ReportGenerationService:
    """
    Industrial engine responsible for assembling raw analytic rows into
    downloadable serialized datasets.
    """
    
    @classmethod
    def process_report(cls, report_id):
        """Primary processor loop called typically by an asynchronous worker."""
        try:
            report = GeneratedReport.objects.get(id=report_id)
            report.status = 'processing'
            report.save()
            
            # Branch out by type
            if report.report_type == 'financial_summary':
                cls._generate_financial_summary(report)
            else:
                raise ValueError("Unknown Report Requested Type")
                
            return True
            
        except Exception as e:
            try:
                report = GeneratedReport.objects.get(id=report_id)
                report.status = 'failed'
                report.filters_json['error'] = str(e)
                report.save()
            except: pass
            return False

    @classmethod
    def _generate_financial_summary(cls, report):
        """Query construction and export pipeline for complete revenue logs."""
        headers = ('Date', 'Period', 'Gross (USD)', 'Net (USD)', 'Transactions', 'Customers')
        
        data = tablib.Dataset(headers=headers, title="Financial Analytics")
        
        # Collect all rollup data
        records = RevenueSnapshot.objects.all().order_by('-snapshot_date')
        
        for row in records:
            data.append((
                row.snapshot_date.strftime("%Y-%m-%d"),
                row.period,
                row.gross_revenue_cents / 100.0,
                row.net_revenue_cents / 100.0,
                row.transaction_count,
                row.active_customers_count
            ))
            
        # Serialize final blob
        file_ext = report.output_format
        
        if file_ext == 'xlsx':
            file_content = data.export('xlsx')
        elif file_ext == 'csv':
            file_content = data.export('csv').encode('utf-8')
        else:
            file_content = data.export('csv').encode('utf-8')
            file_ext = 'csv'
            
        filename = f"report_financial_{report.id}.{file_ext}"
        
        # Save serialized content directly into FileField
        report.file_asset.save(filename, ContentFile(file_content))
        report.status = 'completed'
        report.completed_at = timezone.now()
        report.save()
