"""Load medication master data from MongoDB openFDA labels into PostgreSQL."""

from pymongo import MongoClient
from medisentinel import config, db


def label_to_medication(label: dict) -> dict | None:
    """Pure mapping function: converts an openFDA label dict into a Medication dict.

    Returns None if there is no generic name.
    Does not interact with any database.
    """
    if not isinstance(label, dict):
        return None

    openfda = label.get("openfda")
    if not isinstance(openfda, dict):
        return None

    generic_names = openfda.get("generic_name")
    if not generic_names or not generic_names[0] or not str(generic_names[0]).strip():
        return None

    raw_generic = str(generic_names[0]).strip()
    generic_name = raw_generic.lower()[:150]

    brand_names = openfda.get("brand_name")
    if brand_names and brand_names[0] and str(brand_names[0]).strip():
        raw_name = str(brand_names[0]).strip()
    else:
        raw_name = raw_generic
    name = raw_name.title()[:150]

    rxcuis = openfda.get("rxcui")
    rxcui = str(rxcuis[0]).strip()[:20] if rxcuis and rxcuis[0] else None

    pharm_classes = openfda.get("pharm_class_epc")
    drug_class = None
    if pharm_classes and pharm_classes[0]:
        cls_str = str(pharm_classes[0]).strip()
        if cls_str.endswith(" [EPC]"):
            cls_str = cls_str[:-6].strip()
        drug_class = cls_str[:100] if cls_str else None

    return {
        "name": name,
        "generic_name": generic_name,
        "rxcui": rxcui,
        "drug_class": drug_class,
    }


def load_medications():
    """Read all labels from MongoDB, convert them, and insert into PostgreSQL."""
    client = MongoClient(config.MONGO_URI)
    mongo_db = client[config.MONGO_DB]
    labels_col = mongo_db["medication_labels"]

    conn = db.connect_as("ms_admin")

    with conn.cursor() as cur:
        # Fetch existing generic names (lower case) to avoid duplicating demo meds
        cur.execute("SELECT LOWER(generic_name) AS gname FROM medication;")
        existing_generics = {row["gname"] for row in cur.fetchall() if row.get("gname")}

        labels_read = 0
        inserted = 0
        skipped = 0

        for label in labels_col.find():
            labels_read += 1
            med = label_to_medication(label)
            if not med:
                skipped += 1
                continue

            # Skip if generic_name already exists in Medication table (case-insensitive)
            if med["generic_name"].lower() in existing_generics:
                skipped += 1
                continue

            # Insert with ON CONFLICT (rxcui) DO NOTHING
            cur.execute(
                """
                INSERT INTO medication (name, generic_name, rxcui, drug_class)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (rxcui) DO NOTHING
                RETURNING med_id;
                """,
                (med["name"], med["generic_name"], med["rxcui"], med["drug_class"])
            )
            res = cur.fetchone()
            if res:
                inserted += 1
                existing_generics.add(med["generic_name"].lower())
            else:
                skipped += 1

    conn.close()
    client.close()

    print("\n--- Medication Loader Summary ---")
    print(f"Labels read from MongoDB: {labels_read}")
    print(f"Medications inserted:    {inserted}")
    print(f"Labels skipped:          {skipped}")


if __name__ == "__main__":
    load_medications()
