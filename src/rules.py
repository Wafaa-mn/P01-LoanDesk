from __future__ import annotations

import pandas as pd

from src.config import AS_OF_DATE


FLAG_COLUMNS = [
    "RecordID",
    "RuleID",
    "ReasonCode",
    "Severity",
    "RiskScore",
]


def _clean(value: object) -> str:
    """Convert a value to a stripped string."""
    if pd.isna(value):
        return ""
    return str(value).strip()


def _to_bool(value: object) -> bool:
    """Handle booleans returned by CSV, pandas, or SQLite."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value == 1
    return _clean(value).lower() in {"true", "1", "yes"}


def generate_flags(
    loans: pd.DataFrame,
    borrowers: pd.DataFrame,
    holidays: pd.DataFrame,
    extractions: pd.DataFrame,
    scope: str = "team",
) -> pd.DataFrame:
    """Apply LoanDesk review rules and return one row per flag."""
    if scope not in {"team", "solo"}:
        raise ValueError("scope must be either 'team' or 'solo'.")

    flags: list[dict] = []

    # Prepare lookup sets and dictionaries once.
    holiday_dates = set(holidays["HolidayDate"].astype(str))

    borrower_limits = borrowers.set_index("BorrowerID")[
        "MaxOpenLoans"
    ].astype(int).to_dict()

    extraction_lookup = {
        _clean(row["RecordID"]): row
        for _, row in extractions.iterrows()
    }

    # Count all currently open loans for each borrower.
    open_loans = loans[
        loans["ReturnedDate"].apply(_clean) == ""
    ]
    open_counts = open_loans.groupby("BorrowerID").size().to_dict()

    def add_flag(
        record_id: str,
        rule_id: str,
        reason_code: str,
        severity: str,
    ) -> None:
        flags.append(
            {
                "RecordID": record_id,
                "RuleID": rule_id,
                "ReasonCode": reason_code,
                "Severity": severity,
                "RiskScore": 0.9 if severity == "High" else 0.6,
            }
        )

    for _, loan in loans.iterrows():
        record_id = _clean(loan["LoanID"])
        borrower_id = _clean(loan["BorrowerID"])
        due_date = _clean(loan["DueDate"])
        returned_date = _clean(loan["ReturnedDate"])
        is_open = returned_date == ""

        # R1 — DUE_ON_HOLIDAY (Medium)
        if is_open and due_date in holiday_dates:
            add_flag(
                record_id, "R1", "DUE_ON_HOLIDAY", "Medium"
            )

        # Retrieve extraction only when it exists and succeeded.
        extraction = extraction_lookup.get(record_id)
        extraction_succeeded = (
            extraction is not None
            and _clean(extraction["ExtractionStatus"]).lower()
            == "success"
        )

        # R2 — DAMAGED_OR_INCOMPLETE (High)
        if extraction_succeeded:
            item_condition = _clean(
                extraction["item_condition"]
            ).lower()

            missing_accessories = extraction["missing_accessories"]

            if isinstance(missing_accessories, (list, tuple, set)):

                has_missing_accessories = len(missing_accessories) > 0
            else:
                
                missing_text = _clean(missing_accessories).lower()
                has_missing_accessories = missing_text not in {
                    "",
                    "[]",
                    "nan",
                    "none",
                }


            if (
                item_condition == "damaged"
                or has_missing_accessories
            ):
                add_flag(
                    record_id,
                    "R2",
                    "DAMAGED_OR_INCOMPLETE",
                    "High",
                )

        # R3 — LATE_OR_OVERDUE (High)
        is_late = False

        if is_open:
            is_late = due_date < AS_OF_DATE.isoformat()
        else:
            is_late = returned_date > due_date

        if is_late:
            add_flag(
                record_id, "R3", "LATE_OR_OVERDUE", "High"
            )

        if scope == "team":
            # R4 — TOO_MANY_OPEN_LOANS (Medium)
            borrower_limit = borrower_limits[borrower_id]
            borrower_open_count = open_counts.get(borrower_id, 0)

            if (
                is_open
                and borrower_open_count > borrower_limit
            ):
                add_flag(
                    record_id,
                    "R4",
                    "TOO_MANY_OPEN_LOANS",
                    "Medium",
                )

            # R5 — EXTENSION_ON_OVERDUE (Medium)
            if extraction_succeeded and is_open:
                extension_requested = _to_bool(
                    extraction["extension_requested"]
                )

                if (
                    extension_requested
                    and due_date < AS_OF_DATE.isoformat()
                ):
                    add_flag(
                        record_id,
                        "R5",
                        "EXTENSION_ON_OVERDUE",
                        "Medium",
                    )

    result = pd.DataFrame(flags, columns=FLAG_COLUMNS)

    if not result.empty:
        result = result.sort_values(
            ["RecordID", "RuleID"]
        ).reset_index(drop=True)

    return result