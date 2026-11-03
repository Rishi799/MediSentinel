# MediSentinel

**An Intelligent Medication Safety and Adverse-Reaction Surveillance System**
DBMS Laboratory Project (CD252IA) · RV College of Engineering · Dept. of CSE (AI & ML)

When a medicine is added to a patient's prescription, a database trigger checks it
against the patient's other active medicines (interactions), medical conditions
(contraindications) and allergies, and records an alert for anything unsafe.
Large openFDA datasets live in MongoDB and keep the safety rules up to date.

## Folder structure

```
MediSentinel/
├── README.md
├── CONTRIBUTING.md          how we use git (branches, pull requests, rules)
├── requirements.txt         Python packages
├── pyproject.toml           makes `medisentinel` importable everywhere (pip install -e .)
├── .env.example             copy to .env and fill in (never commit .env)
├── medisentinel/            shared Python code                                  (Person A)
│   ├── config.py            settings from .env
│   ├── constants.py         dropdown values shared by forms and test data
│   └── db/                  PostgreSQL functions used by the app and scripts
├── app/                     Streamlit forms, login, alerts pages                (Person C)
├── ingestion/               openFDA → MongoDB, Medication loader, test data     (Person B)
├── sql/
│   ├── schema.sql           tables, keys, constraints, indexes, trigger, function, view
│   ├── roles.sql            login roles ms_doctor / ms_pharmacist / ms_admin and their rights
│   ├── seed_demo.sql        sample data (fires the safety trigger)
│   ├── queries.sql          joins, subquery, aggregation, window function
│   └── 00_run_all.sql       one-shot schema + seed for psql
├── tests/                   automated tests (python -m pytest)
├── tools/
│   ├── check_setup.py       checks .env, PostgreSQL logins and MongoDB on your machine
│   └── run_demo.py          zero-install check of the SQL logic (Python sqlite3)
└── docs/
    ├── tasks/               PERSON_A.md, PERSON_B.md, PERSON_C.md: your task sheet
    ├── NORMALIZATION.md     UNF → 1NF → 2NF → 3NF → BCNF for all 11 tables
    ├── WORK_PLAN.md         who does what, phase by phase
    ├── PHASE1_SPRINT.md     Phase 1 as a 2-day sprint (hour by hour)
    ├── ER_Diagram_MediSentinel        ER diagram           (.png and .pdf)
    ├── Schema_Diagram_MediSentinel    relational mapping   (.png and .pdf)
    ├── DFD_MediSentinel               DFD levels 0, 1, 2   (.png and .pdf)
    └── manual/              A4 print files for the lab manual (18 mm margins)
```

## Setup (each member, once)

Needs **PostgreSQL 18**, **MongoDB 8** and **Python 3.13**.

1. **Clone and install**
   ```bash
   git clone https://github.com/Rishi799/MediSentinel.git
   cd MediSentinel
   py -3.13 -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   pip install -e .
   ```
2. **Create `.env`**: copy `.env.example` to `.env` and choose three passwords for
   `MS_DOCTOR_PASSWORD`, `MS_PHARMACIST_PASSWORD` and `MS_ADMIN_PASSWORD`.
3. **Build the database** (in a terminal, as the `postgres` user):
   ```bash
   createdb -U postgres medisentinel
   psql -U postgres -d medisentinel -f sql/schema.sql
   psql -U postgres -d medisentinel -f sql/seed_demo.sql
   psql -U postgres -d medisentinel -f sql/roles.sql -v doctor_pw=... -v pharmacist_pw=... -v admin_pw=...
   ```
   Use the same three passwords as in your `.env`. Re-run `roles.sql` whenever you rebuild `schema.sql`.
4. **Check everything:**
   ```bash
   python tools/check_setup.py
   python -m pytest
   ```
   All lines should say OK and all tests should pass.
5. **Load the openFDA data and demo patients** (once):
   ```bash
   python ingestion/load_openfda.py
   python ingestion/load_medications.py
   python ingestion/generate_synthetic.py
   ```

## Run the app

```bash
streamlit run app/Home.py
```

Sign in with `ms_doctor`, `ms_pharmacist` or `ms_admin` and the matching password from your `.env`.

| Page | What it shows |
|---|---|
| Dashboard | headline numbers, active alerts by type and severity, latest alerts and prescriptions |
| Patients | searchable records, a profile with conditions, allergies, active medicines and alerts; registration form |
| Prescriptions | new prescription beside the patient's safety context, the trigger's verdict as alert cards; history |
| Safety alerts | filters by patient, severity and type; doctor override with a reason; override audit trail |
| Drug safety data | openFDA labels and adverse-event reports from MongoDB, label lookup, PRR/ROR signals |

## Login roles

| Role | Can |
|---|---|
| `ms_doctor` | add patients, write prescriptions, view and override alerts |
| `ms_pharmacist` | view only |
| `ms_admin` | everything, including the medication master and data loading |

Alerts are written **only by the safety trigger** (`SECURITY DEFINER`); no login can create,
edit or delete an alert directly. A doctor can only mark one as overridden, with a reason.

## Data model

- **7 entity types:** Patient, Doctor, Prescription, Prescription_Item, Medication, Alert, Adverse_Signal
- **8 relationships:** Receives, Writes, Contains, For, Raises, Allergic_To, Interacts_With (recursive), Has_Signal
- **11 tables** (BCNF): Patient, Doctor, Medication, Prescription, Prescription_Item,
  Interaction, Contraindication, Patient_Condition, Allergy, Adverse_Signal, Alert_Log

## Technology

PostgreSQL 18 · MongoDB 8 · Python 3.13 (psycopg, pymongo, Streamlit) · openFDA + RxNorm data ·
Phase 2: spaCy/scispaCy (NLP), scikit-learn (ML)

## Status

| Phase | Scope | Status |
|---|---|---|
| Design | ER diagram, relational mapping, DFD, synopsis, SRS | Done |
| 1 | Database layer, login roles, MongoDB + openFDA data, forms with validation → Partial Demo | Done (tag `v1-partial-demo`) |
| 2 | NLP rule extraction, PRR/ROR signals, ML risk score, dashboard, paper and report | Planned ([PHASE2_PLAN_AND_SPECIFICATIONS.md](docs/PHASE2_PLAN_AND_SPECIFICATIONS.md)) |

## Team

| USN | Name | Role | Task sheet |
|---|---|---|---|
| | Rishi Agarwal | Person A – repo lead, database & integration | [PERSON_A.md](docs/tasks/PERSON_A.md) |
| | Sambhav | Person B – data & NoSQL | [PERSON_B.md](docs/tasks/PERSON_B.md) |
| | Priyanshi Gupta | Person C – application & AI | [PERSON_C.md](docs/tasks/PERSON_C.md) |
