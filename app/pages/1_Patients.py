"""Patients: searchable records with a clinical profile panel, and the registration form (Task C3)."""

import datetime

import pandas as pd
import streamlit as st
from psycopg import errors as pg_errors

from app import session, ui, validation
from medisentinel import constants, db

conn = session.require_login()
can_register = session.can_write()

ui.page_header("👥", "Patients", "Clinical profiles: the conditions, allergies and medicines the safety "
                                 "trigger checks.")

tab_names = ["Patient records", "Register patient"] if can_register else ["Patient records"]
tabs = st.tabs(tab_names)


def show_profile(patient_id):
    profile = db.patient_profile(conn, patient_id)
    if profile is None:
        st.info("Select a patient to see their profile.")
        return
    gender = constants.GENDERS.get(profile["gender"], profile["gender"] or "-")
    st.markdown(f"#### {profile['full_name']}")
    st.caption(f"Patient #{profile['patient_id']} · {gender} · {ui.age_of(profile['date_of_birth'])} years "
               f"(born {profile['date_of_birth']:%d %b %Y})")
    o1, o2 = st.columns(2)
    o1.metric("Kidney function", (profile["renal_function"] or "-").capitalize())
    o2.metric("Liver function", (profile["hepatic_function"] or "-").capitalize())

    st.markdown("**Conditions**")
    ui.chips(profile["conditions"])
    st.markdown("**Allergies**")
    ui.chips([f"{a['substance']} – {a['reaction']}" if a["reaction"] else a["substance"]
              for a in profile["allergies"]], warn=True, empty="No known allergies")
    st.markdown("**Active medicines**")
    ui.chips([f"{m['name']} {m['dose'] or ''}".strip() for m in profile["active_medicines"]],
             empty="No active medicines")

    alerts = db.get_active_alerts(conn, patient_id)
    st.markdown(f"**Active safety alerts ({len(alerts)})**")
    if not alerts:
        st.markdown('<span class="ms-muted">None</span>', unsafe_allow_html=True)
    for alert in alerts[:5]:
        ui.alert_card(alert, meta=f"{alert['created_at']:%d %b %Y, %H:%M}")


# ---------------- records ----------------
with tabs[0]:
    patients = db.list_patients(conn)
    search = st.text_input("Search patients", placeholder="Type a name…", label_visibility="collapsed",
                           icon=":material/search:")
    if search:
        patients = [p for p in patients if search.strip().lower() in p["full_name"].lower()]

    list_col, profile_col = st.columns([1.15, 1], gap="large")
    with list_col:
        if not patients:
            st.info("No patients match your search." if search else "No patients registered yet.")
            selected_id = None
        else:
            df = pd.DataFrame(patients)
            df["age"] = df["date_of_birth"].map(ui.age_of)
            df["gender"] = df["gender"].map(constants.GENDERS).fillna("-")
            event = st.dataframe(
                df[["patient_id", "full_name", "age", "gender"]],
                hide_index=True, width="stretch", height=430,
                on_select="rerun", selection_mode="single-row", key="patient_table",
                column_config={
                    "patient_id": st.column_config.NumberColumn("ID", format="%d", width="small"),
                    "full_name": "Name",
                    "age": st.column_config.NumberColumn("Age", format="%d", width="small"),
                    "gender": st.column_config.TextColumn("Gender", width="small"),
                })
            st.caption(f"{len(patients)} patient(s) · click a row to open the profile")
            rows = event.selection.rows
            selected_id = int(df.iloc[rows[0]]["patient_id"]) if rows else int(df.iloc[0]["patient_id"])

    with profile_col:
        with st.container(border=True):
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

        with st.container(border=True):
            st.markdown("##### Allergies")
            st.caption("Chosen first, so a reaction field can be shown for each medicine.")
            allergy_labels = st.multiselect(
                "Medicines the patient is allergic to (optional)",
                options=list(med_options.keys()), key="patient_allergy_meds_selection",
                placeholder="Search medicines…")
            allergy_reactions: dict[int, str] = {}
            if allergy_labels:
                cols = st.columns(min(len(allergy_labels), 3))
                for idx, label in enumerate(allergy_labels):
                    med_id = med_options[label]
                    with cols[idx % len(cols)]:
                        allergy_reactions[med_id] = st.text_input(
                            f"Reaction to {label.split(' (')[0]}", placeholder="e.g. rash, hives",
                            key=f"reaction_med_{med_id}").strip()

        with st.form("patient_registration_form", border=True):
            st.markdown("##### Patient details")
            col1, col2, col3 = st.columns([2, 1, 1])
            full_name = col1.text_input("Full name *", placeholder="e.g. Ananya Sharma",
                                        help="2–100 characters: letters, spaces, dots and apostrophes.")
            dob = col2.date_input("Date of birth *", value=datetime.date(1990, 1, 1),
                                  min_value=datetime.date.today() - datetime.timedelta(days=120 * 365 + 30),
                                  max_value=datetime.date.today(), format="DD/MM/YYYY")
            gender = col3.selectbox("Gender *", options=list(constants.GENDERS.keys()),
                                    format_func=lambda k: constants.GENDERS[k])

            col4, col5 = st.columns(2)
            renal = col4.selectbox("Kidney (renal) function *", options=constants.ORGAN_FUNCTION,
                                   format_func=str.capitalize)
            hepatic = col5.selectbox("Liver (hepatic) function *", options=constants.ORGAN_FUNCTION,
                                     format_func=str.capitalize)

            conditions = st.multiselect("Diagnosed conditions", options=known_conditions,
                                        placeholder="Choose conditions…",
                                        help="Medicines contraindicated for these conditions will raise alerts.")

            submitted = st.form_submit_button("Save patient", type="primary", icon=":material/save:")

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
                    st.success(f"Patient #{patient_id} saved", icon=":material/check_circle:")
                    st.toast(f"{full_name.strip()} registered", icon="✅")
                except pg_errors.InsufficientPrivilege:
                    st.error("Your role is not allowed to do this")
                except Exception as e:
                    st.error(f"Failed to save patient: {e}")
else:
    st.caption("🔒 Read-only access: pharmacists can view patients but not register them.")
