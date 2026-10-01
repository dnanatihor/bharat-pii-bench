"""T3 sentences and exact-span precision and recall."""

import random
from collections.abc import Sequence
from dataclasses import dataclass

from bharat_pii.config import BenchConfig
from bharat_pii.detect import Span, find
from bharat_pii.generate import GENERATORS
from bharat_pii.labels import Label

_PERSONAL = tuple(generator for generator in GENERATORS if generator.label is not Label.NONE)
_TEMPLATES = {
    "english": "The recorded value is {value} for this file.",
    "hindi": "दर्ज मूल्य {value} है।",
    "hinglish": "record me {value} save karo.",
}


@dataclass(frozen=True, slots=True)
class Sentence:
    text: str
    language: str
    spans: tuple[Span, ...]


def build_t3(config: BenchConfig) -> tuple[Sentence, ...]:
    """One embedded identifier per sentence, ``per_label_count`` times per language."""
    rng = random.Random(config.seed)
    sentences: list[Sentence] = []
    for language, template in _TEMPLATES.items():
        for index in range(config.per_label_count):
            generator = _PERSONAL[index % len(_PERSONAL)]
            value = generator.generate(rng).value
            prefix, suffix = template.split("{value}")
            text = prefix + value + suffix
            span = Span(generator.label, len(prefix), len(prefix) + len(value))
            sentences.append(Sentence(text, language, (span,)))
    return tuple(sentences)


def span_precision_recall(
    gold: Sequence[Sequence[Span]],
    predicted: Sequence[Sequence[Span]],
) -> tuple[float, float]:
    """Exact ``(label, start, end)`` match. Partial overlaps do not count."""
    if len(gold) != len(predicted):
        raise ValueError("gold and predicted must have the same length")
    true_positives = 0
    false_positives = 0
    false_negatives = 0
    for expected, guessed in zip(gold, predicted, strict=True):
        gold_set = {(span.label, span.start, span.end) for span in expected}
        pred_set = {(span.label, span.start, span.end) for span in guessed}
        true_positives += len(gold_set & pred_set)
        false_positives += len(pred_set - gold_set)
        false_negatives += len(gold_set - pred_set)
    predicted_positive = true_positives + false_positives
    actual_positive = true_positives + false_negatives
    precision = true_positives / predicted_positive if predicted_positive else 0.0
    recall = true_positives / actual_positive if actual_positive else 0.0
    return precision, recall


def regex_spans(texts: Sequence[str]) -> list[list[Span]]:
    return [find(text) for text in texts]
