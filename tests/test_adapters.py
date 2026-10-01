"""Presidio and NER mapping, without downloading models."""

import dataclasses
import json
from pathlib import Path

import pytest

from bharat_pii.adapters.ner import NerDetector
from bharat_pii.adapters.presidio import PresidioDetector
from bharat_pii.config import load_bench_config
from bharat_pii.dataset import with_seed
from bharat_pii.harness import run_baseline
from bharat_pii.labels import Label


class _Hit:
    def __init__(self, entity_type: str, score: float) -> None:
        self.entity_type = entity_type
        self.score = score


class _Recognizer:
    pass


class _Analyzer:
    def analyze(self, text: str, language: str) -> list[_Hit]:
        del language
        if "@" in text:
            return [_Hit("EMAIL_ADDRESS", 0.4), _Hit("URL", 0.9)]
        if text == "Priya":
            return [_Hit("PERSON", 0.4), _Hit("PHONE_NUMBER", 0.99)]
        return [_Hit("CREDIT_CARD", 1.0)]

    def get_recognizers(self, language: str = "en") -> list[_Recognizer]:
        del language
        return [_Recognizer(), _Recognizer()]


def test_unmapped_presidio_entities_are_none() -> None:
    detector = PresidioDetector(analyzer=_Analyzer())
    labels = detector.classify_values(["not-an-id", "user@example.com", "Priya"])
    assert labels == [Label.NONE, Label.EMAIL, Label.PERSON_NAME]
    assert detector.active_recognizers == ("_Recognizer",)


def test_ner_uses_the_highest_mapped_group() -> None:
    def pipeline(text: str) -> list[dict[str, object]]:
        del text
        return [
            {"entity_group": "ORG", "score": 0.99},
            {"entity_group": "PER", "score": 0.5},
        ]

    detector = NerDetector(model_id="toy", pipeline=pipeline)
    assert detector.classify_values(["Priya Sharma"]) == [Label.PERSON_NAME]
    assert detector.classify_column("notes", ["", "Priya", "office"]) == Label.PERSON_NAME
    assert detector.classify_column("notes", ["", ""]) == Label.NONE


def test_report_lists_active_recognizers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    detector = PresidioDetector(analyzer=_Analyzer())

    def loader(name: str, budget: object = None) -> PresidioDetector:
        del budget
        assert name == "presidio"
        return detector

    monkeypatch.setattr("bharat_pii.harness.detector_by_name", loader)
    config = dataclasses.replace(
        with_seed(load_bench_config(), 1),
        per_label_count=1,
        none_count=1,
        column_sample_size=2,
    )
    paths = run_baseline(
        config,
        detectors=("presidio",),
        tasks=("t1",),
        split="test",
        out_root=tmp_path,
    )
    report = (paths.directory / "report.md").read_text(encoding="utf-8")
    recorded = json.loads((paths.directory / "run.json").read_text(encoding="utf-8"))
    assert "### Active Presidio recognizers" in report
    assert "_Recognizer" in report
    assert recorded["active_presidio_recognizers"] == ["_Recognizer"]
