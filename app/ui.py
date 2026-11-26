"""Shared look and feel for every MediSentinel page: styles, icons, page headers, KPI cards,
severity pills, alert lists and small tables.

All text that comes from the database goes through html.escape before it is placed inside
HTML, so a name such as "<script>" is shown as text and never run.
"""

from datetime import date
from html import escape

import streamlit as st

# ---------- design tokens ----------
BRAND = "#0E7A5C"
INK = "#101828"
MUTED = "#667085"
CHART_BLUE = "#1570EF"

# Severity = status colours; always shown with a dot and a word, never colour alone.
SEVERITY_STYLE = {
    "MAJOR":    {"color": "#D92D20", "bg": "#FEF3F2", "text": "#B42318", "border": "#FECDCA", "label": "Major"},
    "MODERATE": {"color": "#DC6803", "bg": "#FFFAEB", "text": "#B54708", "border": "#FEDF89", "label": "Moderate"},
    "MINOR":    {"color": "#1570EF", "bg": "#EFF8FF", "text": "#175CD3", "border": "#B2DDFF", "label": "Minor"},
}
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
}


def icon(name, size=18, color="currentColor", stroke=2):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" '
            f'fill="none" stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" '
            f'stroke-linejoin="round" style="flex-shrink:0">{_ICONS[name]}</svg>')


