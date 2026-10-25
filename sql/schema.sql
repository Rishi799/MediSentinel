-- =====================================================================
--  MediSentinel — Medication Safety & Adverse-Reaction Surveillance
--  SQL layer (PostgreSQL)
--  Run:  psql -U <user> -d medisentinel -f sql/schema.sql
-- =====================================================================

-- ---------- clean start (safe to re-run) ----------
DROP TABLE IF EXISTS Alert_Log, Adverse_Signal, Allergy, Patient_Condition,
    Contraindication, Interaction, Prescription_Item, Prescription,
    Medication, Doctor, Patient CASCADE;

-- ============================ TABLES ============================

CREATE TABLE Patient (
    patient_id       SERIAL PRIMARY KEY,
    full_name        VARCHAR(100) NOT NULL,
    date_of_birth    DATE NOT NULL,
    gender           CHAR(1) CHECK (gender IN ('M','F','O')),
    renal_function   VARCHAR(20),          -- normal / impaired / severe
    hepatic_function VARCHAR(20),
    created_at       TIMESTAMP DEFAULT NOW()
);

CREATE TABLE Doctor (
    doctor_id  SERIAL PRIMARY KEY,
    full_name  VARCHAR(100) NOT NULL,
    specialty  VARCHAR(60)
);

CREATE TABLE Medication (
    med_id        SERIAL PRIMARY KEY,
    rxcui         VARCHAR(20) UNIQUE,       -- RxNorm concept id
    name          VARCHAR(150) NOT NULL,
    generic_name  VARCHAR(150),
    drug_class    VARCHAR(100)
);

CREATE TABLE Prescription (
    prescription_id SERIAL PRIMARY KEY,
    patient_id      INT NOT NULL REFERENCES Patient(patient_id),
    doctor_id       INT NOT NULL REFERENCES Doctor(doctor_id),
    prescribed_date DATE NOT NULL DEFAULT CURRENT_DATE,
    status          VARCHAR(15) DEFAULT 'ACTIVE'   -- ACTIVE / STOPPED
);

CREATE TABLE Prescription_Item (
    item_id         SERIAL PRIMARY KEY,
    prescription_id INT NOT NULL REFERENCES Prescription(prescription_id),
    med_id          INT NOT NULL REFERENCES Medication(med_id),
    dose            VARCHAR(40),
    frequency       VARCHAR(40),
    start_date      DATE DEFAULT CURRENT_DATE,
    end_date        DATE,
    CONSTRAINT uq_item UNIQUE (prescription_id, med_id)   -- a medicine appears once per prescription
);

CREATE TABLE Interaction (
    interaction_id  SERIAL PRIMARY KEY,
    med_id_1        INT NOT NULL REFERENCES Medication(med_id),
    med_id_2        INT NOT NULL REFERENCES Medication(med_id),
    severity        VARCHAR(15) NOT NULL,        -- MINOR / MODERATE / MAJOR
    mechanism       TEXT,
    source_label_id VARCHAR(60),                 -- Mongo label _id it came from
    CONSTRAINT uq_pair   UNIQUE (med_id_1, med_id_2),
    CONSTRAINT chk_order CHECK  (med_id_1 < med_id_2)   -- store each pair once
);

CREATE TABLE Contraindication (
    contra_id      SERIAL PRIMARY KEY,
    med_id         INT NOT NULL REFERENCES Medication(med_id),
    condition_name VARCHAR(100) NOT NULL,
    severity       VARCHAR(15),
    source_label_id VARCHAR(60)             -- Mongo label _id it came from
);

CREATE TABLE Patient_Condition (
    patient_id     INT NOT NULL REFERENCES Patient(patient_id),
    condition_name VARCHAR(100) NOT NULL,
    PRIMARY KEY (patient_id, condition_name)
);

CREATE TABLE Allergy (
    allergy_id  SERIAL PRIMARY KEY,
    patient_id  INT NOT NULL REFERENCES Patient(patient_id),
    med_id      INT REFERENCES Medication(med_id),
    substance   VARCHAR(100),
    reaction    VARCHAR(100)
);

CREATE TABLE Adverse_Signal (
    signal_id     SERIAL PRIMARY KEY,
    med_id        INT NOT NULL REFERENCES Medication(med_id),
    reaction_term VARCHAR(120) NOT NULL,
    report_count  INT,
    prr           NUMERIC(8,3),     -- Proportional Reporting Ratio
    ror           NUMERIC(8,3),     -- Reporting Odds Ratio
    computed_at   TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_signal UNIQUE (med_id, reaction_term)
);

CREATE TABLE Alert_Log (
    alert_id        SERIAL PRIMARY KEY,
    item_id         INT NOT NULL REFERENCES Prescription_Item(item_id),
    alert_type      VARCHAR(20),     -- INTERACTION / CONTRA / ALLERGY
    severity        VARCHAR(15),
    message         TEXT,
    created_at      TIMESTAMP DEFAULT NOW(),
    overridden      BOOLEAN DEFAULT FALSE,
    override_reason TEXT,
    risk_score      NUMERIC(4,3) CHECK (risk_score BETWEEN 0 AND 1)   -- ML-predicted risk (Phase 3)
);

