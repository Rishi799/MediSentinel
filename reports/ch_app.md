# Application and user interface

## Problem and approach

The app makes a rule-based alert inspectable while showing the model score alongside it. Doctors can review an explanation before deciding whether to override an alert. Analysts can see which parts of the safety system are populated and inspect the counts underlying each chart.

## Method

```text
Prescription save → PostgreSQL trigger → alert → stored score or live model estimate
                                       → rule lookup → source_label_id → MongoDB label
PostgreSQL aggregates → read-only Analytics → chart and underlying table
```

| Surface | What it shows |
|---|---|
| Dashboard | High-risk alert count for stored scores at or above 0.66 |
| Safety alerts | Selected alert, named score band, evidence sentence, brand and FDA label link when available |
| Prescriptions | Saved rule alerts beside stored scores or live estimates |
| Analytics | Curated and FDA-derived rule counts, learned-rule severity, score histogram, PRR map, specialty counts and override reasons |

The score gauge shows Low below 0.33, Medium below 0.66 and High from 0.66. The label and percentage accompany the palette. An unavailable score has an explicit text state. The stored model score and rule severity serve different purposes. The database role used at sign-in enforces permissions. A doctor can override with a documented reason. Persisting scores uses the separate admin job. The Analytics page performs reads for all three roles.

## Results

| Local database snapshot | Value |
|---|---:|
| Curated interactions | 6 |
| Curated contraindications | 4 |
| FDA-derived rules imported | 0 |
| Adverse signals | 5 |
| Stored scores | 4 of 4 alerts |
| Overrides | 0 of 4 alerts |

A test prescription in a synthetic peptic-ulcer case exercised the interaction and contraindication paths. A separate transaction used a real FDA label to verify the provenance join and was rolled back after verification. The Analytics page uses stored data to render its severity, risk, PRR and specialty charts.

## Discussion and limitations

The trigger records the message and affected item. The app reconstructs the current rule using the medicine, alert type, target named in the message and severity. Historical explanations can become unavailable when rules are replaced or several current rows match. Contraindication rows retain a label ID and condition but have no mechanism column. The app recovers the most likely matching sentence using the extraction logic. PRR compares the proportion of reports that mention a reaction for one medicine with the proportion for other medicines. An elevated PRR calls for investigation and does not establish causation. [Evans et al., proportional reporting ratios](https://doi.org/10.1002/pds.677).

## Screenshots

**Report placement:** Insert the Safety alerts detail, saved prescription result, and full-page Analytics views for the doctor and pharmacist. The local screenshots are in [screenshots](screenshots/).

Available verification captures:

- [FDA explanation and source link](screenshots/safety-alerts-fda.png) from a temporary test alert using an actual openFDA label.
- [Curated rule and stored score](screenshots/safety-alerts.png) from the seed database.
- [Prescription result with live estimates](screenshots/prescription-result.png) from the synthetic patient.
- [Doctor Analytics](screenshots/analytics-doctor.png) and [pharmacist Analytics](screenshots/analytics-pharmacist.png) from the seed database before the bridge import.
