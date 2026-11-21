from types import SimpleNamespace

from src.extraction_enrichment import (
    LoanExtraction,
    extract_loan_information,
    get_cache_key,
    load_cached_extraction,
    save_cached_extraction,
    extract_dataframe,
    evaluate_dev_set,
    calculate_evaluation_metrics,
    run_dev_evaluation
)



class FakeModels:
    def generate_content(self, **kwargs):
        return SimpleNamespace(
            text=(
                '{"item_condition": "damaged", '
                '"missing_accessories": ["HDMI cable"], '
                '"extension_requested": false}'
            )
        )


class FakeClient:
    def __init__(self):
        self.models = FakeModels()


def test_extract_loan_information_uses_structured_response():
    client = FakeClient()

    result = extract_loan_information(
        "The fan is cracked. Missing HDMI cable.",
        client=client,
    )

    assert isinstance(result, LoanExtraction)
    assert result.item_condition == "damaged"
    assert result.missing_accessories == ["HDMI cable"]
    assert result.extension_requested is False

import pytest
from pydantic import ValidationError


def test_extract_loan_information_rejects_empty_note():
    client = FakeClient()

    with pytest.raises(ValueError, match="must not be empty"):
        extract_loan_information("", client=client)


def test_extract_loan_information_rejects_invalid_response():
    class InvalidModels:
        def generate_content(self, **kwargs):
            return SimpleNamespace(
                text='{"item_condition": "unknown"}'
            )

    class InvalidClient:
        def __init__(self):
            self.models = InvalidModels()

    client = InvalidClient()

    with pytest.raises(ValidationError):
        extract_loan_information(
            "Some loan desk note.",
            client=client,
        )


def test_extract_loan_information_retries_api_errors(monkeypatch):
    calls = {"count": 0}

    class FailingModels:
        def generate_content(self, **kwargs):
            calls["count"] += 1
            raise RuntimeError("Temporary API error")

    class FailingClient:
        def __init__(self):
            self.models = FailingModels()

    # Avoid waiting during the test
    monkeypatch.setattr(
        "src.extraction_enrichment.time.sleep",
        lambda _: None,
    )

    client = FailingClient()

    with pytest.raises(RuntimeError, match="Temporary API error"):
        extract_loan_information(
            "Some loan desk note.",
            client=client,
        )

    assert calls["count"] == 3

def test_extract_loan_information_retries_invalid_response(monkeypatch):
    calls = {"count": 0}

    class InvalidModels:
        def generate_content(self, **kwargs):
            calls["count"] += 1
            return SimpleNamespace(
                text='{"item_condition": "unknown"}'
            )

    class InvalidClient:
        def __init__(self):
            self.models = InvalidModels()

    monkeypatch.setattr(
        "src.extraction_enrichment.time.sleep",
        lambda _: None,
    )

    client = InvalidClient()

    with pytest.raises(ValidationError):
        extract_loan_information(
            "Some loan desk note.",
            client=client,
        )

    assert calls["count"] == 2

def test_cache_key_is_consistent():
    text = "The fan is cracked."

    assert get_cache_key(text) == get_cache_key(text)
    assert get_cache_key(text) != get_cache_key("Different note.")


def test_save_and_load_cached_extraction(tmp_path):
    text = "The fan is cracked."

    extraction = LoanExtraction(
        item_condition="damaged",
        missing_accessories=["HDMI cable"],
        extension_requested=False,
    )

    save_cached_extraction(
        text,
        extraction,
        tmp_path,
    )

    cached = load_cached_extraction(
        text,
        tmp_path,
    )

    assert cached == extraction

def test_extract_loan_information_uses_cache(tmp_path):
    calls = {"count": 0}

    class CountingModels:
        def generate_content(self, **kwargs):
            calls["count"] += 1
            return SimpleNamespace(
                text=(
                    '{"item_condition": "damaged", '
                    '"missing_accessories": ["HDMI cable"], '
                    '"extension_requested": false}'
                )
            )

    class CountingClient:
        def __init__(self):
            self.models = CountingModels()

    client = CountingClient()
    note = "The fan is cracked. Missing HDMI cable."

    # First request: Gemini should be called
    first_result = extract_loan_information(
        note,
        client=client,
        cache_dir=tmp_path,
    )

    # Second request: result should come from cache
    second_result = extract_loan_information(
        note,
        client=client,
        cache_dir=tmp_path,
    )

    assert first_result == second_result
    assert calls["count"] == 1

