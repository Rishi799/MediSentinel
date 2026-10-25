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
