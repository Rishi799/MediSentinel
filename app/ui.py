"""Shared look and feel for every MediSentinel page: styles, icons, page headers, KPI cards,
severity pills, alert lists, risk scale and small tables.

All text that comes from the database goes through html.escape before it is placed inside
HTML, so a name such as "<script>" is shown as text and never run.
"""

from datetime import date
from html import escape

import streamlit as st

# ---------- design tokens: white-dominant, medical green and teal ----------
BRAND = "#0E7A5C"        # medical green (primary)
BRAND_DARK = "#0B6B50"
TEAL = "#65B8AD"         # secondary accent
INK = "#20354A"          # headings
BODY = "#516174"         # body text
MUTED = "#8A98A8"        # supporting text
LINE = "#E8EEF3"         # borders
TINT = "#F6F9F8"         # soft surfaces
CHART_BLUE = BRAND
# one chart look for every page: same font, axis greys, grid and legend
CHART_GRID, CHART_LABEL, CHART_AXIS = "#EEF3F7", "#3C4E63", "#8A98A8"


def chart_style(chart, height=240):
    """Apply the shared MediSentinel chart theme (Inter, white, quiet axes, legend top-left) to an Altair chart."""
    import altair as alt
    return (chart.properties(height=height)
            .configure(font="Inter", background="#FFFFFF",
                       padding={"left": 4, "right": 14, "top": 6, "bottom": 4},
                       autosize=alt.AutoSizeParams(type="fit", contains="padding"))
            .configure_axis(labelColor=CHART_AXIS, titleColor=CHART_AXIS, titleFontWeight=500, titleFontSize=11,
                            labelFontSize=11, gridColor=CHART_GRID, domain=False, ticks=False, labelPadding=8,
                            titlePadding=10)
            .configure_axisBand(labelColor=CHART_LABEL, labelFontSize=12)
            .configure_legend(orient="top", title=None, labelColor="#5C6B7D", labelFontSize=12,
                              symbolType="circle", symbolSize=80, symbolOpacity=1, columnPadding=18, offset=10)
            .configure_view(stroke=None))

# Severity = calm status colours; always shown with a dot and a word, never colour alone.
SEVERITY_STYLE = {
    "MAJOR":    {"color": "#D46A6A", "bg": "#FCF2F2", "text": "#A94444", "border": "#F2D6D6", "label": "Major"},
    "MODERATE": {"color": "#D9A441", "bg": "#FCF7EB", "text": "#8F6A1E", "border": "#F1E2BE", "label": "Moderate"},
    "MINOR":    {"color": "#7D9BC1", "bg": "#F2F6FB", "text": "#4C6A91", "border": "#D9E3F0", "label": "Minor"},
}
SUCCESS = {"color": "#4FAE8A", "bg": "#EFF8F4", "text": "#2F7A5E", "border": "#CDE9DD"}
ALERT_TYPE_LABEL = {"INTERACTION": "Drug interaction", "CONTRA": "Contraindication", "ALLERGY": "Allergy"}
ROLE_LABEL = {"doctor": "Doctor", "pharmacist": "Pharmacist", "admin": "Administrator"}

# Line icons (Lucide, ISC licence), drawn with the current text colour.
_ICONS = {
    "shield": '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 '
              '4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>'
              '<path d="m9 12 2 2 4-4"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>'
             '<path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "pill": '<path d="m10.5 20.5 10-10a4.95 4.95 0 1 0-7-7l-10 10a4.95 4.95 0 1 0 7 7Z"/><path d="m8.5 8.5 7 7"/>',
    "file": '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>'
            '<path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M16 13H8"/><path d="M16 17H8"/>',
    "alert": '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/>'
             '<path d="M12 9v4"/><path d="M12 17h.01"/>',
    "activity": '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    "database": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5"/>'
                '<path d="M3 12a9 3 0 0 0 18 0"/>',
    "lock": '<rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    "zap": '<path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 '
           '0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"/>',
    "globe": '<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/>'
             '<path d="M2 12h20"/>',
    "check": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    "history": '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>'
               '<path d="M12 7v5l4 2"/>',
    "heart": '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 '
             '5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
}


def icon(name, size=18, color="currentColor", stroke=2):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" '
            f'fill="none" stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" '
            f'stroke-linejoin="round" style="flex-shrink:0">{_ICONS[name]}</svg>')


