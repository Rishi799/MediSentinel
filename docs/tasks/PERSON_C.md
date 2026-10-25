# Person C – Application: forms, login & validation (Phase 1)

You own **`app/`**: the Streamlit web app the examiner will use in the demo. It covers the lab's
*Design of Forms, Security & Validation* deliverable.

Before starting: finish **Setup** in the [README](../../README.md) and read [CONTRIBUTING.md](../../CONTRIBUTING.md).

Shared code you will call (written by Person A; ask before changing it). All of it is already tested:

```python
from medisentinel import db
from medisentinel.constants import GENDERS, ORGAN_FUNCTION, FREQUENCIES, DOSE_UNITS

conn = db.connect(username, password)   # wrong login -> psycopg.OperationalError
db.role_of(conn)                        # "doctor" / "pharmacist" / "admin"
db.list_patients(conn)   db.list_doctors(conn)   db.list_medications(conn, search="")   db.list_conditions(conn)
db.add_patient(conn, full_name, dob, gender, renal, hepatic, conditions=[...], allergies=[(med_id, reaction)])
db.create_prescription(conn, patient_id, doctor_id, [{"med_id": .., "dose": "500 mg", "frequency": "twice daily"}])
                                        # -> (prescription_id, alerts)
db.get_active_alerts(conn, patient_id=None)
db.override_alert(conn, alert_id, reason)
```

Logins for testing: `ms_doctor`, `ms_pharmacist`, `ms_admin`, with the passwords from **your** `.env`.

## Files

```
app/
├── Home.py              login page + welcome            run: streamlit run app/Home.py
├── session.py           login helpers shared by all pages
├── validation.py        pure validation functions (no Streamlit, no database), easy to test
└── pages/
    ├── 1_Patients.py
    ├── 2_Prescriptions.py
    └── 3_Alerts.py
```

---

## Task C1 – Login · branch `feature/app-login` · Day 1 morning

- `Home.py`: username + password form → `db.connect(...)`. On `psycopg.OperationalError` show
  "Invalid username or password" (never show the raw error). On success keep `conn` and
  `db.role_of(conn)` in `st.session_state` and show "Logged in as doctor".
- **Logout** button that closes the connection and clears the session.
- `session.py`: `require_login()` (stop the page with a message if not logged in) and
  `require_role(*roles)`. Every page starts with `require_login()`.
- Pharmacists see data but **no forms that write**. Hide them, and if a write still fails with
  `psycopg.errors.InsufficientPrivilege`, show "Your role is not allowed to do this".

## Task C2 – Validation · branch `feature/validation` · Day 1 morning (alongside C1)

`app/validation.py`: functions that **return a list of error messages** (empty = valid):

| Function | Rule |
|---|---|
| `validate_name(name)` | required; letters, spaces, `.` and `'` only; 2–100 characters |
| `validate_dob(dob)` | not in the future; age 0–120 |
| `validate_dose(dose)` | number + unit from `DOSE_UNITS`, e.g. `500 mg`, `2.5 ml` |
| `validate_items(items)` | at least one medicine; no medicine twice; each dose valid; frequency from `FREQUENCIES` |

`tests/test_validation.py`: test every rule, including one valid and one invalid example each.

## Task C3 – Patients page · branch `feature/patient-form` · Day 1 afternoon

`pages/1_Patients.py`, inside an `st.form`:
- full name, date of birth (`st.date_input`), gender (from `GENDERS`), kidney and liver function (from `ORGAN_FUNCTION`)
- **conditions**: multiselect from `db.list_conditions(conn)`
- **allergies**: multiselect of medicines (`db.list_medications`) + a reaction text for each
- On submit: run the validation functions → show **all** errors with `st.error` and do not save;
  if valid → `db.add_patient(...)` → `st.success("Patient #12 saved")`.
- Below the form: a table of existing patients (`db.list_patients`).

## Task C4 – Prescriptions page · branch `feature/prescription-form` · Day 2 morning

`pages/2_Prescriptions.py`:
- choose **patient** and **doctor** (selectboxes showing names, using the ids)
- "How many medicines?" (1–6), then one row per medicine: medicine (selectbox from
  `db.list_medications`), dose (text), frequency (selectbox from `FREQUENCIES`)
- validate with `validate_items` → errors, or save with `db.create_prescription(...)`
- **Show the alerts the trigger returned**: `MAJOR` with `st.error` (red), `MODERATE` with `st.warning`,
  `MINOR` with `st.info`; no alerts → `st.success("No safety issues found")`.
- Database errors get friendly messages (e.g. `UniqueViolation` → "This medicine is already in the prescription").

## Task C5 – Alerts page · branch `feature/alerts-page` · Day 2 afternoon

`pages/3_Alerts.py`:
- optional patient filter; table of `db.get_active_alerts(conn, patient_id)` (`st.dataframe`)
- **doctors only**: choose an alert, type a reason, **Override** → `db.override_alert(...)` → success
  message and the table refreshes. An empty reason shows an error.

## Done when

- [ ] The demo works through the app: doctor logs in → adds a patient with a peptic ulcer who is allergic to
      penicillin → prescribes Warfarin + Aspirin → **red MAJOR alerts** appear → overrides one with a reason
- [ ] Invalid input (future DOB, missing dose, the same medicine twice) shows clear errors and saves nothing
- [ ] `ms_pharmacist` can view but cannot add anything
- [ ] `python -m pytest` passes (including your validation tests); five pull requests merged by Person A

## In the viva, be ready to explain

How login uses **PostgreSQL roles** (the database, not the app, decides what each role may do);
why validation is done twice (in the form for friendly messages, and by database constraints as
the final guard); how the alerts reach the screen (trigger → `Alert_Log` → returned by
`create_prescription`).
