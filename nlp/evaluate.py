"""Evaluate frozen NLP predictions against the manually reviewed gold sheet."""
import argparse
import csv
import json

import sys
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nlp.extract_rules import ROOT, SEVERITY_RANK, normalize
from nlp.make_gold_sheet import FIELDS, GOLD_PATH, SNAPSHOT_PATH

EVAL_PATH = ROOT / "output" / "eval.json"


def metrics(predicted, gold):
    tp = len(predicted & gold)
    precision = tp / len(predicted) if predicted else 0.0
    recall = tp / len(gold) if gold else 0.0
    return {"precision": precision, "recall": recall,
            "f1": 2 * precision * recall / (precision + recall) if tp else 0.0,
            "tp": tp, "fp": len(predicted - gold), "fn": len(gold - predicted)}


def evaluate(predicted, gold):
    predicted_pairs = {row[:-1]: row[-1] for row in predicted}
    gold_pairs = {row[:-1]: row[-1] for row in gold}
    levels = (*SEVERITY_RANK, "MISSING")
    confusion = {actual: dict.fromkeys(levels, 0) for actual in levels}
    for pair in predicted_pairs.keys() | gold_pairs.keys():
        actual = gold_pairs.get(pair, "MISSING")
        prediction = predicted_pairs.get(pair, "MISSING")
        confusion[actual][prediction] += 1
    return {"pair_or_condition": metrics(set(predicted_pairs), set(gold_pairs)),
            "with_severity": metrics(predicted, gold), "severity_confusion": confusion}


def read_gold(path, expected_sentences):
    gold = {}
    reviewed = set()
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or set(reader.fieldnames) != set(FIELDS):
            raise ValueError(f"Expected these CSV columns: {', '.join(FIELDS)}")
        for line, row in enumerate(reader, 2):
            key = (row["label_id"].strip(), normalize(row["drug"]), row["sentence"].strip())
            if not any(key):
                continue
            if key not in expected_sentences:
                raise ValueError(f"Line {line}: keep label ID, drug and sentence unchanged.")
            reviewed.add(key)
            other, condition, severity = (normalize(row[field]) for field in FIELDS[3:])
            if other and condition or bool(other or condition) != bool(severity):
                raise ValueError(f"Line {line}: enter one target and severity, or leave all three blank.")
            if not severity:
                continue
            severity = severity.upper()
            if severity not in SEVERITY_RANK:
                raise ValueError(f"Line {line}: severity must be MINOR, MODERATE or MAJOR.")
            pair = (*key, "interaction" if other else "contraindication", other or condition)
            if pair in gold and gold[pair] != severity:
                raise ValueError(f"Line {line}: conflicting severities for the same rule.")
            gold[pair] = severity
    if reviewed != expected_sentences:
        raise ValueError("The sheet is missing sentences. Keep a blank target row for negative examples.")
    return {(*key, severity) for key, severity in gold.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviewed", action="store_true", help="Confirm manual review of all 50 labels")
    args = parser.parse_args()
    if not args.reviewed:
        parser.error("Finish reviewing the gold sheet, then rerun with --reviewed.")
    try:
        snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        gold = read_gold(GOLD_PATH, {tuple(row) for row in snapshot["sentences"]})
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    predicted = {tuple(row) for row in snapshot["predictions"]}
    results = evaluate(predicted, gold)
    results["labels"] = len(snapshot["labels"])
    results["sentences"] = len(snapshot["sentences"])
    for name in ("pair_or_condition", "with_severity"):
        row = results[name]
        print(f"{name}: precision={row['precision']:.3f} recall={row['recall']:.3f} F1={row['f1']:.3f}")
    table = results["severity_confusion"]
    print("Actual / predicted" + "".join(f"{level:>11}" for level in table))
    for level, counts in table.items():
        print(f"{level:<18}" + "".join(f"{count:>11}" for count in counts.values()))
    EVAL_PATH.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