_CSS = """
<style>
html, body, [class*="css"] {-webkit-font-smoothing: antialiased;}
header[data-testid="stHeader"] {background: transparent;}
.block-container {padding-top: 2.4rem; padding-bottom: 4rem; max-width: 1240px;
    animation: ms-enter 0.35s ease-out both;}
@keyframes ms-enter {from {opacity: 0; transform: translateY(6px);} to {opacity: 1; transform: none;}}
h1, h2, h3, h4, h5 {letter-spacing: -0.015em; color: #20354A;}
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li {color: #516174;}
button[kind^="primary"], button[kind^="primary"] p, button[kind^="primary"] div {color: #FFFFFF !important;}
button[kind^="secondary"] p, button[kind^="tertiary"] p {color: inherit;}

/* sidebar */
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] {border-radius: 8px; margin: 2px 0;
    transition: background 0.15s ease;}
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] span {font-weight: 500; font-size: 0.92rem; color: #3C4E63;}
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] {background: #ECFDF3;}
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] span {color: #0B6B50; font-weight: 600;}
[data-testid="stSidebar"] [data-testid="stNavSectionHeader"] {font-size: 0.7rem; letter-spacing: 0.07em;
    text-transform: uppercase; color: #9AA8B6; font-weight: 600;}

/* surfaces: bordered containers (keyed card_N) and forms become white cards */
.stVerticalBlock[class*="st-key-card_"], [data-testid="stForm"] {background: #FFFFFF;
    border-color: #E8EEF3 !important; border-radius: 14px; box-shadow: 0 1px 2px rgba(32, 53, 74, 0.04);
    padding: 1.25rem 1.35rem; transition: box-shadow 0.2s ease;}
.stVerticalBlock[class*="st-key-card_"]:hover {box-shadow: 0 6px 18px rgba(32, 53, 74, 0.06);}
.stVerticalBlock[class*="st-key-card_"] [data-testid="stForm"] {box-shadow: none; padding: 0;}

/* equal-height rows: cards side by side stretch to the tallest one (the last card in a column grows) */
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"]
    > [data-testid="stLayoutWrapper"] > .stVerticalBlock[class*="st-key-card_"]) {align-items: stretch;}
[data-testid="stColumn"]:has(> [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"]
    > .stVerticalBlock[class*="st-key-card_"]) > [data-testid="stVerticalBlock"] {height: 100%;}
[data-testid="stColumn"] > [data-testid="stVerticalBlock"]
    > [data-testid="stLayoutWrapper"]:last-child:has(> .stVerticalBlock[class*="st-key-card_"]) {flex: 1 1 auto;}
[data-testid="stColumn"] > [data-testid="stVerticalBlock"]
    > [data-testid="stLayoutWrapper"]:last-child > .stVerticalBlock[class*="st-key-card_"] {height: 100%;}

/* inputs, buttons, tabs */
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"] {border-radius: 10px !important;}
[data-baseweb="input"]:focus-within, [data-baseweb="select"] > div:focus-within,
[data-baseweb="textarea"]:focus-within {box-shadow: 0 0 0 3px rgba(14, 122, 92, 0.15);}
.stButton button, .stFormSubmitButton button {font-weight: 600; border-radius: 10px; transition: all 0.15s ease;}
.stButton button[kind="primary"]:hover, .stFormSubmitButton button[kind="primaryFormSubmit"]:hover {
    box-shadow: 0 4px 12px rgba(14, 122, 92, 0.28); transform: translateY(-1px);}
.stButton button:active, .stFormSubmitButton button:active {transform: translateY(0); box-shadow: none;}
[data-testid="stPageLink"] a {border-radius: 8px; transition: background 0.15s ease;}
[data-testid="stPageLink"] a:hover {background: #ECFDF3;}
.stTabs [data-baseweb="tab-list"] {gap: 1.4rem; border-bottom: 1px solid #E8EEF3;}
.stTabs [data-baseweb="tab"] {padding: 0.6rem 0; font-weight: 500; color: #6B7A8C;}
.stTabs [aria-selected="true"] {color: #20354A;}
.stTabs [data-baseweb="tab-highlight"] {background: #0E7A5C; height: 2px;}
[data-testid="stDataFrame"] {border-radius: 10px;}
[data-testid="stAlert"] {border-radius: 12px;}
[data-testid="stExpander"] details {border-radius: 12px; border-color: #E8EEF3;}
::-webkit-scrollbar {width: 10px; height: 10px;}
::-webkit-scrollbar-thumb {background: #D5DEE7; border-radius: 8px; border: 2px solid #F6F9F8;}
::-webkit-scrollbar-thumb:hover {background: #AEBBC8;}
::-webkit-scrollbar-track {background: transparent;}

/* page header */
.ms-eyebrow {font-size: 0.74rem; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase;
    color: #0E7A5C; margin-bottom: 0.3rem;}
.ms-title {font-family: "Plus Jakarta Sans", Inter, sans-serif; font-size: 1.85rem; font-weight: 700;
    letter-spacing: -0.02em; color: #20354A; margin: 0; line-height: 1.22;}
.ms-subtitle {color: #6B7A8C; font-size: 0.98rem; margin: 0.4rem 0 1.5rem 0; max-width: 780px; line-height: 1.55;}

/* welcome banner */
.ms-welcome {display: flex; align-items: center; justify-content: space-between; gap: 1.5rem; flex-wrap: wrap;
    background: #FFFFFF; border: 1px solid #E8EEF3; border-radius: 16px; padding: 1.35rem 1.5rem;
    margin-bottom: 1.25rem; box-shadow: 0 1px 2px rgba(32, 53, 74, 0.04);}
.ms-welcome-left {display: flex; align-items: center; gap: 1rem;}
.ms-welcome-mark {width: 48px; height: 48px; border-radius: 14px; background: #ECFDF3; color: #0E7A5C;
    display: flex; align-items: center; justify-content: center; flex-shrink: 0;}
.ms-welcome-title {font-family: "Plus Jakarta Sans", Inter, sans-serif; font-size: 1.25rem; font-weight: 700;
    color: #20354A;}
.ms-welcome-sub {color: #6B7A8C; font-size: 0.9rem; margin-top: 0.15rem;}
.ms-welcome-chip {display: inline-flex; align-items: center; gap: 0.45rem; padding: 0.4rem 0.8rem;
    border-radius: 999px; background: #F6F9F8; border: 1px solid #E8EEF3; color: #3C4E63; font-size: 0.84rem;
    font-weight: 500;}

/* "why this alert" source sentence */
.ms-quote {border-left: 3px solid #65B8AD; background: #F3FAF9; padding: 0.6rem 0.85rem; border-radius: 0 10px 10px 0;
    color: #3C4E63; font-size: 0.87rem; margin: 0.3rem 0 0.4rem 0; line-height: 1.5;}

/* KPI cards */
.ms-kpi {background: #FFFFFF; border: 1px solid #E8EEF3; border-radius: 14px; padding: 1.1rem 1.2rem;
    box-shadow: 0 1px 2px rgba(32, 53, 74, 0.04); height: 100%; box-sizing: border-box; transition: box-shadow 0.2s ease, transform 0.2s ease;}
.ms-kpi:hover {box-shadow: 0 8px 20px rgba(32, 53, 74, 0.07); transform: translateY(-2px);}
.ms-kpi-top {display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem;}
.ms-kpi-label {color: #5C6B7D; font-size: 0.84rem; font-weight: 500;}
.ms-kpi-icon {width: 36px; height: 36px; border-radius: 10px; display: flex; align-items: center;
    justify-content: center; color: #6B7A8C; background: #F6F9F8; flex-shrink: 0;}
.ms-kpi-icon.danger {color: #C25555; background: #FCF2F2;}
.ms-kpi-icon.brand {color: #067647; background: #ECFDF3; box-shadow: inset 0 0 0 1px #ABEFC6;}
.ms-kpi-icon.teal {color: #3F978B; background: #EFF8F6;}
.ms-kpi-value {font-family: "Plus Jakarta Sans", Inter, sans-serif; font-size: 1.95rem; font-weight: 700;
    color: #20354A; letter-spacing: -0.02em; margin-top: 0.4rem; font-variant-numeric: tabular-nums; line-height: 1.15;}
.ms-kpi-note {color: #8A98A8; font-size: 0.8rem; margin-top: 0.25rem; line-height: 1.35;}

/* card headings inside containers */
.ms-card-title {font-family: "Plus Jakarta Sans", Inter, sans-serif; font-size: 1.02rem; font-weight: 650;
    color: #20354A; margin: 0;}
.ms-card-sub {font-size: 0.84rem; color: #7A8898; margin: 0.2rem 0 0.9rem 0; line-height: 1.5;}

/* pills and chips */
.ms-pill {display: inline-flex; align-items: center; gap: 0.38rem; padding: 0.14rem 0.6rem 0.14rem 0.5rem;
    border-radius: 999px; font-size: 0.75rem; font-weight: 600; border: 1px solid; white-space: nowrap;}
.ms-pill .dot {width: 6px; height: 6px; border-radius: 50%;}
.ms-chip {display: inline-block; padding: 0.2rem 0.65rem; margin: 0 0.35rem 0.4rem 0; border-radius: 8px;
    font-size: 0.82rem; background: #F6F9F8; color: #3C4E63; border: 1px solid #E8EEF3; font-weight: 500;}
.ms-chip.warn {background: #FCF2F2; border-color: #F2D6D6; color: #A94444;}
.ms-muted {color: #9AA8B6; font-size: 0.85rem;}
.ms-label {font-size: 0.72rem; font-weight: 600; color: #7A8898; text-transform: uppercase;
    letter-spacing: 0.07em; margin: 1rem 0 0.45rem 0;}

/* alert list */
.ms-alerts {display: flex; flex-direction: column;}
.ms-alert {display: flex; gap: 0.8rem; padding: 0.85rem 0; border-top: 1px solid #F0F4F8;}
.ms-alert:first-child {border-top: none; padding-top: 0.2rem;}
.ms-alert-bar {width: 3px; border-radius: 3px; flex-shrink: 0;}
.ms-alert-body {flex: 1; min-width: 0;}
.ms-alert-head {display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;}
.ms-alert-title {font-weight: 600; color: #20354A; font-size: 0.92rem;}
.ms-alert-msg {color: #5C6B7D; font-size: 0.88rem; margin-top: 0.25rem;}
.ms-alert-meta {color: #9AA8B6; font-size: 0.78rem; margin-top: 0.2rem;}

/* simple tables */
.ms-table-wrap {border: 1px solid #E8EEF3; border-radius: 12px; overflow-x: auto; background: #FFFFFF;}
.ms-table {width: 100%; border-collapse: collapse; font-size: 0.88rem; border: none; margin: 0;}
.ms-table th, .ms-table td {border-left: none !important; border-right: none !important; border-top: none !important;}
.ms-table th {text-align: left; font-weight: 600; color: #7A8898; font-size: 0.74rem; letter-spacing: 0.03em;
    text-transform: uppercase; padding: 0.65rem 0.85rem; background: #F8FAFC; border-bottom: 1px solid #E8EEF3;
    white-space: nowrap;}
.ms-table td {padding: 0.75rem 0.85rem; border-bottom: 1px solid #F0F4F8; color: #516174; vertical-align: top;}
.ms-table tr:last-child td {border-bottom: none;}
.ms-pair {display: flex; flex-direction: column; gap: 0.1rem; min-width: 0;}
.ms-pair b {color: #20354A; font-weight: 500;}
.ms-pair span {color: #7A8898; font-size: 0.82rem;}
.ms-table td.strong {color: #20354A; font-weight: 500;}
.ms-table td.num {font-variant-numeric: tabular-nums; white-space: nowrap;}
.ms-table tbody tr {transition: background 0.12s ease;}
.ms-table tbody tr:hover td {background: #F7FBF9;}

/* profile */
.ms-avatar {width: 46px; height: 46px; border-radius: 50%; background: #ECFDF3; color: #067647;
    display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 1rem; flex-shrink: 0;
    border: 1px solid #ABEFC6;}
.ms-profile-head {display: flex; gap: 0.85rem; align-items: center;}
.ms-profile-name {font-family: "Plus Jakarta Sans", Inter, sans-serif; font-weight: 700; font-size: 1.12rem; color: #20354A;}
.ms-profile-meta {color: #7A8898; font-size: 0.85rem;}
.ms-facts {display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem; margin-top: 1rem;}
.ms-fact {background: #F8FAFC; border: 1px solid #EDF2F6; border-radius: 10px; padding: 0.6rem 0.8rem;}
.ms-fact-k {font-size: 0.74rem; color: #8A98A8;}
.ms-fact-v {font-weight: 600; color: #20354A; font-size: 0.93rem;}

/* empty states */
.ms-empty {display: flex; flex-direction: column; align-items: center; text-align: center; padding: 1.8rem 1rem;}
.ms-empty .ic {width: 50px; height: 50px; border-radius: 50%; background: #ECFDF3; color: #0E7A5C;
    display: flex; align-items: center; justify-content: center; margin-bottom: 0.75rem;}
.ms-empty b {color: #20354A; font-size: 0.95rem;}
.ms-empty span {color: #7A8898; font-size: 0.85rem; margin-top: 0.25rem; max-width: 280px;}

/* bar list (ranked values) */
.ms-bars {display: flex; flex-direction: column; gap: 0.6rem;}
.ms-bar-row {display: grid; grid-template-columns: 1fr auto; gap: 0.3rem 0.8rem; align-items: center;}
.ms-bar-name {font-size: 0.88rem; color: #20354A; font-weight: 500; white-space: nowrap; overflow: hidden;
    text-overflow: ellipsis;}
.ms-bar-val {font-size: 0.82rem; color: #516174; font-variant-numeric: tabular-nums; white-space: nowrap;}
.ms-bar-val small {color: #9AA8B6; margin-left: 0.35rem;}
.ms-bar-track {grid-column: 1 / span 2; height: 6px; border-radius: 999px; background: #EEF3F7; overflow: hidden;}
.ms-bar-fill {height: 100%; border-radius: 999px; background: #0E7A5C;}

/* risk pill and risk scale */
.ms-risk {display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.22rem 0.7rem; border-radius: 999px;
    font-size: 0.78rem; font-weight: 600; border: 1px solid;}
.ms-scale {padding: 0.15rem 0 0.4rem 0;}
.ms-scale-head {display: flex; align-items: baseline; justify-content: space-between; gap: 0.5rem;}
.ms-scale-value {font-family: "Plus Jakarta Sans", Inter, sans-serif; font-size: 1.35rem; font-weight: 700;
    color: #20354A; font-variant-numeric: tabular-nums;}
.ms-scale-track {position: relative; display: grid; grid-template-columns: 33fr 33fr 34fr; gap: 3px;
    margin-top: 0.45rem;}
.ms-scale-track > div {height: 8px; border-radius: 999px;}
.ms-scale-marker {position: absolute; top: -4px; width: 4px; height: 16px; border-radius: 3px; background: #20354A;
    box-shadow: 0 0 0 2px #FFFFFF; transform: translateX(-50%);}
.ms-scale-labels {display: grid; grid-template-columns: 33fr 33fr 34fr; font-size: 0.72rem; color: #9AA8B6;
    margin-top: 0.3rem;}
.ms-scale-labels span:nth-child(2) {text-align: center;} .ms-scale-labels span:last-child {text-align: right;}
.ms-scale-note {font-size: 0.8rem; color: #7A8898; margin-top: 0.45rem; line-height: 1.45;}
.ms-factors {display: grid; grid-template-columns: 1fr; gap: 0.4rem; margin-top: 0.3rem;}
.ms-factor {display: flex; justify-content: space-between; gap: 0.5rem; background: #F8FAFC; border: 1px solid #EDF2F6;
    border-radius: 9px; padding: 0.45rem 0.7rem; font-size: 0.82rem;}
.ms-factor span {color: #7A8898;} .ms-factor b {color: #20354A; font-weight: 600;}

/* sidebar system status and account */
.ms-status {margin-top: 1.1rem; padding-top: 0.9rem; border-top: 1px solid #E8EEF3;}
.ms-status-title {font-size: 0.7rem; letter-spacing: 0.07em; text-transform: uppercase; color: #9AA8B6;
    font-weight: 600; margin-bottom: 0.45rem;}
.ms-status-row {display: flex; align-items: center; gap: 0.5rem; font-size: 0.84rem; color: #3C4E63; padding: 0.18rem 0;}
.ms-status-dot {width: 7px; height: 7px; border-radius: 50%; box-shadow: 0 0 0 3px rgba(79, 174, 138, 0.16);}
.ms-status-val {margin-left: auto; color: #7A8898; font-size: 0.8rem;}
.ms-status-note {font-size: 0.76rem; color: #9AA8B6; margin-top: 0.55rem; line-height: 1.45;}
.ms-account {display: flex; align-items: center; gap: 0.65rem; padding: 0.7rem 0.75rem; border: 1px solid #E8EEF3;
    border-radius: 12px; background: #F8FAFC; margin-bottom: 0.5rem;}
.ms-account .ms-avatar {width: 36px; height: 36px; font-size: 0.85rem;}
.ms-account-name {font-weight: 600; color: #20354A; font-size: 0.9rem; line-height: 1.2;}
.ms-account-meta {color: #7A8898; font-size: 0.78rem;}

/* responsive */
@media (max-width: 900px) {
    .block-container {padding-top: 1.6rem;}
    .ms-title {font-size: 1.55rem;}
    .ms-kpi-value {font-size: 1.6rem;}
}
@media (max-width: 640px) {
    .block-container {padding-left: 1rem; padding-right: 1rem;}
    .ms-facts, .ms-factors {grid-template-columns: 1fr;}
    .ms-welcome {padding: 1.1rem;}
    .ms-table {font-size: 0.82rem;}
}
@media (prefers-reduced-motion: reduce) {
    .block-container, .ms-kpi, .stVerticalBlock[class*="st-key-card_"] {animation: none; transition: none;}
}
</style>
"""

