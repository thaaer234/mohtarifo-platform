from ..excel.generator import EnterpriseExcelBuilder
from ..pdf.generator import PDFStatementBuilder
from ..print.generator import BrowserPrintRenderer

class ExportOrchestrationService:
    """
    Central point-of-access mapping requested output formats to 
    the internal high-performance generative subsystems.
    """
    
    @classmethod
    def generate_export(cls, format_type, raw_data):
        """
        Gateway entrypoint translating domain objects into binary deliverables.
        """
        # Ensure input data adheres to minimum normalization
        title = raw_data.get('title', 'Financial Operation Summary')
        
        if format_type == 'excel':
            return cls._handle_excel(title, raw_data)
        elif format_type == 'pdf':
            return cls._handle_pdf(title, raw_data)
        elif format_type == 'print':
            return cls._handle_print(title, raw_data)
        else:
            raise ValueError(f"Format unsupported by modern engine: {format_type}")

    @classmethod
    def _handle_excel(cls, title, data):
        builder = EnterpriseExcelBuilder(title=title)
        
        # Normalize into summary metrics & iterative grid
        summary = {
            'total_revenue': data.get('summary_total', 0),
            'net_profit': data.get('summary_net', 0),
            'active_subs': data.get('summary_count', 0)
        }
        
        # Direct mapping expected by builder
        records = data.get('grid_data', []) 
        
        binary_content = builder.build_financial_summary_workbook(summary, records)
        return binary_content

    @classmethod
    def _handle_pdf(cls, title, data):
        builder = PDFStatementBuilder(orientation='portrait')
        
        # Map list of records to 2D raw list expected by ReportLab Table
        grid = [['REFERENCE ID', 'OPERATION', 'UNIT', 'BALANCE']] # Header
        
        for item in data.get('grid_data', []):
            grid.append([
                str(item.get('date', '')),
                item.get('desc', 'Unknown'),
                "1x",
                f"${float(item.get('val', 0)):,.2f}"
            ])
            
        return builder.build_cfo_report(title, grid)

    @classmethod
    def _handle_print(cls, title, data):
        metrics = {
            'Overall Balance': f"${data.get('summary_total', 0):,.2f}",
            'Distinct Events': data.get('summary_count', 0)
        }
        
        table = []
        for item in data.get('grid_data', []):
            table.append({
                'desc': item.get('desc', 'System Ref'),
                'cat': 'General Input',
                'amt': f"${float(item.get('val', 0)):,.2f}"
            })
            
        return BrowserPrintRenderer.render_financial_statement_html(title, metrics, table)
