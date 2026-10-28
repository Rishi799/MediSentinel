"""Patients management page placeholder (Task C3)."""

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


st.set_page_config(page_title="Patients | MediSentinel", page_icon="👤", layout="wide")
session.render_sidebar_status()
conn = session.require_login()

st.title("👤 Patient Registration & Records")
st.caption("Register patients with chronic conditions and allergies, backed by database validation.")

role = session.get_role()
if not session.can_write():
    st.info("ℹ️ Pharmacist role: read-only access.")
else:
    st.info("🩺 Doctor/Admin role: full patient registration privileges.")