-- ============================ INDEXES ============================
CREATE INDEX idx_item_med      ON Prescription_Item(med_id);
CREATE INDEX idx_presc_patient ON Prescription(patient_id);
CREATE INDEX idx_interaction   ON Interaction(med_id_1, med_id_2);
CREATE INDEX idx_signal_med    ON Adverse_Signal(med_id);

-- ==================== TRIGGER: real-time safety check ====================
CREATE OR REPLACE FUNCTION fn_check_medication_safety()
RETURNS TRIGGER AS $$
DECLARE
    v_patient INT;
    rec       RECORD;
BEGIN
    SELECT p.patient_id INTO v_patient
    FROM Prescription p
    WHERE p.prescription_id = NEW.prescription_id;

    -- 1) INTERACTION: against the patient's other ACTIVE medications
    FOR rec IN
        SELECT i.severity, m.name AS other_med
        FROM Prescription_Item pi
        JOIN Prescription p ON p.prescription_id = pi.prescription_id
        JOIN Medication   m ON m.med_id = pi.med_id
        JOIN Interaction  i ON (i.med_id_1 = LEAST(NEW.med_id, pi.med_id)
                            AND i.med_id_2 = GREATEST(NEW.med_id, pi.med_id))
        WHERE p.patient_id = v_patient
          AND p.status = 'ACTIVE'
          AND pi.med_id <> NEW.med_id
    LOOP
        INSERT INTO Alert_Log(item_id, alert_type, severity, message)
        VALUES (NEW.item_id, 'INTERACTION', rec.severity,
                'Interaction with current medication: ' || rec.other_med);
    END LOOP;

    -- 2) CONTRAINDICATION: against the patient's conditions
    FOR rec IN
        SELECT c.severity, c.condition_name
        FROM Contraindication c
        JOIN Patient_Condition pc ON pc.condition_name = c.condition_name
        WHERE c.med_id = NEW.med_id AND pc.patient_id = v_patient
    LOOP
        INSERT INTO Alert_Log(item_id, alert_type, severity, message)
        VALUES (NEW.item_id, 'CONTRA', rec.severity,
                'Contraindicated for condition: ' || rec.condition_name);
    END LOOP;

    -- 3) ALLERGY
    FOR rec IN
        SELECT a.reaction FROM Allergy a
        WHERE a.patient_id = v_patient AND a.med_id = NEW.med_id
    LOOP
        INSERT INTO Alert_Log(item_id, alert_type, severity, message)
        VALUES (NEW.item_id, 'ALLERGY', 'MAJOR',
                'Patient allergy: ' || rec.reaction);
    END LOOP;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public;   -- only the trigger may write alerts (see roles.sql)

DROP TRIGGER IF EXISTS trg_medication_safety ON Prescription_Item;
CREATE TRIGGER trg_medication_safety
AFTER INSERT ON Prescription_Item
FOR EACH ROW EXECUTE FUNCTION fn_check_medication_safety();

-- ==================== FUNCTION: overall item risk ====================
CREATE OR REPLACE FUNCTION compute_combo_risk(p_item INT)
RETURNS VARCHAR AS $$
DECLARE v_risk VARCHAR := 'NONE';
BEGIN
    SELECT CASE
             WHEN bool_or(severity = 'MAJOR')    THEN 'HIGH'
             WHEN bool_or(severity = 'MODERATE') THEN 'MEDIUM'
             WHEN count(*) > 0                   THEN 'LOW'
             ELSE 'NONE'
           END
    INTO v_risk
    FROM Alert_Log WHERE item_id = p_item;
    RETURN v_risk;
END;
$$ LANGUAGE plpgsql;

-- ==================== VIEW: active alerts ====================
CREATE OR REPLACE VIEW v_active_alerts AS
SELECT a.alert_id, pt.full_name AS patient, m.name AS medication,
       a.alert_type, a.severity, a.message, a.created_at
FROM Alert_Log a
JOIN Prescription_Item pi ON pi.item_id = a.item_id
JOIN Prescription p       ON p.prescription_id = pi.prescription_id
JOIN Patient pt           ON pt.patient_id = p.patient_id
JOIN Medication m         ON m.med_id = pi.med_id
WHERE a.overridden = FALSE;

-- Window-function query: rank each medication's strongest safety signals
--   SELECT med_id, reaction_term, prr,
--          RANK() OVER (PARTITION BY med_id ORDER BY prr DESC) AS rk
--   FROM Adverse_Signal WHERE report_count >= 3;

-- ==================== TRANSACTION example ====================
-- A prescription with several medications is atomic: all items commit,
-- or the whole prescription rolls back.
--
--   BEGIN;
--     INSERT INTO Prescription(patient_id, doctor_id)
--       VALUES (1, 1) RETURNING prescription_id;          -- e.g. 1
--     INSERT INTO Prescription_Item(prescription_id, med_id, dose)
--       VALUES (1, 1, '5 mg');     -- trigger runs safety checks
--     INSERT INTO Prescription_Item(prescription_id, med_id, dose)
--       VALUES (1, 2, '75 mg');    -- trigger runs safety checks
--     -- if compute_combo_risk(...) = 'HIGH' the app may ROLLBACK;
--   COMMIT;
