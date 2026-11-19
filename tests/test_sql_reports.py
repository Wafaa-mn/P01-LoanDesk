
import sqlite3

import pandas as pd
import pytest
from pathlib import Path

from src.sql_reports import (
    load_sql_queries,
    run_sql_reports,
)


def test_load_sql_queries(tmp_path):
    sql_path = tmp_path / "queries.sql"
    sql_path.write_text(
        """
-- Q1
SELECT 1 AS result;

-- Q2
SELECT 2 AS result;
""",
        encoding="utf-8",
    )

    queries = load_sql_queries(sql_path)

    assert set(queries) == {"Q1", "Q2"}
    assert "SELECT 1 AS result" in queries["Q1"]
    assert "SELECT 2 AS result" in queries["Q2"]


def test_run_sql_reports_exports_csv(tmp_path):
    database_path = tmp_path / "test.db"
    sql_path = tmp_path / "queries.sql"
    output_dir = tmp_path / "output"

    connection = sqlite3.connect(database_path)
    connection.execute("CREATE TABLE numbers (value INTEGER)")
    connection.executemany(
        "INSERT INTO numbers VALUES (?)",
        [(1,), (2,), (3,)],
    )
    connection.commit()
    connection.close()

    sql_path.write_text(
        """
-- Q1
SELECT value FROM numbers ORDER BY value;
""",
        encoding="utf-8",
    )

    results = run_sql_reports(
        database_path,
        sql_path,
        output_dir,
    )

    assert results["Q1"]["value"].tolist() == [1, 2, 3]
    assert (output_dir / "Q1.csv").exists()

    exported = pd.read_csv(output_dir / "Q1.csv")
    assert exported["value"].tolist() == [1, 2, 3]


def test_run_selected_queries(tmp_path):
    database_path = tmp_path / "test.db"
    sql_path = tmp_path / "queries.sql"

    connection = sqlite3.connect(database_path)
    connection.execute("CREATE TABLE numbers (value INTEGER)")
    connection.execute("INSERT INTO numbers VALUES (10)")
    connection.commit()
    connection.close()

    sql_path.write_text(
        """
-- Q1
SELECT value FROM numbers;

-- Q2
SELECT value + 1 AS value FROM numbers;
""",
        encoding="utf-8",
    )

    results = run_sql_reports(
        database_path,
        sql_path,
        tmp_path / "output",
        selected_queries=["Q2"],
    )

    assert list(results) == ["Q2"]
    assert results["Q2"].iloc[0]["value"] == 11
    assert not (tmp_path / "output" / "Q1.csv").exists()
    assert (tmp_path / "output" / "Q2.csv").exists()


def test_unknown_query_raises_error(tmp_path):
    database_path = tmp_path / "test.db"
    sql_path = tmp_path / "queries.sql"

    connection = sqlite3.connect(database_path)
    connection.close()

    sql_path.write_text(
        "-- Q1\nSELECT 1;",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unknown SQL query"):
        run_sql_reports(
            database_path,
            sql_path,
            tmp_path / "output",
            selected_queries=["Q9"],
        )


def test_q3_cases_by_asset_category():
    project_root = Path(__file__).resolve().parents[1]
    sql_path = project_root / "sql" / "queries.sql"
    query = load_sql_queries(sql_path)["Q3"]

    connection = sqlite3.connect(":memory:")

    connection.executescript(
        """
        CREATE TABLE assets (
            AssetID TEXT PRIMARY KEY,
            Category TEXT
        );

        CREATE TABLE loans (
            LoanID TEXT PRIMARY KEY,
            AssetID TEXT
        );

        CREATE TABLE cases (
            CaseID TEXT PRIMARY KEY,
            Severity TEXT
        );

        INSERT INTO assets VALUES
            ('A1', 'Camera'),
            ('A2', 'Laptop'),
            ('A3', 'Camera'),
            ('A4', 'Projector');

        INSERT INTO loans VALUES
            ('L1', 'A1'),
            ('L2', 'A2'),
            ('L3', 'A3'),
            ('L4', 'A4');

        INSERT INTO cases VALUES
            ('L1', 'High'),
            ('L2', 'Medium'),
            ('L3', 'High');
        """
    )

    results = pd.read_sql_query(query, connection)
    connection.close()

    assert results.to_dict("records") == [
        {
            "Category": "Camera",
            "LoanCount": 2,
            "CaseCount": 2,
            "HighCaseCount": 2,
        },
        {
            "Category": "Laptop",
            "LoanCount": 1,
            "CaseCount": 1,
            "HighCaseCount": 0,
        },
        {
            "Category": "Projector",
            "LoanCount": 1,
            "CaseCount": 0,
            "HighCaseCount": 0,
        },
    ]


def test_q4_borrowers_over_open_loan_limit():
    project_root = Path(__file__).resolve().parents[1]
    sql_path = project_root / "sql" / "queries.sql"
    query = load_sql_queries(sql_path)["Q4"]

    connection = sqlite3.connect(":memory:")

    connection.executescript(
        """
        CREATE TABLE borrowers (
            BorrowerID TEXT PRIMARY KEY,
            BorrowerAlias TEXT,
            BorrowerType TEXT,
            MaxOpenLoans INTEGER
        );

        CREATE TABLE loans (
            LoanID TEXT PRIMARY KEY,
            BorrowerID TEXT,
            ReturnedDate TEXT
        );

        INSERT INTO borrowers VALUES
            ('B1', 'Alice', 'Student', 2),
            ('B2', 'Bob', 'Staff', 2),
            ('B3', 'Charlie', 'Student', 1);

        INSERT INTO loans VALUES
            ('L1', 'B1', NULL),
            ('L2', 'B1', NULL),
            ('L3', 'B1', NULL),
            ('L4', 'B2', NULL),
            ('L5', 'B2', NULL),
            ('L6', 'B3', NULL),
            ('L7', 'B3', '2026-10-20');
        """
    )

    results = pd.read_sql_query(query, connection)
    connection.close()

    assert results.to_dict("records") == [
        {
            "BorrowerAlias": "Alice",
            "BorrowerType": "Student",
            "OpenLoans": 3,
            "MaxOpenLoans": 2,
        },
    ]
