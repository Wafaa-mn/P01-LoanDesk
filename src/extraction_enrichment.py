from __future__ import annotations

import re
import json
import os
import time
from typing import Literal

import hashlib
from pathlib import Path

from google import genai
from google.genai import types
from pydantic import BaseModel, ConfigDict, Field, ValidationError

import pandas as pd

from src.config import (
    GEMINI_MODEL,
    GEMINI_MAX_ATTEMPTS,
    GEMINI_RETRY_DELAY,
    EXTRACTION_CACHE_DIR,
    EXTRACTIONS_FILE,
    LLM_DEV_EVAL_FILE,
    DEV_SET_FILE
)

# Allowed condition values for a loaned item
ItemCondition = Literal[
    "good",
    "worn",
    "damaged",
    "not_inspected",
]


class LoanExtraction(BaseModel):
    """
    Structured information extracted from a loan desk note.
    """

    model_config = ConfigDict(extra="forbid")

    item_condition: ItemCondition = Field(
        description=(
            "Condition of the item: good, worn, damaged, "
            "or not_inspected."
        )
    )

    missing_accessories: list[str] = Field(
        description=(
            "List of accessories explicitly reported as missing. "
            "Return an empty list if none are missing."
        )
    )

    extension_requested: bool = Field(
        description=(
            "True only when the borrower explicitly requests "
            "an extension of the loan period."
        )
    )


def build_extraction_prompt(text: str) -> str:
    """
    Build the prompt used to extract structured loan information.
    """

    return f"""
You are an information extraction assistant for LoanDesk.

Analyze the following loan desk note and extract exactly three fields.

RULES:

1. item_condition:
   - good: The item was inspected and has no reported issues.
   - worn: The item shows normal signs of use or wear.
   - damaged: The item has physical damage or requires repair.
   - not_inspected: The item has not been inspected, or its condition
     cannot be determined from the note.

2. missing_accessories:
   - Return a list containing only accessories explicitly reported
     as missing or not returned.
   - Return an empty list if no missing accessories are mentioned.
   - Do not infer missing accessories.

3. extension_requested:
   - true only when the borrower explicitly asks for an extension.
   - false otherwise.
   - Do not assume an extension request simply because a loan
     is overdue or has not yet been returned.

IMPORTANT:
- Extract only information supported by the text.
- Do not invent information.
- The three fields must be evaluated independently.
- Follow the required JSON schema exactly.

LOAN DESK NOTE:
{text}
""".strip()


def get_cache_key(text: str) -> str:
    """
    Generate a SHA-256 key for a loan desk note.
    """

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def load_cached_extraction(
    text: str,
    cache_dir: Path,
) -> LoanExtraction | None:
    """
    Load a previous extraction from the JSON cache.
    """

    cache_key = get_cache_key(text)
    cache_file = cache_dir / f"{cache_key}.json"

    if not cache_file.exists():
        return None

    try:
        cached_data = json.loads(
            cache_file.read_text(encoding="utf-8")
        )
        return LoanExtraction.model_validate(cached_data)

    except (json.JSONDecodeError, ValueError, OSError):
        # Ignore corrupted or invalid cache entries
        return None


def save_cached_extraction(
    text: str,
    extraction: LoanExtraction,
    cache_dir: Path,
) -> None:
    """
    Save a successful extraction to the JSON cache.
    """

    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_key = get_cache_key(text)
    cache_file = cache_dir / f"{cache_key}.json"

    cache_file.write_text(
        extraction.model_dump_json(indent=2),
        encoding="utf-8",
    )



def extract_loan_information(
    text: str,
    client=None,
    cache_dir: Path | None = None,
) -> LoanExtraction:
    """
    Extract structured loan information using Gemini.

    Successful extractions are cached using SHA-256.
    API errors are retried up to GEMINI_MAX_ATTEMPTS.
    Invalid responses are retried once.
    """

    if not isinstance(text, str) or not text.strip():
        raise ValueError("Loan note text must not be empty.")

    # Use the configured cache directory unless another is supplied
    if cache_dir is None:
        cache_dir = EXTRACTION_CACHE_DIR

    # Check the cache before calling Gemini
    cached_extraction = load_cached_extraction(text, cache_dir)

    if cached_extraction is not None:
        return cached_extraction

    # Create Gemini client using the environment API key
    if client is None:
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY environment variable is not set."
            )

        client = genai.Client(api_key=api_key)

    prompt = build_extraction_prompt(text)

    api_attempts = 0
    invalid_response_attempts = 0

    while api_attempts < GEMINI_MAX_ATTEMPTS:
        try:
            api_attempts += 1

            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_json_schema=LoanExtraction.model_json_schema(),
                    temperature=0.0,
                ),
            )

            raw_text = response.text

            if not raw_text:
                raise ValueError("Gemini returned an empty response.")

            extraction = LoanExtraction.model_validate_json(raw_text)

            # Cache only successful, validated extractions
            save_cached_extraction(text, extraction, cache_dir)

            return extraction

        except (ValidationError, ValueError, json.JSONDecodeError):
            invalid_response_attempts += 1

            if invalid_response_attempts >= 2:
                raise

            time.sleep(GEMINI_RETRY_DELAY)

        except Exception as exc:
            if api_attempts >= GEMINI_MAX_ATTEMPTS:
                raise

            error_message = str(exc)

            # Respect Gemini's requested retry delay for rate limits.
            if "429" in error_message or "RESOURCE_EXHAUSTED" in error_message:
                match = re.search(
                    r"retryDelay['\"]?\s*:\s*['\"]([\d.]+)s",
                    error_message,
                )

                if match is None:
                    match = re.search(
                        r"Please retry in ([\d.]+)s",
                        error_message,
                    )

                wait_seconds = (
                    float(match.group(1)) + 1
                    if match
                    else 60
                )

                print(
                    f"Gemini rate limit reached. "
                    f"Waiting {wait_seconds:.1f} seconds..."
                )

                time.sleep(wait_seconds)

            else:
                time.sleep(GEMINI_RETRY_DELAY)

    raise RuntimeError("Gemini extraction failed.")


