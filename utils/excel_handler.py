import os
import io
import re
import pandas as pd
from typing import Dict, Any, Tuple, Optional

SAMPLE_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "sample_data")

SYNONYM_MAP = {
    "equipo": ["equipo", "descripcion del equipo", "item", "maquinaria"],
    "marca": ["marca", "brand"],
    "modelo": ["modelo", "model"],
    "interno": ["interno", "nro interno", "serie", "n° serie", "patente", "activo"],
    "inicio": ["inicio", "fecha inicio", "desde", "f. inicio", "inicio periodo"],
    "fin": ["fin", "fecha fin", "hasta", "f. fin", "fin periodo"],
    "dias_alq": ["dias alq", "dias de alquiler", "dias", "cant dias", "cant. dias", "dias alquilados"],
    "cant_equipos": ["cant equipos", "cant. equipos", "cantidad", "cant", "cant de equipos"],
    "iade": ["iade", "nro iade", "n° iade", "reclamo"],
    "almacen": ["almacen", "almacén", "centro", "deposito"],
    "repuestos_usd": ["repuestos (usd)", "repuestos", "repuestos usd", "costo repuestos"],
    "mo_usd": ["mano de obra y reparaciones (usd)", "mano de obra", "mo usd", "mo y rep", "reparaciones"],
    "total_rep_mo": ["total rep.+ mo", "total rep+mo", "total repuestos y mo", "total reparacion"],
    "detalle": ["detalle", "motivo", "observaciones", "descripcion de falla", "averia"],
    "posicion": ["posicion", "posición", "pos", "item"],
    "linea": ["linea", "línea", "lin"],
    "um": ["u.m", "um", "unidad", "unidad de medida"],
    "descripcion": ["descripcion", "descripción", "concepto", "equipo", "detalle"],
    "periodo": ["periodo", "período", "mes"],
    "cantidad": ["cantidad", "cant", "unidades"],
    "tarifa": ["tarifa", "tarifa mensual", "tarifa unitaria", "precio", "valor"],
    "tarifa_diario": ["tarifa diario", "tarifa diaria", "tarifa x dia", "tarifa"],
    "tarifa_total": ["tarifa total (usd)", "tarifa total", "total usd", "total"],
    "total": ["total", "subtotal", "importe"]
}

def clean_col_name(col: str) -> str:
    """Normaliza nombres de columna a minúsculas y sin acentos."""
    c = str(col).lower().strip()
    c = c.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    c = re.sub(r'[\(\)\.\,\_\-\/\\]', ' ', c)
    return " ".join(c.split())

def parse_arg_number(val: Any) -> float:
    """Parsea números en formato latino/argentino (ej: '1.808,80' o 'USD 1.808,80' o 1808.8)."""
    if pd.isna(val) or val is None or val == "" or val == "-":
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().upper().replace("USD", "").replace("$", "").strip()
    # Si tiene puntos como separador de miles y coma como decimal (ej: 1.808,80)
    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0

def format_arg_currency(val: Any, symbol: str = "USD", include_symbol: bool = True) -> str:
    """Formatea número a estilo latino: 22.467,00."""
    num = parse_arg_number(val)
    formatted = f"{num:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if include_symbol and symbol:
        return f"{symbol} {formatted}"
    return formatted

def format_decimal(val: Any, decimals: int = 3) -> str:
    """Formatea decimales estilo latino: 0,667 o 1,000."""
    num = parse_arg_number(val)
    if decimals == 0:
        return f"{int(round(num))}"
    fmt = f"{{:,.{decimals}f}}"
    return fmt.format(num).replace(",", "X").replace(".", ",").replace("X", ".")

def map_excel_columns(df: pd.DataFrame, target_columns: list) -> pd.DataFrame:
    """Mapea automáticamente las columnas del Excel a las esperadas por el perfil."""
    df_clean = df.copy()
    raw_cols = list(df_clean.columns)
    mapped_dict = {}

    for target in target_columns:
        target_key = target.get("key", "").lower()
        target_title = target.get("title", "").lower()
        clean_target = clean_col_name(target_title)
        synonyms = SYNONYM_MAP.get(target_key, []) + [clean_target, target_key]

        # Buscar coincidencia exacta o sinónimo
        matched = None
        for col in raw_cols:
            c_norm = clean_col_name(col)
            if col.upper() == target.get("title", "").upper() or c_norm in synonyms:
                matched = col
                break
            # Verificación parcial
            for syn in synonyms:
                if len(syn) > 3 and syn in c_norm:
                    matched = col
                    break
            if matched:
                break
        
        if matched and matched in df_clean.columns:
            mapped_dict[matched] = target.get("title")

    # Renombrar columnas mapeadas
    df_clean = df_clean.rename(columns=mapped_dict)
    
    # Asegurar que existan todas las columnas del perfil
    for target in target_columns:
        title = target.get("title")
        if title not in df_clean.columns:
            df_clean[title] = "-"

    # Asegurar columna de selección '_incluir'
    if "_incluir" not in df_clean.columns:
        df_clean.insert(0, "_incluir", True)
    else:
        df_clean["_incluir"] = df_clean["_incluir"].astype(bool)

    return df_clean

def load_excel_file(file_bytes_or_path, profile: Dict[str, Any]) -> pd.DataFrame:
    """Lee un archivo Excel y lo adapta al perfil seleccionado."""
    df = pd.read_excel(file_bytes_or_path)
    target_cols = profile.get("columns", [])
    return map_excel_columns(df, target_cols)

def get_sample_file_path(profile_id: str) -> Optional[str]:
    """Retorna la ruta del archivo de ejemplo para un perfil."""
    mapping = {
        "nabors": "muestra_nabors.xlsx",
        "ypf_noc_iade": "muestra_ypf_iade.xlsx",
        "ypf_noc_mensual": "muestra_ypf_mensual.xlsx",
        "pluspetrol": "muestra_pluspetrol.xlsx"
    }
    filename = mapping.get(profile_id)
    if filename:
        p = os.path.join(SAMPLE_DATA_DIR, filename)
        if os.path.exists(p):
            return p
    return None

def dataframe_to_excel_bytes(df: pd.DataFrame) -> bytes:
    """Convierte un DataFrame a bytes de Excel para descarga."""
    output = io.BytesIO()
    export_df = df.copy()
    if "_incluir" in export_df.columns:
        export_df = export_df.drop(columns=["_incluir"])
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        export_df.to_excel(writer, index=False, sheet_name='Datos')
    return output.getvalue()
