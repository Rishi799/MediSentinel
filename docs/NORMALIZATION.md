# MediSentinel – Normalization

This document shows how the MediSentinel tables were normalized, starting from a single
unnormalized prescription record and ending with the 11 tables in `sql/schema.sql`,
all of which are in **BCNF** (and therefore also in 3NF).

---

## 1. The unnormalized relation (UNF)

A paper prescription, written down as one record, contains everything at once:

```
PRESCRIPTION_RECORD (
    prescription_id, prescribed_date, status,
    patient_id, patient_name, date_of_birth, gender, renal_function, hepatic_function,
    { condition_name },                                   -- repeating group
    { allergy_med_id, allergy_reaction },                 -- repeating group
    doctor_id, doctor_name, specialty,
    { med_id, med_name, generic_name, rxcui, drug_class,  -- repeating group
      dose, frequency, start_date, end_date }
)
```

**Problems**

| Anomaly | Example |
|---|---|
| Insertion | A new medicine cannot be recorded until someone prescribes it. |
| Update | Changing Aspirin's drug class means editing every prescription that contains Aspirin. |
| Deletion | Deleting a patient's only prescription also loses the patient's name and allergies. |
| Repeating groups | A prescription with 3 medicines needs 3 sets of medicine columns, so the number of columns is not fixed. |

---

## 2. First Normal Form (1NF)

**Rule:** every attribute holds a single (atomic) value; no repeating groups.

The three repeating groups are moved into their own relations, each keeping the key it belongs to:

```
PRESCRIPTION_LINE ( prescription_id, med_id,                      -- key
                    prescribed_date, status,
                    patient_id, patient_name, date_of_birth, gender, renal_function, hepatic_function,
                    doctor_id, doctor_name, specialty,
                    med_name, generic_name, rxcui, drug_class,
                    dose, frequency, start_date, end_date )

PATIENT_CONDITION ( patient_id, condition_name )                  -- key: both columns
ALLERGY           ( patient_id, med_id, reaction )                -- key: (patient_id, med_id)
```

Every cell now holds one value and every row has the same number of columns.
`PRESCRIPTION_LINE` still mixes facts about the prescription, the patient, the doctor and
the medicine, so the redundancy remains.

---

## 3. Second Normal Form (2NF)

**Rule:** 1NF, and no non-key attribute depends on only *part* of a composite key.

The key of `PRESCRIPTION_LINE` is `(prescription_id, med_id)`. Its functional dependencies are:

| Dependency | Type |
|---|---|
| `prescription_id → prescribed_date, status, patient_id, …, doctor_id, …` | **partial** (needs only part of the key) |
| `med_id → med_name, generic_name, rxcui, drug_class` | **partial** |
| `(prescription_id, med_id) → dose, frequency, start_date, end_date` | full |

Removing the partial dependencies splits the relation into three:

```
PRESCRIPTION      ( prescription_id, prescribed_date, status,
                    patient_id, patient_name, date_of_birth, gender, renal_function, hepatic_function,
                    doctor_id, doctor_name, specialty )
MEDICATION        ( med_id, name, generic_name, rxcui, drug_class )
PRESCRIPTION_ITEM ( prescription_id, med_id, dose, frequency, start_date, end_date )
```

`PATIENT_CONDITION` and `ALLERGY` are already in 2NF: they have no attributes outside their keys
that depend on part of the key.

---

## 4. Third Normal Form (3NF)

**Rule:** 2NF, and no non-key attribute depends on another non-key attribute
(no transitive dependency).

`PRESCRIPTION` still has two transitive dependencies:

```
prescription_id → patient_id → patient_name, date_of_birth, gender, renal_function, hepatic_function
prescription_id → doctor_id  → doctor_name, specialty
```

Moving the patient and doctor details into their own relations removes them:

```
PATIENT      ( patient_id, full_name, date_of_birth, gender, renal_function, hepatic_function, created_at )
DOCTOR       ( doctor_id, full_name, specialty )
PRESCRIPTION ( prescription_id, patient_id → PATIENT, doctor_id → DOCTOR, prescribed_date, status )
```

**Implementation choices made at this step**

- `PRESCRIPTION_ITEM` gets a surrogate key `item_id`, because `ALERT_LOG` refers to individual items.
  The natural key `(prescription_id, med_id)` is kept as a `UNIQUE` constraint, so a medicine still
  appears only once per prescription.
