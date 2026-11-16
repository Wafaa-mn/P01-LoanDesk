
from __future__ import annotations

import pandas as pd
import pytest

from src.validation import validate_input


@pytest.fixture
def assets() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "AssetID": ["A01", "A02"],
        }
    )


@pytest.fixture
def borrowers() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "BorrowerID": ["B01", "B02"],
        }
    )


def make_loan(**overrides: str) -> dict:
    """Create a valid loan record, with optional field overrides."""
    loan = {
        "LoanID": "L-0001",
        "AssetID": "A01",
        "BorrowerID": "B01",
        "Purpose": "Course",
        "LoanDate": "2026-10-01",
        "DueDate": "2026-10-15",
        "ReturnedDate": "",
        "DeskNote": "Clean and working.",
    }

    loan.update(overrides)

    return loan


def test_valid_record_is_accepted(assets, borrowers):
    df = pd.DataFrame([make_loan()])

    accepted, rejected = validate_input(df, assets, borrowers)

    assert len(accepted) == 1
    assert len(rejected) == 0
    assert accepted.iloc[0]["LoanID"] == "L-0001"


def test_missing_loan_id_is_rejected(assets, borrowers):
    df = pd.DataFrame([make_loan(LoanID="")])

    accepted, rejected = validate_input(df, assets, borrowers)

    assert len(accepted) == 0
    assert rejected.iloc[0]["ReasonCode"] == "MISSING_ID"


def test_duplicate_id_is_rejected(assets, borrowers):
    df = pd.DataFrame(
        [
            make_loan(),
            make_loan(AssetID="A02"),
        ]
    )

    accepted, rejected = validate_input(df, assets, borrowers)

    assert len(accepted) == 1
    assert len(rejected) == 1
    assert rejected.iloc[0]["ReasonCode"] == "DUPLICATE_ID"


def test_id_is_tracked_even_if_first_record_is_rejected(
    assets,
    borrowers,
):
    df = pd.DataFrame(
        [
            make_loan(AssetID="UNKNOWN"),
            make_loan(),
        ]
    )

    accepted, rejected = validate_input(df, assets, borrowers)

    assert len(accepted) == 0
    assert rejected["ReasonCode"].tolist() == [
        "UNKNOWN_REFERENCE",
        "DUPLICATE_ID",
    ]


def test_unknown_reference_is_rejected(assets, borrowers):
    df = pd.DataFrame([make_loan(AssetID="UNKNOWN")])

    accepted, rejected = validate_input(df, assets, borrowers)

    assert len(accepted) == 0
    assert rejected.iloc[0]["ReasonCode"] == "UNKNOWN_REFERENCE"


def test_invalid_date_is_rejected(assets, borrowers):
    df = pd.DataFrame([make_loan(LoanDate="2026-02-30")])

    accepted, rejected = validate_input(df, assets, borrowers)

    assert len(accepted) == 0
    assert rejected.iloc[0]["ReasonCode"] == "INVALID_DATE"


def test_empty_returned_date_is_allowed(assets, borrowers):
    df = pd.DataFrame([make_loan(ReturnedDate="")])

    accepted, rejected = validate_input(df, assets, borrowers)

    assert len(accepted) == 1
    assert len(rejected) == 0


def test_invalid_purpose_is_rejected(assets, borrowers):
    df = pd.DataFrame([make_loan(Purpose="coursex")])

    accepted, rejected = validate_input(df, assets, borrowers)

    assert len(accepted) == 0
    assert rejected.iloc[0]["ReasonCode"] == "INVALID_VALUE"


def test_validation_priority_unknown_reference_before_date(
    assets,
    borrowers,
):
    df = pd.DataFrame(
        [
            make_loan(
                AssetID="UNKNOWN",
                LoanDate="2026-02-30",
                Purpose="coursex",
            )
        ]
    )

    accepted, rejected = validate_input(df, assets, borrowers)

    assert len(accepted) == 0
    assert rejected.iloc[0]["ReasonCode"] == "UNKNOWN_REFERENCE"


def test_validation_priority_date_before_invalid_purpose(
    assets,
    borrowers,
):
    df = pd.DataFrame(
        [
            make_loan(
                LoanDate="2026-02-30",
                Purpose="coursex",
            )
        ]
    )

    accepted, rejected = validate_input(df, assets, borrowers)

    assert len(accepted) == 0
    assert rejected.iloc[0]["ReasonCode"] == "INVALID_DATE"


def test_whitespace_is_stripped_before_validation(
    assets,
    borrowers,
):
    df = pd.DataFrame(
        [
            make_loan(
                LoanID=" L-0001 ",
                AssetID=" A01 ",
                BorrowerID=" B01 ",
                Purpose=" Course ",
            )
        ]
    )

    accepted, rejected = validate_input(df, assets, borrowers)

    assert len(accepted) == 1
    assert len(rejected) == 0
    assert accepted.iloc[0]["LoanID"] == "L-0001"


def test_source_row_numbers_are_preserved(assets, borrowers):
    df = pd.DataFrame(
        [
            make_loan(),
            make_loan(LoanID=""),
        ]
    )

    accepted, rejected = validate_input(df, assets, borrowers)

    assert accepted.iloc[0]["SourceRow"] == 2
    assert rejected.iloc[0]["SourceRow"] == 3


def test_rejected_output_has_required_columns(assets, borrowers):
    df = pd.DataFrame([make_loan(LoanID="")])

    accepted, rejected = validate_input(df, assets, borrowers)

    assert rejected.columns.tolist() == [
        "SourceRow",
        "RecordID",
        "ReasonCode",
    ]


def test_original_dataframe_is_not_modified(assets, borrowers):
    df = pd.DataFrame([make_loan(LoanID=" L-0001 ")])
    original = df.copy(deep=True)

    validate_input(df, assets, borrowers)

    pd.testing.assert_frame_equal(df, original)
