
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import requests

from src.config import API_TIMEOUT, HOLIDAY_API_URL


HOLIDAY_COLUMNS = [
    "HolidayDate",
    "LocalName",
    "Name",
]


def validate_api_data(data: object) -> None:
    """Check that the API response has the expected structure."""
    if not isinstance(data, list):
        raise ValueError("Holiday API response must be a list.")

    required_fields = {
        "date",
        "localName",
        "name",
        "global",
    }

    for index, holiday in enumerate(data):
        if not isinstance(holiday, dict):
            raise ValueError(
                f"Invalid holiday entry at position {index}."
            )

        missing_fields = required_fields - set(holiday.keys())

        if missing_fields:
            raise ValueError(
                f"Holiday entry {index} is missing fields: "
                f"{', '.join(sorted(missing_fields))}"
            )

        if not isinstance(holiday["global"], bool):
            raise ValueError(
                f"Invalid global value in holiday entry {index}."
            )

        for field in ("date", "localName", "name"):
            if not isinstance(holiday[field], str):
                raise ValueError(
                    f"Invalid {field} in holiday entry {index}."
                )


def fetch_holiday_response(
    cache_path: Path,
    timeout: int = API_TIMEOUT,
) -> list[dict]:
    """Fetch holiday data or reuse the cached API response."""

    if cache_path.exists():
        raw_data = cache_path.read_text(encoding="utf-8")
        data = json.loads(raw_data)
        validate_api_data(data)
        return data

    try:
        response = requests.get(
            HOLIDAY_API_URL,
            timeout=timeout,
        )
        response.raise_for_status()

    except requests.Timeout as exc:
        raise RuntimeError(
            "Holiday API request timed out."
        ) from exc

    except requests.HTTPError as exc:
        status = (
            exc.response.status_code
            if exc.response is not None
            else "unknown"
        )
        raise RuntimeError(
            f"Holiday API request failed with HTTP status {status}."
        ) from exc

    except requests.RequestException as exc:
        raise RuntimeError(
            f"Holiday API request failed: {exc}"
        ) from exc

    raw_data = response.text
    data = json.loads(raw_data)

    validate_api_data(data)

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(raw_data, encoding="utf-8")

    return data


def get_national_holidays(
    cache_path: Path,
    timeout: int = API_TIMEOUT,
) -> pd.DataFrame:
    """Return only nationwide Hungarian public holidays."""

    data = fetch_holiday_response(cache_path, timeout)

    national_holidays = []

    for holiday in data:
        if holiday["global"] is True:
            national_holidays.append(
                {
                    "HolidayDate": holiday["date"],
                    "LocalName": holiday["localName"],
                    "Name": holiday["name"],
                }
            )

    return pd.DataFrame(
        national_holidays,
        columns=HOLIDAY_COLUMNS,
    )
