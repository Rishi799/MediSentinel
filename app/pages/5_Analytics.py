"""Analytics: what Phase 2 added – rules learned from FDA labels, model risk scores, adverse-event signals,
alerts by department and the override audit. Read-only for every role."""
import altair as alt
import pandas as pd
import streamlit as st

from app import analytics_queries as queries
from app import session, ui

conn = session.require_login()
ui.page_header("Analytics", "Rules learned from FDA labels, model risk scores, adverse-event signals and "
                            "override behaviour.", eyebrow="Surveillance")

SEVERITIES = ["MAJOR", "MODERATE", "MINOR"]
SEVERITY_LABELS = [ui.SEVERITY_STYLE[s]["label"] for s in SEVERITIES]
SEVERITY_SCALE = alt.Scale(domain=SEVERITY_LABELS, range=[ui.SEVERITY_STYLE[s]["color"] for s in SEVERITIES])
LABEL, MUTED = ui.CHART_LABEL, ui.CHART_AXIS


def styled(chart, height=240):
    """The shared chart look (same as the Dashboard and Drug safety pages)."""
    return ui.chart_style(chart, height)


def severity_label(series):
    return series.map(lambda s: ui.SEVERITY_STYLE.get(s, {}).get("label", "Unknown"))


rule_rows = {r["kind"]: r for r in queries.rule_totals(conn)}
totals = queries.alert_totals(conn)
risk = queries.risk_summary(conn)
signals = queries.signal_map(conn)
learned_total = sum(r["learned"] for r in rule_rows.values())
curated_total = sum(r["total"] - r["learned"] for r in rule_rows.values())
strong_signals = sum(1 for s in signals if s["prr"] >= 2)
override_rate = totals["overridden"] / totals["total"] if totals["total"] else 0

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    ui.kpi("Learned rules", learned_total,
           f"{rule_rows['Interaction']['learned']:,} inter. · {rule_rows['Contraindication']['learned']:,} contra.",
           "file", "brand")
with k2:
    ui.kpi("Curated rules", curated_total, "Hand-written rules", "shield")
with k3:
    ui.kpi("Safety signals", strong_signals, "PRR ≥ 2 (FAERS)", "activity")
with k4:
    mean = f"mean {risk['mean_score']:.0%}" if risk and risk["mean_score"] is not None else "not scored yet"
    ui.kpi("Scored alerts", totals["scored"], f"of {totals['total']:,} · {mean}", "alert", "danger")
with k5:
    ui.kpi("Override rate", f"{override_rate:.0%}", f"{totals['overridden']:,} of {totals['total']:,} alerts",
           "history")

st.write("")
left, right = st.columns([1.2, 1], gap="medium")

# ---------------- rules learned ----------------
with left:
    with st.container(border=True, key="card_1"):
        ui.card_title("Rules learned from FDA labels", "Extracted from openFDA label text and loaded by the rule "
                                                       "bridge, by severity.")
        learned = pd.DataFrame(queries.learned_by_severity(conn))
        learned = learned[(learned["rules"] > 0) & learned["severity"].isin(SEVERITIES)] if len(learned) else learned
        if learned.empty:
            ui.empty_state("file", "No learned rules yet", "Run the extractor and the rule bridge.")
        else:
            learned["Severity"] = severity_label(learned["severity"])
            chart = alt.Chart(learned).mark_bar(cornerRadiusEnd=4, stroke="#FFFFFF", strokeWidth=2, height=34).encode(
                y=alt.Y("kind:N", title=None, sort=["Interaction", "Contraindication"],
                        axis=alt.Axis(labelColor=LABEL, labelFontSize=12, minExtent=120)),
                x=alt.X("sum(rules):Q", title="Rules", axis=alt.Axis(format="d", tickMinStep=1)),
                color=alt.Color("Severity:N", scale=SEVERITY_SCALE, sort=SEVERITY_LABELS),
                order=alt.Order("rank:Q"),
                tooltip=[alt.Tooltip("kind:N", title="Rule type"), "Severity:N",
                         alt.Tooltip("sum(rules):Q", title="Rules")],
            ).transform_calculate(rank="indexof(['Major','Moderate','Minor'], datum.Severity)")
            st.altair_chart(styled(chart, 150), width="stretch", theme=None)
            ui.label("Medicines with the most learned rules")
            top = queries.rules_per_medicine(conn, limit=5)
            if top:
                ui.bar_list([(r["medicine"], r["rules"], "rules") for r in top])

