"""Add common Indian brand names as Medication rows and give them their generic's safety rules.

Doctors in India usually write brand names (Dolo 650, Ecosprin). Each brand in ingestion/indian_brands.csv
becomes a Medication row with the catalogue generic name, and the Interaction and Contraindication rules of
that generic are copied to the brand's med_id, so the unchanged safety trigger checks "Ecosprin + Warfarin"
exactly like "Aspirin + Warfarin". Run after analytics/bridge.py; safe to re-run.

Run:  python ingestion/load_indian_brands.py
"""
import csv
from pathlib import Path

from medisentinel import db

BRANDS_PATH = Path(__file__).resolve().parent / "indian_brands.csv"


def resolve(generic, catalogue):
    """Catalogue rows for one active ingredient: an exact generic name, or that name plus a salt
    (e.g. 'atorvastatin' -> 'atorvastatin calcium'); combination products ('x and y') only match exactly.

    catalogue: list of (med_id, generic_name, drug_class). Returns (canonical generic_name, drug_class, ids).
    """
    generic = generic.strip().lower()
    rows = [r for r in catalogue if r[1] and (r[1].lower() == generic or (
        r[1].lower().startswith(generic + " ") and " and " not in r[1].lower()))]
    if not rows:
        return generic, None, []
    best = min(rows, key=lambda r: (r[1].lower() != generic, len(r[1])))
    return best[1], best[2], [r[0] for r in rows]


def main():
    brands = list(csv.DictReader(BRANDS_PATH.open(encoding="utf-8")))
    conn = db.connect_as("ms_admin")  # only the admin may change the medication master
    brand_names = [row["brand"].lower() for row in brands]
    catalogue = [(r["med_id"], r["generic_name"], r["drug_class"]) for r in conn.execute(
        "SELECT med_id, generic_name, drug_class FROM Medication WHERE NOT lower(name) = ANY(%s)", (brand_names,))]
    added = inter = contra = no_rules = 0
    with conn.transaction():
        for row in brands:
            generic, drug_class, source_ids = resolve(row["generic"], catalogue)
            existing = conn.execute("SELECT med_id FROM Medication WHERE lower(name) = lower(%s)",
                                    (row["brand"],)).fetchone()
            if existing:
                brand_id = existing["med_id"]
            else:
                brand_id = conn.execute(
                    "INSERT INTO Medication(name, generic_name, drug_class) VALUES (%s, %s, %s) RETURNING med_id",
                    (row["brand"], generic, drug_class)).fetchone()["med_id"]
                added += 1
            if not source_ids:
                no_rules += 1
                continue
            inter += conn.execute(
                "INSERT INTO Interaction(med_id_1, med_id_2, severity, mechanism, source_label_id) "
                "SELECT DISTINCT ON (LEAST(%(b)s, o), GREATEST(%(b)s, o)) LEAST(%(b)s, o), GREATEST(%(b)s, o), "
                "       severity, mechanism, source_label_id "
                "FROM (SELECT CASE WHEN med_id_1 = ANY(%(src)s) THEN med_id_2 ELSE med_id_1 END AS o, "
                "             severity, mechanism, source_label_id FROM Interaction "
                "      WHERE med_id_1 = ANY(%(src)s) OR med_id_2 = ANY(%(src)s)) r "
                "WHERE o <> %(b)s AND NOT o = ANY(%(src)s) "
                "ORDER BY LEAST(%(b)s, o), GREATEST(%(b)s, o), "
                "         CASE severity WHEN 'MAJOR' THEN 0 WHEN 'MODERATE' THEN 1 ELSE 2 END "
                "ON CONFLICT (med_id_1, med_id_2) DO NOTHING",
                {"b": brand_id, "src": source_ids}).rowcount
            contra += conn.execute(
                "INSERT INTO Contraindication(med_id, condition_name, severity, source_label_id) "
                "SELECT DISTINCT ON (lower(c.condition_name)) %(b)s, c.condition_name, c.severity, c.source_label_id "
                "FROM Contraindication c WHERE c.med_id = ANY(%(src)s) AND NOT EXISTS ("
                "  SELECT 1 FROM Contraindication x WHERE x.med_id = %(b)s "
                "  AND lower(x.condition_name) = lower(c.condition_name)) "
                "ORDER BY lower(c.condition_name), CASE c.severity WHEN 'MAJOR' THEN 0 ELSE 1 END",
                {"b": brand_id, "src": source_ids}).rowcount
    print(f"Brands in file: {len(brands)} | new Medication rows: {added} | copied rules: {inter} interactions, "
          f"{contra} contraindications | brands whose generic is not in the catalogue: {no_rules}")
    conn.close()


if __name__ == "__main__":
    main()
