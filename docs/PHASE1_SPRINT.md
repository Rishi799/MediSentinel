# Phase 1 – 2-Day Sprint

**Goal by end of Day 2:** a doctor logs in, registers a patient, writes a multi-medicine prescription,
and the trigger shows safety alerts in the app, with real openFDA data in MongoDB.
Tag the repo `v1-partial-demo`.

| Member | Role | Works in |
|---|---|---|
| **Member 1 – you** | Repo lead · Database & integration | `sql/`, `medisentinel/db/`, repo setup |
| Member 2 | Data & NoSQL | `ingestion/` |
| Member 3 | Application (forms, login, validation) | `app/` |

---

## Day 1, 9:30 kickoff (all three, 30 min): agree on these and don't change them later

**1. Database functions** (Member 1 writes them; Member 3 calls them from the forms)

**Done ✓**: implemented and tested (`python -m pytest`). Rows come back as dicts.

```python
from medisentinel import db
conn = db.connect(username, password)        # log in as a PostgreSQL role (wrong login -> OperationalError)
db.role_of(conn)                             # -> "doctor" / "pharmacist" / "admin"
db.list_doctors(conn)                        # -> [{doctor_id, full_name, specialty}]
db.list_patients(conn)                       # -> [{patient_id, full_name, date_of_birth, gender}]
db.list_medications(conn, search="")         # -> [{med_id, name, generic_name}]
db.list_conditions(conn)                     # -> ["asthma", "peptic ulcer", ...]
db.add_patient(conn, full_name, dob, gender, renal, hepatic,
               conditions=[...], allergies=[(med_id, reaction), ...])    # -> patient_id
db.create_prescription(conn, patient_id, doctor_id,
                       [{"med_id": .., "dose": "500 mg", "frequency": "twice daily"}])
                                             # -> (prescription_id, [alerts raised by the trigger])
db.get_active_alerts(conn, patient_id=None)  # -> rows of v_active_alerts
db.override_alert(conn, alert_id, reason)    # -> True if overridden
```
Scripts and tests log in with `db.connect_as("ms_admin")` (passwords from `.env`).

**2. Login = PostgreSQL roles.** No extra users table, so the schema stays at 11 tables. The login form
connects to PostgreSQL with the typed username/password. The role decides what the user can do:

| Role | Can |
|---|---|
| `ms_doctor` | add patients, write prescriptions, view/override alerts |
| `ms_pharmacist` | view prescriptions and alerts only |
| `ms_admin` | everything, including the medication master |

**3. MongoDB layout** (Member 2 creates it)
- Database `medisentinel`, collections `medication_labels` and `adverse_reports`

---

## Day 1

| Time | Member 1 – you | Member 2 – Data & NoSQL | Member 3 – Application |
|---|---|---|---|
| **10:00–13:00** | • Create the GitHub repo, protect `main`, add both members<br>• ✓ `requirements.txt`, `.env.example`, `.gitignore`<br>• ✓ Apply `schema.sql`; help each member run `tools/check_setup.py` | • Install MongoDB + Compass<br>• `ingestion/load_openfda.py`: download ~1,000 drug labels and ~5,000 adverse-event reports from the openFDA API into the two collections | • Streamlit skeleton: sidebar navigation, page per form<br>• **Login page** calling `connect()`; show pages by role |
| **14:00–18:00** | • ✓ DB functions above: parameterized queries only<br>• ✓ `create_prescription`: header + all items in **one transaction**, with a per-patient advisory lock (stops two doctors racing)<br>• ✓ The 3 roles with `GRANT`s (`sql/roles.sql`); alerts writable only by the trigger | • Indexes on both collections (`openfda.generic_name`, `patient.drug.medicinalproduct`)<br>• `ingestion/load_medications.py`: fill the SQL `Medication` table from the label documents (name, generic name, RxCUI, class) | • **Patient form:** name, DOB, gender, kidney/liver function, conditions, allergies<br>• Validation (rules below), clear error messages |
| **18:00 sync (30 min)** | Merge everyone's branches; run the app once end to end | Show the data in Compass | Show the forms working |

## Day 2

| Time | Member 1 – you | Member 2 – Data & NoSQL | Member 3 – Application |
|---|---|---|---|
| **10:00–13:00** | • **Normalization document** (functional dependencies, 1NF → BCNF for all 11 tables) for the Week 6 submission<br>• Help Member 3 wire the forms to the DB functions | • `ingestion/generate_synthetic.py`: 100 patients, 10 doctors, 300 prescriptions with realistic conditions/allergies (privacy-safe test data)<br>• One demo aggregation query (e.g. top 10 reported reactions) | • **Prescription form:** pick patient + doctor, add several medicines (dose, frequency)<br>• After saving, show the alerts the trigger raised (red for MAJOR) |
| **14:00–16:00** | Code review and merge of all pull requests | Test the forms with the synthetic data; report bugs | **Alerts page:** list active alerts, override with a reason |
| **16:00–18:00 (all)** | Lead the demo rehearsal; fix the last bugs; tag `v1-partial-demo` | Present the MongoDB part of the demo | Present the forms and validation |

---

## Validation rules (Member 3 implements them; Member 1's constraints back them up in the DB)

| Field | Rule |
|---|---|
| Name | required, letters and spaces, 2–100 characters |
| Date of birth | not in the future; age 0–120 |
| Gender | M / F / O only (dropdown) |
| Kidney / liver function | dropdown: normal, impaired, severe |
| Medicine | chosen from the list (no free text) |
| Dose | required, a number plus a unit (e.g. `500 mg`) |
| Frequency | dropdown (once daily, twice daily, …) |
| Prescription | at least one medicine; the same medicine not twice |

## Security checklist
- [ ] Login through PostgreSQL roles; each role has only the rights it needs (`GRANT`)
- [ ] All SQL uses parameters (`%s`), never string concatenation, to prevent SQL injection
- [ ] Passwords only in `.env` (never committed); `.env.example` shows the format
- [ ] Prescription saved in one transaction; any error rolls everything back

## Demo script (Day 2, 16:00)
1. Log in as `ms_doctor`.
2. Register a patient with a peptic ulcer, already on Warfarin.
3. Write a prescription adding Aspirin → **MAJOR interaction + contraindication alerts appear**.
4. Try an invalid form (future DOB, missing dose) → validation errors shown.
5. Log in as `ms_pharmacist` → can view, cannot write (the database refuses it).
6. Open MongoDB Compass → real openFDA labels and reports; run the aggregation query.

## Done when
- [ ] Every item in the demo script works from a fresh clone of `main`
- [ ] Normalization document written
- [ ] All three branches merged, `v1-partial-demo` tagged
