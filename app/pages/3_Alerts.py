"""Adverse safety alerts page placeholder (Task C5)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

try:
    from app import session
except ImportError:
    import session


st.set_page_config(page_title="Alerts | MediSentinel", page_icon="🚨", layout="wide")
session.render_sidebar_status()
conn = session.require_login()

st.title("🚨 Adverse Medication Alerts & Overrides")
st.caption("Active safety alerts raised by the PostgreSQL database safety trigger.")

role = session.get_role()
if role == "doctor":
    st.info("🩺 Doctor role: view alerts and submit clinical overrides with justification.")
else:
    st.info("ℹ️ View-only access: alert overrides require doctor authorization.")
