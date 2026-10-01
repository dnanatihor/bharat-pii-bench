"""Column label from a majority of value labels. A tie is ``NONE``."""

from collections import Counter
from collections.abc import Sequence

from bharat_pii.labels import Label


def majority_label(labels: Sequence[Label]) -> Label:
    if not labels:
        return Label.NONE
    counts = Counter(labels)
    best = max(counts.values())
    tied = [label for label, count in counts.items() if count == best]
    if len(tied) == 1:
        return tied[0]
    return Label.NONE
