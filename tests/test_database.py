
import sqlite3

from src.database import create_database


def test_create_database_creates_file(tmp_path):
    database_path = tmp_path / "output" / "project.sqlite"

    create_database(database_path)

    assert database_path.exists()


def test_create_database_creates_all_tables(tmp_path):
    database_path = tmp_path / "project.sqlite"

    create_database(database_path)

    connection = sqlite3.connect(database_path)

    try:
        tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            )
        }

        expected_tables = {
            "assets",
            "borrowers",
            "loans",
            "api_holidays",
            "extractions",
            "flags",
            "cases",
            "reviews",
            "review_codes",
        }

        assert expected_tables.issubset(tables)

    finally:
        connection.close()


def test_create_database_enables_foreign_keys(tmp_path):
    database_path = tmp_path / "project.sqlite"

    create_database(database_path)

    connection = sqlite3.connect(database_path)

    try:
        connection.execute("PRAGMA foreign_keys = ON")

        result = connection.execute(
            "PRAGMA foreign_keys"
        ).fetchone()[0]

        assert result == 1

    finally:
        connection.close()


def test_create_database_rebuilds_existing_database(tmp_path):
    database_path = tmp_path / "project.sqlite"

    connection = sqlite3.connect(database_path)
    connection.execute(
        "CREATE TABLE old_table (id INTEGER)"
    )
    connection.close()

    create_database(database_path)

    connection = sqlite3.connect(database_path)

    try:
        tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            )
        }

        assert "old_table" not in tables
        assert "loans" in tables

    finally:
        connection.close()