_CSS = """
<style>
html, body, [class*="css"] {-webkit-font-smoothing: antialiased;}
header[data-testid="stHeader"] {background: transparent;}
.block-container {padding-top: 2.4rem; padding-bottom: 4rem; max-width: 1240px;}
h1, h2, h3, h4, h5 {letter-spacing: -0.015em; color: #101828;}
p, li {color: #344054;}

/* sidebar */
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] {border-radius: 6px; margin: 1px 0;}
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] span {font-weight: 500; font-size: 0.92rem;}
[data-testid="stSidebar"] [data-testid="stNavSectionHeader"] {font-size: 0.7rem; letter-spacing: 0.06em;
    text-transform: uppercase; color: #98A2B3; font-weight: 600;}

/* surfaces: bordered containers (keyed card_N) and forms become white cards */
.stVerticalBlock[class*="st-key-card_"], [data-testid="stForm"] {background: #FFFFFF;
    border-color: #EAECF0 !important; border-radius: 12px; box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05);
    padding: 1.15rem 1.25rem;}
.stVerticalBlock[class*="st-key-card_"] [data-testid="stForm"] {box-shadow: none; padding: 0;}
.stTabs [data-baseweb="tab-list"] {gap: 1.4rem; border-bottom: 1px solid #EAECF0;}
.stTabs [data-baseweb="tab"] {padding: 0.55rem 0; font-weight: 500;}
.stButton button, .stFormSubmitButton button {font-weight: 600;}
[data-testid="stDataFrame"] {border-radius: 8px;}

<<<<<<< HEAD
/* page header */
.ms-eyebrow {font-size: 0.75rem; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase;
    color: #0E7A5C; margin-bottom: 0.25rem;}
.ms-title {font-size: 1.75rem; font-weight: 700; letter-spacing: -0.02em; color: #101828; margin: 0;
    line-height: 1.25;}
.ms-subtitle {color: #667085; font-size: 0.97rem; margin: 0.35rem 0 1.4rem 0; max-width: 760px;}
=======
.ms-badge {display: inline-flex; align-items: center; gap: 0.3rem; padding: 0.12rem 0.55rem;
    border-radius: 999px; font-size: 0.75rem; font-weight: 700; letter-spacing: 0.02em;}
.ms-chip {display: inline-block; padding: 0.15rem 0.6rem; margin: 0 0.3rem 0.35rem 0;
    border-radius: 999px; font-size: 0.82rem; background: #EEF2F6; color: #0F172A;
    border: 1px solid #E2E8F0;}
.ms-chip.ms-warn {background: #FDECEC; border-color: #F5C2C2; color: #8A1C1C;}
.ms-muted {color: #64748B; font-size: 0.85rem;}
div.stVerticalBlock[class*="st-key-card_"] {background: #FFFFFF; border-radius: 0.6rem;}
>>>>>>> origin/main

/* KPI cards */
.ms-kpi {background: #FFFFFF; border: 1px solid #EAECF0; border-radius: 12px; padding: 1.05rem 1.15rem;
    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05); height: 100%;}
.ms-kpi-top {display: flex; justify-content: space-between; align-items: flex-start;}
.ms-kpi-label {color: #475467; font-size: 0.85rem; font-weight: 500;}
.ms-kpi-icon {width: 34px; height: 34px; border-radius: 8px; display: flex; align-items: center;
    justify-content: center; border: 1px solid #EAECF0; color: #475467; background: #FFFFFF;}
.ms-kpi-icon.danger {color: #D92D20; background: #FEF3F2; border-color: #FECDCA;}
.ms-kpi-icon.brand {color: #0E7A5C; background: #ECFDF3; border-color: #ABEFC6;}
.ms-kpi-value {font-size: 1.85rem; font-weight: 700; color: #101828; letter-spacing: -0.02em;
    margin-top: 0.35rem; font-variant-numeric: tabular-nums; line-height: 1.15;}
.ms-kpi-note {color: #667085; font-size: 0.8rem; margin-top: 0.2rem;}

/* card headings inside containers */
.ms-card-title {font-size: 1rem; font-weight: 600; color: #101828; margin: 0;}
.ms-card-sub {font-size: 0.84rem; color: #667085; margin: 0.15rem 0 0.8rem 0;}

/* pills and chips */
.ms-pill {display: inline-flex; align-items: center; gap: 0.38rem; padding: 0.12rem 0.55rem 0.12rem 0.45rem;
    border-radius: 999px; font-size: 0.75rem; font-weight: 600; border: 1px solid; white-space: nowrap;}
.ms-pill .dot {width: 6px; height: 6px; border-radius: 50%;}
.ms-chip {display: inline-block; padding: 0.16rem 0.6rem; margin: 0 0.35rem 0.4rem 0; border-radius: 6px;
    font-size: 0.82rem; background: #F9FAFB; color: #344054; border: 1px solid #EAECF0; font-weight: 500;}
.ms-chip.warn {background: #FEF3F2; border-color: #FECDCA; color: #B42318;}
.ms-muted {color: #98A2B3; font-size: 0.85rem;}
.ms-label {font-size: 0.75rem; font-weight: 600; color: #667085; text-transform: uppercase;
    letter-spacing: 0.05em; margin: 0.9rem 0 0.4rem 0;}

/* alert list */
.ms-alerts {display: flex; flex-direction: column;}
.ms-alert {display: flex; gap: 0.8rem; padding: 0.8rem 0; border-top: 1px solid #F2F4F7;}
.ms-alert:first-child {border-top: none; padding-top: 0.2rem;}
.ms-alert-bar {width: 3px; border-radius: 3px; flex-shrink: 0;}
.ms-alert-body {flex: 1; min-width: 0;}
.ms-alert-head {display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;}
.ms-alert-title {font-weight: 600; color: #101828; font-size: 0.92rem;}
.ms-alert-msg {color: #475467; font-size: 0.88rem; margin-top: 0.2rem;}
.ms-alert-meta {color: #98A2B3; font-size: 0.78rem; margin-top: 0.2rem;}

/* simple tables */
.ms-table {width: 100%; border-collapse: collapse; font-size: 0.88rem;}
.ms-table th {text-align: left; font-weight: 500; color: #667085; font-size: 0.78rem; padding: 0.55rem 0.75rem;
    background: #F9FAFB; border-bottom: 1px solid #EAECF0;}
.ms-table td {padding: 0.7rem 0.75rem; border-bottom: 1px solid #F2F4F7; color: #344054; vertical-align: top;}
.ms-table tr:last-child td {border-bottom: none;}
.ms-table td.strong {color: #101828; font-weight: 500;}
.ms-table td.num {font-variant-numeric: tabular-nums; white-space: nowrap;}
.ms-table-wrap {border: 1px solid #EAECF0; border-radius: 10px; overflow: hidden; background: #FFFFFF;}

/* profile */
.ms-avatar {width: 44px; height: 44px; border-radius: 50%; background: #ECFDF3; color: #0E7A5C;
    display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 1rem;
    border: 1px solid #ABEFC6; flex-shrink: 0;}
.ms-profile-head {display: flex; gap: 0.8rem; align-items: center;}
.ms-profile-name {font-weight: 650; font-size: 1.1rem; color: #101828;}
.ms-profile-meta {color: #667085; font-size: 0.85rem;}
.ms-facts {display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem; margin-top: 0.9rem;}
.ms-fact {background: #F9FAFB; border: 1px solid #EAECF0; border-radius: 8px; padding: 0.55rem 0.75rem;}
.ms-fact-k {font-size: 0.75rem; color: #667085;}
.ms-fact-v {font-weight: 600; color: #101828; font-size: 0.92rem;}

/* motion and interaction polish */
.stVerticalBlock[class*="st-key-card_"] {transition: box-shadow 0.18s ease, transform 0.18s ease;}
.stVerticalBlock[class*="st-key-card_"]:hover {box-shadow: 0 4px 14px rgba(16, 24, 40, 0.07);}
.ms-kpi {transition: box-shadow 0.18s ease, transform 0.18s ease;}
.ms-kpi:hover {box-shadow: 0 6px 16px rgba(16, 24, 40, 0.08); transform: translateY(-1px);}
.ms-table tbody tr {transition: background 0.12s ease;}
.ms-table tbody tr:hover td {background: #F9FAFB;}
.stButton button, .stFormSubmitButton button, [data-testid="stPageLink"] a {transition: all 0.15s ease;}
.stButton button[kind="primary"]:hover, .stFormSubmitButton button[kind="primaryFormSubmit"]:hover {
    box-shadow: 0 4px 12px rgba(14, 122, 92, 0.3); transform: translateY(-1px);}
.stTabs [data-baseweb="tab-highlight"] {background: #0E7A5C; height: 2px;}
::-webkit-scrollbar {width: 10px; height: 10px;}
::-webkit-scrollbar-thumb {background: #D0D5DD; border-radius: 8px; border: 2px solid #F6F7F9;}
::-webkit-scrollbar-thumb:hover {background: #98A2B3;}
::-webkit-scrollbar-track {background: transparent;}

/* empty states */
.ms-empty {display: flex; flex-direction: column; align-items: center; text-align: center; padding: 1.6rem 1rem;}
.ms-empty .ic {width: 48px; height: 48px; border-radius: 50%; background: #ECFDF3; color: #0E7A5C;
    display: flex; align-items: center; justify-content: center; margin-bottom: 0.7rem;
    box-shadow: 0 0 0 8px #F6FEF9;}
.ms-empty b {color: #101828; font-size: 0.95rem;}
.ms-empty span {color: #667085; font-size: 0.85rem; margin-top: 0.2rem; max-width: 260px;}

/* bar list (ranked values) */
.ms-bars {display: flex; flex-direction: column; gap: 0.55rem;}
.ms-bar-row {display: grid; grid-template-columns: 1fr auto; gap: 0.3rem 0.8rem; align-items: center;}
.ms-bar-name {font-size: 0.88rem; color: #101828; font-weight: 500; white-space: nowrap; overflow: hidden;
    text-overflow: ellipsis;}
.ms-bar-val {font-size: 0.82rem; color: #475467; font-variant-numeric: tabular-nums; white-space: nowrap;}
.ms-bar-val small {color: #98A2B3; margin-left: 0.35rem;}
.ms-bar-track {grid-column: 1 / span 2; height: 6px; border-radius: 999px; background: #F2F4F7; overflow: hidden;}
.ms-bar-fill {height: 100%; border-radius: 999px; background: linear-gradient(90deg, #0E7A5C, #17B26A);}

/* risk pill */
.ms-risk {display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.2rem 0.65rem; border-radius: 999px;
    font-size: 0.78rem; font-weight: 600; border: 1px solid;}

/* sidebar system status */
.ms-status {margin-top: 1.1rem; padding-top: 0.9rem; border-top: 1px solid #EAECF0;}
.ms-status-title {font-size: 0.7rem; letter-spacing: 0.06em; text-transform: uppercase; color: #98A2B3;
    font-weight: 600; margin-bottom: 0.45rem;}
.ms-status-row {display: flex; align-items: center; gap: 0.5rem; font-size: 0.84rem; color: #344054; padding: 0.18rem 0;}
.ms-status-dot {width: 7px; height: 7px; border-radius: 50%; box-shadow: 0 0 0 3px rgba(23, 178, 106, 0.15);}
.ms-status-val {margin-left: auto; color: #667085; font-size: 0.8rem;}
.ms-status-note {font-size: 0.76rem; color: #98A2B3; margin-top: 0.55rem; line-height: 1.4;}

/* sidebar account */
.ms-account {display: flex; align-items: center; gap: 0.65rem; padding: 0.7rem 0.75rem; border: 1px solid #EAECF0;
    border-radius: 10px; background: #F9FAFB; margin-bottom: 0.5rem;}
.ms-account .ms-avatar {width: 34px; height: 34px; font-size: 0.85rem;}
.ms-account-name {font-weight: 600; color: #101828; font-size: 0.9rem; line-height: 1.2;}
.ms-account-meta {color: #667085; font-size: 0.78rem;}
</style>
"""

