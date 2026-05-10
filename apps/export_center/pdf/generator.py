import io
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.units import cm

class PDFStatementBuilder:
    """
    Vector graphic calculation engine producing tamper-resistant PDF financial assets
    utilizing Platypus geometry managers for deterministic pagination flow.
    """
    
    def __init__(self, orientation='portrait'):
        self.output = io.BytesIO()
        self.page_size = A4 if orientation == 'portrait' else landscape(A4)
        self.doc = SimpleDocTemplate(
            self.output,
            pagesize=self.page_size,
            rightMargin=1.5*cm,
            leftMargin=1.5*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        self.styles = getSampleStyleSheet()
        self._register_custom_styles()
        
    def _register_custom_styles(self):
        """Configures premium typography layers matching system-wide aesthetics."""
        self.styles.add(ParagraphStyle(
            name='ExecutiveTitle',
            fontSize=22,
            leading=28,
            textColor=colors.HexColor('#0F172A'),
            fontName='Helvetica-Bold',
            spaceAfter=12
        ))
        self.styles.add(ParagraphStyle(
            name='SubHeaderMuted',
            fontSize=10,
            textColor=colors.HexColor('#64748B'),
            fontName='Helvetica',
            spaceAfter=20
        ))
        self.styles.add(ParagraphStyle(
            name='GridLabel',
            fontSize=14,
            textColor=colors.HexColor('#0F172A'),
            fontName='Helvetica-Bold',
            spaceAfter=8,
            spaceBefore=12
        ))

    def build_cfo_report(self, title, data_grid):
        """Sequences a composite story document containing text, spacing and logic grid."""
        story = []
        
        # 1. Header Identity
        story.append(Paragraph(title.upper(), self.styles['ExecutiveTitle']))
        story.append(Paragraph(f"Certified Executive Report | Issued: {datetime.now().strftime('%Y-%m-%d')}", self.styles['SubHeaderMuted']))
        story.append(Spacer(1, 0.5*cm))
        
        # 2. Main Table Grid
        story.append(Paragraph("Audit Detail Grid", self.styles['GridLabel']))
        
        table_style = TableStyle([
            # Header aesthetics
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('TOPPADDING', (0,0), (-1,0), 12),
            
            # Body data formatting
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,1), (-1,-1), 9),
            ('BOTTOMPADDING', (0,1), (-1,-1), 8),
            ('TOPPADDING', (0,1), (-1,-1), 8),
            ('TEXTCOLOR', (0,1), (-1,-1), colors.HexColor('#334155')),
            
            # Row Alternating Zebra effect
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
            
            # Framing
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            
            # Align monetary column to right
            ('ALIGN', (-1,0), (-1,-1), 'RIGHT') 
        ])
        
        # Auto compute width allocation
        w = self.page_size[0] - 3*cm
        col_widths = [w*0.2, w*0.4, w*0.2, w*0.2]
        
        t = Table(data_grid, colWidths=col_widths)
        t.setStyle(table_style)
        story.append(t)
        
        # Execute layout sequence
        self.doc.build(story, onFirstPage=self._header_footer, onLaterPages=self._header_footer)
        
        self.output.seek(0)
        return self.output.read()

    def _header_footer(self, canvas, doc):
        """Custom low-level canvas callback executing fixed frame rendering per page."""
        canvas.saveState()
        
        # Draw footer border
        canvas.setStrokeColor(colors.HexColor('#E2E8F0'))
        canvas.setLineWidth(0.5)
        canvas.line(1.5*cm, 1.5*cm, doc.pagesize[0] - 1.5*cm, 1.5*cm)
        
        # Write Page Count & Disclaimers
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#94A3B8'))
        
        page_str = f"Page {doc.page} | Proprietary Confidiential Intelligence"
        canvas.drawRightString(doc.pagesize[0] - 1.5*cm, 1.1*cm, page_str)
        
        # Branding watermark text
        canvas.drawString(1.5*cm, 1.1*cm, "SYSTEM FINANCE EXPORT ENGINE V2")
        
        canvas.restoreState()
