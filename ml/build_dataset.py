"""Build the report-seriousness training table from FAERS reports in MongoDB."""
import csv
from collections import Counter

from pymongo import MongoClient

from medisentinel import config, db
from ml.features import FEATURE_NAMES, ROOT, age_in_years, medication_features, normalize_name, safety_data

DATA_PATH = ROOT / "data" / "train.csv"


def medication_index(conn):
    rows = conn.execute("SELECT med_id, name, generic_name FROM Medication ORDER BY med_id").fetchall()
    generics = {}
    for row in rows:
        if row["generic_name"]:
            generics.setdefault(normalize_name(row["generic_name"]), row["med_id"])
    aliases = generics.copy()
    for row in rows:
        aliases.setdefault(normalize_name(row["name"]), row["med_id"])
    return aliases


def match_drug(entry, aliases):
    fda = entry.get("openfda") or {}
    names = [*(fda.get("generic_name") or []), entry.get("medicinalproduct")]
    for name in names:
        med_id = aliases.get(normalize_name(name))
        if med_id is not None:
            return med_id
    return None


def report_features(report, aliases, interactions, signals):
    patient = report.get("patient") or {}
    age = age_in_years(patient.get("patientonsetage"), patient.get("patientonsetageunit"))
    if age is None:
        return None
    drugs = patient.get("drug") or []
    meds = {match_drug(entry, aliases) for entry in drugs}
    meds.discard(None)
    return medication_features(age, patient.get("patientsex"), len(drugs), meds, interactions, signals)


def main():
    with db.connect_as("ms_pharmacist") as conn:
        aliases = medication_index(conn)
        interactions, signals = safety_data(conn)

    counts = Counter()
    read = 0
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = DATA_PATH.with_suffix(".tmp")
    with (MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=5000) as client,
          temp.open("w", newline="", encoding="utf-8") as out):
        writer = csv.writer(out)
        writer.writerow((*FEATURE_NAMES, "y"))
        reports = client[config.MONGO_DB].adverse_reports.find({}, {
            "serious": 1, "patient.patientonsetage": 1, "patient.patientonsetageunit": 1,
            "patient.patientsex": 1, "patient.drug": 1,
        }).sort("_id", 1)
        for report in reports:
            read += 1
            features = report_features(report, aliases, interactions, signals)
            if features is not None:
                label = int(str(report.get("serious")) == "1")
                counts[label] += 1
                writer.writerow((*features, label))
    if not counts:
        temp.unlink()
        raise SystemExit("No reports had a usable onset age. Load openFDA adverse reports first.")
    temp.replace(DATA_PATH)
    print(f"Reports read: {read:,} | Retained: {counts.total():,} | Dropped: {read - counts.total():,}")
    for label, name in ((0, "Nonserious"), (1, "Serious")):
        print(f"{name}: {counts[label]:,} ({counts[label] / counts.total():.1%})")


if __name__ == "__main__":
    main()
