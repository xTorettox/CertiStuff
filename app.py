import os
import io
import json
import datetime
import streamlit as st
import pandas as pd
from PIL import Image

# Configuración de página Streamlit
st.set_page_config(
    page_title="Generador de Certificados | Sullair Argentina",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Importar módulos del sistema
from utils.auth import check_authentication, render_user_sidebar
from utils.database import db
from utils.profile_manager import ProfileManager
from utils.excel_handler import (
    load_excel_file,
    map_excel_columns,
    parse_arg_number,
    format_arg_currency,
    get_sample_file_path,
    dataframe_to_excel_bytes,
    clean_date_val,
    auto_calculate_dataframe
)
from utils.pdf_preview import pdf_bytes_to_images, crop_pdf_to_content
from utils.bulk_handler import generate_bulk_excel_template, process_bulk_excel
from utils.signature_helper import (
    make_transparent_signature,
    pil_to_base64_data_uri,
    base64_to_pil,
    get_html5_signature_pad_html
)
from generators import get_generator_by_template

BASE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
CUSTOM_SIG_PATH = os.path.join(ASSETS_DIR, "firma_subida.png")
DEFAULT_SIG_PATH = os.path.join(ASSETS_DIR, "firma_default.png")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo_sullair.png")

# --- CONTROL DE ACCESO / LOGIN (Secrets) ---
if not check_authentication():
    st.stop()

# CSS personalizado para estilo corporativo de alto impacto
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #00853E 0%, #065F2C 100%);
        color: white;
        padding: 16px 24px;
        border-radius: 12px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 4px 14px rgba(0, 133, 62, 0.2);
    }
    .main-header h1 {
        color: white !important;
        font-size: 1.55rem !important;
        font-weight: 700 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    .main-header p {
        color: #E2F2E9 !important;
        font-size: 0.88rem !important;
        margin: 3px 0 0 0 !important;
    }
    .stat-card {
        background: white;
        border: 1px solid #E2E8F0;
        border-left: 5px solid #00853E;
        border-radius: 10px;
        padding: 12px 16px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
    }
    .stat-label {
        color: #64748B;
        font-size: 0.76rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .stat-value {
        color: #0F172A;
        font-size: 1.35rem;
        font-weight: 700;
        margin-top: 3px;
    }
    .badge-client {
        background: #DCFCE7;
        color: #166534;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }
    .empty-state-box {
        background: #F8FAFC;
        border: 2px dashed #CBD5E1;
        border-radius: 12px;
        padding: 32px 20px;
        text-align: center;
        margin: 16px 0;
    }
</style>
""", unsafe_allow_html=True)

# Usuario activo en sesión
current_username = st.session_state.get("username", "fcendra")
current_display_name = st.session_state.get("user_display_name", "Federico García Cendra")

# Barra lateral: Sesión activa
render_user_sidebar()

# Inicializar gestor de perfiles
pm = ProfileManager()
all_profiles = pm.list_profiles()

# Encabezado corporativo con Logo Oficial Sullair
col_head1, col_head2 = st.columns([3, 1.2])
with col_head1:
    st.markdown("""
    <div class="main-header">
        <div>
            <h1>📄 Generador de Certificados de Alquiler y Servicios</h1>
            <p>Emisión y Certificación PDF con Recorte Dinámico y Firma Digital | Sullair Argentina</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
with col_head2:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=230)

# Tabs principales
tab_cert, tab_bulk, tab_historial, tab_precios, tab_firma, tab_perfiles, tab_ayuda = st.tabs([
    "📋 Emisión Individual",
    "🚀 Generación Masiva (Bulk)",
    "📜 Historial de Certificados",
    "💰 Contratos y Lista de Precios",
    "✍️ Gestión de Firmas y Logo",
    "⚙️ Perfiles y Plantillas",
    "📖 Manual de Usuario"
])

# ==========================================
# TAB 1: EMISIÓN INDIVIDUAL
# ==========================================
with tab_cert:
    with st.sidebar:
        st.markdown("### 🏢 Selección de Cliente")
        
        # Cargar lista de clientes desde la base de datos
        db_clientes = db.get_clientes()
        client_options = [c["nombre"] for c in db_clientes]
        client_options.append("➕ Registrar Nuevo Cliente...")

        selected_client_name = st.selectbox(
            "Cliente / Operadora:",
            options=client_options,
            index=0,
            key="sb_client_select"
        )

        # Modal/formulario para registrar nuevo cliente
        if selected_client_name == "➕ Registrar Nuevo Cliente...":
            with st.expander("📝 Formulario Nuevo Cliente", expanded=True):
                new_c_name = st.text_input("Razón Social / Nombre:", placeholder="Ej: VISTA ENERGY S.A.").strip()
                new_c_template = st.selectbox("Plantilla PDF Base:", options=["nabors", "pluspetrol", "ypf_noc_iade", "ypf_noc_mensual"])
                new_c_last = st.number_input("Último N° Certificado Emitido:", min_value=0, value=0)
                new_c_oc = st.text_input("OC / Contrato Habitual:", placeholder="Ej: 4500987621")
                new_c_serv = st.text_input("Servicio / Yacimiento:", placeholder="Ej: Bajada del Palo")
                if st.button("💾 Guardar Cliente", use_container_width=True, type="primary"):
                    if new_c_name:
                        cid = db.save_cliente({
                            "nombre": new_c_name,
                            "template_type": new_c_template,
                            "ultimo_certificado": int(new_c_last),
                            "contrato_nro": new_c_oc,
                            "servicio_defecto": new_c_serv,
                            "oc_np_defecto": new_c_oc
                        })
                        st.success(f"Cliente '{new_c_name}' guardado correctamente.")
                        st.rerun()
                    else:
                        st.error("Ingrese el nombre del cliente.")

            cliente_actual = db_clientes[0] if db_clientes else {"nombre": "NABORS", "template_type": "nabors", "ultimo_certificado": 46}
        else:
            cliente_actual = db.get_cliente(selected_client_name) or {"nombre": selected_client_name, "template_type": "nabors", "ultimo_certificado": 1}

        template_type = cliente_actual.get("template_type", "nabors")
        active_profile = pm.get_profile(template_type) or pm.get_profile("nabors")

        st.markdown("---")
        st.markdown("#### ⚡ Opciones de Certificación")

        show_dates = st.checkbox("Mostrar Fechas Inicio / Fin", value=True, key=f"opt_dates_{template_type}")
        show_tariffs = st.checkbox("Mostrar Tarifas y Montos", value=True, key=f"opt_tariffs_{template_type}")
        show_signature = st.checkbox("Incluir Firma Digital", value=True, key=f"opt_sig_{template_type}")
        show_obs = st.checkbox("Incluir Observaciones", value=True, key=f"opt_obs_{template_type}")

        include_other_charges = False
        if template_type == "pluspetrol":
            include_other_charges = st.checkbox("Incluir Tabla de Otros Cargos (Fletes/Seguros)", value=True, key="opt_oc_plus")

        st.markdown("---")
        st.markdown("#### 📝 Metadatos del Encabezado")

        # Calcular sugerencia del número de certificado siguiente (recordar último índice)
        ultimo_idx = int(cliente_actual.get("ultimo_certificado", 0))
        siguiente_nro = str(ultimo_idx + 1) if ultimo_idx > 0 else "1"

        def get_meta_val(field: str, label: str, default_val: str, is_area: bool = False) -> str:
            k = f"meta_{cliente_actual.get('id', 'cli')}_{field}"
            if k not in st.session_state:
                st.session_state[k] = default_val
            if is_area:
                return st.text_area(label, key=k, height=75)
            return st.text_input(label, key=k)

        meta_inputs = {}

        if template_type == "nabors":
            meta_inputs["certificado_nro"] = get_meta_val("cert_nro", "Certificado N°:", siguiente_nro)
            meta_inputs["cliente"] = get_meta_val("cliente", "Cliente:", cliente_actual.get("nombre", "NABORS"))
            meta_inputs["servicio"] = get_meta_val("servicio", "Servicio:", cliente_actual.get("servicio_defecto", "F10"))
            meta_inputs["oc_np"] = get_meta_val("oc_np", "OC / NP N°:", cliente_actual.get("oc_np_defecto", "19084166"))
            meta_inputs["sucursal"] = cliente_actual.get("sucursal", "Sucursal NQN y Valle")
            meta_inputs["direccion"] = cliente_actual.get("direccion", "Industriales Neuquinos 2920, PIN")
            meta_inputs["telefono"] = cliente_actual.get("telefono", "T:[0299] 4782500")

        elif template_type == "ypf_noc_iade":
            meta_inputs["titulo"] = get_meta_val("titulo", "Título:", "REPARACIONES DE EQUIPOS")
            meta_inputs["contrato_sap"] = get_meta_val("contrato_sap", "Contrato SAP:", cliente_actual.get("contrato_nro", "4900102848"))
            meta_inputs["almacen"] = get_meta_val("almacen", "Almacén:", "NOC")
            meta_inputs["subtotal_label"] = "SUBTOTOTAL"

        elif template_type == "ypf_noc_mensual":
            meta_inputs["titulo"] = get_meta_val("titulo", "Título:", "SERVICIO ALQUILER DE EQUIPOS")
            meta_inputs["contrato_sap"] = get_meta_val("contrato_sap", "Contrato SAP:", cliente_actual.get("contrato_nro", "4900114308"))
            meta_inputs["almacen"] = get_meta_val("almacen", "Almacén:", "NOC")
            meta_inputs["periodo"] = get_meta_val("periodo", "Período:", "21/09/2026 al 20/10/2026")

        elif template_type == "pluspetrol":
            meta_inputs["certificado_nro"] = get_meta_val("cert_nro", "Certificado N°:", siguiente_nro)
            meta_inputs["cliente"] = get_meta_val("cliente", "Cliente:", cliente_actual.get("nombre", "PLUSPETROL S.A."))
            meta_inputs["obra"] = get_meta_val("obra", "Obra / Yacimiento:", cliente_actual.get("servicio_defecto", "Yacimiento La Calera"))
            meta_inputs["periodo"] = get_meta_val("periodo", "Período:", "01/10/2026 al 31/10/2026")
            meta_inputs["oc_np"] = get_meta_val("oc_np", "OC / NP N°:", cliente_actual.get("oc_np_defecto", "4500987621"))

        # Firmante y Selección de Firma del Usuario
        st.markdown("---")
        st.markdown("#### 🖋️ Firma del Responsable")
        user_sigs = db.get_user_signatures(current_username)
        sig_options = {}
        if user_sigs:
            for s in user_sigs:
                label = f"{s['alias']} ({s['nombre_firmante']})" + (" ⭐" if s['is_default'] else "")
                sig_options[label] = s
            selected_sig_label = st.selectbox("Firma a Estampar:", options=list(sig_options.keys()))
            chosen_sig = sig_options[selected_sig_label]
            meta_inputs["firmante_nombre"] = get_meta_val("firmante_nombre", "Nombre:", chosen_sig["nombre_firmante"])
            meta_inputs["firmante_cargo"] = get_meta_val("firmante_cargo", "Cargo:", chosen_sig["cargo"])
            meta_inputs["firma_source"] = chosen_sig["firma_png_base64"]
        else:
            meta_inputs["firmante_nombre"] = get_meta_val("firmante_nombre", "Nombre:", current_display_name)
            meta_inputs["firmante_cargo"] = get_meta_val("firmante_cargo", "Cargo:", "Comercial Alquileres")
            meta_inputs["firma_source"] = None

        if show_obs:
            meta_inputs["observacion"] = get_meta_val("obs", "Observaciones / Deducciones:", "", is_area=True)
            meta_inputs["observaciones"] = meta_inputs["observacion"]

    # ÁREA PRINCIPAL: Carga y Edición de Datos
    col_up1, col_up2, col_up3 = st.columns([3, 1.5, 1.5])
    with col_up1:
        uploaded_file = st.file_uploader(
            f"📂 Cargar archivo Excel (.xlsx) para {cliente_actual.get('nombre')}:",
            type=["xlsx", "xls"],
            key=f"uploader_{template_type}"
        )
    with col_up2:
        st.write("")
        st.write("")
        btn_cargar_muestra = st.button("🔄 Cargar Muestra", use_container_width=True)
    with col_up3:
        st.write("")
        st.write("")
        sample_path = get_sample_file_path(template_type)
        if sample_path and os.path.exists(sample_path):
            with open(sample_path, "rb") as sf:
                st.download_button(
                    "📥 Descargar Plantilla",
                    data=sf.read(),
                    file_name=f"plantilla_{template_type}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

    data_key = f"df_data_{cliente_actual.get('id', 'cli')}_{template_type}"
    editor_key = f"editor_{cliente_actual.get('id', 'cli')}_{template_type}"

    # Lógica de carga
    if uploaded_file is not None:
        try:
            df_loaded = load_excel_file(uploaded_file, active_profile)
            st.session_state[data_key] = df_loaded
            st.session_state.pop(editor_key, None)
            st.success("✅ Archivo Excel cargado y normalizado exitosamente.")
        except Exception as e:
            st.error(f"Error al leer el archivo Excel: {e}")

    elif btn_cargar_muestra:
        if sample_path and os.path.exists(sample_path):
            try:
                df_sample = load_excel_file(sample_path, active_profile)
                st.session_state[data_key] = df_sample
                st.session_state.pop(editor_key, None)
                st.rerun()
            except Exception as e:
                st.error(f"Error al cargar muestra: {e}")

    # Obtener DataFrame: si no hay datos, inicializar VACÍO (no precargar datos)
    if data_key not in st.session_state:
        target_cols = [c.get("title") for c in active_profile.get("columns", [])]
        empty_dict = {"_incluir": pd.Series(dtype=bool)}
        for c in target_cols:
            empty_dict[c] = pd.Series(dtype=object)
        st.session_state[data_key] = pd.DataFrame(empty_dict)

    current_df = st.session_state.get(data_key, pd.DataFrame())

    if current_df.empty:
        st.markdown(f"""
        <div class="empty-state-box">
            <h3 style="color: #334155; margin-bottom: 8px;">Planilla en Blanco Lista</h3>
            <p style="color: #64748B; font-size: 0.95rem; margin-bottom: 16px;">
                No hay ítems precargados para <b>{cliente_actual.get('nombre')}</b>.<br>
                Sube tu archivo Excel con el botón superior, haz clic en <b>'Cargar Muestra'</b> para probar con datos reales, o agrega filas en la tabla inferior.
            </p>
        </div>
        """, unsafe_allow_html=True)

    # Botones de acción rápida sobre la planilla
    col_act1, col_act2, col_act3 = st.columns([2, 1.5, 1.5])
    with col_act1:
        st.markdown("#### 📊 Revisión y Edición Interactiva de Datos")
    with col_act2:
        calc_mode = active_profile.get("calc_mode", "diario")
        if st.button("⚡ Recalcular y Sincronizar Totales", use_container_width=True):
            if not current_df.empty:
                st.session_state[data_key] = auto_calculate_dataframe(current_df, calc_mode=calc_mode)
                st.rerun()
    with col_act3:
        if st.button("🗑️ Limpiar Planilla", use_container_width=True):
            target_cols = [c.get("title") for c in active_profile.get("columns", [])]
            empty_dict = {"_incluir": pd.Series(dtype=bool)}
            for c in target_cols:
                empty_dict[c] = pd.Series(dtype=object)
            st.session_state[data_key] = pd.DataFrame(empty_dict)
            st.rerun()

    # Asegurar tipo booleano estricto en '_incluir' para evitar StreamlitAPIException en CheckboxColumn
    if "_incluir" not in current_df.columns:
        current_df.insert(0, "_incluir", pd.Series(True, index=current_df.index, dtype=bool))
    else:
        current_df["_incluir"] = current_df["_incluir"].fillna(True).astype(bool)
    
    # Sanitizar explícitamente el session_state para purgar cualquier residuo de float de sesiones previas
    st.session_state[data_key] = current_df

    # Editor de datos interactivo
    edited_df = st.data_editor(
        current_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "_incluir": st.column_config.CheckboxColumn("Incluir en PDF", default=True)
        },
        key=editor_key
    )

    # Auto-cálculo si hay valores
    if not edited_df.empty:
        edited_df = auto_calculate_dataframe(edited_df, calc_mode=active_profile.get("calc_mode", "diario"))

        # Métricas de la planilla
        incluidos = edited_df[edited_df.get("_incluir", True)] if "_incluir" in edited_df.columns else edited_df
        total_items = len(incluidos)
        total_monto = 0.0
        for _, r in edited_df.iterrows():
            if r.get("_incluir", True):
                total_monto += pm.calculate_row_total(r.to_dict(), active_profile.get("calc_mode", "diario"))

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        with kpi1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">Cliente Seleccionado</div>
                <div class="stat-value" style="font-size: 1.1rem; color: #00853E;">{cliente_actual.get('nombre')}</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi2:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">Ítems a Certificar</div>
                <div class="stat-value">{total_items} / {len(edited_df)}</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi3:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">Modalidad Tarifaria</div>
                <div class="stat-value" style="font-size: 1.1rem;">{active_profile.get('calc_mode', 'diario').upper()}</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi4:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">Total Certificado</div>
                <div class="stat-value" style="color: #047857;">{format_arg_currency(total_monto, symbol='USD')}</div>
            </div>
            """, unsafe_allow_html=True)

        # Tabla de Otros Cargos para Pluspetrol
        if include_other_charges and template_type == "pluspetrol":
            st.markdown("#### 🚚 Tabla de Otros Cargos (Fletes, Seguros, Lavado)")
            oc_key = f"df_otros_cargos_{cliente_actual.get('id', 'cli')}"
            if oc_key not in st.session_state:
                st.session_state[oc_key] = pd.DataFrame({
                    "CONCEPTO": ["Flete de entrega y retiro en base", "Seguro técnico operativo mensual"],
                    "CANTIDAD": [2, 1],
                    "TARIFA UNIT (USD)": [350.0, 180.0]
                })
            edited_oc_df = st.data_editor(
                st.session_state[oc_key],
                num_rows="dynamic",
                use_container_width=True,
                key=f"editor_oc_{cliente_actual.get('id', 'cli')}"
            )
            meta_inputs["otros_cargos_df"] = edited_oc_df

        st.markdown("---")

        # GENERACIÓN Y PREVISUALIZACIÓN PDF
        col_gen_btn, col_down_btn = st.columns([2, 2])
        render_options = {
            "show_dates": show_dates,
            "show_tariffs": show_tariffs,
            "show_signature": show_signature,
            "show_observations": show_obs,
            "include_other_charges": include_other_charges,
            "trim_frame": True
        }

        generator = get_generator_by_template(template_type)

        try:
            pdf_buffer = io.BytesIO()
            pdf_bytes = generator.build_pdf(
                buffer=pdf_buffer,
                metadata=meta_inputs,
                df_data=edited_df,
                options=render_options
            )
            # Recorte automático estricto de hoja
            pdf_bytes = crop_pdf_to_content(pdf_bytes, margin_bottom=24.0)

            clean_cname = "".join(c for c in cliente_actual.get("nombre", "") if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
            cert_id = meta_inputs.get("certificado_nro") or meta_inputs.get("contrato_sap", "1")
            download_filename = f"Certificado_{clean_cname}_{cert_id}.pdf"

            with col_gen_btn:
                st.success(f"📄 Certificado PDF generado con éxito ({len(pdf_bytes):,} bytes).")

            with col_down_btn:
                if st.download_button(
                    label=f"💾 Descargar {download_filename}",
                    data=pdf_bytes,
                    file_name=download_filename,
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary"
                ):
                    # Registrar emisión en base de datos al descargar
                    db.add_historial({
                        "cliente": cliente_actual.get("nombre", ""),
                        "certificado_nro": str(cert_id),
                        "fecha_emision": datetime.date.today().strftime("%d/%m/%Y"),
                        "servicio_obra": meta_inputs.get("servicio") or meta_inputs.get("obra", ""),
                        "oc_np": meta_inputs.get("oc_np", ""),
                        "total_monto": total_monto,
                        "moneda": "USD",
                        "usuario": current_username,
                        "items_count": total_items,
                        "metadata": meta_inputs,
                        "items": edited_df.to_dict(orient="records")
                    })

            # Previsualización gráfica en vivo
            st.markdown("### 👁️ Vista Previa del Certificado (Recorte Automático)")
            preview_images = pdf_bytes_to_images(pdf_bytes, dpi=160)
            if preview_images:
                for idx, img_bytes in enumerate(preview_images):
                    st.image(img_bytes, use_container_width=True)

        except Exception as e:
            st.error(f"Error generando el documento PDF: {e}")
            import traceback
            st.code(traceback.format_exc())

# ==========================================
# TAB 2: GENERACIÓN MASIVA (BULK)
# ==========================================
with tab_bulk:
    st.markdown("### 🚀 Generación de Certificados en Lote (Bulk)")
    st.write("Sube una planilla Excel con múltiples certificados o equipos. El sistema los procesará en lote, recortará cada PDF automáticamente y te entregará un archivo ZIP descargable con un solo clic.")

    col_b_info, col_b_tmpl = st.columns([3, 1.5])
    with col_b_info:
        st.info("💡 La planilla debe contener las columnas `CLIENTE`, `CERTIFICADO_NRO`, `INICIO`, `FIN`, `DIAS_ALQ`, `CANT_EQUIPOS`, `MODALIDAD` (diario/semanal/mensual) y `TARIFA`.")
    with col_b_tmpl:
        bulk_tmpl_bytes = generate_bulk_excel_template()
        st.download_button(
            "📥 Descargar Plantilla Bulk Oficial",
            data=bulk_tmpl_bytes,
            file_name="Plantilla_Carga_Masiva_Certificados.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    uploaded_bulk = st.file_uploader("📂 Cargar archivo Excel Bulk (.xlsx):", type=["xlsx", "xls"], key="uploader_bulk")
    
    col_b_opt1, col_b_opt2, col_b_opt3 = st.columns(3)
    with col_b_opt1:
        default_bulk_mod = st.selectbox("Modalidad por defecto si está en blanco:", options=["diario", "semanal", "mensual", "fijo"], index=0)
    with col_b_opt2:
        bulk_signer_name = st.text_input("Firmante en Lote:", value=current_display_name)
    with col_b_opt3:
        bulk_signer_role = st.text_input("Cargo del Firmante:", value="Comercial Alquileres")

    if uploaded_bulk is not None:
        try:
            df_preview_bulk = pd.read_excel(uploaded_bulk)
            st.markdown(f"#### 🔍 Vista Previa del Archivo Cargado ({len(df_preview_bulk)} filas)")
            st.dataframe(df_preview_bulk.head(15), use_container_width=True)

            if st.button("🚀 Procesar Certificados y Generar ZIP", type="primary", use_container_width=True):
                with st.spinner("Generando certificados PDF y empaquetando en ZIP..."):
                    uploaded_bulk.seek(0)
                    zip_data, summary = process_bulk_excel(
                        uploaded_bulk,
                        default_modalidad=default_bulk_mod,
                        signer_name=bulk_signer_name,
                        signer_role=bulk_signer_role,
                        user_name=current_username
                    )

                st.success(f"🎉 Proceso completado: se generaron **{len(summary)} certificados** exitosamente.")
                
                # Tabla de resumen
                st.dataframe(pd.DataFrame(summary), use_container_width=True)

                st.download_button(
                    label=f"💾 Descargar Archivo Comprimido ({len(summary)} Certificados en ZIP)",
                    data=zip_data,
                    file_name=f"Certificados_Sullair_Lote_{datetime.date.today().strftime('%Y%m%d')}.zip",
                    mime="application/zip",
                    use_container_width=True,
                    type="primary"
                )
        except Exception as e:
            st.error(f"Error procesando archivo masivo: {e}")

# ==========================================
# TAB 3: HISTORIAL DE CERTIFICADOS
# ==========================================
with tab_historial:
    st.markdown("### 📜 Historial de Certificados Emitidos")
    st.write("Consulta, filtra y recupera información de los certificados generados por cualquier usuario del equipo.")

    col_h_f1, col_h_f2 = st.columns([2, 1])
    with col_h_f1:
        clientes_hist = ["TODOS"] + [c["nombre"] for c in db.get_clientes()]
        filtro_cliente = st.selectbox("Filtrar por Cliente:", options=clientes_hist, index=0)
    with col_h_f2:
        limite_hist = st.selectbox("Registros a mostrar:", options=[50, 100, 200, 500], index=1)

    historial_data = db.get_historial(cliente_filtro=filtro_cliente, limit=limite_hist)

    if historial_data:
        df_hist = pd.DataFrame(historial_data)
        
        # Tarjetas de estadísticas
        monto_total_acum = df_hist["total_monto"].sum()
        h_kpi1, h_kpi2, h_kpi3 = st.columns(3)
        with h_kpi1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">Certificados Emitidos</div>
                <div class="stat-value">{len(df_hist)}</div>
            </div>
            """, unsafe_allow_html=True)
        with h_kpi2:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">Monto Total Facturado (USD)</div>
                <div class="stat-value" style="color: #047857;">{format_arg_currency(monto_total_acum, symbol='USD')}</div>
            </div>
            """, unsafe_allow_html=True)
        with h_kpi3:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">Clientes en Registros</div>
                <div class="stat-value">{df_hist['cliente'].nunique()}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        # Columnas para mostrar en tabla amigable
        cols_display = ["id", "cliente", "certificado_nro", "fecha_emision", "servicio_obra", "oc_np", "total_monto", "usuario", "items_count", "created_at"]
        st.dataframe(
            df_hist[cols_display],
            use_container_width=True,
            column_config={
                "id": "ID",
                "cliente": "Cliente",
                "certificado_nro": "Certificado N°",
                "fecha_emision": "Fecha",
                "servicio_obra": "Servicio / Obra",
                "oc_np": "OC / NP",
                "total_monto": st.column_config.NumberColumn("Total USD", format="$%.2f"),
                "usuario": "Usuario",
                "items_count": "Cant Equipos",
                "created_at": "Registrado El"
            }
        )
    else:
        st.info("No hay registros en el historial para el filtro seleccionado.")

# ==========================================
# TAB 4: CONTRATOS Y LISTA DE PRECIOS
# ==========================================
with tab_precios:
    st.markdown("### 💰 Contratos y Tarifarios por Cliente")
    st.write("Gestiona la lista de precios y tarifas acordadas por contrato para cada cliente. Los valores se utilizan para sugerir y auto-completar los costos de alquiler.")

    cliente_precio_sel = st.selectbox("Seleccionar Cliente para ver Tarifario:", options=[c["nombre"] for c in db.get_clientes()])
    
    col_pr1, col_pr2 = st.columns([3, 1.5])
    with col_pr1:
        st.markdown(f"#### Tarifas Registradas para **{cliente_precio_sel}**")
    with col_pr2:
        pass

    precios_existentes = db.get_precios_cliente(cliente_precio_sel)
    if precios_existentes:
        df_p = pd.DataFrame(precios_existentes)[["equipo", "marca", "modelo", "tarifa_diaria", "tarifa_semanal", "tarifa_mensual", "modalidad_defecto", "moneda", "observaciones"]]
        st.dataframe(df_p, use_container_width=True)
    else:
        st.info(f"Aún no hay tarifas cargadas para {cliente_precio_sel}. Puedes agregar ítems abajo o importar desde Excel.")

    with st.expander("➕ Agregar Ítem al Tarifario", expanded=False):
        with st.form("form_add_precio"):
            c_eq = st.text_input("Descripción del Equipo:", placeholder="Ej: Compresor 375Q")
            col_eq1, col_eq2 = st.columns(2)
            with col_eq1:
                c_marca = st.text_input("Marca:", value="Sullair")
                c_td = st.number_input("Tarifa Diaria (USD):", min_value=0.0, value=150.0, step=10.0)
                c_tm = st.number_input("Tarifa Mensual (USD):", min_value=0.0, value=3500.0, step=100.0)
            with col_eq2:
                c_modelo = st.text_input("Modelo:", value="375Q")
                c_ts = st.number_input("Tarifa Semanal (USD):", min_value=0.0, value=900.0, step=50.0)
                c_mod = st.selectbox("Modalidad Habitual:", options=["diario", "semanal", "mensual", "fijo"])
            
            c_obs = st.text_input("Observaciones / Notas:", placeholder="Tarifa según contrato vigente")
            if st.form_submit_button("💾 Guardar Tarifa", type="primary"):
                if c_eq:
                    db.save_item_precio({
                        "cliente_id": cliente_precio_sel,
                        "equipo": c_eq,
                        "marca": c_marca,
                        "modelo": c_modelo,
                        "tarifa_diaria": c_td,
                        "tarifa_semanal": c_ts,
                        "tarifa_mensual": c_tm,
                        "modalidad_defecto": c_mod,
                        "moneda": "USD",
                        "observaciones": c_obs
                    })
                    st.success("Tarifa guardada correctamente.")
                    st.rerun()

# ==========================================
# TAB 5: GESTIÓN DE FIRMA Y LOGO
# ==========================================
with tab_firma:
    st.markdown("### ✍️ Biblioteca de Firmas de Usuario y Logo Sullair")
    st.write(f"Gestiona tus firmas digitales personales registradas para **{current_display_name}** (`{current_username}`). Puedes subir una imagen escaneada o dibujarla en pantalla.")

    col_sig_list, col_sig_add = st.columns([1.2, 1.8])

    with col_sig_list:
        st.markdown("#### 📂 Mis Firmas Registradas")
        user_sigs = db.get_user_signatures(current_username)
        if user_sigs:
            for s in user_sigs:
                st.markdown(f"**{s['alias']}** {'⭐ *(Predeterminada)*' if s['is_default'] else ''}")
                st.caption(f"{s['nombre_firmante']} — {s['cargo']}")
                pil_s = base64_to_pil(s["firma_png_base64"])
                if pil_s:
                    st.image(pil_s, width=180)
                
                col_btn_def, col_btn_del = st.columns(2)
                with col_btn_def:
                    if not s['is_default']:
                        if st.button("Hacer Default", key=f"def_{s['id']}"):
                            db.set_default_signature(current_username, s["id"])
                            st.rerun()
                with col_btn_del:
                    if st.button("Eliminar", key=f"del_{s['id']}"):
                        db.delete_signature(current_username, s["id"])
                        st.rerun()
                st.markdown("---")
        else:
            st.info("No tienes firmas registradas aún. Utiliza el formulario contiguo para registrar tu primera firma.")

    with col_sig_add:
        tab_subir, tab_dibujar = st.tabs(["📤 Subir Firma (PNG/JPG)", "✏️ Dibujar en Pantalla"])
        
        with tab_subir:
            st.markdown("##### Subir Imagen de Firma")
            st.caption("💡 Se eliminará automáticamente el fondo blanco del papel para que quede una firma transparente nítida.")
            up_sig_file = st.file_uploader("Selecciona archivo de imagen:", type=["png", "jpg", "jpeg"], key="up_sig_user")
            
            sig_alias = st.text_input("Nombre / Alias de la Firma:", value="Firma Principal", key="sig_alias_input")
            sig_name = st.text_input("Nombre y Apellido:", value=current_display_name, key="sig_name_input")
            sig_role = st.text_input("Cargo / Sector:", value="Comercial Alquileres", key="sig_role_input")
            sig_make_def = st.checkbox("Establecer como firma predeterminada", value=True, key="sig_def_input")

            if up_sig_file is not None:
                orig_img = Image.open(up_sig_file)
                clean_sig = make_transparent_signature(orig_img)
                st.image(clean_sig, caption="Vista previa de firma con fondo transparente", width=220)

                if st.button("💾 Guardar en Mi Perfil", type="primary", key="btn_save_up_sig"):
                    b64_uri = pil_to_base64_data_uri(clean_sig)
                    db.save_user_signature(
                        usuario=current_username,
                        nombre_firmante=sig_name,
                        cargo=sig_role,
                        alias=sig_alias,
                        firma_png_base64=b64_uri,
                        is_default=sig_make_def
                    )
                    st.success("✅ Firma registrada y guardada exitosamente.")
                    st.rerun()

        with tab_dibujar:
            st.markdown("##### Lienzo de Dibujo Táctil / Mouse")
            st.components.v1.html(get_html5_signature_pad_html(), height=260)
            st.caption("Una vez descargada la firma dibujada, puedes subirla en la pestaña 'Subir Firma' para agregarla a tu biblioteca permanente.")

    st.markdown("---")
    st.markdown("#### 🏢 Logo Corporativo Sullair Argentina")
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=320, caption="Isotipo y Logotipo Oficial de Sullair Argentina")
    else:
        st.warning("⚠️ No se encontró el logo en assets/logo_sullair.png")

# ==========================================
# TAB 6: PERFILES Y PLANTILLAS
# ==========================================
with tab_perfiles:
    st.markdown("### 🛠️ Configuración de Perfiles y Plantillas Dinámicas")
    st.write("Crea, clona o modifica plantillas de certificación para diferentes clientes y modalidades de facturación.")

    col_p_list, col_p_edit = st.columns([1, 2])
    with col_p_list:
        st.markdown("#### Perfiles Disponibles")
        prof_to_edit = st.radio(
            "Seleccionar para editar:",
            options=list(all_profiles.keys()),
            format_func=lambda x: all_profiles.get(x, x),
            key="p_edit_radio"
        )
        st.markdown("---")
        btn_nuevo_perfil = st.button("➕ Crear Nuevo Perfil", use_container_width=True)

    with col_p_edit:
        target_prof_data = pm.get_profile(prof_to_edit) if not btn_nuevo_perfil else {
            "id": "nuevo_perfil",
            "name": "Nuevo Cliente - Personalizado",
            "template_type": "nabors",
            "calc_mode": "diario",
            "description": "Plantilla personalizada",
            "default_metadata": {"cliente": "NUEVO CLIENTE", "certificado_nro": "1"},
            "options": {"show_dates": True, "show_tariffs": True, "show_signature": True, "show_observations": True},
            "columns": [
                {"key": "equipo", "title": "EQUIPO", "visible": True, "width_ratio": 3.0, "align": "LEFT"},
                {"key": "cant_dias", "title": "CANT DIAS", "visible": True, "width_ratio": 1.2, "align": "CENTER"},
                {"key": "tarifa", "title": "TARIFA", "visible": True, "width_ratio": 1.5, "align": "RIGHT"}
            ]
        }

        with st.form("form_perfil"):
            st.markdown(f"#### Editando Perfil: `{target_prof_data.get('id')}`")
            p_name = st.text_input("Nombre Descriptivo del Perfil:", value=target_prof_data.get("name", ""))
            p_template = st.selectbox(
                "Estructura Base de PDF:",
                options=["nabors", "ypf_noc_iade", "ypf_noc_mensual", "pluspetrol"],
                index=["nabors", "ypf_noc_iade", "ypf_noc_mensual", "pluspetrol"].index(target_prof_data.get("template_type", "nabors"))
            )
            p_calc = st.selectbox(
                "Modalidad de Cálculo de Tarifas:",
                options=["diario", "semanal", "mensual", "fijo"],
                index=["diario", "semanal", "mensual", "fijo"].index(target_prof_data.get("calc_mode", "diario"))
            )
            p_desc = st.text_area("Descripción de la Plantilla:", value=target_prof_data.get("description", ""))

            st.markdown("##### Columnas a Renderizar en el Certificado")
            cols_df = pd.DataFrame(target_prof_data.get("columns", []))
            if "visible" in cols_df.columns:
                cols_df["visible"] = cols_df["visible"].fillna(True).astype(bool)
            edited_cols_df = st.data_editor(
                cols_df,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "visible": st.column_config.CheckboxColumn("Visible", default=True),
                    "align": st.column_config.SelectboxColumn("Alineación", options=["LEFT", "CENTER", "RIGHT"], default="CENTER"),
                    "width_ratio": st.column_config.NumberColumn("Proporción de Ancho", min_value=0.5, max_value=10.0, step=0.1)
                }
            )

            if st.form_submit_button("💾 Guardar Cambios en el Perfil", type="primary"):
                target_prof_data["name"] = p_name
                target_prof_data["template_type"] = p_template
                target_prof_data["calc_mode"] = p_calc
                target_prof_data["description"] = p_desc
                target_prof_data["columns"] = edited_cols_df.to_dict(orient="records")
                saved_id = pm.save_profile(target_prof_data)
                st.success(f"✅ Perfil '{saved_id}' guardado correctamente.")
                st.rerun()

# ==========================================
# TAB 7: MANUAL DE USUARIO
# ==========================================
with tab_ayuda:
    st.markdown("""
    ### 📖 Guía de Operación y Preguntas Frecuentes

    #### 1. Formato de Fechas
    - El sistema sólo trabaja con fechas en formato latino `DD/MM/AAAA`. Los horarios (`00:00:00`) se remueven de forma automática.

    #### 2. Recorte de Hoja y Cuadro
    - Todos los certificados PDF se recortan automáticamente al terminar la firma y el logotipo, evitando espacios en blanco innecesarios.

    #### 3. Emisión Masiva (Bulk)
    - En la solapa **'Generación Masiva (Bulk)'** puedes descargar la plantilla oficial, cargar varios certificados en una sola planilla, y descargar un archivo `.ZIP` consolidado con un solo clic.

    #### 4. Gestión de Clientes y Correlativos
    - Al emitir un certificado, el sistema actualiza automáticamente el índice correlativo del cliente para sugerir el número siguiente en la próxima emisión.
    """)
