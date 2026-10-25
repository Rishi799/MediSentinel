-- =====================================================================
--  MediSentinel — login roles and permissions (run as the postgres superuser)
--  Re-run after every schema.sql rebuild (dropping tables drops their grants).
--
--  psql -U postgres -d medisentinel -f sql/roles.sql \
--       -v doctor_pw=... -v pharmacist_pw=... -v admin_pw=...
-- =====================================================================

-- ---------- roles (created once, passwords reset on every run) ----------
SELECT 'CREATE ROLE ms_doctor'     WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ms_doctor')     \gexec
SELECT 'CREATE ROLE ms_pharmacist' WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ms_pharmacist') \gexec
SELECT 'CREATE ROLE ms_admin'      WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ms_admin')      \gexec

ALTER ROLE ms_doctor     WITH LOGIN PASSWORD :'doctor_pw';
ALTER ROLE ms_pharmacist WITH LOGIN PASSWORD :'pharmacist_pw';
ALTER ROLE ms_admin      WITH LOGIN PASSWORD :'admin_pw';

GRANT CONNECT ON DATABASE medisentinel TO ms_doctor, ms_pharmacist, ms_admin;
GRANT USAGE ON SCHEMA public TO ms_doctor, ms_pharmacist, ms_admin;

-- ---------- pharmacist: read only ----------
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ms_pharmacist;

-- ---------- doctor: read everything, write patients and prescriptions ----------
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ms_doctor;
GRANT INSERT ON Patient, Patient_Condition, Allergy, Prescription, Prescription_Item TO ms_doctor;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ms_doctor;
-- a doctor may override an alert but never create, edit or delete one:
-- alerts are written only by the SECURITY DEFINER trigger
GRANT UPDATE (overridden, override_reason) ON Alert_Log TO ms_doctor;

-- ---------- admin: full control (medication master, data loading) ----------
GRANT ALL ON ALL TABLES    IN SCHEMA public TO ms_admin;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO ms_admin;
