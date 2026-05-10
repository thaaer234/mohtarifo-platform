class ExcelEnterpriseStyler:
    """
    Global registry of corporate aesthetics for high-fidelity BI spreadsheet rendering.
    Centralizes font weights, border radiuses (simulated), and executive color branding.
    """
    
    # Brand Identity Tokens
    COLORS = {
        'brand_dark': '#0F172A',   # Rich Slate Dark
        'brand_gold': '#C5A059',   # Metallic Accents
        'header_bg': '#F8FAFC',    # Light Subtle Wash
        'border_soft': '#E2E8F0',
        'positive': '#10B981',     # Emerald Green
        'negative': '#EF4444',     # Critical Red
        'muted': '#64748B'
    }
    
    FONTS = {
        'primary': 'Calibri',
        'header': 'Segoe UI',
    }

    @classmethod
    def register_formats(cls, workbook):
        """Registers standardized styling objects into workbook memory."""
        formats = {}
        
        # 1. Executive Cover Title
        formats['title'] = workbook.add_format({
            'bold': True,
            'font_name': cls.FONTS['header'],
            'font_size': 24,
            'font_color': cls.COLORS['brand_dark'],
            'align': 'left',
            'valign': 'vcenter'
        })
        
        # 2. Dashboard Card Label
        formats['card_label'] = workbook.add_format({
            'font_name': cls.FONTS['primary'],
            'font_size': 10,
            'font_color': cls.COLORS['muted'],
            'valign': 'bottom',
            'italic': False
        })
        
        # 3. Big Metric Number (Currency)
        formats['metric_val'] = workbook.add_format({
            'bold': True,
            'font_name': cls.FONTS['header'],
            'font_size': 16,
            'num_format': '$#,##0.00',
            'font_color': cls.COLORS['brand_dark'],
            'valign': 'top'
        })

        # 4. Standard Table Header (Professional/Dark)
        formats['tbl_hdr'] = workbook.add_format({
            'bold': True,
            'font_name': cls.FONTS['header'],
            'font_size': 11,
            'font_color': '#FFFFFF',
            'bg_color': cls.COLORS['brand_dark'],
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#1E293B'
        })

        # 5. Data Row Formats
        formats['cell_std'] = workbook.add_format({
            'font_name': cls.FONTS['primary'],
            'font_size': 10,
            'border': 1,
            'border_color': cls.COLORS['border_soft'],
            'valign': 'vcenter'
        })
        
        formats['cell_curr'] = workbook.add_format({
            'font_name': cls.FONTS['primary'],
            'font_size': 10,
            'num_format': '$#,##0.00',
            'border': 1,
            'border_color': cls.COLORS['border_soft'],
            'valign': 'vcenter'
        })
        
        formats['cell_pct'] = workbook.add_format({
            'font_name': cls.FONTS['primary'],
            'font_size': 10,
            'num_format': '0.00%',
            'border': 1,
            'border_color': cls.COLORS['border_soft'],
            'valign': 'vcenter',
            'align': 'right'
        })

        # 6. Highlight & Visual Indicator specific formats
        formats['positive_pill'] = workbook.add_format({
            'bg_color': '#D1FAE5',
            'font_color': '#065F46',
            'bold': True,
            'align': 'center',
            'border': 1,
            'border_color': cls.COLORS['border_soft']
        })
        
        formats['negative_pill'] = workbook.add_format({
            'bg_color': '#FEE2E2',
            'font_color': '#991B1B',
            'bold': True,
            'align': 'center',
            'border': 1,
            'border_color': cls.COLORS['border_soft']
        })

        return formats
