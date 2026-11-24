"""Read alert provenance across PostgreSQL and MongoDB."""
from urllib.parse import urlencode

from bson import ObjectId
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from medisentinel import config
from nlp.extract_rules import Extractor, label_sentences, language_model, normalize

INTERACTION_PREFIX = "Interaction with current medication: "
CONTRA_PREFIX = "Contraindicated for condition: "


def interaction_rules(conn, alert, other):
    return conn.execute("""
        SELECT i.mechanism, i.source_label_id
        FROM Interaction i
        JOIN Medication m ON m.med_id = CASE WHEN i.med_id_1 = %s THEN i.med_id_2 ELSE i.med_id_1 END
        WHERE %s IN (i.med_id_1, i.med_id_2) AND m.name = %s AND i.severity = %s
        ORDER BY i.interaction_id
    """, (alert["med_id"], alert["med_id"], other, alert["severity"])).fetchall()


def contraindication_rules(conn, alert, condition):
    return conn.execute("""
        SELECT source_label_id, NULL::text AS mechanism
        FROM Contraindication
        WHERE med_id = %s AND condition_name = %s AND severity IS NOT DISTINCT FROM %s
        ORDER BY contra_id
    """, (alert["med_id"], condition, alert["severity"])).fetchall()


def matching_sentence(label, section, mechanism, condition, severity):
    """Recover the full original text or reconstruct a contraindication match."""
    if mechanism and not label:
        return mechanism
    if not label:
        return None
    nlp = language_model()
    sentences = (sentence for _, sentence in label_sentences(label, nlp, (section,)))
    if mechanism:
        return next((sentence for sentence in sentences if sentence.startswith(mechanism)), mechanism)
    if condition:
        condition = normalize(condition)
        matcher = Extractor({}, {condition: condition}, nlp)
        matches = [(confidence, sentence) for sentence in sentences
                   for _, level, confidence in matcher.predict(sentence, "", "contraindication")
                   if level == severity]
        # Same confidence rule and first-sentence tie-break as the extractor.
        return max(matches, default=(0, None), key=lambda match: match[0])[1]
    return None


def explain_alert(conn, alert_id):
    alert = conn.execute("""
        SELECT a.alert_type, a.message, a.severity, a.risk_score, i.med_id
        FROM Alert_Log a JOIN Prescription_Item i USING (item_id)
        WHERE a.alert_id = %s
    """, (alert_id,)).fetchone()
    if not alert:
        return None
    explanation = {"score": alert["risk_score"], "message": alert["message"], "status": "Rule unavailable"}
    message = alert["message"] or ""
    condition = None
    if alert["alert_type"] == "INTERACTION" and message.startswith(INTERACTION_PREFIX):
        other = message.removeprefix(INTERACTION_PREFIX)
        rules = interaction_rules(conn, alert, other)
        section = "drug_interactions"
    elif alert["alert_type"] == "CONTRA" and message.startswith(CONTRA_PREFIX):
        condition = message.removeprefix(CONTRA_PREFIX)
        rules = contraindication_rules(conn, alert, condition)
        section = "contraindications"
    elif alert["alert_type"] == "ALLERGY":
        explanation["status"] = "Recorded patient allergy"
        return explanation
    else:
        return explanation
    if len(rules) != 1:
        return explanation

    rule = rules[0]
    source_id = rule["source_label_id"]
    if not source_id:
        explanation.update(status="Curated rule", sentence=rule["mechanism"])
        return explanation
    ids = [source_id]
    if ObjectId.is_valid(source_id):
        ids.append(ObjectId(source_id))
    try:
        with MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=2000) as client:
            label = client[config.MONGO_DB].medication_labels.find_one(
                {"_id": {"$in": ids}}, {"openfda.brand_name": 1, section: 1})
    except PyMongoError:
        label = None
    mechanism = rule["mechanism"]
    try:
        sentence = matching_sentence(label, section, mechanism, condition, alert["severity"])
    except OSError:
        sentence = mechanism
    brands = ((label or {}).get("openfda") or {}).get("brand_name") or []
    query = urlencode({"search": f'id:"{source_id}"', "limit": 1})
    explanation.update(
        status="FDA label" if label else "FDA label unavailable locally",
        sentence=sentence, brand=", ".join(brands), source_id=source_id,
        url=f"https://api.fda.gov/drug/label.json?{query}",
    )
    return explanation
