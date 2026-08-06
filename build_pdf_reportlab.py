from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph, Image
from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from reportlab.lib.styles import getSampleStyleSheet
from svglib.svglib import svg2rlg
import io
import shutil
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QPushButton, QFileDialog, QHBoxLayout
)
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtPdfWidgets import QPdfView


def get_header(data):
    logo = Image("pdf/logo.png")
    target_height = 24 * mm

    aspect = logo.imageWidth / float(logo.imageHeight)
    logo.drawHeight = target_height
    logo.drawWidth = target_height * aspect

    header_data = [
        [logo, Paragraph(f"<para align='right'>{data['date']}</para>", getSampleStyleSheet()['Normal'])]
    ]
    
    usable_width = A4[0] - 2 * inch
    col_widths = [0.6 * usable_width, 0.4 * usable_width]
    
    header_table = Table(header_data, colWidths=col_widths)
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    
    return header_table

def get_info_table(data):
    info_data = [
        [Paragraph('<b>Produkt-ID</b>', getSampleStyleSheet()['Normal']), data['product_id'], Paragraph('<b>Batch nr.</b>', getSampleStyleSheet()['Normal']), data['batch_nr']],
        [Paragraph('<b>Produkt navn</b>', getSampleStyleSheet()['Normal']), data['product_name'], Paragraph('<b>Produceret</b>', getSampleStyleSheet()['Normal']), data['produced_date']],
        [Paragraph('<b>Kunde</b>', getSampleStyleSheet()['Normal']), data['customer'], Paragraph('<b>Udført af</b>', getSampleStyleSheet()['Normal']), data['preformed_by']],
    ]

    usable_width = A4[0] - 2 * inch
    col_widths = [0.22 * usable_width, 0.37 * usable_width, 0.22 * usable_width, 0.19 * usable_width]
    
    info_table = Table(info_data, colWidths=col_widths)
    info_table.setStyle(TableStyle([
        ('TOPPADDING', (0,0), (-1,-1), 3), 
        ('BOTTOMPADDING', (0,0), (-1,-1), -3),
        
        ('GRID', (0,0), (-1,-1), 0, colors.transparent), 
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('LEFTPADDING', (0,0), (-1,-1), 0), 
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('VALIGN', (0,0), (-1,-1), 'TOP'), 
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
    ]))
    
    return info_table

def get_properties_row(data):
    density_text = f"{data['density']} (kg/m&sup3;)"

    properties_data = [
        [Paragraph('<b>Pulverandel</b>', getSampleStyleSheet()['Normal']), f"{data['dust']} (g)", Paragraph('<b>Densitet</b>', getSampleStyleSheet()['Normal']), density_text],
    ]
    
    usable_width = A4[0] - 2 * inch
    col_widths = [0.3 * usable_width, 0.2 * usable_width, 0.3 * usable_width, 0.2 * usable_width]

    styled_properties_data = [
        [cell if type(cell) is Paragraph else Paragraph(str(cell), getSampleStyleSheet()['Normal']) for cell in row]
        for row in properties_data
    ]

    prop_table = Table(styled_properties_data, colWidths=col_widths)
    prop_table.setStyle(TableStyle([
        ('TOPPADDING', (0,0), (-1,-1), 3), 
        ('BOTTOMPADDING', (0,0), (-1,-1), -3), 
        
        ('GRID', (0,0), (-1,-1), 0, colors.transparent),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'), 
    ]))
    
    return prop_table

def get_sieve_table(data):
    headers = [
        ['Maskevidde', 'Sigterest', 'Fordeling', 'Gennemfald', 'Nedre', 'Øvre'],
        ['(mm)', '(g)', '%', '%', '%', '%']
    ]
    
    table_data = headers + data['sieve_rows']

    usable_width = A4[0] - 2 * inch
    col_width = usable_width / 6 
    col_widths = [col_width] * 6

    sieve_table = Table(table_data, colWidths=col_widths, repeatRows=2)
    sieve_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        ('GRID', (0, 0), (-1, -1), 0, colors.transparent), 
        
        ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 1), colors.black),
        ('TEXTCOLOR', (0, 0), (-1, 1), colors.white),
    ]))
    
    return sieve_table

def get_svg_graph(svg_path):
    drawing = svg2rlg(svg_path)
    
    usable_width = A4[0] - 2 * inch
    
    scale_factor = usable_width / drawing.width * 0.9
    
    drawing.width = drawing.width * scale_factor
    drawing.height = drawing.height * scale_factor
    drawing.scale(scale_factor, scale_factor)
    
    return drawing

def get_horizontal_rule():
    thickness=0.5
    color=colors.black
    padding=0

    data = [['']]
    usable_width = A4[0] - 2 * inch
    
    rule_table = Table(data, colWidths=[usable_width])
    
    style = TableStyle([
        ('LINEBELOW', (0, 0), (0, 0), thickness, color),
        ('BOTTOMPADDING', (0, 0), (0, 0), padding),
        ('TOPPADDING', (0, 0), (0, 0), -5),
    ])
    rule_table.setStyle(style)
    return rule_table

def build_pdf(data):
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        title="Sieve Analysis Report",
        leftMargin=inch,
        rightMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
    )
    
    elements = []
    
    elements.append(get_header(data))
    
    elements.append(Spacer(1, 0.1 * inch))
    elements.append(get_horizontal_rule())
    elements.append(Spacer(1, 0.1 * inch))
    
    elements.append(get_info_table(data))

    elements.append(Spacer(1, 0.1 * inch))
    elements.append(get_horizontal_rule())
    elements.append(Spacer(1, 0.1 * inch))
    
    elements.append(get_properties_row(data))
    
    elements.append(Spacer(1, 0.2 * inch))
    
    elements.append(get_sieve_table(data))

    svg_graph = get_svg_graph("pdf/graph.svg")
    
    usable_width = A4[0] - 2 * inch
    graph_table = Table([[svg_graph]], colWidths=[usable_width])
    graph_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (0,0), 'CENTER'),
        ('VALIGN', (0,0), (0,0), 'MIDDLE'),
    ]))
    
    elements.append(graph_table)

    doc.build(elements)

    with open("pdf/output.pdf", 'wb') as f:
        f.write(buffer.getvalue())
    
    viewer = PdfViewerDialog("pdf/output.pdf")
    viewer.exec()

class PdfViewerDialog(QDialog):
    def __init__(self, pdf_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PDF Viewer")
        self.resize(800, 600)
        self.pdf_path = pdf_path

        main_layout = QVBoxLayout(self)
        button_layout = QHBoxLayout()

        self.pdf_view = QPdfView(self)
        main_layout.addWidget(self.pdf_view)
        
        self.document = QPdfDocument(self)
        self.pdf_view.setDocument(self.document)

        load_status = self.document.load(pdf_path)
        if load_status == QPdfDocument.Status.Ready:
            self.pdf_view.setPageMode(QPdfView.PageMode.SinglePage)
            self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitInView)
            self.pdf_view.setPage(0)

        save_button = QPushButton("Save As…")
        save_button.clicked.connect(self.save_pdf)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)

        button_layout.addWidget(save_button)
        button_layout.addStretch()
        button_layout.addWidget(close_button)

        main_layout.addLayout(button_layout)

    def save_pdf(self):
        if not self.pdf_path:
            return

        target_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save PDF As",
            "copy.pdf",
            "PDF Files (*.pdf)"
        )

        if target_path:
            try:
                shutil.copy(self.pdf_path, target_path)
                print(f"Saved PDF to: {target_path}")
            except Exception as e:
                print(f"Error saving PDF: {e}")