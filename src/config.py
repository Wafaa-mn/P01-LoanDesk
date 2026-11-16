
from __future__ import annotations

from datetime import date
from pathlib import Path


# Project directories
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"


# Input files
LOANS_FILE = DATA_DIR / "loans_team.csv"
ASSETS_FILE = DATA_DIR / "assets.csv"
BORROWERS_FILE = DATA_DIR / "borrowers.csv"
DEV_SET_FILE = DATA_DIR / "llm_dev_set.csv"


# Fixed project reference date
AS_OF_DATE = date(2026, 10, 30)


# Required columns in the loan input file
REQUIRED_LOAN_COLUMNS = {
    "LoanID",
    "AssetID",
    "BorrowerID",
    "Purpose",
    "LoanDate",
    "DueDate",
    "ReturnedDate",
    "DeskNote",
}


# Allowed loan purposes
ALLOWED_PURPOSES = {
    "Course",
    "Thesis",
    "Event",
    "Research",
}


# Required validation order
VALIDATION_ORDER = [
    "MISSING_ID",
    "DUPLICATE_ID",
    "UNKNOWN_REFERENCE",
    "INVALID_DATE",
    "INVALID_VALUE",
]
