
from __future__ import annotations

import pandas as pd
import pytest

from src.data_loader import (
    load_cases,
    load_csv,
    load_master_data,
)


def test_load_csv_reads_file_as_strings(tmp_path):
    csv_file = tmp_path / "sample.csv"
    csv_file.write_text(
        "ID,Name\n001,Anna\n002,Bence\n",
        encoding="utf-8",
    )

    df = load_csv(csv_file)

    assert len(df) == 2
    assert df.iloc[0]["ID"] == "001"
    assert df.iloc[1]["Name"] == "Bence"


def test_load_csv_preserves_empty_values(tmp_path):
    csv_file = tmp_path / "sample.csv"
    csv_file.write_text(
        "ID,Name\n001,\n",
        encoding="utf-8",
    )

    df = load_csv(csv_file)

    assert df.iloc[0]["Name"] == ""


def test_load_cases_adds_source_row_numbers(tmp_path):
    csv_file = tmp_path / "loans.csv"
    csv_file.write_text(
        "LoanID,AssetID,BorrowerID,Purpose,LoanDate,DueDate,ReturnedDate,DeskNote\n"
        "L-0001,A01,B01,Course,2026-10-01,2026-10-15,,Clean\n"
        "L-0002,A02,B02,Thesis,2026-10-02,2026-10-16,,Working\n",
        encoding="utf-8",
    )

    df = load_cases(csv_file)

    assert df["SourceRow"].tolist() == [2, 3]
    assert len(df) == 2


def test_load_cases_raises_error_when_required_column_is_missing(
    tmp_path,
):
    csv_file = tmp_path / "loans.csv"
    csv_file.write_text(
        "LoanID,AssetID,BorrowerID,Purpose\n"
        "L-0001,A01,B01,Course\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Missing required loan columns"):
        load_cases(csv_file)


def test_load_master_data_reads_both_files(tmp_path):
    assets_file = tmp_path / "assets.csv"
    borrowers_file = tmp_path / "borrowers.csv"

    assets_file.write_text(
        "AssetID,AssetName,Category,ReplacementValueHUF\n"
        "A01,Camera,Camera,320000\n",
        encoding="utf-8",
    )

    borrowers_file.write_text(
        "BorrowerID,BorrowerAlias,Faculty,BorrowerType,MaxOpenLoans\n"
        "B01,Anna K.,Informatics,Student,2\n",
        encoding="utf-8",
    )

    assets, borrowers = load_master_data(
        assets_file,
        borrowers_file,
    )

    assert len(assets) == 1
    assert len(borrowers) == 1
    assert assets.iloc[0]["AssetID"] == "A01"
    assert borrowers.iloc[0]["BorrowerID"] == "B01"


def test_load_master_data_rejects_missing_asset_columns(tmp_path):
    assets_file = tmp_path / "assets.csv"
    borrowers_file = tmp_path / "borrowers.csv"

    assets_file.write_text(
        "AssetID,AssetName\nA01,Camera\n",
        encoding="utf-8",
    )

    borrowers_file.write_text(
        "BorrowerID,BorrowerAlias,Faculty,BorrowerType,MaxOpenLoans\n"
        "B01,Anna K.,Informatics,Student,2\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Missing required asset columns"):
        load_master_data(assets_file, borrowers_file)


def test_load_master_data_rejects_missing_borrower_columns(tmp_path):
    assets_file = tmp_path / "assets.csv"
    borrowers_file = tmp_path / "borrowers.csv"

    assets_file.write_text(
        "AssetID,AssetName,Category,ReplacementValueHUF\n"
        "A01,Camera,Camera,320000\n",
        encoding="utf-8",
    )

    borrowers_file.write_text(
        "BorrowerID,BorrowerAlias\n"
        "B01,Anna K.\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Missing required borrower columns",
    ):
        load_master_data(assets_file, borrowers_file)
