"""Tests for medisentinel.db against the local medisentinel database (after schema + seed + roles).

Every test cleans up the rows it creates, so the demo data stays as it was.
Run from the repo root:  python -m pytest
"""
import datetime

import psycopg
import pytest

from medisentinel import db


@pytest.fixture(scope="module")
def doctor():
    with db.connect_as("ms_doctor") as conn:
        yield conn


@pytest.fixture(scope="module")
def pharmacist():
    with db.connect_as("ms_pharmacist") as conn:
        yield conn


@pytest.fixture(scope="module")
def admin():
    with db.connect_as("ms_admin") as conn:
        yield conn


@pytest.fixture
def med(doctor):
    """med_id by medication name (from the demo seed)."""
    return lambda name: next(m["med_id"] for m in db.list_medications(doctor, name) if m["name"] == name)


@pytest.fixture
def new_patient(doctor, admin):
    """A patient with a peptic ulcer, removed again (with everything that refers to them) after the test."""
    patient_id = db.add_patient(doctor, "Test Patient", datetime.date(1960, 5, 1), "M", "normal", "normal",
                                conditions=["peptic ulcer"])
    yield patient_id
    with admin.transaction():
        admin.execute("DELETE FROM Alert_Log WHERE item_id IN (SELECT pi.item_id FROM Prescription_Item pi "
                      "JOIN Prescription p USING (prescription_id) WHERE p.patient_id = %s)", (patient_id,))
        admin.execute("DELETE FROM Prescription_Item WHERE prescription_id IN "
                      "(SELECT prescription_id FROM Prescription WHERE patient_id = %s)", (patient_id,))
        for table in ("Prescription", "Allergy", "Patient_Condition", "Patient"):
            admin.execute(f"DELETE FROM {table} WHERE patient_id = %s", (patient_id,))


def first_doctor(conn):
    return db.list_doctors(conn)[0]["doctor_id"]


def test_lists_for_the_forms(doctor):
    assert "peptic ulcer" in db.list_conditions(doctor)
    assert any(m["name"] == "Aspirin" for m in db.list_medications(doctor, "asp"))
    assert db.list_doctors(doctor) and db.list_patients(doctor)


def test_roles_are_recognised(doctor, pharmacist, admin):
    assert (db.role_of(doctor), db.role_of(pharmacist), db.role_of(admin)) == ("doctor", "pharmacist", "admin")


def test_prescription_raises_safety_alerts(doctor, med, new_patient):
    items = [{"med_id": med("Warfarin"), "dose": "5 mg", "frequency": "once daily"},
             {"med_id": med("Aspirin"), "dose": "75 mg", "frequency": "once daily"}]
    prescription_id, alerts = db.create_prescription(doctor, new_patient, first_doctor(doctor), items)
    found = {(a["alert_type"], a["severity"]) for a in alerts}
    assert prescription_id > 0
    assert ("INTERACTION", "MAJOR") in found  # Warfarin + Aspirin
    assert ("CONTRA", "MAJOR") in found       # Aspirin with peptic ulcer
    assert len(db.get_active_alerts(doctor, new_patient)) == len(alerts)


def test_failed_item_saves_nothing(doctor, admin, med, new_patient):
    items = [{"med_id": med("Warfarin"), "dose": "5 mg", "frequency": "once daily"},
             {"med_id": 999999, "dose": "1 mg", "frequency": "once daily"}]  # no such medication
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        db.create_prescription(doctor, new_patient, first_doctor(doctor), items)
    count = admin.execute("SELECT count(*) AS n FROM Prescription WHERE patient_id = %s",
                          (new_patient,)).fetchone()["n"]
    assert count == 0  # the header was rolled back together with the items


def test_same_medicine_twice_rejected(doctor, admin, med, new_patient):
    item = {"med_id": med("Warfarin"), "dose": "5 mg", "frequency": "once daily"}
    with pytest.raises(psycopg.errors.UniqueViolation):
        db.create_prescription(doctor, new_patient, first_doctor(doctor), [item, dict(item)])
    count = admin.execute("SELECT count(*) AS n FROM Prescription WHERE patient_id = %s",
                          (new_patient,)).fetchone()["n"]
    assert count == 0


def test_empty_prescription_rejected(doctor, new_patient):
    with pytest.raises(ValueError):
        db.create_prescription(doctor, new_patient, first_doctor(doctor), [])


def test_override_needs_reason_and_happens_once(doctor, med, new_patient):
    items = [{"med_id": med("Aspirin"), "dose": "75 mg", "frequency": "once daily"}]
    _, alerts = db.create_prescription(doctor, new_patient, first_doctor(doctor), items)
    alert_id = alerts[0]["alert_id"]
    with pytest.raises(ValueError):
        db.override_alert(doctor, alert_id, "  ")
    assert db.override_alert(doctor, alert_id, "Benefit outweighs risk; monitored")
    assert not db.override_alert(doctor, alert_id, "again")


def test_pharmacist_cannot_write(pharmacist):
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.add_patient(pharmacist, "Not Allowed", datetime.date(1990, 1, 1), "F", "normal", "normal")


def test_doctor_cannot_forge_or_delete_alerts(doctor):
    item_id = doctor.execute("SELECT min(item_id) AS i FROM Prescription_Item").fetchone()["i"]
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        doctor.execute("INSERT INTO Alert_Log(item_id, alert_type, severity, message) "
                       "VALUES (%s, 'INTERACTION', 'MINOR', 'forged')", (item_id,))
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        doctor.execute("DELETE FROM Alert_Log")
