# NLP gold set – annotation guide and method

**Sample:** 50 openFDA drug labels (seed 7, `nlp/make_gold_sheet.py`), 1,161 sentences from the
`drug_interactions` and `contraindications` sections.

**How the labels were produced:** AI-assisted annotation. Every sentence that mentions an in-scope
medicine or condition (330 sentences) was read and labelled individually by an AI assistant following the
rules below; the extractor's pre-filled guesses were only a starting point and were corrected wherever they
disagreed with the rules. The remaining 831 sentences mention no in-scope medicine or condition (checked with
a broader matcher than the extractor, including salt-free names such as "atorvastatin" for "atorvastatin
calcium") and are negatives by definition. The authors verify a random sample of 100 sentences in
`verify_sample.csv`; report the agreement rate together with the metrics.

## Scope

- **Medicines:** those in the MediSentinel `Medication` table, written as their catalogue generic name
  (e.g. `phenytoin sodium`, even when the sentence says "phenytoin"). Drug classes ("NSAIDs", "CYP3A4
  inhibitors") are out of scope.
- **Conditions:** the extractor's condition list (peptic ulcer, chronic kidney disease, renal failure, liver
  disease, hyperkalemia, pregnancy, asthma, heart failure, hypertension, diabetes, epilepsy, bleeding
  disorder, glaucoma, and conditions already in the database).
- A sentence that only mentions the label's own drug or one of its components is not a rule.

## When a sentence is a rule

- **Interaction:** the sentence states a clinically relevant effect, risk or precaution for using the label
  drug together with a named in-scope medicine (raised or lowered levels, bleeding, toxicity, monitor,
  adjust dose, avoid, contraindicated combination).
- **Contraindication:** the sentence states the label drug must not be used, or must be stopped, in a named
  in-scope condition.
- **Not a rule:** "no interaction / no effect / not significantly changed"; section headings that are only a
  drug name; lists of examples without a stated effect in the same sentence; a condition mentioned only as an
  outcome ("may cause hyperkalemia") or as the indication; studies about a third drug (e.g. pemetrexed).

## Severity

- **MAJOR:** contraindicated, avoid, do not use / do not co-administer, or a serious outcome stated
  (serious bleeding, hospitalisation).
- **MODERATE:** increased risk, raised or lowered levels, monitor, caution, dose adjustment, not recommended.
- **MINOR:** an effect explicitly described as small or theoretical.