_LOGIN_CSS = """
<style>
section[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {display: none;}
[data-testid="stForm"] {background: transparent; box-shadow: none; padding: 0;}
.block-container {max-width: 1180px; padding-top: 2.2rem;}
.ms-hero {position: relative; overflow: hidden; border-radius: 18px; padding: 2.4rem 2.4rem 2rem 2.4rem;
    min-height: 600px; color: #FFFFFF; display: flex; flex-direction: column;
    background: radial-gradient(120% 90% at 0% 0%, #0E7A5C 0%, rgba(14, 122, 92, 0) 55%),
                radial-gradient(90% 70% at 100% 100%, #134E48 0%, rgba(19, 78, 72, 0) 60%), #0B1424;}
.ms-hero::before {content: ""; position: absolute; inset: 0; pointer-events: none;
    background-image: radial-gradient(rgba(255, 255, 255, 0.10) 1px, transparent 1px);
    background-size: 22px 22px; mask-image: linear-gradient(180deg, rgba(0,0,0,0.9), transparent 70%);}
.ms-hero > * {position: relative;}
.ms-hero-brand {display: flex; align-items: center; gap: 0.6rem; font-weight: 700; font-size: 1.05rem;}
.ms-hero-mark {width: 34px; height: 34px; border-radius: 9px; background: rgba(255, 255, 255, 0.12);
    border: 1px solid rgba(255, 255, 255, 0.18); display: flex; align-items: center; justify-content: center;}
.ms-hero h1 {color: #FFFFFF; font-size: 2.3rem; line-height: 1.15; letter-spacing: -0.03em; font-weight: 700;
    margin: 3.2rem 0 0.9rem 0;}
.ms-hero p.lead {color: rgba(255, 255, 255, 0.72); font-size: 1.02rem; max-width: 460px; margin: 0;}
.ms-hero-list {margin-top: 2.2rem; display: flex; flex-direction: column; gap: 1.05rem;}
.ms-hero-item {display: flex; gap: 0.8rem; align-items: flex-start;}
.ms-hero-item .ic {width: 34px; height: 34px; border-radius: 9px; background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.14); display: flex; align-items: center; justify-content: center;
    color: #6CE9A6; flex-shrink: 0;}
.ms-hero-item b {color: #FFFFFF; font-weight: 600; font-size: 0.95rem;}
.ms-hero-item span {color: rgba(255, 255, 255, 0.65); font-size: 0.88rem;}
.ms-hero-foot {margin-top: auto; padding-top: 2rem; color: rgba(255, 255, 255, 0.5); font-size: 0.78rem;}
.ms-signin-title {font-size: 1.6rem; font-weight: 700; letter-spacing: -0.02em; color: #101828; margin: 0;}
.ms-signin-sub {color: #667085; margin: 0.35rem 0 1.4rem 0;}
.ms-roles {margin-top: 1.4rem; border: 1px solid #EAECF0; border-radius: 10px; background: #FFFFFF;}
.ms-role {display: flex; justify-content: space-between; gap: 1rem; padding: 0.6rem 0.85rem;
    border-top: 1px solid #F2F4F7; font-size: 0.85rem;}
.ms-role:first-child {border-top: none;}
.ms-role code {background: #F2F4F7; color: #101828; padding: 0.05rem 0.4rem; border-radius: 5px; font-size: 0.8rem;}
.ms-role span {color: #667085; text-align: right;}
</style>
"""


