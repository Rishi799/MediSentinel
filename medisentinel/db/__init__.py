"""PostgreSQL functions shared by the app, the scripts and the tests.

Every function takes a connection from connect(). The role that logged in on that
connection (ms_doctor, ms_pharmacist, ms_admin) decides what the database allows,
so permissions are enforced by PostgreSQL itself (see sql/roles.sql).
Rows come back as dicts. All values are passed as query parameters, never pasted
into the SQL text, which rules out SQL injection.
"""
import psycopg
from psycopg.rows import dict_row

from medisentinel import config

ROLES = {"ms_doctor": "doctor", "ms_pharmacist": "pharmacist", "ms_admin": "admin"}
_PRESCRIBE_LOCK = 1  # namespace for the per-patient advisory lock


def connect(username, password):
    """Log in as a PostgreSQL role. A wrong username/password raises psycopg.OperationalError.

    Autocommit is on, so reads need no commit; every write below wraps its statements
    in conn.transaction(), which commits them together or rolls all of them back.
    """
    return psycopg.connect(host=config.PG_HOST, port=config.PG_PORT, dbname=config.PG_DB,
                           user=username, password=password, row_factory=dict_row, autocommit=True)


def connect_as(role):
    """Log in with a role password from .env (for scripts and tests; the app uses connect())."""
    password = config.ROLE_PASSWORDS.get(role)
    if not password:
        raise RuntimeError(f"no password for {role} in .env")
    return connect(role, password)


def role_of(conn):
    """'doctor', 'pharmacist' or 'admin' for the logged-in role, None for any other login."""
    return ROLES.get(conn.info.user)


def list_doctors(conn):
    return conn.execute("SELECT doctor_id, full_name, specialty FROM Doctor ORDER BY full_name").fetchall()


def list_patients(conn):
    return conn.execute(
        "SELECT patient_id, full_name, date_of_birth, gender FROM Patient ORDER BY full_name").fetchall()


def list_medications(conn, search=""):
    """Medications whose brand or generic name contains `search` (case-insensitive)."""
    pattern = f"%{search}%"
    return conn.execute(
        "SELECT med_id, name, generic_name FROM Medication "
        "WHERE name ILIKE %s OR generic_name ILIKE %s ORDER BY name", (pattern, pattern)).fetchall()


def list_conditions(conn):
    """Condition names known to the system (from contraindication rules and existing patients)."""
    rows = conn.execute("SELECT condition_name FROM Contraindication UNION "
                        "SELECT condition_name FROM Patient_Condition ORDER BY 1").fetchall()
    return [row["condition_name"] for row in rows]


def add_patient(conn, full_name, dob, gender, renal, hepatic, conditions=(), allergies=()):
    """Save a patient with their conditions and allergies as one transaction; returns patient_id.

    conditions: condition names. allergies: (med_id, reaction) pairs.
    """
    with conn.transaction():
        patient_id = conn.execute(
            "INSERT INTO Patient(full_name, date_of_birth, gender, renal_function, hepatic_function) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING patient_id",
            (full_name, dob, gender, renal, hepatic)).fetchone()["patient_id"]
        for condition in dict.fromkeys(conditions):  # drop duplicates, keep order
            conn.execute("INSERT INTO Patient_Condition(patient_id, condition_name) VALUES (%s, %s)",
                         (patient_id, condition))
        for med_id, reaction in allergies:
            conn.execute("INSERT INTO Allergy(patient_id, med_id, reaction) VALUES (%s, %s, %s)",
                         (patient_id, med_id, reaction))
    return patient_id


def create_prescription(conn, patient_id, doctor_id, items):
    """Save a prescription and all its medicines as one transaction.

    items: dicts with med_id, dose and frequency. The safety trigger checks each item as it
    is inserted; returns (prescription_id, alerts the trigger raised for this prescription).
    If any item fails, nothing is saved.

    Prescriptions for the same patient are serialised with an advisory lock, so two doctors
    prescribing at the same moment always see each other's medicines.
    """
    if not items:
        raise ValueError("a prescription needs at least one medicine")
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(%s::int, %s::int)", (_PRESCRIBE_LOCK, patient_id))
        prescription_id = conn.execute(
            "INSERT INTO Prescription(patient_id, doctor_id) VALUES (%s, %s) RETURNING prescription_id",
            (patient_id, doctor_id)).fetchone()["prescription_id"]
        item_ids = [
            conn.execute(
                "INSERT INTO Prescription_Item(prescription_id, med_id, dose, frequency) "
                "VALUES (%s, %s, %s, %s) RETURNING item_id",
                (prescription_id, item["med_id"], item["dose"], item["frequency"])).fetchone()["item_id"]
            for item in items
        ]
        alerts = conn.execute(
            "SELECT a.alert_id, m.name AS medication, a.alert_type, a.severity, a.message "
            "FROM Alert_Log a "
            "JOIN Prescription_Item pi ON pi.item_id = a.item_id "
            "JOIN Medication m ON m.med_id = pi.med_id "
            "WHERE a.item_id = ANY(%s) ORDER BY a.alert_id", (item_ids,)).fetchall()
    return prescription_id, alerts


def get_active_alerts(conn, patient_id=None):
    """Alerts not yet overridden, newest first, optionally for one patient."""
    if patient_id is None:
        return conn.execute("SELECT * FROM v_active_alerts ORDER BY created_at DESC").fetchall()
    return conn.execute(
        "SELECT v.* FROM v_active_alerts v "
        "JOIN Alert_Log a ON a.alert_id = v.alert_id "
        "JOIN Prescription_Item pi ON pi.item_id = a.item_id "
        "JOIN Prescription p ON p.prescription_id = pi.prescription_id "
        "WHERE p.patient_id = %s ORDER BY v.created_at DESC", (patient_id,)).fetchall()


