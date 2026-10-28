"""Patient registration and records viewing page (Task C3)."""

import datetime
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

st.set_page_config(page_title="Patients | MediSentinel", page_icon="👤", layout="wide")
session.render_sidebar_status()

# 1. Require login first
conn = session.require_login()

st.title("👤 Patient Management")
st.caption("Register patients with clinical profiles, chronic conditions, and allergy history.")

# 2. Check user role permissions
can_register = session.can_write()

if not can_register:
    st.info("ℹ️ **Read-Only Mode**: Pharmacists cannot register new patients. You can view existing patient records below.")
else:
    st.markdown("### 📝 Register New Patient")

    # Fetch lookup data from database
    try:
        known_conditions = db.list_conditions(conn)
    except Exception as e:
        known_conditions = []
        st.warning(f"Could not load conditions list: {e}")

    try:
        medications = db.list_medications(conn)
    except Exception as e:
        medications = []
        st.warning(f"Could not load medications list: {e}")

    # Build medicine lookup helpers
    # Display name format: "Name (Generic Name)"
    med_display_options = {}
    for med in medications:
        label = f"{med['name']} ({med['generic_name']})" if med.get("generic_name") else med["name"]
        med_display_options[label] = med["med_id"]

    # Allergy selection outside the form so reaction inputs can dynamically adapt
    st.markdown("##### Allergies & Adverse Reactions")
    selected_med_labels = st.multiselect(
        "Select medicines the patient is allergic to (optional):",
        options=list(med_display_options.keys()),
        help="Select any medications that cause adverse or allergic reactions for this patient.",
        key="patient_allergy_meds_selection",
    )

    # Dictionary to collect reaction text for each selected allergy
    allergy_reactions: dict[int, str] = {}
    if selected_med_labels:
        st.caption("Specify the observed reaction for each selected medication:")
        cols = st.columns(min(len(selected_med_labels), 2))
        for idx, med_label in enumerate(selected_med_labels):
            med_id = med_display_options[med_label]
            col = cols[idx % len(cols)]
            with col:
                reaction = st.text_input(
                    f"Reaction for {med_label}:",
                    placeholder="e.g. rash, hives, anaphylaxis",
                    key=f"reaction_med_{med_id}",
                )
                allergy_reactions[med_id] = reaction.strip()

    # Main Registration Form
    with st.form("patient_registration_form", clear_on_submit=False):
        st.markdown("##### Basic Information")
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input(
                "Full Name *",
                placeholder="e.g. Jane Doe",
                help="2 to 100 characters. Letters, spaces, dots, and apostrophes allowed.",
            )
        with col2:
            dob = st.date_input(
                "Date of Birth *",
                value=datetime.date(1990, 1, 1),
                min_value=datetime.date.today() - datetime.timedelta(days=120 * 365 + 30),
                max_value=datetime.date.today(),
                help="Patient date of birth (must not be in future, max age 120).",
            )

        col3, col4, col5 = st.columns(3)
        with col3:
            gender_keys = list(constants.GENDERS.keys())
            gender = st.selectbox(
                "Gender *",
                options=gender_keys,
                format_func=lambda k: f"{constants.GENDERS[k]} ({k})",
            )
        with col4:
            renal_func = st.selectbox(
                "Kidney (Renal) Function *",
                options=constants.ORGAN_FUNCTION,
                format_func=lambda s: s.capitalize(),
                index=0,
            )
        with col5:
            hepatic_func = st.selectbox(
                "Liver (Hepatic) Function *",
                options=constants.ORGAN_FUNCTION,
                format_func=lambda s: s.capitalize(),
                index=0,
            )

        st.markdown("##### Chronic Conditions")
        selected_conditions = st.multiselect(
            "Pre-existing / Diagnosed Conditions",
            options=known_conditions,
            help="Select all diagnosed medical conditions for safety checking.",
        )

        submitted = st.form_submit_button("💾 Save Patient", use_container_width=True)

        if submitted:
            # 1. Run all validations and gather errors
            errors = []
            errors.extend(validation.validate_name(full_name))
            errors.extend(validation.validate_dob(dob))

            # 2. If there are validation errors, display ALL of them and do not save
            if errors:
                for err in errors:
                    st.error(err)
            else:
                # Prepare allergies list as (med_id, reaction) tuples
                allergies_list = [
                    (med_id, allergy_reactions.get(med_id, ""))
                    for med_label in selected_med_labels
                    if (med_id := med_display_options.get(med_label)) is not None
                ]

                try:
                    patient_id = db.add_patient(
                        conn=conn,
                        full_name=full_name.strip(),
                        dob=dob,
                        gender=gender,
                        renal=renal_func,
                        hepatic=hepatic_func,
                        conditions=tuple(selected_conditions),
                        allergies=tuple(allergies_list),
                    )
                    st.success(f"Patient #{patient_id} saved")
                except pg_errors.InsufficientPrivilege:
                    st.error("Your role is not allowed to do this")
                except Exception as e:
                    st.error(f"Failed to save patient: {e}")

st.divider()

# 3. Below the form: display table of existing patients
st.markdown("### 📋 Existing Patients")
try:
    patients = db.list_patients(conn)
    if patients:
        # Format records for display
        display_data = []
        for p in patients:
            display_data.append({
                "ID": p["patient_id"],
                "Full Name": p["full_name"],
                "Date of Birth": str(p["date_of_birth"]),
                "Gender": constants.GENDERS.get(p["gender"], p["gender"]),
            })
        st.dataframe(display_data, use_container_width=True)
        st.caption(f"Total registered patients: {len(patients)}")
    else:
        st.info("No patients found in the database.")
except pg_errors.InsufficientPrivilege:
    st.error("Your role is not allowed to view patients.")
except Exception as e:
    st.error(f"Error loading patients table: {e}")
