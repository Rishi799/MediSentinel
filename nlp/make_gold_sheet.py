"""Sample and prefill a gold sheet for independent manual review."""
import argparse
import csv
import json
import random

from pymongo import MongoClient

from medisentinel import config
from nlp.extract_rules import ROOT, SECTIONS, label_drugs, label_sentences, load_extractor

GOLD_PATH = ROOT / "gold" / "gold_sheet.csv"
SNAPSHOT_PATH = ROOT / "output" / "gold_predictions.json"
FIELDS = ("label_id", "drug", "sentence", "other_drug", "condition", "severity")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replace", action="store_true", help="Replace the sheet and prediction snapshot")
    args = parser.parse_args()
    if GOLD_PATH.exists() and not args.replace:
        parser.error(f"{GOLD_PATH} already exists. Keep your annotations or pass --replace.")
    extractor = load_extractor()
    with MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=5000) as client:
        labels = client[config.MONGO_DB].medication_labels
        query = {"drug_interactions.0": {"$exists": True}, "openfda.generic_name.0": {"$exists": True}}
        candidates = [row["_id"] for row in labels.find(query, {"_id": 1}).sort("_id", 1)]
        if len(candidates) < 50:
            parser.error(f"Need 50 eligible labels. Found {len(candidates)}.")
        selected = random.Random(7).sample(candidates, 50)
        documents = {row["_id"]: row for row in labels.find({"_id": {"$in": selected}})}

    predictions = set()
    sentences = set()
    rows = []
    for label_id in selected:
        label = documents[label_id]
        names = label_drugs(label)
        drug = extractor.drugs.get(names[0], names[0])
        for kind, sentence in label_sentences(label, extractor.nlp, SECTIONS):
            key = (str(label_id), drug, sentence)
            matches = extractor.predict(sentence, drug, kind, names)
            for target, severity, _ in matches:
                predictions.add((*key, kind, target, severity))
            sentences.add(key)

    represented = set()
    for label_id, drug, sentence, kind, target, severity in sorted(predictions):
        other, condition = (target, "") if kind == "interaction" else ("", target)
        rows.append((label_id, drug, sentence, other, condition, severity))
        represented.add((label_id, drug, sentence))
    rows.extend((*key, "", "", "") for key in sentences - represented)
    rows.sort()
    GOLD_PATH.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with GOLD_PATH.open("w", newline="", encoding="utf-8-sig") as out:
        writer = csv.writer(out)
        writer.writerow(FIELDS)
        writer.writerows(rows)
    SNAPSHOT_PATH.write_text(json.dumps({
        "labels": [str(label) for label in selected],
        "sentences": sorted(sentences),
        "predictions": sorted(predictions),
    }, ensure_ascii=False), encoding="utf-8")
    print(f"Prefilled {len(rows):,} rows from {len(sentences):,} sentences in 50 labels.")
    print(GOLD_PATH)


if __name__ == "__main__":
    main()
