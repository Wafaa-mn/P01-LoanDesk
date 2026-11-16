
from __future__ import annotations

from datetime import date

import pandas as pd

from src.config import ALLOWED_PURPOSES


REJECTED_COLUMNS = ["SourceRow", "RecordID", "ReasonCode"]


def clean_value(value: object) -> str:
    """Convert a value to a trimmed string."""
    if pd.isna(value):
        return ""

    return str(value).strip()


def is_valid_date(value: str) -> bool:
    """Check whether a date uses the exact YYYY-MM-DD format."""
    try:
        parsed_date = date.fromisoformat(value)
        return parsed_date.isoformat() == value
    except ValueError:
        return False


def validate_input(
    df: pd.DataFrame,
    assets: pd.DataFrame,
    borrowers: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Validate loan records and separate accepted and rejected records."""

    # Work on a copy so the original DataFrame is not modified.
    df = df.copy()

    # Add source row numbers if the loader has not already added them.
    if "SourceRow" not in df.columns:
        df.insert(0, "SourceRow", range(2, len(df) + 2))

    # Remove surrounding whitespace before performing checks.
    for column in df.columns:
        if column != "SourceRow":
            df[column] = df[column].apply(clean_value)

    # Build sets of valid master-data IDs.
    valid_asset_ids = set(assets["AssetID"].apply(clean_value))
    valid_borrower_ids = set(borrowers["BorrowerID"].apply(clean_value))

    seen_ids = set()
    accepted_indices = []
    rejected_records = []

    for index, row in df.iterrows():
        loan_id = row["LoanID"]
        asset_id = row["AssetID"]
        borrower_id = row["BorrowerID"]

        reason_code = None

        # 1. Missing ID
        if not loan_id:
            reason_code = "MISSING_ID"

        # 2. Duplicate ID
        elif loan_id in seen_ids:
            reason_code = "DUPLICATE_ID"

        else:
            # Remember the ID even if a later check rejects this record.
            seen_ids.add(loan_id)

            # 3. Unknown reference
            if (
                asset_id not in valid_asset_ids
                or borrower_id not in valid_borrower_ids
            ):
                reason_code = "UNKNOWN_REFERENCE"

            # 4. Invalid date
            elif (
                not is_valid_date(row["LoanDate"])
                or not is_valid_date(row["DueDate"])
                or (
                    row["ReturnedDate"]
                    and not is_valid_date(row["ReturnedDate"])
                )
            ):
                reason_code = "INVALID_DATE"

            # 5. Invalid value
            elif row["Purpose"] not in ALLOWED_PURPOSES:
                reason_code = "INVALID_VALUE"

        if reason_code is None:
            accepted_indices.append(index)
        else:
            rejected_records.append(
                {
                    "SourceRow": row["SourceRow"],
                    "RecordID": loan_id,
                    "ReasonCode": reason_code,
                }
            )

    accepted = df.loc[accepted_indices].copy().reset_index(drop=True)

    rejected = pd.DataFrame(
        rejected_records,
        columns=REJECTED_COLUMNS,
    )

    return accepted, rejected
