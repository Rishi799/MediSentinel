-- =====================================================================
--  MediSentinel — seed data (PostgreSQL)
--  Run AFTER schema.sql:  psql -d medisentinel -f sql/seed_demo.sql
--  Populates a realistic slice and demonstrates the safety trigger firing.
-- =====================================================================

-- ---------- doctors ----------
INSERT INTO Doctor(full_name, specialty) VALUES
  ('Dr. A Rao',   'Cardiology'),      -- 1
  ('Dr. B Nair',  'Dentistry'),       -- 2
  ('Dr. C Mehta', 'General Medicine');-- 3

-- ---------- patients ----------
INSERT INTO Patient(full_name, date_of_birth, gender, renal_function) VALUES
  ('Ravi Kumar',   '1958-04-12', 'M', 'impaired'),  -- 1
  ('Sara Ali',     '1972-09-30', 'F', 'severe'),    -- 2
  ('John DSouza',  '1990-01-08', 'M', 'normal');    -- 3

-- ---------- medications ----------
INSERT INTO Medication(rxcui, name, generic_name, drug_class) VALUES
  ('11289', 'Warfarin',       'warfarin',       'Anticoagulant'),      -- 1
  ('1191',  'Aspirin',        'aspirin',        'Antiplatelet/NSAID'), -- 2
  ('6809',  'Metformin',      'metformin',      'Biguanide'),          -- 3
  ('5640',  'Ibuprofen',      'ibuprofen',      'NSAID'),              -- 4
  ('29046', 'Lisinopril',     'lisinopril',     'ACE inhibitor'),      -- 5
  ('9997',  'Spironolactone', 'spironolactone', 'K-sparing diuretic'),  -- 6
  ('36567', 'Simvastatin',    'simvastatin',    'Statin'),             -- 7
  ('21212', 'Clarithromycin', 'clarithromycin', 'Macrolide antibiotic'),-- 8
  ('723',   'Amoxicillin',    'amoxicillin',    'Penicillin antibiotic'),-- 9
  ('36437', 'Sertraline',     'sertraline',     'SSRI');               -- 10

-- ---------- interaction knowledge base (normally filled by the NLP pipeline) ----------
-- stored once per pair with med_id_1 < med_id_2
INSERT INTO Interaction(med_id_1, med_id_2, severity, mechanism) VALUES
  (1, 2, 'MAJOR',    'Additive bleeding risk (anticoagulant + antiplatelet)'),
  (1, 4, 'MAJOR',    'Additive bleeding risk (anticoagulant + NSAID)'),
  (2, 4, 'MODERATE', 'Increased GI bleeding (two NSAIDs)'),
  (5, 6, 'MAJOR',    'Hyperkalemia (ACE inhibitor + K-sparing diuretic)'),
  (7, 8, 'MAJOR',    'Rhabdomyolysis (statin + macrolide inhibits CYP3A4)'),
  (1, 7, 'MODERATE', 'Warfarin effect potentiated by simvastatin');

-- ---------- contraindications (medication vs condition) ----------
INSERT INTO Contraindication(med_id, condition_name, severity) VALUES
  (2, 'peptic ulcer',            'MAJOR'),
  (4, 'chronic kidney disease',  'MAJOR'),
  (3, 'renal failure',           'MAJOR'),
  (6, 'hyperkalemia',            'MODERATE');

-- ---------- patient conditions ----------
INSERT INTO Patient_Condition(patient_id, condition_name) VALUES
  (1, 'peptic ulcer'),
  (1, 'hypertension'),
  (2, 'chronic kidney disease');

-- ---------- allergies ----------
INSERT INTO Allergy(patient_id, med_id, substance, reaction) VALUES
  (3, 9, 'penicillin', 'rash and swelling');

-- ---------- adverse-event signals (normally written by the PRR/ROR pipeline) ----------
INSERT INTO Adverse_Signal(med_id, reaction_term, report_count, prr, ror) VALUES
  (7, 'rhabdomyolysis',              40,  8.500, 9.100),
  (1, 'haemorrhage',                120,  5.200, 5.600),
  (4, 'gastrointestinal haemorrhage',60,  4.000, 4.200),
  (3, 'lactic acidosis',             25,  3.100, 3.200),
  (10,'nausea',                     200,  1.100, 1.100);

-- =====================================================================
--  Prescriptions — each new item runs the safety trigger automatically
-- =====================================================================

-- P1: Ravi (peptic ulcer, on Warfarin) is now given Aspirin
INSERT INTO Prescription(patient_id, doctor_id) VALUES (1, 1);              -- prescription 1
INSERT INTO Prescription_Item(prescription_id, med_id, dose) VALUES (1, 1, '5 mg');   -- Warfarin
INSERT INTO Prescription_Item(prescription_id, med_id, dose) VALUES (1, 2, '75 mg');  -- Aspirin -> INTERACTION + CONTRA

-- P2: Sara (chronic kidney disease) is given Ibuprofen
INSERT INTO Prescription(patient_id, doctor_id) VALUES (2, 3);              -- prescription 2
INSERT INTO Prescription_Item(prescription_id, med_id, dose) VALUES (2, 4, '400 mg'); -- Ibuprofen -> CONTRA

-- P3: John (allergic to penicillin) is given Amoxicillin
INSERT INTO Prescription(patient_id, doctor_id) VALUES (3, 3);              -- prescription 3
INSERT INTO Prescription_Item(prescription_id, med_id, dose) VALUES (3, 9, '500 mg'); -- Amoxicillin -> ALLERGY

-- P4: John is also given Aspirin (no condition/interaction for him -> no alert;
--     this makes Aspirin a medication shared across two patients for the reports)
INSERT INTO Prescription(patient_id, doctor_id) VALUES (3, 2);              -- prescription 4
INSERT INTO Prescription_Item(prescription_id, med_id, dose) VALUES (4, 2, '75 mg');  -- Aspirin (safe here)

-- ---------- inspect what the trigger produced ----------
SELECT * FROM v_active_alerts ORDER BY alert_id;
