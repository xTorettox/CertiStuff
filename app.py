import os
import io
import json
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

# Importar módulos del proyecto
from utils.profile_manager import ProfileManager
from utils.excel_handler import (
    load_excel_file,
    map_excel_columns,
    parse_arg_number,
    format_arg_currency,
    get_sample_file_path,
    dataframe_to_excel_bytes
)
from utils.pdf_preview import pdf_bytes_to_images, crop_pdf_to_content
from generators import get_generator_by_template

BASE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
CUSTOM_SIG_PATH = os.path.join(ASSETS_DIR, "firma_subida.png")
DEFAULT_SIG_PATH = os.path.join(ASSETS_DIR, "firma_default.png")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo_sullair.png")

# CSS personalizado para estilo corporativo de alto impacto
st.markdown("""
<style>
    /* Estilos generales y tipografía */
    .main-header {
        background: linear-gradient(135deg, #00853E 0%, #065F2C 100%);
        color: white;
        padding: 18px 24px;
        border-radius: 12px;
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 4px 14px rgba(0, 133, 62, 0.2);
    }
    .main-header h1 {
        color: white !important;
        font-size: 1.6rem !important;
        font-weight: 700 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    .main-header p {
        color: #E2F2E9 !important;
        font-size: 0.9rem !important;
        margin: 4px 0 0 0 !important;
    }
    .stat-card {
        background: white;
        border: 1px solid #E2E8F0;
        border-left: 5px solid #00853E;
        border-radius: 10px;
        padding: 14px 18px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
    }
    .stat-label {
        color: #64748B;
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .stat-value {
        color: #0F172A;
        font-size: 1.4rem;
        font-weight: 700;
        margin-top: 4px;
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
    .preview-box {
        background: #F1F5F9;
        border: 2px dashed #CBD5E1;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Inicializar gestor de perfiles
pm = ProfileManager()
all_profiles = pm.list_profiles()

# Encabezado corporativo
st.markdown("""
<div class="main-header">
    <div>
        <h1>Generador de Certificados de Alquiler y Servicios</h1>
        <p>Automatización de Certificaciones PDF con Firma Digital | Sullair Argentina</p>
    </div>
    <div style="background: rgba(255,255,255,0.15); padding: 8px 16px; border-radius: 8px; text-align: right;">
        <span style="font-size: 0.8rem; font-weight: 600; color: white;">Sucursal Neuquén & Valle</span><br>
        <span style="font-size: 0.75rem; color: #DCFCE7;">Industriales Neuquinos 2920, PIN</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Tabs principales
tab_cert, tab_perfiles, tab_firma, tab_ayuda = st.tabs([
    "📋 Generador de Certificados",
    "⚙️ Gestor de Perfiles Dinámicos",
    "✍️ Gestión de Firma y Logo",
    "📖 Manual de Usuario"
])

# ==========================================
# TAB 1: GENERADOR DE CERTIFICADOS
# ==========================================
with tab_cert:
    # Barra lateral: Selección de perfil y configuraciones rápidas
    with st.sidebar:
        st.markdown("### ⚙️ Configuración del Certificado")
        
        # 1. Selección de Perfil
        profile_options = list(all_profiles.keys())
        default_index = 0
        if "selected_profile_id" in st.session_state and st.session_state.selected_profile_id in profile_options:
            default_index = profile_options.index(st.session_state.selected_profile_id)
            
        selected_profile_id = st.selectbox(
            "Seleccionar Perfil / Cliente:",
            options=profile_options,
            format_func=lambda x: all_profiles.get(x, x),
            index=default_index,
            key="sb_profile"
        )
        st.session_state.selected_profile_id = selected_profile_id
        active_profile = pm.get_profile(selected_profile_id)

        st.markdown("---")
        st.markdown("#### ⚡ Opciones Rápidas")
        
        # Opciones por perfil con checkboxes persistentes
        default_options = active_profile.get("options", {}) if active_profile else {}
        
        show_dates = st.checkbox(
            "Mostrar Fechas Inicio / Fin",
            value=default_options.get("show_dates", False),
            key=f"opt_{selected_profile_id}_dates",
            help="Incluye las columnas de Inicio y Fin del período en la tabla de equipos."
        )
        
        show_tariffs = st.checkbox(
            "Mostrar Tarifas y Montos",
            value=default_options.get("show_tariffs", True),
            key=f"opt_{selected_profile_id}_tariffs",
            help="Muestra u oculta los valores monetarios en la certificación."
        )
        
        show_signature = st.checkbox(
            "Incluir Firma Digital",
            value=default_options.get("show_signature", True),
            key=f"opt_{selected_profile_id}_sig",
            help="Estampa la firma escaneada del responsable comercial al pie."
        )
        
        show_obs = st.checkbox(
            "Incluir Observaciones",
            value=default_options.get("show_observations", True),
            key=f"opt_{selected_profile_id}_obs",
            help="Habilita el recuadro de observaciones o deducciones."
        )

        trim_frame = st.checkbox(
            "Recortar Recuadro al Contenido",
            value=default_options.get("trim_frame", True),
            key=f"opt_{selected_profile_id}_trim",
            help="Cierra el marco perimetral negro justo después de las firmas/observaciones para evitar adulteraciones o espacios vacíos innecesarios."
        )

        recortar_hoja = st.checkbox(
            "Ajustar hoja al certificado (sin blanco inferior)",
            value=default_options.get("crop_page", True),
            key=f"opt_{selected_profile_id}_crop_page",
            help="Recorta el tamaño físico del PDF para que termine exactamente donde finaliza el recuadro del certificado, como en la imagen de ejemplo."
        )

        include_other_charges = False
        if active_profile and (active_profile.get("template_type") == "pluspetrol" or "pluspetrol" in selected_profile_id):
            include_other_charges = st.checkbox(
                "Incluir Tabla de 'Otros Cargos'",
                value=default_options.get("include_other_charges", True),
                key=f"opt_{selected_profile_id}_oc",
                help="Agrega la tabla secundaria de fletes, seguros y cargos adicionales."
            )

        st.markdown("---")
        st.markdown("#### 📝 Metadatos del Encabezado")
        
        # Cargar valores por defecto del perfil
        def_meta = active_profile.get("default_metadata", {}) if active_profile else {}
        template_type = active_profile.get("template_type", "nabors") if active_profile else "nabors"

        def get_meta_field(field_name: str, label: str, default_val: str, is_area: bool = False, height: int = 80) -> str:
            k = f"meta_{selected_profile_id}_{field_name}"
            if k not in st.session_state:
                st.session_state[k] = default_val
            if is_area:
                return st.text_area(label, key=k, height=height)
            return st.text_input(label, key=k)

        meta_inputs = {}

        if template_type == "nabors":
            meta_inputs["certificado_nro"] = get_meta_field("certificado_nro", "Certificado N°:", str(def_meta.get("certificado_nro", "45")))
            meta_inputs["cliente"] = get_meta_field("cliente", "Cliente:", str(def_meta.get("cliente", "NABORS")))
            meta_inputs["servicio"] = get_meta_field("servicio", "Servicio:", str(def_meta.get("servicio", "F36")))
            meta_inputs["oc_np"] = get_meta_field("oc_np", "OC / NP N°:", str(def_meta.get("oc_np", "19084416")))
            meta_inputs["sucursal"] = def_meta.get("sucursal", "Sucursal NQN y Valle")
            meta_inputs["direccion"] = def_meta.get("direccion", "Industriales Neuquinos 2920, PIN")
            meta_inputs["telefono"] = def_meta.get("telefono", "T:[0299] 4782500")

        elif template_type == "ypf_noc_iade":
            meta_inputs["titulo"] = get_meta_field("titulo", "Título:", str(def_meta.get("titulo", "REPARACIONES DE EQUIPOS")))
            meta_inputs["contrato_sap"] = get_meta_field("contrato_sap", "Contrato SAP:", str(def_meta.get("contrato_sap", "4900102848")))
            meta_inputs["almacen"] = get_meta_field("almacen", "Almacén:", str(def_meta.get("almacen", "NOC")))
            meta_inputs["subtotal_label"] = def_meta.get("subtotal_label", "SUBTOTOTAL")

        elif template_type == "ypf_noc_mensual":
            meta_inputs["titulo"] = get_meta_field("titulo", "Título:", str(def_meta.get("titulo", "SERVICIO ALQUILER DE EQUIPOS")))
            meta_inputs["contrato_sap"] = get_meta_field("contrato_sap", "Contrato SAP:", str(def_meta.get("contrato_sap", "4900114308")))
            meta_inputs["almacen"] = get_meta_field("almacen", "Almacén:", str(def_meta.get("almacen", "NOC")))
            meta_inputs["periodo"] = get_meta_field("periodo", "Período:", str(def_meta.get("periodo", "21/09/2026 al 20/10/2026")))

        elif template_type == "pluspetrol":
            meta_inputs["certificado_nro"] = get_meta_field("certificado_nro", "Certificado N°:", str(def_meta.get("certificado_nro", "112")))
            meta_inputs["cliente"] = get_meta_field("cliente", "Cliente:", str(def_meta.get("cliente", "PLUSPETROL S.A.")))
            meta_inputs["obra"] = get_meta_field("obra", "Obra / Yacimiento:", str(def_meta.get("obra", "Yacimiento La Calera")))
            meta_inputs["periodo"] = get_meta_field("periodo", "Período:", str(def_meta.get("periodo", "01/10/2026 al 31/10/2026")))
            meta_inputs["oc_np"] = get_meta_field("oc_np", "OC / NP N°:", str(def_meta.get("oc_np", "4500987621")))

        # Firmante
        st.markdown("---")
        st.markdown("#### 🖋️ Datos del Firmante")
        meta_inputs["firmante_nombre"] = get_meta_field("firmante_nombre", "Nombre Responsable:", "Federico García Cendra")
        meta_inputs["firmante_cargo"] = get_meta_field("firmante_cargo", "Cargo / Sector:", "Comercial Alquileres")

        # Observaciones
        if show_obs:
            default_obs = def_meta.get("observacion") or def_meta.get("observaciones", "")
            meta_inputs["observacion"] = get_meta_field("observacion", "Observaciones / Deducciones:", default_obs, is_area=True, height=80)
            meta_inputs["observaciones"] = meta_inputs["observacion"]

    # ÁREA PRINCIPAL: Carga y Edición de Datos
    col_upload1, col_upload2, col_upload3 = st.columns([3, 1.5, 1.5])
    
    with col_upload1:
        uploaded_file = st.file_uploader(
            f"📂 Cargar archivo Excel (.xlsx) para {active_profile.get('name')}:",
            type=["xlsx", "xls"],
            help="Sube un archivo Excel. Los nombres de columna se mapearán automáticamente al perfil seleccionado."
        )

    with col_upload2:
        st.write("")
        st.write("")
        btn_cargar_muestra = st.button("🔄 Cargar Datos de Ejemplo", use_container_width=True)

    with col_upload3:
        st.write("")
        st.write("")
        sample_path = get_sample_file_path(selected_profile_id)
        if sample_path and os.path.exists(sample_path):
            with open(sample_path, "rb") as sf:
                st.download_button(
                    "📥 Descargar Plantilla Excel",
                    data=sf.read(),
                    file_name=f"plantilla_{selected_profile_id}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

    # Lógica de carga del DataFrame
    data_key = f"df_data_{selected_profile_id}"
    editor_key = f"editor_{selected_profile_id}"
    
    # Si el usuario subió un archivo nuevo
    if uploaded_file is not None:
        try:
            df_loaded = load_excel_file(uploaded_file, active_profile)
            st.session_state[data_key] = df_loaded
            st.session_state.pop(editor_key, None)
            st.success("✅ Archivo Excel cargado y mapeado exitosamente.")
        except Exception as e:
            st.error(f"Error al leer el archivo Excel: {e}")

    # Si hizo click en cargar datos de ejemplo o aún no hay datos en session state
    elif btn_cargar_muestra or data_key not in st.session_state:
        if sample_path and os.path.exists(sample_path):
            try:
                df_sample = load_excel_file(sample_path, active_profile)
                st.session_state[data_key] = df_sample
                st.session_state.pop(editor_key, None)
                if btn_cargar_muestra:
                    for k in list(st.session_state.keys()):
                        if k.startswith(f"meta_{selected_profile_id}_"):
                            st.session_state.pop(k, None)
                    st.rerun()
            except Exception as e:
                st.error(f"Error al cargar muestra: {e}")

    # Obtener el DataFrame base estable de session_state
    current_df = st.session_state.get(data_key, pd.DataFrame())

    if not current_df.empty:
        st.markdown("---")
        st.markdown("#### 📊 Revisión y Edición Interactiva de Datos")
        st.caption("💡 Puedes editar celdas directamente (presiona **ENTER** o **TAB** para confirmar), agregar/eliminar filas, o desmarcar **Incluir en PDF** para excluir ítems.")

        # Editor de datos interactivo - no sobreescribir current_df en session_state para garantizar edición fluida sin reversión de campos
        edited_df = st.data_editor(
            current_df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "_incluir": st.column_config.CheckboxColumn(
                    "Incluir en PDF",
                    default=True,
                    help="Marca o desmarca para incluir esta fila en el certificado."
                )
            },
            key=editor_key
        )

        # Calcular totales actuales para mostrar KPIs directamente desde los datos editados
        calc_mode = active_profile.get("calc_mode", "diario")
        incluidos = edited_df[edited_df.get("_incluir", True)] if "_incluir" in edited_df.columns else edited_df
        total_items = len(incluidos)
        
        # Sumar totales
        total_monto = 0.0
        for _, r in edited_df.iterrows():
            if r.get("_incluir", True):
                total_monto += pm.calculate_row_total(r.to_dict(), calc_mode)

        # Tarjetas de estadísticas reactivas
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        with kpi1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">Cliente / Plantilla</div>
                <div class="stat-value" style="font-size: 1.1rem; color: #00853E;">{active_profile.get('name').split('-')[0].strip()}</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi2:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">Ítems Seleccionados</div>
                <div class="stat-value">{total_items} / {len(edited_df)}</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi3:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">Modalidad de Cálculo</div>
                <div class="stat-value" style="font-size: 1.1rem;">{calc_mode.upper()}</div>
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
            oc_key = f"df_otros_cargos_{selected_profile_id}"
            oc_editor_key = f"editor_oc_{selected_profile_id}"
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
                key=oc_editor_key
            )
            meta_inputs["otros_cargos_df"] = edited_oc_df

        st.markdown("---")
        
        # SECCIÓN DE GENERACIÓN Y PREVISUALIZACIÓN PDF
        col_gen_btn, col_down_btn = st.columns([2, 2])
        
        # Opciones consolidadas
        render_options = {
            "show_dates": show_dates,
            "show_tariffs": show_tariffs,
            "show_signature": show_signature,
            "show_observations": show_obs,
            "include_other_charges": include_other_charges,
            "trim_frame": trim_frame
        }

        # Generador de PDF
        generator = get_generator_by_template(template_type)
        
        try:
            pdf_buffer = io.BytesIO()
            pdf_bytes = generator.build_pdf(
                buffer=pdf_buffer,
                metadata=meta_inputs,
                df_data=edited_df,
                options=render_options
            )
            # Si se activa recortar hoja, ajustar altura física del PDF al contenido
            if recortar_hoja:
                pdf_bytes = crop_pdf_to_content(pdf_bytes, margin_bottom=24.0)
            
            # Nombre de archivo dinámico y amigable
            clean_client = selected_profile_id.replace("ypf_noc_", "").upper()
            cert_id = meta_inputs.get("certificado_nro") or meta_inputs.get("contrato_sap", "1")
            download_filename = f"Certificado_{clean_client}_{cert_id}.pdf"

            with col_gen_btn:
                st.success(f"📄 Certificado PDF generado con éxito ({len(pdf_bytes):,} bytes).")

            with col_down_btn:
                st.download_button(
                    label=f"💾 Descargar {download_filename}",
                    data=pdf_bytes,
                    file_name=download_filename,
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary"
                )

            # Previsualización visual de alta fidelidad
            st.markdown("### 👁️ Vista Previa del Certificado Generado")
            preview_images = pdf_bytes_to_images(pdf_bytes, dpi=160)
            
            if preview_images:
                for idx, img_bytes in enumerate(preview_images):
                    if len(preview_images) > 1:
                        st.caption(f"Página {idx + 1} de {len(preview_images)}")
                    st.image(img_bytes, use_container_width=True)
            else:
                st.info("Previsualización gráfica no disponible, puedes descargar el archivo PDF con el botón superior.")

        except Exception as e:
            st.error(f"Error generando el documento PDF: {e}")
            import traceback
            st.code(traceback.format_exc())

    else:
        st.warning("No hay datos cargados para este perfil. Haz clic en 'Cargar Datos de Ejemplo' o sube un archivo Excel.")

