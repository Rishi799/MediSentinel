"""Shared look and feel for every MediSentinel page: styles, headers, KPI tiles, severity badges.

All text that comes from the database is passed through html.escape before it is placed
inside HTML, so a name such as "<script>" is shown as text and never run.
"""

from datetime import date
from html import escape

import streamlit as st

# Severity colours (status palette) - always shown together with an icon and a label,
# so the meaning never depends on colour alone.
SEVERITY_STYLE = {
    "MAJOR":    {"color": "#D03B3B", "bg": "#FDECEC", "icon": "⛔", "label": "Major"},
    "MODERATE": {"color": "#C2410C", "bg": "#FFF1E6", "icon": "⚠️", "label": "Moderate"},
    "MINOR":    {"color": "#1C5CAB", "bg": "#E8F1FC", "icon": "ℹ️", "label": "Minor"},
}
ALERT_TYPE_LABEL = {"INTERACTION": "Drug interaction", "CONTRA": "Contraindication", "ALLERGY": "Allergy"}
ROLE_LABEL = {"doctor": "Doctor", "pharmacist": "Pharmacist", "admin": "Administrator"}
CHART_BLUE = "#3987E5"  # single-series charts (sequential blue, step 400)

_CSS = """
<style>
.block-container {padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1280px;}
h1, h2, h3 {letter-spacing: -0.01em;}
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] span {font-weight: 500;}

.ms-header {display: flex; align-items: center; gap: 0.9rem; margin-bottom: 1.2rem;}
.ms-header .ms-icon {width: 46px; height: 46px; border-radius: 12px; display: flex;
    align-items: center; justify-content: center; font-size: 1.45rem;
    background: linear-gradient(135deg, #0F766E, #14B8A6); color: #fff; flex-shrink: 0;}
.ms-header h1 {font-size: 1.65rem; font-weight: 700; margin: 0; padding: 0; line-height: 1.2;}
.ms-header p {margin: 0.15rem 0 0 0; color: #64748B; font-size: 0.95rem;}

.ms-kpi {background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px;
    padding: 1rem 1.1rem; height: 100%; box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);}
.ms-kpi .ms-kpi-label {color: #64748B; font-size: 0.8rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.04em;}
.ms-kpi .ms-kpi-value {font-size: 1.9rem; font-weight: 700; color: #0F172A; line-height: 1.2;
    margin-top: 0.25rem; font-variant-numeric: tabular-nums;}
.ms-kpi .ms-kpi-note {color: #64748B; font-size: 0.8rem; margin-top: 0.15rem;}
.ms-kpi.ms-critical {border-left: 4px solid #D03B3B;}
.ms-kpi.ms-accent {border-left: 4px solid #0F766E;}

.ms-badge {display: inline-flex; align-items: center; gap: 0.3rem; padding: 0.12rem 0.55rem;
    border-radius: 999px; font-size: 0.75rem; font-weight: 700; letter-spacing: 0.02em;}
.ms-chip {display: inline-block; padding: 0.15rem 0.6rem; margin: 0 0.3rem 0.35rem 0;
    border-radius: 999px; font-size: 0.82rem; background: #EEF2F6; color: #0F172A;
    border: 1px solid #E2E8F0;}
.ms-chip.ms-warn {background: #FDECEC; border-color: #F5C2C2; color: #8A1C1C;}
.ms-muted {color: #64748B; font-size: 0.85rem;}

.ms-alert {border: 1px solid #E2E8F0; border-left-width: 5px; border-radius: 12px;
    padding: 0.75rem 0.95rem; margin-bottom: 0.6rem; background: #FFFFFF;}
.ms-alert .ms-alert-top {display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;}
.ms-alert .ms-alert-title {font-weight: 650; color: #0F172A;}
.ms-alert .ms-alert-msg {color: #334155; margin-top: 0.3rem; font-size: 0.92rem;}
.ms-alert .ms-alert-meta {color: #64748B; font-size: 0.78rem; margin-top: 0.3rem;}

.ms-login-brand {text-align: center; margin: 1.5rem 0 1.2rem 0;}
.ms-login-brand .ms-logo {width: 64px; height: 64px; margin: 0 auto 0.7rem auto; border-radius: 18px;
    display: flex; align-items: center; justify-content: center; font-size: 2rem; color: #fff;
    background: linear-gradient(135deg, #0F766E, #14B8A6);
    box-shadow: 0 8px 24px rgba(15, 118, 110, 0.25);}
.ms-login-brand h1 {font-size: 2rem; font-weight: 800; margin: 0;}
.ms-login-brand p {color: #64748B; margin: 0.3rem 0 0 0;}
.ms-feature {display: flex; gap: 0.6rem; align-items: flex-start; margin-bottom: 0.7rem;}
.ms-feature .ms-feature-icon {font-size: 1.15rem; line-height: 1.4;}
.ms-feature b {color: #0F172A;}
.ms-feature span {color: #475569; font-size: 0.9rem;}
.ms-footer {text-align: center; color: #94A3B8; font-size: 0.78rem; margin-top: 2rem;}
</style>
"""


