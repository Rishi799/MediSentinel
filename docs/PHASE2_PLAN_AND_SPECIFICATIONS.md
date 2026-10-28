# MediSentinel — Phase 2 Technical Specifications & Implementation Blueprint

**Intelligence, Machine Learning & Post-Market Surveillance Architecture**  
*Department of Computer Science & Engineering (AI & ML) · RV College of Engineering®*  
*Target Release:* `v2-final` · *Prerequisite Milestone:* `v1-partial-demo`  
*Repository:* [https://github.com/Rishi799/MediSentinel](https://github.com/Rishi799/MediSentinel)

---

## 1. Executive Scope & Objectives

While **Phase 1** established the structural, relational, and transactional foundations (11 BCNF PostgreSQL relations, PL/pgSQL triggers, role-based security, openFDA data ingestion, and Streamlit clinical forms), **Phase 2 ("Intelligence & Delivery")** activates the innovative artificial intelligence and analytics layers of MediSentinel.

### Phase 2 Core Objectives
1. **Automated Knowledge Extraction (NLP)**: Transition from manual rule curation to automated mining of FDA drug monographs using biomedical NLP (`spaCy` / `scispaCy` / BioBERT) to populate drug-drug interactions and disease contraindications.
2. **Surveillance Signal Mining (NoSQL Analytics)**: Execute disproportionality analytics (PRR & ROR) over millions of post-market FAERS adverse reaction reports in MongoDB, streaming newly detected safety signals into PostgreSQL.
3. **Personalized Clinical Risk Scoring (ML)**: Train and deploy supervised machine learning models to calculate patient-specific acute risk probabilities ($0.000$ to $1.000$) on `Alert_Log.risk_score`.
4. **Drill-Down Clinical Surveillance Dashboard**: Build an executive healthcare analytics suite (`app/pages/4_Analytics.py`) with real-time alert aggregation, override audit logging, and direct drill-down links to original FDA source monographs.
5. **Academic & Research Publications**: Author an IEEE-format research paper, benchmark query plans via `EXPLAIN ANALYZE`, and complete the final project report.

---

## 2. End-to-End Phase 2 System Architecture

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              PHASE 2 WORKFLOW & PIPELINES                              │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│   ┌──────────────────────────┐                   ┌─────────────────────────────────┐   │
│   │   MongoDB (Data Lake)    │                   │   PostgreSQL (Operational Core) │   │
│   │                          │                   │                                 │   │
│   │  medication_labels       │                   │  Interaction / Contraindication │   │
│   │  (Free-text monographs)  │                   │  (Curated relational rules)     │   │
│   └────────────┬─────────────┘                   └────────────────▲────────────────┘   │
│                │                                                  │                    │
│                ▼                                                  │                    │
│   ┌──────────────────────────┐                   ┌────────────────┴────────────────┐   │
│   │  MODULE 1: NLP ENGINE    │                   │  MODULE 2: INTEGRATION BRIDGE   │   │
│   │  • spaCy / scispaCy NER  │ ──Extracted Trips─►  • Canonical ordering (id1 < id2│   │
│   │  • BioBERT Classifier    │   (Drug, Disease, │  • Source label linking         │   │
│   │  • Rule Extractor        │    Severity, Conf)│  • Duplicate prevention upsert  │   │
│   └──────────────────────────┘                   └─────────────────────────────────┘   │
│                                                                                        │
│   ┌──────────────────────────┐                   ┌─────────────────────────────────┐   │
│   │  MongoDB (Data Lake)     │                   │  PostgreSQL (Surveillance)      │   │
│   │                          │                   │                                 │   │
│   │  adverse_reports         │                   │  Adverse_Signal                 │   │
│   │  (Millions of FAERS JSON)│                   │  (PRR, ROR, report count)       │   │
│   └────────────┬─────────────┘                   └────────────────▲────────────────┘   │
│                │                                                  │                    │
│                ▼                                                  │                    │
│   ┌──────────────────────────┐                                    │                    │
│   │  MODULE 3: SIGNAL MINING │ ──────Detected Signals (PRR>=2)────┘                    │
│   │  • $unwind -> $group     │                                                         │
│   │  • 2x2 Contingency Matrix│                                                         │
│   │  • PRR / ROR Calculator  │                                                         │
│   └──────────────────────────┘                                                         │
│                                                                                        │
│   ┌──────────────────────────┐                   ┌─────────────────────────────────┐   │
│   │  Prescription Event      │                   │  MODULE 4: ML PATIENT RISK      │   │
│   │  • Patient Age & Labs    │ ───Feature Vector─►  • XGBoost / Random Forest      │   │
│   │  • Active Comorbidities  │                   │  • Risk Probability (0.0 - 1.0) │   │
│   │  • Prescribed Drug Count │                   │  • Saves to Alert_Log.risk_score│   │
│   └──────────────────────────┘                   └────────────────┬────────────────┘   │
│                                                                   │                    │
│                                                                   ▼                    │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │  MODULE 5: CLINICAL EXECUTIVE DASHBOARD (app/pages/4_Analytics.py)             │   │
│   │  • Departmental Alert Trends   • PRR Signal Scatterplots   • Label Drill-Down  │   │
│   └────────────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Technical Module Specifications

### Module 1: NLP Monograph Extraction Engine (`nlp/`)
* **Primary Owner**: Member 2 (Data & NoSQL) · *Assisted by*: Rishi (Lead)
* **Goal**: Automatically extract clinical interaction rules and disease contraindications from FDA package insert documents.
* **Source Corpus**: MongoDB `medication_labels` collection (`drug_interactions` and `contraindications` text fields).

#### Architecture & Pipeline
1. **Text Preprocessing**: Tokenization, sentence segmentation, and regex cleanup of label monograph sections.
2. **Biomedical Named Entity Recognition (NER)**:
   * Model: `scispaCy` (`en_core_sci_sm` or `en_ner_bc5cdr_md`) fine-tuned for drug chemicals (`CHEMICAL`) and diseases (`DISEASE`).
   * Normalization: Map extracted drug mentions to standardized RxNorm concepts in PostgreSQL `Medication.generic_name`.
3. **Relation Extraction & Severity Classification**:
   * Rule syntax: Extract `(Subject Drug, Object Drug/Condition, Severity, Mechanism, Confidence)`.
   * Severity lexicon:
     * `MAJOR`: Keywords like *"contraindicated", "fatal", "avoid concomitant use", "severe toxicity", "death"*.
     * `MODERATE`: Keywords like *"monitor carefully", "potentiates effect", "dose adjustment required"*.
     * `MINOR`: Keywords like *"may slightly increase", "clinical significance minimal"*.
4. **Validation Test Set**:
   * Construct a hand-labeled benchmark of 50 drug labels.
   * Target Metrics: Precision $\ge 85\%$, Recall $\ge 80\%$, F1-score $\ge 82\%$.

---

### Module 2: SQL $\leftrightarrow$ NoSQL Integration Bridge (`analytics/bridge.py`)
* **Primary Owner**: Rishi (Person A - Lead)
* **Goal**: Feed NLP-extracted rules into PostgreSQL while linking operational records back to the NoSQL lake.

#### Core Capabilities
1. **Conflict-Safe Rule Loader**:
   * Inserts extracted drug pairs into `Interaction` using:
     ```sql
     INSERT INTO Interaction (med_id_1, med_id_2, severity, mechanism, source_label_id)
     VALUES (LEAST(%s, %s), GREATEST(%s, %s), %s, %s, %s)
     ON CONFLICT (med_id_1, med_id_2) DO UPDATE
     SET severity = EXCLUDED.severity, mechanism = EXCLUDED.mechanism;
     ```
   * Inserts disease rules into `Contraindication`:
     ```sql
     INSERT INTO Contraindication (med_id, condition_name, severity, source_label_id)
     VALUES (%s, %s, %s, %s)
     ON CONFLICT DO NOTHING;
     ```
2. **Source Monograph Drill-Down**:
   * Clinical end-point allowing doctors to view the original FDA text snippet in the app:
     ```python
     def get_source_label_snippet(mongo_db, source_label_id, section="drug_interactions"):
         doc = mongo_db.medication_labels.find_one({"_id": source_label_id})
         return doc.get(section, ["No text available"])[0] if doc else None
     ```

---

### Module 3: Pharmacovigilance Big Data Signal Mining (`analytics/signal_mining.py`)
* **Primary Owner**: Rishi (Person A) & Member 2 (Person B)
* **Goal**: Autonomous post-market safety surveillance over FAERS reports in MongoDB.

#### Mathematical Formulation

$$\text{PRR} = \frac{A / (A + B)}{C / (C + D)}$$

$$\text{ROR} = \frac{A \cdot D}{B \cdot C}$$

Where:
* $A$: Reports citing Target Drug with Target Adverse Reaction.
* $B$: Reports citing Target Drug with all other adverse reactions.
* $C$: Reports citing all other drugs with Target Adverse Reaction.
* $D$: Reports citing all other drugs with all other adverse reactions.

#### Execution Pipeline
1. Run MongoDB aggregation on `adverse_reports`:
   ```javascript
   db.adverse_reports.aggregate([
     { $unwind: "$patient.drug" },
     { $unwind: "$patient.reaction" },
     { $group: {
         _id: {
           drug: "$patient.drug.medicinalproduct",
           reaction: "$patient.reaction.reactionmeddrapt"
         },
         count: { $sum: 1 }
     }},
     { $match: { count: { $gte: 3 } } },
     { $sort: { count: -1 } }
   ])
   ```
2. Filter statistically significant signals ($\text{PRR} \ge 2.0$, $\chi^2 \ge 4.0$, count $\ge 3$).
3. Upsert into PostgreSQL `Adverse_Signal` table.

---

### Module 4: Predictive ML Patient Risk Scoring (`ml/`)
* **Primary Owner**: Priyanshi Gupta (Person C - AI & Application)
* **Goal**: Provide personalized, multi-factor acute risk scores ($0.000$ to $1.000$) whenever an alert is generated.

#### Feature Matrix ($X$)
| Feature Name | Type | Description |
|---|---|---|
| `patient_age` | Continuous | Derived from `date_of_birth` ($0 - 120$) |
| `gender_enc` | Categorical | Encoded ($M=0, F=1, O=2$) |
| `renal_score` | Ordinal | $0 = \text{normal}, 1 = \text{impaired}, 2 = \text{severe}$ |
| `hepatic_score`| Ordinal | $0 = \text{normal}, 1 = \text{impaired}, 2 = \text{severe}$ |
| `polypharmacy_count` | Discrete | Total number of concurrent active medications |
| `max_interaction_sev` | Ordinal | $0 = \text{None}, 1 = \text{MINOR}, 2 = \text{MODERATE}, 3 = \text{MAJOR}$ |
| `has_contraindication`| Binary | $1$ if active diagnosis matches drug contraindication, else $0$ |
| `has_allergy_match` | Binary | $1$ if drug matches patient allergy history, else $0$ |

#### Model Training & Deployment
1. Train a classifier using `scikit-learn` (`RandomForestClassifier` or `XGBoost`).
2. Evaluate with 5-fold cross-validation: Target ROC-AUC $\ge 0.88$.
3. Serialize model to `ml/model_risk_v1.joblib`.
4. Inference hook in `medisentinel/db`: On alert creation, model outputs `risk_score` which is saved to `Alert_Log.risk_score`.

---

### Module 5: Clinical Executive Surveillance Dashboard (`app/pages/4_Analytics.py`)
* **Primary Owner**: Priyanshi Gupta (Person C) & Rishi (Person A)
* **Goal**: Executive oversight tool for hospital medical directors and chief pharmacists.

#### Dashboard Capabilities
1. **Real-Time KPI Metrics**:
   * Total prescriptions analyzed.
   * Total safety alerts intercepted.
   * Override frequency rate ($\% \text{ Overridden}$).
   * Mined post-market signals count.
2. **Interactive Visualizations (Plotly / Streamlit native)**:
   * **Alert Severity Distribution**: Pie / donut chart breakdown.
   * **Departmental Risk Profiling**: Bar chart of alerts raised across Cardiology, General Medicine, Nephrology, etc.
   * **Signal Disproportionality Scatterplot**: PRR vs. Report Count identifying high-risk medication outliers.
3. **Clinical Audit Log**:
   * Filterable ledger of doctor overrides displaying the required medical rationale (`override_reason`).
   * One-click modal displaying the raw FDA drug monograph snippet from MongoDB.

---

## 4. Database Profiling & Index Optimization (`sql/benchmark.sql`)

To prove enterprise readiness for academic review:
1. **Scale Data Volume**: Execute `generate_synthetic.py` to simulate **1,000 patients, 100 doctors, and 5,000 multi-drug prescriptions**.
2. **Execute `EXPLAIN ANALYZE`**:
   * Measure scan costs: Compare `Seq Scan` vs. `Index Scan` on `Prescription_Item(med_id)` and `Interaction(med_id_1, med_id_2)`.
   * Trigger Latency: Benchmark insert overhead of `trg_medication_safety` under high concurrent batch operations (target $< 10 \text{ ms}$).
3. **Document Execution Plans**: Save execution plan diagrams into `docs/BENCHMARK_RESULTS.md`.

---

## 5. Team Roles & Responsibilities in Phase 2

| Member | Primary Focus | Folders Owned | Key Deliverables |
|---|---|---|---|
| **Rishi (Person A)**<br>*Lead Architect* | SQL $\leftrightarrow$ NoSQL Integration, Signal Mining, Benchmarking | `sql/`, `analytics/`, `medisentinel/` | • `analytics/bridge.py` (Rule upsert & drill-down)<br>• `analytics/signal_mining.py` (PRR/ROR pipeline)<br>• `sql/benchmark.sql` (`EXPLAIN ANALYZE` reports)<br>• Final integration, PR reviews, release management |
| **Member 2 (Person B)**<br>*Data & NoSQL* | NLP Monograph Extraction, Pipeline Evaluation | `ingestion/`, `nlp/` | • `nlp/extract_labels.py` (spaCy biomedical entity extractor)<br>• `nlp/evaluate.py` (Precision/Recall benchmark)<br>• Expanded MongoDB bulk load (~2,000 labels, ~10,000 reports)<br>• NoSQL chapter for the final project report |
| **Priyanshi (Person C)**<br>*AI & Application* | ML Risk Model, Clinical Dashboard | `app/`, `ml/` | • `ml/train_risk_model.py` (RandomForest classifier)<br>• `ml/model_risk_v1.joblib` (Exported model)<br>• `app/pages/4_Analytics.py` (Surveillance dashboard)<br>• ML & UI evaluation chapter for final paper |

---

## 6. Phase 2 Sprint Schedule (Weeks 9 to 13)

```
WEEKS 9-10 (Nov 16 - Nov 28)
├── Member 2: Build NLP extractor (nlp/extract_labels.py) using scispaCy
├── Member 1: Build SQL ↔ NoSQL bridge (analytics/bridge.py) & PRR pipeline
└── Member 3: Engineer features & train ML risk model (ml/train_risk_model.py)

WEEK 11 (Nov 30 - Dec 06) — CIE / Mid-Term Sync
├── Revise for lab internals & CIE tests
└── Bug fixing and preliminary pipeline smoke tests

WEEK 12 (Dec 07 - Dec 13) — Integration & Optimization
├── Member 3: Build Streamlit Analytics Dashboard (4_Analytics.py)
├── Member 1: Run EXPLAIN ANALYZE benchmarks on 5,000+ prescriptions
└── Code freeze (Friday Dec 11) & end-to-end integration

WEEK 13 (Dec 14 - Dec 26) — Closure & Submissions
├── Author IEEE-format research paper
├── Finalize project report and slide deck
├── Demo rehearsal & panel presentation
└── Release milestone: git tag v2-final && git push origin v2-final
```

---

## 7. Phase 2 Completion Checklist ("Done When")

- [ ] **NLP Extraction Live**: `nlp/extract_labels.py` parses FDA labels into structured triples with $\ge 80\%$ F1-score.
- [ ] **Bridge Active**: Extracted rules automatically populate PostgreSQL `Interaction` and `Contraindication`.
- [ ] **Signal Mining Operational**: `analytics/signal_mining.py` computes PRR/ROR and updates `Adverse_Signal`.
- [ ] **ML Risk Model Deployed**: Every generated alert contains a predicted `risk_score` ($0.000 - 1.000$) displayed via in-app risk gauges.
- [ ] **Analytics Dashboard Built**: `4_Analytics.py` provides interactive charts, override logs, and source monograph drill-downs.
- [ ] **Query Benchmarks Documented**: `EXPLAIN ANALYZE` reports show verified execution plan speedups.
- [ ] **Paper & Report Formatted**: IEEE paper draft and final laboratory report completed.
- [ ] **Milestone Tagged**: `git tag v2-final` pushed to GitHub.
