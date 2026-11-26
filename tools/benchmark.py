"""Index and trigger benchmarks for MediSentinel on a large synthetic workload.

Everything runs inside ONE transaction that is rolled back at the end, so the database is left unchanged:
  1. bulk-load 20,000 patients, 100,000 prescriptions and ~300,000 items (trigger paused for the load),
  2. EXPLAIN ANALYZE the queries in sql/benchmark.sql with the indexes, then with them dropped,
  3. time single prescription-item inserts with the safety trigger on and off,
  4. write reports/benchmark_results.md.

Needs the PostgreSQL superuser (indexes belong to it): set PGPASSWORD or type it when asked.
Run:  python tools/benchmark.py
"""
import getpass
import os
import re
import statistics
import sys
import time
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from medisentinel import config  # noqa: E402

PATIENTS, PRESCRIPTIONS, ITEMS_PER_RX, RUNS, TRIGGER_INSERTS = 20_000, 100_000, 3, 5, 300
INDEXES = ["idx_presc_patient", "idx_item_med", "idx_interaction"]


def load_queries():
    text = (ROOT / "sql" / "benchmark.sql").read_text(encoding="utf-8")
    parts = re.split(r"^-- name: (.+)$", text, flags=re.M)[1:]
    return [(parts[i].strip(), parts[i + 1].strip().rstrip(";")) for i in range(0, len(parts), 2)]


def plan_nodes(node, out):
    """Scan nodes of a JSON plan, e.g. 'Index Scan on prescription (idx_presc_patient)'."""
    if "Relation Name" in node:
        index = f" ({node['Index Name']})" if node.get("Index Name") else ""
        out.append(f"{node['Node Type']} on {node['Relation Name']}{index}")
    elif node.get("Index Name"):  # e.g. the Bitmap Index Scan under a Bitmap Heap Scan
        out.append(f"{node['Node Type']} ({node['Index Name']})")
    for child in node.get("Plans", []):
        plan_nodes(child, out)
    return out


def measure(cur, sql, params):
    times, nodes = [], []
    for _ in range(RUNS):
        cur.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql, params)
        plan = cur.fetchone()["QUERY PLAN"][0]
        times.append(plan["Execution Time"])
        nodes = plan_nodes(plan["Plan"], [])
    return statistics.median(times), nodes


def bulk_load(cur):
    cur.execute("ALTER TABLE Prescription_Item DISABLE TRIGGER trg_medication_safety")
    cur.execute("""INSERT INTO Patient(full_name, date_of_birth, gender, renal_function, hepatic_function)
                   SELECT 'Benchmark patient ' || g, DATE '1940-01-01' + (g * 7 %% 25000),
                          (ARRAY['M','F','O'])[1 + g %% 3], 'normal', 'normal'
                   FROM generate_series(1, %s) g""", (PATIENTS,))
    # ids from one INSERT are consecutive, but the sequence may have skipped numbers before it
    cur.execute("SELECT min(patient_id) AS m FROM Patient WHERE full_name LIKE 'Benchmark patient %%'")
    first = cur.fetchone()["m"]
    cur.execute("""INSERT INTO Prescription(patient_id, doctor_id)
                   SELECT %s + (g %% %s), d.ids[1 + g %% cardinality(d.ids)]
                   FROM generate_series(1, %s) g, (SELECT array_agg(doctor_id) AS ids FROM Doctor) d""",
                (first, PATIENTS, PRESCRIPTIONS))
    cur.execute("""INSERT INTO Prescription_Item(prescription_id, med_id, dose, frequency)
                   SELECT p.prescription_id, m.ids[1 + ((p.prescription_id * 7 + k * 13) %% cardinality(m.ids))],
                          '10 mg', 'once daily'
                   FROM Prescription p, generate_series(0, %s) k, (SELECT array_agg(med_id) AS ids FROM Medication) m
                   WHERE p.patient_id >= %s
                   ON CONFLICT (prescription_id, med_id) DO NOTHING""", (ITEMS_PER_RX - 1, first))
    cur.execute("""INSERT INTO Alert_Log(item_id, alert_type, severity, message)
                   SELECT item_id, 'INTERACTION', 'MODERATE', 'benchmark'
                   FROM Prescription_Item WHERE item_id % 10 = 0""")
    cur.execute("ALTER TABLE Prescription_Item ENABLE TRIGGER trg_medication_safety")
    cur.execute("ANALYZE Patient, Prescription, Prescription_Item, Interaction, Alert_Log")
    cur.execute("""SELECT (SELECT count(*) FROM Patient) AS patients, (SELECT count(*) FROM Prescription) AS rx,
                          (SELECT count(*) FROM Prescription_Item) AS items, (SELECT count(*) FROM Interaction) AS rules,
                          (SELECT count(*) FROM Alert_Log) AS alerts""")
    return first, cur.fetchone()


