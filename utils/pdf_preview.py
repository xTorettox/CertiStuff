try:
    import pymupdf as fitz
except ImportError:
    import fitz # PyMuPDF fallback
from typing import List

def pdf_bytes_to_images(pdf_bytes: bytes, dpi: int = 150) -> List[bytes]:
    """Convierte las páginas de un PDF en bytes a una lista de imágenes PNG en bytes."""
    images = []
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        for page in doc:
            pix = page.get_pixmap(matrix=mat, alpha=False)
            images.append(pix.tobytes("png"))
        doc.close()
    except Exception as e:
        print(f"Error al convertir PDF a imagen: {e}")
    return images

def crop_pdf_to_content(pdf_bytes: bytes, margin_bottom: float = 24.0) -> bytes:
    """
    Recorta la altura física de la página PDF para que coincida exactamente
    con el cuadro del certificado (eliminando el espacio en blanco inferior de la hoja).
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            drawings = page.get_drawings()
            outer_rect = None
            # Buscar el rectángulo exterior del certificado
            for d in drawings:
                r = d.get("rect")
                if r and abs(r.x0 - 24.0) < 3.0 and abs(r.width - 793.89) < 6.0:
                    outer_rect = r
                    break
            if outer_rect:
                H = page.rect.height
                needed_h = outer_rect.y1 + margin_bottom
                crop_box = fitz.Rect(0, max(0.0, H - needed_h), page.rect.width, H)
                page.set_cropbox(crop_box)
                page.set_mediabox(crop_box)
        cropped_bytes = doc.tobytes()
        doc.close()
        return cropped_bytes
    except Exception as e:
        print(f"Error al recortar página PDF: {e}")
        return pdf_bytes

