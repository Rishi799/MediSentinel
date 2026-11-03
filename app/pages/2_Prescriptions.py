"""Prescriptions: write a prescription and see the safety trigger's verdict at once (Task C4)."""

import pandas as pd
import streamlit as st
from psycopg import errors as pg_errors

from app import session, ui, validation
from medisentinel import constants, db

conn = session.require_login()

ui.page_header("💊", "Prescriptions", "Every medicine is checked by the database trigger the moment it is saved.")

tab_names = ["New prescription", "History"] if session.can_write() else ["History"]
tabs = st.tabs(tab_names)


def show_history():
    recent = db.recent_prescriptions(conn, limit=50)
    if not recent:
        st.info("No prescriptions yet.")
        return
    st.dataframe(
        pd.DataFrame(recent)[["prescription_id", "prescribed_date", "patient", "doctor", "medicines",
                              "alerts", "status"]],
        hide_index=True, width="stretch", height=480,
        column_config={
            "prescription_id": st.column_config.NumberColumn("Rx #", format="%d", width="small"),
            "prescribed_date": st.column_config.DateColumn("Date", format="DD MMM YYYY"),
            "patient": "Patient", "doctor": "Doctor",
            "medicines": st.column_config.TextColumn("Medicines", width="large"),
            "alerts": st.column_config.NumberColumn("Alerts raised", format="%d", width="small"),
            "status": "Status",
        })
    st.caption("Latest 50 prescriptions.")


def show_context(patient_id):
    """What the trigger will compare the new medicines against."""
    profile = db.patient_profile(conn, patient_id)
    st.markdown("##### Safety context")
    st.caption("The trigger checks each new medicine against these.")
    st.markdown("**Active medicines** · interactions")
    ui.chips([m["name"] for m in profile["active_medicines"]], empty="None")
    st.markdown("**Conditions** · contraindications")
    ui.chips(profile["conditions"], empty="None")
    st.markdown("**Allergies**")
    ui.chips([a["substance"] for a in profile["allergies"]], warn=True, empty="No known allergies")


if session.can_write():
    with tabs[0]:
        patients = db.list_patients(conn)
        doctors = db.list_doctors(conn)
        medications = db.list_medications(conn)

        if not patients or not doctors or not medications:
            st.warning("Patients, doctors and medicines must exist before a prescription can be written.")
        else:
            patient_options = {f"{p['full_name']} · #{p['patient_id']}": p["patient_id"] for p in patients}
            doctor_options = {f"{d['full_name']} ({d['specialty'] or 'General'})": d["doctor_id"]
                              for d in doctors}
            med_options = {
                (f"{m['name']} ({m['generic_name']})" if m.get("generic_name") else m["name"]): m["med_id"]
                for m in medications
            }

            form_col, context_col = st.columns([1.6, 1], gap="large")

            with context_col:
                with st.container(border=True):
                    patient_label = st.selectbox("Patient *", options=list(patient_options.keys()),
                                                 key="rx_patient")
                    patient_id = patient_options[patient_label]
                    show_context(patient_id)

            with form_col:
                with st.container(border=True):
                    top1, top2 = st.columns([2, 1])
                    doctor_label = top1.selectbox("Prescribing doctor *", options=list(doctor_options.keys()))
                    num_meds = top2.number_input("Number of medicines", min_value=1, max_value=6, value=1,
                                                 step=1)

                    with st.form("prescription_form", border=False):
                        h1, h2, h3 = st.columns([3, 1.4, 1.6])
                        h1.markdown("**Medicine**")
                        h2.markdown("**Dose**")
                        h3.markdown("**Frequency**")
                        items = []
                        for i in range(int(num_meds)):
                            c1, c2, c3 = st.columns([3, 1.4, 1.6])
                            label = c1.selectbox(f"Medicine {i + 1}", options=list(med_options.keys()),
                                                 index=None, placeholder="Search medicine…",
                                                 key=f"med_select_{i}", label_visibility="collapsed")
                            dose = c2.text_input(f"Dose {i + 1}", placeholder="e.g. 500 mg",
                                                 key=f"dose_input_{i}", label_visibility="collapsed",
                                                 help=f"A number and a unit: {', '.join(constants.DOSE_UNITS)}")
                            freq = c3.selectbox(f"Frequency {i + 1}", options=constants.FREQUENCIES,
                                                key=f"freq_select_{i}", label_visibility="collapsed")
                            items.append({"med_id": med_options.get(label), "dose": (dose or "").strip(),
                                          "frequency": freq})
                        submitted = st.form_submit_button("Check & save prescription", type="primary",
                                                          icon=":material/verified_user:")

            if submitted:
                errors = validation.validate_items(items)
                if errors:
                    with form_col:
                        for err in errors:
                            st.error(err, icon=":material/error:")
                else:
                    try:
                        prescription_id, alerts = db.create_prescription(
                            conn, patient_id=patient_id, doctor_id=doctor_options[doctor_label], items=items)
                        st.session_state["rx_result"] = (prescription_id, patient_label.split(" · ")[0], alerts)
                        st.rerun()  # refresh the safety context with the new medicines
                    except pg_errors.UniqueViolation:
                        st.error("This medicine is already in the prescription")
                    except pg_errors.InsufficientPrivilege:
                        st.error("Your role is not allowed to do this")
                    except Exception as e:
                        st.error(f"Error creating prescription: {e}")

            result = st.session_state.pop("rx_result", None)
            if result:
                prescription_id, patient_name, alerts = result
                with st.container(border=True):
                    st.markdown(f"##### Safety check result · Prescription #{prescription_id} for "
                                f"{patient_name}")
                    if not alerts:
                        st.success("Saved. No safety issues found.", icon=":material/verified:")
                    else:
                        majors = sum(1 for a in alerts if a["severity"] == "MAJOR")
                        st.warning(f"Saved with {len(alerts)} safety alert(s), {majors} major. Review them "
                                   "before dispensing.", icon=":material/warning:")
                        for alert in alerts:
                            ui.alert_card(alert)
                        st.page_link("pages/3_Alerts.py", label="Review or override on the Alerts page",
                                     icon=":material/arrow_forward:")

    with tabs[1]:
        show_history()
else:
    with tabs[0]:
        st.caption("🔒 Read-only access: pharmacists can view prescriptions but not write them.")
        show_history()
