
import pandas as pd

from src.cases import generate_cases


def test_multiple_flags_create_one_case_with_combined_reason_codes():
    loans = pd.DataFrame([
        {
            "LoanID": "L01",
            "AssetID": "A01",
            "BorrowerID": "B01",
            "DueDate": "2026-10-20",
            "ReturnedDate": "",
        }
    ])

    assets = pd.DataFrame([
        {"AssetID": "A01", "AssetName": "Camera"}
    ])

    borrowers = pd.DataFrame([
        {"BorrowerID": "B01", "BorrowerAlias": "Anna K."}
    ])

    extractions = pd.DataFrame([
        {
            "RecordID": "L01",
            "item_condition": "damaged",
            "ExtractionStatus": "success",
        }
    ])

    flags = pd.DataFrame([
        {
            "RecordID": "L01",
            "RuleID": "R3",
            "ReasonCode": "LATE_OR_OVERDUE",
            "Severity": "High",
            "RiskScore": 0.9,
        },
        {
            "RecordID": "L01",
            "RuleID": "R1",
            "ReasonCode": "DUE_ON_HOLIDAY",
            "Severity": "Medium",
            "RiskScore": 0.6,
        },
    ])

    cases = generate_cases(
        loans, assets, borrowers, extractions, flags
    )

    assert len(cases) == 1
    assert cases.iloc[0]["CaseID"] == "L01"
    assert cases.iloc[0]["Severity"] == "High"
    assert cases.iloc[0]["RiskScore"] == 0.9
    assert cases.iloc[0]["ReasonCodes"] == (
        "DUE_ON_HOLIDAY;LATE_OR_OVERDUE"
    )
    assert cases.iloc[0]["Status"] == "New"
    assert cases.iloc[0]["AssetName"] == "Camera"
    assert cases.iloc[0]["BorrowerAlias"] == "Anna K."
    assert cases.iloc[0]["item_condition"] == "damaged"


def test_case_is_medium_when_all_flags_are_medium():
    loans = pd.DataFrame([
        {
            "LoanID": "L01",
            "AssetID": "A01",
            "BorrowerID": "B01",
            "DueDate": "2026-11-05",
            "ReturnedDate": "",
        }
    ])

    assets = pd.DataFrame([
        {"AssetID": "A01", "AssetName": "Camera"}
    ])

    borrowers = pd.DataFrame([
        {"BorrowerID": "B01", "BorrowerAlias": "Anna K."}
    ])

    extractions = pd.DataFrame(columns=[
        "RecordID", "item_condition", "ExtractionStatus"
    ])

    flags = pd.DataFrame([
        {
            "RecordID": "L01",
            "RuleID": "R1",
            "ReasonCode": "DUE_ON_HOLIDAY",
            "Severity": "Medium",
            "RiskScore": 0.6,
        }
    ])

    cases = generate_cases(
        loans, assets, borrowers, extractions, flags
    )

    assert cases.iloc[0]["Severity"] == "Medium"
    assert cases.iloc[0]["RiskScore"] == 0.6
    assert cases.iloc[0]["item_condition"] is None


def test_cases_are_sorted_by_risk_score_then_case_id():
    loans = pd.DataFrame([
        {
            "LoanID": "L02",
            "AssetID": "A01",
            "BorrowerID": "B01",
            "DueDate": "2026-11-05",
            "ReturnedDate": "",
        },
        {
            "LoanID": "L01",
            "AssetID": "A01",
            "BorrowerID": "B01",
            "DueDate": "2026-11-05",
            "ReturnedDate": "",
        },
        {
            "LoanID": "L03",
            "AssetID": "A01",
            "BorrowerID": "B01",
            "DueDate": "2026-11-05",
            "ReturnedDate": "",
        },
    ])

    assets = pd.DataFrame([
        {"AssetID": "A01", "AssetName": "Camera"}
    ])

    borrowers = pd.DataFrame([
        {"BorrowerID": "B01", "BorrowerAlias": "Anna K."}
    ])

    extractions = pd.DataFrame(columns=[
        "RecordID", "item_condition", "ExtractionStatus"
    ])

    flags = pd.DataFrame([
        {
            "RecordID": "L02",
            "RuleID": "R1",
            "ReasonCode": "DUE_ON_HOLIDAY",
            "Severity": "Medium",
            "RiskScore": 0.6,
        },
        {
            "RecordID": "L01",
            "RuleID": "R3",
            "ReasonCode": "LATE_OR_OVERDUE",
            "Severity": "High",
            "RiskScore": 0.9,
        },
        {
            "RecordID": "L03",
            "RuleID": "R1",
            "ReasonCode": "DUE_ON_HOLIDAY",
            "Severity": "Medium",
            "RiskScore": 0.6,
        },
    ])

    cases = generate_cases(
        loans, assets, borrowers, extractions, flags
    )

    assert list(cases["CaseID"]) == ["L01", "L02", "L03"]


def test_empty_flags_produce_empty_cases():
    loans = pd.DataFrame()
    assets = pd.DataFrame()
    borrowers = pd.DataFrame()
    extractions = pd.DataFrame()

    flags = pd.DataFrame(columns=[
        "RecordID", "RuleID", "ReasonCode", "Severity", "RiskScore"
    ])

    cases = generate_cases(
        loans, assets, borrowers, extractions, flags
    )

    assert cases.empty
    assert list(cases.columns) == [
        "CaseID",
        "Severity",
        "RiskScore",
        "ReasonCodes",
        "Status",
        "AssetName",
        "BorrowerAlias",
        "DueDate",
        "ReturnedDate",
        "item_condition",
    ]
