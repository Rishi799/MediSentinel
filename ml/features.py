"""Shared feature order and medication-pair logic for FAERS and live alerts."""
from itertools import combinations
from math import isfinite
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FEATURE_NAMES = ("age", "sex", "n_drugs", "max_interaction_sev", "n_interactions", "has_signal")
SEVERITY_RANK = {"MINOR": 1, "MODERATE": 2, "MAJOR": 3}
AGE_YEARS_PER_UNIT = {
    "800": 10, "801": 1, "802": 1 / 12, "803": 7 / 365.25,
    "804": 1 / 365.25, "805": 1 / (365.25 * 24),
}
SEX_CODES = {"1": 0, "2": 1, "M": 0, "F": 1}


def age_in_years(age, unit):
    """Convert coded FAERS onset age to years, dropping absent or unusable values."""
    if str(unit) not in AGE_YEARS_PER_UNIT:
        return None
    try:
        years = float(age) * AGE_YEARS_PER_UNIT[str(unit)]
    except (TypeError, ValueError):
        return None
    return years if isfinite(years) and years >= 0 else None


def feature_vector(age, sex, n_drugs, max_sev, n_inter, has_signal):
    """Return the model inputs in their shared, stable order."""
    return (float(age), int(sex), int(n_drugs), int(max_sev), int(n_inter), int(bool(has_signal)))


def normalize_name(name):
    return " ".join(str(name or "").casefold().split())


def safety_data(conn):
    interactions = {
        (row["med_id_1"], row["med_id_2"]): SEVERITY_RANK.get((row["severity"] or "").upper(), 0)
        for row in conn.execute("SELECT med_id_1, med_id_2, severity FROM Interaction").fetchall()
    }
    signals = {row["med_id"] for row in conn.execute("SELECT DISTINCT med_id FROM Adverse_Signal").fetchall()}
    return interactions, signals


def medication_features(age, sex, n_drugs, med_ids, interactions, signals):
    ids = set(med_ids)
    pairs = [pair for pair in combinations(sorted(ids), 2) if pair in interactions]
    return feature_vector(age, SEX_CODES.get(str(sex), 2), n_drugs,
                          max((interactions[pair] for pair in pairs), default=0),
                          len(pairs), bool(ids & signals))
