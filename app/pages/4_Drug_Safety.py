"""Drug safety data: openFDA labels and adverse-event reports from MongoDB, signals from PostgreSQL."""

import altair as alt
import pandas as pd
import streamlit as st
from pymongo.errors import PyMongoError

from app import session, ui
from ingestion import mongo_queries
from medisentinel import db

conn = session.require_login()

ui.page_header("🌐", "Drug safety data", "openFDA drug labels and adverse-event reports (MongoDB) behind "
                                        "the safety rules.")


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
    """Single-series horizontal bar chart of report counts (one hue, sorted, with tooltips)."""
    df = pd.DataFrame(rows).rename(columns={"_id": label, "report_count": "Reports"})
    df[label] = df[label].astype(str).str.title()
    chart = (
        alt.Chart(df)
        .mark_bar(color=ui.CHART_BLUE, cornerRadiusEnd=4, height=18)
        .encode(
            y=alt.Y(f"{label}:N", sort="-x", title=None, axis=alt.Axis(labelLimit=200, labelFontSize=12)),
            x=alt.X("Reports:Q", title="Reports", axis=alt.Axis(grid=True, gridColor="#E2E8F0", tickMinStep=1)),
            tooltip=[alt.Tooltip(f"{label}:N"), alt.Tooltip("Reports:Q", format=",")],
        )
        .properties(height=height)
        .configure_view(stroke=None)
    )
    st.altair_chart(chart, width="stretch")


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
    ui.kpi("Drug labels", counts["labels"], "openFDA · MongoDB", tone="accent")
with k2:
    ui.kpi("Adverse-event reports", counts["reports"], "openFDA FAERS · MongoDB")
with k3:
    ui.kpi("Safety signals", len(signals), "PRR / ROR · PostgreSQL")

st.write("")
c1, c2 = st.columns(2, gap="large")
with c1:
    with st.container(border=True):
        st.markdown("##### Most reported adverse reactions")
        if reactions:
            bar_chart(reactions, "Reaction")
            st.caption("MongoDB aggregation: $unwind reactions → $group → $sort → $limit.")
        else:
            st.info("No reports loaded. Run ingestion/load_openfda.py.")
with c2:
    with st.container(border=True):
        st.markdown("##### Most reported drugs")
        if drugs:
            bar_chart(drugs, "Drug")
            st.caption("Counts every drug named in a report, suspect or concomitant.")
        else:
            st.info("No reports loaded. Run ingestion/load_openfda.py.")

with st.container(border=True):
    st.markdown("##### Drug label lookup")
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
                st.markdown("**Drug interactions (label text)**")
                st.write(short(label.get("drug_interactions", ["Not stated."])[0]))
                if label.get("contraindications"):
                    st.markdown("**Contraindications**")
                    st.write(short(label["contraindications"][0], 500))
                reported = drug_reactions(fda.get("generic_name", [brand])[0])
                if reported:
                    st.markdown("**Reactions reported for this drug**")
                    bar_chart(reported, "Reaction", height=200)
        st.caption("Phase 2 turns this label text into Interaction and Contraindication rows with NLP.")

with st.container(border=True):
    st.markdown("##### Adverse-reaction signals")
    if not signals:
        st.info("No signals computed yet.")
    else:
        st.dataframe(
            pd.DataFrame(signals), hide_index=True, width="stretch",
            column_config={
                "medication": "Medicine", "reaction_term": "Reaction",
                "report_count": st.column_config.NumberColumn("Reports", format="%d"),
                "prr": st.column_config.NumberColumn("PRR", format="%.2f",
                                                     help="Proportional Reporting Ratio: above 2 suggests a signal"),
                "ror": st.column_config.NumberColumn("ROR", format="%.2f", help="Reporting Odds Ratio"),
            })
        st.caption("PRR above 2 with at least 3 reports is the usual threshold for a signal. Phase 2 computes "
                   "these from the MongoDB reports.")
