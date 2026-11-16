# P01 — LoanDesk

## Project Overview

LoanDesk is a data-driven application for reviewing campus equipment loans. It processes loan records, validates them against master data, retrieves public holiday information, extracts information from desk notes, and applies review rules to identify cases that may require attention.

The project is developed as part of the Data-driven Application Development course at the University of Debrecen.

## Project Objectives

- Validate incoming loan records and quarantine invalid records.
- Enrich loan data with Hungarian public holiday information.
- Extract relevant information from free-text desk notes.
- Apply rule-based checks to identify potentially problematic loans.
- Store processed data and review cases in SQLite.
- Provide reports and a review interface for users.

## Repository Structure

```text
P01-LoanDesk/
├── data/                  # Input CSV files and master data
├── src/                   # Python application modules
├── tests/                 # Automated tests
├── sql/                   # SQL reporting queries
├── output/                # Generated results and reports
├── powerplatform/         # Power Platform components
├── main.py                # Main pipeline entry point
├── requirements.txt       # Python dependencies
├── README.md
├── AI_USAGE_LOG.md
├── CONTRIBUTIONS.md
└── .gitignore
```

## Input Data

The project uses the following input files:

- `loans_team.csv` — team loan records, including intentionally invalid records.
- `loans_solo.csv` — individual-scope loan records.
- `assets.csv` — equipment master data.
- `borrowers.csv` — borrower master data.
- `llm_dev_set.csv` — development dataset for evaluating text extraction.

## Processing Pipeline

The planned processing pipeline consists of:

1. Load input CSV files.
2. Validate loan records and separate rejected records.
3. Retrieve Hungarian public holiday data.
4. Extract structured information from desk notes.
5. Apply review rules.
6. Store processed data in SQLite.
7. Generate SQL reports and review outputs.

## Data Validation

Loan records are checked in the required order:

1. `MISSING_ID`
2. `DUPLICATE_ID`
3. `UNKNOWN_REFERENCE`
4. `INVALID_DATE`
5. `INVALID_VALUE`

Each rejected record receives one reason code: the first failed validation check. Structural problems, such as missing required CSV columns, stop processing with an error.

## Testing

The project uses pytest for automated testing. Tests cover data validation, rejection reasons, validation priority, and important boundary conditions.

## Installation and Execution

Installation instructions and the complete pipeline command will be added as the application is implemented.

## Reports and Outputs

Generated files will be stored in the `output/` directory. This section will be updated as the pipeline and reports are implemented.

## Team Contributions

See [`CONTRIBUTIONS.md`](CONTRIBUTIONS.md).

## AI Usage

See [`AI_USAGE_LOG.md`](AI_USAGE_LOG.md) for documentation of AI-assisted work and verification.