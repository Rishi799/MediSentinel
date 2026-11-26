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
    """Split-screen sign-in: product story on the left, the form on the right.
    The username and password are checked by PostgreSQL itself."""
    ui.apply_login_styles()
    hero_col, _, form_col = st.columns([1.1, 0.12, 0.9])

    with hero_col:
        items = [
            ("zap", "Checked the moment it is prescribed",
             "A database trigger compares each medicine with the patient's medicines, conditions and allergies."),
            ("lock", "Permissions enforced by PostgreSQL",
             "Doctors write, pharmacists read, and no login can forge or delete a safety alert."),
            ("globe", "Backed by openFDA",
             "Drug labels and adverse-event reports in MongoDB keep the safety knowledge current."),
        ]
        rows = "".join(
            f'<div class="ms-hero-item"><div class="ic">{ui.icon(name, 17)}</div>'
            f'<div><b>{title}</b><br><span>{text}</span></div></div>' for name, title, text in items)
        st.markdown(
            f'<div class="ms-hero"><div class="ms-hero-brand"><div class="ms-hero-mark">'
            f'{ui.icon("shield", 18, "#FFFFFF")}</div>MediSentinel</div>'
            f'<h1>Medication safety,<br>enforced by the database.</h1>'
            f'<p class="lead">Real-time interaction, contraindication and allergy checks for every prescription, '
            f'with an audit trail for every override.</p>'
            f'<div class="ms-hero-list">{rows}</div>'
            f'<div class="ms-hero-foot">DBMS Laboratory (CD252IA) · RV College of Engineering · '
            f'Dept. of CSE (AI &amp; ML)</div></div>', unsafe_allow_html=True)

    with form_col:
        st.markdown('<div style="height:5.5rem"></div><h2 class="ms-signin-title">Sign in</h2>'
                    '<p class="ms-signin-sub">Use the database login for your role.</p>', unsafe_allow_html=True)
        with st.form("login_form", border=False):
            username = st.text_input("Username", placeholder="e.g. ms_doctor")
            password = st.text_input("Password", type="password", placeholder="Your role password")
            submit = st.form_submit_button("Sign in", type="primary", width="stretch")
        if submit:
            success, error_msg = session.login(username, password)
            if success:
                st.rerun()
            else:
                st.error(error_msg, icon=":material/error:")
        st.markdown(
            '<div class="ms-roles">'
            '<div class="ms-role"><code>ms_doctor</code><span>Patients, prescriptions, overrides</span></div>'
            '<div class="ms-role"><code>ms_pharmacist</code><span>Read-only review</span></div>'
            '<div class="ms-role"><code>ms_admin</code><span>Full access, data loading</span></div></div>',
            unsafe_allow_html=True)


if not session.is_logged_in():
    nav = st.navigation([st.Page(login_page, title="Sign in", icon=":material/login:")], position="hidden")
else:
    st.logo(str(APP_DIR / "assets" / "logo.svg"), icon_image=str(APP_DIR / "assets" / "icon.svg"),
            size="large")
    pages = APP_DIR / "pages"
    nav = st.navigation({
        "Overview": [
            st.Page(pages / "0_Dashboard.py", title="Dashboard", icon=":material/space_dashboard:", default=True),
        ],
        "Clinical": [
            st.Page(pages / "1_Patients.py", title="Patients", icon=":material/group:"),
            st.Page(pages / "2_Prescriptions.py", title="Prescriptions", icon=":material/prescriptions:"),
            st.Page(pages / "3_Alerts.py", title="Safety alerts", icon=":material/notifications:"),
        ],
        "Surveillance": [
            st.Page(pages / "4_Drug_Safety.py", title="Drug safety data", icon=":material/monitoring:"),
        ],
    })
    session.render_sidebar_status()

nav.run()
