import io
import os
from typing import Dict, Any, List
import pandas as pd
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer
)
from reportlab.lib.styles import ParagraphStyle
from .base_generator import BasePDFGenerator
from utils.excel_handler import parse_arg_number, format_arg_currency

class YPFIADEPDFGenerator(BasePDFGenerator):
    """Generador para el certificado YPF NOC - IADE (Reparaciones de Equipos)."""

    def build_pdf(
        self,
        buffer: io.BytesIO,
        metadata: Dict[str, Any],
        df_data: pd.DataFrame,
        options: Dict[str, Any]
    ) -> bytes:
        doc = SimpleDocTemplate(
            buffer,
            pagesize=self.page_size,
            leftMargin=self.margin + 12,
            rightMargin=self.margin + 12,
            topMargin=self.margin + 12,
            bottomMargin=self.margin + 12
        )
        story = []
        available_width = self.content_width - 24

        # 1. ENCABEZADO
        style_h1 = ParagraphStyle(
            "YPF_H1",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13
        )
        style_h2 = ParagraphStyle(
            "YPF_H2",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12
        )

        titulo = metadata.get("titulo", "REPARACIONES DE EQUIPOS")
        contrato_sap = metadata.get("contrato_sap", "4900102848")
        almacen = metadata.get("almacen", "NOC")

        header_left = [
            Paragraph(titulo, style_h1),
            Spacer(1, 4),
            Paragraph(f"Contrato SAP: {contrato_sap}", style_h2),
            Paragraph(f"ALMACEN: {almacen}", style_h2),
        ]

        logo_flowable = self.get_logo_flowable(width=140, height=32)
        if not logo_flowable:
            logo_flowable = Paragraph("<b>SULLAIR ARGENTINA</b>", self.style_cell_bold_right)

        header_table = Table(
            [[header_left, logo_flowable]],
            colWidths=[available_width - 160, 160]
        )
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 14))

        # 2. TABLA IADE CON ENCABEZADO NEGRO Y TEXTO BLANCO
        col_names = [
            "IADE",
            "EQUIPO",
            "INTERNO",
            "ALMACEN",
            "REPUESTOS (USD)",
            "MANO DE OBRA Y REPARACIONES (USD)",
            "TOTAL REP.+ MO",
            "DETALLE"
        ]
        
        # Proporciones de columnas
        weights = [0.09, 0.17, 0.08, 0.07, 0.12, 0.13, 0.12, 0.22]
        col_widths = [available_width * w for w in weights]

        header_cells = [
            Paragraph(f"<b>{col_names[0]}</b>", self.style_th_white_center),
            Paragraph(f"<b>{col_names[1]}</b>", self.style_th_white_center),
            Paragraph(f"<b>{col_names[2]}</b>", self.style_th_white_center),
            Paragraph(f"<b>{col_names[3]}</b>", self.style_th_white_center),
            Paragraph(f"<b>{col_names[4]}</b>", self.style_th_white_center),
            Paragraph(f"<b>{col_names[5]}</b>", self.style_th_white_center),
            Paragraph(f"<b>{col_names[6]}</b>", self.style_th_white_center),
            Paragraph(f"<b>{col_names[7]}</b>", self.style_th_white_center),
        ]
        table_rows = [header_cells]

        total_general = 0.0

        for _, r in df_data.iterrows():
            if not r.get("_incluir", True):
                continue

            iade_val = str(r.get("IADE", "-")).replace(".0", "")
            equipo_val = str(r.get("EQUIPO", "-"))
            interno_val = str(r.get("INTERNO", "-"))
            almacen_val = str(r.get("ALMACEN", almacen))
            
            rep_num = parse_arg_number(r.get("REPUESTOS (USD)", 0))
            mo_num = parse_arg_number(r.get("MANO DE OBRA Y REPARACIONES (USD)", 0))
            
            tot_num = parse_arg_number(r.get("TOTAL REP.+ MO", 0))
            if tot_num == 0.0 and (rep_num > 0 or mo_num > 0):
                tot_num = rep_num + mo_num
            total_general += tot_num

            detalle_val = str(r.get("DETALLE", "-"))

            row_cells = [
                self.format_cell(iade_val, align="CENTER"),
                self.format_cell(equipo_val, align="LEFT"),
                self.format_cell(interno_val, align="CENTER"),
                self.format_cell(almacen_val, align="CENTER"),
                self.format_cell(format_arg_currency(rep_num, symbol="USD"), align="RIGHT"),
                self.format_cell(format_arg_currency(mo_num, symbol="USD"), align="RIGHT"),
                self.format_cell(format_arg_currency(tot_num, symbol="USD"), align="RIGHT"),
                self.format_cell(detalle_val, align="LEFT"),
            ]
            table_rows.append(row_cells)

        # Fila vacía de resguardo
        if len(table_rows) == 1:
            table_rows.append([self.format_cell("-", align="CENTER") for _ in col_names])

        # Fila de SUBTOTAL
        subtotal_label = metadata.get("subtotal_label", "SUBTOTOTAL")
        footer_cells = [
            Paragraph(f"<b>{subtotal_label}</b>", self.style_cell_bold_right),
            "", "", "", "", "", # Celdas que se fusionan
            Paragraph("<b>USD</b>", self.style_cell_bold_center),
            Paragraph(f"<b>{format_arg_currency(total_general, symbol='', include_symbol=False)}</b>", self.style_cell_bold_right)
        ]
        table_rows.append(footer_cells)
        subtotal_row_idx = len(table_rows) - 1

        # Construcción y estilo de la tabla
        iade_table = Table(table_rows, colWidths=col_widths)
        t_style = [
            # Encabezado negro
            ('BACKGROUND', (0, 0), (-1, 0), colors.black),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, subtotal_row_idx - 1), 1, colors.black),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            # Fila de subtotal
            ('SPAN', (0, subtotal_row_idx), (5, subtotal_row_idx)),
            ('GRID', (0, subtotal_row_idx), (-1, subtotal_row_idx), 1, colors.black),
            ('BACKGROUND', (0, subtotal_row_idx), (-1, subtotal_row_idx), colors.HexColor("#F9FAFB")),
        ]
        iade_table.setStyle(TableStyle(t_style))
        story.append(iade_table)

        # Construir documento: si trim_frame es True, cerrar el marco al final del contenido
        trim_frame = options.get("trim_frame", True)
        if trim_frame:
            story.append(self.get_closing_box_flowable(bottom_padding=12))
            doc.build(story)
        else:
            doc.build(story, onFirstPage=self.draw_outer_frame, onLaterPages=self.draw_outer_frame)
        return buffer.getvalue()