def apply_styles():
    st.markdown(_CSS, unsafe_allow_html=True)


<<<<<<< HEAD
def apply_login_styles():
    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)
=======
def page_header(icon, title, subtitle=""):
    sub = f"<p>{escape(subtitle)}</p>" if subtitle else ""
    mark = f'<div class="ms-icon">{icon}</div>' if icon else ""
    st.markdown(f'<div class="ms-header">{mark}'
                f'<div><h1>{escape(title)}</h1>{sub}</div></div>', unsafe_allow_html=True)
>>>>>>> origin/main


def page_header(title, subtitle="", eyebrow=""):
    eyebrow_html = f'<div class="ms-eyebrow">{escape(eyebrow)}</div>' if eyebrow else ""
    sub_html = f'<p class="ms-subtitle">{escape(subtitle)}</p>' if subtitle else '<div style="height:1rem"></div>'
    st.markdown(f'{eyebrow_html}<h1 class="ms-title">{escape(title)}</h1>{sub_html}', unsafe_allow_html=True)


def card_title(title, subtitle=""):
    sub = f'<div class="ms-card-sub">{escape(subtitle)}</div>' if subtitle else '<div style="height:0.6rem"></div>'
    st.markdown(f'<div class="ms-card-title">{escape(title)}</div>{sub}', unsafe_allow_html=True)


