"""Tests for matching an Indian brand's generic to catalogue rows (no database needed)."""
from ingestion.load_indian_brands import resolve

CATALOGUE = [(1, "warfarin", "Anticoagulant"), (87, "atorvastatin calcium", "Statin"),
             (9, "amoxicillin", "Penicillin"), (90, "amoxicillin and clavulanate potassium", None)]


def test_exact_and_salt_names_match_but_combinations_do_not():
    assert resolve("warfarin", CATALOGUE) == ("warfarin", "Anticoagulant", [1])
    assert resolve("atorvastatin", CATALOGUE) == ("atorvastatin calcium", "Statin", [87])
    assert resolve("amoxicillin", CATALOGUE)[2] == [9]
    assert resolve("amoxicillin and clavulanate potassium", CATALOGUE)[2] == [90]


def test_unknown_generic_keeps_its_name_and_has_no_rules():
    assert resolve("Paracetamol", CATALOGUE) == ("paracetamol", None, [])
