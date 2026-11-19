
import pandas as pd

from src.database import (
    connect_database,
    create_database,
    insert_master_data,
    insert_accepted_loans,
    insert_flags,
    insert_cases,
)


def test_insert_flags_and_cases(tmp_path):
    database_path = tmp_path / "test.db"
    create_database(database_path)

    assets = pd.DataFrame([
        {
            "AssetID": "A01",
            "AssetName": "Camera",
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

    loans = pd.DataFrame([
        {
            "LoanID": "L01",
            "AssetID": "A01",
            "BorrowerID": "B01",
            "Purpose": "Thesis",
            "LoanDate": "2026-10-01",
            "DueDate": "2026-10-20",
            "ReturnedDate": "",
            "DeskNote": "Damaged camera.",
        }
    ])

    flags = pd.DataFrame([
        {
            "RecordID": "L01",
            "RuleID": "R2",
            "ReasonCode": "DAMAGED_OR_INCOMPLETE",
            "Severity": "High",
            "RiskScore": 0.9,
        },
        {
            "RecordID": "L01",
            "RuleID": "R3",
            "ReasonCode": "LATE_OR_OVERDUE",
            "Severity": "High",
            "RiskScore": 0.9,
        },
    ])

    cases = pd.DataFrame([
        {
            "CaseID": "L01",
            "Severity": "High",
            "RiskScore": 0.9,
            "ReasonCodes": (
                "DAMAGED_OR_INCOMPLETE;LATE_OR_OVERDUE"
            ),
            "Status": "New",
            "AssetName": "Camera",
            "BorrowerAlias": "Anna K.",
            "DueDate": "2026-10-20",
            "ReturnedDate": None,
            "item_condition": "damaged",
        }
    ])

    connection = connect_database(database_path)

    try:
        insert_master_data(connection, assets, borrowers)
        insert_accepted_loans(connection, loans)
        insert_flags(connection, flags)
        insert_cases(connection, cases)
        connection.commit()

        stored_flags = connection.execute(
            """
            SELECT RecordID, RuleID, ReasonCode, Severity, RiskScore
            FROM flags
            ORDER BY RecordID, RuleID
            """
        ).fetchall()

        stored_cases = connection.execute(
            """
            SELECT CaseID, Severity, RiskScore, ReasonCodes, Status
            FROM cases
            """
        ).fetchall()

        assert len(stored_flags) == 2
        assert stored_flags[0] == (
            "L01",
            "R2",
            "DAMAGED_OR_INCOMPLETE",
            "High",
            0.9,
        )

        assert stored_cases == [
            (
                "L01",
                "High",
                0.9,
                "DAMAGED_OR_INCOMPLETE;LATE_OR_OVERDUE",
                "New",
            )
        ]

    finally:
        connection.close()


def test_empty_flags_and_cases_are_allowed(tmp_path):
    database_path = tmp_path / "empty.db"
    create_database(database_path)

    connection = connect_database(database_path)

    try:
        insert_flags(
            connection,
            pd.DataFrame(
                columns=[
                    "RecordID", "RuleID", "ReasonCode",
                    "Severity", "RiskScore",
                ]
            ),
        )

        insert_cases(
            connection,
            pd.DataFrame(
                columns=[
                    "CaseID", "Severity", "RiskScore",
                    "ReasonCodes", "Status", "AssetName",
                    "BorrowerAlias", "DueDate", "ReturnedDate",
                    "item_condition",
                ]
            ),
        )

        connection.commit()

        assert connection.execute(
            "SELECT COUNT(*) FROM flags"
        ).fetchone()[0] == 0

        assert connection.execute(
            "SELECT COUNT(*) FROM cases"
        ).fetchone()[0] == 0

    finally:
        connection.close()
