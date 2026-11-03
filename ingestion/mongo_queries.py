"""MongoDB aggregation demo queries for adverse-event surveillance."""

import re

from pymongo import MongoClient
from medisentinel import config


_client = None


def get_db():
    """The openFDA database; one MongoClient (it pools connections) is reused for every query."""
    global _client
    if _client is None:
        _client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=3000)
    return _client[config.MONGO_DB]


def top_reactions(n: int = 10) -> list[dict]:
    """Return top N reported adverse reactions across all reports using aggregation pipeline."""
    db = get_db()
    pipeline = [
        {"$unwind": "$patient.reaction"},
        {
            "$group": {
                "_id": "$patient.reaction.reactionmeddrapt",
                "report_count": {"$sum": 1}
            }
        },
        {"$match": {"_id": {"$ne": None}}},
        {"$sort": {"report_count": -1}},
        {"$limit": n}
    ]
    return list(db["adverse_reports"].aggregate(pipeline))


def top_reported_drugs(n: int = 10) -> list[dict]:
    """Return top N reported suspect drugs across all reports using aggregation pipeline."""
    db = get_db()
    pipeline = [
        {"$unwind": "$patient.drug"},
        {
            "$group": {
                "_id": "$patient.drug.medicinalproduct",
                "report_count": {"$sum": 1}
            }
        },
        {"$match": {"_id": {"$ne": None}}},
        {"$sort": {"report_count": -1}},
        {"$limit": n}
    ]
    return list(db["adverse_reports"].aggregate(pipeline))


def collection_counts() -> dict:
    """Number of documents in each openFDA collection."""
    db = get_db()
    return {"labels": db["medication_labels"].estimated_document_count(),
            "reports": db["adverse_reports"].estimated_document_count()}


def find_labels(search: str, limit: int = 10) -> list[dict]:
    """Drug labels whose generic or brand name starts with `search` (case-insensitive)."""
    db = get_db()
    pattern = {"$regex": "^" + re.escape(search.strip()), "$options": "i"}
    projection = {"openfda.brand_name": 1, "openfda.generic_name": 1, "openfda.manufacturer_name": 1,
                  "openfda.pharm_class_epc": 1, "drug_interactions": 1, "contraindications": 1,
                  "boxed_warning": 1}
    query = {"$or": [{"openfda.generic_name": pattern}, {"openfda.brand_name": pattern}]}
    return list(db["medication_labels"].find(query, projection).limit(limit))


def reactions_for_drug(drug: str, n: int = 10) -> list[dict]:
    """Top N reactions in reports that mention `drug` (matched on the start of the product name)."""
    db = get_db()
    name = {"$regex": "^" + re.escape(drug.strip()), "$options": "i"}
    pipeline = [
        {"$match": {"patient.drug.medicinalproduct": name}},
        {"$unwind": "$patient.reaction"},
        {"$group": {"_id": "$patient.reaction.reactionmeddrapt", "report_count": {"$sum": 1}}},
        {"$match": {"_id": {"$ne": None}}},
        {"$sort": {"report_count": -1}},
        {"$limit": n},
    ]
    return list(db["adverse_reports"].aggregate(pipeline))


def print_table(title: str, headers: tuple[str, str], rows: list[dict]):
    print(f"\n=== {title} ===")
    col1, col2 = headers
    print(f"{'#':<4} {col1:<45} {col2:>12}")
    print("-" * 65)
    for idx, row in enumerate(rows, start=1):
        name = str(row.get("_id") or "UNKNOWN")[:44]
        count = row.get("report_count", 0)
        print(f"{idx:<4} {name:<45} {count:>12,}")


def main():
    print("Running MongoDB adverse event surveillance aggregations...")
    reactions = top_reactions(n=10)
    print_table("Top 10 Adverse Reactions (reactionmeddrapt)", ("Adverse Reaction", "Reports"), reactions)

    drugs = top_reported_drugs(n=10)
    print_table("Top 10 Reported Drugs (medicinalproduct)", ("Medicinal Product", "Reports"), drugs)


if __name__ == "__main__":
    main()
