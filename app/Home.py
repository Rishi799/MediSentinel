"""MediSentinel Streamlit Application - Home & Authentication."""

import sys
from pathlib import Path

# Ensure repository root is in sys.path for Streamlit execution
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

try:
    from app import session
except ImportError:
    import session


st.set_page_config(
    page_title="MediSentinel | Safe Medication Surveillance",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom styling for a polished, modern healthcare interface
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    .role-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

session.init_session()
session.render_sidebar_status()

st.markdown('<div class="main-title">🏥 MediSentinel</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">An Intelligent Medication Safety & Adverse-Reaction Surveillance System</div>',
    unsafe_allow_html=True,
)

st.divider()

if not session.is_logged_in():
    col1, col2 = st.columns([1.2, 1.8], gap="large")

    with col1:
        st.subheader("Sign In")
        st.caption("Authenticate with your PostgreSQL credentials to access the system.")

        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", placeholder="e.g. ms_doctor, ms_pharmacist, ms_admin")
            password = st.text_input("Password", type="password", placeholder="Enter your role password")
            submit = st.form_submit_button("Sign In", use_container_width=True, type="primary")

            if submit:
                success, error_msg = session.login(username, password)
                if success:
                    st.success(f"Logged in as **{session.get_role()}**")
                    st.rerun()
                else:
                    st.error(error_msg)

    with col2:
        st.subheader("System Access Roles")
        st.markdown(
            """
            MediSentinel enforces **Role-Based Access Control (RBAC)** directly at the PostgreSQL database level:
            """
        )

        st.markdown(
            """
            * 🩺 **`ms_doctor`**:
              * Register patients and specify active medical conditions & allergies.
              * Create multi-drug prescriptions.
              * Review automatic trigger safety alerts and mark them as clinically overridden with reasons.
            * 💊 **`ms_pharmacist`**:
              * View-only audit mode for active prescriptions, patient histories, and safety alerts.
              * Database prevents modifying or saving clinical records (`InsufficientPrivilege`).
            * ⚙️ **`ms_admin`**:
              * Full system and database administrative authority.
              * Medication master maintenance and openFDA automated data ingestion.
            """
        )

else:
    role = session.get_role()
    username = session.get_username()

    st.success(f"### Logged in as {role}")
    st.write(f"Active session user: **`{username}`**")

    col_info, col_actions = st.columns([2, 1], gap="medium")

    with col_info:
        st.markdown("#### Authorized Operations")
        if role == "doctor":
            st.info(
                """
                **You have full clinical write privileges:**
                - Register new patients in **Patients** page.
                - Create prescriptions in **Prescriptions** page with live interaction & contraindication alerts.
                - Review and override flagged safety alerts in **Alerts** page.
                """
            )
        elif role == "pharmacist":
            st.warning(
                """
                **You have view-only audit privileges:**
                - Inspect patient records and medication details.
                - Review all triggered alerts and prescription statuses.
                - Data creation forms are disabled to maintain role segregation.
                """
            )
        elif role == "admin":
            st.info(
                """
                **You have administrative access:**
                - Access all clinical and audit data across the hospital.
                - Ingest and synchronize openFDA data into MongoDB.
                """
            )

    with col_actions:
        st.markdown("#### Session Actions")
        if st.button("🚪 Log Out", key="home_logout_btn", type="secondary", use_container_width=True):
            session.logout()
