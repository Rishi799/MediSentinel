# Person B – Data & NoSQL (Phase 1)

You own **`ingestion/`**: getting real medicine data from openFDA into MongoDB, filling the
PostgreSQL `Medication` table from it, and generating realistic test data.
This is the project's **SQL ↔ NoSQL** part, so you will present it in the demo.

Before starting: finish **Setup** in the [README](../../README.md) and read [CONTRIBUTING.md](../../CONTRIBUTING.md).
Also install **MongoDB Compass** (free GUI) to look at your data.

Shared code you will use (written by Person A; ask before changing it):

```python
from medisentinel import config, db            # config.MONGO_URI, config.MONGO_DB
from medisentinel.constants import FREQUENCIES, ORGAN_FUNCTION, GENDERS
conn = db.connect_as("ms_admin")                # PostgreSQL login for scripts (password from .env)
```

---

## Task B1 – openFDA → MongoDB · branch `feature/openfda-ingestion` · Day 1 morning

**File:** `ingestion/load_openfda.py` · run: `python ingestion/load_openfda.py --labels 1000 --reports 5000`

1. Download **drug labels** that have an interaction section:
   `GET https://api.fda.gov/drug/label.json?search=_exists_:drug_interactions&limit=1000&skip=<n>`
2. Download **adverse-event reports**:
   `GET https://api.fda.gov/drug/event.json?limit=1000&skip=<n>`
3. Store each document **as it is** (raw JSON) in MongoDB database `medisentinel`:
   - labels → collection `medication_labels`, with `_id` = the label's `id`
   - reports → collection `adverse_reports`, with `_id` = `safetyreportid`
   - use **upserts** (`ReplaceOne(..., upsert=True)` in a `bulk_write`) so running the script twice
     does not create duplicates
4. Create indexes:
   - `medication_labels`: `openfda.generic_name`, `openfda.rxcui`
   - `adverse_reports`: `patient.drug.medicinalproduct`, `patient.reaction.reactionmeddrapt`
5. Be polite to the API: `limit` is at most 1000 per request, `skip` at most 25000; without an API key
   you get 240 requests/minute and 1000/day, so wait ~0.3 s between requests and retry on errors.
6. Print how many documents were stored in each collection.

## Task B2 – Medication loader · branch `feature/medication-loader` · Day 1 afternoon

**File:** `ingestion/load_medications.py` · run: `python ingestion/load_medications.py`

Fill the PostgreSQL `Medication` table from the labels in MongoDB.

| Medication column | From the label (`openfda` section) |
|---|---|
| `name` | `brand_name[0]` (fall back to `generic_name[0]`), Title Case, max 150 chars |
| `generic_name` | `generic_name[0]`, lower case, max 150 chars |
| `rxcui` | `rxcui[0]`, max 20 chars |
| `drug_class` | `pharm_class_epc[0]` without the trailing ` [EPC]`, max 100 chars (may be empty) |

- Put the mapping in a **pure function** `label_to_medication(label) -> dict | None` (returns `None` when
  the label has no generic name), so it can be tested without a database.
- Insert with `INSERT ... ON CONFLICT (rxcui) DO NOTHING`, and **skip** a label whose generic name
  already exists in `Medication` (so the 10 demo medicines, e.g. Warfarin, are not duplicated).
- Print: labels read, medications inserted, skipped.

## Task B3 – Synthetic test data · branch `feature/synthetic-data` · Day 2 morning

**File:** `ingestion/generate_synthetic.py` · run: `python ingestion/generate_synthetic.py --patients 100 --prescriptions 300 --seed 42`

Use **Faker** (`Faker("en_IN")`, seeded so the same seed gives the same data). No real patient data.

1. **10 doctors**: insert as `ms_admin` (doctors can't add doctors) with Indian names and a specialty.
2. **Patients**: create them with `db.add_patient(...)` logged in as `ms_doctor`:
   random DOB (age 18–90), gender from `GENDERS`, renal/hepatic from `ORGAN_FUNCTION` (mostly `normal`),
   0–3 conditions from `db.list_conditions(conn)`, 0–2 allergies to random medicines.
3. **Prescriptions**: create them with `db.create_prescription(...)` as `ms_doctor`, with 1–4 **different**
   medicines each (`random.sample`), a dose like `"500 mg"` and a frequency from `FREQUENCIES`.
   Using the `db` functions means the **trigger runs**, so you also get realistic alerts.
4. Print totals: doctors, patients, prescriptions, and **how many alerts the trigger raised**.

## Task B4 – Demo query on MongoDB · same branch as B3 · Day 2 morning

**File:** `ingestion/mongo_queries.py` · run: `python ingestion/mongo_queries.py`

Write `top_reactions(n=10)` and `top_reported_drugs(n=10)` using **aggregation pipelines**
(`$unwind` → `$group` → `$sort` → `$limit`) on `adverse_reports`, and print them as tables.
You'll run this live in the demo. Be ready to explain each pipeline stage.

## Tests (part of each task)

`tests/test_ingestion.py`: at least
- `label_to_medication` on a small hand-made label dict (normal case, missing brand name, missing generic name → `None`, `[EPC]` removed, long name truncated)

## Done when

- [ ] Compass shows ~1,000 labels and ~5,000 reports, with the indexes
- [ ] `Medication` has several hundred rows and the demo medicines are not duplicated
- [ ] 100 patients and 300 prescriptions generated; the script reports the alerts raised
- [ ] `python ingestion/mongo_queries.py` prints both top-10 tables
- [ ] `python -m pytest` passes; three pull requests merged by Person A

## In the viva, be ready to explain

Why labels and reports are in MongoDB and not PostgreSQL (nested, varying, high-volume JSON);
what an upsert is; what each aggregation stage does; how `load_medications.py` moves data
**from NoSQL into SQL**.
