import os
import io
import base64
from PIL import Image
from typing import Optional, List, Dict, Any
from utils.database import db

def make_transparent_signature(pil_img: Image.Image, threshold: int = 215) -> Image.Image:
    """
    Convierte una imagen de firma en un PNG transparente nítido.
    - Si la imagen ya tiene canal alpha con transparencia (como un PNG transparente subido por el usuario),
      preserva la transparencia original sin alterar ningún pixel ni forzar fondo negro.
    - Si es una foto/escaneo sobre papel blanco (JPG o PNG opaco), remueve el fondo blanco o grisáceo.
    """
    img = pil_img.copy()

    # 1. Detectar si la imagen ya cuenta con transparencia real
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        alpha = rgba.split()[3]
        min_a, max_a = alpha.getextrema()
        # Si tiene píxeles con transparencia real (< 220), respetarla y preservarla al 100%
        if min_a < 220:
            return rgba

    # 2. Si es una imagen opaca sobre papel, convertir a RGBA y remover fondo blanco
    img = img.convert("RGBA")
    datas = img.getdata()
    new_data = []
    
    for item in datas:
        r, g, b, a = item
        # Si ya era transparente, mantener transparente
        if a < 50:
            new_data.append((255, 255, 255, 0))
        # Si el pixel es cercano al blanco (fondo de papel), hacerlo transparente
        elif r > threshold and g > threshold and b > threshold:
            new_data.append((255, 255, 255, 0))
        else:
            # Preservar la tinta con su color original
            new_data.append((r, g, b, a if a > 0 else 255))
            
    img.putdata(new_data)
    return img

def pil_to_base64_data_uri(pil_img: Image.Image) -> str:
    """Convierte un PIL Image a string Data URI base64."""
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_str}"

def base64_to_pil(b64_str: str) -> Optional[Image.Image]:
    """Convierte un string base64 o Data URI a PIL Image."""
    try:
        if "base64," in b64_str:
            b64_str = b64_str.split("base64,")[1]
        img_bytes = base64.b64decode(b64_str)
        return Image.open(io.BytesIO(img_bytes))
    except Exception as e:
        print(f"Error decodificando firma base64: {e}")
        return None

def get_html5_signature_pad_html() -> str:
    """Retorna el código HTML/JS para el pad interactivo de dibujo de firmas táctil y con mouse."""
    return """
    <div style="font-family: sans-serif; text-align: center; max-width: 500px; margin: auto;">
        <canvas id="pad" width="460" height="170" style="border: 2px dashed #00853E; border-radius: 8px; background: #ffffff; cursor: crosshair; touch-action: none; box-shadow: 0 2px 8px rgba(0,0,0,0.05);"></canvas>
        <div style="margin-top: 10px; display: flex; justify-content: space-between;">
            <button id="btnClear" style="background: #EF4444; color: white; border: none; padding: 7px 16px; border-radius: 6px; font-weight: 600; cursor: pointer;">Limpiar Lienzo</button>
            <button id="btnDownload" style="background: #00853E; color: white; border: none; padding: 7px 16px; border-radius: 6px; font-weight: 600; cursor: pointer;">Descargar Firma Dibujada (PNG)</button>
        </div>
        <p style="font-size: 11px; color: #64748B; margin-top: 6px;">💡 Puedes firmar con el mouse, lápiz óptico o con el dedo en pantallas táctiles.</p>
    </div>
    <script>
        const canvas = document.getElementById('pad');
        const ctx = canvas.getContext('2d');
        ctx.strokeStyle = "#0B2545";
        ctx.lineWidth = 2.5;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';

        let drawing = false;

        function getPos(e) {
            const rect = canvas.getBoundingClientRect();
            const clientX = e.touches ? e.touches[0].clientX : e.clientX;
            const clientY = e.touches ? e.touches[0].clientY : e.clientY;
            return {
                x: clientX - rect.left,
                y: clientY - rect.top
            };
        }

        function start(e) {
            drawing = true;
            const pos = getPos(e);
            ctx.beginPath();
            ctx.moveTo(pos.x, pos.y);
            e.preventDefault();
        }

        function draw(e) {
            if (!drawing) return;
            const pos = getPos(e);
            ctx.lineTo(pos.x, pos.y);
            ctx.stroke();
            e.preventDefault();
        }

        function stop(e) {
            if (!drawing) return;
            drawing = false;
            e.preventDefault();
        }

        canvas.addEventListener('mousedown', start);
        canvas.addEventListener('mousemove', draw);
        window.addEventListener('mouseup', stop);

        canvas.addEventListener('touchstart', start, {passive: false});
        canvas.addEventListener('touchmove', draw, {passive: false});
        window.addEventListener('touchend', stop, {passive: false});

        document.getElementById('btnClear').addEventListener('click', () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
        });

        document.getElementById('btnDownload').addEventListener('click', () => {
            const link = document.createElement('a');
            link.download = 'mi_firma_dibujada.png';
            link.href = canvas.toDataURL('image/png');
            link.click();
        });
    </script>
    """

