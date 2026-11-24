"""Persist report-seriousness scores for alerts using the PostgreSQL admin role."""
import argparse
from statistics import mean

import sys
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from medisentinel import db
from ml.score import alert_inputs, predict_risk


def score_alerts(conn, rescore=False):
    written = []
    with conn.transaction():
        for row in alert_inputs(conn, only_unscored=not rescore):
            score = round(predict_risk(row["features"]), 3)
            update = conn.execute("""
                UPDATE Alert_Log SET risk_score = %s
                WHERE alert_id = %s AND (%s OR risk_score IS NULL)
            """, (score, row["alert_id"], rescore))
            if update.rowcount:
                written.append(score)
    return written


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rescore", action="store_true", help="Include already-scored alerts")
    args = parser.parse_args()
    with db.connect_as("ms_admin") as conn:
        scores = score_alerts(conn, args.rescore)
    print(f"Scored {len(scores):,} alerts.")
    if scores:
        print(f"Min {min(scores):.3f} | Mean {mean(scores):.3f} | Max {max(scores):.3f}")


if __name__ == "__main__":
    main()
