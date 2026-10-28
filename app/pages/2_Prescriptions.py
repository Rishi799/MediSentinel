"""Prescriptions management page placeholder (Task C4)."""

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


st.set_page_config(page_title="Prescriptions | MediSentinel", page_icon="📝", layout="wide")
session.render_sidebar_status()
conn = session.require_login()

st.title("📝 Prescriptions & Medication Safety")
st.caption("Create multi-drug prescriptions with real-time safety trigger evaluation.")

role = session.get_role()
if not session.can_write():
    st.info("ℹ️ Pharmacist role: read-only access.")
else:
    st.info("🩺 Doctor/Admin role: prescription creation and safety checks.")
