-- MediSentinel: invalid writes that the database itself must refuse.
-- Run:  psql -U ms_admin -d medisentinel -v VERBOSITY=terse -f sql/test_invalid_inserts.sql
-- Every statement below breaks a rule, so nothing is saved.

-- gender must be M, F or O
INSERT INTO Patient(full_name, date_of_birth, gender) VALUES ('Test Patient', '1990-01-01', 'X');
-- a patient must have a name
INSERT INTO Patient(full_name, date_of_birth, gender) VALUES (NULL, '1990-01-01', 'F');
-- a prescription must belong to an existing patient
INSERT INTO Prescription(patient_id, doctor_id) VALUES (999999, 1);
-- the same medicine cannot appear twice in one prescription (item 1 is Warfarin in prescription 1)
INSERT INTO Prescription_Item(prescription_id, med_id, dose, frequency) VALUES (1, 1, '5 mg', 'once daily');
-- an interaction pair is stored once, with the smaller id first
INSERT INTO Interaction(med_id_1, med_id_2, severity) VALUES (2, 1, 'MAJOR');
-- two medicines cannot share one RxNorm id
INSERT INTO Medication(rxcui, name) VALUES ('11289', 'Duplicate Warfarin');
-- a risk score must lie between 0 and 1
UPDATE Alert_Log SET risk_score = 1.5 WHERE alert_id = (SELECT min(alert_id) FROM Alert_Log);
