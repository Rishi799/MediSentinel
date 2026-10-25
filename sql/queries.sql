-- =====================================================================
--  MediSentinel — demonstrative SQL queries (PostgreSQL)
--  Covers the guideline items: CRUD, joins, subqueries, aggregation,
--  views, and a window function.
--  Run AFTER schema.sql + seed_demo.sql.
-- =====================================================================

-- ---------- 1. CRUD ----------
-- CREATE
INSERT INTO Patient(full_name, date_of_birth, gender, renal_function)
VALUES ('Test Patient', '2000-05-05', 'F', 'normal');
-- READ
SELECT * FROM Patient WHERE full_name = 'Test Patient';
-- UPDATE
UPDATE Patient SET renal_function = 'impaired' WHERE full_name = 'Test Patient';
-- DELETE
DELETE FROM Patient WHERE full_name = 'Test Patient';

-- ---------- 2. JOIN: every prescribed medication with patient + doctor ----------
SELECT pt.full_name AS patient, d.full_name AS doctor,
       m.name AS medication, pi.dose, p.prescribed_date
FROM Prescription_Item pi
JOIN Prescription p ON p.prescription_id = pi.prescription_id
JOIN Patient    pt  ON pt.patient_id = p.patient_id
JOIN Doctor     d   ON d.doctor_id  = p.doctor_id
JOIN Medication m   ON m.med_id     = pi.med_id
ORDER BY pt.full_name, m.name;

-- ---------- 3. SUBQUERY: patients currently on at least one MAJOR-interacting pair ----------
SELECT pt.patient_id, pt.full_name
FROM Patient pt
WHERE EXISTS (
    SELECT 1
    FROM Prescription_Item i1
    JOIN Prescription p1 ON p1.prescription_id = i1.prescription_id
         AND p1.patient_id = pt.patient_id AND p1.status = 'ACTIVE'
    JOIN Prescription_Item i2 ON TRUE
    JOIN Prescription p2 ON p2.prescription_id = i2.prescription_id
         AND p2.patient_id = pt.patient_id AND p2.status = 'ACTIVE'
    JOIN Interaction ix ON ix.med_id_1 = LEAST(i1.med_id, i2.med_id)
                       AND ix.med_id_2 = GREATEST(i1.med_id, i2.med_id)
    WHERE i1.med_id < i2.med_id
      AND ix.severity = 'MAJOR'
);

-- ---------- 4. AGGREGATION: alert counts by type and severity ----------
SELECT alert_type, severity, COUNT(*) AS n
FROM Alert_Log
GROUP BY alert_type, severity
ORDER BY n DESC;

-- ---------- 5. GROUP BY + HAVING: medications prescribed to more than one patient ----------
SELECT m.name, COUNT(DISTINCT p.patient_id) AS patient_count
FROM Prescription_Item pi
JOIN Prescription p ON p.prescription_id = pi.prescription_id
JOIN Medication  m ON m.med_id = pi.med_id
GROUP BY m.name
HAVING COUNT(DISTINCT p.patient_id) > 1;

-- ---------- 6. WINDOW FUNCTION: rank each medication's strongest safety signals ----------
SELECT m.name, s.reaction_term, s.prr,
       RANK() OVER (PARTITION BY s.med_id ORDER BY s.prr DESC) AS rk
FROM Adverse_Signal s
JOIN Medication m ON m.med_id = s.med_id
WHERE s.report_count >= 3
ORDER BY s.prr DESC;

-- ---------- 7. VIEW: all active (non-overridden) safety alerts ----------
SELECT * FROM v_active_alerts ORDER BY alert_id;
