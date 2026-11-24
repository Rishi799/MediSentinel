"""Extract explainable drug interactions and contraindications from openFDA labels."""
import argparse
from collections import Counter
from functools import lru_cache
import json
from pathlib import Path
import re

from pymongo import MongoClient
import spacy
from spacy.matcher import PhraseMatcher
from spacy.util import filter_spans

from medisentinel import config, db

ROOT = Path(__file__).resolve().parent
RULES_PATH = ROOT / "output" / "rules.jsonl"
SECTIONS = {"drug_interactions": "interaction", "contraindications": "contraindication"}
BUILT_IN_CONDITIONS = (
    "peptic ulcer", "chronic kidney disease", "renal failure", "liver disease",
    "hyperkalemia", "pregnancy", "asthma", "heart failure", "hypertension",
    "diabetes", "epilepsy", "bleeding disorder", "glaucoma",
)
LEXICON = {
    "MAJOR": ("contraindicated", "fatal", "death", "life-threatening", "avoid",
              "do not use", "serious", "severe"),
    "MODERATE": ("monitor", "caution", "dose adjustment", "reduce the dose",
                 "increase the risk", "may increase", "potentiate"),
    "MINOR": ("minor", "slight", "small", "not clinically significant"),
}
PATTERNS = {
    severity: re.compile(r"\b(?:" + "|".join(map(re.escape, words)) + r")\b", re.I)
    for severity, words in LEXICON.items()
}
SEVERITY_RANK = {"MINOR": 1, "MODERATE": 2, "MAJOR": 3}


def normalize(value):
    return " ".join(str(value or "").casefold().split())


@lru_cache
def language_model():
    return spacy.load("en_core_web_sm", disable=["ner", "lemmatizer", "tagger", "attribute_ruler"])


def classify_severity(sentence):
    """Return severity and confidence using the lexicon in priority order."""
    for severity, pattern in PATTERNS.items():
        if pattern.search(sentence):
            return severity, 0.9
    return "MODERATE", 0.6


def make_matcher(nlp, aliases):
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    matcher.add("TERM", [nlp.make_doc(name) for name in sorted(aliases)])
    return matcher


def find_mentions(sentence, nlp, matcher, aliases):
    """Match whole tokens and prefer the longest overlapping phrase."""
    doc = nlp.make_doc(sentence)
    return list(dict.fromkeys(
        aliases[normalize(span.text)] for span in filter_spans(matcher(doc, as_spans=True))
    ))


def label_sentences(label, nlp, sections=SECTIONS):
    for section in sections:
        paragraphs = label.get(section) or []
        docs = nlp.pipe((" ".join(text.split()) for text in paragraphs if text), batch_size=8)
        for doc in docs:
            for sentence in doc.sents:
                if sentence.text.strip():
                    yield SECTIONS[section], sentence.text.strip()


def label_drugs(label):
    names = (label.get("openfda") or {}).get("generic_name") or []
    return list(dict.fromkeys(normalize(name) for name in names if normalize(name)))


class Extractor:
    def __init__(self, drugs, conditions, nlp):
        self.nlp = nlp
        self.drugs = drugs
        self.conditions = conditions
        self.drug_matcher = make_matcher(nlp, drugs)
        self.condition_matcher = make_matcher(nlp, conditions)

    def predict(self, sentence, drug, kind, own_names=()):
        if kind == "interaction":
            matches = find_mentions(sentence, self.nlp, self.drug_matcher, self.drugs)
            own = {self.drugs.get(name, name) for name in (*own_names, drug)}
            matches = [match for match in matches if match not in own]
        else:
            matches = find_mentions(sentence, self.nlp, self.condition_matcher, self.conditions)
        severity, confidence = classify_severity(sentence)
        return [(match, severity, confidence) for match in matches]


def load_extractor():
    with db.connect_as("ms_pharmacist") as conn:
        rows = conn.execute("SELECT generic_name, name FROM Medication ORDER BY med_id").fetchall()
        conditions = db.list_conditions(conn)
    drugs = {normalize(row["generic_name"]): normalize(row["generic_name"])
             for row in rows if normalize(row["generic_name"])}
    for row in rows:
        if normalize(row["name"]) and normalize(row["generic_name"]):
            drugs.setdefault(normalize(row["name"]), normalize(row["generic_name"]))
    condition_aliases = {normalize(condition): normalize(condition)
                         for condition in (*BUILT_IN_CONDITIONS, *conditions)}
    return Extractor(drugs, condition_aliases, language_model())


def extract(labels, extractor, min_confidence=0.6):
    rules = {}
    totals = Counter(labels=0, sentences=0, interaction=0, contraindication=0)
    for label in labels:
        totals["labels"] += 1
        names = label_drugs(label)
        for kind, sentence in label_sentences(label, extractor.nlp):
            totals["sentences"] += 1
            if not names:
                continue
            drug = extractor.drugs.get(names[0], names[0])
            for target, severity, confidence in extractor.predict(sentence, drug, kind, names):
                if confidence < min_confidence:
                    continue
                key = (kind, drug, target)
                old = rules.get(key)
                if old and (SEVERITY_RANK[old["severity"]], old["confidence"]) >= (
                    SEVERITY_RANK[severity], confidence
                ):
                    continue
                rules[key] = {
                    "kind": kind, "drug": drug,
                    ("other" if kind == "interaction" else "condition"): target,
                    "severity": severity, "mechanism": sentence[:300],
                    "source_label_id": str(label["_id"]), "confidence": confidence,
                }
    totals.update(kind for kind, _, _ in rules)
    return rules.values(), totals


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--min-confidence", type=float, default=0.6)
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if not 0 <= args.min_confidence <= 1:
        parser.error("--min-confidence must be between 0 and 1")
    extractor = load_extractor()
    with MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=5000) as client:
        collection = client[config.MONGO_DB].medication_labels
        labels = collection.find({}, {"openfda.generic_name": 1, **dict.fromkeys(SECTIONS, 1)})
        labels = labels.sort("_id", 1).limit(args.limit or 0)
        rules, totals = extract(labels, extractor, args.min_confidence)
    RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RULES_PATH.open("w", encoding="utf-8") as output:
        for rule in rules:
            output.write(json.dumps(rule, ensure_ascii=False) + "\n")
    print(f"Labels read: {totals['labels']:,} | Sentences: {totals['sentences']:,} | "
          f"Interaction rules: {totals['interaction']:,} | "
          f"Contraindication rules: {totals['contraindication']:,}")


if __name__ == "__main__":
    main()
