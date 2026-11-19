
from __future__ import annotations

import pandas as pd


CASE_COLUMNS = [
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

RULE_ORDER = {
    "R1": 1,
    "R2": 2,
    "R3": 3,
    "R4": 4,
    "R5": 5,
}


def _clean(value: object) -> str:
    """Convert a value to a stripped string."""
    if pd.isna(value):
        return ""
    return str(value).strip()


def generate_cases(
    loans: pd.DataFrame,
    assets: pd.DataFrame,
    borrowers: pd.DataFrame,
    extractions: pd.DataFrame,
    flags: pd.DataFrame,
) -> pd.DataFrame:
    """Create one review case for each loan with at least one flag."""

    if flags.empty:
        return pd.DataFrame(columns=CASE_COLUMNS)

    asset_names = assets.set_index("AssetID")[
        "AssetName"
    ].to_dict()

    borrower_aliases = borrowers.set_index("BorrowerID")[
        "BorrowerAlias"
    ].to_dict()

    extraction_lookup = {
        _clean(row["RecordID"]): row
        for _, row in extractions.iterrows()
    }

    loan_lookup = {
        _clean(row["LoanID"]): row
        for _, row in loans.iterrows()
    }

    cases = []

    # Group flags so that each flagged loan creates only one case.
    for record_id, group in flags.groupby("RecordID"):

        loan = loan_lookup[record_id]

        # Sort reason codes in the required R1-R5 order.
        ordered_flags = group.copy()
        ordered_flags["_order"] = (
            ordered_flags["RuleID"].map(RULE_ORDER)
        )
        ordered_flags = ordered_flags.sort_values("_order")

        reason_codes = ";".join(
            ordered_flags["ReasonCode"].astype(str)
        )

        # A case is High if at least one of its flags is High.
        severity = (
            "High"
            if (group["Severity"] == "High").any()
            else "Medium"
        )

        risk_score = group["RiskScore"].max()

        asset_id = _clean(loan["AssetID"])
        borrower_id = _clean(loan["BorrowerID"])

        extraction = extraction_lookup.get(record_id)

        item_condition = None
        if extraction is not None:
            status = _clean(
                extraction["ExtractionStatus"]
            ).lower()

            if status == "success":
                item_condition = _clean(
                    extraction["item_condition"]
                )

        cases.append(
            {
                "CaseID": record_id,
                "Severity": severity,
                "RiskScore": risk_score,
                "ReasonCodes": reason_codes,
                "Status": "New",
                "AssetName": asset_names[asset_id],
                "BorrowerAlias": borrower_aliases[borrower_id],
                "DueDate": _clean(loan["DueDate"]),
                "ReturnedDate": (
                    _clean(loan["ReturnedDate"]) or None
                ),
                "item_condition": item_condition,
            }
        )

    result = pd.DataFrame(cases, columns=CASE_COLUMNS)

    result = result.sort_values(
        ["RiskScore", "CaseID"],
        ascending=[False, True],
    ).reset_index(drop=True)

    return result
