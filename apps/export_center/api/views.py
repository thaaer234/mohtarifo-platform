from django.http import HttpResponse, FileResponse
from django.views import View
from django.utils import timezone
from ..services.coordinator import ExportOrchestrationService

class TestDemoExportView(View):
    """
    Verification endpoint facilitating instantaneous end-to-end capability checks
    for all supported file serialization engines.
    """
    
    def get(self, request, format_type):
        """
        Renders dynamically generated simulated artifacts.
        Usage: /exports/test/excel/ or /exports/test/pdf/
        """
        
        # Formulate stable sample matrix representing analytical data
        mock_matrix = {
            'title': 'Consolidated CFO Summary',
            'summary_total': 845200.50,
            'summary_net': 730400.20,
            'summary_count': 1240,
            'grid_data': []
        }
        
        # Build a sequence of data rows for filling output grids
        base_date = timezone.now().date()
        for i in range(25):
            mock_matrix['grid_data'].append({
                'date': str(base_date - timezone.timedelta(days=i)),
                'count': 12 + i,
                'val': 1500.00 + (i * 25),
                'desc': f"Simulated Activity Log Batch {i+1000}"
            })

        # Fire Orchestration Engine
        content = ExportOrchestrationService.generate_export(format_type, mock_matrix)
        
        if format_type == 'excel':
            response = HttpResponse(
                content, 
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename="Executive_Finance_Grid.xlsx"'
            return response
            
        elif format_type == 'pdf':
            response = HttpResponse(content, content_type='application/pdf')
            # Render inline so browser opens immediately to show off styling
            response['Content-Disposition'] = 'inline; filename="CFO_Certification.pdf"'
            return response
            
        elif format_type == 'print':
            return HttpResponse(content) # Returns plain HTML for rendering
            
        else:
            return HttpResponse("Unsupported Type", status=400)
