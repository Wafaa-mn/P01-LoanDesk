
import pandas as pd
import pytest

from src.rules import generate_flags


def make_loans(rows):
    return pd.DataFrame(
        rows,
        columns=[
            "LoanID",
            "AssetID",
            "BorrowerID",
            "DueDate",
            "ReturnedDate",
        ],
    )


def make_borrowers(rows=None):
    if rows is None:
        rows = [("B01", 2)]

    return pd.DataFrame(
        rows,
        columns=["BorrowerID", "MaxOpenLoans"],
    )


def make_holidays(dates=None):
    if dates is None:
        dates = []

    return pd.DataFrame({"HolidayDate": dates})


def make_extractions(rows=None):
    if rows is None:
        rows = []

    return pd.DataFrame(
        rows,
        columns=[
            "RecordID",
            "item_condition",
            "missing_accessories",
            "extension_requested",
            "ExtractionStatus",
        ],
    )


def get_rule_ids(flags):
    return list(flags["RuleID"])


def test_r1_flags_open_loan_due_on_public_holiday():
    loans = make_loans([
        ("L01", "A01", "B01", "2026-12-25", ""),
    ])

    flags = generate_flags(
        loans,
        make_borrowers(),
        make_holidays(["2026-12-25"]),
        make_extractions(),
        scope="solo",
    )

    assert get_rule_ids(flags) == ["R1"]
    assert flags.iloc[0]["ReasonCode"] == "DUE_ON_HOLIDAY"
    assert flags.iloc[0]["Severity"] == "Medium"
    assert flags.iloc[0]["RiskScore"] == 0.6


def test_r1_does_not_flag_returned_loan():
    loans = make_loans([
        ("L01", "A01", "B01", "2026-12-25", "2026-12-24"),
    ])

    flags = generate_flags(
        loans,
        make_borrowers(),
        make_holidays(["2026-12-25"]),
        make_extractions(),
        scope="solo",
    )

    assert flags.empty


def test_r2_flags_damaged_item():
    loans = make_loans([
        ("L01", "A01", "B01", "2026-11-05", ""),
    ])

    extractions = make_extractions([
        ("L01", "damaged", [], False, "success"),
    ])

    flags = generate_flags(
        loans,
        make_borrowers(),
        make_holidays(),
        extractions,
        scope="solo",
    )

    assert get_rule_ids(flags) == ["R2"]
    assert flags.iloc[0]["ReasonCode"] == "DAMAGED_OR_INCOMPLETE"
    assert flags.iloc[0]["Severity"] == "High"
    assert flags.iloc[0]["RiskScore"] == 0.9


def test_r2_flags_missing_accessories_even_if_condition_is_good():
    loans = make_loans([
        ("L01", "A01", "B01", "2026-11-05", ""),
    ])

    extractions = make_extractions([
        ("L01", "good", ["power cable"], False, "success"),
    ])

    flags = generate_flags(
        loans,
        make_borrowers(),
        make_holidays(),
        extractions,
        scope="solo",
    )

    assert get_rule_ids(flags) == ["R2"]


def test_failed_extraction_does_not_trigger_r2_or_r5():
    loans = make_loans([
        ("L01", "A01", "B01", "2026-10-20", ""),
    ])

    extractions = make_extractions([
        ("L01", "damaged", ["power cable"], True, "failed"),
    ])

    flags = generate_flags(
        loans,
        make_borrowers(),
        make_holidays(),
        extractions,
        scope="team",
    )

    assert "R2" not in get_rule_ids(flags)
    assert "R5" not in get_rule_ids(flags)


def test_r3_does_not_flag_due_date_equal_to_as_of_date():
    loans = make_loans([
        ("L01", "A01", "B01", "2026-10-30", ""),
    ])

    flags = generate_flags(
        loans,
        make_borrowers(),
        make_holidays(),
        make_extractions(),
        scope="solo",
    )

    assert "R3" not in get_rule_ids(flags)


def test_r3_does_not_flag_returned_on_due_date():
    loans = make_loans([
        ("L01", "A01", "B01", "2026-10-20", "2026-10-20"),
    ])

    flags = generate_flags(
        loans,
        make_borrowers(),
        make_holidays(),
        make_extractions(),
        scope="solo",
    )

    assert "R3" not in get_rule_ids(flags)