# ---------------- risk scores ----------------
with right:
    with st.container(border=True, key="card_2"):
        high = risk["high_risk"] if risk else 0
        ui.card_title("Model risk scores", f"{totals['scored']:,} alerts scored · {high:,} active alerts at high "
                                           "risk (≥ 66%).")
        dist = pd.DataFrame(queries.risk_distribution(conn))
        if dist.empty:
            ui.empty_state("activity", "No scores yet", "Run python -m ml.score_alerts.")
        else:
            bands = [f"{b * 10}–{b * 10 + 10}%" for b in range(10)]
            dist["Score band"] = dist["lower"].map(lambda v: bands[min(int(round(float(v) * 10)), 9)])
            dist["Severity"] = severity_label(dist["severity"])
            chart = alt.Chart(dist).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3, stroke="#FFFFFF",
                                             strokeWidth=1).encode(
                x=alt.X("Score band:O", title="Risk score", scale=alt.Scale(domain=bands),
                        axis=alt.Axis(labelAngle=-35, labelColor=MUTED, labelFontSize=10)),
                y=alt.Y("alerts:Q", title="Alerts", stack="zero",
                        axis=alt.Axis(format="d", tickMinStep=1, minExtent=30)),
                color=alt.Color("Severity:N", scale=SEVERITY_SCALE, sort=SEVERITY_LABELS),
                order=alt.Order("rank:Q"),
                tooltip=["Score band:N", "Severity:N", alt.Tooltip("alerts:Q", title="Alerts")],
            ).transform_calculate(rank="indexof(['Major','Moderate','Minor'], datum.Severity)")
            st.altair_chart(styled(chart, 360), width="stretch", theme=None)
            st.caption("Scores of 66% and above are shown as \"High\" on each alert's risk meter.")

# ---------------- signals ----------------
st.write("")
left, right = st.columns([1, 1], gap="medium")
with left:
    with st.container(border=True, key="card_3"):
        ui.card_title("Signal map", "Each point is a medicine–reaction pair from the adverse-event reports. Both "
                                    "axes use a log scale; the dashed line is the PRR = 2 signal threshold.")
        if not signals:
            ui.empty_state("activity", "No signals yet", "Run python -m analytics.signal_mining.")
        else:
            frame = pd.DataFrame(signals)
            frame["Status"] = frame["prr"].map(lambda p: "Signal (PRR ≥ 2)" if p >= 2 else "Below threshold")
            points = alt.Chart(frame).mark_circle(opacity=0.75, stroke="#FFFFFF", strokeWidth=1).encode(
                x=alt.X("reports:Q", title="Reports with the pair (log scale)", scale=alt.Scale(type="log", nice=False),
                        axis=alt.Axis(values=[1, 3, 10, 30, 100, 300, 1000], format="~s")),
                y=alt.Y("prr:Q", title="PRR (log scale)", scale=alt.Scale(type="log"),
                        axis=alt.Axis(values=[1, 2, 10, 100, 1000, 10000], format="~s", minExtent=34)),
                size=alt.Size("reports:Q", legend=None, scale=alt.Scale(range=[40, 280])),
                color=alt.Color("Status:N", scale=alt.Scale(domain=["Signal (PRR ≥ 2)", "Below threshold"],
                                                            range=[ui.BRAND, "#B7C2CE"])),
                tooltip=[alt.Tooltip("medicine:N", title="Medicine"), alt.Tooltip("reaction:N", title="Reaction"),
                         alt.Tooltip("reports:Q", title="Reports"), alt.Tooltip("prr:Q", title="PRR", format=".2f")],
            )
            threshold = alt.Chart(pd.DataFrame({"y": [2]})).mark_rule(strokeDash=[5, 4], color=ui.SEVERITY_STYLE["MAJOR"]["color"], strokeWidth=1.5).encode(
                y="y:Q")
            st.altair_chart(styled(points + threshold, 470), width="stretch", theme=None)
