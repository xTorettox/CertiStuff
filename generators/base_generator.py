import os
import io
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm, inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image as RLImage,
    KeepTogether,
    Flowable
)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

class DynamicBoxClosingFlowable(Flowable):
    """
    Flowable colocado al final de la lista de elementos para dibujar el marco
    perimetral negro exterior recortado exactamente donde finaliza el contenido
    (tablas, observaciones, firma y logo), evitando dejar grandes espacios vacíos
    que se presten a adulteraciones o llenados indebidos.
    """
    def __init__(
        self,
        left: float,
        top: float,
        width: float,
        bottom_padding: float = 12.0,
        min_bottom: float = 24.0,
        stroke_color=colors.black,
        line_width: float = 1.2
    ):
        super().__init__()
        self.width = 0
        self.height = 0
        self.left = left
        self.top = top
        self.box_width = width
        self.bottom_padding = bottom_padding
        self.min_bottom = min_bottom
        self.stroke_color = stroke_color
        self.line_width = line_width

    def wrap(self, availWidth, availHeight):
        return 0, 0

    def draw(self):
        pass

    def drawOn(self, canvas, x, y, _sW=0):
        super().drawOn(canvas, x, y, _sW)
        bottom_y = max(y - self.bottom_padding, self.min_bottom)
        box_height = self.top - bottom_y
        canvas.saveState()
        canvas.setStrokeColor(self.stroke_color)
        canvas.setLineWidth(self.line_width)
        canvas.rect(self.left, bottom_y, self.box_width, box_height, stroke=1, fill=0)
        canvas.restoreState()