# ==========================================
# TAB 2: GESTOR DE PERFILES DINÁMICOS
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
                index=["nabors", "ypf_noc_iade", "ypf_noc_mensual", "pluspetrol"].index(target_prof_data.get("template_type", "nabors")),
                help="Define el diseño del encabezado, tablas y ubicación de logos/firmas según el cliente."
            )

            p_calc = st.selectbox(
                "Modalidad de Cálculo de Tarifas:",
                options=["diario", "semanal", "mensual", "fijo"],
                index=["diario", "semanal", "mensual", "fijo"].index(target_prof_data.get("calc_mode", "diario")),
                help="• Diario: Días * Tarifa\n• Semanal: (Días/7) * Tarifa\n• Mensual: Cantidad * Tarifa o (Días/30) * Tarifa\n• Fijo: Toma el valor exacto de la celda de Excel."
            )

            p_desc = st.text_area("Descripción de la Plantilla:", value=target_prof_data.get("description", ""))

            st.markdown("##### Columnas a Renderizar en el Certificado")
            cols_df = pd.DataFrame(target_prof_data.get("columns", []))
            
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

            btn_guardar_perfil = st.form_submit_button("💾 Guardar Cambios en el Perfil", type="primary")

            if btn_guardar_perfil:
                target_prof_data["name"] = p_name
                target_prof_data["template_type"] = p_template
                target_prof_data["calc_mode"] = p_calc
                target_prof_data["description"] = p_desc
                target_prof_data["columns"] = edited_cols_df.to_dict(orient="records")
                
                saved_id = pm.save_profile(target_prof_data)
                st.success(f"✅ Perfil '{saved_id}' guardado correctamente.")
                st.rerun()

