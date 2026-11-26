"""Prescriptions: build a prescription with a live safety preview, then save it through the trigger (Task C4)."""

import pandas as pd
import streamlit as st
from psycopg import errors as pg_errors

from app import session, ui, validation
from medisentinel import constants, db
from ml.score import alert_inputs, predict_risk

conn = session.require_login()

ui.page_header("Prescriptions", "Safety problems show up as you choose medicines. The database trigger makes the "
                                "final check when you save.", eyebrow="Clinical")

tabs = st.tabs(["New prescription", "History"] if session.can_write() else ["History"])
SEVERITY_RANK = {"MAJOR": 0, "MODERATE": 1, "MINOR": 2}


def show_history():
    recent = db.recent_prescriptions(conn, limit=50)
    if not recent:
        ui.empty_state("file", "No prescriptions yet", "Saved prescriptions appear here.")
        return
    for r in recent:
        r["rx"] = f"RX-{r['prescription_id']:05d}"
        r["date"] = f"{r['prescribed_date']:%d %b %Y}"
        r["alert_pill"] = (ui.neutral_pill(f"{r['alerts']} alert" + ("s" if r["alerts"] != 1 else ""),
                                           "#A94444", "#FCF2F2", "#F2D6D6") if r["alerts"]
                           else ui.neutral_pill("Clear", "#2F7A5E", "#EFF8F4", "#CDE9DD"))
        r["status_pill"] = ui.neutral_pill((r["status"] or "").capitalize())
    ui.table(recent, [("rx", "Prescription", "strong"), ("date", "Date", "num"), ("patient", "Patient", ""),
                      ("doctor", "Doctor", ""), ("medicines", "Medicines", ""), ("alert_pill", "Safety", "html"),
                      ("status_pill", "Status", "html")])
    st.caption("Latest 50 prescriptions.")


def show_context(profile):
    ui.label("Already taking · checked for interactions")
    ui.chips([m["name"] for m in profile["active_medicines"]], empty="No active medicines")
    ui.label("Conditions · checked for contraindications")
    ui.chips(profile["conditions"], empty="None recorded")
    ui.label("Allergies")
    ui.chips([a["substance"] for a in profile["allergies"]], warn=True, empty="No known allergies")


def empty_items():
    return pd.DataFrame({"Medicine": pd.Series([None], dtype="object"), "Dose": pd.Series([""], dtype="object"),
                         "Frequency": pd.Series([constants.FREQUENCIES[0]], dtype="object")})


