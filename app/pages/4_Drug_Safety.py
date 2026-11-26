"""Drug safety data: openFDA labels and adverse-event reports from MongoDB, signals from PostgreSQL."""

import altair as alt
import pandas as pd
import streamlit as st
from pymongo.errors import PyMongoError

from app import session, ui
from ingestion import mongo_queries
from medisentinel import db

conn = session.require_login()

ui.page_header("Drug safety data", "openFDA drug labels and adverse-event reports stored in MongoDB: the "
                                   "evidence behind the safety rules.", eyebrow="Surveillance")


@st.cache_data(ttl=600, show_spinner=False)
def mongo_overview():
    return (mongo_queries.collection_counts(), mongo_queries.top_reactions(10),
            mongo_queries.top_reported_drugs(10))


@st.cache_data(ttl=600, show_spinner=False)
def label_search(text):
    return mongo_queries.find_labels(text, limit=8)


@st.cache_data(ttl=600, show_spinner=False)
def drug_reactions(drug):
    return mongo_queries.reactions_for_drug(drug, 8)


def bar_chart(rows, label, height=300):
    """Single-series horizontal bars of report counts (one hue, sorted, with tooltips)."""
    df = pd.DataFrame(rows).rename(columns={"_id": label, "report_count": "Reports"})
    df[label] = df[label].astype(str).str.title()
    chart = (
        alt.Chart(df)
        .mark_bar(color=ui.BRAND, cornerRadiusEnd=4, height=16)
        .encode(
            y=alt.Y(f"{label}:N", sort="-x", title=None,
                    axis=alt.Axis(labelLimit=200, labelFontSize=12, labelColor="#344054", ticks=False, domain=False,
                                  labelPadding=8, minExtent=170)),
            x=alt.X("Reports:Q", title=None,
                    axis=alt.Axis(gridColor="#F2F4F7", labelColor="#98A2B3", domain=False, ticks=False,
                                  tickMinStep=1)),
            tooltip=[alt.Tooltip(f"{label}:N"), alt.Tooltip("Reports:Q", format=",")],
        )
        .properties(height=height)
        .configure_view(stroke=None)
        .configure(font="Inter", background="#FFFFFF", padding={"left": 16, "right": 12, "top": 4, "bottom": 4},
                   autosize=alt.AutoSizeParams(type="fit", contains="padding"))
    )
    st.altair_chart(chart, width="stretch", theme=None)


def short(text, limit=700):
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + " …"


try:
    counts, reactions, drugs = mongo_overview()
except PyMongoError:
    st.error("MongoDB is not reachable. Start the MongoDB service and reload this page.",
             icon=":material/cloud_off:")
    st.stop()

signals = db.list_signals(conn, limit=20)
k1, k2, k3 = st.columns(3)
with k1:
    ui.kpi("Drug labels", counts["labels"], "openFDA SPL · MongoDB", "database", "brand")
with k2:
    ui.kpi("Adverse-event reports", counts["reports"], "openFDA FAERS · MongoDB", "activity")
with k3:
    ui.kpi("Safety signals", len(signals), "PRR / ROR · PostgreSQL", "alert")

st.write("")
c1, c2 = st.columns(2, gap="medium")
with c1:
    with st.container(border=True, key="card_1"):
        ui.card_title("Most reported reactions", "MongoDB aggregation: $unwind → $group → $sort → $limit")
        if reactions:
            bar_chart(reactions, "Reaction")
        else:
            st.info("No reports loaded. Run ingestion/load_openfda.py.")
with c2:
    with st.container(border=True, key="card_2"):
        ui.card_title("Most reported drugs", "Every drug named in a report, suspect or concomitant")
        if drugs:
            bar_chart(drugs, "Drug")
        else:
            st.info("No reports loaded. Run ingestion/load_openfda.py.")

with st.container(border=True, key="card_3"):
    ui.card_title("Drug label lookup", "Search the FDA label text that Phase 2 turns into interaction rules.")
    query = st.text_input("Search a drug", placeholder="e.g. warfarin, ibuprofen, metformin",
                          icon=":material/search:", label_visibility="collapsed")
    if query.strip():
        labels = label_search(query.strip())
        if not labels:
            st.info(f"No openFDA label starts with “{query.strip()}”.")
        for label in labels:
            fda = label.get("openfda", {})
            brand = ", ".join(fda.get("brand_name", [])[:2]) or "Unbranded"
            generic = ", ".join(fda.get("generic_name", [])[:2]) or "-"
            maker = ", ".join(fda.get("manufacturer_name", [])[:1])
            with st.expander(f"{brand.title()} · {generic.lower()}" + (f" · {maker}" if maker else "")):
                drug_class = ", ".join(fda.get("pharm_class_epc", [])[:2])
                if drug_class:
                    st.caption(drug_class)
                if label.get("boxed_warning"):
                    st.error(short(label["boxed_warning"][0], 500), icon=":material/warning:")
                ui.label("Drug interactions")
                st.write(short(label.get("drug_interactions", ["Not stated."])[0]))
                if label.get("contraindications"):
                    ui.label("Contraindications")
                    st.write(short(label["contraindications"][0], 500))
                reported = drug_reactions(fda.get("generic_name", [brand])[0])
                if reported:
                    ui.label("Reactions reported for this drug")
                    bar_chart(reported, "Reaction", height=200)

with st.container(border=True, key="card_4"):
    ui.card_title("Adverse-reaction signals", "A PRR above 2 with at least 3 reports is the usual threshold for "
                                              "a signal.")
    if not signals:
        st.info("No signals computed yet.")
    else:
        rows = [{"medication": s["medication"], "reaction": s["reaction_term"].capitalize(),
                 "reports": f"{s['report_count']:,}", "prr": f"{s['prr']:.2f}", "ror": f"{s['ror']:.2f}",
                 "flag": ui.neutral_pill("Signal", "#B42318", "#FEF3F2", "#FECDCA")
                 if s["prr"] and s["prr"] >= 2 and (s["report_count"] or 0) >= 3
                 else ui.neutral_pill("Below threshold")} for s in signals]
        ui.table(rows, [("medication", "Medicine", "strong"), ("reaction", "Reaction", ""),
                        ("reports", "Reports", "num"), ("prr", "PRR", "num"), ("ror", "ROR", "num"),
                        ("flag", "Status", "html")])
