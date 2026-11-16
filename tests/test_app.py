
from __future__ import annotations

import pandas as pd
import pytest

from src.app import run_pipeline, save_outputs


def test_save_outputs_creates_directory_and_files(tmp_path):
    output_dir = tmp_path / "results"

    accepted = pd.DataFrame(
        [{"LoanID": "L-0001", "Purpose": "Course"}]
    )

    rejected = pd.DataFrame(
        [{
            "SourceRow": 3,
            "RecordID": "L-0002",
            "ReasonCode": "INVALID_VALUE",
        }]
    )

    save_outputs(accepted, rejected, output_dir)

    assert output_dir.exists()
    assert (output_dir / "accepted_loans.csv").exists()
    assert (output_dir / "rejected.csv").exists()


def test_save_outputs_preserves_data_and_columns(tmp_path):
    accepted = pd.DataFrame(
        [{"LoanID": "L-0001", "Purpose": "Course"}]
    )

    rejected = pd.DataFrame(
        [{
            "SourceRow": 3,
            "RecordID": "L-0002",
            "ReasonCode": "INVALID_VALUE",
        }],
        columns=["SourceRow", "RecordID", "ReasonCode"],
    )

    save_outputs(accepted, rejected, tmp_path)

    saved_accepted = pd.read_csv(
        tmp_path / "accepted_loans.csv",
        dtype=str,
    )

    saved_rejected = pd.read_csv(
        tmp_path / "rejected.csv",
        dtype=str,
    )

    assert saved_accepted.iloc[0]["LoanID"] == "L-0001"
    assert saved_accepted.iloc[0]["Purpose"] == "Course"

    assert saved_rejected.columns.tolist() == [
        "SourceRow",
        "RecordID",
        "ReasonCode",
    ]

    assert saved_rejected.iloc[0]["ReasonCode"] == "INVALID_VALUE"


def test_run_pipeline_processes_and_saves_records(tmp_path, capsys):
    loans_file = tmp_path / "loans.csv"
    assets_file = tmp_path / "assets.csv"
    borrowers_file = tmp_path / "borrowers.csv"
    output_dir = tmp_path / "output"

    loans_file.write_text(
        "LoanID,AssetID,BorrowerID,Purpose,LoanDate,DueDate,ReturnedDate,DeskNote\n"
        "L-0001,A01,B01,Course,2026-10-01,2026-10-15,,Clean\n"
        "L-0002,A01,B01,coursex,2026-10-01,2026-10-15,,Working\n",
        encoding="utf-8",
    )

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

    run_pipeline(
        loans_file,
        assets_file,
        borrowers_file,
        output_dir,
    )

    accepted = pd.read_csv(output_dir / "accepted_loans.csv")
    rejected = pd.read_csv(output_dir / "rejected.csv")

    assert len(accepted) == 1
    assert len(rejected) == 1
    assert accepted.iloc[0]["LoanID"] == "L-0001"
    assert rejected.iloc[0]["RecordID"] == "L-0002"
    assert rejected.iloc[0]["ReasonCode"] == "INVALID_VALUE"

    captured = capsys.readouterr()

    assert "Input records:    2" in captured.out
    assert "Accepted records: 1" in captured.out
    assert "Rejected records: 1" in captured.out


def test_run_pipeline_rejects_missing_required_columns(tmp_path):
    loans_file = tmp_path / "loans.csv"
    assets_file = tmp_path / "assets.csv"
    borrowers_file = tmp_path / "borrowers.csv"
    output_dir = tmp_path / "output"

    loans_file.write_text(
        "LoanID,AssetID,Purpose\n"
        "L-0001,A01,Course\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Missing required loan columns",
    ):
        run_pipeline(
            loans_file,
            assets_file,
            borrowers_file,
            output_dir,
        )

    assert not output_dir.exists()


def test_save_outputs_handles_empty_results(tmp_path):
    accepted = pd.DataFrame(
        columns=["LoanID", "AssetID", "Purpose"]
    )

    rejected = pd.DataFrame(
        columns=["SourceRow", "RecordID", "ReasonCode"]
    )

    save_outputs(accepted, rejected, tmp_path)

    saved_accepted = pd.read_csv(
        tmp_path / "accepted_loans.csv"
    )

    saved_rejected = pd.read_csv(
        tmp_path / "rejected.csv"
    )

    assert saved_accepted.empty
    assert saved_rejected.empty
    assert saved_rejected.columns.tolist() == [
        "SourceRow",
        "RecordID",
        "ReasonCode",
    ]
