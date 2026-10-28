"""Pure validation functions for patient and prescription input forms.

These functions have no Streamlit or database dependencies, returning a list of
error messages (an empty list indicates the input is valid).
"""
import datetime
import re
from typing import Any, Mapping, Sequence

from medisentinel.constants import DOSE_UNITS, FREQUENCIES

_NAME_ALLOWED_CHARS = re.compile(r"^[A-Za-z\s.']+$")
_DOSE_REGEX = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([A-Za-z]+)\s*$")


def validate_name(name: Any) -> list[str]:
    """Validate a person's full name.

    Rules:
    - Required
    - 2 to 100 characters
    - Letters, spaces, dots (.), and apostrophes (') only
    """
    if name is None:
        return ["Name is required."]

    name_str = str(name).strip()
    if not name_str:
        return ["Name is required."]

    errors: list[str] = []
    if len(name_str) < 2 or len(name_str) > 100:
        errors.append("Name must be between 2 and 100 characters.")

    if not _NAME_ALLOWED_CHARS.match(name_str):
        errors.append("Name may only contain letters, spaces, dots, and apostrophes.")

    return errors


def validate_dob(dob: Any) -> list[str]:
    """Validate date of birth.

    Rules:
    - Required
    - Cannot be in the future
    - Age between 0 and 120 years
    """
    if dob is None:
        return ["Date of birth is required."]

    parsed_date: datetime.date
    if isinstance(dob, datetime.datetime):
        parsed_date = dob.date()
    elif isinstance(dob, datetime.date):
        parsed_date = dob
    elif isinstance(dob, str):
        try:
            parsed_date = datetime.date.fromisoformat(dob.strip())
        except ValueError:
            return ["Invalid date format. Expected YYYY-MM-DD."]
    else:
        return ["Invalid date format."]

    today = datetime.date.today()
    if parsed_date > today:
        return ["Date of birth cannot be in the future."]

    age = today.year - parsed_date.year - (
        (today.month, today.day) < (parsed_date.month, parsed_date.day)
    )
    if age > 120:
        return ["Age cannot exceed 120 years."]

    return []


def validate_dose(dose: Any) -> list[str]:
    """Validate medication dose string.

    Rules:
    - Required
    - Must be a positive number followed by a unit from medisentinel.constants.DOSE_UNITS
      e.g. '500 mg', '2.5 ml', '100 IU'
    """
    if dose is None:
        return ["Dose is required."]

    dose_str = str(dose).strip()
    if not dose_str:
        return ["Dose is required."]

    match = _DOSE_REGEX.match(dose_str)
    if not match:
        return [
            f"Dose must be a positive number followed by an allowed unit ({', '.join(DOSE_UNITS)})."
        ]

    amount_str, unit_str = match.groups()
    try:
        amount = float(amount_str)
    except ValueError:
        return ["Dose amount is not a valid number."]

    if amount <= 0:
        return ["Dose amount must be greater than zero."]

    matched_unit = next((u for u in DOSE_UNITS if u.lower() == unit_str.lower()), None)
    if not matched_unit:
        return [
            f"Invalid dose unit '{unit_str}'. Allowed units: {', '.join(DOSE_UNITS)}."
        ]

    return []


def validate_items(items: Sequence[Mapping[str, Any]] | Any) -> list[str]:
    """Validate prescription items.

    Rules:
    - At least one medicine item required
    - No duplicate medicines (same med_id cannot be prescribed twice)
    - Each item must have a valid dose
    - Each item must have a frequency from medisentinel.constants.FREQUENCIES
    """
    if not items:
        return ["Prescription must contain at least one medicine."]

    errors: list[str] = []
    seen_med_ids: set[Any] = set()

    for idx, item in enumerate(items, start=1):
        if not isinstance(item, Mapping):
            errors.append(f"Item #{idx}: invalid item format.")
            continue

        med_id = item.get("med_id")
        if med_id is None:
            errors.append(f"Item #{idx}: medicine must be selected.")
        elif med_id in seen_med_ids:
            errors.append(f"Item #{idx}: duplicate medicine detected (each medicine can only be included once).")
        else:
            seen_med_ids.add(med_id)

        dose = item.get("dose")
        dose_errors = validate_dose(dose)
        for err in dose_errors:
            errors.append(f"Item #{idx}: {err}")

        frequency = item.get("frequency")
        if not frequency:
            errors.append(f"Item #{idx}: frequency is required.")
        elif frequency not in FREQUENCIES:
            errors.append(
                f"Item #{idx}: invalid frequency '{frequency}'. Allowed: {', '.join(FREQUENCIES)}."
            )

    return errors
