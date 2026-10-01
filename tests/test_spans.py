"""T3 sentences and exact-span precision and recall for regex and the stub LLM."""

import dataclasses
from pathlib import Path

import pytest

from bharat_pii.adapters.llm import LlmDetector
from bharat_pii.config import ModelPrice, load_bench_config
from bharat_pii.cost import Budget
from bharat_pii.dataset import with_seed
from bharat_pii.detect import Span, find
from bharat_pii.harness import run_baseline
from bharat_pii.labels import Label
from bharat_pii.spans import build_t3, span_precision_recall

_PRICE = ModelPrice(1_000_000, 1_000_000)


def test_span_precision_and_recall_are_exact() -> None:
    gold = [[Span(Label.IN_PAN, 4, 14)]]
    predicted = [[Span(Label.IN_PAN, 4, 14), Span(Label.EMAIL, 0, 3)]]
    precision, recall = span_precision_recall(gold, predicted)
    assert precision == 0.5
    assert recall == 1.0


def test_sentences_cover_english_hindi_and_hinglish() -> None:
    config = dataclasses.replace(with_seed(load_bench_config(), 3), per_label_count=15)
    sentences = build_t3(config)
    assert {sentence.language for sentence in sentences} == {"english", "hindi", "hinglish"}
    hindi = next(sentence for sentence in sentences if sentence.language == "hindi")
    hinglish = next(sentence for sentence in sentences if sentence.language == "hinglish")
    assert any("\u0900" <= character <= "\u097f" for character in hindi.text)
    assert "record me " in hinglish.text
    english = next(
        sentence
        for sentence in sentences
        if sentence.language == "english" and sentence.spans[0].label is Label.IN_PAN
    )
    span = english.spans[0]
    assert english.text[span.start : span.end]
    assert span in find(english.text)


def test_t3_report_lists_regex_and_llm_span_scores(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Empty:
        def invoke(self, prompt: str) -> dict[str, object]:
            del prompt
            usage = {"input_tokens": 1, "output_tokens": 1}
            return {"parsed": {"items": []}, "raw": {"usage_metadata": usage}}

    def loader(name: str, budget: Budget | None = None) -> object:
        if name == "regex_checksum":
            from bharat_pii.detect import RegexChecksum

            return RegexChecksum()
        assert name == "llm"
        return LlmDetector(model=_Empty(), model_id="stub", budget=budget, price=_PRICE)

    monkeypatch.setattr("bharat_pii.harness.detector_by_name", loader)
    config = dataclasses.replace(with_seed(load_bench_config(), 3), per_label_count=15)
    paths = run_baseline(
        config,
        detectors=("regex_checksum", "llm"),
        tasks=("t3",),
        out_root=tmp_path,
        budget_usd=1_000_000,
    )
    report = (paths.directory / "report.md").read_text(encoding="utf-8")
    sentences = build_t3(config)
    regex_precision, regex_recall = span_precision_recall(
        [sentence.spans for sentence in sentences],
        [find(sentence.text) for sentence in sentences],
    )
    assert f"- span precision: {regex_precision:.4f}" in report
    assert f"- span recall: {regex_recall:.4f}" in report
    assert report.count("### Span detection (T3)") == 2
    assert "- span precision: 0.0000" in report
    assert "- span recall: 0.0000" in report
