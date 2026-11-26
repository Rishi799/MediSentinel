# Extracting medication safety rules from FDA labels

## Problem and approach

FDA drug labels describe interactions and contraindications in prose and tables. The Phase 1 trigger can query a structured PostgreSQL rule immediately, but it cannot interpret a label paragraph at prescription time. Phase 2 extracts candidate rules offline from openFDA labels in MongoDB and retains the source label ID and evidence sentence so a reviewer can trace each candidate back to its context. [FDA drug labeling overview](https://open.fda.gov/apis/drug/label/).

## Method

```text
MongoDB label → spaCy sentences → drug or condition matches → severity and confidence
              → strongest candidate per ordered pair → JSONL → reviewed bridge import
```

1. Read the primary generic name and the interaction and contraindication sections. The vocabulary comes from PostgreSQL generic names, brand aliases and known conditions, supplemented by common conditions such as peptic ulcer and renal failure.
2. Use spaCy sentence boundaries and two case-insensitive token phrase matchers. Retain the longest overlapping phrase and exclude the label drug from its own interaction candidates. [spaCy PhraseMatcher](https://spacy.io/api/phrasematcher).
3. Apply the severity lexicon in order. A keyword plus a target in the same sentence gives confidence 0.9. A target alone gives the Moderate default at 0.6. These values encode the rule logic.
4. Keep one candidate per ordered drug and target for each rule type, choosing the highest severity, then the highest confidence. Export the sentence excerpt, MongoDB ID and confidence. The PostgreSQL bridge can resolve medicine IDs and reconcile opposite directions for its canonical pair.
5. For evaluation, sample 50 eligible labels with seed 7. Freeze the prefilled predictions and independently correct every sentence, including empty rows. Compare exact sentence-level pairs with and without severity. The severity confusion table includes missing predictions and false positive pairs. Precision is the fraction of predictions supported by the annotations. Recall is the fraction of annotated rules found. F1 is their harmonic mean.

| Severity | Examples from the lexicon |
|---|---|
| Major | contraindicated, fatal, death, life-threatening, avoid, do not use, serious, severe |
| Moderate | monitor, caution, dose adjustment, reduce the dose, increase the risk, may increase, potentiate |
| Minor | minor, slight, small, not clinically significant |
| Default | Moderate at lower confidence |

## Results

The extraction used the 1,000 labels present in MongoDB. The PostgreSQL snapshot contains six curated interactions and four curated contraindications. The reviewed bridge import is pending. Pilot inspection found monitoring instructions with clear drug targets and also found negated statements that generated candidates.

| Evaluation level | Precision | Recall | F1 |
|---|---|---|---|
| Drug pair or condition | Manual review pending | Manual review pending | Manual review pending |
| Pair or condition with correct severity | Manual review pending | Manual review pending | Manual review pending |

Complete the gold-sheet review and run `python -m nlp.evaluate --reviewed`. Populate the table from `nlp/output/eval.json` and use its severity confusion table to discuss disagreement patterns.

## Discussion and limitations

Phrase matching can pair mentions from unrelated clauses or flattened tables. It can miss class-level references, alternate spellings and unfamiliar synonyms. For example, a statement saying that warfarin did not change a drug's pharmacokinetics still supplies a phrase match. A nearby word such as “avoid” can also apply to a different medicine in a long passage. High precision helps reduce alert fatigue, while high recall matters because missed safety rules can leave hazards unflagged. Negation handling, more medication aliases and a biomedical entity recognizer could be evaluated on a separate sample. [Nanji et al., medication-alert overrides](https://doi.org/10.1136/amiajnl-2013-001813).

## Screenshots

**Report placement:** Insert the Safety alerts screenshot with an imported FDA-derived rule selected once the reviewed bridge load is available. Include the source link, brand and recovered sentence.

[Verification capture with a temporary rule](screenshots/safety-alerts-fda.png). The source text and brand came from the actual openFDA label.
