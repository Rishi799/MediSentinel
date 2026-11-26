"""Patients: searchable records with a clinical profile panel, and the registration form (Task C3)."""

import datetime
from html import escape

import pandas as pd
import streamlit as st
from psycopg import errors as pg_errors

from app import session, ui, validation
from medisentinel import constants, db

conn = session.require_login()
can_register = session.can_write()

ui.page_header("Patients", "Each profile holds what the safety trigger checks: conditions, allergies and the "
                           "medicines the patient already takes.", eyebrow="Clinical")

tabs = st.tabs(["Records", "Register patient"] if can_register else ["Records"])


def prescribe_button(patient_id, where):
    """Open the Prescriptions page with this patient already selected."""
    if st.button("New prescription", key=f"prescribe_{where}_{patient_id}", icon=":material/add:",
                 width="stretch"):
        st.session_state["rx_patient_id"] = patient_id
        st.session_state.pop("patient_saved", None)
        st.switch_page("pages/2_Prescriptions.py")


def show_profile(patient_id):
    profile = db.patient_profile(conn, patient_id)
    if profile is None:
        st.info("Select a patient to see their profile.")
        return
    gender = constants.GENDERS.get(profile["gender"], profile["gender"] or "-")
    alerts = db.get_active_alerts(conn, patient_id)
    st.markdown(
        f'<div class="ms-profile-head"><div class="ms-avatar">{ui.initials(profile["full_name"])}</div>'
        f'<div><div class="ms-profile-name">{escape(profile["full_name"])}</div>'
        f'<div class="ms-profile-meta">Patient #{profile["patient_id"]} · born '
        f'{profile["date_of_birth"]:%d %b %Y}</div></div></div>'
        f'<div style="margin-top:0.7rem">{ui.risk_pill(alerts)}</div>'
        f'<div class="ms-facts">'
        f'<div class="ms-fact"><div class="ms-fact-k">Age</div><div class="ms-fact-v">'
        f'{ui.age_of(profile["date_of_birth"])} years</div></div>'
        f'<div class="ms-fact"><div class="ms-fact-k">Gender</div><div class="ms-fact-v">{escape(gender)}</div></div>'
        f'<div class="ms-fact"><div class="ms-fact-k">Kidney function</div><div class="ms-fact-v">'
        f'{escape((profile["renal_function"] or "-").capitalize())}</div></div>'
        f'<div class="ms-fact"><div class="ms-fact-k">Liver function</div><div class="ms-fact-v">'
        f'{escape((profile["hepatic_function"] or "-").capitalize())}</div></div></div>',
        unsafe_allow_html=True)
    if can_register:
        st.write("")
        prescribe_button(profile["patient_id"], "profile")

    ui.label("Conditions")
    ui.chips(profile["conditions"])
    ui.label("Allergies")
    ui.chips([f"{a['substance']} · {a['reaction']}" if a["reaction"] else a["substance"]
              for a in profile["allergies"]], warn=True, empty="No known allergies")
    ui.label("Active medicines")
    ui.chips([f"{m['name']} {m['dose'] or ''}".strip() for m in profile["active_medicines"]],
             empty="No active medicines")

    ui.label(f"Active alerts · {len(alerts)}")
    if alerts:
        ui.alert_list(alerts[:4], meta=lambda a: f"{a['created_at']:%d %b %Y, %H:%M}")
    else:
        st.markdown('<span class="ms-muted">None</span>', unsafe_allow_html=True)


# ---------------- records ----------------
with tabs[0]:
    patients = db.list_patients(conn)
    list_col, profile_col = st.columns([1.2, 1], gap="medium")
    with list_col:
        search = st.text_input("Search patients", placeholder="Search by name", label_visibility="collapsed",
                               icon=":material/search:")
        if search:
            patients = [p for p in patients if search.strip().lower() in p["full_name"].lower()]
        if not patients:
            ui.empty_state("users", "No patients found", "Try another name." if search else "Register the first patient.")
            selected_id = None
        else:
            df = pd.DataFrame(patients)
            df["age"] = df["date_of_birth"].map(ui.age_of)
            df["gender"] = df["gender"].map(constants.GENDERS).fillna("-")
            event = st.dataframe(
                df[["patient_id", "full_name", "age", "gender"]],
                hide_index=True, width="stretch", height=470, row_height=38,
                on_select="rerun", selection_mode="single-row", key="patient_table",
                column_config={
                    "patient_id": st.column_config.NumberColumn("ID", format="%d", width="small"),
                    "full_name": st.column_config.TextColumn("Name", width="medium"),
                    "age": st.column_config.NumberColumn("Age", format="%d", width=70),
                    "gender": st.column_config.TextColumn("Gender", width=90),
                })
            st.caption(f"{len(patients)} patients · select a row to open the profile")
            rows = event.selection.rows
            selected_id = int(df.iloc[rows[0]]["patient_id"]) if rows else int(df.iloc[0]["patient_id"])

    with profile_col:
        with st.container(border=True, key="card_1"):
            if selected_id is None:
                st.info("Select a patient to see their profile.")
            else:
                show_profile(selected_id)

