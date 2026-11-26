"""Dashboard: headline numbers, 14-day activity, alerts by type, medicines raising alerts, latest activity."""

from datetime import date

import altair as alt
import pandas as pd
import streamlit as st

from app import session, ui
from medisentinel import db

conn = session.require_login()
role = session.get_role()

ui.page_header("Dashboard", f"{date.today():%A, %d %B %Y} · Live view of prescriptions and the safety alerts "
                            "the database raised for them.", eyebrow="Overview")

counts = db.dashboard_counts(conn)
activity = db.daily_activity(conn, days=30)
month_rx = sum(d["prescriptions"] for d in activity)
month_alerts = sum(d["alerts"] for d in activity)

high_risk = conn.execute("SELECT count(*) AS n FROM Alert_Log WHERE NOT overridden AND risk_score >= %s",
                         (0.66,)).fetchone()["n"]

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    ui.kpi("Patients", counts["patients"], "Registered profiles", "users", "brand")
with c2:
    ui.kpi("Prescriptions", counts["prescriptions"], f"Written by {counts['doctors']} doctors", "file")
with c3:
    ui.kpi("Active alerts", counts["active_alerts"], f"{counts['major_alerts']} major · awaiting review",
           "alert", "danger")
with c4:
    ui.kpi("High-risk alerts", high_risk, "Model risk score ≥ 66%", "activity", "danger")
with c5:
    ui.kpi("Overrides", counts["overridden_alerts"], "Each with a recorded reason", "history")

st.write("")
left, right = st.columns([1.35, 1], gap="medium")

with left:
    with st.container(border=True, key="card_1"):
        ui.card_title("Activity · last 30 days", f"{month_rx} prescriptions written and {month_alerts} alerts raised.")
        df = pd.DataFrame(activity)
        df["day"] = pd.to_datetime(df["day"])
        long = df.melt(id_vars="day", value_vars=["prescriptions", "alerts"], var_name="series", value_name="count")
        long["series"] = long["series"].map({"prescriptions": "Prescriptions", "alerts": "Alerts"})
        base = alt.Chart(long).encode(
            x=alt.X("day:T", title=None, axis=alt.Axis(format="%d %b", labelColor="#98A2B3", grid=False, ticks=False,
                                                      domain=False, tickCount=8, labelPadding=8)),
            y=alt.Y("count:Q", title=None, axis=alt.Axis(gridColor="#F2F4F7", labelColor="#98A2B3", domain=False,
                                                        ticks=False, tickMinStep=1, format="d", minExtent=34)),
            color=alt.Color("series:N", scale=alt.Scale(domain=["Prescriptions", "Alerts"],
                                                        range=[ui.BRAND, ui.SEVERITY_STYLE["MAJOR"]["color"]]),
                            legend=alt.Legend(orient="top", title=None, labelColor="#475467", symbolType="circle",
                                              symbolSize=70, symbolOpacity=1)),
        )
        area = base.mark_area(opacity=0.08, interpolate="monotone")
        line = base.mark_line(strokeWidth=2.2, interpolate="monotone")
        points = base.mark_circle(size=42).encode(
            tooltip=[alt.Tooltip("day:T", title="Day", format="%d %b"), alt.Tooltip("series:N", title="Series"),
                     alt.Tooltip("count:Q", title="Count")])
        chart = (
            (area + line + points).properties(height=235)
            .configure_view(stroke=None)
            .configure(font="Inter", background="#FFFFFF", padding={"left": 8, "right": 12, "top": 4, "bottom": 4},
                       autosize=alt.AutoSizeParams(type="fit", contains="padding"))
        )
        st.altair_chart(chart, width="stretch", theme=None)

with right:
    with st.container(border=True, key="card_2"):
        ui.card_title("Needs review", "Newest active alerts")
        latest = db.get_active_alerts(conn)[:4]
        if not latest:
            ui.empty_state("check", "All clear", "No active alerts need attention.")
        else:
            ui.alert_list(latest, meta=lambda a: f"{a['patient']} · {a['created_at']:%d %b, %H:%M}")
            st.page_link("pages/3_Alerts.py", label="Open safety alerts", icon=":material/arrow_forward:")

