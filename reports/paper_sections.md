# MediSentinel Phase 2 · IEEE manuscript sections

## III. NLP extraction of safety rules

We processed structured product labels from openFDA [1]. The extractor split interaction and contraindication text into sentences with spaCy and applied case-insensitive phrase matching over a PostgreSQL-derived vocabulary [2]. A lexicon assigned severity. Candidates were deduplicated by rule type, generic drug and target, retaining the highest severity and a source label ID. The independent sentence-level evaluation separates target detection from agreement on severity. Manual annotation of the sampled labels is pending. Preliminary inspection identified negated interaction statements and flattened tables as sources of false positives.

## IV. Report seriousness estimation

OpenFDA FAERS reports provided the serious flag [3], [4]. Shared predictors included age, sex, drug count, maximum interaction severity, interaction count and the presence of a signal. In five-fold stratified cross-validation on 3,590 reports, class-balanced logistic regression and random forest obtained mean ROC-AUC values of 0.678 and 0.693, respectively [5]. The random forest achieved F1 of 0.608 at a threshold of 0.5 and was refitted for batch and live scoring. Spontaneous reporting bias and differences between FAERS reports and patient prescriptions limit the clinical interpretation of the score.

## V. Alert explanation and surveillance

The Streamlit interface displays a named score band and, for sourced rules, uses a PostgreSQL rule's label ID to retrieve openFDA provenance. Analytics aggregates rule severity, scored alerts, PRR signals and prescribing specialties and exposes the underlying tables. PRR highlights disproportional reporting for investigation [6]. Overrides preserve the doctor's rationale for review. False positives and override patterns warrant attention because high alert burden can drive alert fatigue [7].

## References

1. U.S. Food and Drug Administration, “Drug Labeling Overview,” openFDA. [Dataset documentation](https://open.fda.gov/apis/drug/label/).
2. Explosion, “PhraseMatcher,” spaCy API Documentation. [API documentation](https://spacy.io/api/phrasematcher).
3. U.S. Food and Drug Administration, “Drug Adverse Events,” openFDA. [Dataset documentation](https://open.fda.gov/apis/drug/event/).
4. U.S. Food and Drug Administration, “M2 Electronic Transmission of Individual Case Safety Report Message Specification.” [Field codes](https://www.fda.gov/files/drugs/published/M2-Electronic-Transmission-of-Individual-Case-Safety-Report-Message-Specification.pdf).
5. F. Pedregosa et al., “Scikit-learn: Machine Learning in Python,” *J. Mach. Learn. Res.*, vol. 12, pp. 2825–2830, 2011. [Article](https://jmlr.org/papers/v12/pedregosa11a.html).
6. S. J. W. Evans, P. C. Waller, and S. Davis, “Use of proportional reporting ratios (PRRs) for signal generation from spontaneous adverse drug reaction reports,” *Pharmacoepidemiol. Drug Saf.*, vol. 10, no. 6, pp. 483–486, 2001. [Article](https://doi.org/10.1002/pds.677).
7. K. C. Nanji et al., “Overrides of medication-related clinical decision support alerts in outpatients,” *J. Am. Med. Inform. Assoc.*, vol. 21, no. 3, pp. 487–491, 2014. [Article](https://doi.org/10.1136/amiajnl-2013-001813).
