
from __future__ import annotations

import argparse
from pathlib import Path

from src.config import (
    ASSETS_FILE,
    BORROWERS_FILE,
    LOANS_FILE,
    OUTPUT_DIR,
)
from src.data_loader import load_cases, load_master_data
from src.validation import validate_input


def save_outputs(
    accepted,
    rejected,
    output_dir: Path,
) -> None:
    """Save accepted and rejected loan records."""
    output_dir.mkdir(parents=True, exist_ok=True)

    accepted_path = output_dir / "accepted_loans.csv"
    rejected_path = output_dir / "rejected.csv"

    accepted.to_csv(accepted_path, index=False)
    rejected.to_csv(rejected_path, index=False)


def run_pipeline(
    loans_path: Path,
    assets_path: Path,
    borrowers_path: Path,
    output_dir: Path,
) -> None:
    """Run the initial loan loading and validation pipeline."""

    # Load input data
    loans = load_cases(loans_path)
    assets, borrowers = load_master_data(
        assets_path,
        borrowers_path,
    )

    # Validate loan records
    accepted, rejected = validate_input(
        loans,
        assets,
        borrowers,
    )

    # Save results
    save_outputs(accepted, rejected, output_dir)

    # Print run summary
    print("LoanDesk ingestion summary")
    print("--------------------------")
    print(f"Input records:    {len(loans)}")
    print(f"Accepted records: {len(accepted)}")
    print(f"Rejected records: {len(rejected)}")
    print(f"Output directory: {output_dir}")


def main() -> None:
    """Parse command-line arguments and run the pipeline."""
    parser = argparse.ArgumentParser(
        description="Load and validate LoanDesk loan records."
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=LOANS_FILE,
        help="Path to the loan CSV file.",
    )

    args = parser.parse_args()

    run_pipeline(
        loans_path=args.input,
        assets_path=ASSETS_FILE,
        borrowers_path=BORROWERS_FILE,
        output_dir=OUTPUT_DIR,
    )


if __name__ == "__main__":
    main()