_LOGIN_CSS = """
<style>
section[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {display: none;}
[data-testid="stForm"] {background: transparent; box-shadow: none; padding: 0; border: none;}
.stApp {background:
    radial-gradient(60% 50% at 12% 8%, rgba(52, 192, 143, 0.10) 0%, rgba(52, 192, 143, 0) 70%),
    radial-gradient(50% 45% at 92% 90%, rgba(101, 184, 173, 0.10) 0%, rgba(101, 184, 173, 0) 70%), #F6F9F8;}
.block-container {max-width: 1220px; padding-top: 2.2rem;}

/* left: product story with a 3D scene */
.ms-hero {position: relative; border-radius: 26px; padding: 2.3rem 2.4rem 2rem 2.4rem; overflow: hidden;
    background: linear-gradient(160deg, #FFFFFF 0%, #F1FAF6 100%); border: 1px solid #E3EFEA;
    box-shadow: 0 1px 2px rgba(16, 60, 45, 0.04), 0 24px 60px -28px rgba(16, 90, 66, 0.25);}
.ms-hero::after {content: ""; position: absolute; right: -120px; top: -120px; width: 320px; height: 320px;
    border-radius: 50%; background: radial-gradient(circle, rgba(52, 192, 143, 0.14), rgba(52, 192, 143, 0) 70%);}
.ms-hero > * {position: relative; z-index: 1;}
.ms-hero-brand {display: flex; align-items: center; gap: 0.65rem; font-weight: 700; font-size: 1.08rem; color: #20354A;
    font-family: "Plus Jakarta Sans", Inter, sans-serif;}
.ms-hero-mark {width: 38px; height: 38px; border-radius: 11px; display: flex; align-items: center; justify-content: center;
    background: linear-gradient(145deg, #34C08F, #0B6B50);
    box-shadow: 0 6px 14px -4px rgba(14, 122, 92, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.35);}
.ms-hero h1 {font-family: "Plus Jakarta Sans", Inter, sans-serif; color: #20354A; font-size: 2.3rem;
    line-height: 1.14; letter-spacing: -0.03em; font-weight: 800; margin: 1.9rem 0 0.7rem 0;}
.ms-hero h1 em {font-style: normal; background: linear-gradient(90deg, #0E7A5C, #34C08F);
    -webkit-background-clip: text; background-clip: text; color: transparent;}
.ms-hero p.lead {color: #5C6B7D; font-size: 1rem; max-width: 470px; margin: 0; line-height: 1.6;}
.ms-hero-chips {display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 0.6rem;}
.ms-hero-chip {display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.38rem 0.75rem; border-radius: 999px;
    background: #FFFFFF; border: 1px solid #DDEDE6; color: #2F5A4C; font-size: 0.8rem; font-weight: 500;
    box-shadow: 0 2px 6px -2px rgba(16, 90, 66, 0.15);}
.ms-hero-chip svg {color: #0E7A5C;}

/* the 3D stage */
.ms-3d {position: relative; height: 330px; margin-top: 0.4rem; perspective: 1100px;}
.ms-3d-art {position: absolute; left: 50%; top: 10px; width: 420px; max-width: 100%; transform: translateX(-50%);
    overflow: visible;}
.ms-float-a {animation: ms-float 6s ease-in-out infinite; transform-origin: center;}
.ms-float-b {animation: ms-float 7s ease-in-out -2s infinite;}
.ms-float-c {animation: ms-float 8s ease-in-out -4s infinite;}
@keyframes ms-float {0%, 100% {transform: translateY(0);} 50% {transform: translateY(-9px);}}
.ms-glass {position: absolute; padding: 0.7rem 0.85rem; border-radius: 14px; background: rgba(255, 255, 255, 0.78);
    -webkit-backdrop-filter: blur(10px); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.9);
    box-shadow: 0 18px 40px -18px rgba(16, 60, 45, 0.35), 0 2px 6px rgba(16, 60, 45, 0.06);
    transform-style: preserve-3d; animation: ms-drift 9s ease-in-out infinite;}
.ms-glass-1 {left: 0; top: 18px; width: 190px; transform: rotateY(16deg) rotateX(6deg); animation-delay: -1s;}
.ms-glass-2 {right: 0; top: 26px; width: 176px; transform: rotateY(-18deg) rotateX(6deg); animation-delay: -4s;}
.ms-glass-3 {left: 50%; bottom: 4px; display: flex; align-items: center; gap: 0.45rem; white-space: nowrap;
    transform: translateX(-50%) rotateX(14deg); color: #2F5A4C; font-size: 0.8rem; font-weight: 600;
    animation-delay: -6s;}
.ms-glass-3 svg {color: #0E7A5C;}
@keyframes ms-drift {0%, 100% {margin-top: 0;} 50% {margin-top: -6px;}}
.ms-glass-k {font-size: 0.68rem; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: #7A8898;}
.ms-glass-v {font-weight: 700; color: #20354A; font-size: 0.92rem; margin: 0.15rem 0 0.45rem 0;}
.ms-glass-scale {position: relative; display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 3px; margin-top: 0.55rem;}
.ms-glass-scale div {height: 7px; border-radius: 999px;}
.ms-glass-scale div:nth-child(1) {background: #D9E3F0;} .ms-glass-scale div:nth-child(2) {background: #F1E2BE;}
.ms-glass-scale div:nth-child(3) {background: #F2D6D6;}
.ms-glass-scale i {position: absolute; left: 76%; top: -4px; width: 4px; height: 15px; border-radius: 3px;
    background: #20354A; box-shadow: 0 0 0 2px #FFFFFF;}
.ms-glass-labels {display: flex; justify-content: space-between; font-size: 0.66rem; color: #9AA8B6; margin-top: 0.3rem;}

/* right: the form on a raised card */
.ms-signin-gap {height: 2.6rem;}
.st-key-login_card {background: #FFFFFF; border: 1px solid #E3EFEA; border-radius: 22px; padding: 2rem 2rem 1.6rem 2rem;
    box-shadow: 0 1px 2px rgba(16, 60, 45, 0.04), 0 30px 60px -30px rgba(16, 60, 45, 0.30),
                0 10px 24px -12px rgba(16, 60, 45, 0.10);}
.ms-signin-badge {display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.3rem 0.7rem; border-radius: 999px;
    background: #ECFDF3; border: 1px solid #ABEFC6; color: #067647; font-size: 0.76rem; font-weight: 600;}
.ms-signin-title {font-family: "Plus Jakarta Sans", Inter, sans-serif; font-size: 1.75rem; font-weight: 800;
    letter-spacing: -0.02em; color: #20354A; margin: 0.9rem 0 0 0;}
.ms-signin-sub {color: #6B7A8C; margin: 0.35rem 0 1.3rem 0;}
.st-key-login_card .stFormSubmitButton button p {color: #FFFFFF !important; font-weight: 600;}
.st-key-login_card .stFormSubmitButton button {height: 2.9rem; font-size: 0.98rem; color: #FFFFFF;
    background: linear-gradient(180deg, #14916E, #0E7A5C); border: none;
    box-shadow: 0 10px 20px -10px rgba(14, 122, 92, 0.7), inset 0 1px 0 rgba(255, 255, 255, 0.2);}
.ms-roles {margin-top: 1.3rem; border: 1px solid #EDF2F0; border-radius: 12px; background: #FAFCFB;}
.ms-role {display: flex; justify-content: space-between; gap: 1rem; padding: 0.6rem 0.9rem;
    border-top: 1px solid #EEF3F1; font-size: 0.84rem;}
.ms-role:first-child {border-top: none;}
.ms-role code {background: #ECFDF3; color: #0B6B50; padding: 0.08rem 0.45rem; border-radius: 6px; font-size: 0.8rem;}
.ms-role span {color: #7A8898; text-align: right;}

@media (max-width: 900px) {
    .ms-hero {padding: 1.6rem;} .ms-hero h1 {font-size: 1.75rem; margin-top: 1.3rem;}
    .ms-3d, .ms-hero-chips {display: none;} .ms-signin-gap {height: 0.6rem;}
    .st-key-login_card {padding: 1.5rem;}
}
@media (prefers-reduced-motion: reduce) {
    .ms-float-a, .ms-float-b, .ms-float-c, .ms-glass {animation: none;}
}
</style>
"""