def apply_styles():
    st.markdown(_CSS, unsafe_allow_html=True)


def page_header(icon, title, subtitle=""):
    sub = f"<p>{escape(subtitle)}</p>" if subtitle else ""
    st.markdown(f'<div class="ms-header"><div class="ms-icon">{icon}</div>'
                f'<div><h1>{escape(title)}</h1>{sub}</div></div>', unsafe_allow_html=True)


def kpi(label, value, note="", tone=""):
    """A headline number tile. tone: '' | 'critical' | 'accent'."""
    css = f"ms-kpi ms-{tone}" if tone else "ms-kpi"
    note_html = f'<div class="ms-kpi-note">{escape(note)}</div>' if note else ""
    value_text = f"{value:,}" if isinstance(value, int) else escape(str(value))
    st.markdown(f'<div class="{css}"><div class="ms-kpi-label">{escape(label)}</div>'
                f'<div class="ms-kpi-value">{value_text}</div>{note_html}</div>', unsafe_allow_html=True)


def severity_badge(severity):
    s = SEVERITY_STYLE.get((severity or "").upper())
    if s is None:
        return f'<span class="ms-badge" style="background:#EEF2F6;color:#334155">{escape(severity or "-")}</span>'
    return (f'<span class="ms-badge" style="background:{s["bg"]};color:{s["color"]}">'
            f'{s["icon"]} {s["label"].upper()}</span>')


def alert_card(alert, meta=""):
    """One safety alert as a card: severity badge, type, medicine, message."""
    severity = (alert.get("severity") or "").upper()
    color = SEVERITY_STYLE.get(severity, {}).get("color", "#94A3B8")
    kind = ALERT_TYPE_LABEL.get(alert.get("alert_type"), alert.get("alert_type") or "Alert")
    meta_html = f'<div class="ms-alert-meta">{escape(meta)}</div>' if meta else ""
    st.markdown(
        f'<div class="ms-alert" style="border-left-color:{color}">'
        f'<div class="ms-alert-top">{severity_badge(severity)}'
        f'<span class="ms-alert-title">{escape(kind)} · {escape(str(alert.get("medication", "")))}</span></div>'
        f'<div class="ms-alert-msg">{escape(str(alert.get("message", "")))}</div>{meta_html}</div>',
        unsafe_allow_html=True)


def chips(items, warn=False, empty="None recorded"):
    if not items:
        st.markdown(f'<span class="ms-muted">{escape(empty)}</span>', unsafe_allow_html=True)
        return
    css = "ms-chip ms-warn" if warn else "ms-chip"
    st.markdown("".join(f'<span class="{css}">{escape(str(i))}</span>' for i in items),
                unsafe_allow_html=True)


def age_of(dob):
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
