# Phase 2 viva and demo notes

## Setup and ownership

PostgreSQL keeps the structured rules, signals and alert scores. `Interaction` holds medicine pairs. `Contraindication` holds medication and condition pairs. `Adverse_Signal` holds medicine and reaction signals. `Alert_Log.risk_score` holds the model score. Within the app roles, `ms_admin` may write those data. Doctors can prescribe and override alerts with a reason. Pharmacists read. The trigger creates alerts during prescription insertion.

## P1 · Rule extraction

`nlp/extract_rules.py` reads nested FDA label documents from MongoDB. Sentence splitting narrows each extraction to a piece of evidence. A PhraseMatcher finds complete medicine or condition phrases from a known vocabulary, and the lexicon assigns severity. The MongoDB source ID lets the app trace a candidate back to its label. The extractor can find reassuring statements and nearby terms because it lacks a model of negation and relationships.

1. Why is MongoDB suitable for FDA labels?
2. How does the matcher distinguish “warfarin” from a longer unrelated token?
3. If a sentence says one drug “did not affect” the other, why might it still become a candidate?

## P2 · Extraction evaluation

`nlp/make_gold_sheet.py` takes a reproducible random sample and freezes its predictions. An independent human review supplies the reference labels. `nlp/evaluate.py` compares predictions and the corrected rows at two levels. Pair-level evaluation asks if the target is correct. Severity-aware evaluation also requires the correct severity. Precision measures how often predictions are correct. Recall measures how much of the reference set was found. F1 balances them. Excess false positives can add alert fatigue, and false negatives can leave hazards unflagged.

1. What is a false positive in pair-level evaluation?
2. What changes in the metrics if a pair is correct but its severity is wrong?
3. Why should an evaluation set be kept separate from rule tuning?

## P3 and P4 · Dataset and model

`ml/build_dataset.py` extracts the FDA serious flag and usable onset age. `ml/features.py` defines the feature order and counts medication pairs. `ml/train_risk_model.py` evaluates a logistic baseline and a random forest on identical stratified folds. Each fold preserves the class balance and tests on reports held out from training. ROC-AUC measures ranking across thresholds. The forest's mean ROC-AUC was 0.693 and the baseline's was 0.678 in the local FAERS sample.

1. Where does the target label come from, and why is it different from trigger severity?
2. Why do the training and scoring paths share the same feature order?
3. What does a mean ROC-AUC of 0.693 tell you about ranking, and what does an FDA reporting database leave unknown?

## P5 · Scoring

`ml/score.py` assembles a current active regimen and predicts using the saved model. `ml/score_alerts.py` updates unscored rows with `ms_admin` in a single transaction. The trigger stays in PostgreSQL and saves the rule alert immediately. The prescription screen can show a live estimate while the admin job handles persistence.

1. Why is prediction performed after the trigger completes?
2. Why can a doctor view or override an alert while admin access is needed to persist the score?
3. What does a second scoring run do, and what changes with `--rescore`?

## P6 · Alert explanation

`app/explain.py` finds the current matching rule using the alert's item and message. A stored source ID ties the PostgreSQL rule to the MongoDB label. `app/ui.py` shows a percentage, the named score band and a color for that band. The Alerts page shows the stored score and provenance. Prescriptions can also show a live estimate.

1. What is provenance, and which column connects the two databases?
2. What can the app display for a curated rule without an FDA source ID?
3. Why show “Medium” and the percentage along with the color?

## P7 · Analytics

`app/analytics_queries.py` aggregates with the signed-in role, and the Analytics page presents those aggregates as charts and data tables. The learned rules chart shows which FDA-derived rules reached PostgreSQL and their severity. The score histogram shows the spread of stored scores by alert severity. The signal map compares reporting count and PRR. The department chart breaks alert volume down by prescribing specialty. The audit presents override reasons.

1. What does a point with PRR above 2 represent?
2. What is the denominator of the override rate?
3. How can a pharmacist check the values under a chart, and why does the page work with read-only access?

## Rehearsal

1. Sign in as doctor. Open Dashboard, then select a seeded interaction in Safety alerts and explain the score and evidence.
2. Use a synthetic patient with peptic ulcer. In Prescriptions, select Warfarin and Aspirin as the prescribed medicines for the lab scenario. Point out the interaction, contraindication and live model estimates.
3. In Analytics, expand **Show data** under the score or signal chart. Explain why the rule chart shows zero FDA-derived rules before the bridge loads reviewed rules.
4. Sign in as pharmacist and open Analytics to demonstrate the same read-only surveillance view.
5. Show the three training figures and both mean ROC-AUC values. Add the evaluation results after reviewing the gold sheet. After the team imports the reviewed rules, repeat the FDA provenance demonstration on the integrated database.

## Review order

The branches are stacked so each review can focus on one task. The first comparison starts at main and each subsequent comparison starts at its immediate dependency.

1. [P1 · Extractor](https://github.com/Rishi799/MediSentinel/compare/main...feature/nlp-extractor?expand=1)
2. [P2 · Gold set and evaluation](https://github.com/Rishi799/MediSentinel/compare/feature/nlp-extractor...feature/nlp-evaluation?expand=1)
3. [P3–P4 · FAERS dataset and model](https://github.com/Rishi799/MediSentinel/compare/feature/nlp-evaluation...feature/ml-risk-model?expand=1)
4. [P5 · Admin scoring](https://github.com/Rishi799/MediSentinel/compare/feature/ml-risk-model...feature/ml-scoring?expand=1)
5. [P6 · Alert explanation](https://github.com/Rishi799/MediSentinel/compare/feature/ml-scoring...feature/alert-explain?expand=1)
6. [P7 · Analytics](https://github.com/Rishi799/MediSentinel/compare/feature/alert-explain...feature/analytics-page?expand=1)
7. [P8 · Report chapters](https://github.com/Rishi799/MediSentinel/compare/feature/analytics-page...docs/phase2-chapters?expand=1)