def trigger_latency(cur, patient, enabled):
    cur.execute(f"ALTER TABLE Prescription_Item {'ENABLE' if enabled else 'DISABLE'} TRIGGER trg_medication_safety")
    cur.execute("SELECT array_agg(med_id ORDER BY med_id) AS ids FROM Medication")
    meds = cur.fetchone()["ids"]
    timings = []
    for i in range(TRIGGER_INSERTS):
        cur.execute("INSERT INTO Prescription(patient_id, doctor_id) SELECT %s, min(doctor_id) FROM Doctor "
                    "RETURNING prescription_id", (patient + i % 50,))
        rx = cur.fetchone()["prescription_id"]
        start = time.perf_counter()
        cur.execute("INSERT INTO Prescription_Item(prescription_id, med_id, dose, frequency) "
                    "VALUES (%s, %s, '10 mg', 'once daily')", (rx, meds[i * 17 % len(meds)]))
        timings.append((time.perf_counter() - start) * 1000)
    cur.execute("ALTER TABLE Prescription_Item ENABLE TRIGGER trg_medication_safety")
    timings.sort()
    return statistics.mean(timings), timings[int(len(timings) * 0.95) - 1]


def main():
    password = os.environ.get("PGPASSWORD") or getpass.getpass("postgres password: ")
    conn = psycopg.connect(host=config.PG_HOST, port=config.PG_PORT, dbname=config.PG_DB, user="postgres",
                           password=password, row_factory=dict_row)
    queries = load_queries()
    try:
        with conn.cursor() as cur:
            print("Loading the synthetic workload (inside a transaction that will be rolled back)…")
            first, sizes = bulk_load(cur)
            params = {"patient": first + 123, "med": 2}

            with_idx = {name: measure(cur, sql, params) for name, sql in queries}
            for index in INDEXES:
                cur.execute(f"DROP INDEX {index}")
            cur.execute("ALTER TABLE Interaction DROP CONSTRAINT uq_pair")
            cur.execute("ANALYZE Prescription, Prescription_Item, Interaction")
            without_idx = {name: measure(cur, sql, params) for name, sql in queries}
            # the dropped indexes return with the rollback; recreate them for the trigger timing
            cur.execute("CREATE INDEX idx_presc_patient ON Prescription(patient_id)")
            cur.execute("CREATE INDEX idx_item_med ON Prescription_Item(med_id)")
            cur.execute("CREATE INDEX idx_interaction ON Interaction(med_id_1, med_id_2)")
            cur.execute("ANALYZE Prescription, Prescription_Item, Interaction")

            on_mean, on_p95 = trigger_latency(cur, first, enabled=True)
            off_mean, off_p95 = trigger_latency(cur, first, enabled=False)
    finally:
        conn.rollback()
        conn.close()

    lines = [
        "# MediSentinel benchmark results", "",
        "Generated by `python tools/benchmark.py`. The workload is loaded inside one transaction that is rolled "
        "back afterwards, so the database is unchanged.", "",
        f"**Data volume:** {sizes['patients']:,} patients · {sizes['rx']:,} prescriptions · "
        f"{sizes['items']:,} prescription items · {sizes['rules']:,} interaction rules · {sizes['alerts']:,} alerts",
        "", f"Median of {RUNS} runs of `EXPLAIN (ANALYZE, BUFFERS)`.", "",
        "| Query | With indexes (ms) | Without indexes (ms) | Speed-up | Plan with indexes | Plan without |",
        "|---|---|---|---|---|---|",
    ]
    for name, _ in queries:
        (t1, n1), (t2, n2) = with_idx[name], without_idx[name]
        lines.append(f"| {name} | {t1:.3f} | {t2:.3f} | {t2 / t1:.0f}× | {'; '.join(n1)} | {'; '.join(n2)} |")
    lines += ["", "## Safety trigger cost per prescription item", "",
              f"{TRIGGER_INSERTS} single-row inserts, measured from the application.", "",
              "| Trigger | Mean (ms) | 95th percentile (ms) |", "|---|---|---|",
              f"| On (interaction, contraindication and allergy checks) | {on_mean:.2f} | {on_p95:.2f} |",
              f"| Off | {off_mean:.2f} | {off_p95:.2f} |", "",
              f"The safety check adds about {on_mean - off_mean:.2f} ms per medicine on this machine.", ""]
    out = ROOT / "reports" / "benchmark_results.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nSaved {out}")


if __name__ == "__main__":
    main()
