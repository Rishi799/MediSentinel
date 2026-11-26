"""Safety alerts: filter active alerts, override with a reason, and view the audit trail (Task C5)."""

from html import escape

import pandas as pd
import streamlit as st
from psycopg import errors as pg_errors

from app import session, ui
from app.explain import explain_alert
from ml.score import alert_inputs
from medisentinel import db

conn = session.require_login()
is_doctor = session.get_role() == "doctor"

ui.page_header("Safety alerts", "Raised only by the database trigger. A doctor may override an alert with a "
                                "clinical reason, which is kept permanently.", eyebrow="Clinical")

flash = st.session_state.pop("alerts_flash", None)
if flash:
    st.success(flash, icon=":material/check_circle:")

tab_active, tab_audit = st.tabs(["Active", "Override audit trail"])

with tab_active:
    patients = db.list_patients(conn)
    patient_options = {"All patients": None}
    patient_options.update({f"{p['full_name']} · #{p['patient_id']}": p["patient_id"] for p in patients})

    f1, f2, f3 = st.columns([2, 1.3, 1.5])
    patient_label = f1.selectbox("Patient", options=list(patient_options.keys()))
    severities = f2.multiselect("Severity", options=list(ui.SEVERITY_STYLE.keys()),
                                format_func=lambda s: ui.SEVERITY_STYLE[s]["label"], placeholder="All severities")
    types = f3.multiselect("Type", options=list(ui.ALERT_TYPE_LABEL.keys()),
                           format_func=ui.ALERT_TYPE_LABEL.get, placeholder="All types")

    alerts = db.get_active_alerts(conn, patient_id=patient_options[patient_label])
    if severities:
        alerts = [a for a in alerts if a["severity"] in severities]
    if types:
        alerts = [a for a in alerts if a["alert_type"] in types]

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        ui.kpi("Matching alerts", len(alerts), "Active, not overridden", "alert")
    notes = {"MAJOR": "Avoid or change therapy", "MODERATE": "Monitor closely", "MINOR": "For information"}
    for col, sev in zip((k2, k3, k4), ("MAJOR", "MODERATE", "MINOR")):
        with col:
            ui.kpi(ui.SEVERITY_STYLE[sev]["label"], sum(1 for a in alerts if a["severity"] == sev), notes[sev])

    st.write("")
    if not alerts:
        ui.empty_state("check", "All clear", "No active alerts match these filters.")
    else:
        list_col, detail_col = st.columns([2.1, 1], gap="medium")
        with list_col:
            df = pd.DataFrame(alerts)
            df["severity_label"] = df["severity"].map(lambda s: "● " + ui.SEVERITY_STYLE.get(s, {}).get("label", s))
            df["type_label"] = df["alert_type"].map(ui.ALERT_TYPE_LABEL).fillna(df["alert_type"])
            event = st.dataframe(
                df[["alert_id", "severity_label", "patient", "medication", "type_label", "created_at"]],
                hide_index=True, width="stretch", height=min(460, 40 + 36 * len(df)), row_height=36,
                on_select="rerun", selection_mode="single-row", key="alert_table",
                column_config={
                    "alert_id": st.column_config.NumberColumn("Alert", format="#%d", width=70),
                    "severity_label": st.column_config.TextColumn("Severity", width=95),
                    "patient": "Patient", "medication": "Medicine", "type_label": "Type",
                    "created_at": st.column_config.DatetimeColumn("Raised", format="DD MMM, HH:mm", width=105),
                })
            st.caption(f"{len(alerts)} alerts · select a row to review it")
            picked = event.selection.rows
            alert = alerts[picked[0]] if picked else alerts[0]

        with detail_col:
            with st.container(border=True, key="card_1"):
                ui.card_title(f"Alert #{alert['alert_id']}", f"{alert['patient']} · raised "
                                                             f"{alert['created_at']:%d %b %Y, %H:%M}")
                ui.alert_list([alert])
                detail = explain_alert(conn, alert["alert_id"])
                if detail:
                    ui.label("Model risk score")
                    ui.risk_meter(detail["score"], explain=True)
                    inputs = alert_inputs(conn, [alert["alert_id"]])
                    if inputs:
                        ui.label("What the model looked at")
                        ui.risk_factors(inputs[0]["features"])
                    ui.label("Why this alert")
                    st.caption(detail["status"])
                    if detail.get("sentence"):
                        st.markdown(f'<div class="ms-quote">{escape(detail["sentence"])}</div>',
                                    unsafe_allow_html=True)
                    elif detail.get("source_id"):
                        st.caption("Matching sentence unavailable.")
                    if detail.get("brand"):
                        st.caption(f"Label: {detail['brand']}")
                    if detail.get("source_id"):
                        st.link_button(f"Source: openFDA label {detail['source_id']}", detail["url"],
                                       icon=":material/open_in_new:")
                if is_doctor:
                    ui.label("Override")
                    with st.form(f"override_{alert['alert_id']}", border=False, clear_on_submit=True):
                        reason = st.text_area("Clinical reason", max_chars=500, label_visibility="collapsed",
                                              placeholder="Clinical reason, e.g. short course under close INR "
                                                          "monitoring; benefit outweighs risk.")
                        submitted = st.form_submit_button("Override with this reason", type="primary",
                                                          width="stretch")
                    if submitted:
                        if not reason or not reason.strip():
                            st.error("A reason is required: an alert cannot be overridden without a clinical "
                                     "justification.", icon=":material/error:")
                        else:
                            try:
                                if db.override_alert(conn, alert["alert_id"], reason):
                                    st.session_state["alerts_flash"] = (
                                        f"Alert #{alert['alert_id']} overridden and added to the audit trail.")
                                    st.rerun()
                                else:
                                    st.warning(f"Alert #{alert['alert_id']} was already overridden.")
                            except pg_errors.InsufficientPrivilege:
                                st.error("Your role is not allowed to do this")
                    st.caption("The reason is stored permanently with the alert.")
                else:
                    st.caption("Only doctors can override alerts.")

with tab_audit:
    trail = db.get_overridden_alerts(conn)
    if not trail:
        ui.empty_state("history", "No overrides yet", "Overridden alerts and their reasons appear here.")
    else:
        rows = [{"id": f"#{a['alert_id']}", "sev": ui.severity_pill(a["severity"]),
                 "type": ui.ALERT_TYPE_LABEL.get(a["alert_type"], a["alert_type"]), "patient": a["patient"],
                 "medication": a["medication"], "reason": a["override_reason"],
                 "raised": f"{a['created_at']:%d %b, %H:%M}"} for a in trail]
        ui.table(rows, [("id", "Alert", "num"), ("sev", "Severity", "html"), ("type", "Type", ""),
                        ("patient", "Patient", "strong"), ("medication", "Medicine", ""),
                        ("reason", "Override reason", ""), ("raised", "Raised", "num")])
        st.caption("Alerts are never deleted. A doctor can change only the overridden flag and the reason "
                   "(column-level GRANT in sql/roles.sql).")
