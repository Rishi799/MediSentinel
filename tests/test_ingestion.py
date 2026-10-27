"""Unit tests for ingestion functions."""

from ingestion.load_medications import label_to_medication


def test_label_to_medication_normal():
    label = {
        "openfda": {
            "brand_name": ["Advil"],
            "generic_name": ["Ibuprofen"],
            "rxcui": ["5640"],
            "pharm_class_epc": ["Nonsteroidal Anti-inflammatory Drug [EPC]"],
        }
    }
    res = label_to_medication(label)
    assert res == {
        "name": "Advil",
        "generic_name": "ibuprofen",
        "rxcui": "5640",
        "drug_class": "Nonsteroidal Anti-inflammatory Drug",
    }


def test_label_to_medication_missing_brand_name():
    label = {
        "openfda": {
            "generic_name": ["paracetamol"],
            "rxcui": ["161"],
            "pharm_class_epc": ["Analgesic [EPC]"],
        }
    }
    res = label_to_medication(label)
    assert res["name"] == "Paracetamol"
    assert res["generic_name"] == "paracetamol"
    assert res["rxcui"] == "161"
    assert res["drug_class"] == "Analgesic"


def test_label_to_medication_missing_generic_name():
    label = {
        "openfda": {
            "brand_name": ["MysteryDrug"],
            "rxcui": ["9999"],
        }
    }
    assert label_to_medication(label) is None


def test_label_to_medication_epc_removed():
    label = {
        "openfda": {
            "brand_name": ["Lipitor"],
            "generic_name": ["Atorvastatin"],
            "pharm_class_epc": ["HMG-CoA Reductase Inhibitor [EPC]"],
        }
    }
    res = label_to_medication(label)
    assert res["drug_class"] == "HMG-CoA Reductase Inhibitor"


def test_label_to_medication_long_name_truncated():
    very_long_name = "A" * 200
    label = {
        "openfda": {
            "brand_name": [very_long_name],
            "generic_name": [very_long_name],
            "rxcui": ["1234567890123456789099999"],
            "pharm_class_epc": ["Long Class " * 15 + " [EPC]"],
        }
    }
    res = label_to_medication(label)
    assert len(res["name"]) <= 150
    assert len(res["generic_name"]) <= 150
    assert len(res["rxcui"]) <= 20
    assert len(res["drug_class"]) <= 100
