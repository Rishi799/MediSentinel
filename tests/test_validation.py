"""Unit tests for app/validation.py rules."""

import datetime
import pytest

from app.validation import validate_dob, validate_dose, validate_items, validate_name


# =====================================================================
# validate_name
# =====================================================================

def test_validate_name_valid():
    assert validate_name("John Doe") == []
    assert validate_name("Dr. O'Connor") == []
    assert validate_name("A. B. Smith") == []


def test_validate_name_required():
    assert "Name is required." in validate_name("")
    assert "Name is required." in validate_name("   ")
    assert "Name is required." in validate_name(None)


def test_validate_name_too_short():
    errors = validate_name("A")
    assert any("between 2 and 100 characters" in e for e in errors)


def test_validate_name_too_long():
    long_name = "A" * 101
    errors = validate_name(long_name)
    assert any("between 2 and 100 characters" in e for e in errors)


def test_validate_name_invalid_characters():
    errors_numbers = validate_name("John123")
    assert any("letters, spaces, dots, and apostrophes" in e for e in errors_numbers)

    errors_symbols = validate_name("Ravi @ Kumar!")
    assert any("letters, spaces, dots, and apostrophes" in e for e in errors_symbols)


# =====================================================================
# validate_dob
# =====================================================================

def test_validate_dob_valid():
    today = datetime.date.today()
    assert validate_dob(datetime.date(1990, 5, 12)) == []
    assert validate_dob(today) == []  # newborn (age 0)
    assert validate_dob("2000-01-01") == []


def test_validate_dob_required():
    assert "Date of birth is required." in validate_dob(None)


def test_validate_dob_future_rejected():
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    errors = validate_dob(tomorrow)
    assert "Date of birth cannot be in the future." in errors


def test_validate_dob_age_over_120_rejected():
    old_date = datetime.date.today() - datetime.timedelta(days=365 * 125)
    errors = validate_dob(old_date)
    assert "Age cannot exceed 120 years." in errors


def test_validate_dob_invalid_format():
    errors = validate_dob("not-a-date")
    assert any("Invalid date format" in e for e in errors)


# =====================================================================
# validate_dose
# =====================================================================

def test_validate_dose_valid():
    assert validate_dose("500 mg") == []
    assert validate_dose("2.5 ml") == []
    assert validate_dose("100 IU") == []
    assert validate_dose("1 g") == []
    assert validate_dose("10 units") == []
    assert validate_dose("25 mcg") == []


def test_validate_dose_required():
    assert "Dose is required." in validate_dose("")
    assert "Dose is required." in validate_dose("   ")
    assert "Dose is required." in validate_dose(None)


def test_validate_dose_missing_unit_or_invalid_format():
    errors_no_unit = validate_dose("500")
    assert any("positive number followed by an allowed unit" in e for e in errors_no_unit)

    errors_text_only = validate_dose("five hundred milligrams")
    assert any("positive number followed by an allowed unit" in e for e in errors_text_only)


def test_validate_dose_non_positive_amount():
    errors_zero = validate_dose("0 mg")
    assert "Dose amount must be greater than zero." in errors_zero


def test_validate_dose_unsupported_unit():
    errors = validate_dose("500 tablets")
    assert any("Invalid dose unit 'tablets'" in e for e in errors)


# =====================================================================
# validate_items
# =====================================================================

def test_validate_items_valid():
    items = [
        {"med_id": 1, "dose": "500 mg", "frequency": "once daily"},
        {"med_id": 2, "dose": "2.5 ml", "frequency": "twice daily"},
    ]
    assert validate_items(items) == []


def test_validate_items_empty_rejected():
    errors = validate_items([])
    assert "Prescription must contain at least one medicine." in errors


def test_validate_items_duplicate_medicine_rejected():
    items = [
        {"med_id": 1, "dose": "500 mg", "frequency": "once daily"},
        {"med_id": 1, "dose": "250 mg", "frequency": "twice daily"},
    ]
    errors = validate_items(items)
    assert any("duplicate medicine detected" in e for e in errors)


def test_validate_items_invalid_dose():
    items = [
        {"med_id": 1, "dose": "invalid_dose", "frequency": "once daily"},
    ]
    errors = validate_items(items)
    assert any("positive number followed by an allowed unit" in e for e in errors)


def test_validate_items_invalid_frequency():
    items = [
        {"med_id": 1, "dose": "500 mg", "frequency": "whenever needed"},
    ]
    errors = validate_items(items)
    assert any("invalid frequency 'whenever needed'" in e for e in errors)
