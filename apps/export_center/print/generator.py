from django.template.loader import render_to_string

class BrowserPrintRenderer:
    """
    Generates hyper-specialized standalone web pages configured strictly 
    for paper-directed presentation using standard system dialog calls.
    """
    
    @classmethod
    def render_financial_statement_html(cls, title, metrics, table_data):
        """Uses server-side template composition to blend styling matrix with data."""
        
        context = {
            'title': title,
            'metrics': metrics,
            'rows': table_data
        }
        
        # Pass off rendering into templated domain
        return render_to_string('export_center/print_statement.html', context)
