"""Public detector API from SPEC.md §5.

Algorithms land in Phase 3. This module stays free of optional dependencies
so ``pip install bharat-pii`` can import it.
"""

from typing import Protocol

from bharat_pii.labels import Label


class Span:
    """A labelled character span inside a string."""

    __slots__ = ("end", "label", "start")

    def __init__(self, label: Label, start: int, end: int) -> None:
        self.label = label
        self.start = start
        self.end = end


class Detector(Protocol):
    """A value-level and column-level classifier."""

    name: str
    version: str

    def classify_values(self, values: list[str]) -> list[Label]:
        """Classify each value independently."""
        ...

    def classify_column(self, name: str, samples: list[str]) -> Label:
        """Classify one column from its name and sample values."""
        ...


def find(text: str) -> list[Span]:
    """Return labelled spans in ``text``. Implemented in Phase 3."""
    raise NotImplementedError("bharat_pii.detect.find is implemented in Phase 3")


def classify_value(value: str) -> Label:
    """Classify one value. Implemented in Phase 3."""
    raise NotImplementedError("bharat_pii.detect.classify_value is implemented in Phase 3")


def mask(text: str, token_style: str = "typed") -> str:
    """Mask detected spans. Implemented in Phase 3."""
    raise NotImplementedError("bharat_pii.detect.mask is implemented in Phase 3")
