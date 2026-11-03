import io
import os
from typing import Dict, Any, List
import pandas as pd
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    KeepTogether
)
from reportlab.lib.styles import ParagraphStyle
from .base_generator import BasePDFGenerator

class NaborsPDFGenerator(BasePDFGenerator):
    """Generador especializado para certificados de Nabors."""

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
        available_width = self.content_width - 24 # Espacio dentro del marco interior

        # 1. ENCABEZADO SUPERIOR (Dos columnas: Datos Certificado a la Izq, Sucursal Sullair a la Der)
        style_title = ParagraphStyle(
            "TitleNabors",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12
        )
        style_meta_label = ParagraphStyle(
            "MetaLabel",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12
        )
        style_meta_val = ParagraphStyle(
            "MetaVal",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12
        )
        style_sucursal_bold = ParagraphStyle(
            "SucursalBold",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            alignment=2 # Right
        )
        style_sucursal = ParagraphStyle(
            "Sucursal",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11.5,
            alignment=2 # Right
        )

        p_title1 = Paragraph("CERTIFICACION DE SERVICIOS", style_title)
        p_title2 = Paragraph("ALQUILER EQUIPOS", style_title)

        cert_nro = metadata.get("certificado_nro", "45")
        cliente = metadata.get("cliente", "NABORS")
        servicio = metadata.get("servicio", "F36")
        oc_np = metadata.get("oc_np", "19084416")

        # Tabla de metadatos izquierda
        meta_rows = [
            [p_title1, Paragraph("", self.style_normal)],
            [p_title2, Paragraph("", self.style_normal)],
            [Spacer(1, 4), Spacer(1, 4)],
            [Paragraph("<b>Certificado N°</b>", style_meta_label), Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{cert_nro}", style_meta_val)],
            [
                Paragraph("<b>Cliente</b>", style_meta_label),
                Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{cliente}&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>Servicio</b>&nbsp;&nbsp;&nbsp;&nbsp;{servicio}", style_meta_val)
            ],
            [Paragraph("<b>OC/NP N°</b>", style_meta_label), Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{oc_np}", style_meta_val)]
        ]
        t_meta_left = Table(meta_rows, colWidths=[120, 320])
        t_meta_left.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))

        # Bloque de sucursal derecha
        sucursal = metadata.get("sucursal", "Sucursal NQN y Valle")
        direccion = metadata.get("direccion", "Industriales Neuquinos 2920, PIN")
        telefono = metadata.get("telefono", "T:[0299] 4782500")

        sucursal_rows = [
            [Paragraph("SULLAIR ARGENTINA SA", style_sucursal_bold)],
            [Paragraph(sucursal, style_sucursal)],
            [Paragraph(direccion, style_sucursal)],
            [Paragraph(telefono, style_sucursal)]
        ]
        t_sucursal_right = Table(sucursal_rows, colWidths=[240])
        t_sucursal_right.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
        ]))

        header_table = Table([[t_meta_left, t_sucursal_right]], colWidths=[available_width - 250, 250])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 14))

        # 2. TABLA DINÁMICA DE EQUIPOS
        show_dates_opt = options.get("show_dates", True)
        has_dates = False
        for _, r in df_data.iterrows():
            ini = str(r.get("INICIO", "") or "").strip()
            fin = str(r.get("FIN", "") or "").strip()
            if ini not in ["", "-", "nan", "None"] or fin not in ["", "-", "nan", "None"]:
                has_dates = True
                break
        show_dates = show_dates_opt and has_dates

        if show_dates:
            col_headers = ["EQUIPO", "MARCA", "MODELO", "INICIO", "FIN", "DÍAS ALQ", "CANT EQUIPOS"]
            widths_prop = [0.34, 0.11, 0.11, 0.12, 0.12, 0.10, 0.10]
        else:
            col_headers = ["EQUIPO", "MARCA", "MODELO", "DÍAS ALQ", "CANT EQUIPOS"]
            widths_prop = [0.46, 0.14, 0.14, 0.13, 0.13]

        col_widths = [available_width * p for p in widths_prop]

        # Encabezado de la tabla
        header_row = [Paragraph(f"<b>{col}</b>", self.style_th_black_center) for col in col_headers]
        table_data = [header_row]

        # Llenar datos de la tabla
        for _, row in df_data.iterrows():
            if not row.get("_incluir", True):
                continue
            r_cells = []
            if show_dates:
                r_cells.append(self.format_cell(row.get("EQUIPO", "-"), align="LEFT"))
                r_cells.append(self.format_cell(row.get("MARCA", "-"), align="CENTER"))
                r_cells.append(self.format_cell(row.get("MODELO", "-"), align="CENTER"))
                r_cells.append(self.format_cell(row.get("INICIO", "-"), align="CENTER"))
                r_cells.append(self.format_cell(row.get("FIN", "-"), align="CENTER"))
                r_cells.append(self.format_cell(row.get("DÍAS ALQ", row.get("CANT DIAS", "-")), align="CENTER"))
                r_cells.append(self.format_cell(row.get("CANT EQUIPOS", row.get("CANTIDAD", "1")), align="CENTER"))
            else:
                r_cells.append(self.format_cell(row.get("EQUIPO", "-"), align="LEFT"))
                r_cells.append(self.format_cell(row.get("MARCA", "-"), align="CENTER"))
                r_cells.append(self.format_cell(row.get("MODELO", "-"), align="CENTER"))
                r_cells.append(self.format_cell(row.get("DÍAS ALQ", row.get("CANT DIAS", "-")), align="CENTER"))
                r_cells.append(self.format_cell(row.get("CANT EQUIPOS", row.get("CANTIDAD", "1")), align="CENTER"))
            table_data.append(r_cells)

        # Si no hay filas, mostrar fila vacía
        if len(table_data) == 1:
            table_data.append([self.format_cell("-", align="CENTER") for _ in col_headers])

        grid_table = Table(table_data, colWidths=col_widths)
        grid_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ]))
        story.append(grid_table)
        story.append(Spacer(1, 18))

        # 3. SECCIÓN INFERIOR: Observaciones a la izquierda, Firma y Logo a la derecha
        obs_text = metadata.get("observacion", "")
        show_obs = options.get("show_observations", True)
        clean_obs = str(obs_text).strip() if obs_text and not pd.isna(obs_text) else ""
        if clean_obs.lower() in ["nan", "none", "null", "-"]:
            clean_obs = ""

        style_obs_label = ParagraphStyle("ObsLabel", parent=self.styles["Normal"], fontName="Helvetica-Bold", fontSize=9, leading=12)
        style_obs_text = ParagraphStyle("ObsText", parent=self.styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=11)

        if show_obs and clean_obs:
            obs_flowable = [
                Paragraph("<b>Observación:</b>", style_obs_label),
                Spacer(1, 4),
                Paragraph(clean_obs, style_obs_text)
            ]
        else:
            obs_flowable = Paragraph("", self.style_normal)

        # Bloque de firma
        signer_name = metadata.get("firmante_nombre", "Federico García Cendra")
        signer_role = metadata.get("firmante_cargo", "Comercial Alquileres")
        show_sig = options.get("show_signature", True)
        sig_source = metadata.get("firma_source") or metadata.get("firma_base64")
        
        sig_flowable = self.get_signature_flowable(signer_name, signer_role, width=130, height=48, sig_img_source=sig_source) if show_sig else Paragraph("", self.style_normal)

        # Logo a la derecha
        logo_flowable = self.get_logo_flowable(width=135, height=30)
        if not logo_flowable:
            logo_flowable = Paragraph("<b>SULLAIR ARGENTINA</b>", self.style_cell_bold_center)

        footer_table = Table(
            [[obs_flowable, sig_flowable, logo_flowable]],
            colWidths=[available_width - 320, 160, 160]
        )
        footer_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (0, 0), 'TOP'),
            ('VALIGN', (1, 0), (-1, -1), 'BOTTOM'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))

        story.append(footer_table)

        # Construir documento: si trim_frame es True, cerrar el marco al final del contenido
        trim_frame = options.get("trim_frame", True)
        if trim_frame:
            story.append(self.get_closing_box_flowable(bottom_padding=12))
            doc.build(story)
        else:
            doc.build(story, onFirstPage=self.draw_outer_frame, onLaterPages=self.draw_outer_frame)
        return buffer.getvalue()
