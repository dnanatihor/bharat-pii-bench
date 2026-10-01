"""Hugging Face token-classification adapter. Imported only when ``ner`` is requested."""

import importlib
from typing import Any

from bharat_pii.config import load_bench_config, load_label_map
from bharat_pii.labels import Label
from bharat_pii.reference import project_path
from bharat_pii.vote import majority_label


class NerDetector:
    name = "ner"

    def __init__(self, model_id: str | None = None, pipeline: Any | None = None) -> None:
        chosen = model_id if model_id is not None else load_bench_config().detectors.ner_model_id
        if pipeline is None and not chosen:
            raise ValueError("detectors.ner.model_id is empty")
        self.model_id = chosen
        self.version = chosen or "injected"
        self._mapping = load_label_map(project_path("configs", "ner_map.yaml"))
        self._pipeline = pipeline if pipeline is not None else _pipeline(chosen)

    def classify_values(self, values: list[str]) -> list[Label]:
        return [_best_label(self._pipeline, value, self._mapping) for value in values]

    def classify_column(self, name: str, samples: list[str]) -> Label:
        del name
        votes = [label for label in self.classify_values(samples) if label is not Label.NONE]
        if not votes:
            return Label.NONE
        return majority_label(votes)


def _pipeline(model_id: str) -> Any:
    transformers = importlib.import_module("transformers")
    return transformers.pipeline(
        "token-classification",
        model=model_id,
        aggregation_strategy="simple",
    )


def _best_label(pipeline: Any, value: str, mapping: dict[str, Label]) -> Label:
    text = value.strip()
    if not text:
        return Label.NONE
    ranked: list[tuple[float, Label]] = []
    for hit in pipeline(text):
        entity = str(hit.get("entity_group") or hit.get("entity") or "")
        label = mapping.get(entity, Label.NONE)
        if label is Label.NONE:
            continue
        ranked.append((float(hit.get("score", 0.0)), label))
    if not ranked:
        return Label.NONE
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][1]
