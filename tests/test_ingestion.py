import sqlite3
import pandas as pd
import pytest


from src import ingestion
from src.ingestion import run_ingestion


def create_test_files(tmp_path):
    assets_path = tmp_path / "assets.csv"
    borrowers_path = tmp_path / "borrowers.csv"
    loans_path = tmp_path / "loans.csv"

    pd.DataFrame([
        {
            "AssetID": "A01",
            "AssetName": "Canon Camera",
            "Category": "Camera",
            "ReplacementValueHUF": 320000,
        }
    ]).to_csv(assets_path, index=False)

    pd.DataFrame([
        {
            "BorrowerID": "B01",
            "BorrowerAlias": "Anna K.",
            "Faculty": "Informatics",
            "BorrowerType": "Student",
            "MaxOpenLoans": 2,
        }
    ]).to_csv(borrowers_path, index=False)

    pd.DataFrame([
        {
            "LoanID": "L-0001",
            "AssetID": "A01",
            "BorrowerID": "B01",
            "Purpose": "Course",
            "LoanDate": "2026-10-01",
            "DueDate": "2026-10-30",
            "ReturnedDate": "",
            "DeskNote": "Not returned yet.",
        },
        {
            "LoanID": "",
            "AssetID": "A01",
            "BorrowerID": "B01",
            "Purpose": "Course",
            "LoanDate": "2026-10-02",
            "DueDate": "2026-10-30",
            "ReturnedDate": "",
            "DeskNote": "Missing loan ID.",
        },
    ]).to_csv(loans_path, index=False)

    return loans_path, assets_path, borrowers_path


def test_run_ingestion_loads_and_stores_data(tmp_path, monkeypatch):
    loans_path, assets_path, borrowers_path = create_test_files(
        tmp_path
    )

    holidays = pd.DataFrame([
        {
            "HolidayDate": "2026-01-01",
            "LocalName": "Újév",
            "Name": "New Year's Day",
        }
    ])

    monkeypatch.setattr(
        ingestion,
        "get_national_holidays",
        lambda cache_path: holidays,
    )

    def fake_extract_dataframe(
        loans,
        client=None,
        cache_dir=None,
        output_file=None,
    ):
        extractions = pd.DataFrame([
            {
                "LoanID": loan_id,
                "item_condition": "damaged",
                "missing_accessories": "[]",
                "extension_requested": False,
                "extraction_status": "ok",
                "extraction_error": None,
            }
            for loan_id in loans["LoanID"]
        ])

        if output_file is not None:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            extractions.to_csv(output_file, index=False)

        return extractions


    monkeypatch.setattr(
        ingestion,
        "extract_dataframe",
        fake_extract_dataframe,
    )

    output_dir = tmp_path / "output"
    database_path = output_dir / "loandesk.db"
    cache_path = output_dir / "cache" / "holidays.json"

    result = run_ingestion(
        loans_path,
        assets_path,
        borrowers_path,
        output_dir,
        database_path,
        cache_path,
    )

    assert result["input_records"] == 2
    assert result["accepted_records"] == 1
    assert result["rejected_records"] == 1
    assert result["asset_records"] == 1
    assert result["borrower_records"] == 1
    assert result["holiday_records"] == 1

    assert result["extraction_records"] == 1
    assert result["flag_records"] == 1
    assert result["case_records"] == 1

    assert (output_dir / "extractions.csv").exists()
    assert (output_dir / "flags.csv").exists()
    assert (output_dir / "cases.csv").exists()

    flags = pd.read_csv(output_dir / "flags.csv")
    assert flags.iloc[0]["RuleID"] == "R2"
    assert flags.iloc[0]["ReasonCode"] == "DAMAGED_OR_INCOMPLETE"

    cases = pd.read_csv(output_dir / "cases.csv")
    assert cases.iloc[0]["item_condition"] == "damaged"

    assert database_path.exists()
    assert (output_dir / "accepted_loans.csv").exists()
    assert (output_dir / "rejected.csv").exists()

    connection = sqlite3.connect(database_path)

    try:
        assert connection.execute(
            "SELECT COUNT(*) FROM assets"
        ).fetchone()[0] == 1

        assert connection.execute(
            "SELECT COUNT(*) FROM borrowers"
        ).fetchone()[0] == 1

        assert connection.execute(
            "SELECT COUNT(*) FROM loans"
        ).fetchone()[0] == 1

        assert connection.execute(
            "SELECT COUNT(*) FROM api_holidays"
        ).fetchone()[0] == 1

        returned_date = connection.execute(
            "SELECT ReturnedDate FROM loans WHERE LoanID = 'L-0001'"
        ).fetchone()[0]

        assert returned_date is None
    finally:
        connection.close()

    rejected = pd.read_csv(
        output_dir / "rejected.csv",
        dtype=str,
        keep_default_na=False,
    )

    assert list(rejected.columns) == [
        "SourceRow",
        "RecordID",
        "ReasonCode",
    ]
    assert rejected.iloc[0]["ReasonCode"] == "MISSING_ID"


def test_api_failure_does_not_rebuild_database(tmp_path, monkeypatch):
    loans_path, assets_path, borrowers_path = create_test_files(
        tmp_path
    )

    output_dir = tmp_path / "output"
    database_path = output_dir / "loandesk.db"

    output_dir.mkdir()
    original_connection = sqlite3.connect(database_path)
    original_connection.execute(
        "CREATE TABLE keep_me (id INTEGER)"
    )
    original_connection.commit()
    original_connection.close()

    def fail_to_fetch(cache_path):
        raise RuntimeError("Holiday API unavailable.")

    monkeypatch.setattr(
        ingestion,
        "get_national_holidays",
        fail_to_fetch,
    )

    with pytest.raises(RuntimeError, match="Holiday API unavailable"):
        run_ingestion(
            loans_path,
            assets_path,
            borrowers_path,
            output_dir,
            database_path,
            output_dir / "cache" / "holidays.json",
        )

    connection = sqlite3.connect(database_path)

    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert "keep_me" in tables
    finally:
        connection.close()
