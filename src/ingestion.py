
from __future__ import annotations

from pathlib import Path

import pandas as pd
from src.cases import generate_cases
from src.rules import generate_flags

from src.api_client import get_national_holidays
from src.data_loader import load_cases, load_master_data
from src.database import (
    connect_database,
    create_database,
    insert_accepted_loans,
    insert_holidays,
    insert_master_data,
    insert_flags,
    insert_cases,
)
from src.validation import validate_input



def run_ingestion(
    loans_path: Path,
    assets_path: Path,
    borrowers_path: Path,
    output_dir: Path,
    database_path: Path,
    holiday_cache_path: Path,
    scope: str = "team",
) -> dict[str, int]:
    """Run validation, rule evaluation, and case generation."""

    if scope not in {"team", "solo"}:
        raise ValueError("scope must be either 'team' or 'solo'.")

    # 1. Load and validate the input data.
    loans = load_cases(loans_path)
    assets, borrowers = load_master_data(
        assets_path,
        borrowers_path,
    )

    accepted, rejected = validate_input(
        loans,
        assets,
        borrowers,
    )

    # 2. Retrieve nationwide Hungarian public holidays.
    holidays = get_national_holidays(holiday_cache_path)

    # 3. Gemini integration comes later.
    # Until then, no extraction results are available.
    extractions = pd.DataFrame(
        columns=[
            "RecordID",
            "item_condition",
            "missing_accessories",
            "extension_requested",
            "ExtractionStatus",
        ]
    )

    # 4. Generate rule flags and review cases.
    flags = generate_flags(
        accepted,
        borrowers,
        holidays,
        extractions,
        scope=scope,
    )

    cases = generate_cases(
        accepted,
        assets,
        borrowers,
        extractions,
        flags,
    )

    # 5. Rebuild the database and insert all records.
    create_database(database_path)

    connection = connect_database(database_path)

    try:
        insert_master_data(connection, assets, borrowers)
        insert_accepted_loans(connection, accepted)
        insert_holidays(connection, holidays)
        insert_flags(connection, flags)
        insert_cases(connection, cases)

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    # 6. Export pipeline outputs.
    output_dir.mkdir(parents=True, exist_ok=True)

    accepted.to_csv(
        output_dir / "accepted_loans.csv",
        index=False,
    )

    rejected.to_csv(
        output_dir / "rejected.csv",
        index=False,
    )

    flags.to_csv(
        output_dir / "flags.csv",
        index=False,
    )

    cases.to_csv(
        output_dir / "cases.csv",
        index=False,
    )

    return {
        "input_records": len(loans),
        "accepted_records": len(accepted),
        "rejected_records": len(rejected),
        "asset_records": len(assets),
        "borrower_records": len(borrowers),
        "holiday_records": len(holidays),
        "flag_records": len(flags),
        "case_records": len(cases),
    }
