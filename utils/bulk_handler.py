import os
import io
import zipfile
import datetime
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
from generators import get_generator_by_template
from utils.database import db
from utils.excel_handler import clean_date_val, parse_arg_number, auto_calculate_dataframe
from utils.pdf_preview import crop_pdf_to_content

BULK_COLUMNS = [
    "CLIENTE",
    "CERTIFICADO_NRO",
    "SERVICIO_OBRA",
    "OC_NP",
    "EQUIPO",
    "MARCA",
    "MODELO",
    "INICIO",
    "FIN",
    "DIAS_ALQ",
    "CANT_EQUIPOS",
    "MODALIDAD",
    "TARIFA",
    "TOTAL",
    "OBSERVACION"
]

def generate_bulk_excel_template() -> bytes:
    """Genera una plantilla Excel lista para carga masiva con datos de ejemplo y modalidades."""
    sample_rows = [
        {
            "CLIENTE": "NABORS",
            "CERTIFICADO_NRO": "48",
            "SERVICIO_OBRA": "RIG F36",
            "OC_NP": "19084416",
            "EQUIPO": "Generador 480V / 60 Hz",
            "MARCA": "Sullair",
            "MODELO": "480-60",
            "INICIO": "01/10/2026",
            "FIN": "14/10/2026",
            "DIAS_ALQ": 14,
            "CANT_EQUIPOS": 1,
            "MODALIDAD": "diario",
            "TARIFA": 250.0,
            "TOTAL": 3500.0,
            "OBSERVACION": "Equipo operativo en locación"
        },
        {
            "CLIENTE": "NABORS",
            "CERTIFICADO_NRO": "48",
            "SERVICIO_OBRA": "RIG F36",
            "OC_NP": "19084416",
            "EQUIPO": "Compresor 375Q",
            "MARCA": "Sullair",
            "MODELO": "375Q",
            "INICIO": "01/10/2026",
            "FIN": "10/10/2026",
            "DIAS_ALQ": 10,
            "CANT_EQUIPOS": 1,
            "MODALIDAD": "diario",
            "TARIFA": 180.0,
            "TOTAL": 1800.0,
            "OBSERVACION": ""
        },
        {
            "CLIENTE": "PLUSPETROL S.A.",
            "CERTIFICADO_NRO": "113",
            "SERVICIO_OBRA": "Yacimiento La Calera",
            "OC_NP": "4500987621",
            "EQUIPO": "Generador 500 kVA",
            "MARCA": "Atlas Copco",
            "MODELO": "QAS 500",
            "INICIO": "01/10/2026",
            "FIN": "30/10/2026",
            "DIAS_ALQ": 30,
            "CANT_EQUIPOS": 1,
            "MODALIDAD": "mensual",
            "TARIFA": 8400.0,
            "TOTAL": 8400.0,
            "OBSERVACION": "Mantenimiento preventivo al día"
        }
    ]
    df = pd.DataFrame(sample_rows, columns=BULK_COLUMNS)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Carga_Masiva")
    return output.getvalue()

