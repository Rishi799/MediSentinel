"""Settings read from the .env file in the repo root (copy .env.example to .env)."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "medisentinel")

# passwords of the login roles on this machine, used by scripts and tests
# (people using the app type their own password on the login page)
ROLE_PASSWORDS = {
    "ms_doctor": os.getenv("MS_DOCTOR_PASSWORD"),
    "ms_pharmacist": os.getenv("MS_PHARMACIST_PASSWORD"),
    "ms_admin": os.getenv("MS_ADMIN_PASSWORD"),
}

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "medisentinel")
