"""Read alert features and run inference without modifying the database."""
from datetime import date
from functools import lru_cache
from math import isfinite

import joblib

from ml.features import FEATURE_NAMES, ROOT, medication_features, safety_data

MODEL_PATH = ROOT / "model_risk_v1.joblib"


@lru_cache(maxsize=1)
def load_model(path, modified_ns):
    artifact = joblib.load(path)
    if tuple(artifact["feature_names"]) != FEATURE_NAMES:
        raise ValueError("The saved model has an incompatible feature order.")
    return artifact["model"]


def predict_risk(features):
    """Return the saved model's probability for the serious report class."""
    model = load_model(MODEL_PATH, MODEL_PATH.stat().st_mtime_ns)
    probability = float(model.predict_proba([features])[0, 1])
    if not isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError("The model returned an invalid probability.")
    return probability


def alert_inputs(conn, alert_ids=None, *, only_unscored=False):
    """Get stored scores and the current patient regimen under the caller's role."""
    if alert_ids is not None and not alert_ids:
        return []
    rows = conn.execute("""
        WITH selected AS (
            SELECT a.alert_id, a.alert_type, a.severity, a.risk_score, p.patient_id
            FROM Alert_Log a
            JOIN Prescription_Item i ON i.item_id = a.item_id
            JOIN Prescription p ON p.prescription_id = i.prescription_id
            WHERE (%s::int[] IS NULL OR a.alert_id = ANY(%s))
              AND (NOT %s OR a.risk_score IS NULL)
        ), active AS (
            SELECT p.patient_id, array_agg(i.med_id) AS meds
            FROM Prescription p JOIN Prescription_Item i USING (prescription_id)
            WHERE p.status = 'ACTIVE' AND p.patient_id IN (SELECT patient_id FROM selected)
            GROUP BY p.patient_id
        )
        SELECT a.*, pt.date_of_birth, pt.gender, active.meds
        FROM selected a JOIN Patient pt USING (patient_id)
        LEFT JOIN active USING (patient_id) ORDER BY a.alert_id
    """, (alert_ids, alert_ids, only_unscored)).fetchall()
    if not rows:
        return []

    interactions, signals = safety_data(conn)
    today = date.today()
    context = {}
    for row in rows:
        patient_id = row["patient_id"]
        if patient_id not in context:
            dob = row["date_of_birth"]
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            meds = row["meds"] or []
            context[patient_id] = medication_features(age, row["gender"], len(meds), meds,
                                                       interactions, signals)
        row["features"] = context[patient_id]
    return rows