def process_bulk_excel(
    file_bytes_or_path,
    default_modalidad: str = "diario",
    signer_name: str = "Federico García Cendra",
    signer_role: str = "Comercial Alquileres",
    signature_source: Optional[str] = None,
    user_name: str = "comercial"
) -> Tuple[bytes, List[Dict[str, Any]]]:
    """
    Procesa un archivo Excel con múltiples filas/certificados y devuelve:
    1. Archivo ZIP en bytes conteniendo los PDFs individuales recortados y el reporte Excel.
    2. Lista de resúmenes de certificados generados.
    """
    df = pd.read_excel(file_bytes_or_path)

    # Normalizar columnas
    col_mapping = {}
    for col in df.columns:
        c_clean = str(col).upper().strip().replace(" ", "_").replace(".", "").replace("/", "_")
        for std_col in BULK_COLUMNS:
            if std_col in c_clean or c_clean in std_col:
                col_mapping[col] = std_col
                break
    df = df.rename(columns=col_mapping)

    # Asegurar columnas obligatorias
    for col in BULK_COLUMNS:
        if col not in df.columns:
            df[col] = "-" if "OBS" in col or "MARCA" in col or "MODELO" in col else 0

    # Limpiar fechas estrictamente a DD/MM/AAAA
    df["INICIO"] = df["INICIO"].apply(clean_date_val)
    df["FIN"] = df["FIN"].apply(clean_date_val)

    # Modalidad por defecto si viene vacía
    df["MODALIDAD"] = df["MODALIDAD"].apply(lambda m: str(m).lower().strip() if pd.notna(m) and str(m).strip() not in ["-", "", "0"] else default_modalidad)

    # Agrupar por CLIENTE y CERTIFICADO_NRO
    zip_buffer = io.BytesIO()
    generated_summary = []

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        grouped = df.groupby(["CLIENTE", "CERTIFICADO_NRO"], sort=False)

        for (cliente_raw, cert_nro_raw), group_df in grouped:
            cliente_name = str(cliente_raw).strip()
            cert_nro = str(cert_nro_raw).strip()
            if not cliente_name or cliente_name == "nan" or not cert_nro or cert_nro == "nan":
                continue

            # Buscar o inferir plantilla según cliente
            cliente_info = db.get_cliente(cliente_name)
            template_type = cliente_info.get("template_type", "nabors") if cliente_info else "nabors"
            
            # Encabezado del certificado
            first_row = group_df.iloc[0]
            servicio_obra = str(first_row.get("SERVICIO_OBRA", first_row.get("SERVICIO", "-")))
            oc_np = str(first_row.get("OC_NP", "-"))
            obs_text = str(first_row.get("OBSERVACION", ""))

            # Preparar DataFrame de equipos para la plantilla correspondiente
            cert_df = group_df.copy()
            cert_df["_incluir"] = True

            # Nombres de columnas esperados según el generador
            if template_type == "nabors":
                cert_df = cert_df.rename(columns={"DIAS_ALQ": "DÍAS ALQ", "CANT_EQUIPOS": "CANT EQUIPOS"})
            elif template_type == "pluspetrol":
                cert_df = cert_df.rename(columns={
                    "DIAS_ALQ": "CANT DIAS",
                    "INICIO": "INICIO PERIODO",
                    "FIN": "FIN PERIODO",
                    "TARIFA": "TARIFA DIARIO",
                    "TOTAL": "TARIFA TOTAL (USD)"
                })
            
            # Evitar columnas duplicadas
            cert_df = cert_df.loc[:, ~cert_df.columns.duplicated()]

            # Auto-calcular totales de tarifas si faltan
            calc_mode = str(first_row.get("MODALIDAD", default_modalidad)).lower()
            cert_df = auto_calculate_dataframe(cert_df, calc_mode=calc_mode)

            # Metadata consolidada
            metadata = {
                "certificado_nro": cert_nro,
                "cliente": cliente_name,
                "servicio": servicio_obra,
                "obra": servicio_obra,
                "oc_np": oc_np,
                "observacion": obs_text if obs_text != "-" else "",
                "observaciones": obs_text if obs_text != "-" else "",
                "periodo": f"{first_row.get('INICIO', '')} al {first_row.get('FIN', '')}",
                "firmante_nombre": signer_name,
                "firmante_cargo": signer_role,
                "firma_source": signature_source,
                "sucursal": cliente_info.get("sucursal", "Sucursal NQN y Valle") if cliente_info else "Sucursal NQN y Valle",
                "direccion": cliente_info.get("direccion", "Industriales Neuquinos 2920, PIN") if cliente_info else "Industriales Neuquinos 2920, PIN",
                "telefono": cliente_info.get("telefono", "T:[0299] 4782500") if cliente_info else "T:[0299] 4782500",
            }

            options = {
                "show_dates": True,
                "show_tariffs": True,
                "show_signature": True,
                "show_observations": bool(obs_text and obs_text != "-"),
                "trim_frame": True
            }

            # Construir PDF
            generator = get_generator_by_template(template_type)
            pdf_buf = io.BytesIO()
            pdf_bytes = generator.build_pdf(pdf_buf, metadata, cert_df, options)
            
            # Recortar hoja física de forma automática
            pdf_bytes = crop_pdf_to_content(pdf_bytes, margin_bottom=24.0)

            # Calcular monto total
            monto_total = 0.0
            for _, r in cert_df.iterrows():
                monto_total += parse_arg_number(r.get("TOTAL") or r.get("TARIFA TOTAL (USD)") or 0)

            # Guardar en Historial de Base de Datos
            db.add_historial({
                "cliente": cliente_name,
                "certificado_nro": cert_nro,
                "fecha_emision": datetime.date.today().strftime("%d/%m/%Y"),
                "servicio_obra": servicio_obra,
                "oc_np": oc_np,
                "total_monto": monto_total,
                "moneda": "USD",
                "usuario": user_name,
                "items_count": len(cert_df),
                "metadata": metadata,
                "items": cert_df.to_dict(orient="records")
            })

            # Nombre de archivo limpio
            clean_client = "".join(c for c in cliente_name if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
            pdf_filename = f"Certificado_{clean_client}_{cert_nro}.pdf"

            # Agregar PDF al ZIP
            zip_file.writestr(pdf_filename, pdf_bytes)

            generated_summary.append({
                "Cliente": cliente_name,
                "Certificado N°": cert_nro,
                "Servicio / Obra": servicio_obra,
                "OC/NP": oc_np,
                "Ítems": len(cert_df),
                "Total USD": monto_total,
                "Archivo PDF": pdf_filename
            })

        # Agregar planilla índice al ZIP
        if generated_summary:
            df_summary = pd.DataFrame(generated_summary)
            summary_buf = io.BytesIO()
            with pd.ExcelWriter(summary_buf, engine="openpyxl") as writer:
                df_summary.to_excel(writer, index=False, sheet_name="Resumen_Lote")
            zip_file.writestr("Indice_Certificados_Emitidos.xlsx", summary_buf.getvalue())

    return zip_buffer.getvalue(), generated_summary