def apply_styles():
    st.markdown(_CSS, unsafe_allow_html=True)


def apply_login_styles():
    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)


def page_header(title, subtitle="", eyebrow=""):
    eyebrow_html = f'<div class="ms-eyebrow">{escape(eyebrow)}</div>' if eyebrow else ""
    sub_html = f'<p class="ms-subtitle">{escape(subtitle)}</p>' if subtitle else '<div style="height:1rem"></div>'
    st.markdown(f'{eyebrow_html}<h1 class="ms-title">{escape(title)}</h1>{sub_html}', unsafe_allow_html=True)


def welcome(title, subtitle, chip_text, icon_name="heart"):
    """A calm welcome banner for the top of the dashboard."""
    st.markdown(
        f'<div class="ms-welcome"><div class="ms-welcome-left"><div class="ms-welcome-mark">{icon(icon_name, 22)}</div>'
        f'<div><div class="ms-welcome-title">{escape(title)}</div><div class="ms-welcome-sub">{escape(subtitle)}</div>'
        f'</div></div><div class="ms-welcome-chip">{icon("shield", 15)}{escape(chip_text)}</div></div>',
        unsafe_allow_html=True)


def card_title(title, subtitle=""):
    sub = f'<div class="ms-card-sub">{escape(subtitle)}</div>' if subtitle else '<div style="height:0.6rem"></div>'
    st.markdown(f'<div class="ms-card-title">{escape(title)}</div>{sub}', unsafe_allow_html=True)


