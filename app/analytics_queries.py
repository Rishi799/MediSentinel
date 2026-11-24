"""Read-only surveillance queries, executed with the signed-in PostgreSQL role."""
from medisentinel import db


def rule_totals(conn):
    return conn.execute("""
        SELECT 'Interaction' AS kind, count(*) AS total,
               count(source_label_id) AS learned
        FROM Interaction
        UNION ALL
        SELECT 'Contraindication', count(*), count(source_label_id)
        FROM Contraindication
    """).fetchall()


def alert_totals(conn):
    return conn.execute("""
        SELECT count(*) AS total, count(risk_score) AS scored,
               count(*) FILTER (WHERE overridden) AS overridden,
               (SELECT count(*) FROM Adverse_Signal) AS signals
        FROM Alert_Log
    """).fetchone()


def learned_by_severity(conn):
    return conn.execute("""
        WITH learned AS (
            SELECT 'Interaction' AS kind, severity
            FROM Interaction WHERE source_label_id IS NOT NULL
            UNION ALL
            SELECT 'Contraindication', severity
            FROM Contraindication WHERE source_label_id IS NOT NULL
        ), counts AS (
            SELECT kind, CASE WHEN severity IN ('MAJOR', 'MODERATE', 'MINOR')
                             THEN severity ELSE 'Unknown' END AS severity, count(*) AS rules
            FROM learned GROUP BY 1, 2
        )
        SELECT k.kind, s.severity, coalesce(c.rules, 0) AS rules
        FROM (VALUES ('Interaction'), ('Contraindication')) k(kind)
        CROSS JOIN (VALUES ('MAJOR'), ('MODERATE'), ('MINOR'), ('Unknown')) s(severity)
        LEFT JOIN counts c USING (kind, severity)
        ORDER BY k.kind, s.severity
    """).fetchall()


def risk_distribution(conn):
    return conn.execute("""
        WITH binned AS (
            SELECT least(floor(risk_score * 10)::int, 9) AS bin,
                   coalesce(severity, 'Unknown') AS severity
            FROM Alert_Log WHERE risk_score IS NOT NULL
        )
        SELECT bin / 10.0 AS lower, (bin + 1) / 10.0 AS upper, severity, count(*) AS alerts
        FROM binned GROUP BY bin, severity ORDER BY bin, severity
    """).fetchall()


def signal_map(conn):
    return conn.execute("""
        SELECT m.name AS medicine, s.reaction_term AS reaction, s.report_count AS reports,
               s.prr::float AS prr,
               CASE WHEN s.prr > %s THEN 'Above 2' ELSE '2 or below' END AS band
        FROM Adverse_Signal s JOIN Medication m USING (med_id)
        WHERE s.prr IS NOT NULL AND s.report_count IS NOT NULL
        ORDER BY s.prr DESC, s.signal_id
    """, (2,)).fetchall()


def alerts_by_department(conn):
    return conn.execute("""
        SELECT coalesce(nullif(trim(d.specialty), ''), 'Unspecified') AS department,
               coalesce(a.severity, 'Unknown') AS severity, count(*) AS alerts
        FROM Alert_Log a JOIN Prescription_Item i USING (item_id)
        JOIN Prescription p USING (prescription_id) JOIN Doctor d USING (doctor_id)
        GROUP BY 1, 2 ORDER BY 1, 2
    """).fetchall()


def recent_overrides(conn):
    return db.get_overridden_alerts(conn, limit=20)