st.write("")
left2, right2 = st.columns([1.35, 1], gap="medium")

with left2:
    with st.container(border=True, key="card_3"):
        ui.card_title("Active alerts by type", "Stacked by severity. Every alert was written by the database "
                                               "trigger.")
        breakdown = db.alert_breakdown(conn)
        if not breakdown:
            ui.empty_state("shield", "No active alerts", "Alerts appear here as prescriptions are checked.")
        else:
            bdf = pd.DataFrame(breakdown)
            bdf["Type"] = bdf["alert_type"].map(ui.ALERT_TYPE_LABEL).fillna(bdf["alert_type"])
            bdf["Severity"] = bdf["severity"].str.capitalize()
            order = ["Major", "Moderate", "Minor"]
            chart = (
                alt.Chart(bdf)
                .transform_calculate(rank="indexof(['Major','Moderate','Minor'], datum.Severity)")
                .mark_bar(cornerRadiusEnd=4, stroke="#FFFFFF", strokeWidth=2, height=28)
                .encode(
                    y=alt.Y("Type:N", title=None, sort="-x",
                            axis=alt.Axis(labelFontSize=12, labelColor="#344054", labelLimit=180, ticks=False,
                                          domain=False, labelPadding=8, minExtent=130)),
                    x=alt.X("sum(n):Q", title=None,
                            axis=alt.Axis(tickMinStep=1, gridColor="#F2F4F7", labelColor="#98A2B3", domain=False,
                                          ticks=False)),
                    color=alt.Color("Severity:N", sort=order,
                                    scale=alt.Scale(domain=order,
                                                    range=[ui.SEVERITY_STYLE[s.upper()]["color"] for s in order]),
                                    legend=alt.Legend(orient="top", title=None, labelColor="#475467",
                                                      symbolType="circle", symbolSize=70)),
                    order=alt.Order("rank:Q"),
                    tooltip=[alt.Tooltip("Type:N"), alt.Tooltip("Severity:N"), alt.Tooltip("n:Q", title="Alerts")],
                )
                .properties(height=190)
                .configure_view(stroke=None)
                .configure(font="Inter", background="#FFFFFF", padding={"left": 16, "right": 12, "top": 4, "bottom": 4},
                           autosize=alt.AutoSizeParams(type="fit", contains="padding"))
            )
            st.altair_chart(chart, width="stretch", theme=None)

with right2:
    with st.container(border=True, key="card_4"):
        ui.card_title("Medicines raising alerts", "Active alerts per medicine")
        top = db.top_alert_medicines(conn, limit=6)
        if not top:
            ui.empty_state("pill", "Nothing flagged", "No medicine has an active alert.")
        else:
            ui.bar_list([(t["medication"], t["alerts"], f"{t['major']} major") for t in top])

with st.container(border=True, key="card_5"):
    head, action = st.columns([4, 1])
    with head:
        ui.card_title("Recent prescriptions", "Latest prescriptions and how many alerts the trigger raised.")
    if role in ("doctor", "admin"):
        action.page_link("pages/2_Prescriptions.py", label="New prescription", icon=":material/add:")
    recent = db.recent_prescriptions(conn, limit=7)
    if not recent:
        ui.empty_state("file", "No prescriptions yet", "Write the first one from the Prescriptions page.")
    else:
        for r in recent:
            r["rx"] = f"RX-{r['prescription_id']:05d}"
            r["date"] = f"{r['prescribed_date']:%d %b %Y}"
            r["alert_pill"] = (ui.neutral_pill(f"{r['alerts']} alert" + ("s" if r["alerts"] != 1 else ""),
                                               "#B42318", "#FEF3F2", "#FECDCA") if r["alerts"]
                               else ui.neutral_pill("Clear", "#067647", "#ECFDF3", "#ABEFC6"))
        ui.table(recent, [("rx", "Prescription", "strong"), ("date", "Date", "num"), ("patient", "Patient", ""),
                          ("doctor", "Doctor", ""), ("medicines", "Medicines", ""),
                          ("alert_pill", "Safety", "html")])
