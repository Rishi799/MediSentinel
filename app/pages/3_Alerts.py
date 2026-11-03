"""Safety alerts: filter active alerts, override with a reason, and view the audit trail (Task C5)."""

import pandas as pd
import streamlit as st
from psycopg import errors as pg_errors

from app import session, ui
from medisentinel import db

conn = session.require_login()
is_doctor = session.get_role() == "doctor"

ui.page_header("🚨", "Safety alerts", "Raised only by the database trigger. Doctors may override one with a "
                                     "clinical reason, which is kept as an audit trail.")

flash = st.session_state.pop("alerts_flash", None)
if flash:
    st.success(flash, icon=":material/check_circle:")

tab_active, tab_audit = st.tabs(["Active alerts", "Override audit trail"])

with tab_active:
    patients = db.list_patients(conn)
    patient_options = {"All patients": None}
    patient_options.update({f"{p['full_name']} · #{p['patient_id']}": p["patient_id"] for p in patients})

    f1, f2, f3 = st.columns([2, 1.3, 1.5])
    patient_label = f1.selectbox("Patient", options=list(patient_options.keys()))
    severities = f2.multiselect("Severity", options=list(ui.SEVERITY_STYLE.keys()),
                                format_func=lambda s: ui.SEVERITY_STYLE[s]["label"], placeholder="All")
    types = f3.multiselect("Type", options=list(ui.ALERT_TYPE_LABEL.keys()),
                           format_func=ui.ALERT_TYPE_LABEL.get, placeholder="All")

    alerts = db.get_active_alerts(conn, patient_id=patient_options[patient_label])
    if severities:
        alerts = [a for a in alerts if a["severity"] in severities]
    if types:
        alerts = [a for a in alerts if a["alert_type"] in types]

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        ui.kpi("Showing", len(alerts), "active alerts")
    for col, sev in zip((k2, k3, k4), ("MAJOR", "MODERATE", "MINOR")):
        with col:
            ui.kpi(ui.SEVERITY_STYLE[sev]["label"], sum(1 for a in alerts if a["severity"] == sev),
                   tone="critical" if sev == "MAJOR" else "")

    st.write("")
    if not alerts:
        st.success("No active alerts match these filters.", icon=":material/verified:")
    else:
        df = pd.DataFrame(alerts)
        df["severity"] = df["severity"].map(
            lambda s: f"{ui.SEVERITY_STYLE[s]['icon']} {ui.SEVERITY_STYLE[s]['label']}" if s in ui.SEVERITY_STYLE
            else s)
        df["alert_type"] = df["alert_type"].map(ui.ALERT_TYPE_LABEL).fillna(df["alert_type"])
        st.dataframe(
            df[["alert_id", "severity", "alert_type", "patient", "medication", "message", "created_at"]],
            hide_index=True, width="stretch", height=min(420, 38 + 35 * len(df)),
            column_config={
                "alert_id": st.column_config.NumberColumn("Alert #", format="%d", width="small"),
                "severity": st.column_config.TextColumn("Severity", width="small"),
                "alert_type": "Type", "patient": "Patient", "medication": "Medicine",
                "message": st.column_config.TextColumn("Details", width="large"),
                "created_at": st.column_config.DatetimeColumn("Raised", format="DD MMM YYYY, HH:mm"),
            })

        if is_doctor:
            with st.container(border=True):
                st.markdown("##### Override an alert")
                st.caption("Only when the clinical benefit outweighs the risk. The reason is stored with the alert.")
                choices = {f"#{a['alert_id']} · {a['severity']} · {a['patient']} · {a['medication']}": a
                           for a in alerts}
                with st.form("alert_override_form", border=False, clear_on_submit=True):
                    chosen = st.selectbox("Alert *", options=list(choices.keys()))
                    reason = st.text_area("Clinical reason *", max_chars=500,
                                          placeholder="e.g. Short course under close INR monitoring; "
                                                      "benefit outweighs risk.")
                    submitted = st.form_submit_button("Override alert", type="primary", icon=":material/gavel:")
                if submitted:
                    alert = choices[chosen]
                    if not reason or not reason.strip():
                        st.error("A reason is required: an alert cannot be overridden without a clinical "
                                 "justification.", icon=":material/error:")
                    else:
                        try:
                            if db.override_alert(conn, alert["alert_id"], reason):
                                st.session_state["alerts_flash"] = (
                                    f"Alert #{alert['alert_id']} overridden. It is now in the audit trail.")
                                st.rerun()
                            else:
                                st.warning(f"Alert #{alert['alert_id']} was already overridden.")
                        except pg_errors.InsufficientPrivilege:
                            st.error("Your role is not allowed to do this")
        else:
            st.caption("🔒 Only doctors can override alerts.")

with tab_audit:
    trail = db.get_overridden_alerts(conn)
    if not trail:
        st.info("No alerts have been overridden yet.")
    else:
        df = pd.DataFrame(trail)
        df["alert_type"] = df["alert_type"].map(ui.ALERT_TYPE_LABEL).fillna(df["alert_type"])
        st.dataframe(
            df[["alert_id", "severity", "alert_type", "patient", "medication", "override_reason", "created_at"]],
            hide_index=True, width="stretch",
            column_config={
                "alert_id": st.column_config.NumberColumn("Alert #", format="%d", width="small"),
                "severity": "Severity", "alert_type": "Type", "patient": "Patient", "medication": "Medicine",
                "override_reason": st.column_config.TextColumn("Override reason", width="large"),
                "created_at": st.column_config.DatetimeColumn("Raised", format="DD MMM YYYY, HH:mm"),
            })
        st.caption("Alerts are never deleted: the database lets a doctor change only the overridden flag "
                   "and the reason (column-level GRANT in sql/roles.sql).")
