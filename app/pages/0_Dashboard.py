"""Dashboard: headline numbers, active alerts by type and severity, latest activity."""

import altair as alt
import pandas as pd
import streamlit as st

from app import session, ui
from medisentinel import db

conn = session.require_login()
role = session.get_role()

ui.page_header("📊", "Dashboard", "Live overview of patients, prescriptions and medication-safety alerts.")

counts = db.dashboard_counts(conn)

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    ui.kpi("Patients", counts["patients"], "registered", tone="accent")
with c2:
    ui.kpi("Prescriptions", counts["prescriptions"], f"by {counts['doctors']} doctors")
with c3:
    ui.kpi("Active alerts", counts["active_alerts"], f"{counts['major_alerts']} major", tone="critical")
with c4:
    ui.kpi("Overridden", counts["overridden_alerts"], "with a recorded reason")
with c5:
    ui.kpi("Medicines", counts["medications"], "in the catalogue")

if role in ("doctor", "admin"):
    st.write("")
    a1, a2, a3, _ = st.columns([1, 1, 1, 2])
    a1.page_link("pages/1_Patients.py", label="Register a patient", icon=":material/person_add:")
    a2.page_link("pages/2_Prescriptions.py", label="New prescription", icon=":material/add_circle:")
    a3.page_link("pages/3_Alerts.py", label="Review alerts", icon=":material/notifications_active:")

st.write("")
left, right = st.columns([1.25, 1], gap="large")

with left:
    with st.container(border=True):
        st.markdown("##### Active alerts by type and severity")
        breakdown = db.alert_breakdown(conn)
        if not breakdown:
            st.success("No active alerts.", icon=":material/check_circle:")
        else:
            df = pd.DataFrame(breakdown)
            df["Type"] = df["alert_type"].map(ui.ALERT_TYPE_LABEL).fillna(df["alert_type"])
            df["Severity"] = df["severity"].str.capitalize()
            order = ["Major", "Moderate", "Minor"]
            chart = (
                alt.Chart(df)
                .mark_bar(cornerRadiusEnd=4, stroke="#FFFFFF", strokeWidth=2, height=26)
                .encode(
                    y=alt.Y("Type:N", title=None, sort="-x", axis=alt.Axis(labelFontSize=12, labelLimit=180)),
                    x=alt.X("sum(n):Q", title="Active alerts", axis=alt.Axis(tickMinStep=1, grid=True,
                                                                            gridColor="#E2E8F0")),
                    color=alt.Color("Severity:N", sort=order,
                                    scale=alt.Scale(domain=order, range=[ui.SEVERITY_STYLE[s.upper()]["color"]
                                                                         for s in order]),
                                    legend=alt.Legend(orient="top", title=None)),
                    order=alt.Order("severity_rank:Q"),
                    tooltip=[alt.Tooltip("Type:N"), alt.Tooltip("Severity:N"), alt.Tooltip("n:Q", title="Alerts")],
                )
                .transform_calculate(severity_rank="indexof(['Major','Moderate','Minor'], datum.Severity)")
                .properties(height=200)
                .configure_view(stroke=None)
            )
            st.altair_chart(chart, width="stretch")
            st.caption("Each alert was written by the database trigger when the medicine was prescribed.")

with right:
    with st.container(border=True):
        st.markdown("##### Latest active alerts")
        latest = db.get_active_alerts(conn)[:4]
        if not latest:
            st.success("Nothing needs attention.", icon=":material/check_circle:")
        for alert in latest:
            ui.alert_card(alert, meta=f"{alert['patient']} · {alert['created_at']:%d %b %Y, %H:%M}")
        if latest:
            st.page_link("pages/3_Alerts.py", label="See all alerts", icon=":material/arrow_forward:")

with st.container(border=True):
    st.markdown("##### Recent prescriptions")
    recent = db.recent_prescriptions(conn, limit=8)
    if not recent:
        st.info("No prescriptions yet.")
    else:
        st.dataframe(
            pd.DataFrame(recent)[["prescription_id", "prescribed_date", "patient", "doctor", "medicines",
                                  "alerts", "status"]],
            hide_index=True, width="stretch",
            column_config={
                "prescription_id": st.column_config.NumberColumn("Rx #", format="%d", width="small"),
                "prescribed_date": st.column_config.DateColumn("Date", format="DD MMM YYYY"),
                "patient": "Patient", "doctor": "Doctor",
                "medicines": st.column_config.TextColumn("Medicines", width="large"),
                "alerts": st.column_config.NumberColumn("Alerts raised", format="%d", width="small"),
                "status": "Status",
            })
