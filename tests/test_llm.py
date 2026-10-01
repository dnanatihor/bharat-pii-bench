"""Stub LLM: batching, the column prompt, hybrid routing, and the budget guard."""

import dataclasses
import json
import re
from pathlib import Path

import pytest

from bharat_pii.adapters.hybrid import HybridDetector
from bharat_pii.adapters.llm import LlmDetector, render_prompt
from bharat_pii.config import ModelPrice, load_bench_config
from bharat_pii.cost import Budget, estimate_tokens, token_cost
from bharat_pii.dataset import with_seed
from bharat_pii.detect import detector_by_name
from bharat_pii.harness import run_baseline
from bharat_pii.labels import Label

_PRICE = ModelPrice(input_per_million_usd=1_000_000, output_per_million_usd=1_000_000)


class _Model:
    def __init__(self, label: str = "PERSON_NAME") -> None:
        self.prompts: list[str] = []
        self.label = label

    def invoke(self, prompt: str) -> dict[str, object]:
        self.prompts.append(prompt)
        count = len(re.findall(r"(?m)^\d+\. ", prompt))
        input_tokens, output_tokens = estimate_tokens(prompt, count)
        items = [{"label": self.label, "reported_confidence": 0.5} for _ in range(count)]
        return {
            "parsed": {"items": items},
            "raw": {
                "usage_metadata": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                }
            },
        }


def test_token_cost_uses_the_price_file_units() -> None:
    price = ModelPrice(input_per_million_usd=2.0, output_per_million_usd=8.0)
    assert token_cost(1_000_000, 500_000, price) == 6.0


def test_values_are_batched_fifty_per_call() -> None:
    model = _Model()
    detector = LlmDetector(model=model, model_id="stub", budget=Budget(1_000_000), price=_PRICE)
    labels = detector.classify_values(["aa"] * 101)
    assert detector.calls == 3
    assert len(labels) == 101
    assert labels[0] is Label.PERSON_NAME


def test_unknown_model_label_becomes_none() -> None:
    model = _Model(label="NOT_A_LABEL")
    detector = LlmDetector(model=model, model_id="stub", budget=Budget(1_000_000), price=_PRICE)
    assert detector.classify_values(["aa"]) == [Label.NONE]


def test_column_prompt_contains_taxonomy_name_and_samples() -> None:
    model = _Model()
    detector = LlmDetector(model=model, model_id="stub", budget=Budget(1_000_000), price=_PRICE)
    label = detector.classify_column("customer_name", ["Priya", "", "Amit"])
    prompt = model.prompts[0]
    assert "prompt_version: llm_v1" in prompt
    assert "IN_AADHAAR" in prompt
    assert "Column name: customer_name" in prompt
    assert "1. Priya" in prompt
    assert "2. Amit" in prompt
    assert label is Label.PERSON_NAME
    text = Path("src/bharat_pii/prompts/llm_v1.txt").read_text(encoding="utf-8")
    assert "prompt_version: llm_v1" in text


def test_budget_stops_later_batches() -> None:
    values = ["aa"] * 120
    first = render_prompt("(none)", values[:50])
    estimate = token_cost(*estimate_tokens(first, 50), _PRICE)
    budget = Budget(estimate)
    model = _Model()
    detector = LlmDetector(model=model, model_id="stub", budget=budget, price=_PRICE)
    labels = detector.classify_values(values)
    assert detector.calls == 1
    assert detector.cost_usd <= budget.limit_usd
    assert labels[:50] == [Label.PERSON_NAME] * 50
    assert labels[50:] == [Label.NONE] * 70


def test_hybrid_sends_only_lettered_none_values() -> None:
    model = _Model()
    detector = LlmDetector(model=model, model_id="stub", budget=Budget(1_000_000), price=_PRICE)
    hybrid = HybridDetector(detector)
    labels = hybrid.classify_values(["hello", "......", "6000000001"])
    assert labels == [Label.PERSON_NAME, Label.NONE, Label.IN_MOBILE]
    assert "hello" in model.prompts[0]
    assert "......" not in model.prompts[0]
    assert "6000000001" not in model.prompts[0]


def test_empty_model_list_is_rejected() -> None:
    with pytest.raises(ValueError, match="model_ids"):
        detector_by_name("llm")


def test_harness_run_stays_within_budget(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[LlmDetector] = []

    def loader(name: str, budget: Budget | None = None) -> LlmDetector:
        assert name == "llm"
        detector = LlmDetector(model=_Model(), model_id="stub", budget=budget, price=_PRICE)
        created.append(detector)
        return detector

    monkeypatch.setattr("bharat_pii.harness.detector_by_name", loader)
    config = dataclasses.replace(
        with_seed(load_bench_config(), 1),
        per_label_count=1,
        none_count=1,
    )
    paths = run_baseline(
        config,
        detectors=("llm",),
        tasks=("t1",),
        split="test",
        out_root=tmp_path,
        budget_usd=0,
    )
    recorded = json.loads((paths.directory / "run.json").read_text(encoding="utf-8"))
    assert recorded["cost_usd"] <= recorded["budget_usd"]
    assert recorded["prompt_version"] == "llm_v1"
    assert recorded["model_ids"] == ["stub"]
    assert created[0].calls == 0
    report = (paths.directory / "report.md").read_text(encoding="utf-8")
    assert "cost per 1,000 values" in report
