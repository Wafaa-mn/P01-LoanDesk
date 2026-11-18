
from __future__ import annotations

import json

import pytest
import requests

from src.api_client import (
    fetch_holiday_response,
    get_national_holidays,
)


def sample_holidays() -> list[dict]:
    """Return sample API data with national and regional holidays."""
    return [
        {
            "date": "2026-01-01",
            "localName": "Újév",
            "name": "New Year's Day",
            "global": True,
        },
        {
            "date": "2026-03-15",
            "localName": "Nemzeti ünnep",
            "name": "National Day",
            "global": True,
        },
        {
            "date": "2026-06-06",
            "localName": "Regional holiday",
            "name": "Regional holiday",
            "global": False,
        },
    ]


class FakeResponse:
    """A small fake HTTP response for testing."""

    def __init__(self, data: list[dict], status_code: int = 200):
        self.text = json.dumps(data)
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(
                f"HTTP {self.status_code}",
                response=self,
            )


def test_fetch_holiday_response_saves_raw_cache(tmp_path, monkeypatch):
    payload = sample_holidays()
    cache_path = tmp_path / "cache" / "holidays.json"
    calls = []

    def fake_get(url, timeout):
        calls.append((url, timeout))
        return FakeResponse(payload)

    monkeypatch.setattr("src.api_client.requests.get", fake_get)

    result = fetch_holiday_response(cache_path, timeout=5)

    assert result == payload
    assert cache_path.exists()
    assert json.loads(cache_path.read_text(encoding="utf-8")) == payload
    assert len(calls) == 1
    assert calls[0][1] == 5


def test_fetch_holiday_response_reuses_cache(tmp_path, monkeypatch):
    payload = sample_holidays()
    cache_path = tmp_path / "holidays.json"
    cache_path.write_text(json.dumps(payload), encoding="utf-8")

    def unexpected_request(*args, **kwargs):
        raise AssertionError("A request should not be made when cache exists.")

    monkeypatch.setattr(
        "src.api_client.requests.get",
        unexpected_request,
    )

    result = fetch_holiday_response(cache_path)

    assert result == payload


def test_get_national_holidays_excludes_regional_holidays(
    tmp_path,
    monkeypatch,
):
    payload = sample_holidays()

    def fake_get(url, timeout):
        return FakeResponse(payload)

    monkeypatch.setattr("src.api_client.requests.get", fake_get)

    df = get_national_holidays(tmp_path / "holidays.json")

    assert list(df.columns) == [
        "HolidayDate",
        "LocalName",
        "Name",
    ]
    assert len(df) == 2
    assert "Regional holiday" not in df["Name"].tolist()


def test_fetch_holiday_response_raises_on_timeout(
    tmp_path,
    monkeypatch,
):
    def fake_get(url, timeout):
        raise requests.Timeout("Request timed out")

    monkeypatch.setattr("src.api_client.requests.get", fake_get)

    with pytest.raises(RuntimeError, match="timed out"):
        fetch_holiday_response(tmp_path / "holidays.json")

    assert not (tmp_path / "holidays.json").exists()


def test_fetch_holiday_response_raises_on_http_error(
    tmp_path,
    monkeypatch,
):
    def fake_get(url, timeout):
        return FakeResponse([], status_code=500)

    monkeypatch.setattr("src.api_client.requests.get", fake_get)

    with pytest.raises(RuntimeError, match="HTTP status 500"):
        fetch_holiday_response(tmp_path / "holidays.json")

    assert not (tmp_path / "holidays.json").exists()


def test_fetch_holiday_response_rejects_invalid_payload(
    tmp_path,
    monkeypatch,
):
    invalid_payload = [
        {
            "date": "2026-01-01",
            "localName": "Újév",
            "name": "New Year's Day",
            # The required "global" field is missing.
        }
    ]

    def fake_get(url, timeout):
        return FakeResponse(invalid_payload)

    monkeypatch.setattr("src.api_client.requests.get", fake_get)

    with pytest.raises(ValueError, match="missing fields"):
        fetch_holiday_response(tmp_path / "holidays.json")

    assert not (tmp_path / "holidays.json").exists()
