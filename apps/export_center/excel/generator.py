import io
import xlsxwriter
from datetime import datetime
from .styler import ExcelEnterpriseStyler

class EnterpriseExcelBuilder:
    """
    High-fidelity XLS Generation Factory utilizing native byte streams for 
    extreme performance serialization, incorporating embedded visualizations 
    and conditional formatting schemas.
    """
    
    def __init__(self, title="Executive Financial Statement"):
        self.output = io.BytesIO()
        self.workbook = xlsxwriter.Workbook(self.output, {'in_memory': True})
        self.formats = ExcelEnterpriseStyler.register_formats(self.workbook)
        self.title = title
        
    def build_financial_summary_workbook(self, summary_data, detail_records):
        """Assembles top-level composite workbook with rich visualization cover."""
        # 1. Executive Cover Sheet
        summary_sheet = self.workbook.add_worksheet("Executive Overview")
        self._render_executive_cover(summary_sheet, summary_data)
        
        # 2. Discrete Transaction Data
        data_sheet = self.workbook.add_worksheet("Detailed Logs")
        self._render_detailed_grid(data_sheet, detail_records)
        
        # 3. Inject visual chart layer referencing the grid
        self._add_revenue_trend_chart(summary_sheet, "Detailed Logs", len(detail_records))
        
        self.workbook.close()
        self.output.seek(0)
        return self.output.read()

    def _render_executive_cover(self, sheet, data):
        """Draws dashboard style matrix layout on first worksheet."""
        sheet.hide_gridlines(2) # Hide all default lines for canvas look
        
        # Dimensions & Header Row
        sheet.set_column('A:A', 2)   # Left margin spacer
        sheet.set_column('B:G', 18)
        
        sheet.write('B2', self.title.upper(), self.formats['title'])
        sheet.write('B3', f"Generated Cycle: {datetime.now().strftime('%Y-%m-%d %H:%M')}", self.formats['card_label'])
        
        # Drawing Composite Metric Cards via simple placement logic
        start_row = 5
        
        metrics = [
            ("Total Gross Revenue", data.get('total_revenue', 0), 'B'),
            ("Net Profit Margin", data.get('net_profit', 0), 'D'),
            ("Subscriber Base", data.get('active_subs', 0), 'F')
        ]
        
        for label, val, col in metrics:
            sheet.write(f"{col}{start_row}", label, self.formats['card_label'])
            sheet.write(f"{col}{start_row + 1}", val, self.formats['metric_val'])
            
        # Informational placeholder for chart destination
        sheet.write('B9', 'HISTORICAL PERFORMANCE TRAJECTORY', self.formats['tbl_hdr'])
        sheet.merge_range('B9:G9', 'HISTORICAL PERFORMANCE TRAJECTORY', self.formats['tbl_hdr'])

    def _render_detailed_grid(self, sheet, records):
        """Builds industrial hardened table with filters and fixed pane positions."""
        sheet.freeze_panes(1, 0) # Freeze Top Row
        
        headers = ['Processing Date', 'Item Count', 'Currency', 'Gross Metric', 'Status Indicator']
        sheet.set_column('A:E', 20)
        
        for idx, h in enumerate(headers):
            sheet.write(0, idx, h, self.formats['tbl_hdr'])
            
        r_idx = 1
        for item in records:
            sheet.write(r_idx, 0, item['date'], self.formats['cell_std'])
            sheet.write(r_idx, 1, item['count'], self.formats['cell_std'])
            sheet.write(r_idx, 2, "USD", self.formats['cell_std'])
            sheet.write(r_idx, 3, item['val'], self.formats['cell_curr'])
            
            # Conditional Logic Render
            stat_format = self.formats['positive_pill'] if item['val'] > 1000 else self.formats['cell_std']
            sheet.write(r_idx, 4, "NOMINAL" if item['val'] > 1000 else "LOW", stat_format)
            
            r_idx += 1
            
        # Autofilters activate excel native dropdown controls
        sheet.autofilter(0, 0, r_idx - 1, len(headers) - 1)

    def _add_revenue_trend_chart(self, dashboard_sheet, source_sheet_name, data_count):
        """Creates dynamic native Excel chart linked automatically to data sheets."""
        if data_count == 0: return
        
        chart = self.workbook.add_chart({'type': 'line'})
        
        # Configure high quality visual look
        chart.add_series({
            'name': 'Daily Growth',
            'categories': f"='{source_sheet_name}'!$A$2:$A${data_count+1}",
            'values':     f"='{source_sheet_name}'!$D$2:$D${data_count+1}",
            'line':       {'color': '#C5A059', 'width': 2.5},
            'smooth':     True
        })
        
        chart.set_style(10)
        chart.set_size({'width': 720, 'height': 340})
        chart.set_legend({'position': 'none'})
        
        chart.set_x_axis({'num_font':  {'name': 'Calibri', 'size': 9, 'color': '#64748B'}})
        chart.set_y_axis({'major_gridlines': {'visible': True, 'line': {'color': '#F1F5F9'}}})
        
        # Insert Chart onto floating Dashboard Cover layout below metrics
        dashboard_sheet.insert_chart('B10', chart, {'x_offset': 0, 'y_offset': 5})