with right:
    with st.container(border=True, key="card_4"):
        ui.card_title("Strongest signals", "At least 3 reports, ranked by proportional reporting ratio.")
        top = queries.top_signals(conn, limit=7)
        if not top:
            ui.empty_state("activity", "No signals yet", "Run python -m analytics.signal_mining.")
        else:
            rows = [{"pair": f'<div class="ms-pair"><b>{ui.escape(r["medicine"])}</b>'
                             f'<span>{ui.escape(r["reaction"].capitalize())}</span></div>',
                     "reports": f"{r['reports']:,}", "prr": f"{r['prr']:,.1f}"} for r in top]
            ui.table(rows, [("pair", "Medicine · reaction", "html"), ("reports", "Reports", "num"),
                            ("prr", "PRR", "num")])
            st.caption("A high PRR can also reflect why the drug was prescribed (e.g. levothyroxine and "
                       "hypothyroidism); signals need clinical review.")

# ---------------- departments and overrides ----------------
st.write("")
left, right = st.columns([1.2, 1], gap="medium")
with left:
    with st.container(border=True, key="card_5"):
        ui.card_title("Alerts by department", "Alerts raised for each prescribing doctor's specialty.")
        dept = pd.DataFrame(queries.alerts_by_department(conn))
        if dept.empty:
            ui.empty_state("alert", "No alerts yet", "Alerts appear when prescriptions are checked.")
        else:
            dept = dept[dept["severity"].isin(SEVERITIES)]
            dept["Severity"] = severity_label(dept["severity"])
            chart = alt.Chart(dept).mark_bar(cornerRadiusEnd=4, stroke="#FFFFFF", strokeWidth=2, height=22).encode(
                y=alt.Y("department:N", sort="-x", title=None,
                        axis=alt.Axis(labelColor=LABEL, labelFontSize=12, labelLimit=170, minExtent=130)),
                x=alt.X("sum(alerts):Q", title="Alerts", axis=alt.Axis(format="d", tickMinStep=1)),
                color=alt.Color("Severity:N", scale=SEVERITY_SCALE, sort=SEVERITY_LABELS),
                order=alt.Order("rank:Q"),
                tooltip=[alt.Tooltip("department:N", title="Specialty"), "Severity:N",
                         alt.Tooltip("sum(alerts):Q", title="Alerts")],
            ).transform_calculate(rank="indexof(['Major','Moderate','Minor'], datum.Severity)")
            st.altair_chart(styled(chart, max(150, 34 * dept["department"].nunique())), width="stretch", theme=None)
with right:
    with st.container(border=True, key="card_6"):
        ui.card_title("Override audit", "Latest overridden alerts with the doctor's recorded reason.")
        overrides = queries.recent_overrides(conn)
        if not overrides:
            ui.empty_state("history", "No overrides yet", "Every override and its reason is listed here.")
        else:
            rows = [{"id": f"#{o['alert_id']}", "sev": ui.severity_pill(o["severity"]), "patient": o["patient"],
                     "medication": o["medication"], "reason": o["override_reason"]} for o in overrides[:8]]
            ui.table(rows, [("id", "Alert", "num"), ("sev", "Severity", "html"), ("patient", "Patient", "strong"),
                            ("medication", "Medicine", ""), ("reason", "Reason", "")])
