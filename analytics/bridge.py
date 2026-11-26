"""Load the rules extracted from FDA labels (nlp/output/rules.jsonl) into PostgreSQL.

Interaction pairs are stored once with the smaller med_id first (the schema's CHECK), curated rules are
never overwritten, and every rule keeps the openFDA label it came from in source_label_id.
Run:  python -m analytics.bridge            (add --dry-run to only count)
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

from medisentinel import db

RULES_PATH = Path(__file__).resolve().parent.parent / "nlp" / "output" / "rules.jsonl"
SEVERITY_RANK = {"MAJOR": 3, "MODERATE": 2, "MINOR": 1}


def plan_rows(rules, med_ids_by_generic):
    """Turn extracted rules into Interaction and Contraindication rows (no database access).

    med_ids_by_generic: lower-case generic name -> list of med_ids. Returns (interactions, contras, skipped)
    where interactions maps (med_id_1, med_id_2) -> row with med_id_1 < med_id_2, keeping the most severe rule.
    """
    interactions, contras, skipped = {}, {}, 0
    for rule in rules:
        drugs = med_ids_by_generic.get(rule["drug"].lower(), [])
        if rule["kind"] == "interaction":
            others = med_ids_by_generic.get(rule["other"].lower(), [])
            if not drugs or not others:
                skipped += 1
                continue
            for a in drugs:
                for b in others:
                    if a == b:
                        continue
                    key = (min(a, b), max(a, b))
                    old = interactions.get(key)
                    if old is None or SEVERITY_RANK[rule["severity"]] > SEVERITY_RANK[old["severity"]]:
                        interactions[key] = {"severity": rule["severity"], "mechanism": rule["mechanism"],
                                             "source_label_id": rule["source_label_id"]}
        else:
            if not drugs:
                skipped += 1
                continue
            for med_id in drugs:
                key = (med_id, rule["condition"].lower())
                old = contras.get(key)
                if old is None or SEVERITY_RANK[rule["severity"]] > SEVERITY_RANK[old["severity"]]:
                    contras[key] = {"severity": rule["severity"], "source_label_id": rule["source_label_id"]}
    return interactions, contras, skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="count what would be loaded, change nothing")
    args = parser.parse_args()

    rules = [json.loads(line) for line in RULES_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    conn = db.connect_as("ms_admin")  # only the admin may write the knowledge tables
    med_ids = defaultdict(list)
    for row in conn.execute("SELECT med_id, lower(generic_name) AS g FROM Medication WHERE generic_name IS NOT NULL"):
        med_ids[row["g"]].append(row["med_id"])

    interactions, contras, skipped = plan_rows(rules, med_ids)
    print(f"Rules read: {len(rules):,} | not in the Medication table: {skipped:,} | "
          f"interaction pairs: {len(interactions):,} | contraindications: {len(contras):,}")
    if args.dry_run:
        return

    with conn.transaction():
        new_inter = sum(conn.execute(
            "INSERT INTO Interaction(med_id_1, med_id_2, severity, mechanism, source_label_id) "
            "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (med_id_1, med_id_2) DO NOTHING",
            (a, b, r["severity"], r["mechanism"], r["source_label_id"])).rowcount
            for (a, b), r in interactions.items())
        new_contra = sum(conn.execute(
            "INSERT INTO Contraindication(med_id, condition_name, severity, source_label_id) "
            "SELECT %s, %s, %s, %s WHERE NOT EXISTS (SELECT 1 FROM Contraindication "
            "WHERE med_id = %s AND lower(condition_name) = %s)",
            (med_id, cond, r["severity"], r["source_label_id"], med_id, cond)).rowcount
            for (med_id, cond), r in contras.items())
    totals = conn.execute("SELECT (SELECT count(*) FROM Interaction) AS i, "
                          "(SELECT count(*) FROM Contraindication) AS c").fetchone()
    print(f"Inserted {new_inter:,} interactions and {new_contra:,} contraindications "
          f"(existing and curated rules kept). Totals now: {totals['i']:,} interactions, "
          f"{totals['c']:,} contraindications.")
    conn.close()


if __name__ == "__main__":
    main()
