"""Read-only monitoring for extraction, risk scores, signals and overrides."""
import altair as alt
import pandas as pd
import streamlit as st

from app import analytics_queries as queries
from app import session, ui

conn = session.require_login()
ui.page_header("Analytics", "Track FDA-derived rules, model scores, adverse-event signals and overrides.",
               eyebrow="Surveillance")

rule_rows = queries.rule_totals(conn)
totals = queries.alert_totals(conn)
override_rate = totals["overridden"] / totals["total"] if totals["total"] else 0
with st.container(border=True, key="card_1"):
    interaction, contra, signals, override = st.columns(4)
    for col, row in zip((interaction, contra), rule_rows):
        with col:
            ui.kpi(f"{row['kind']} rules", row["total"],
                   f"{row['total'] - row['learned']:,} curated · {row['learned']:,} FDA-derived")
    with signals:
        ui.kpi("Adverse signals", totals["signals"], "Medicine–reaction pairs")
    with override:
        ui.kpi("Override rate", f"{override_rate:.1%}",
               f"{totals['overridden']:,} of {totals['total']:,} alerts")

severity_order = list(ui.SEVERITY_STYLE) + ["Unknown"]
severity_color = alt.Color(
    "severity:N", title="Severity",
    scale=alt.Scale(domain=severity_order,
                    range=[style["color"] for style in ui.SEVERITY_STYLE.values()] + ["#64748B"]),
    legend=alt.Legend(orient="top"),
)
axis = alt.Axis(minExtent=41)
chart_font = "Inter, system-ui, sans-serif"


def chart_card(key, title, caption, rows, make_chart, empty):
    with st.container(border=True, key=key):
        st.markdown(f"##### {title}")
        st.caption(caption)
        frame = pd.DataFrame(rows)
        if rows:
            chart = (make_chart(frame).properties(height=228, background="#FFFFFF")
                     .configure(font=chart_font)
                     .configure_axis(labelFont=chart_font, titleFont=chart_font, gridColor="#E2E8F0")
                     .configure_legend(labelFont=chart_font, titleFont=chart_font)
                     .configure_view(stroke=None))
            st.altair_chart(chart, theme=None, width="stretch", alt=title)
        else:
            st.info(empty)
        with st.expander("Show data"):
            st.dataframe(frame, hide_index=True, width="stretch", alt=f"{title} data")


def learned_chart(data):
    upper = max(1, int(data.groupby("kind")["rules"].sum().max()))
    return alt.Chart(data).mark_bar().encode(
        x=alt.X("kind:N", title="Rule type", axis=alt.Axis(labelAngle=0, minExtent=38)),
        y=alt.Y("sum(rules):Q", title="FDA-derived rules", scale=alt.Scale(domain=[0, upper]),
                axis=alt.Axis(format="d", tickMinStep=1, minExtent=41)),
        color=severity_color,
        tooltip=["kind:N", "severity:N", alt.Tooltip("sum(rules):Q", title="Rules")],
    )


def risk_chart(data):
    data = data.astype({"lower": float, "upper": float})
    return alt.Chart(data).mark_bar().encode(
        x=alt.X("lower:Q", bin=alt.Bin(binned=True, step=0.1), title="Model score",
                scale=alt.Scale(domain=[0, 1]),
                axis=alt.Axis(values=[i / 10 for i in range(11)], format=".0%", minExtent=38,
                              labelOverlap="greedy")),
        x2=alt.X2("upper:Q"),
        y=alt.Y("alerts:Q", stack="zero", title="Alerts", axis=alt.Axis(tickMinStep=1, minExtent=41)),
        color=severity_color,
        tooltip=[alt.Tooltip("lower:Q", title="From", format=".0%"),
                 alt.Tooltip("upper:Q", title="To", format=".0%"), "severity:N", "alerts:Q"],
    )


def signal_chart(data):
    return alt.Chart(data).mark_circle(size=86, opacity=0.85).encode(
        x=alt.X("reports:Q", title="Report count", axis=axis),
        y=alt.Y("prr:Q", title="Proportional reporting ratio", axis=axis),
        color=alt.Color("band:N", title="PRR",
                        scale=alt.Scale(domain=["Above 2", "2 or below"], range=["#0E7A5C", "#64748B"]),
                        legend=alt.Legend(orient="top")),
        tooltip=["medicine:N", "reaction:N", "reports:Q", alt.Tooltip("prr:Q", format=".2f")],
    )


def department_chart(data):
    return alt.Chart(data).mark_bar().encode(
        x=alt.X("sum(alerts):Q", title="Alerts", axis=alt.Axis(tickMinStep=1, minExtent=38)),
        y=alt.Y("department:N", sort="-x", title="Specialty",
                axis=alt.Axis(labelLimit=170, minExtent=94)),
        color=severity_color,
        tooltip=["department:N", "severity:N", alt.Tooltip("sum(alerts):Q", title="Alerts")],
    )


left, right = st.columns(2)
with left:
    learned_caption = ("Rules with a source label, grouped by severity and rule type."
                       if any(row["learned"] for row in rule_rows)
                       else "No FDA-derived rules have been loaded into PostgreSQL.")
    chart_card("card_2", "Rules learned from FDA labels", learned_caption,
               queries.learned_by_severity(conn), learned_chart, "No rule counts are available.")
with right:
    chart_card("card_3", "Risk distribution",
               f"{totals['scored']:,} scored alerts, grouped in ten-point bands by severity.",
               queries.risk_distribution(conn), risk_chart, "No alerts have been scored.")
left, right = st.columns(2)
with left:
    chart_card("card_4", "Signal map",
               "Each point is a medicine–reaction pair. PRR values above 2 are highlighted.",
               queries.signal_map(conn), signal_chart, "No signals with PRR and report counts are available.")
with right:
    chart_card("card_5", "Alerts by department",
               "Alert counts by the prescribing doctor's specialty and alert severity.",
               queries.alerts_by_department(conn), department_chart, "No alerts are available.")

with st.container(border=True, key="card_6"):
    st.markdown("##### Override audit")
    st.caption("Up to 20 overridden alerts, ordered by descending alert ID, with the recorded reason.")
    overrides = queries.recent_overrides(conn)
    if overrides:
        frame = pd.DataFrame(overrides)
        frame = frame[["alert_id", "patient", "medication", "severity", "override_reason", "created_at"]]
        st.dataframe(frame, hide_index=True, width="stretch", alt="Latest overridden alerts",
                     column_config={"alert_id": "Alert #", "override_reason": "Reason",
                                    "created_at": "Alert raised"})
    else:
        st.info("No alerts have been overridden.")
