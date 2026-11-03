import os
import streamlit as st
from typing import Optional, Dict

DEFAULT_PASSWORDS = {
    "fcendra": "sullair2026",
    "admin": "sullair2026",
    "comercial": "sullair123",
    "operaciones": "sullair123"
}

def get_auth_credentials() -> Dict[str, str]:
    """Obtiene los usuarios y contraseñas de st.secrets o valores predeterminados."""
    try:
        if hasattr(st, "secrets") and "passwords" in st.secrets:
            return dict(st.secrets["passwords"])
        if hasattr(st, "secrets") and "users" in st.secrets:
            return dict(st.secrets["users"])
    except Exception:
        pass
    return DEFAULT_PASSWORDS

def check_authentication() -> bool:
    """Verifica si el usuario está autenticado en st.session_state."""
    if st.session_state.get("authenticated", False):
        return True

    # Renderizar pantalla de login corporativa
    col_l1, col_l2, col_l3 = st.columns([1, 1.8, 1])
    with col_l2:
        st.write("")
        st.write("")
        
        # Logo Sullair
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "logo_sullair.png")
        if os.path.exists(logo_path):
            st.image(logo_path, width=280)
        
        st.markdown("""
        <div style="background: white; border: 1px solid #E2E8F0; border-top: 4px solid #00853E; border-radius: 12px; padding: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.06);">
            <h2 style="color: #0F172A; margin: 0 0 6px 0; font-size: 1.4rem;">Iniciar Sesión</h2>
            <p style="color: #64748B; font-size: 0.88rem; margin-bottom: 18px;">Sistema de Certificados de Alquiler y Servicios</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("Usuario:", placeholder="Ej: fcendra, comercial").strip().lower()
            password = st.text_input("Contraseña:", type="password")
            submitted = st.form_submit_button("Ingresar al Sistema", use_container_width=True, type="primary")

            if submitted:
                users = get_auth_credentials()
                if username in users and str(users[username]) == str(password):
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = username
                    st.session_state["user_display_name"] = "Federico García Cendra" if username == "fcendra" else username.capitalize()
                    st.success("Acceso concedido...")
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas. Verifique su usuario y contraseña.")

    return False

def render_user_sidebar():
    """Muestra la tarjeta del usuario autenticado en la barra lateral con opción de salir."""
    username = st.session_state.get("username", "usuario")
    display_name = st.session_state.get("user_display_name", username.capitalize())
    
    st.sidebar.markdown(f"""
    <div style="background: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 8px; padding: 10px 14px; margin-bottom: 14px;">
        <div style="font-size: 0.75rem; color: #64748B; font-weight: 600; text-transform: uppercase;">Sesión Activa</div>
        <div style="font-size: 0.95rem; font-weight: 700; color: #0F172A;">👤 {display_name}</div>
        <div style="font-size: 0.78rem; color: #00853E; font-weight: 600;">Sullair Argentina</div>
    </div>
    """, unsafe_allow_html=True)

    if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state["username"] = None
        st.rerun()