def label(text):
    st.markdown(f'<div class="ms-label">{escape(text)}</div>', unsafe_allow_html=True)


def kpi(label_text, value, note="", icon_name=None, tone=""):
    """A headline number card. tone: '' | 'danger' | 'brand' | 'teal' (tints the icon only)."""
    value_text = f"{value:,}" if isinstance(value, int) else escape(str(value))
    icon_html = f'<div class="ms-kpi-icon {tone}">{icon(icon_name, 18)}</div>' if icon_name else ""
    note_html = f'<div class="ms-kpi-note">{escape(note)}</div>' if note else ""
    st.markdown(f'<div class="ms-kpi"><div class="ms-kpi-top"><div class="ms-kpi-label">{escape(label_text)}'
                f'</div>{icon_html}</div><div class="ms-kpi-value">{value_text}</div>{note_html}</div>',
                unsafe_allow_html=True)


def severity_pill(severity):
    s = SEVERITY_STYLE.get((severity or "").upper())
    if s is None:
        return f'<span class="ms-pill" style="background:#F6F9F8;color:#516174;border-color:#E8EEF3">' \
               f'{escape(severity or "-")}</span>'
    return (f'<span class="ms-pill" style="background:{s["bg"]};color:{s["text"]};border-color:{s["border"]}">'
            f'<span class="dot" style="background:{s["color"]}"></span>{s["label"]}</span>')


