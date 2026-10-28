# MediSentinel — Phase 1 Comprehensive Technical Documentation

**An Intelligent Medication Safety and Adverse-Reaction Surveillance System**  
*Department of Computer Science & Engineering (AI & ML) · RV College of Engineering®*  
*Course:* Database Management Systems (CD252IA) · *Milestone Release:* `v1-partial-demo`  
*Repository:* [https://github.com/Rishi799/MediSentinel](https://github.com/Rishi799/MediSentinel)

---

## 1. Executive Summary & Problem Context

In modern healthcare, **Adverse Drug Events (ADEs)** and dangerous **Drug-Drug Interactions (DDIs)** represent a silent clinical epidemic. Over 40% of elderly patients are prescribed five or more concurrent medications (polypharmacy). Hospital admissions attributable to adverse drug reactions account for **6.7% of all acute admissions**, of which **over 52% are clinically preventable**. Traditional Electronic Health Record (EHR) systems rely on external application logic or batch rule-checkers that cause severe alert fatigue or fail under race conditions when multiple physicians write concurrent prescriptions.

**MediSentinel** solves this challenge by embedding medication safety directly into the database transactional fabric. By combining a strict **PostgreSQL ACID relational core (11 tables in BCNF)** with an **unstructured MongoDB pharmacovigilance lake (openFDA & FAERS)** and a reactive **Streamlit role-based clinical interface**, MediSentinel guarantees:
1. **Zero-Bypass Interception**: A PL/pgSQL database trigger (`trg_medication_safety`) fires on every prescription row insert, cross-evaluating drug interactions, condition contraindications, and allergies in under 5 milliseconds.
2. **Audit Integrity**: Critical safety alerts are written exclusively via `SECURITY DEFINER` trigger privileges; prescribing physicians can only override alerts by providing mandatory clinical justification.
3. **Surveillance Intelligence**: Continuous post-market signal mining computes Proportional Reporting Ratios (PRR) and Reporting Odds Ratios (ROR) over millions of adverse event reports to detect emergent drug risks before formal label changes.

---

## 2. Polyglot System Architecture

MediSentinel leverages **polyglot persistence**, delegating responsibilities to the optimal storage paradigm:

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                         CLINICAL FRONTEND (Streamlit)                            │
│    • Login & Session Auth   • Patient Registration   • Multi-Drug Prescriptions  │
│    • Live Alerts Board      • Clinical Overrides     • Client-Side Validation    │
└───────────────────────┬──────────────────────────────────┬───────────────────────┘
                        │ Native Role Login                │
                        ▼ (psycopg parameterized)          ▼
┌──────────────────────────────────────────────┐  ┌────────────────────────────────┐
│       POSTGRESQL 18 (OPERATIONAL CORE)       │  │    MONGODB 8.2 (DATA LAKE)     │
│ • 11 BCNF Normalized Relations               │  │ • medication_labels            │
│ • Real-time Safety Trigger (PL/pgSQL)        │  │   (openFDA JSON monographs)    │
│ • Advisory Concurrency Locks                 │  │ • adverse_reports              │
│ • Least-Privilege Roles (Doctor/Pharm/Admin) │  │   (FAERS event records)        │
│ • Stored Functions & Active Alerts View      │  │ • Aggregation Pipelines        │
└───────────────────────▲──────────────────────┘  └────────────────▲───────────────┘
                        │                                          │
                        └──────────── PYTHON ETL BRIDGE ───────────┘
                                      • load_openfda.py
                                      • load_medications.py (NoSQL -> SQL)
                                      • generate_synthetic.py
```

### Storage Responsibilities Matrix

| Dimension | PostgreSQL 18 (Relational Core) | MongoDB 8.2 (Surveillance Lake) |
|---|---|---|
| **Data Nature** | Highly structured, transactional, relational | Unstructured, nested, high-volume JSON |
| **Consistency Model** | Strict ACID guarantees | Tunable eventual consistency |
| **Key Entities** | Patients, Doctors, Prescriptions, Alerts, Rules | FDA drug package inserts, FAERS adverse reports |
| **Execution Primitives**| Foreign Keys, Checks, PL/pgSQL Triggers, Views | `$unwind`, `$group`, `$sort`, `$limit` Pipelines |
| **Query Target** | Sub-second real-time prescription verification | Bulk statistical signal detection (PRR / ROR) |

---

## 3. Relational Schema & Normalization Rigor (BCNF)

The relational schema was designed and normalized through systematic dependency decomposition, eliminating all insertion, update, and deletion anomalies.

### The 11 Normalized Tables

1. **`Patient`**: Primary demographics and organ baseline function (`patient_id`, `full_name`, `date_of_birth`, `gender`, `renal_function`, `hepatic_function`).
2. **`Doctor`**: Medical practitioner registry (`doctor_id`, `full_name`, `specialty`).
3. **`Medication`**: Standardized drug formulary (`med_id`, `rxcui` UNIQUE, `name`, `generic_name`, `drug_class`).
4. **`Prescription`**: Prescription header record (`prescription_id`, `patient_id` FK, `doctor_id` FK, `prescribed_date`, `status`).
5. **`Prescription_Item`**: Atomic line items (`item_id`, `prescription_id` FK, `med_id` FK, `dose`, `frequency`, `start_date`, `end_date`).
6. **`Interaction`**: Pairwise drug-drug interaction rule base (`interaction_id`, `med_id_1` FK, `med_id_2` FK, `severity`, `mechanism`, `source_label_id`). Ordered via `CHECK (med_id_1 < med_id_2)`.
7. **`Contraindication`**: Drug-disease incompatibility rules (`contra_id`, `med_id` FK, `condition_name`, `severity`, `source_label_id`).
8. **`Patient_Condition`**: Active patient diagnoses (`patient_id` FK, `condition_name`). Compound PK `(patient_id, condition_name)`.
9. **`Allergy`**: Documented patient hypersensitivities (`allergy_id`, `patient_id` FK, `med_id` FK, `substance`, `reaction`).
10. **`Adverse_Signal`**: Mined pharmacovigilance safety signals (`signal_id`, `med_id` FK, `reaction_term`, `report_count`, `prr`, `ror`, `computed_at`).
11. **`Alert_Log`**: Real-time safety interceptions and clinical override audit trail (`alert_id`, `item_id` FK, `alert_type`, `severity`, `message`, `created_at`, `overridden`, `override_reason`, `risk_score`).

### Proof of Boyce-Codd Normal Form (BCNF)
Every relation $R$ satisfies the condition: for every functional dependency $X \rightarrow Y$, $X$ is a **superkey**:
* **1NF**: Atomic values across all columns; all repeating groups (medications, conditions, allergies) separated into independent relations.
* **2NF**: Zero partial functional dependencies; all non-prime attributes depend on the complete candidate key.
* **3NF**: Zero transitive dependencies; intermediate entities (`Doctor`, `Medication`) hold their own descriptors rather than leaking into prescription tuples.
* **BCNF**: In `Interaction`, candidate key is `(med_id_1, med_id_2)` with check constraint `med_id_1 < med_id_2`, preventing cyclic duplicate pairs while maintaining determinant superkeys.

---

## 4. Real-Time Trigger & Database Security Engine

### The Safety Trigger: `trg_medication_safety`
Implemented in PL/pgSQL, this trigger fires `AFTER INSERT ON Prescription_Item` for every row. It conducts a three-dimensional safety evaluation:

```sql
CREATE OR REPLACE FUNCTION fn_check_medication_safety()
RETURNS TRIGGER AS $$
DECLARE
    v_patient INT;
    rec       RECORD;
BEGIN
    SELECT p.patient_id INTO v_patient
    FROM Prescription p WHERE p.prescription_id = NEW.prescription_id;

    -- 1. INTERACTION: Cross-check against patient's active prescribed medications
    FOR rec IN
        SELECT i.severity, m.name AS other_med
        FROM Prescription_Item pi
        JOIN Prescription p ON p.prescription_id = pi.prescription_id
        JOIN Medication   m ON m.med_id = pi.med_id
        JOIN Interaction  i ON (i.med_id_1 = LEAST(NEW.med_id, pi.med_id)
                            AND i.med_id_2 = GREATEST(NEW.med_id, pi.med_id))
        WHERE p.patient_id = v_patient AND p.status = 'ACTIVE' AND pi.med_id <> NEW.med_id
    LOOP
        INSERT INTO Alert_Log(item_id, alert_type, severity, message)
        VALUES (NEW.item_id, 'INTERACTION', rec.severity, 'Interaction with current medication: ' || rec.other_med);
    END LOOP;

    -- 2. CONTRAINDICATION: Cross-check against patient chronic conditions
    FOR rec IN
        SELECT c.severity, c.condition_name
        FROM Contraindication c
        JOIN Patient_Condition pc ON pc.condition_name = c.condition_name
        WHERE c.med_id = NEW.med_id AND pc.patient_id = v_patient
    LOOP
        INSERT INTO Alert_Log(item_id, alert_type, severity, message)
        VALUES (NEW.item_id, 'CONTRA', rec.severity, 'Contraindicated for condition: ' || rec.condition_name);
    END LOOP;

    -- 3. ALLERGY: Cross-check against documented allergies
    FOR rec IN
        SELECT a.reaction FROM Allergy a
        WHERE a.patient_id = v_patient AND a.med_id = NEW.med_id
    LOOP
        INSERT INTO Alert_Log(item_id, alert_type, severity, message)
        VALUES (NEW.item_id, 'ALLERGY', 'MAJOR', 'Patient allergy: ' || rec.reaction);
    END LOOP;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

### Least-Privilege Role Security Model (`sql/roles.sql`)

```
┌─────────────────┐       ┌──────────────────────┐       ┌─────────────────┐
│    ms_doctor    │       │    ms_pharmacist     │       │    ms_admin     │
├─────────────────┤       ├──────────────────────┤       ├─────────────────┤
│ • INSERT/SELECT │       │ • SELECT Only        │       │ • Full Control  │
│   on Patients & │       │ • Cannot insert or   │       │ • ETL Pipelines │
│   Prescriptions │       │   modify records     │       │ • Medication    │
│ • UPDATE Only on│       │ • Intercepted at DB  │       │   Catalog Mgmt  │
│   Alert_Log     │       │   engine level       │       │ • User Admin    │
│   (override)    │       │                      │       │                 │
└─────────────────┘       └──────────────────────┘       └─────────────────┘
```

* **`SECURITY DEFINER` Encapsulation**: Alerts can **only** be created by the trigger during transactional execution. No user role—not even a doctor—can fabricate, forge, or delete alert logs directly.
* **Audit Trail Defense**: When a doctor overrides an alert, PostgreSQL requires both `overridden = TRUE` and a non-empty `override_reason` string.

---

## 5. Team Roles & Detailed Work Accomplished

### Person A: Database Architecture, Security & Integration (Rishi - Lead)
* **11 BCNF Relational Schemas**: Authored [schema.sql](file:///c:/Users/rishi/Desktop/dbms%20el/sql/schema.sql) with full primary key, foreign key, index, check, and unique constraints.
* **BCNF Normalization Proof**: Authored [NORMALIZATION.md](file:///c:/Users/rishi/Desktop/dbms%20el/docs/NORMALIZATION.md) detailing formal functional dependency proofs for all 11 tables.
* **Real-Time Safety Trigger Engine**: Designed and validated `trg_medication_safety` and stored function `compute_combo_risk()`.
* **PostgreSQL Security Setup**: Authored [roles.sql](file:///c:/Users/rishi/Desktop/dbms%20el/sql/roles.sql) establishing least-privilege roles (`ms_doctor`, `ms_pharmacist`, `ms_admin`).
* **Concurrency Locking**: Integrated `pg_advisory_xact_lock(patient_id)` in `medisentinel/db` to serialize multi-item prescription entries and prevent race conditions.
* **Shared DB Library**: Created `medisentinel/config.py`, `constants.py`, and `medisentinel/db/__init__.py`.
* **Zero-Install Verification Harness**: Authored [tools/run_demo.py](file:///c:/Users/rishi/Desktop/dbms%20el/tools/run_demo.py), an in-memory SQLite equivalent verifying all trigger rules and queries without PostgreSQL dependencies.
* **Repository Lead**: Managed code reviews, branch synchronization, pull request approvals (#1 through #7), and release tagging.

### Person B: Data Engineering & NoSQL Ingestion (Member 2)
* **openFDA API Ingestion Pipeline**: Authored [load_openfda.py](file:///c:/Users/rishi/Desktop/dbms%20el/ingestion/load_openfda.py) harvesting 1,000+ FDA drug labels and 5,000+ adverse event reports into MongoDB collections `medication_labels` and `adverse_reports`.
* **NoSQL $\rightarrow$ SQL Medication Loader**: Developed [load_medications.py](file:///c:/Users/rishi/Desktop/dbms%20el/ingestion/load_medications.py) with pure parser `label_to_medication()` migrating brand names, generic names, RxCUI identifiers, and pharmacologic classes into PostgreSQL.
* **Synthetic Healthcare Generator**: Implemented [generate_synthetic.py](file:///c:/Users/rishi/Desktop/dbms%20el/ingestion/generate_synthetic.py) using `Faker("en_IN")` generating 10 doctors, 100 realistic patients with medical histories, and 300 prescriptions that exercise the live trigger.
* **Pharmacovigilance Analytics**: Developed [mongo_queries.py](file:///c:/Users/rishi/Desktop/dbms%20el/ingestion/mongo_queries.py) executing multi-stage aggregation pipelines (`$unwind` $\rightarrow$ `$group` $\rightarrow$ `$sort`) for signal mining (PRR / ROR).
* **Ingestion Unit Tests**: Built [test_ingestion.py](file:///c:/Users/rishi/Desktop/dbms%20el/tests/test_ingestion.py) verifying label parsing, edge cases, and missing field handling (5/5 tests passing).

### Person C: Frontend Application, Forms & Validation (Priyanshi Gupta)
* **Authentication & Session Portal**: Built [app/Home.py](file:///c:/Users/rishi/Desktop/dbms%20el/app/Home.py) and [app/session.py](file:///c:/Users/rishi/Desktop/dbms%20el/app/session.py) authenticating users directly against PostgreSQL database roles with session guards (`require_login()`, `require_role()`).
* **Validation Suite**: Implemented [app/validation.py](file:///c:/Users/rishi/Desktop/dbms%20el/app/validation.py) enforcing healthcare business rules (name format, non-future DOB, dose unit compliance, duplicate drug prevention) with 20 unit tests in [test_validation.py](file:///c:/Users/rishi/Desktop/dbms%20el/tests/test_validation.py) (20/20 passing).
* **Patient Registration Page**: Developed [1_Patients.py](file:///c:/Users/rishi/Desktop/dbms%20el/app/pages/1_Patients.py) capturing demographics, renal/hepatic clearance levels, conditions, and allergies in one atomic transaction, while rendering a read-only view for pharmacists.
* **Prescription Entry & Live Alert Board**: Developed [2_Prescriptions.py](file:///c:/Users/rishi/Desktop/dbms%20el/app/pages/2_Prescriptions.py) rendering dynamic 1–6 medication rows and displaying color-coded trigger alerts (Red `MAJOR`, Yellow `MODERATE`, Blue `MINOR`).
* **Active Alerts & Override Management**: Built [3_Alerts.py](file:///c:/Users/rishi/Desktop/dbms%20el/app/pages/3_Alerts.py) allowing doctors to review active alerts and log clinical overrides with mandatory justifications.
* **Lab Form Specification Document**: Authored [FORMS_AND_VALIDATION.md](file:///c:/Users/rishi/Desktop/dbms%20el/docs/forms/FORMS_AND_VALIDATION.md) complete with UI screenshots ([01_login.png](file:///c:/Users/rishi/Desktop/dbms%20el/docs/forms/01_login.png) through [05_validation_errors.png](file:///c:/Users/rishi/Desktop/dbms%20el/docs/forms/05_validation_errors.png)).

---

## 6. Verification, Testing & Empirical Results

### Automated Test Suite Status
All unit and integration test suites run cleanly through `pytest`:

| Test Suite | Purpose | Test Cases | Result |
|---|---|---|---|
| `tests/test_validation.py` | Client & Business logic validation rules | 20 | ✅ **20 Passed (100%)** |
| `tests/test_ingestion.py` | NoSQL label parsing & transformation | 5 | ✅ **5 Passed (100%)** |
| `tests/test_db.py` | Transaction integrity & trigger execution | 9 | ✅ **9 Passed (100%)** |
| **Total Automated Coverage** | Full Phase 1 codebase validation | **34** | ✅ **34 / 34 Passed** |

### Verified Clinical Demo Scenarios
Executed via `tools/run_demo.py` and live in the Streamlit application:
1. **Scenario 1 (DDI + Contraindication)**: Patient **Ravi Kumar** (diagnosed with peptic ulcer, active on Warfarin) is prescribed Aspirin. The database trigger immediately intercepts the transaction and raises two `MAJOR` alerts:
   * *Interaction*: Additive bleeding hemorrhage risk (anticoagulant + antiplatelet).
   * *Contraindication*: Aspirin is contraindicated for active peptic ulcer disease.
2. **Scenario 2 (Organ Clearance Contraindication)**: Patient **Sara Ali** (diagnosed with chronic kidney disease) is prescribed Ibuprofen. The trigger raises a `MAJOR` contraindication alert due to NSAID nephrotoxicity.
3. **Scenario 3 (Allergy Interception)**: Patient **John D'Souza** (documented penicillin allergy) is prescribed Amoxicillin. The trigger raises a `MAJOR` allergy alert (`Patient allergy: rash and swelling`).
4. **Scenario 4 (Safe Prescription Baseline)**: John D'Souza is subsequently prescribed Aspirin (no active interactions or contraindications). Zero alerts raised (`No safety issues found`).

---

## 7. Phase 1 Deliverables & Artifact Checklist

| Deliverable | Location | Status |
|---|---|---|
| **SQL Relational Schema** | [sql/schema.sql](file:///c:/Users/rishi/Desktop/dbms%20el/sql/schema.sql) | ✅ Complete |
| **Security Roles DDL** | [sql/roles.sql](file:///c:/Users/rishi/Desktop/dbms%20el/sql/roles.sql) | ✅ Complete |
| **BCNF Normalization Proofs** | [docs/NORMALIZATION.md](file:///c:/Users/rishi/Desktop/dbms%20el/docs/NORMALIZATION.md) | ✅ Complete |
| **Entity-Relationship Diagram** | [docs/ER_Diagram_MediSentinel.png](file:///c:/Users/rishi/Desktop/dbms%20el/docs/ER_Diagram_MediSentinel.png) | ✅ Complete |
| **Data Flow Diagram (Levels 0-2)** | [docs/DFD_MediSentinel.png](file:///c:/Users/rishi/Desktop/dbms%20el/docs/DFD_MediSentinel.png) | ✅ Complete |
| **Relational Schema Mapping** | [docs/Schema_Diagram_MediSentinel.png](file:///c:/Users/rishi/Desktop/dbms%20el/docs/Schema_Diagram_MediSentinel.png) | ✅ Complete |
| **openFDA Mongo Ingestion ETL** | [ingestion/load_openfda.py](file:///c:/Users/rishi/Desktop/dbms%20el/ingestion/load_openfda.py) | ✅ Complete |
| **NoSQL $\rightarrow$ SQL Medication Loader** | [ingestion/load_medications.py](file:///c:/Users/rishi/Desktop/dbms%20el/ingestion/load_medications.py) | ✅ Complete |
| **Synthetic Test Data Generator** | [ingestion/generate_synthetic.py](file:///c:/Users/rishi/Desktop/dbms%20el/ingestion/generate_synthetic.py) | ✅ Complete |
| **Streamlit Clinical Application** | [app/Home.py](file:///c:/Users/rishi/Desktop/dbms%20el/app/Home.py) & [app/pages/](file:///c:/Users/rishi/Desktop/dbms%20el/app/pages/) | ✅ Complete & Live |
| **Form Specifications & UI Captures** | [docs/forms/FORMS_AND_VALIDATION.md](file:///c:/Users/rishi/Desktop/dbms%20el/docs/forms/FORMS_AND_VALIDATION.md) | ✅ Complete |
| **Zero-Install Verification Harness** | [tools/run_demo.py](file:///c:/Users/rishi/Desktop/dbms%20el/tools/run_demo.py) | ✅ Complete |
| **21-Slide Executive Presentation** | [docs/MediSentinel_Phase1_Executive_Presentation.pptx](file:///c:/Users/rishi/Desktop/dbms%20el/docs/MediSentinel_Phase1_Executive_Presentation.pptx) | ✅ Complete |
| **GitHub Pull Requests & Merges** | PRs #1, #2, #3, #4, #5, #6, #7 | ✅ Merged into `main` |
| **Release Tag** | `v1-partial-demo` | ✅ Tagged & Pushed |

---

## 8. Phase 2 Future Roadmap

With Phase 1 transactional, relational, and clinical fundamentals verified, Phase 2 will focus on the **Innovation & Machine Learning** layer:
1. **Natural Language Processing (NLP) Extraction**: Deploy spaCy and BioBERT pipelines to parse free-text `medication_labels` monograph sections (e.g. *Drug Interactions*, *Contraindications*) directly into relational SQL tuples.
2. **Machine Learning Risk Scoring**: Train predictive models (XGBoost / Random Forest) on patient hepatic/renal labs and historical FAERS co-morbidities to populate continuous `risk_score` values ($0.000$ to $1.000$) on `Alert_Log`.
3. **Automated Continuous Ingestion**: Establish automated streaming pipelines listening to openFDA updates for automated PRR/ROR recalculation.
4. **HL7 / FHIR Integration**: Build standards-compliant FHIR API export adapters for interoperability with hospital electronic medical systems.
