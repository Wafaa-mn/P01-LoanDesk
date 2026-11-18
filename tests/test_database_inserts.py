
import sqlite3

import pandas as pd
import pytest

from src.database import (
    create_database,
    connect_database,
    insert_master_data,
    insert_accepted_loans,
    insert_holidays,
)


@pytest.fixture
def database(tmp_path):
    database_path = tmp_path / "loandesk.db"
    create_database(database_path)

    connection = connect_database(database_path)

    yield connection

    connection.close()


def test_insert_master_data(database):
    assets = pd.DataFrame([
        {
            "AssetID": "A01",
            "AssetName": "Canon Camera",
            "Category": "Camera",
            "ReplacementValueHUF": "320000",
        }
    ])

    borrowers = pd.DataFrame([
        {
            "BorrowerID": "B01",
            "BorrowerAlias": "Anna K.",
            "Faculty": "Informatics",
            "BorrowerType": "Student",
            "MaxOpenLoans": "2",
        }
    ])

    insert_master_data(database, assets, borrowers)
    database.commit()

    asset = database.execute(
        "SELECT * FROM assets WHERE AssetID = 'A01'"
    ).fetchone()

    borrower = database.execute(
        "SELECT * FROM borrowers WHERE BorrowerID = 'B01'"
    ).fetchone()

    assert asset[1] == "Canon Camera"
    assert asset[3] == 320000
    assert borrower[1] == "Anna K."
    assert borrower[4] == 2


def test_insert_accepted_loans(database):
    assets = pd.DataFrame([
        {
            "AssetID": "A01",
            "AssetName": "Canon Camera",
            "Category": "Camera",
            "ReplacementValueHUF": "320000",
        }
    ])

    borrowers = pd.DataFrame([
        {
            "BorrowerID": "B01",
            "BorrowerAlias": "Anna K.",
            "Faculty": "Informatics",
            "BorrowerType": "Student",
            "MaxOpenLoans": "2",
        }
    ])

    insert_master_data(database, assets, borrowers)

    loans = pd.DataFrame([
        {
            "LoanID": "L-0001",
            "AssetID": "A01",
            "BorrowerID": "B01",
            "Purpose": "Course",
            "LoanDate": "2026-10-01",
            "DueDate": "2026-10-30",
            "ReturnedDate": "",
            "DeskNote": "Camera not returned yet.",
        }
    ])

    insert_accepted_loans(database, loans)
    database.commit()

    loan = database.execute(
        "SELECT * FROM loans WHERE LoanID = 'L-0001'"
    ).fetchone()

    assert loan[0] == "L-0001"
    assert loan[6] is None
    assert loan[7] == "Camera not returned yet."


def test_insert_holidays(database):
    holidays = pd.DataFrame([
        {
            "HolidayDate": "2026-01-01",
            "LocalName": "Újév",
            "Name": "New Year's Day",
        }
    ])

    insert_holidays(database, holidays)
    database.commit()

    holiday = database.execute(
        """
        SELECT * FROM api_holidays
        WHERE HolidayDate = '2026-01-01'
        """
    ).fetchone()

    assert holiday == (
        "2026-01-01",
        "Újév",
        "New Year's Day",
    )


def test_foreign_keys_are_enforced(database):
    result = database.execute(
        "PRAGMA foreign_keys"
    ).fetchone()[0]

    assert result == 1


def test_loan_with_unknown_asset_is_rejected(database):
    loans = pd.DataFrame([
        {
            "LoanID": "L-0001",
            "AssetID": "UNKNOWN",
            "BorrowerID": "B01",
            "Purpose": "Course",
            "LoanDate": "2026-10-01",
            "DueDate": "2026-10-30",
            "ReturnedDate": "",
            "DeskNote": "Test loan.",
        }
    ])

    with pytest.raises(sqlite3.IntegrityError):
        insert_accepted_loans(database, loans)