# ---------------- registration (doctors and admins) ----------------
if can_register:
    with tabs[1]:
        known_conditions = db.list_conditions(conn)
        medications = db.list_medications(conn)
        med_options = {
            (f"{m['name']} ({m['generic_name']})" if m.get("generic_name") else m["name"]): m["med_id"]
            for m in medications
        }

        form_col, help_col = st.columns([1.7, 1], gap="medium")
        with help_col:
            with st.container(border=True, key="card_2"):
                ui.card_title("Why these fields matter")
                st.markdown(
                    "- **Conditions** are matched against contraindication rules.\n"
                    "- **Allergies** raise a major alert whenever that medicine is prescribed.\n"
                    "- **Kidney and liver function** are stored for dose-related checks.\n\n"
                    "Every field is validated here, and again by database constraints.")

        with form_col:
            with st.container(border=True, key="card_3"):
                ui.card_title("Allergies", "Choose these first so a reaction field appears for each medicine.")
                allergy_labels = st.multiselect(
                    "Medicines the patient is allergic to", options=list(med_options.keys()),
                    key="patient_allergy_meds_selection", placeholder="Search medicines")
                allergy_reactions: dict[int, str] = {}
                if allergy_labels:
                    cols = st.columns(min(len(allergy_labels), 2))
                    for idx, label in enumerate(allergy_labels):
                        med_id = med_options[label]
                        with cols[idx % len(cols)]:
                            allergy_reactions[med_id] = st.text_input(
                                f"Reaction to {label.split(' (')[0]}", placeholder="e.g. rash, hives",
                                key=f"reaction_med_{med_id}").strip()

            with st.form("patient_registration_form", border=True):
                ui.card_title("Patient details")
                col1, col2, col3 = st.columns([2, 1.2, 1])
                full_name = col1.text_input("Full name", placeholder="e.g. Ananya Sharma",
                                            help="2–100 characters: letters, spaces, dots and apostrophes.")
                dob = col2.date_input("Date of birth", value=datetime.date(1990, 1, 1),
                                      min_value=datetime.date.today() - datetime.timedelta(days=120 * 365 + 30),
                                      max_value=datetime.date.today(), format="DD/MM/YYYY")
                gender = col3.selectbox("Gender", options=list(constants.GENDERS.keys()),
                                        format_func=lambda k: constants.GENDERS[k])
                col4, col5 = st.columns(2)
                renal = col4.selectbox("Kidney function", options=constants.ORGAN_FUNCTION,
                                       format_func=str.capitalize)
                hepatic = col5.selectbox("Liver function", options=constants.ORGAN_FUNCTION,
                                         format_func=str.capitalize)
                conditions = st.multiselect("Diagnosed conditions", options=known_conditions,
                                            placeholder="Choose conditions")
                submitted = st.form_submit_button("Save patient", type="primary")

            if submitted:
                errors = validation.validate_name(full_name) + validation.validate_dob(dob)
                if errors:
                    for err in errors:
                        st.error(err, icon=":material/error:")
                else:
                    allergies = [(med_options[label], allergy_reactions.get(med_options[label], ""))
                                 for label in allergy_labels]
                    try:
                        patient_id = db.add_patient(conn, full_name=full_name.strip(), dob=dob, gender=gender,
                                                    renal=renal, hepatic=hepatic, conditions=tuple(conditions),
                                                    allergies=tuple(allergies))
                        st.session_state["patient_saved"] = (patient_id, full_name.strip())
                        st.toast(f"{full_name.strip()} registered", icon=":material/check_circle:")
                    except pg_errors.InsufficientPrivilege:
                        st.error("Your role is not allowed to do this")
                    except Exception as e:
                        st.error(f"Failed to save patient: {e}")

            saved = st.session_state.get("patient_saved")
            if saved:
                with st.container(border=True, key="card_4"):
                    ui.card_title(f"Patient #{saved[0]} saved", f"{saved[1]} is ready for prescribing.")
                    prescribe_button(saved[0], "saved")
else:
    st.caption("Read-only access: pharmacists can view patients but not register them.")