class BasePDFGenerator(ABC):
    """
    Clase base abstracta para la generación de certificados en PDF de Sullair Argentina.
    Utiliza ReportLab para renderizado vectorial preciso, marco exterior y manejo de tablas.
    """

    def __init__(self, page_size=landscape(A4), margin_pt: float = 24.0):
        self.page_size = page_size
        self.page_width, self.page_height = page_size
        self.margin = margin_pt
        self.content_width = self.page_width - 2 * self.margin
        self.content_height = self.page_height - 2 * self.margin
        
        # Rutas de assets
        self.logo_path = os.path.join(ASSETS_DIR, "logo_sullair.png")
        self.default_sig_path = os.path.join(ASSETS_DIR, "firma_default.png")
        self.custom_sig_path = os.path.join(ASSETS_DIR, "firma_subida.png")
        
        # Inicializar estilos de texto
        self.styles = getSampleStyleSheet()
        self._init_custom_styles()

    def _init_custom_styles(self):
        """Inicializa estilos tipográficos de ReportLab."""
        self.style_normal = self.styles["Normal"]
        
        self.style_cell_left = ParagraphStyle(
            "CellLeft",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=0 # Left
        )
        self.style_cell_center = ParagraphStyle(
            "CellCenter",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=1 # Center
        )
        self.style_cell_right = ParagraphStyle(
            "CellRight",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=2 # Right
        )
        self.style_cell_bold_left = ParagraphStyle(
            "CellBoldLeft",
            parent=self.style_cell_left,
            fontName="Helvetica-Bold"
        )
        self.style_cell_bold_center = ParagraphStyle(
            "CellBoldCenter",
            parent=self.style_cell_center,
            fontName="Helvetica-Bold"
        )
        self.style_cell_bold_right = ParagraphStyle(
            "CellBoldRight",
            parent=self.style_cell_right,
            fontName="Helvetica-Bold"
        )
        
        # Encabezados de tabla blancos (para fondos oscuros)
        self.style_th_white_center = ParagraphStyle(
            "THWhiteCenter",
            parent=self.style_cell_center,
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9,
            textColor=colors.white
        )
        self.style_th_white_left = ParagraphStyle(
            "THWhiteLeft",
            parent=self.style_cell_left,
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9,
            textColor=colors.white
        )
        self.style_th_white_right = ParagraphStyle(
            "THWhiteRight",
            parent=self.style_cell_right,
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9,
            textColor=colors.white
        )

        # Encabezados de tabla negros (para fondos claros)
        self.style_th_black_center = ParagraphStyle(
            "THBlackCenter",
            parent=self.style_cell_center,
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.black
        )

    def draw_outer_frame(self, canvas, doc):
        """Dibuja el marco perimetral negro rectangular típico de los certificados Sullair."""
        canvas.saveState()
        canvas.setStrokeColor(colors.black)
        canvas.setLineWidth(1.2)
        # Rectángulo perimetral con margen exacto
        canvas.rect(
            self.margin,
            self.margin,
            self.content_width,
            self.content_height,
            stroke=1,
            fill=0
        )
        canvas.restoreState()

    def get_closing_box_flowable(self, bottom_padding: float = 12.0) -> DynamicBoxClosingFlowable:
        """Crea el Flowable para cerrar el marco al final exacto del contenido."""
        top_y = self.page_height - self.margin
        return DynamicBoxClosingFlowable(
            left=self.margin,
            top=top_y,
            width=self.content_width,
            bottom_padding=bottom_padding,
            min_bottom=self.margin
        )

    def get_logo_flowable(self, width: float = 140, height: float = 32) -> Optional[RLImage]:
        """Retorna un flowable de ReportLab con el logo corporativo de Sullair."""
        if os.path.exists(self.logo_path):
            try:
                img = RLImage(self.logo_path, width=width, height=height)
                return img
            except Exception as e:
                print(f"Error cargando logo Sullair: {e}")
        return None

    def get_signature_path(self) -> Optional[str]:
        """Obtiene la ruta de la firma a usar (personalizada o default)."""
        if os.path.exists(self.custom_sig_path):
            return self.custom_sig_path
        if os.path.exists(self.default_sig_path):
            return self.default_sig_path
        return None

    def get_signature_flowable(
        self,
        signer_name: str = "Federico García Cendra",
        signer_role: str = "Comercial Alquileres",
        width: float = 120,
        height: float = 48,
        sig_img_source: Optional[Any] = None
    ) -> Table:
        """Crea un bloque de firma con la imagen escaneada y texto de aclaración."""
        rows = []
        loaded_img = None
        
        # 1. Si se pasó una imagen en base64
        if sig_img_source and isinstance(sig_img_source, str) and "base64," in sig_img_source:
            try:
                import base64
                b64_data = sig_img_source.split("base64,")[1]
                img_bytes = io.BytesIO(base64.b64decode(b64_data))
                loaded_img = RLImage(img_bytes, width=width, height=height)
            except Exception as e:
                print(f"Error cargando firma desde base64: {e}")
        # 2. Si se pasó una ruta directa existente
        elif sig_img_source and isinstance(sig_img_source, str) and os.path.exists(sig_img_source):
            try:
                loaded_img = RLImage(sig_img_source, width=width, height=height)
            except Exception as e:
                print(f"Error cargando firma desde ruta {sig_img_source}: {e}")
        
        # 3. Fallback a rutas predeterminadas en assets
        if not loaded_img:
            sig_path = self.get_signature_path()
            if sig_path and os.path.exists(sig_path):
                try:
                    loaded_img = RLImage(sig_path, width=width, height=height)
                except Exception as e:
                    print(f"Error cargando firma default: {e}")

        rows.append([loaded_img if loaded_img else ""])

        # Nombre y Cargo
        p_name = Paragraph(f"<b>{signer_name}</b>", self.style_cell_center)
        p_role = Paragraph(signer_role, self.style_cell_center)
        rows.append([p_name])
        rows.append([p_role])

        table = Table(rows, colWidths=[width + 20])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
        ]))
        return table

    def format_cell(self, text: Any, align: str = "LEFT", bold: bool = False, textColor: Optional[colors.Color] = None) -> Paragraph:
        """Envuelve texto en un Paragraph para que no desborde las celdas de la tabla."""
        import re
        text_str = str(text) if text is not None else ""
        if text_str.strip().lower() in ["", "nan", "none", "null"]:
            text_str = "-"
        
        # Eliminar cualquier componente de hora residual
        if " 00:00:00" in text_str:
            text_str = text_str.replace(" 00:00:00", "").strip()
        elif "T00:00:00" in text_str:
            text_str = text_str.replace("T00:00:00", "").strip()
            
        m_iso = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$", text_str.strip())
        if m_iso:
            y, mth, d = m_iso.groups()
            text_str = f"{int(d):02d}/{int(mth):02d}/{y}"
            
        if textColor == colors.white:
            style = self.style_th_white_center if align == "CENTER" else (self.style_th_white_right if align == "RIGHT" else self.style_th_white_left)
        else:
            if bold:
                style = self.style_cell_bold_center if align == "CENTER" else (self.style_cell_bold_right if align == "RIGHT" else self.style_cell_bold_left)
            else:
                style = self.style_cell_center if align == "CENTER" else (self.style_cell_right if align == "RIGHT" else self.style_cell_left)
                
        return Paragraph(text_str, style)

    @abstractmethod
    def build_pdf(
        self,
        buffer: io.BytesIO,
        metadata: Dict[str, Any],
        df_data: pd.DataFrame,
        options: Dict[str, Any]
    ) -> bytes:
        """Método abstracto que construye el documento PDF."""
        pass
