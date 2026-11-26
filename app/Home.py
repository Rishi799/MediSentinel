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


SCENE_SVG = """
<svg class="ms-3d-art" viewBox="0 0 420 300" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <defs>
    <linearGradient id="shieldFront" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#34C08F"/><stop offset="0.55" stop-color="#139170"/><stop offset="1" stop-color="#0B6B50"/>
    </linearGradient>
    <linearGradient id="shieldSide" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#0A5A43"/><stop offset="1" stop-color="#073F30"/>
    </linearGradient>
    <linearGradient id="shine" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#FFFFFF" stop-opacity="0.55"/><stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="capGreen" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#5FD1A8"/><stop offset="1" stop-color="#119072"/>
    </linearGradient>
    <linearGradient id="capWhite" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#D9E6E1"/>
    </linearGradient>
    <linearGradient id="dbBody" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#C9EBDD"/><stop offset="0.5" stop-color="#F2FBF7"/><stop offset="1" stop-color="#B5E0CF"/>
    </linearGradient>
    <filter id="soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="9"/></filter>
  </defs>
  <!-- ground shadows -->
  <ellipse cx="212" cy="272" rx="92" ry="12" fill="#0E7A5C" opacity="0.18" filter="url(#soft)"/>
  <ellipse cx="78" cy="262" rx="44" ry="7" fill="#0E7A5C" opacity="0.14" filter="url(#soft)"/>
  <ellipse cx="352" cy="252" rx="40" ry="7" fill="#0E7A5C" opacity="0.14" filter="url(#soft)"/>
  <!-- database cylinder -->
  <g class="ms-float-c">
    <rect x="42" y="158" width="72" height="78" fill="url(#dbBody)"/>
    <ellipse cx="78" cy="236" rx="36" ry="11" fill="#A9D9C5"/>
    <rect x="42" y="158" width="72" height="78" fill="url(#dbBody)"/>
    <path d="M42 184 a36 11 0 0 0 72 0" fill="none" stroke="#8CCBB1" stroke-width="1.5"/>
    <path d="M42 210 a36 11 0 0 0 72 0" fill="none" stroke="#8CCBB1" stroke-width="1.5"/>
    <ellipse cx="78" cy="158" rx="36" ry="11" fill="#E9F7F1" stroke="#9FD5BF" stroke-width="1.5"/>
    <circle cx="98" cy="196" r="2.6" fill="#0E7A5C"/><circle cx="98" cy="222" r="2.6" fill="#34C08F"/>
  </g>
  <!-- 3D shield -->
  <g class="ms-float-a">
    <path d="M222 34 L292 60 V128 C292 182 260 216 222 232 C184 216 152 182 152 128 V60 Z" fill="url(#shieldSide)"
          transform="translate(10 10)"/>
    <path d="M212 30 L282 56 V124 C282 178 250 212 212 228 C174 212 142 178 142 124 V56 Z" fill="url(#shieldFront)"/>
    <path d="M212 30 L282 56 V92 C240 76 186 82 142 104 V56 Z" fill="url(#shine)"/>
    <path d="M212 46 L268 67 V124 C268 170 242 198 212 212 C182 198 156 170 156 124 V67 Z" fill="none"
          stroke="#FFFFFF" stroke-opacity="0.35" stroke-width="2"/>
    <path d="M182 126 L204 148 L246 104" fill="none" stroke="#FFFFFF" stroke-width="13" stroke-linecap="round"
          stroke-linejoin="round"/>
  </g>
  <!-- capsule -->
  <g class="ms-float-b">
    <g transform="rotate(-32 352 150)">
      <rect x="306" y="130" width="46" height="40" rx="20" fill="url(#capGreen)"/>
      <rect x="352" y="130" width="46" height="40" rx="20" fill="url(#capWhite)"/>
      <rect x="340" y="130" width="24" height="40" fill="url(#capWhite)"/>
      <rect x="330" y="130" width="22" height="40" fill="url(#capGreen)"/>
      <rect x="316" y="137" width="70" height="7" rx="3.5" fill="#FFFFFF" opacity="0.55"/>
      <line x1="352" y1="130" x2="352" y2="170" stroke="#0B6B50" stroke-opacity="0.25" stroke-width="1.5"/>
    </g>
  </g>
</svg>
"""


def login_scene():
    """The decorative 3D scene: shield, capsule, database and three tilted glass cards (all illustrative)."""
    major = ui.SEVERITY_STYLE["MAJOR"]
    return (
        '<div class="ms-3d" aria-hidden="true">' + "".join(line.strip() for line in SCENE_SVG.splitlines()) +
        '<div class="ms-glass ms-glass-1"><div class="ms-glass-k">Drug interaction</div>'
        '<div class="ms-glass-v">Warfarin + Aspirin</div>'
        f'<span class="ms-pill" style="background:{major["bg"]};color:{major["text"]};border-color:{major["border"]}">'
        f'<span class="dot" style="background:{major["color"]}"></span>Major · bleeding risk</span></div>'
        '<div class="ms-glass ms-glass-2"><div class="ms-glass-k">Model risk score</div>'
        '<div class="ms-glass-scale"><div></div><div></div><div></div><i></i></div>'
        '<div class="ms-glass-labels"><span>Low</span><span>Medium</span><span>High</span></div></div>'
        f'<div class="ms-glass ms-glass-3">{ui.icon("zap", 15)}<span>Checked by the trigger in under 1 ms</span></div>'
        '</div>')


def login_page():
    """Split-screen sign-in: a 3D product scene on the left, the form on a raised card on the right.
    The username and password are checked by PostgreSQL itself."""
    ui.apply_login_styles()
    hero_col, _, form_col = st.columns([1.15, 0.08, 0.9])

    with hero_col:
        chips = "".join(f'<span class="ms-hero-chip">{ui.icon(name, 14)}{text}</span>' for name, text in (
            ("zap", "Real-time trigger"), ("lock", "PostgreSQL roles"), ("globe", "openFDA knowledge")))
        st.markdown(
            f'<div class="ms-hero"><div class="ms-hero-brand"><div class="ms-hero-mark">'
            f'{ui.icon("shield", 18, "#FFFFFF")}</div>MediSentinel</div>'
            f'<h1>Medication safety,<br><em>enforced by the database.</em></h1>'
            f'<p class="lead">Real-time interaction, contraindication and allergy checks for every prescription, '
            f'with an audit trail for every override.</p>{login_scene()}'
            f'<div class="ms-hero-chips">{chips}</div></div>', unsafe_allow_html=True)

    with form_col:
        st.markdown('<div class="ms-signin-gap"></div>', unsafe_allow_html=True)
        with st.container(key="login_card"):
            st.markdown(f'<div class="ms-signin-badge">{ui.icon("lock", 14)}Secured by PostgreSQL roles</div>'
                        '<h2 class="ms-signin-title">Welcome back</h2>'
                        '<p class="ms-signin-sub">Sign in with the database login for your role.</p>',
                        unsafe_allow_html=True)
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
            st.Page(pages / "5_Analytics.py", title="Analytics", icon=":material/insights:"),
        ],
    })
    session.render_sidebar_status()

nav.run()
