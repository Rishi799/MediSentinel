"""MediSentinel Streamlit app - entry point: sign-in screen and page navigation.

Run from the repo root:  streamlit run app/Home.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from app import session, ui

APP_DIR = Path(__file__).resolve().parent

st.set_page_config(
    page_title="MediSentinel",
    page_icon=str(APP_DIR / "assets" / "icon.svg"),
    layout="wide",
    initial_sidebar_state="expanded",
)
ui.apply_styles()
session.init_session()


def login_page():
    """Sign-in screen: the database itself checks the username and password."""
    st.markdown(
        '<div class="ms-login-brand"><div class="ms-logo">🛡️</div><h1>MediSentinel</h1>'
        '<p>Intelligent Medication Safety &amp; Adverse-Reaction Surveillance</p></div>',
        unsafe_allow_html=True)

    _, form_col, info_col, _ = st.columns([0.5, 1.15, 1.15, 0.5], gap="large")

    with form_col:
        with st.container(border=True):
            st.markdown("#### Sign in")
            st.caption("Use the database login for your role.")
            with st.form("login_form", border=False):
                username = st.text_input("Username", placeholder="ms_doctor / ms_pharmacist / ms_admin")
                password = st.text_input("Password", type="password", placeholder="Your role password")
                submit = st.form_submit_button("Sign in", type="primary", width="stretch",
                                               icon=":material/login:")
            if submit:
                success, error_msg = session.login(username, password)
                if success:
                    st.rerun()
                else:
                    st.error(error_msg, icon=":material/error:")

    with info_col:
        st.markdown("#### What MediSentinel does")
        features = [
            ("⚡", "Real-time safety check",
             "A database trigger checks every new medicine against the patient's other medicines, "
             "conditions and allergies."),
            ("🔐", "Role-based access in the database",
             "Doctors write, pharmacists only read, and no one can forge or delete an alert."),
            ("🌐", "openFDA surveillance data",
             "Drug labels and adverse-event reports in MongoDB back the safety rules."),
        ]
        st.markdown("".join(
            f'<div class="ms-feature"><div class="ms-feature-icon">{icon}</div>'
            f'<div><b>{title}</b><br><span>{text}</span></div></div>'
            for icon, title, text in features), unsafe_allow_html=True)
        st.markdown(
            "| Login | Access |\n|---|---|\n"
            "| `ms_doctor` | Patients, prescriptions, alert overrides |\n"
            "| `ms_pharmacist` | View only |\n"
            "| `ms_admin` | Everything, incl. data loading |")

    st.markdown('<div class="ms-footer">DBMS Laboratory Project (CD252IA) · RV College of Engineering · '
                'Dept. of CSE (AI &amp; ML)</div>', unsafe_allow_html=True)


if not session.is_logged_in():
    nav = st.navigation([st.Page(login_page, title="Sign in", icon=":material/login:")], position="hidden")
else:
    st.logo(str(APP_DIR / "assets" / "logo.svg"), icon_image=str(APP_DIR / "assets" / "icon.svg"),
            size="large")
    pages = APP_DIR / "pages"
    nav = st.navigation({
        "Overview": [
            st.Page(pages / "0_Dashboard.py", title="Dashboard", icon=":material/dashboard:", default=True),
        ],
        "Clinical": [
            st.Page(pages / "1_Patients.py", title="Patients", icon=":material/groups:"),
            st.Page(pages / "2_Prescriptions.py", title="Prescriptions", icon=":material/medication:"),
            st.Page(pages / "3_Alerts.py", title="Safety alerts", icon=":material/notifications_active:"),
        ],
        "Surveillance": [
            st.Page(pages / "4_Drug_Safety.py", title="Drug safety data", icon=":material/monitoring:"),
        ],
    })
    session.render_sidebar_status()

nav.run()