def override_alert(conn, alert_id, reason):
    """Mark an alert as overridden, keeping the reason as an audit trail.

    Returns False if the alert does not exist or was already overridden.
    """
    if not reason or not reason.strip():
        raise ValueError("an override needs a reason")
    with conn.transaction():
        updated = conn.execute(
            "UPDATE Alert_Log SET overridden = TRUE, override_reason = %s "
            "WHERE alert_id = %s AND NOT overridden", (reason.strip(), alert_id)).rowcount
    return updated == 1


# ---------- read-only summaries for the app's dashboard and detail panels ----------

def dashboard_counts(conn):
    """Headline numbers: patients, doctors, medications, prescriptions and alert totals."""
    return conn.execute(
        "SELECT (SELECT count(*) FROM Patient)      AS patients, "
        "       (SELECT count(*) FROM Doctor)       AS doctors, "
        "       (SELECT count(*) FROM Medication)   AS medications, "
        "       (SELECT count(*) FROM Prescription) AS prescriptions, "
        "       count(*) FILTER (WHERE NOT overridden)                      AS active_alerts, "
        "       count(*) FILTER (WHERE NOT overridden AND severity = 'MAJOR') AS major_alerts, "
        "       count(*) FILTER (WHERE overridden)                          AS overridden_alerts "
        "FROM Alert_Log").fetchone()


def alert_breakdown(conn):
    """Active alerts counted by type and severity (for the dashboard chart)."""
    return conn.execute(
        "SELECT alert_type, severity, count(*) AS n FROM v_active_alerts "
        "GROUP BY alert_type, severity ORDER BY alert_type, severity").fetchall()


def recent_prescriptions(conn, limit=10, patient_id=None):
    """Newest prescriptions with their medicines and how many alerts each raised."""
    return conn.execute(
        "SELECT p.prescription_id, p.prescribed_date, p.status, pt.full_name AS patient, "
        "       d.full_name AS doctor, "
        "       string_agg(m.name || ' ' || coalesce(pi.dose, ''), ', ' ORDER BY m.name) AS medicines, "
        "       (SELECT count(*) FROM Alert_Log a JOIN Prescription_Item x ON x.item_id = a.item_id "
        "         WHERE x.prescription_id = p.prescription_id) AS alerts "
        "FROM Prescription p "
        "JOIN Patient pt ON pt.patient_id = p.patient_id "
        "JOIN Doctor d ON d.doctor_id = p.doctor_id "
        "JOIN Prescription_Item pi ON pi.prescription_id = p.prescription_id "
        "JOIN Medication m ON m.med_id = pi.med_id "
        "WHERE %(patient)s::int IS NULL OR p.patient_id = %(patient)s "
        "GROUP BY p.prescription_id, pt.full_name, d.full_name "
        "ORDER BY p.prescription_id DESC LIMIT %(limit)s",
        {"patient": patient_id, "limit": limit}).fetchall()


def patient_profile(conn, patient_id):
    """One patient with the facts the safety trigger checks: conditions, allergies, active medicines.

    Returns None if there is no such patient.
    """
    patient = conn.execute(
        "SELECT patient_id, full_name, date_of_birth, gender, renal_function, hepatic_function "
        "FROM Patient WHERE patient_id = %s", (patient_id,)).fetchone()
    if patient is None:
        return None
    patient["conditions"] = [r["condition_name"] for r in conn.execute(
        "SELECT condition_name FROM Patient_Condition WHERE patient_id = %s ORDER BY 1",
        (patient_id,)).fetchall()]
    patient["allergies"] = conn.execute(
        "SELECT coalesce(m.name, a.substance) AS substance, a.reaction FROM Allergy a "
        "LEFT JOIN Medication m ON m.med_id = a.med_id WHERE a.patient_id = %s ORDER BY 1",
        (patient_id,)).fetchall()
    patient["active_medicines"] = conn.execute(
        "SELECT DISTINCT m.name, pi.dose, pi.frequency FROM Prescription_Item pi "
        "JOIN Prescription p ON p.prescription_id = pi.prescription_id "
        "JOIN Medication m ON m.med_id = pi.med_id "
        "WHERE p.patient_id = %s AND p.status = 'ACTIVE' ORDER BY m.name", (patient_id,)).fetchall()
    return patient


def get_overridden_alerts(conn, limit=50):
    """Audit trail: alerts a doctor overrode, with the reason given."""
    return conn.execute(
        "SELECT a.alert_id, pt.full_name AS patient, m.name AS medication, a.alert_type, "
        "       a.severity, a.message, a.override_reason, a.created_at "
        "FROM Alert_Log a "
        "JOIN Prescription_Item pi ON pi.item_id = a.item_id "
        "JOIN Prescription p ON p.prescription_id = pi.prescription_id "
        "JOIN Patient pt ON pt.patient_id = p.patient_id "
        "JOIN Medication m ON m.med_id = pi.med_id "
        "WHERE a.overridden ORDER BY a.alert_id DESC LIMIT %s", (limit,)).fetchall()


def list_signals(conn, limit=20):
    """Strongest adverse-reaction signals (PRR) per medication from Adverse_Signal."""
    return conn.execute(
        "SELECT m.name AS medication, s.reaction_term, s.report_count, s.prr, s.ror "
        "FROM Adverse_Signal s JOIN Medication m ON m.med_id = s.med_id "
        "ORDER BY s.prr DESC NULLS LAST LIMIT %s", (limit,)).fetchall()
