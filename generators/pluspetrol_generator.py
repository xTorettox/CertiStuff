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

class PluspetrolPDFGenerator(BasePDFGenerator):
    """Generador para el certificado de alquiler de Pluspetrol con tabla de equipos y otros cargos opcional."""

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
        style_title = ParagraphStyle(
            "Plus_Title",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=13
        )
        style_meta_label = ParagraphStyle(
            "Plus_MetaLabel",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12
        )
        style_meta_val = ParagraphStyle(
            "Plus_MetaVal",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12
        )

        cert_nro = metadata.get("certificado_nro", "112")
        cliente = metadata.get("cliente", "PLUSPETROL S.A.")
        obra = metadata.get("obra", "Yacimiento La Calera")
        periodo = metadata.get("periodo", "01/10/2026 al 31/10/2026")
        oc_np = metadata.get("oc_np", "4500987621")

        meta_left_rows = [
            [Paragraph("CERTIFICACION DE SERVICIOS - ALQUILER EQUIPOS", style_title), ""],
            [Spacer(1, 4), Spacer(1, 4)],
            [Paragraph("Certificado N°:", style_meta_label), Paragraph(str(cert_nro), style_meta_val)],
            [Paragraph("Cliente:", style_meta_label), Paragraph(f"{cliente}&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>Obra:</b> {obra}", style_meta_val)],
            [Paragraph("Periodo:", style_meta_label), Paragraph(f"{periodo}&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>OC/NP N°:</b> {oc_np}", style_meta_val)]
        ]
        t_meta_left = Table(meta_left_rows, colWidths=[90, available_width - 250])
        t_meta_left.setStyle(TableStyle([
            ('SPAN', (0, 0), (1, 0)),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))

        logo_flowable = self.get_logo_flowable(width=140, height=32)
        if not logo_flowable:
            logo_flowable = Paragraph("<b>SULLAIR ARGENTINA</b>", self.style_cell_bold_right)

        header_table = Table(
            [[t_meta_left, logo_flowable]],
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
        story.append(Spacer(1, 12))

        # 2. TABLA PRINCIPAL DE EQUIPOS
        col_names = [
            "EQUIPO",
            "MARCA",
            "MODELO",
            "INTERNO",
            "CANT DIAS",
            "INICIO PERIODO",
            "FIN PERIODO",
            "TARIFA DIARIO",
            "TARIFA TOTAL (USD)"
        ]
        weights = [0.22, 0.10, 0.10, 0.08, 0.08, 0.10, 0.10, 0.10, 0.12]
        col_widths = [available_width * w for w in weights]

        header_cells = [Paragraph(f"<b>{col}</b>", self.style_th_black_center) for col in col_names]
        table_rows = [header_cells]

        total_equipos = 0.0

        for _, r in df_data.iterrows():
            if not r.get("_incluir", True):
                continue

            eq = str(r.get("EQUIPO", "-"))
            marca = str(r.get("MARCA", "-"))
            mod = str(r.get("MODELO", "-"))
            interno = str(r.get("INTERNO", "-"))
            dias_val = r.get("CANT DIAS", r.get("DÍAS ALQ", 0))
            inicio = str(r.get("INICIO PERIODO", r.get("INICIO", "-")))
            fin = str(r.get("FIN PERIODO", r.get("FIN", "-")))
            tarifa_d = parse_arg_number(r.get("TARIFA DIARIO", r.get("TARIFA", 0)))
            
            tot_val = r.get("TARIFA TOTAL (USD)", r.get("TOTAL", None))
            if tot_val is not None and str(tot_val).strip() != "" and str(tot_val).strip() != "-":
                tot_item = parse_arg_number(tot_val)
            else:
                dias_num = parse_arg_number(dias_val)
                tot_item = dias_num * tarifa_d

            total_equipos += tot_item

            row_cells = [
                self.format_cell(eq, align="LEFT"),
                self.format_cell(marca, align="CENTER"),
                self.format_cell(mod, align="CENTER"),
                self.format_cell(interno, align="CENTER"),
                self.format_cell(str(dias_val), align="CENTER"),
                self.format_cell(inicio, align="CENTER"),
                self.format_cell(fin, align="CENTER"),
                self.format_cell(format_arg_currency(tarifa_d, symbol="", include_symbol=False), align="RIGHT"),
                self.format_cell(format_arg_currency(tot_item, symbol="USD"), align="RIGHT"),
            ]
            table_rows.append(row_cells)

        if len(table_rows) == 1:
            table_rows.append([self.format_cell("-", align="CENTER") for _ in col_names])

        equipos_table = Table(table_rows, colWidths=col_widths)
        equipos_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 3.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
        ]))
        story.append(equipos_table)
        story.append(Spacer(1, 10))

        # 3. TABLA OPCIONAL DE OTROS CARGOS
        total_otros_cargos = 0.0
        include_other_charges = options.get("include_other_charges", False)
        other_charges_data = metadata.get("otros_cargos_df", None)

        if include_other_charges and other_charges_data is not None and not other_charges_data.empty:
            oc_title = Paragraph("<b>OTROS CARGOS Y SERVICIOS ASOCIADOS</b>", style_meta_label)
            story.append(oc_title)
            story.append(Spacer(1, 4))

            oc_cols = ["CONCEPTO", "CANTIDAD", "TARIFA UNIT (USD)", "SUBTOTAL (USD)"]
            oc_widths = [available_width * w for w in [0.55, 0.15, 0.15, 0.15]]
            oc_rows = [[Paragraph(f"<b>{c}</b>", self.style_th_black_center) for c in oc_cols]]

            for _, ocr in other_charges_data.iterrows():
                conc = str(ocr.get("CONCEPTO", "-"))
                cant = parse_arg_number(ocr.get("CANTIDAD", 1))
                tarifa_u = parse_arg_number(ocr.get("TARIFA UNIT (USD)", 0))
                sub_oc = cant * tarifa_u
                total_otros_cargos += sub_oc

                oc_rows.append([
                    self.format_cell(conc, align="LEFT"),
                    self.format_cell(f"{cant:g}", align="CENTER"),
                    self.format_cell(format_arg_currency(tarifa_u, symbol="", include_symbol=False), align="RIGHT"),
                    self.format_cell(format_arg_currency(sub_oc, symbol="USD"), align="RIGHT"),
                ])

            t_oc = Table(oc_rows, colWidths=oc_widths)
            t_oc.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
            ]))
            story.append(t_oc)
            story.append(Spacer(1, 8))

        # 4. CUADRO RESUMEN DE TOTALES Y PIE CON FIRMA
        total_final = total_equipos + total_otros_cargos

        # Cuadro de totales a la derecha
        summary_rows = [
            [Paragraph("Subtotal Equipos:", self.style_cell_left), Paragraph(format_arg_currency(total_equipos, symbol="USD"), self.style_cell_bold_right)],
        ]
        if include_other_charges and total_otros_cargos > 0:
            summary_rows.append([Paragraph("Subtotal Otros Cargos:", self.style_cell_left), Paragraph(format_arg_currency(total_otros_cargos, symbol="USD"), self.style_cell_bold_right)])
        summary_rows.append([Paragraph("<b>TOTAL GENERAL (USD):</b>", self.style_cell_bold_left), Paragraph(f"<b>{format_arg_currency(total_final, symbol='USD')}</b>", self.style_cell_bold_right)])

        t_summary = Table(summary_rows, colWidths=[130, 110])
        t_summary.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#E2E8F0")),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))

        # Observaciones a la izquierda
        obs_text = metadata.get("observacion", "")
        obs_box = [
            Paragraph("<b>Observaciones:</b>", style_meta_label),
            Spacer(1, 2),
            Paragraph(obs_text if obs_text else "-", self.style_cell_left)
        ]

        # Bloque de firma
        signer_name = metadata.get("firmante_nombre", "Federico García Cendra")
        signer_role = metadata.get("firmante_cargo", "Comercial Alquileres")
        show_sig = options.get("show_signature", True)
        sig_source = metadata.get("firma_source") or metadata.get("firma_base64")
        sig_flowable = self.get_signature_flowable(signer_name, signer_role, width=125, height=44, sig_img_source=sig_source) if show_sig else Paragraph("", self.style_normal)

        bottom_table = Table(
            [[obs_box, sig_flowable, t_summary]],
            colWidths=[available_width - 400, 160, 240]
        )
        bottom_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (0, 0), 'TOP'),
            ('VALIGN', (1, 0), (-1, -1), 'BOTTOM'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(bottom_table)

        # Construir documento: si trim_frame es True, cerrar el marco al final del contenido
        trim_frame = options.get("trim_frame", True)
        if trim_frame:
            story.append(self.get_closing_box_flowable(bottom_padding=12))
            doc.build(story)
        else:
            doc.build(story, onFirstPage=self.draw_outer_frame, onLaterPages=self.draw_outer_frame)
        return buffer.getvalue()
