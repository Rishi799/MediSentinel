# MediSentinel – Work Plan (2 phases, 3 members)

| Member | Role | Owns (folders) |
|---|---|---|
| **Member 1 – _(you)_** | **Repo lead · Database & Integration** | `sql/`, `medisentinel/db/`, `analytics/`, final integration |
| Member 2 – _(name)_ | Data & NoSQL | `ingestion/`, `nlp/` |
| Member 3 – _(name)_ | Application & AI | `app/`, `ml/` |

Everyone writes tests for their own module in `tests/` and contributes to `docs/`.
**Everyone must be able to explain every module in the viva**, so each member demos their work to the other two at the end of every week.

---

## Phase 1 – Core system (26 Oct → 13 Nov) · ends with the Partial Demo

> **Being done as a 2-day sprint: follow [PHASE1_SPRINT.md](PHASE1_SPRINT.md) for the hour-by-hour plan.**
> The table below shows how the same work maps onto the lab schedule weeks.

**Goal:** a working app where a doctor logs in, registers a patient, writes a prescription, and the trigger raises a safety alert, with openFDA data loaded in MongoDB.

| Week (lab schedule) | Member 1 – you (lead) | Member 2 – Data & NoSQL | Member 3 – Application |
|---|---|---|---|
| **Wk 6 · 26–30 Oct**<br>*Normalized tables due* | • Set up the GitHub repo, branches, `requirements.txt`, `.env.example`<br>• Apply the latest `schema.sql` to every member's PostgreSQL<br>• **Write the normalization document** (FDs, 1NF → BCNF) | • Install MongoDB + Compass, create the `medisentinel` database<br>• Script to download a sample of openFDA labels and adverse-event reports into `medication_labels` and `adverse_reports` | • Paper/wireframe designs for every form<br>• Streamlit skeleton: pages, navigation, login page |
| **Wk 7 · 2–6 Nov**<br>*Forms, security & validation due* | • DB access layer (`medisentinel/db/`): connection pool, parameterized queries<br>• Prescription save as **one transaction**; fix the concurrency gap (row lock on patient)<br>• Create PostgreSQL roles (doctor, pharmacist, admin) with `GRANT`s | • Indexes on the Mongo collections<br>• RxNorm mapping → fill the `Medication` table<br>• **Synthetic patient/prescription generator** (privacy-safe test data) | • Forms: patient (with conditions & allergies), doctor, prescription (multi-item), alerts view<br>• **Input validation** on every field<br>• Login with hashed passwords, role-based pages |
| **Wk 8 · 9–13 Nov**<br>*Partial Demo* | • Integrate the app with the DB layer<br>• Rehearse and run the demo | • Show Mongo data + one aggregation query in the demo | • Polish the forms, error messages and alert display |

**Phase 1 done when:** the full demo flow works on your machine from a fresh clone, every form validates input, the trigger fires from the app, and MongoDB holds real openFDA data.

**Tag the repo:** `v1-partial-demo`

---

## Phase 2 – Intelligence & delivery (16 Nov → 26 Dec)

**Goal:** the innovative component (NLP + ML) feeding the database, safety-signal analytics, a dashboard, and all final documents.

| Week (lab schedule) | Member 1 – you (lead) | Member 2 – Data & NoSQL | Member 3 – Application & AI |
|---|---|---|---|
| **16–28 Nov**<br>*Wk 9: AI integration due 23–28 Nov* | • **SQL ↔ NoSQL bridge:** load extracted rules into `Interaction` / `Contraindication` with `source_label_id` (upsert, no duplicates)<br>• **PRR/ROR pipeline** → `Adverse_Signal`<br>• Drill-down: alert → original label in MongoDB | • **NLP extraction** (spaCy/scispaCy): label text → drug pairs, severity, contraindicated conditions, with a confidence score<br>• Small hand-checked test set; report precision/recall | • **ML risk model** (scikit-learn) predicting patient risk<br>• Store the score in `Alert_Log.risk_score` and show it with each alert |
| **30 Nov – 4 Dec**<br>*Wk 10: CIE test* | Light week: revise for the test, fix bugs | Light week: revise for the test | Light week: revise for the test |
| **7–13 Dec** | • Performance: `EXPLAIN ANALYZE` before/after indexes on large data<br>• Final integration and code freeze (Fri 11 Dec) | • Load larger data volumes; time the aggregation pipelines | • Dashboard: alerts by severity, top safety signals, recent alerts<br>• Test cases for forms and trigger |
| **14–18 Dec**<br>*Wk 11: Final Demo + Technical Paper* | Lead the demo; write the paper's **system design + database** sections | Paper: **data, NoSQL, NLP + evaluation** sections | Paper: **AI model + results** sections; compile and format the paper |
| **21–26 Dec**<br>*Wk 12: Final Report* | Final review and sign-off | Data & NLP chapters | **Compile and format the final report** |

**Phase 2 done when:** NLP-extracted rules drive real alerts, every alert shows a risk score, the dashboard shows PRR/ROR signals, and the paper and report are submitted.

**Tag the repo:** `v2-final`

---

## How we work in the repo (Member 1 manages this)

1. **Repo:** private GitHub repo owned by Member 1; Members 2 and 3 added as collaborators.
2. **Protect `main`:** nobody pushes to `main` directly. Every change goes through a pull request that Member 1 reviews and merges.
3. **Branches:** one per task, named after it: `feature/forms`, `feature/openfda-ingestion`, `feature/nlp-extraction`, `fix/prescription-lock`.
4. **Stay in your folders.** Changes to `sql/schema.sql` go only through Member 1, because everyone's code depends on it.
5. **Sync often:** `git pull origin main` before starting work each day.
6. **Never commit secrets:** passwords live in `.env` (already ignored); only `.env.example` is committed.
7. **Weekly:** merge on Friday, run the full demo flow, and each member demos their part to the others.

## Hand-offs (who waits for whom)

| Needs | From | By |
|---|---|---|
| Final schema + DB access layer | Member 1 → Member 3 (forms) | 3 Nov |
| openFDA data in MongoDB | Member 2 → Member 1 (bridge) | 6 Nov |
| NLP output format (fields, confidence) | Member 2 → Member 1 (bridge) | 20 Nov |
| Risk-model interface (inputs → score) | Member 3 → Member 1 (integration) | 23 Nov |
