import streamlit as st
from sullapps_ui import verify_sullapps_sso, clear_sullapps_sso, render_sullapps_portal_notice


def check_authentication() -> bool:
    """Verifica si el usuario está autenticado vía SSO SullApps."""
    sso_identity = verify_sullapps_sso()
    if sso_identity:
        sso_user = sso_identity.get("username", "usuario")
        st.session_state["authenticated"] = True
        st.session_state["username"] = sso_user
        st.session_state["user_display_name"] = sso_identity.get("display_name") or sso_user
        st.session_state["user_role"] = sso_identity.get("role", "user")
        return True

    render_sullapps_portal_notice(app_slug="certiflow")
    return False


def render_user_sidebar():
    """Muestra la tarjeta del usuario autenticado en la barra lateral."""
    username = st.session_state.get("username", "usuario")
    display_name = st.session_state.get("user_display_name", username.capitalize())
    role = st.session_state.get("user_role", "user")
    role_label = "Administrador" if role == "admin" else "Usuario SullApps"

    st.sidebar.markdown(f"""
    <div style="background: #F1F5F9; border: 1px solid #CBD5E1; border-left: 4px solid #006837; border-radius: 8px; padding: 10px 14px; margin-bottom: 14px;">
        <div style="font-size: 0.72rem; color: #64748B; font-weight: 700; text-transform: uppercase;">Sesión SSO SullApps</div>
        <div style="font-size: 0.95rem; font-weight: 700; color: #0F172A; margin-top: 2px;">👤 {display_name}</div>
        <div style="font-size: 0.76rem; color: #006837; font-weight: 600;">@{username} · {role_label}</div>
    </div>
    """, unsafe_allow_html=True)