def test_extract_dataframe_processes_multiple_loans(tmp_path):
    import pandas as pd

    class BatchModels:
        def generate_content(self, **kwargs):
            return SimpleNamespace(
                text=(
                    '{"item_condition": "good", '
                    '"missing_accessories": [], '
                    '"extension_requested": false}'
                )
            )

    class BatchClient:
        def __init__(self):
            self.models = BatchModels()

    loans = pd.DataFrame([
        {
            "LoanID": "L-001",
            "DeskNote": "Device works fine.",
        },
        {
            "LoanID": "L-002",
            "DeskNote": "Device tested and working.",
        },
    ])

    output_file = tmp_path / "extractions.csv"

    result = extract_dataframe(
        loans,
        client=BatchClient(),
        cache_dir=tmp_path / "cache",
        output_file=output_file,
    )

    assert len(result) == 2
    assert result["extraction_status"].tolist() == ["ok", "ok"]
    assert result["item_condition"].tolist() == ["good", "good"]
    assert output_file.exists()

def test_evaluate_dev_set_calculates_correctness(tmp_path):
    import pandas as pd

    class EvaluationModels:
        def generate_content(self, **kwargs):
            return SimpleNamespace(
                text=(
                    '{"item_condition": "good", '
                    '"missing_accessories": [], '
                    '"extension_requested": false}'
                )
            )

    class EvaluationClient:
        def __init__(self):
            self.models = EvaluationModels()

    dev_set = pd.DataFrame([
        {
            "DevID": "DEV-01",
            "Text": "Device works fine.",
            "gold_item_condition": "good",
            "gold_missing_accessories": "[]",
            "gold_extension_requested": False,
        },
        {
            "DevID": "DEV-02",
            "Text": "Device has light scratches.",
            "gold_item_condition": "worn",
            "gold_missing_accessories": "[]",
            "gold_extension_requested": False,
        },
    ])

    output_file = tmp_path / "llm_dev_eval.csv"

    result = evaluate_dev_set(
        dev_set,
        client=EvaluationClient(),
        cache_dir=tmp_path / "cache",
        output_file=output_file,
    )

    assert len(result) == 2
    assert result["extraction_status"].tolist() == ["ok", "ok"]

    assert result["condition_correct"].tolist() == [True, False]
    assert result["accessories_correct"].tolist() == [True, True]
    assert result["extension_correct"].tolist() == [True, True]

    assert output_file.exists()

def test_calculate_evaluation_metrics():
    import pandas as pd

    evaluation_df = pd.DataFrame([
        {
            "extraction_status": "ok",
            "condition_correct": True,
            "accessories_correct": True,
            "extension_correct": False,
        },
        {
            "extraction_status": "ok",
            "condition_correct": False,
            "accessories_correct": True,
            "extension_correct": True,
        },
        {
            "extraction_status": "failed",
            "condition_correct": False,
            "accessories_correct": False,
            "extension_correct": False,
        },
    ])

    metrics = calculate_evaluation_metrics(evaluation_df)

    assert metrics["evaluated_records"] == 2
    assert metrics["condition_accuracy"] == 0.5
    assert metrics["accessories_accuracy"] == 1.0
    assert metrics["extension_accuracy"] == 0.5

def test_run_dev_evaluation(tmp_path, monkeypatch):
    import pandas as pd
    import src.extraction_enrichment as extraction_module

    class FakeModels:
        def generate_content(self, **kwargs):
            return SimpleNamespace(
                text=(
                    '{"item_condition": "good", '
                    '"missing_accessories": [], '
                    '"extension_requested": false}'
                )
            )

    class FakeClient:
        def __init__(self):
            self.models = FakeModels()

    dev_set = pd.DataFrame([
        {
            "DevID": "DEV-01",
            "Text": "Device works fine.",
            "gold_item_condition": "good",
            "gold_missing_accessories": "[]",
            "gold_extension_requested": False,
        }
    ])

    dev_file = tmp_path / "llm_dev_set.csv"
    output_file = tmp_path / "llm_dev_eval.csv"

    dev_set.to_csv(dev_file, index=False)

    monkeypatch.setattr(
        extraction_module,
        "DEV_SET_FILE",
        dev_file,
    )
    monkeypatch.setattr(
        extraction_module,
        "LLM_DEV_EVAL_FILE",
        output_file,
    )

    evaluation_df, metrics = run_dev_evaluation(
        client=FakeClient(),
        cache_dir=tmp_path / "cache",
    )

    assert len(evaluation_df) == 1
    assert metrics["evaluated_records"] == 1
    assert metrics["condition_accuracy"] == 1.0
    assert metrics["accessories_accuracy"] == 1.0
    assert metrics["extension_accuracy"] == 1.0
    assert output_file.exists()