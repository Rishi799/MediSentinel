"""MongoDB aggregation demo queries for adverse-event surveillance."""

from pymongo import MongoClient
from medisentinel import config


def get_db():
    client = MongoClient(config.MONGO_URI)
    return client[config.MONGO_DB]


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
