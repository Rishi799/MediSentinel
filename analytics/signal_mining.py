"""Find drug–reaction safety signals in the openFDA adverse-event reports (MongoDB) and store them in
PostgreSQL's Adverse_Signal table.

For every (drug, reaction) pair the reports form a 2x2 table:
    a = reports with the drug and the reaction      b = reports with the drug, other reactions
    c = reports with other drugs and the reaction   d = reports with neither
    PRR = (a / (a + b)) / (c / (c + d))      ROR = (a * d) / (b * c)
A pair is kept as a signal when a >= 3, PRR >= 2 and chi-square >= 4 (the usual Evans criteria).

Run:  python -m analytics.signal_mining            (add --dry-run to only print the strongest signals)
"""
import argparse

from pymongo import MongoClient

from medisentinel import config, db

MIN_REPORTS, MIN_PRR, MIN_CHI2 = 3, 2.0, 4.0

# One row per report: its distinct drugs (first openFDA generic name, else the product name) and reactions.
REPORT_SETS = [
    {"$project": {
        "drugs": {"$setUnion": [{"$map": {
            "input": {"$ifNull": ["$patient.drug", []]}, "as": "d",
            "in": {"$toLower": {"$ifNull": [{"$first": "$$d.openfda.generic_name"}, "$$d.medicinalproduct"]}}}}]},
        "reactions": {"$setUnion": [{"$map": {
            "input": {"$ifNull": ["$patient.reaction", []]}, "as": "r",
            "in": {"$toLower": "$$r.reactionmeddrapt"}}}]},
    }},
]


def disproportionality(a, n_drug, n_reaction, n_total):
    """PRR, ROR and Yates-corrected chi-square for one drug–reaction pair (None when undefined)."""
    b, c = n_drug - a, n_reaction - a
    d = n_total - a - b - c
    if a == 0 or b <= 0 or c <= 0 or d <= 0:
        return None
    prr = (a / (a + b)) / (c / (c + d))
    ror = (a * d) / (b * c)
    chi2 = n_total * (abs(a * d - b * c) - n_total / 2) ** 2 / ((a + b) * (c + d) * (a + c) * (b + d))
    return round(prr, 3), round(ror, 3), round(chi2, 2)


def is_signal(a, stats):
    return stats is not None and a >= MIN_REPORTS and stats[0] >= MIN_PRR and stats[2] >= MIN_CHI2


def mine(reports):
    """Count reports per drug, per reaction and per pair with MongoDB aggregation; return the signals."""
    n_total = reports.count_documents({})
    drug_counts = {r["_id"]: r["n"] for r in reports.aggregate(
        REPORT_SETS + [{"$unwind": "$drugs"}, {"$group": {"_id": "$drugs", "n": {"$sum": 1}}}])}
    reaction_counts = {r["_id"]: r["n"] for r in reports.aggregate(
        REPORT_SETS + [{"$unwind": "$reactions"}, {"$group": {"_id": "$reactions", "n": {"$sum": 1}}}])}
    pairs = reports.aggregate(REPORT_SETS + [
        {"$unwind": "$drugs"}, {"$unwind": "$reactions"},
        {"$group": {"_id": {"drug": "$drugs", "reaction": "$reactions"}, "a": {"$sum": 1}}},
        {"$match": {"a": {"$gte": MIN_REPORTS}}},
    ], allowDiskUse=True)
    signals = []
    for p in pairs:
        drug, reaction, a = p["_id"]["drug"], p["_id"]["reaction"], p["a"]
        stats = disproportionality(a, drug_counts[drug], reaction_counts[reaction], n_total)
        if is_signal(a, stats):
            signals.append({"drug": drug, "reaction": reaction[:120], "a": a,
                            "prr": stats[0], "ror": stats[1], "chi2": stats[2]})
    return n_total, sorted(signals, key=lambda s: (-s["prr"], -s["a"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="print the strongest signals, change nothing")
    args = parser.parse_args()

    client = MongoClient(config.MONGO_URI)
    n_total, signals = mine(client[config.MONGO_DB]["adverse_reports"])
    client.close()

    conn = db.connect_as("ms_admin")  # only the admin may write Adverse_Signal
    med_ids = {}
    for row in conn.execute("SELECT med_id, lower(generic_name) AS g FROM Medication WHERE generic_name IS NOT NULL"):
        med_ids.setdefault(row["g"], []).append(row["med_id"])
    matched = [s for s in signals if s["drug"] in med_ids]
    print(f"Reports analysed: {n_total:,} | signals found: {len(signals):,} | "
          f"for medicines in the Medication table: {len(matched):,}")
    for s in matched[:10]:
        print(f"  {s['drug']:<22} {s['reaction']:<34} reports={s['a']:<4} PRR={s['prr']:<8} ROR={s['ror']}")
    if args.dry_run:
        return

    with conn.transaction():
        written = 0
        for s in matched:
            for med_id in med_ids[s["drug"]]:
                conn.execute(
                    "INSERT INTO Adverse_Signal(med_id, reaction_term, report_count, prr, ror) "
                    "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (med_id, reaction_term) DO UPDATE SET "
                    "report_count = EXCLUDED.report_count, prr = EXCLUDED.prr, ror = EXCLUDED.ror, "
                    "computed_at = now()",
                    (med_id, s["reaction"], s["a"], min(s["prr"], 99999), min(s["ror"], 99999)))
                written += 1
    total = conn.execute("SELECT count(*) AS n FROM Adverse_Signal").fetchone()["n"]
    print(f"Wrote {written:,} signal rows. Adverse_Signal now holds {total:,} rows.")
    conn.close()


if __name__ == "__main__":
    main()