def neutral_pill(text, color="#516174", bg="#F6F9F8", border="#E8EEF3"):
    return (f'<span class="ms-pill" style="background:{bg};color:{color};border-color:{border}">'
            f'{escape(str(text))}</span>')


def success_pill(text):
    return neutral_pill(text, SUCCESS["text"], SUCCESS["bg"], SUCCESS["border"])


def alert_pill(text):
    s = SEVERITY_STYLE["MAJOR"]
    return neutral_pill(text, s["text"], s["bg"], s["border"])


def alert_list(alerts, meta=None):
    """Alerts as a compact list: severity bar, pill, type and medicine, message, optional meta line."""
    rows = []
    for a in alerts:
        sev = (a.get("severity") or "").upper()
        color = SEVERITY_STYLE.get(sev, {}).get("color", "#D5DEE7")
        kind = ALERT_TYPE_LABEL.get(a.get("alert_type"), a.get("alert_type") or "Alert")
        meta_text = meta(a) if meta else ""
        meta_html = f'<div class="ms-alert-meta">{escape(meta_text)}</div>' if meta_text else ""
        rows.append(
            f'<div class="ms-alert"><div class="ms-alert-bar" style="background:{color}"></div>'
            f'<div class="ms-alert-body"><div class="ms-alert-head">{severity_pill(sev)}'
            f'<span class="ms-alert-title">{escape(str(a.get("medication", "")))}</span>'
            f'<span class="ms-muted">· {escape(kind)}</span></div>'
            f'<div class="ms-alert-msg">{escape(str(a.get("message", "")))}</div>{meta_html}</div></div>')
    st.markdown(f'<div class="ms-alerts">{"".join(rows)}</div>', unsafe_allow_html=True)


