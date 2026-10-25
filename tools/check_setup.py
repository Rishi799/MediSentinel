"""Check that this machine is ready for MediSentinel: .env, PostgreSQL roles and MongoDB.

Run from the repo root:  python tools/check_setup.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pymongo import MongoClient  # noqa: E402

from medisentinel import config, db  # noqa: E402

ok = True


def report(passed, what, detail=""):
    global ok
    ok &= passed
    print(f"  [{'OK' if passed else 'FAIL'}] {what}" + (f" - {detail}" if detail else ""))


print("MediSentinel setup check")
report((ROOT / ".env").exists(), ".env file present", "" if (ROOT / ".env").exists() else "copy .env.example to .env")

for role in ("ms_doctor", "ms_pharmacist", "ms_admin"):
    try:
        with db.connect_as(role) as conn:
            tables = conn.execute("SELECT count(*) AS n FROM information_schema.tables "
                                  "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'").fetchone()["n"]
        report(tables == 11, f"PostgreSQL login as {role}", f"{tables} tables")
    except Exception as e:  # noqa: BLE001 - show any failure to the user
        report(False, f"PostgreSQL login as {role}", str(e).strip().splitlines()[0])

try:
    client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=3000)
    version = client.server_info()["version"]
    report(True, f"MongoDB at {config.MONGO_URI}", f"version {version}")
except Exception as e:  # noqa: BLE001
    report(False, f"MongoDB at {config.MONGO_URI}", str(e).splitlines()[0])

print("\nAll good." if ok else "\nFix the FAIL lines above (see README, 'Setup').")
sys.exit(0 if ok else 1)
