"""Download medication labels and adverse-event reports from openFDA into MongoDB."""

import argparse
import time
import requests
from pymongo import MongoClient, ReplaceOne
from medisentinel import config


OPENFDA_LABEL_URL = "https://api.fda.gov/drug/label.json"
OPENFDA_EVENT_URL = "https://api.fda.gov/drug/event.json"


def fetch_paged_data(base_url: str, params: dict, target_count: int, max_batch_size: int = 1000) -> list[dict]:
    """Fetch target_count documents from openFDA using pagination with limit and skip."""
    results = []
    skip = 0

    while len(results) < target_count:
        fetch_limit = min(max_batch_size, target_count - len(results))
        req_params = {**params, "limit": fetch_limit, "skip": skip}

        for attempt in range(5):
            try:
                resp = requests.get(base_url, params=req_params, timeout=45)
                if resp.status_code == 200:
                    data = resp.json()
                    batch = data.get("results", [])
                    if not batch:
                        return results
                    results.extend(batch)
                    print(f"Fetched {len(results)}/{target_count} records from {base_url}...")
                    break
                elif resp.status_code == 404:
                    print(f"No more results found at skip={skip}.")
                    return results
                elif resp.status_code in (403, 429, 500, 502, 503, 504):
                    wait_time = (attempt + 1) * 2
                    print(f"HTTP {resp.status_code} on skip={skip}. Backing off {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    resp.raise_for_status()
            except requests.RequestException as e:
                wait_time = (attempt + 1) * 2
                print(f"Network error: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
        else:
            print("Max retries exceeded. Proceeding with what was collected.")
            break

        skip += len(batch)
        if skip >= 25000:
            print("Reached openFDA skip limit (25000).")
            break
        time.sleep(0.3)

    return results


def load_openfda(label_count: int = 1000, report_count: int = 5000):
    client = MongoClient(config.MONGO_URI)
    db = client[config.MONGO_DB]

    medication_labels = db["medication_labels"]
    adverse_reports = db["adverse_reports"]

    print(f"\n1. Fetching up to {label_count} drug labels from openFDA...")
    labels = fetch_paged_data(
        OPENFDA_LABEL_URL,
        {"search": "_exists_:drug_interactions"},
        label_count,
        max_batch_size=1000
    )

    if labels:
        print(f"Upserting {len(labels)} drug labels into MongoDB...")
        label_ops = []
        for doc in labels:
            doc_id = doc.get("id")
            if not doc_id:
                continue
            doc["_id"] = doc_id
            label_ops.append(ReplaceOne({"_id": doc_id}, doc, upsert=True))

        if label_ops:
            medication_labels.bulk_write(label_ops, ordered=False)

    print(f"\n2. Fetching up to {report_count} adverse-event reports from openFDA...")
    # openFDA enforces a max limit of 500 per request on the drug/event endpoint without api key
    reports = fetch_paged_data(
        OPENFDA_EVENT_URL,
        {},
        report_count,
        max_batch_size=500
    )

    if reports:
        print(f"Upserting {len(reports)} adverse-event reports into MongoDB...")
        report_ops = []
        for doc in reports:
            report_id = doc.get("safetyreportid")
            if not report_id:
                continue
            doc["_id"] = report_id
            report_ops.append(ReplaceOne({"_id": report_id}, doc, upsert=True))

        if report_ops:
            adverse_reports.bulk_write(report_ops, ordered=False)

    print("\n3. Creating indexes...")
    medication_labels.create_index("openfda.generic_name")
    medication_labels.create_index("openfda.rxcui")
    adverse_reports.create_index("patient.drug.medicinalproduct")
    adverse_reports.create_index("patient.reaction.reactionmeddrapt")

    total_labels = medication_labels.count_documents({})
    total_reports = adverse_reports.count_documents({})

    print("\n--- Ingestion Summary ---")
    print(f"medication_labels collection: {total_labels} documents")
    print(f"adverse_reports collection:   {total_reports} documents")
    print("Indexes created:")
    print("  medication_labels: openfda.generic_name, openfda.rxcui")
    print("  adverse_reports:   patient.drug.medicinalproduct, patient.reaction.reactionmeddrapt")


def main():
    parser = argparse.ArgumentParser(description="Ingest openFDA labels and adverse reports into MongoDB.")
    parser.add_argument("--labels", type=int, default=1000, help="Number of drug labels to fetch (default: 1000)")
    parser.add_argument("--reports", type=int, default=5000, help="Number of adverse reports to fetch (default: 5000)")
    args = parser.parse_args()

    load_openfda(label_count=args.labels, report_count=args.reports)


if __name__ == "__main__":
    main()