def extract_dataframe(
    loans: pd.DataFrame,
    client=None,
    cache_dir: Path | None = None,
    output_file: Path | None = None,
) -> pd.DataFrame:
    """
    Extract structured information from all loan desk notes.

    Each loan is processed independently. A failed extraction
    does not stop the remaining loans from being processed.
    """

    required_columns = {"LoanID", "DeskNote"}

    missing_columns = required_columns - set(loans.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    results = []

    for _, row in loans.iterrows():
        loan_id = row["LoanID"]
        note = row["DeskNote"]

        result = {
            "LoanID": loan_id,
            "item_condition": None,
            "missing_accessories": None,
            "extension_requested": None,
            "extraction_status": "failed",
            "extraction_error": None,
        }

        try:
            extraction = extract_loan_information(
                note,
                client=client,
                cache_dir=cache_dir,
            )

            result.update({
                "item_condition": extraction.item_condition,
                "missing_accessories": json.dumps(
                    extraction.missing_accessories
                ),
                "extension_requested": extraction.extension_requested,
                "extraction_status": "ok",
            })

        except Exception as error:
            result["extraction_error"] = str(error)

        results.append(result)

    extraction_df = pd.DataFrame(results)

    if output_file is None:
        output_file = EXTRACTIONS_FILE

    output_file.parent.mkdir(parents=True, exist_ok=True)

    extraction_df.to_csv(output_file, index=False)

    return extraction_df


def evaluate_dev_set(
    dev_set: pd.DataFrame,
    client=None,
    cache_dir: Path | None = None,
    output_file: Path | None = None,
) -> pd.DataFrame:
    """
    Evaluate Gemini extraction against the labelled development set.

    Calculates exact-match correctness for each extracted field.
    """

    required_columns = {
        "DevID",
        "Text",
        "gold_item_condition",
        "gold_missing_accessories",
        "gold_extension_requested",
    }

    missing_columns = required_columns - set(dev_set.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    results = []

    for _, row in dev_set.iterrows():
        result = {
            "DevID": row["DevID"],
            "item_condition": None,
            "missing_accessories": None,
            "extension_requested": None,
            "extraction_status": "failed",
            "condition_correct": False,
            "accessories_correct": False,
            "extension_correct": False,
        }

        try:
            extraction = extract_loan_information(
                row["Text"],
                client=client,
                cache_dir=cache_dir,
            )

            predicted_accessories = sorted(
                extraction.missing_accessories
            )
            gold_accessories = sorted(
                json.loads(row["gold_missing_accessories"])
            )

            result.update({
                "item_condition": extraction.item_condition,
                "missing_accessories": json.dumps(
                    extraction.missing_accessories
                ),
                "extension_requested": extraction.extension_requested,
                "extraction_status": "ok",
                "condition_correct": (
                    extraction.item_condition
                    == row["gold_item_condition"]
                ),
                "accessories_correct": (
                    predicted_accessories == gold_accessories
                ),
                "extension_correct": (
                    extraction.extension_requested
                    == bool(row["gold_extension_requested"])
                ),
            })

        except Exception as error:
            result["extraction_error"] = str(error)

        results.append(result)

    evaluation_df = pd.DataFrame(results)

    if output_file is None:
        output_file = LLM_DEV_EVAL_FILE

    output_file.parent.mkdir(parents=True, exist_ok=True)

    evaluation_df.to_csv(output_file, index=False)

    return evaluation_df

def calculate_evaluation_metrics(
    evaluation_df: pd.DataFrame,
) -> dict:
    """
    Calculate field-level accuracy using successful extractions only.
    """

    successful = evaluation_df[
        evaluation_df["extraction_status"] == "ok"
    ]

    total = len(successful)

    if total == 0:
        return {
            "evaluated_records": 0,
            "condition_accuracy": 0.0,
            "accessories_accuracy": 0.0,
            "extension_accuracy": 0.0,
        }

    return {
        "evaluated_records": total,
        "condition_accuracy": successful["condition_correct"].mean(),
        "accessories_accuracy": successful["accessories_correct"].mean(),
        "extension_accuracy": successful["extension_correct"].mean(),
    }

def run_dev_evaluation(
    client=None,
    cache_dir: Path | None = None,
) -> tuple[pd.DataFrame, dict]:
    """
    Load the labelled development set, evaluate Gemini,
    and calculate field-level accuracy.
    """

    dev_set = pd.read_csv(DEV_SET_FILE)

    evaluation_df = evaluate_dev_set(
        dev_set,
        client=client,
        cache_dir=cache_dir,
        output_file=LLM_DEV_EVAL_FILE,
    )

    metrics = calculate_evaluation_metrics(evaluation_df)

    return evaluation_df, metrics