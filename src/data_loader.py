
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config import REQUIRED_LOAN_COLUMNS


def load_csv(path: Path) -> pd.DataFrame:
    """Load a CSV file while preserving values as strings."""
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def validate_loan_columns(df: pd.DataFrame) -> None:
    """Check that the loan input contains all required columns."""
    missing_columns = REQUIRED_LOAN_COLUMNS - set(df.columns)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Missing required loan columns: {missing}")


def load_cases(path: Path) -> pd.DataFrame:
    """Load loan records and check the input structure."""
    df = load_csv(path)
    validate_loan_columns(df)

    # CSV line 1 contains the header, so the first data row is line 2.
    df.insert(0, "SourceRow", range(2, len(df) + 2))

    return df


def load_master_data(
    assets_path: Path,
    borrowers_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the asset and borrower master data."""
    assets = load_csv(assets_path)
    borrowers = load_csv(borrowers_path)

    required_asset_columns = {
        "AssetID",
        "AssetName",
        "Category",
        "ReplacementValueHUF",
    }

    required_borrower_columns = {
        "BorrowerID",
        "BorrowerAlias",
        "Faculty",
        "BorrowerType",
        "MaxOpenLoans",
    }

    missing_asset_columns = required_asset_columns - set(assets.columns)
    missing_borrower_columns = required_borrower_columns - set(borrowers.columns)

    if missing_asset_columns:
        missing = ", ".join(sorted(missing_asset_columns))
        raise ValueError(f"Missing required asset columns: {missing}")

    if missing_borrower_columns:
        missing = ", ".join(sorted(missing_borrower_columns))
        raise ValueError(f"Missing required borrower columns: {missing}")

    return assets, borrowers
