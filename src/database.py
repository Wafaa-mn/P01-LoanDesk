
from __future__ import annotations

import sqlite3
from pathlib import Path
import pandas as pd

SCHEMA = """
CREATE TABLE assets (
    AssetID TEXT PRIMARY KEY,
    AssetName TEXT NOT NULL,
    Category TEXT NOT NULL,
    ReplacementValueHUF INTEGER NOT NULL
);

CREATE TABLE borrowers (
    BorrowerID TEXT PRIMARY KEY,
    BorrowerAlias TEXT NOT NULL,
    Faculty TEXT NOT NULL,
    BorrowerType TEXT NOT NULL,
    MaxOpenLoans INTEGER NOT NULL
);

CREATE TABLE loans (
    LoanID TEXT PRIMARY KEY,
    AssetID TEXT NOT NULL,
    BorrowerID TEXT NOT NULL,
    Purpose TEXT NOT NULL,
    LoanDate TEXT NOT NULL,
    DueDate TEXT NOT NULL,
    ReturnedDate TEXT,
    DeskNote TEXT NOT NULL,
    FOREIGN KEY (AssetID) REFERENCES assets(AssetID),
    FOREIGN KEY (BorrowerID) REFERENCES borrowers(BorrowerID)
);

CREATE TABLE api_holidays (
    HolidayDate TEXT PRIMARY KEY,
    LocalName TEXT NOT NULL,
    Name TEXT NOT NULL
);

CREATE TABLE extractions (
    RecordID TEXT PRIMARY KEY,
    item_condition TEXT,
    missing_accessories TEXT,
    extension_requested TEXT,
    ExtractionStatus TEXT NOT NULL,
    FOREIGN KEY (RecordID) REFERENCES loans(LoanID)
);

CREATE TABLE flags (
    RecordID TEXT NOT NULL,
    RuleID TEXT NOT NULL,
    ReasonCode TEXT NOT NULL,
    Severity TEXT NOT NULL,
    RiskScore REAL NOT NULL,
    PRIMARY KEY (RecordID, RuleID),
    FOREIGN KEY (RecordID) REFERENCES loans(LoanID)
);

CREATE TABLE cases (
    CaseID TEXT PRIMARY KEY,
    Severity TEXT NOT NULL,
    RiskScore REAL NOT NULL,
    ReasonCodes TEXT NOT NULL,
    Status TEXT NOT NULL,
    AssetName TEXT NOT NULL,
    BorrowerAlias TEXT NOT NULL,
    DueDate TEXT NOT NULL,
    ReturnedDate TEXT,
    item_condition TEXT,
    FOREIGN KEY (CaseID) REFERENCES loans(LoanID)
);

CREATE TABLE reviews (
    CaseID TEXT PRIMARY KEY,
    ReviewDecision TEXT NOT NULL,
    ReviewerNotes TEXT NOT NULL,
    FOREIGN KEY (CaseID) REFERENCES cases(CaseID)
);

CREATE TABLE review_codes (
    CaseID TEXT NOT NULL,
    ReasonCode TEXT NOT NULL,
    PRIMARY KEY (CaseID, ReasonCode),
    FOREIGN KEY (CaseID) REFERENCES reviews(CaseID)
);
"""



def connect_database(database_path: Path) -> sqlite3.Connection:
    """Open a SQLite connection with foreign-key enforcement enabled."""
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def create_database(database_path: Path) -> None:
    """Create a fresh SQLite database with the project schema."""
    database_path.parent.mkdir(parents=True, exist_ok=True)

    if database_path.exists():
        database_path.unlink()

    connection = connect_database(database_path)

    try:
        connection.executescript(SCHEMA)
        connection.commit()
    finally:
        connection.close()


def insert_master_data(
    connection: sqlite3.Connection,
    assets: pd.DataFrame,
    borrowers: pd.DataFrame,
) -> None:
    """Insert asset and borrower master data."""
    asset_rows = [
        (
            row["AssetID"],
            row["AssetName"],
            row["Category"],
            int(row["ReplacementValueHUF"]),
        )
        for row in assets.to_dict("records")
    ]

    borrower_rows = [
        (
            row["BorrowerID"],
            row["BorrowerAlias"],
            row["Faculty"],
            row["BorrowerType"],
            int(row["MaxOpenLoans"]),
        )
        for row in borrowers.to_dict("records")
    ]

    connection.executemany(
        """
        INSERT INTO assets (
            AssetID, AssetName, Category, ReplacementValueHUF
        )
        VALUES (?, ?, ?, ?)
        """,
        asset_rows,
    )

    connection.executemany(
        """
        INSERT INTO borrowers (
            BorrowerID, BorrowerAlias, Faculty, BorrowerType,
            MaxOpenLoans
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        borrower_rows,
    )


def insert_accepted_loans(
    connection: sqlite3.Connection,
    loans: pd.DataFrame,
) -> None:
    """Insert validated loan records."""
    loan_rows = []

    for row in loans.to_dict("records"):
        returned_date = row["ReturnedDate"]

        if returned_date == "":
            returned_date = None

        loan_rows.append(
            (
                row["LoanID"],
                row["AssetID"],
                row["BorrowerID"],
                row["Purpose"],
                row["LoanDate"],
                row["DueDate"],
                returned_date,
                row["DeskNote"],
            )
        )

    connection.executemany(
        """
        INSERT INTO loans (
            LoanID, AssetID, BorrowerID, Purpose,
            LoanDate, DueDate, ReturnedDate, DeskNote
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        loan_rows,
    )


def insert_holidays(
    connection: sqlite3.Connection,
    holidays: pd.DataFrame,
) -> None:
    """Insert nationwide Hungarian public holidays."""
    holiday_rows = [
        (
            row["HolidayDate"],
            row["LocalName"],
            row["Name"],
        )
        for row in holidays.to_dict("records")
    ]

    connection.executemany(
        """
        INSERT INTO api_holidays (
            HolidayDate, LocalName, Name
        )
        VALUES (?, ?, ?)
        """,
        holiday_rows,
    )



def insert_flags(
    connection: sqlite3.Connection,
    flags: pd.DataFrame,
) -> None:
    """Insert generated rule flags into SQLite."""
    if flags.empty:
        return

    rows = [
        (
            str(row["RecordID"]),
            str(row["RuleID"]),
            str(row["ReasonCode"]),
            str(row["Severity"]),
            float(row["RiskScore"]),
        )
        for _, row in flags.iterrows()
    ]

    connection.executemany(
        """
        INSERT INTO flags (
            RecordID,
            RuleID,
            ReasonCode,
            Severity,
            RiskScore
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )


def insert_cases(
    connection: sqlite3.Connection,
    cases: pd.DataFrame,
) -> None:
    """Insert generated review cases into SQLite."""
    if cases.empty:
        return

    rows = [
        (
            str(row["CaseID"]),
            str(row["Severity"]),
            float(row["RiskScore"]),
            str(row["ReasonCodes"]),
            str(row["Status"]),
            str(row["AssetName"]),
            str(row["BorrowerAlias"]),
            str(row["DueDate"]),
            row["ReturnedDate"] or None,
            row["item_condition"] or None,
        )
        for _, row in cases.iterrows()
    ]

    connection.executemany(
        """
        INSERT INTO cases (
            CaseID,
            Severity,
            RiskScore,
            ReasonCodes,
            Status,
            AssetName,
            BorrowerAlias,
            DueDate,
            ReturnedDate,
            item_condition
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    