# ==========================================
# TAB 3: GESTIÓN DE FIRMA Y LOGO
# ==========================================
with tab_firma:
    st.markdown("### ✍️ Gestión de Firmas y Logos Corporativos")
    st.write("Configura la firma digital escaneada y visualiza el isotipo corporativo de Sullair Argentina.")

    col_sig1, col_sig2 = st.columns(2)

    with col_sig1:
        st.markdown("#### 🖋️ Firma Digital Escaneada (PNG Transparente)")
        
        # Verificar firma actual
        current_sig_path = CUSTOM_SIG_PATH if os.path.exists(CUSTOM_SIG_PATH) else DEFAULT_SIG_PATH
        if os.path.exists(current_sig_path):
            st.image(current_sig_path, caption="Firma actual en uso", width=260)
            if current_sig_path == CUSTOM_SIG_PATH:
                st.info("ℹ️ Estás usando una firma personalizada subida desde tu equipo.")
            else:
                st.info("ℹ️ Estás usando la firma corporativa por defecto (Federico García Cendra).")

        # Subir nueva firma
        uploaded_sig = st.file_uploader(
            "Cargar firma escaneada (.PNG con fondo transparente):",
            type=["png"],
            key="sig_uploader"
        )
        
        col_sig_save, col_sig_reset = st.columns(2)
        with col_sig_save:
            if uploaded_sig is not None:
                if st.button("💾 Guardar Nueva Firma", use_container_width=True, type="primary"):
                    with open(CUSTOM_SIG_PATH, "wb") as f:
                        f.write(uploaded_sig.getbuffer())
                    st.success("✅ Firma guardada exitosamente.")
                    st.rerun()

        with col_sig_reset:
            if os.path.exists(CUSTOM_SIG_PATH):
                if st.button("🔄 Restaurar Firma por Defecto", use_container_width=True):
                    os.remove(CUSTOM_SIG_PATH)
                    st.success("✅ Se restauró la firma predeterminada.")
                    st.rerun()

    with col_sig2:
        st.markdown("#### 🏢 Isotipo Corporativo Sullair Argentina")
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, caption="Logo corporativo oficial de Sullair Argentina", width=340)
            st.success("✅ Logo estático cargado y listo para ser estampado en encabezados y pies de página.")
        else:
            st.warning("⚠️ No se encontró el archivo de logo corporativo en assets/logo_sullair.png")

