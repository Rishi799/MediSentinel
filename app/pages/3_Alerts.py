"""Active safety alerts and clinical overrides page (Task C5)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import psycopg
from psycopg import errors as pg_errors
import streamlit as st

from app import session
from medisentinel import db

st.set_page_config(page_title="Alerts | MediSentinel", page_icon="🚨", layout="wide")
session.render_sidebar_status()

# 1. Require login first
conn = session.require_login()

st.title("🚨 Medication Safety Alerts & Clinical Overrides")
st.caption("Active safety alerts automatically raised by the database safety trigger (drug-drug interactions, contraindications, and patient allergies).")

# 2. Patient filter
try:
    patients = db.list_patients(conn)
except Exception as e:
    patients = []
    st.error(f"Could not load patients: {e}")

filter_options = {"All Patients": None}
for p in patients:
    filter_options[f"{p['full_name']} (ID: #{p['patient_id']})"] = p["patient_id"]

selected_filter_label = st.selectbox(
    "Filter alerts by patient:",
    options=list(filter_options.keys()),
    index=0,
    help="Select a specific patient to filter active alerts, or select 'All Patients'.",
)
selected_patient_id = filter_options[selected_filter_label]

# 3. Fetch active alerts
try:
    alerts = db.get_active_alerts(conn, patient_id=selected_patient_id)
except Exception as e:
    alerts = []
    st.error(f"Error fetching active alerts: {e}")

st.markdown("### 📋 Active Safety Alerts")

if not alerts:
    st.success("No active safety alerts found.")
else:
    # Format alerts for dataframe display
    table_rows = []
    for a in alerts:
        table_rows.append({
            "Alert ID": a["alert_id"],
            "Patient": a["patient"],
            "Medication": a["medication"],
            "Type": a["alert_type"],
            "Severity": a["severity"],
            "Message": a["message"],
            "Created At": a["created_at"].strftime("%Y-%m-%d %H:%M:%S") if hasattr(a["created_at"], "strftime") else str(a["created_at"]),
        })

    st.dataframe(table_rows, use_container_width=True)
    st.caption(f"Showing {len(alerts)} active alert(s)")

# 4. Role-based override section: Doctors only
st.divider()
user_role = session.get_role()

if user_role == "doctor":
    st.markdown("### 🩺 Clinical Alert Override")
    st.caption("Physicians may override active safety alerts if the clinical benefit outweighs the detected risk. An audit trail reason is required by the database.")

    if not alerts:
        st.info("No active alerts available to override.")
    else:
        # Build dictionary for alert selection: "Alert #<id> - [<SEVERITY>] <Patient> - <Medication>: <Message>"
        alert_choice_map = {}
        for a in alerts:
            label = f"Alert #{a['alert_id']} · [{a['severity']} {a['alert_type']}] {a['patient']} — {a['medication']}: {a['message']}"
            alert_choice_map[label] = a["alert_id"]

        with st.form("alert_override_form", clear_on_submit=True):
            chosen_alert_label = st.selectbox(
                "Select Alert to Override *",
                options=list(alert_choice_map.keys()),
            )
            chosen_alert_id = alert_choice_map[chosen_alert_label]

            override_reason = st.text_area(
                "Clinical Override Reason / Justification *",
                placeholder="e.g. Patient previously tolerated combination under close monitoring; benefit outweighs risk.",
                help="Enter a clear clinical justification. An empty reason will be rejected.",
            )

            override_submitted = st.form_submit_button("🛡️ Override Alert", use_container_width=True)

            if override_submitted:
                clean_reason = override_reason.strip() if override_reason else ""
                if not clean_reason:
                    st.error("Override reason is required. An alert cannot be overridden without clinical justification.")
                else:
                    try:
                        success = db.override_alert(conn, chosen_alert_id, clean_reason)
                        if success:
                            st.success(f"Alert #{chosen_alert_id} overridden successfully!")
                            st.rerun()
                        else:
                            st.warning(f"Alert #{chosen_alert_id} could not be overridden (it may have already been overridden).")
                    except pg_errors.InsufficientPrivilege:
                        st.error("Your role is not allowed to do this")
                    except Exception as e:
                        st.error(f"Failed to override alert: {e}")

else:
    st.info("ℹ️ **Pharmacist / View-Only Mode**: Only doctors can override clinical safety alerts.")
