import matplotlib.pyplot as plt
import numpy as np

# Set overall aesthetics
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.sans-serif'] = 'Arial'
plt.rcParams['font.family'] = 'sans-serif'

# 1. ADR Healthcare Burden Statistics Chart
fig, ax1 = plt.subplots(figsize=(8, 4.5), dpi=200)
categories = ['Adverse Drug\nReactions (ADRs)', 'Preventable\nMedication Errors', 'Emergency Dept.\nVisits (Annual)', 'Fatal Hospital\nEvents (Annual)']
colors = ['#1E3A8A', '#EF4444', '#0EA5E9', '#D97706']

bars = ax1.bar(categories, [6.7, 52.0, 13.0, 10.6], color=colors, width=0.55, edgecolor='none', zorder=3)
ax1.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)
ax1.set_title('Global Clinical Impact of Medication Incompatibilities (WHO & FDA Studies)', fontsize=12, fontweight='bold', pad=15, color='#0F172A')
ax1.set_ylabel('Impact Scale Index', fontsize=10, fontweight='bold', color='#334155')

annotations = ['6.7% Hospital\nAdmissions', '52% Readily\nPreventable', '1.3 Million\nOutpatients/yr', '106k+ Deaths\nper Year (US)']
for bar, text in zip(bars, annotations):
    yval = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2.0, yval + 1.2, text, ha='center', va='bottom', fontsize=9, fontweight='bold', color='#1E293B')

ax1.set_ylim(0, 65)
plt.tight_layout()
plt.savefig('docs/chart_adr_stats.png', bbox_inches='tight')
plt.close()

# 2. Project Timeline Gantt Chart
fig, ax = plt.subplots(figsize=(9, 4), dpi=200)
tasks = [
    'Phase 1: Problem Definition & SRS (W1-2)',
    'Phase 1: Polyglot Architecture & Normalization (W3-4)',
    'Phase 1: SQL Schema, Triggers & Ingestion (W5-7)',
    'Phase 1: Streamlit UI & Role Authentication (W8)',
    'Phase 2: NLP Entity Extraction & Pipelines (W9-10)',
    'Phase 2: Signal Mining (PRR/ROR) & Risk ML (W11-12)',
    'Phase 2: Final Validation, Paper & Closure (W13)'
]
start_weeks = [1, 3, 5, 8, 9, 11, 13]
durations =   [2, 2, 3, 1, 2, 2, 1]
colors = ['#0284C7', '#0EA5E9', '#38BDF8', '#10B981', '#F59E0B', '#EF4444', '#6366F1']

y_pos = np.arange(len(tasks))
ax.barh(y_pos, durations, left=start_weeks, color=colors, height=0.45, align='center', edgecolor='none', zorder=3)
ax.set_yticks(y_pos)
ax.set_yticklabels(tasks, fontsize=9, fontweight='bold', color='#1E293B')
ax.invert_yaxis()
ax.set_xlabel('Project Schedule (Academic Weeks)', fontsize=10, fontweight='bold', color='#334155')
ax.set_xlim(0, 15)
ax.set_xticks(range(1, 15))
ax.grid(axis='x', linestyle='--', alpha=0.5, zorder=0)
ax.set_title('MediSentinel Comprehensive Development Roadmap (Weeks 1 to 13)', fontsize=11, fontweight='bold', pad=12, color='#0F172A')

plt.tight_layout()
plt.savefig('docs/chart_gantt.png', bbox_inches='tight')
plt.close()

# 3. PRR and Disproportionality Signal Mining Matrix
fig, ax = plt.subplots(figsize=(7, 3.8), dpi=200)
matrix_data = [
    ["Target Drug (i)", "Adverse Reaction (j)", "All Other Reactions", "Total Drug Reports"],
    ["Drug of Interest (X)", "A (Observed)", "B", "A + B"],
    ["All Other Drugs", "C", "D", "C + D"],
    ["Total Database", "A + C", "B + D", "N (Total Reports)"]
]
table = ax.table(cellText=matrix_data, loc='center', cellLoc='center')
table.auto_set_font_size(False)
table.set_fontsize(9)
table.scale(1.2, 1.8)

for i in range(4):
    for j in range(4):
        cell = table[i, j]
        if i == 0 or j == 0:
            cell.set_facecolor('#1E3A8A')
            cell.get_text().set_color('white')
            cell.get_text().set_weight('bold')
        elif i == 1 and j == 1:
            cell.set_facecolor('#FEE2E2')
            cell.get_text().set_color('#B91C1C')
            cell.get_text().set_weight('bold')
        else:
            cell.set_facecolor('#F8FAFC')
ax.axis('off')
ax.set_title('2x2 Pharmacovigilance Disproportionality Contingency Table\nPRR = [A / (A+B)] / [C / (C+D)]   |   ROR = (A * D) / (B * C)', fontsize=10, fontweight='bold', pad=10, color='#0F172A')
plt.tight_layout()
plt.savefig('docs/chart_prr_math.png', bbox_inches='tight')
plt.close()
print("Charts generated successfully!")