RISK_BANDS = (("Low", "MINOR", 0.33), ("Medium", "MODERATE", 0.66), ("High", "MAJOR", 1.01))


def risk_band(score):
    return next((name, sev) for name, sev, upper in RISK_BANDS if score < upper)


def risk_meter(score, explain=False):
    """The model's risk score on a calm Low / Medium / High scale with a marker; never colour alone."""
    if score is None:
        st.markdown('<span class="ms-muted">Not scored yet</span>', unsafe_allow_html=True)
        return
    score = min(max(float(score), 0.0), 1.0)
    name, sev = risk_band(score)
    style = SEVERITY_STYLE[sev]
    zones = "".join(f'<div style="background:{SEVERITY_STYLE[s]["border"]}"></div>' for _, s, _ in RISK_BANDS)
    note = ('<div class="ms-scale-note">Estimated probability that an adverse event like this is reported as '
            'serious, from a model trained on openFDA reports. A decision aid, not a diagnosis.</div>'
            if explain else "")
    st.markdown(
        f'<div class="ms-scale" role="meter" aria-label="{name} model risk" aria-valuemin="0" aria-valuemax="100" '
        f'aria-valuenow="{score * 100:.0f}" aria-valuetext="{name}, {score:.0%}">'
        f'<div class="ms-scale-head"><span class="ms-scale-value">{score:.0%}</span>'
        f'<span class="ms-pill" style="background:{style["bg"]};color:{style["text"]};border-color:{style["border"]}">'
        f'<span class="dot" style="background:{style["color"]}"></span>{name} risk</span></div>'
        f'<div class="ms-scale-track">{zones}<div class="ms-scale-marker" style="left:{score * 100:.1f}%"></div></div>'
        f'<div class="ms-scale-labels"><span>Low</span><span>Medium</span><span>High</span></div>{note}</div>',
        unsafe_allow_html=True)


