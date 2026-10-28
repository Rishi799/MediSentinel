"""Prescription creation and safety verification page (Task C4)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import psycopg
from psycopg import errors as pg_errors
import streamlit as st

from app import session
from app import validation
from medisentinel import constants, db

st.set_page_config(page_title="Prescriptions | MediSentinel", page_icon="📝", layout="wide")
session.render_sidebar_status()

# 1. Require login first
conn = session.require_login()

st.title("📝 New Prescription & Safety Check")
st.caption("Prescribe medications with real-time database safety triggers detecting drug interactions, contraindications, and allergies.")

# 2. Check role authorization
if not session.can_write():
    st.info("ℹ️ **Read-Only Mode**: Pharmacists cannot create prescriptions. You can review and verify alerts on the **Alerts** page.")
else:
    # Load patients, doctors, and medications
    try:
        patients = db.list_patients(conn)
    except Exception as e:
        patients = []
        st.error(f"Could not load patients list: {e}")

    try:
        doctors = db.list_doctors(conn)
    except Exception as e:
        doctors = []
        st.error(f"Could not load doctors list: {e}")

    try:
        medications = db.list_medications(conn)
    except Exception as e:
        medications = []
        st.error(f"Could not load medications list: {e}")

    if not patients:
        st.warning("No registered patients found. Please add a patient first on the **Patients** page.")
    elif not doctors:
        st.warning("No doctors found in the database.")
    elif not medications:
        st.warning("No medications found in the database.")
    else:
        # Build lookup maps
        # Patients: "Full Name (DOB: YYYY-MM-DD)" -> patient_id
        patient_options = {
            f"{p['full_name']} (DOB: {p['date_of_birth']})": p["patient_id"]
            for p in patients
        }

        # Doctors: "Full Name (Specialty)" -> doctor_id
        doctor_options = {
            f"{d['full_name']} ({d['specialty'] or 'General'})": d["doctor_id"]
            for d in doctors
        }

        # Medications: "Name (Generic Name)" -> med_id
        med_options = {
            (f"{m['name']} ({m['generic_name']})" if m.get("generic_name") else m["name"]): m["med_id"]
            for m in medications
        }
        med_labels = list(med_options.keys())

        # Select Patient & Doctor
        col_p, col_d = st.columns(2)
        with col_p:
            selected_patient_label = st.selectbox(
                "Select Patient *",
                options=list(patient_options.keys()),
                help="Choose the patient receiving this prescription.",
            )
            selected_patient_id = patient_options[selected_patient_label]

        with col_d:
            selected_doctor_label = st.selectbox(
                "Prescribing Doctor *",
                options=list(doctor_options.keys()),
                help="Choose the physician issuing this prescription.",
            )
            selected_doctor_id = doctor_options[selected_doctor_label]

        st.markdown("---")
        st.markdown("### 💊 Prescribed Medications")

        num_meds = st.number_input(
            "How many medicines? (1-6)",
            min_value=1,
            max_value=6,
            value=1,
            step=1,
            help="Select the number of medication items to include in this prescription.",
        )

        with st.form("prescription_form", clear_on_submit=False):
            items_input = []
            for i in range(int(num_meds)):
                st.markdown(f"**Medicine #{i + 1}**")
                col_m, col_dose, col_freq = st.columns([3, 2, 2])

                with col_m:
                    chosen_med_label = st.selectbox(
                        f"Medication #{i + 1}",
                        options=med_labels,
                        key=f"med_select_{i}",
                        label_visibility="collapsed",
                    )
                    med_id = med_options[chosen_med_label]

                with col_dose:
                    dose = st.text_input(
                        f"Dose #{i + 1}",
                        placeholder="e.g. 500 mg, 10 ml",
                        help=f"Number followed by allowed unit ({', '.join(constants.DOSE_UNITS)})",
                        key=f"dose_input_{i}",
                        label_visibility="collapsed",
                    )

                with col_freq:
                    freq = st.selectbox(
                        f"Frequency #{i + 1}",
                        options=constants.FREQUENCIES,
                        key=f"freq_select_{i}",
                        label_visibility="collapsed",
                    )

                items_input.append({
                    "med_id": med_id,
                    "med_name": chosen_med_label,
                    "dose": dose.strip() if dose else "",
                    "frequency": freq,
                })

            submitted = st.form_submit_button("🩺 Verify & Create Prescription", use_container_width=True)

            if submitted:
                # 1. Validate items using pure validation function
                errors = validation.validate_items(items_input)

                if errors:
                    for err in errors:
                        st.error(err)
                else:
                    # 2. Prepare items payload for database
                    clean_items = [
                        {"med_id": item["med_id"], "dose": item["dose"], "frequency": item["frequency"]}
                        for item in items_input
                    ]

                    try:
                        prescription_id, alerts = db.create_prescription(
                            conn=conn,
                            patient_id=selected_patient_id,
                            doctor_id=selected_doctor_id,
                            items=clean_items,
                        )

                        st.success(f"✅ Prescription #{prescription_id} created successfully!")

                        # 3. Display safety trigger alerts
                        st.markdown("#### 🛡️ Clinical Safety Trigger Results")
                        if not alerts:
                            st.success("No safety issues found")
                        else:
                            for alert in alerts:
                                severity = (alert.get("severity") or "").upper()
                                med_name = alert.get("medication", "Medication")
                                alert_type = alert.get("alert_type", "SAFETY")
                                msg = alert.get("message", "Safety trigger alert.")
                                alert_text = f"**[{severity} - {alert_type}] {med_name}**: {msg}"

                                if severity == "MAJOR":
                                    st.error(alert_text)
                                elif severity == "MODERATE":
                                    st.warning(alert_text)
                                else:  # MINOR or other
                                    st.info(alert_text)

                    except pg_errors.UniqueViolation:
                        st.error("This medicine is already in the prescription")
                    except pg_errors.InsufficientPrivilege:
                        st.error("Your role is not allowed to do this")
                    except Exception as e:
                        st.error(f"Error creating prescription: {e}")
