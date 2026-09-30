"""Precision, recall, and the benchmark summaries from SPEC.md §6."""

import math
from collections.abc import Sequence
from dataclasses import dataclass

from bharat_pii.labels import Label


@dataclass(frozen=True, slots=True)
class LabelScore:
    label: Label
    precision: float
    recall: float
    f1: float
    support: int


@dataclass(frozen=True, slots=True)
class ScoreCard:
    per_label: tuple[LabelScore, ...]
    macro_f1: float
    micro_f1: float
    confusion: dict[tuple[Label, Label], int]


def score(truth: Sequence[Label], predicted: Sequence[Label]) -> ScoreCard:
    """Per-label precision, recall, F1, plus macro-F1 and micro-F1."""
    if len(truth) != len(predicted):
        raise ValueError("truth and predicted must have the same length")
    labels = tuple(Label)
    confusion = {(row, column): 0 for row in labels for column in labels}
    for actual, guess in zip(truth, predicted, strict=True):
        confusion[(actual, guess)] += 1
    per_label: list[LabelScore] = []
    true_positives = 0
    predicted_positive = 0
    support_total = 0
    for label in labels:
        tp = confusion[(label, label)]
        fp = sum(confusion[(other, label)] for other in labels if other is not label)
        fn = sum(confusion[(label, other)] for other in labels if other is not label)
        support = tp + fn
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = _f1(precision, recall)
        per_label.append(LabelScore(label, precision, recall, f1, support))
        if label is not Label.NONE:
            true_positives += tp
            predicted_positive += tp + fp
            support_total += support
    scored = [item for item in per_label if item.label is not Label.NONE]
    macro = sum(item.f1 for item in scored) / len(scored) if scored else 0.0
    micro_precision = true_positives / predicted_positive if predicted_positive else 0.0
    micro_recall = true_positives / support_total if support_total else 0.0
    return ScoreCard(tuple(per_label), macro, _f1(micro_precision, micro_recall), confusion)


def hard_negative_false_positive_rate(truth: Sequence[bool], predicted: Sequence[Label]) -> float:
    """Share of hard negatives predicted as a personal label."""
    if len(truth) != len(predicted):
        raise ValueError("truth and predicted must have the same length")
    negatives = [guess for flag, guess in zip(truth, predicted, strict=True) if flag]
    if not negatives:
        return 0.0
    false_positives = sum(guess is not Label.NONE for guess in negatives)
    return false_positives / len(negatives)


def name_sensitivity(scores: dict[str, float]) -> dict[str, float]:
    """Macro-F1 by name condition and the drop from truthful."""
    truthful = scores["truthful"]
    return {
        "truthful": truthful,
        "obfuscated": scores["obfuscated"],
        "misleading": scores["misleading"],
        "drop_obfuscated": truthful - scores["obfuscated"],
        "drop_misleading": truthful - scores["misleading"],
    }


def percentile(values: Sequence[float], pct: float) -> float:
    """Nearest-rank percentile in ``[0, 100]``."""
    if not values:
        raise ValueError("percentile of an empty sequence")
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100 * len(ordered)))
    return ordered[rank - 1]


def _f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)