def risk_factors(features):
    """The six model inputs for one alert, as read from the database (age, sex, medicines, interactions, signals)."""
    if not features:
        return
    age, sex, n_drugs, max_sev, n_inter, has_signal = features
    sexes = {0: "Male", 1: "Female"}
    sev_names = {0: "None", 1: "Minor", 2: "Moderate", 3: "Major"}
    items = [("Age", f"{age:.0f} years"), ("Sex", sexes.get(int(sex), "Other")),
             ("Active medicines", f"{int(n_drugs)}"), ("Strongest interaction", sev_names.get(int(max_sev), "-")),
             ("Interacting pairs", f"{int(n_inter)}"), ("Known safety signal", "Yes" if has_signal else "No")]
    st.markdown('<div class="ms-factors">' + "".join(
        f'<div class="ms-factor"><span>{escape(k)}</span><b>{escape(v)}</b></div>' for k, v in items) + "</div>",
        unsafe_allow_html=True)


def chips(items, warn=False, empty="None recorded"):
    if not items:
        st.markdown(f'<span class="ms-muted">{escape(empty)}</span>', unsafe_allow_html=True)
        return
    css = "ms-chip warn" if warn else "ms-chip"
    st.markdown("".join(f'<span class="{css}">{escape(str(i))}</span>' for i in items), unsafe_allow_html=True)


def table(rows, columns):
    """A small static table. columns: list of (key, heading, kind) with kind '' | 'strong' | 'num' | 'html'.
    Values of kind 'html' must already be safe HTML (built by this module); all others are escaped."""
    head = "".join(f"<th>{escape(h)}</th>" for _, h, _ in columns)
    body = []
    for r in rows:
        cells = []
        for key, _, kind in columns:
            value = r.get(key, "")
            text = value if kind == "html" else escape("" if value is None else str(value))
            cells.append(f'<td class="{kind}">{text}</td>')
        body.append("<tr>" + "".join(cells) + "</tr>")
    st.markdown(f'<div class="ms-table-wrap"><table class="ms-table"><thead><tr>{head}</tr></thead>'
                f'<tbody>{"".join(body)}</tbody></table></div>', unsafe_allow_html=True)


def initials(name):
    parts = [p for p in str(name).replace(".", " ").split() if p.lower() not in ("dr", "mr", "mrs", "ms")]
    return escape("".join(p[0] for p in parts[:2]).upper() or "?")


def age_of(dob):
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def empty_state(icon_name, title, text=""):
    """A calm empty state: icon in a soft circle, a short title and one line of help."""
    st.markdown(f'<div class="ms-empty"><div class="ic">{icon(icon_name, 22)}</div><b>{escape(title)}</b>'
                f'<span>{escape(text)}</span></div>', unsafe_allow_html=True)


def bar_list(rows):
    """Ranked horizontal bars. rows: (name, value, note) with the first row as the full-width reference."""
    top = max((v for _, v, _ in rows), default=1) or 1
    html = "".join(
        f'<div class="ms-bar-row"><div class="ms-bar-name">{escape(str(name))}</div>'
        f'<div class="ms-bar-val">{value:,}<small>{escape(note)}</small></div>'
        f'<div class="ms-bar-track"><div class="ms-bar-fill" style="width:{max(4, 100 * value / top):.0f}%"></div>'
        f'</div></div>' for name, value, note in rows)
    st.markdown(f'<div class="ms-bars">{html}</div>', unsafe_allow_html=True)


def risk_pill(alerts):
    """Patient risk from their active alerts: High (any major), Watch (moderate/minor), Clear."""
    severities = {a["severity"] for a in alerts}
    count = f"{len(alerts)} active alert" + ("s" if len(alerts) != 1 else "")
    if "MAJOR" in severities:
        s, text = SEVERITY_STYLE["MAJOR"], f"Needs review · {count}"
    elif severities:
        s, text = SEVERITY_STYLE["MODERATE"], f"Watch · {count}"
    else:
        s, text = SUCCESS, "No active alerts"
    return (f'<span class="ms-risk" style="background:{s["bg"]};color:{s["text"]};border-color:{s["border"]}">'
            f'<span class="dot" style="width:6px;height:6px;border-radius:50%;background:{s["color"]}"></span>'
            f'{text}</span>')
