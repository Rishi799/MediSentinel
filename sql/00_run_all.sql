-- =====================================================================
--  MediSentinel — one-shot setup for psql (schema + demo data + queries).
--  Open "SQL Shell (psql)", log in as postgres, then run (forward slashes):
--     \i '<path to your clone>/sql/00_run_all.sql'
--  Afterwards run sql/roles.sql to create the login roles (see README).
-- =====================================================================

\echo >>> Creating database medisentinel ...
CREATE DATABASE medisentinel;

\c medisentinel

\echo >>> Building schema (tables, indexes, trigger, function, view) ...
\ir schema.sql

\echo >>> Loading seed data (this fires the safety trigger) ...
\ir seed_demo.sql

\echo >>> Running demonstrative queries ...
\ir queries.sql

\echo >>> Done. Active safety alerts:
SELECT * FROM v_active_alerts ORDER BY alert_id;
