
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd



def load_sql_queries(sql_path: Path) -> dict[str, str]:
    """Load SQL queries separated by -- Q1, -- Q2, etc."""
    content = sql_path.read_text(encoding="utf-8")
    queries = {}
    current_query = None
    current_lines = []

    for line in content.splitlines():
        stripped = line.strip()

        if stripped.startswith("-- Q") and stripped[4:].isdigit():
            if current_query is not None:
                queries[current_query] = "\n".join(
                    current_lines
                ).strip()

            current_query = stripped[3:]
            current_lines = []

        elif current_query is not None:
            current_lines.append(line)

    if current_query is not None:
        queries[current_query] = "\n".join(
            current_lines
        ).strip()

    return queries



def run_sql_reports(
    database_path: Path,
    sql_path: Path,
    output_dir: Path,
    selected_queries: list[str] | None = None,
) -> dict[str, pd.DataFrame]:
    """Execute selected SQL reports and export their results."""
    queries = load_sql_queries(sql_path)

    if selected_queries is None:
        selected_queries = list(queries)

    output_dir.mkdir(parents=True, exist_ok=True)
    results = {}

    connection = sqlite3.connect(database_path)

    try:
        for query_id in selected_queries:
            if query_id not in queries:
                raise ValueError(
                    f"Unknown SQL query: {query_id}"
                )

            query = queries[query_id]

            if not query:
                raise ValueError(
                    f"SQL query {query_id} is empty."
                )

            df = pd.read_sql_query(query, connection)

            df.to_csv(
                output_dir / f"{query_id}.csv",
                index=False,
            )

            results[query_id] = df
    finally:
        connection.close()

    return results