- `ALLERGY` gets a surrogate key `allergy_id`; it also allows non-medicine allergies (`substance`).
- `Age` is **not stored**: it is derived from `date_of_birth`, so storing it would create an
  update anomaly every birthday.

---

## 5. The remaining tables

The knowledge-base and output tables were designed directly in normal form:

| Table | Holds |
|---|---|
| `INTERACTION (interaction_id, med_id_1, med_id_2, severity, mechanism, source_label_id)` | which two medicines interact |
| `CONTRAINDICATION (contra_id, med_id, condition_name, severity, source_label_id)` | medicine unsafe for a condition |
| `ADVERSE_SIGNAL (signal_id, med_id, reaction_term, report_count, prr, ror, computed_at)` | reporting statistics per medicine and reaction |
| `ALERT_LOG (alert_id, item_id, alert_type, severity, message, created_at, overridden, override_reason, risk_score)` | alerts raised by the trigger |

An interacting pair is stored once: `CHECK (med_id_1 < med_id_2)` together with
`UNIQUE (med_id_1, med_id_2)` prevents (Warfarin, Aspirin) and (Aspirin, Warfarin) being stored twice.

---

## 6. Final check: every table is in BCNF

**BCNF rule:** for every non-trivial functional dependency `X → Y`, `X` is a candidate key.

| # | Table | Candidate keys | Functional dependencies | 1NF | 2NF | 3NF | BCNF |
|---|---|---|---|:-:|:-:|:-:|:-:|
| 1 | Patient | `patient_id` | `patient_id → full_name, date_of_birth, gender, renal_function, hepatic_function, created_at` | ✓ | ✓ | ✓ | ✓ |
| 2 | Doctor | `doctor_id` | `doctor_id → full_name, specialty` | ✓ | ✓ | ✓ | ✓ |
| 3 | Medication | `med_id`, `rxcui` | `med_id → rxcui, name, generic_name, drug_class`; `rxcui → med_id` | ✓ | ✓ | ✓ | ✓ |
| 4 | Prescription | `prescription_id` | `prescription_id → patient_id, doctor_id, prescribed_date, status` | ✓ | ✓ | ✓ | ✓ |
| 5 | Prescription_Item | `item_id`, `(prescription_id, med_id)` | `item_id → prescription_id, med_id, dose, frequency, start_date, end_date`; `(prescription_id, med_id) → item_id` | ✓ | ✓ | ✓ | ✓ |
| 6 | Interaction | `interaction_id`, `(med_id_1, med_id_2)` | `interaction_id → med_id_1, med_id_2, severity, mechanism, source_label_id`; `(med_id_1, med_id_2) → interaction_id` | ✓ | ✓ | ✓ | ✓ |
| 7 | Contraindication | `contra_id` | `contra_id → med_id, condition_name, severity, source_label_id` | ✓ | ✓ | ✓ | ✓ |
| 8 | Patient_Condition | `(patient_id, condition_name)` | none except the trivial key dependency (all-key relation) | ✓ | ✓ | ✓ | ✓ |
| 9 | Allergy | `allergy_id` | `allergy_id → patient_id, med_id, substance, reaction` | ✓ | ✓ | ✓ | ✓ |
| 10 | Adverse_Signal | `signal_id`, `(med_id, reaction_term)` | `signal_id → med_id, reaction_term, report_count, prr, ror, computed_at`; `(med_id, reaction_term) → signal_id` | ✓ | ✓ | ✓ | ✓ |
| 11 | Alert_Log | `alert_id` | `alert_id → item_id, alert_type, severity, message, created_at, overridden, override_reason, risk_score` | ✓ | ✓ | ✓ | ✓ |

**Why every table passes**

- **1NF:** all columns are atomic; multi-valued facts (conditions, allergies, medicines) live in their own tables.
- **2NF:** every table except `Patient_Condition` has a single-column primary key, so a partial dependency
  is impossible; `Patient_Condition` has no non-key attributes.
- **3NF:** no non-key attribute determines another (e.g. `drug_class` lives only in `Medication`,
  `specialty` only in `Doctor`).
- **BCNF:** the only determinants in each table are its candidate keys. The alternate keys
  (`rxcui`, `(prescription_id, med_id)`, `(med_id_1, med_id_2)`, `(med_id, reaction_term)`)
  are all enforced with `UNIQUE` constraints in `sql/schema.sql`.

**Result:** the anomalies from Section 1 are gone. A medicine can be added without a prescription, a
drug class is changed in one row, and deleting a prescription never deletes patient data.