# ==========================================
# TAB 4: MANUAL DE USUARIO
# ==========================================
with tab_ayuda:
    st.markdown("""
    ### 📖 Guía Rápida de Uso del Sistema

    Esta aplicación automatiza el flujo de emisión de certificados de alquiler y servicios para contratistas y operadoras:

    1. **Selección del Perfil:**
       - En el panel lateral, elige el perfil del cliente (Nabors, YPF NOC IADE, YPF NOC Mensual, Pluspetrol).
       - Cada perfil configura automáticamente los encabezados, columnas requeridas y fórmula de tarifas.

    2. **Carga del Archivo Excel:**
       - Haz clic en **'Descargar Plantilla Excel'** para obtener el formato recomendado o sube directamente el archivo de tu equipo.
       - El sistema mapea nombres de columnas mediante sinónimos y variaciones (ej: 'N° Serie', 'Interno', 'CANT DIAS', etc.).

    3. **Revisión y Edición:**
       - Utiliza la tabla interactiva para ajustar valores o desmarcar la columna **'Incluir en PDF'** para excluir filas no certificadas.
       - Si estás emitiendo para Pluspetrol, puedes sumar fletes y seguros técnicos en la tabla de **'Otros Cargos'**.

    4. **Emisión y Descarga:**
       - Al presionar **'Descargar Certificado'**, obtendrás un documento PDF con resolución vectorial, marco exterior continuo, logo de Sullair Argentina y firma estampada.
    """)
