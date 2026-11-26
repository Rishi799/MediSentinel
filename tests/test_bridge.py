"""Tests for the pure rule-planning step of analytics/bridge.py (no database needed)."""
from analytics.bridge import plan_rows

MEDS = {"warfarin": [1], "aspirin": [2], "ibuprofen": [4]}


def rule(kind, drug, other, severity, label="L1"):
    key = "other" if kind == "interaction" else "condition"
    return {"kind": kind, "drug": drug, key: other, "severity": severity, "mechanism": "text",
            "source_label_id": label, "confidence": 0.9}


def test_pair_is_stored_once_with_smaller_id_first():
    inter, _, _ = plan_rows([rule("interaction", "aspirin", "warfarin", "MAJOR"),
                             rule("interaction", "warfarin", "aspirin", "MINOR")], MEDS)
    assert list(inter) == [(1, 2)] and inter[(1, 2)]["severity"] == "MAJOR"


def test_unknown_medicines_are_skipped_and_label_is_kept():
    inter, contras, skipped = plan_rows([rule("interaction", "warfarin", "unknownium", "MAJOR"),
                                         rule("contraindication", "ibuprofen", "Peptic Ulcer", "MAJOR", "L9")], MEDS)
    assert skipped == 1 and not inter
    assert contras[(4, "peptic ulcer")]["source_label_id"] == "L9"
