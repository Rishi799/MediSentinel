-- MediSentinel benchmark queries, run by tools/benchmark.py with EXPLAIN (ANALYZE, BUFFERS).
-- Each query starts with a "-- name:" line. %(patient)s and %(med)s are filled in by the script.

-- name: Q1 active alerts of one patient (Safety alerts page)
SELECT a.alert_id, a.alert_type, a.severity
FROM Alert_Log a
JOIN Prescription_Item pi ON pi.item_id = a.item_id
JOIN Prescription p ON p.prescription_id = pi.prescription_id
WHERE p.patient_id = %(patient)s AND NOT a.overridden;

-- name: Q2 active medicines of one patient (safety trigger and safety preview)
SELECT pi.med_id
FROM Prescription_Item pi
JOIN Prescription p ON p.prescription_id = pi.prescription_id
WHERE p.patient_id = %(patient)s AND p.status = 'ACTIVE';

-- name: Q3 interaction rule for one medicine pair (safety trigger)
SELECT severity FROM Interaction
WHERE med_id_1 = LEAST(%(med)s, 1) AND med_id_2 = GREATEST(%(med)s, 1);

-- name: Q4 prescriptions containing one medicine (signal and usage reports)
SELECT count(*) FROM Prescription_Item WHERE med_id = %(med)s;
