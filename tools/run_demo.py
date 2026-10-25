"""
MediSentinel — Phase 1 verification harness.

PostgreSQL is the real target (see sql/schema.sql). This script recreates the
SAME schema, seed data, and safety trigger in an in-memory SQLite database using
Python's built-in sqlite3 module, so the Phase-1 logic can be run and verified
with zero installation.

Run:  python tools/run_demo.py
"""
import sqlite3
import textwrap

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE Patient (
    patient_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name        TEXT NOT NULL,
    date_of_birth    TEXT NOT NULL,
    gender           TEXT CHECK (gender IN ('M','F','O')),
    renal_function   TEXT,
    hepatic_function TEXT,
    created_at       TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE Doctor (
    doctor_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name  TEXT NOT NULL,
    specialty  TEXT
);
CREATE TABLE Medication (
    med_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    rxcui        TEXT UNIQUE,
    name         TEXT NOT NULL,
    generic_name TEXT,
    drug_class   TEXT
);
CREATE TABLE Prescription (
    prescription_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id      INTEGER NOT NULL REFERENCES Patient(patient_id),
    doctor_id       INTEGER NOT NULL REFERENCES Doctor(doctor_id),
    prescribed_date TEXT DEFAULT CURRENT_DATE,
    status          TEXT DEFAULT 'ACTIVE'
);
CREATE TABLE Prescription_Item (
    item_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    prescription_id INTEGER NOT NULL REFERENCES Prescription(prescription_id),
    med_id          INTEGER NOT NULL REFERENCES Medication(med_id),
    dose            TEXT,
    frequency       TEXT,
    start_date      TEXT DEFAULT CURRENT_DATE,
    end_date        TEXT
);
CREATE TABLE Interaction (
    interaction_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    med_id_1        INTEGER NOT NULL REFERENCES Medication(med_id),
    med_id_2        INTEGER NOT NULL REFERENCES Medication(med_id),
    severity        TEXT NOT NULL,
    mechanism       TEXT,
    source_label_id TEXT,
    UNIQUE (med_id_1, med_id_2),
    CHECK  (med_id_1 < med_id_2)
);
CREATE TABLE Contraindication (
    contra_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    med_id         INTEGER NOT NULL REFERENCES Medication(med_id),
    condition_name TEXT NOT NULL,
    severity       TEXT,
    source_label_id TEXT
);
CREATE TABLE Patient_Condition (
    patient_id     INTEGER NOT NULL REFERENCES Patient(patient_id),
    condition_name TEXT NOT NULL,
    PRIMARY KEY (patient_id, condition_name)
);
CREATE TABLE Allergy (
    allergy_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id  INTEGER NOT NULL REFERENCES Patient(patient_id),
    med_id      INTEGER REFERENCES Medication(med_id),
    substance   TEXT,
    reaction    TEXT
);
CREATE TABLE Adverse_Signal (
    signal_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    med_id        INTEGER NOT NULL REFERENCES Medication(med_id),
    reaction_term TEXT NOT NULL,
    report_count  INTEGER,
    prr           REAL,
    ror           REAL,
    computed_at   TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (med_id, reaction_term)
);
CREATE TABLE Alert_Log (
    alert_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id         INTEGER NOT NULL REFERENCES Prescription_Item(item_id),
    alert_type      TEXT,
    severity        TEXT,
    message         TEXT,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    overridden      INTEGER DEFAULT 0,
    override_reason TEXT,
    risk_score      REAL CHECK (risk_score BETWEEN 0 AND 1)
);

CREATE INDEX idx_item_med      ON Prescription_Item(med_id);
CREATE INDEX idx_presc_patient ON Prescription(patient_id);
CREATE INDEX idx_interaction   ON Interaction(med_id_1, med_id_2);
CREATE INDEX idx_signal_med    ON Adverse_Signal(med_id);

-- ---- the safety trigger (set-based equivalent of the PL/pgSQL version) ----
CREATE TRIGGER trg_medication_safety
AFTER INSERT ON Prescription_Item
FOR EACH ROW
BEGIN
    INSERT INTO Alert_Log(item_id, alert_type, severity, message)
    SELECT NEW.item_id, 'INTERACTION', i.severity,
           'Interaction with current medication: ' || m.name
    FROM Prescription_Item pi
    JOIN Prescription p ON p.prescription_id = pi.prescription_id
    JOIN Medication  m ON m.med_id = pi.med_id
    JOIN Interaction i ON i.med_id_1 = min(NEW.med_id, pi.med_id)
                      AND i.med_id_2 = max(NEW.med_id, pi.med_id)
    WHERE p.patient_id = (SELECT patient_id FROM Prescription WHERE prescription_id = NEW.prescription_id)
      AND p.status = 'ACTIVE'
      AND pi.item_id <> NEW.item_id;

    INSERT INTO Alert_Log(item_id, alert_type, severity, message)
    SELECT NEW.item_id, 'CONTRA', c.severity,
           'Contraindicated for condition: ' || c.condition_name
    FROM Contraindication c
    JOIN Patient_Condition pc ON pc.condition_name = c.condition_name
    WHERE c.med_id = NEW.med_id
      AND pc.patient_id = (SELECT patient_id FROM Prescription WHERE prescription_id = NEW.prescription_id);

    INSERT INTO Alert_Log(item_id, alert_type, severity, message)
    SELECT NEW.item_id, 'ALLERGY', 'MAJOR', 'Patient allergy: ' || a.reaction
    FROM Allergy a
    WHERE a.med_id = NEW.med_id
      AND a.patient_id = (SELECT patient_id FROM Prescription WHERE prescription_id = NEW.prescription_id);
END;

CREATE VIEW v_active_alerts AS
SELECT a.alert_id, pt.full_name AS patient, m.name AS medication,
       a.alert_type, a.severity, a.message
FROM Alert_Log a
JOIN Prescription_Item pi ON pi.item_id = a.item_id
JOIN Prescription p       ON p.prescription_id = pi.prescription_id
JOIN Patient pt           ON pt.patient_id = p.patient_id
JOIN Medication m         ON m.med_id = pi.med_id
WHERE a.overridden = 0;
"""

SEED = """
INSERT INTO Doctor(full_name, specialty) VALUES
  ('Dr. A Rao','Cardiology'), ('Dr. B Nair','Dentistry'), ('Dr. C Mehta','General Medicine');

INSERT INTO Patient(full_name, date_of_birth, gender, renal_function) VALUES
  ('Ravi Kumar','1958-04-12','M','impaired'),
  ('Sara Ali','1972-09-30','F','severe'),
  ('John DSouza','1990-01-08','M','normal');

INSERT INTO Medication(rxcui, name, generic_name, drug_class) VALUES
  ('11289','Warfarin','warfarin','Anticoagulant'),
  ('1191','Aspirin','aspirin','Antiplatelet/NSAID'),
  ('6809','Metformin','metformin','Biguanide'),
  ('5640','Ibuprofen','ibuprofen','NSAID'),
  ('29046','Lisinopril','lisinopril','ACE inhibitor'),
  ('9997','Spironolactone','spironolactone','K-sparing diuretic'),
  ('36567','Simvastatin','simvastatin','Statin'),
  ('21212','Clarithromycin','clarithromycin','Macrolide antibiotic'),
  ('723','Amoxicillin','amoxicillin','Penicillin antibiotic'),
  ('36437','Sertraline','sertraline','SSRI');

INSERT INTO Interaction(med_id_1, med_id_2, severity, mechanism) VALUES
  (1,2,'MAJOR','Additive bleeding risk (anticoagulant + antiplatelet)'),
  (1,4,'MAJOR','Additive bleeding risk (anticoagulant + NSAID)'),
  (2,4,'MODERATE','Increased GI bleeding (two NSAIDs)'),
  (5,6,'MAJOR','Hyperkalemia (ACE inhibitor + K-sparing diuretic)'),
  (7,8,'MAJOR','Rhabdomyolysis (statin + macrolide)'),
  (1,7,'MODERATE','Warfarin effect potentiated by simvastatin');

INSERT INTO Contraindication(med_id, condition_name, severity) VALUES
  (2,'peptic ulcer','MAJOR'),
  (4,'chronic kidney disease','MAJOR'),
  (3,'renal failure','MAJOR'),
  (6,'hyperkalemia','MODERATE');

INSERT INTO Patient_Condition(patient_id, condition_name) VALUES
  (1,'peptic ulcer'), (1,'hypertension'), (2,'chronic kidney disease');

INSERT INTO Allergy(patient_id, med_id, substance, reaction) VALUES
  (3,9,'penicillin','rash and swelling');

INSERT INTO Adverse_Signal(med_id, reaction_term, report_count, prr, ror) VALUES
  (7,'rhabdomyolysis',40,8.5,9.1),
  (1,'haemorrhage',120,5.2,5.6),
  (4,'gastrointestinal haemorrhage',60,4.0,4.2),
  (3,'lactic acidosis',25,3.1,3.2),
  (10,'nausea',200,1.1,1.1);
"""

# Prescriptions inserted one item at a time so the trigger fires per row.
PRESCRIPTIONS = [
    ("INSERT INTO Prescription(patient_id, doctor_id) VALUES (1,1)", None),      # P1 Ravi
    ("INSERT INTO Prescription_Item(prescription_id, med_id, dose) VALUES (1,1,'5 mg')", "Ravi <- Warfarin"),
    ("INSERT INTO Prescription_Item(prescription_id, med_id, dose) VALUES (1,2,'75 mg')", "Ravi <- Aspirin"),
    ("INSERT INTO Prescription(patient_id, doctor_id) VALUES (2,3)", None),      # P2 Sara
    ("INSERT INTO Prescription_Item(prescription_id, med_id, dose) VALUES (2,4,'400 mg')", "Sara <- Ibuprofen"),
    ("INSERT INTO Prescription(patient_id, doctor_id) VALUES (3,3)", None),      # P3 John
    ("INSERT INTO Prescription_Item(prescription_id, med_id, dose) VALUES (3,9,'500 mg')", "John <- Amoxicillin"),
    ("INSERT INTO Prescription(patient_id, doctor_id) VALUES (3,2)", None),      # P4 John
    ("INSERT INTO Prescription_Item(prescription_id, med_id, dose) VALUES (4,2,'75 mg')", "John <- Aspirin (safe)"),
]


def table(cur, sql, params=()):
    cur.execute(sql, params)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    widths = [len(c) for c in cols]
    for r in rows:
        widths = [max(w, len(str(v))) for w, v in zip(widths, r)]
    line = "  ".join(c.ljust(w) for c, w in zip(cols, widths))
    print(line)
    print("  ".join("-" * w for w in widths))
    for r in rows:
        print("  ".join(str(v).ljust(w) for v, w in zip(r, widths)))
    print()


def section(t):
    print("\n" + "=" * 70 + "\n" + t + "\n" + "=" * 70)


def main():
    print("SQLite engine version:", sqlite3.sqlite_version)
    con = sqlite3.connect(":memory:")
    cur = con.cursor()
    cur.executescript(SCHEMA)
    cur.executescript(SEED)

    section("Applying prescriptions (each item runs the safety trigger)")
    for sql, note in PRESCRIPTIONS:
        cur.execute(sql)
        if note:
            print(f"  + {note}")
    con.commit()

    section("v_active_alerts  (alerts raised automatically by the trigger)")
    table(cur, "SELECT * FROM v_active_alerts ORDER BY alert_id")

    section("JOIN: every prescribed medication with patient + doctor")
    table(cur, """
        SELECT pt.full_name AS patient, d.full_name AS doctor, m.name AS medication, pi.dose
        FROM Prescription_Item pi
        JOIN Prescription p ON p.prescription_id = pi.prescription_id
        JOIN Patient pt ON pt.patient_id = p.patient_id
        JOIN Doctor  d  ON d.doctor_id  = p.doctor_id
        JOIN Medication m ON m.med_id = pi.med_id
        ORDER BY patient, medication""")

    section("AGGREGATION: alert counts by type and severity")
    table(cur, """
        SELECT alert_type, severity, COUNT(*) AS n
        FROM Alert_Log GROUP BY alert_type, severity ORDER BY n DESC""")

    section("WINDOW FUNCTION: strongest safety signal per medication")
    table(cur, """
        SELECT m.name, s.reaction_term, s.prr,
               RANK() OVER (PARTITION BY s.med_id ORDER BY s.prr DESC) AS rk
        FROM Adverse_Signal s JOIN Medication m ON m.med_id = s.med_id
        WHERE s.report_count >= 3 ORDER BY s.prr DESC""")

    section("SUBQUERY (EXISTS): patients on a MAJOR-interacting active pair")
    table(cur, """
        SELECT pt.patient_id, pt.full_name
        FROM Patient pt
        WHERE EXISTS (
            SELECT 1
            FROM Prescription_Item i1
            JOIN Prescription p1 ON p1.prescription_id = i1.prescription_id
                 AND p1.patient_id = pt.patient_id AND p1.status = 'ACTIVE'
            JOIN Prescription_Item i2 ON 1 = 1
            JOIN Prescription p2 ON p2.prescription_id = i2.prescription_id
                 AND p2.patient_id = pt.patient_id AND p2.status = 'ACTIVE'
            JOIN Interaction ix ON ix.med_id_1 = min(i1.med_id, i2.med_id)
                               AND ix.med_id_2 = max(i1.med_id, i2.med_id)
            WHERE i1.med_id < i2.med_id AND ix.severity = 'MAJOR')""")

    # Simple assertions so the run self-verifies.
    cur.execute("SELECT COUNT(*) FROM Alert_Log")
    n_alerts = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM Alert_Log WHERE alert_type='ALLERGY'")
    n_allergy = cur.fetchone()[0]
    section("Self-check")
    assert n_alerts >= 3, "expected at least 3 alerts"
    assert n_allergy == 1, "expected exactly 1 allergy alert"
    print(f"  OK - {n_alerts} alerts raised by the trigger (incl. {n_allergy} allergy).")
    con.close()


if __name__ == "__main__":
    main()
