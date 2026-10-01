"""Presidio adapter. Imported only when the ``presidio`` detector is requested."""

import importlib
from collections.abc import Iterable
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from bharat_pii.config import load_label_map
from bharat_pii.labels import Label
from bharat_pii.reference import project_path
from bharat_pii.vote import majority_label


class PresidioDetector:
    name = "presidio"

    def __init__(self, analyzer: Any | None = None) -> None:
        self._mapping = load_label_map(project_path("configs", "presidio_map.yaml"))
        self._analyzer = analyzer if analyzer is not None else _build_analyzer()
        self.active_recognizers = tuple(_recognizer_names(self._analyzer))
        try:
            self.version = version("presidio-analyzer")
        except PackageNotFoundError:
            self.version = "unknown"

    def classify_values(self, values: list[str]) -> list[Label]:
        return [_best_label(self._analyzer, value, self._mapping) for value in values]

    def classify_column(self, name: str, samples: list[str]) -> Label:
        del name
        votes = [label for label in self.classify_values(samples) if label is not Label.NONE]
        if not votes:
            return Label.NONE
        return majority_label(votes)


def _build_analyzer() -> Any:
    engine_cls = importlib.import_module("presidio_analyzer").AnalyzerEngine
    engine = engine_cls()
    _register_india_recognizers(engine)
    return engine


def _register_india_recognizers(engine: Any) -> None:
    """Add India-specific recognizer classes shipped with this Presidio version."""
    module = importlib.import_module("presidio_analyzer.predefined_recognizers")
    present = set(_recognizer_names(engine))
    for attr in dir(module):
        if not attr.startswith("In") or attr in present:
            continue
        cls = getattr(module, attr)
        if not isinstance(cls, type):
            continue
        try:
            recognizer = cls()
        except TypeError:
            continue
        engine.registry.add_recognizer(recognizer)


def _recognizer_names(engine: Any) -> Iterable[str]:
    recognizers = engine.get_recognizers(language="en")
    names = [type(recognizer).__name__ for recognizer in recognizers]
    return sorted(set(names))


def _best_label(engine: Any, value: str, mapping: dict[str, Label]) -> Label:
    text = value.strip()
    if not text:
        return Label.NONE
    hits = engine.analyze(text=text, language="en")
    ranked: list[tuple[float, Label]] = []
    for hit in hits:
        label = mapping.get(str(hit.entity_type), Label.NONE)
        if label is Label.NONE:
            continue
        score = float(hit.score)
        ranked.append((score, label))
    if not ranked:
        return Label.NONE
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][1]
