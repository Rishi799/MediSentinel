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
5. For evaluation, sample 50 eligible labels with seed 7. Freeze the prefilled predictions and label every sentence, including empty rows (AI-assisted annotation with an author-verified sample; see Results). Compare exact sentence-level pairs with and without severity. The severity confusion table includes missing predictions and false positive pairs. Precision is the fraction of predictions supported by the annotations. Recall is the fraction of annotated rules found. F1 is their harmonic mean.

| Severity | Examples from the lexicon |
|---|---|
| Major | contraindicated, fatal, death, life-threatening, avoid, do not use, serious, severe |
| Moderate | monitor, caution, dose adjustment, reduce the dose, increase the risk, may increase, potentiate |
| Minor | minor, slight, small, not clinically significant |
| Default | Moderate at lower confidence |

## Results

The extraction read the 1,000 labels in MongoDB (30,173 sentences) and produced 895 candidate rules: 783 interactions and 112 contraindications. The bridge (`analytics/bridge.py`) matched 866 of them to medicines in PostgreSQL and loaded 710 interaction pairs and 110 contraindications alongside the 6 + 4 curated rules, each with its source label ID.

**Gold set.** The 50 sampled labels contain 1,161 sentences. The 330 sentences that mention an in-scope medicine or condition were labelled one by one with AI assistance, following the rules in `nlp/gold/ANNOTATION_GUIDE.md`; the other 831 mention no in-scope term and are negatives. The result is 214 gold rules in 173 sentences. The authors checked a random sample of 100 sentences (`nlp/gold/verify_sample.csv`); report the agreement rate here: **agreement = ___ / 100**.

| Evaluation level | Precision | Recall | F1 |
|---|---|---|---|
| Drug pair or condition | 0.585 | 0.752 | 0.658 |
| Pair or condition with correct severity | 0.520 | 0.668 | 0.585 |

Severity confusion (rows = gold, columns = predicted):

| Gold \ Predicted | Minor | Moderate | Major | Missing |
|---|---|---|---|---|
| Minor | 1 | 1 | 0 | 0 |
| Moderate | 0 | 130 | 1 | 44 |
| Major | 0 | 16 | 12 | 9 |
| Missing (false positive) | 1 | 106 | 7 | – |

The extractor finds three quarters of the real rules, but about four in ten of its predictions are wrong. Most false positives are negated statements ("no clinically significant interaction"), drug-name headings, and the label's own active ingredient matched under a second catalogue name. Most misses are salt-free names that the phrase matcher does not link to the catalogue entry (for example "phenytoin" for "phenytoin sodium"). Major rules are often predicted as Moderate (16 of 37), because the default severity is Moderate when no keyword is present.

## Discussion and limitations

Phrase matching can pair mentions from unrelated clauses or flattened tables. It can miss class-level references, alternate spellings and unfamiliar synonyms. For example, a statement saying that warfarin did not change a drug's pharmacokinetics still supplies a phrase match. A nearby word such as “avoid” can also apply to a different medicine in a long passage. High precision helps reduce alert fatigue, while high recall matters because missed safety rules can leave hazards unflagged. Negation handling, more medication aliases and a biomedical entity recognizer could be evaluated on a separate sample. [Nanji et al., medication-alert overrides](https://doi.org/10.1136/amiajnl-2013-001813).

## Screenshots

**Report placement:** Insert the Safety alerts screenshot with an imported FDA-derived rule selected once the reviewed bridge load is available. Include the source link, brand and recovered sentence.

[Verification capture with a temporary rule](screenshots/safety-alerts-fda.png). The source text and brand came from the actual openFDA label.
