"""Generate realistic synthetic clinical data for MediSentinel.

Inserts doctors as ms_admin, then generates patients and prescriptions
as ms_doctor, firing database safety triggers and logging alerts.
"""

import argparse
import random
from datetime import date, timedelta
from faker import Faker
from medisentinel import db
from medisentinel.constants import FREQUENCIES, GENDERS, ORGAN_FUNCTION


SPECIALTIES = [
    "General Medicine",
    "Cardiology",
    "Endocrinology",
    "Nephrology",
    "Neurology",
    "Gastroenterology",
    "Pulmonology",
    "Oncology",
    "Pediatrics",
    "Orthopedics",
]

ALLERGY_REACTIONS = [
    "Severe skin rash and itching",
    "Anaphylaxis and breathlessness",
    "Facial angioedema",
    "Urticaria / hives",
    "Bronchospasm",
]


def generate_synthetic_data(num_patients: int = 100, num_prescriptions: int = 300, seed: int = 42):
    random.seed(seed)
    fake = Faker("en_IN")
    Faker.seed(seed)

    print(f"Connecting as ms_admin to verify/create doctors (seed={seed})...")
    admin_conn = db.connect_as("ms_admin")
    doctor_ids = []

    with admin_conn.cursor() as cur:
        # Check existing doctors
        cur.execute("SELECT doctor_id FROM doctor;")
        existing_doc_rows = cur.fetchall()
        doctor_ids = [row["doctor_id"] for row in existing_doc_rows]

        # Insert 10 doctors if needed
        needed = max(0, 10 - len(doctor_ids))
        for _ in range(needed):
            doc_name = f"Dr. {fake.first_name()} {fake.last_name()}"
            specialty = random.choice(SPECIALTIES)
            cur.execute(
                "INSERT INTO doctor (full_name, specialty) VALUES (%s, %s) RETURNING doctor_id;",
                (doc_name, specialty)
            )
            doctor_ids.append(cur.fetchone()["doctor_id"])

    admin_conn.close()
    print(f"Total available doctors: {len(doctor_ids)}")

    print(f"Connecting as ms_doctor to generate {num_patients} patients and {num_prescriptions} prescriptions...")
    doc_conn = db.connect_as("ms_doctor")

    available_meds = db.list_medications(doc_conn)
    if not available_meds:
        doc_conn.close()
        raise RuntimeError("No medications found in database. Please run load_medications.py first.")
    med_ids = [m["med_id"] for m in available_meds]

    known_conditions = db.list_conditions(doc_conn)
    if not known_conditions:
        known_conditions = ["hypertension", "type 2 diabetes", "asthma", "peptic ulcer", "chronic kidney disease"]

    # Gender choices and organ function distribution (mostly "normal")
    gender_keys = list(GENDERS.keys())
    organ_weights = [0.80, 0.15, 0.05]

    patient_ids = []
    today = date.today()

    print("Generating patients...")
    for _ in range(num_patients):
        full_name = f"{fake.first_name()} {fake.last_name()}"
        age = random.randint(18, 90)
        dob = today - timedelta(days=age * 365 + random.randint(0, 364))
        gender = random.choice(gender_keys)
        renal = random.choices(ORGAN_FUNCTION, weights=organ_weights)[0]
        hepatic = random.choices(ORGAN_FUNCTION, weights=organ_weights)[0]

        # 0-3 conditions
        num_conds = random.randint(0, min(3, len(known_conditions)))
        conds = random.sample(known_conditions, num_conds)

        # 0-2 allergies to random medicines
        num_allergies = random.randint(0, min(2, len(med_ids)))
        allergy_meds = random.sample(med_ids, num_allergies)
        allergies = [(m_id, random.choice(ALLERGY_REACTIONS)) for m_id in allergy_meds]

        p_id = db.add_patient(
            doc_conn,
            full_name=full_name,
            dob=dob,
            gender=gender,
            renal=renal,
            hepatic=hepatic,
            conditions=conds,
            allergies=allergies,
        )
        patient_ids.append(p_id)

    print(f"Created {len(patient_ids)} patients.")

    print(f"Creating {num_prescriptions} prescriptions (firing safety trigger)...")
    total_alerts_raised = 0
    prescriptions_created = 0

    dose_values = [100, 200, 250, 500, 650, 1000]

    for _ in range(num_prescriptions):
        patient_id = random.choice(patient_ids)
        doctor_id = random.choice(doctor_ids)

        # 1-4 DIFFERENT medicines
        num_items = random.randint(1, min(4, len(med_ids)))
        selected_meds = random.sample(med_ids, num_items)

        items = []
        for m_id in selected_meds:
            dose_str = f"{random.choice(dose_values)} mg"
            freq_str = random.choice(FREQUENCIES)
            items.append({
                "med_id": m_id,
                "dose": dose_str,
                "frequency": freq_str
            })

        rx_id, alerts = db.create_prescription(
            doc_conn,
            patient_id=patient_id,
            doctor_id=doctor_id,
            items=items
        )
        prescriptions_created += 1
        total_alerts_raised += len(alerts)

    doc_conn.close()

    print("\n--- Synthetic Data Generation Summary ---")
    print(f"Doctors active:         {len(doctor_ids)}")
    print(f"Patients generated:     {len(patient_ids)}")
    print(f"Prescriptions created:  {prescriptions_created}")
    print(f"Safety alerts raised:   {total_alerts_raised}")


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic patients and prescriptions.")
    parser.add_argument("--patients", type=int, default=100, help="Number of patients (default: 100)")
    parser.add_argument("--prescriptions", type=int, default=300, help="Number of prescriptions (default: 300)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    args = parser.parse_args()

    generate_synthetic_data(
        num_patients=args.patients,
        num_prescriptions=args.prescriptions,
        seed=args.seed
    )


if __name__ == "__main__":
    main()