def label(text):
    st.markdown(f'<div class="ms-label">{escape(text)}</div>', unsafe_allow_html=True)


def kpi(label_text, value, note="", icon_name=None, tone=""):
    """A headline number card. tone: '' | 'danger' | 'brand' (tints the icon only)."""
    value_text = f"{value:,}" if isinstance(value, int) else escape(str(value))
    icon_html = f'<div class="ms-kpi-icon {tone}">{icon(icon_name, 17)}</div>' if icon_name else ""
    note_html = f'<div class="ms-kpi-note">{escape(note)}</div>' if note else ""
    st.markdown(f'<div class="ms-kpi"><div class="ms-kpi-top"><div class="ms-kpi-label">{escape(label_text)}'
                f'</div>{icon_html}</div><div class="ms-kpi-value">{value_text}</div>{note_html}</div>',
                unsafe_allow_html=True)


def severity_pill(severity):
    s = SEVERITY_STYLE.get((severity or "").upper())
    if s is None:
        return f'<span class="ms-pill" style="background:#F9FAFB;color:#344054;border-color:#EAECF0">' \
               f'{escape(severity or "-")}</span>'
    return (f'<span class="ms-pill" style="background:{s["bg"]};color:{s["text"]};border-color:{s["border"]}">'
            f'<span class="dot" style="background:{s["color"]}"></span>{s["label"]}</span>')


def neutral_pill(text, color="#344054", bg="#F9FAFB", border="#EAECF0"):
    return (f'<span class="ms-pill" style="background:{bg};color:{color};border-color:{border}">'
            f'{escape(str(text))}</span>')


def alert_list(alerts, meta=None):
    """Alerts as a compact list: severity bar, pill, type and medicine, message, optional meta line."""
    rows = []
    for a in alerts:
        sev = (a.get("severity") or "").upper()
        color = SEVERITY_STYLE.get(sev, {}).get("color", "#D0D5DD")
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


def risk_meter(score):
    """Show a model score with an accessible percentage and a named band."""
    if score is None:
        st.caption("Not scored yet")
        return
    score = float(score)
    if score < 0.33:
        label, severity = "Low", "MINOR"
    elif score < 0.66:
        label, severity = "Medium", "MODERATE"
    else:
        label, severity = "High", "MAJOR"
    color = SEVERITY_STYLE[severity]["color"]
    percentage = f"{score:.1%}"
    st.markdown(
        f'<div style="display:grid;gap:0.32rem;padding:0.2rem 0 0.55rem">'
        f'<span style="color:{color};font-size:0.85rem;font-weight:650">'
        f'{label} · {percentage}</span>'
        f'<div role="meter" aria-label="{label} model score" aria-valuemin="0" '
        f'aria-valuemax="100" aria-valuenow="{score * 100:.1f}" '
        f'aria-valuetext="{label} {percentage}" '
        f'style="height:0.42rem;border-radius:1rem;background:#E2E8F0;overflow:hidden">'
        f'<div style="height:100%;width:{percentage};background:{color}"></div></div></div>',
        unsafe_allow_html=True,
    )


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
    if "MAJOR" in severities:
        s, label = SEVERITY_STYLE["MAJOR"], f"High risk · {len(alerts)} active alert" + ("s" if len(alerts) != 1 else "")
    elif severities:
        s, label = SEVERITY_STYLE["MODERATE"], f"Watch · {len(alerts)} active alert" + ("s" if len(alerts) != 1 else "")
    else:
        s, label = {"bg": "#ECFDF3", "text": "#067647", "border": "#ABEFC6", "color": "#17B26A"}, "No active alerts"
    return (f'<span class="ms-risk" style="background:{s["bg"]};color:{s["text"]};border-color:{s["border"]}">'
            f'<span class="dot" style="width:6px;height:6px;border-radius:50%;background:{s["color"]}"></span>'
            f'{label}</span>')