if session.can_write():
    with tabs[0]:
        patients = db.list_patients(conn)
        doctors = db.list_doctors(conn)
        medications = db.list_medications(conn)

        if not patients or not doctors or not medications:
            st.warning("Patients, doctors and medicines must exist before a prescription can be written.")
        else:
            patient_options = {f"{p['full_name']} · #{p['patient_id']}": p["patient_id"] for p in patients}
            patient_labels = list(patient_options.keys())
            doctor_options = {f"{d['full_name']} · {d['specialty'] or 'General'}": d["doctor_id"] for d in doctors}
            med_options = {
                (f"{m['name']} ({m['generic_name']})" if m.get("generic_name") else m["name"]): m["med_id"]
                for m in medications
            }

            # a patient handed over from the Patients page is pre-selected
            handover = st.session_state.pop("rx_patient_id", None)
            if handover is not None:
                st.session_state["rx_patient"] = next(
                    (lbl for lbl, pid in patient_options.items() if pid == handover), patient_labels[0])
            st.session_state.setdefault("rx_editor_version", 0)

            form_col, side_col = st.columns([1.65, 1], gap="medium")

            with form_col:
                with st.container(border=True, key="card_1"):
                    ui.card_title("New prescription", "Three steps: choose the patient, add the medicines, then check "
                                                      "and save.")
                    ui.label("1 · Patient and prescriber")
                    p1, p2 = st.columns(2)
                    patient_label = p1.selectbox("Patient", options=patient_labels, key="rx_patient")
                    doctor_label = p2.selectbox("Prescribing doctor", options=list(doctor_options.keys()))
                    patient_id = patient_options[patient_label]

                    ui.label("2 · Medicines")
                    st.caption(f"One row per medicine. Dose is a number and a unit ({', '.join(constants.DOSE_UNITS)}).")
                    edited = st.data_editor(
                        empty_items(), key=f"rx_items_{st.session_state['rx_editor_version']}",
                        num_rows="dynamic", hide_index=True, width="stretch",
                        column_config={
                            "Medicine": st.column_config.SelectboxColumn(
                                "Medicine", options=list(med_options.keys()), required=True, width=270),
                            "Dose": st.column_config.TextColumn(
                                "Dose", help=f"A number and a unit, e.g. 500 mg ({', '.join(constants.DOSE_UNITS)})",
                                width=95),
                            "Frequency": st.column_config.SelectboxColumn(
                                "Frequency", options=list(constants.FREQUENCIES), required=True,
                                default=constants.FREQUENCIES[0], width=140),
                        })
                    rows = [r for r in edited.to_dict("records") if r.get("Medicine") or (r.get("Dose") or "").strip()]
                    items = [{"med_id": med_options.get(r.get("Medicine")), "dose": (r.get("Dose") or "").strip(),
                              "frequency": r.get("Frequency")} for r in rows]

                    ui.label("3 · Check and save")
                    save = st.button("Check and save prescription", type="primary", icon=":material/verified_user:",
                                     disabled=not rows, width="stretch")

            profile = db.patient_profile(conn, patient_id)
            preview = sorted(db.preview_conflicts(conn, patient_id, [i["med_id"] for i in items]),
                             key=lambda a: SEVERITY_RANK.get(a["severity"], 3))

            with side_col:
                with st.container(border=True, key="card_2"):
                    ui.card_title("Safety preview", "Updates as you choose medicines. Nothing is saved yet.")
                    if not any(i["med_id"] for i in items):
                        st.markdown('<span class="ms-muted">Choose a medicine to see interactions, contraindications '
                                    'and allergies for this patient.</span>', unsafe_allow_html=True)
                    elif not preview:
                        st.success("No known problems for this patient.", icon=":material/verified:")
                    else:
                        majors = sum(1 for a in preview if a["severity"] == "MAJOR")
                        st.warning(f"{len(preview)} problem(s) found, {majors} major.", icon=":material/warning:")
                        ui.alert_list(preview)
                with st.container(border=True, key="card_3"):
                    ui.card_title(profile["full_name"], f"Patient #{profile['patient_id']} · "
                                                        f"{ui.age_of(profile['date_of_birth'])} years")
                    show_context(profile)

            if save:
                errors = validation.validate_items(items)
                if errors:
                    with form_col:
                        for err in errors:
                            st.error(err, icon=":material/error:")
                else:
                    try:
                        prescription_id, alerts = db.create_prescription(
                            conn, patient_id=patient_id, doctor_id=doctor_options[doctor_label], items=items)
                        st.session_state["rx_result"] = (prescription_id, profile["full_name"], alerts)
                        st.session_state["rx_editor_version"] += 1  # start the next prescription with an empty table
                        st.rerun()
                    except pg_errors.UniqueViolation:
                        st.error("This medicine is already in the prescription")
                    except pg_errors.InsufficientPrivilege:
                        st.error("Your role is not allowed to do this")
                    except Exception as e:
                        st.error(f"Error creating prescription: {e}")

            result = st.session_state.pop("rx_result", None)
            if result:
                prescription_id, patient_name, alerts = result
                with form_col:
                    with st.container(border=True, key="card_4"):
                        ui.card_title(f"Saved · RX-{prescription_id:05d}", f"For {patient_name}. Checked by the "
                                                                           "database trigger.")
                        if not alerts:
                            st.success("No safety issues found.", icon=":material/verified:")
                        else:
                            majors = sum(1 for a in alerts if a["severity"] == "MAJOR")
                            st.warning(f"{len(alerts)} alert(s) recorded, {majors} major. Review before dispensing.",
                                       icon=":material/warning:")
                            inputs = {row["alert_id"]: row for row in alert_inputs(
                                conn, [alert["alert_id"] for alert in alerts])}
                            for alert in alerts:
                                row = inputs.get(alert["alert_id"])
                                score = row["risk_score"] if row else None
                                live = False
                                if score is None and row:
                                    try:
                                        score = round(predict_risk(row["features"]), 3)
                                        live = True
                                    except (FileNotFoundError, ValueError):
                                        pass
                                card, meter = st.columns([2.2, 1], vertical_alignment="center")
                                with card:
                                    ui.alert_list([alert])
                                with meter:
                                    ui.risk_meter(score)
                                    if live:
                                        st.caption("Live model estimate")
                            st.page_link("pages/3_Alerts.py", label="Review in Safety alerts",
                                         icon=":material/arrow_forward:")
                st.toast(f"RX-{prescription_id:05d} saved", icon=":material/check_circle:")

    with tabs[1]:
        show_history()
else:
    with tabs[0]:
        st.caption("Read-only access: pharmacists can view prescriptions but not write them.")
        show_history()
