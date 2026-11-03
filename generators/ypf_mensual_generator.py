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
from utils.excel_handler import parse_arg_number, format_arg_currency, format_decimal

class YPFMensualPDFGenerator(BasePDFGenerator):
    """Generador para el certificado mensual de alquileres YPF NOC."""

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
        style_title_center = ParagraphStyle(
            "YPFM_Center",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=13,
            alignment=1 # Center
        )
        style_meta = ParagraphStyle(
            "YPFM_Meta",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12
        )

        titulo = metadata.get("titulo", "SERVICIO ALQUILER DE EQUIPOS")
        contrato_sap = metadata.get("contrato_sap", "4900114308")
        almacen = metadata.get("almacen", "NOC")
        periodo = metadata.get("periodo", "21/09/2026 al 20/10/2026")

        logo_flowable = self.get_logo_flowable(width=140, height=32)
        if not logo_flowable:
            logo_flowable = Paragraph("<b>SULLAIR ARGENTINA</b>", self.style_cell_bold_right)

        # Fila superior: Título centrado con logo a la derecha
        top_row = Table(
            [[Paragraph("", self.style_normal), Paragraph(titulo, style_title_center), logo_flowable]],
            colWidths=[100, available_width - 260, 160]
        )
        top_row.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(top_row)
        story.append(Spacer(1, 4))

        # Metadatos a la izquierda
        meta_block = [
            Paragraph(f"Contrato SAP: {contrato_sap}", style_meta),
            Paragraph(f"Almacen: {almacen}", style_meta),
            Paragraph(f"Periodo: {periodo}", style_meta),
        ]
        meta_table = Table([[meta_block]], colWidths=[available_width])
        meta_table.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 12))

        # 2. TABLA DE SERVICIOS
        show_dates_opt = options.get("show_dates", True)
        has_dates = False
        for _, r in df_data.iterrows():
            per_val = str(r.get("PERIODO", "") or "").strip()
            if per_val not in ["", "-", "nan", "None"]:
                has_dates = True
                break
        show_dates = show_dates_opt and has_dates

        show_tariffs_opt = options.get("show_tariffs", True)
        has_tariffs = False
        for _, r in df_data.iterrows():
            t_num = parse_arg_number(r.get("TARIFA", 0))
            tot_num = parse_arg_number(r.get("TOTAL", 0))
            if t_num > 0 or tot_num > 0:
                has_tariffs = True
                break
        show_tariffs = show_tariffs_opt and has_tariffs

        # Construir columnas dinámicamente
        if show_dates and show_tariffs:
            col_names = ["POSICIÓN", "LINEA", "U.M", "DESCRIPCION", "PERIODO", "CANTIDAD", "TARIFA", "TOTAL"]
            weights = [0.08, 0.07, 0.06, 0.38, 0.11, 0.09, 0.10, 0.11]
        elif show_dates and not show_tariffs:
            col_names = ["POSICIÓN", "LINEA", "U.M", "DESCRIPCION", "PERIODO", "CANTIDAD"]
            weights = [0.10, 0.09, 0.08, 0.50, 0.12, 0.11]
        elif not show_dates and show_tariffs:
            col_names = ["POSICIÓN", "LINEA", "U.M", "DESCRIPCION", "CANTIDAD", "TARIFA", "TOTAL"]
            weights = [0.09, 0.08, 0.07, 0.44, 0.10, 0.11, 0.11]
        else:
            col_names = ["POSICIÓN", "LINEA", "U.M", "DESCRIPCION", "CANTIDAD"]
            weights = [0.11, 0.10, 0.09, 0.58, 0.12]

        col_widths = [available_width * w for w in weights]
        header_cells = [Paragraph(f"<b>{col}</b>", self.style_th_black_center) for col in col_names]
        table_rows = [header_cells]

        total_general = 0.0

        for _, r in df_data.iterrows():
            if not r.get("_incluir", True):
                continue

            pos = str(r.get("POSICIÓN", "-")).replace(".0", "")
            lin = str(r.get("LINEA", "-")).replace(".0", "")
            um = str(r.get("U.M", "MES"))
            desc = str(r.get("DESCRIPCION", "-"))
            per = str(r.get("PERIODO", "-"))

            cant_val = r.get("CANTIDAD", 1.0)
            tarifa_val = r.get("TARIFA", 0.0)
            tot_val = r.get("TOTAL", None)

            cant_num = parse_arg_number(cant_val)
            tarifa_num = parse_arg_number(tarifa_val)
            
            if tot_val is not None and str(tot_val).strip() != "" and str(tot_val).strip() != "-":
                tot_num = parse_arg_number(tot_val)
            else:
                tot_num = cant_num * tarifa_num

            total_general += tot_num

            row_cells = [
                self.format_cell(pos, align="CENTER"),
                self.format_cell(lin, align="CENTER"),
                self.format_cell(um, align="CENTER"),
                self.format_cell(desc, align="LEFT"),
            ]
            if show_dates:
                row_cells.append(self.format_cell(per, align="CENTER"))
            row_cells.append(self.format_cell(format_decimal(cant_num, decimals=3), align="RIGHT"))
            if show_tariffs:
                row_cells.append(self.format_cell(format_arg_currency(tarifa_num, symbol="", include_symbol=False), align="RIGHT"))
                row_cells.append(self.format_cell(format_decimal(tot_num, decimals=3), align="RIGHT"))
            table_rows.append(row_cells)

        if len(table_rows) == 1:
            table_rows.append([self.format_cell("-", align="CENTER") for _ in col_names])

        # Fila del Subtotal / Total General USD (solo si show_tariffs está activo)
        if show_tariffs:
            blank_cols_count = len(col_names) - 2
            total_cells = ["" for _ in range(blank_cols_count)] + [
                Paragraph("<b>USD</b>", self.style_cell_bold_center),
                Paragraph(f"<b>{format_arg_currency(total_general, symbol='', include_symbol=False)}</b>", self.style_cell_bold_right)
            ]
            table_rows.append(total_cells)
            total_row_idx = len(table_rows) - 1

            mensual_table = Table(table_rows, colWidths=col_widths)
            mensual_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, total_row_idx - 1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('GRID', (blank_cols_count, total_row_idx), (-1, total_row_idx), 1, colors.black),
                ('BACKGROUND', (blank_cols_count, total_row_idx), (-1, total_row_idx), colors.HexColor("#F9FAFB")),
            ]))
        else:
            mensual_table = Table(table_rows, colWidths=col_widths)
            mensual_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))

        story.append(mensual_table)
        story.append(Spacer(1, 10))

        # 3. SECCIÓN DE OBSERVACIONES (Deducciones por fuera de servicio)
        obs_text = metadata.get("observaciones", metadata.get("observacion", ""))
        show_obs = options.get("show_observations", True)
        clean_obs = str(obs_text).strip() if obs_text and not pd.isna(obs_text) else ""
        if clean_obs.lower() in ["nan", "none", "null", "-"]:
            clean_obs = ""

        style_obs_title = ParagraphStyle(
            "YPF_ObsTitle",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11
        )
        style_obs_body = ParagraphStyle(
            "YPF_ObsBody",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10.5
        )

        if show_obs and clean_obs:
            obs_content = [Paragraph("<b>Obs:</b>", style_obs_title)]
            for line in clean_obs.split("\n"):
                if line.strip():
                    obs_content.append(Paragraph(line.strip(), style_obs_body))

            obs_box = Table([[obs_content]], colWidths=[available_width])
            obs_box.setStyle(TableStyle([
                ('BOX', (0, 0), (-1, -1), 1, colors.black),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(obs_box)
            story.append(Spacer(1, 8))

        # Si el usuario activa firma opcionalmente
        if options.get("show_signature", False):
            story.append(Spacer(1, 10))
            signer_name = metadata.get("firmante_nombre", "Federico García Cendra")
            signer_role = metadata.get("firmante_cargo", "Comercial Alquileres")
            sig_source = metadata.get("firma_source") or metadata.get("firma_base64")
            sig_flowable = self.get_signature_flowable(signer_name, signer_role, width=130, height=48, sig_img_source=sig_source)
            sig_table = Table([[Paragraph("", self.style_normal), sig_flowable]], colWidths=[available_width - 160, 160])
            sig_table.setStyle(TableStyle([
                ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(sig_table)

        # Construir documento: si trim_frame es True, cerrar el marco al final del contenido
        trim_frame = options.get("trim_frame", True)
        if trim_frame:
            story.append(self.get_closing_box_flowable(bottom_padding=12))
            doc.build(story)
        else:
            doc.build(story, onFirstPage=self.draw_outer_frame, onLaterPages=self.draw_outer_frame)
        return buffer.getvalue()
