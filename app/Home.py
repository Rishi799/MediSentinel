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
    initial_sidebar_state="auto",
)
ui.apply_styles()
session.init_session()


def _block(cx, cy, a, h, top, left, right, label, cls="blk", main=False, side=False):
    """One isometric box: a diamond top face and two shaded side faces, with its table name above."""
    t = f"{cx},{cy - a / 2} {cx + a},{cy} {cx},{cy + a / 2} {cx - a},{cy}"
    lf = f"{cx - a},{cy} {cx},{cy + a / 2} {cx},{cy + a / 2 + h} {cx - a},{cy + h}"
    rf = f"{cx},{cy + a / 2} {cx + a},{cy} {cx + a},{cy + h} {cx},{cy + a / 2 + h}"
    text_cls = "lbl-main" if main else "lbl"
    return (f'<g class="{cls}"><polygon points="{lf}" fill="{left}"/><polygon points="{rf}" fill="{right}"/>'
            f'<polygon points="{t}" fill="{top}" stroke="#FFFFFF" stroke-opacity="0.7"/>'
            + (f'<text x="{cx + a + 12}" y="{cy + h / 2 + 4}" class="{text_cls}">{label}</text></g>' if side else
               f'<text x="{cx}" y="{cy - a / 2 - 10}" text-anchor="middle" class="{text_cls}">{label}</text></g>'))


def schema_scene():
    """Isometric view of the real data flow: three tables feed the safety trigger, which writes Alert_Log."""
    pale = ("#E9F7F1", "#C7E9DB", "#B2DFCC")
    mid = ("#CFEFE2", "#9FD5BF", "#86C9AE")
    green = ("#34C08F", "#0E7A5C", "#0B6B50")
    alert = ("#FCF2F2", "#F2D6D6", "#E8C3C3")
    lines = "".join(
        f'<path class="flow" d="M{x1} {y1} L{x2} {y2}" stroke="{c}" stroke-width="2" fill="none"/>'
        for x1, y1, x2, y2, c in ((110, 172, 222, 228, "#34C08F"), (270, 104, 270, 196, "#34C08F"),
                                  (430, 172, 318, 228, "#34C08F"), (270, 282, 270, 330, "#D46A6A")))
    return (
        '<svg class="ms-iso" viewBox="0 0 540 420" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
        '<ellipse cx="270" cy="228" rx="120" ry="60" fill="#34C08F" class="pulse" opacity="0.3"/>'
        + lines
        + _block(110, 150, 46, 26, *pale, "Patient", "blk d1")
        + _block(270, 82, 46, 26, *mid, "Prescription", "blk d2")
        + _block(430, 150, 46, 26, *pale, "Medication", "blk d3")
        + _block(270, 214, 66, 40, *green, "trg_medication_safety", "blk", main=True, side=True)
        + '<path d="M252 214 l12 11 l24 -22" stroke="#FFFFFF" stroke-width="6" fill="none" stroke-linecap="round" '
          'stroke-linejoin="round" class="blk"/>'
        + _block(270, 352, 46, 24, *alert, "Alert_Log", "blk d1", side=True)
        + '</svg>')


def login_page():
    """Split screen: the isometric schema story on the left, the sign-in card on the right.
    The username and password are checked by PostgreSQL itself."""
    ui.apply_login_styles()
    story_col, _, form_col = st.columns([1.2, 0.1, 0.85])

    with story_col:
        st.markdown(
            f'<div class="ms-story"><div class="ms-brand"><div class="ms-brand-mark">{ui.icon("shield", 18, "#FFFFFF")}'
            '</div>MediSentinel</div>'
            '<h1>Medication safety,<br><em>enforced by the database.</em></h1>'
            '<p class="lead">Every prescription passes through a PostgreSQL trigger that checks interactions, '
            'contraindications and allergies before it is saved.</p>'
            f'{schema_scene()}</div>', unsafe_allow_html=True)

    with form_col:
        st.markdown('<div class="ms-signin-gap"></div>', unsafe_allow_html=True)
        with st.container(key="login_card"):
            st.markdown(f'<div class="ms-signin-badge">{ui.icon("lock", 14)}Secured by PostgreSQL roles</div>'
                        '<h2 class="ms-signin-title">Welcome back</h2>'
                        '<p class="ms-signin-sub">Sign in with the database login for your role.</p>',
                        unsafe_allow_html=True)
            with st.form("login_form", border=False):
                username = st.text_input("Username", placeholder="ms_doctor")
                password = st.text_input("Password", type="password", placeholder="Your role password")
                submit = st.form_submit_button("Sign in", type="primary", width="stretch")
            if submit:
                success, error_msg = session.login(username, password)
                if success:
                    st.rerun()
                else:
                    st.error(error_msg, icon=":material/error:")
            st.markdown(f'<div class="ms-signin-note">{ui.icon("info", 15)}What you can see and change depends '
                        'on your role.</div>', unsafe_allow_html=True)


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
            st.Page(pages / "5_Analytics.py", title="Analytics", icon=":material/insights:"),
        ],
    })
    session.render_sidebar_status()

nav.run()
