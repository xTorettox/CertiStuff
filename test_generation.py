import io
import os
import pandas as pd
from generators import get_generator_by_template
from utils import ProfileManager, load_excel_file, pdf_bytes_to_images

def test_all():
    pm = ProfileManager()
    profiles = pm.list_profiles()
    print("Perfiles detectados:", profiles)

    for pid in ["nabors", "ypf_noc_iade", "ypf_noc_mensual", "pluspetrol"]:
        prof = pm.get_profile(pid)
        assert prof is not None, f"Perfil {pid} no encontrado"
        ttype = prof.get("template_type", pid)
        generator = get_generator_by_template(ttype)

        # Cargar datos de ejemplo
        sample_path = os.path.join("assets", "sample_data", f"muestra_{pid.replace('_noc', '')}.xlsx")
        if not os.path.exists(sample_path):
            sample_path = os.path.join("assets", "sample_data", f"muestra_{pid}.xlsx")
        
        df = load_excel_file(sample_path, prof)
        
        # Opciones y metadata
        options = prof.get("options", {})
        metadata = prof.get("default_metadata", {})
        metadata["firmante_nombre"] = "Federico García Cendra"
        metadata["firmante_cargo"] = "Comercial Alquileres"

        if pid == "pluspetrol":
            # Agregar muestra de otros cargos
            metadata["otros_cargos_df"] = pd.DataFrame({
                "CONCEPTO": ["Flete de entrega y retiro en base", "Seguro técnico operativo mensual"],
                "CANTIDAD": [2, 1],
                "TARIFA UNIT (USD)": [350.0, 180.0]
            })

        buf = io.BytesIO()
        pdf_bytes = generator.build_pdf(buf, metadata, df, options)
        assert len(pdf_bytes) > 1000, f"PDF generado para {pid} es demasiado pequeño"
        
        # Test render to image
        images = pdf_bytes_to_images(pdf_bytes)
        assert len(images) > 0, f"No se pudo renderizar la imagen para {pid}"
        print(f"[OK] Exito: {pid} -> {len(pdf_bytes)} bytes PDF, {len(images)} pagina(s) renderizada(s)")

        # Guardar en disco para verificación
        out_pdf = f"test_{pid}.pdf"
        with open(out_pdf, "wb") as f:
            f.write(pdf_bytes)
        print(f"  Guardado en {out_pdf}")

if __name__ == "__main__":
    test_all()