def test_r3_flags_loan_returned_after_due_date():
    loans = make_loans([
        ("L01", "A01", "B01", "2026-10-20", "2026-10-21"),
    ])

    flags = generate_flags(
        loans,
        make_borrowers(),
        make_holidays(),
        make_extractions(),
        scope="solo",
    )

    assert get_rule_ids(flags) == ["R3"]


def test_r4_flags_every_open_loan_when_limit_is_exceeded():
    loans = make_loans([
        ("L01", "A01", "B01", "2026-11-05", ""),
        ("L02", "A02", "B01", "2026-11-06", ""),
        ("L03", "A03", "B01", "2026-11-07", ""),
    ])

    flags = generate_flags(
        loans,
        make_borrowers([("B01", 2)]),
        make_holidays(),
        make_extractions(),
        scope="team",
    )

    r4_flags = flags[flags["RuleID"] == "R4"]

    assert set(r4_flags["RecordID"]) == {"L01", "L02", "L03"}
    assert len(r4_flags) == 3
    assert set(r4_flags["Severity"]) == {"Medium"}


def test_r4_does_not_flag_borrower_at_exact_limit():
    loans = make_loans([
        ("L01", "A01", "B01", "2026-11-05", ""),
        ("L02", "A02", "B01", "2026-11-06", ""),
    ])

    flags = generate_flags(
        loans,
        make_borrowers([("B01", 2)]),
        make_holidays(),
        make_extractions(),
        scope="team",
    )

    assert "R4" not in get_rule_ids(flags)


def test_r5_flags_overdue_open_loan_with_extension_request():
    loans = make_loans([
        ("L01", "A01", "B01", "2026-10-20", ""),
    ])

    extractions = make_extractions([
        ("L01", "not_inspected", [], True, "success"),
    ])

    flags = generate_flags(
        loans,
        make_borrowers(),
        make_holidays(),
        extractions,
        scope="team",
    )

    assert get_rule_ids(flags) == ["R3", "R5"]
    r5_flag = flags[flags["RuleID"] == "R5"].iloc[0]
    assert r5_flag["ReasonCode"] == "EXTENSION_ON_OVERDUE"
    assert r5_flag["Severity"] == "Medium"


def test_r5_does_not_flag_extension_when_due_date_is_today():
    loans = make_loans([
        ("L01", "A01", "B01", "2026-10-30", ""),
    ])

    extractions = make_extractions([
        ("L01", "not_inspected", [], True, "success"),
    ])

    flags = generate_flags(
        loans,
        make_borrowers(),
        make_holidays(),
        extractions,
        scope="team",
    )

    assert "R5" not in get_rule_ids(flags)


def test_solo_scope_does_not_apply_team_only_rules():
    loans = make_loans([
        ("L01", "A01", "B01", "2026-10-20", ""),
        ("L02", "A02", "B01", "2026-10-21", ""),
        ("L03", "A03", "B01", "2026-10-22", ""),
    ])

    extractions = make_extractions([
        ("L01", "not_inspected", [], True, "success"),
    ])

    flags = generate_flags(
        loans,
        make_borrowers([("B01", 2)]),
        make_holidays(),
        extractions,
        scope="solo",
    )

    assert "R4" not in get_rule_ids(flags)
    assert "R5" not in get_rule_ids(flags)


def test_flags_are_sorted_by_record_id_then_rule_id():
    loans = make_loans([
        ("L02", "A01", "B01", "2026-10-20", ""),
        ("L01", "A02", "B01", "2026-10-21", ""),
    ])

    extractions = make_extractions([
        ("L02", "damaged", [], False, "success"),
        ("L01", "damaged", [], False, "success"),
    ])

    flags = generate_flags(
        loans,
        make_borrowers(),
        make_holidays(),
        extractions,
        scope="solo",
    )

    assert list(zip(flags["RecordID"], flags["RuleID"])) == [
    ("L01", "R2"),
    ("L01", "R3"),
    ("L02", "R2"),
    ("L02", "R3"), ]
