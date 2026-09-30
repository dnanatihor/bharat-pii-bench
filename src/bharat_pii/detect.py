"""Pattern and checksum detector. No optional dependencies."""

import re
from collections import Counter
from typing import Protocol

from bharat_pii.labels import Label
from bharat_pii.validate import VALIDATORS

_VERSION = "0.1.0"
_ISO_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}")
_UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
_VEHICLE = (
    r"[0-9]{2}[ -]?BH[ -]?\d{4}[ -]?[A-Z]{1,2}"
    r"|[A-Z]{2}[ -]?\d{1,2}[ -]?[A-Z]{1,3}[ -]?\d{4}"
)
_DOB = r"\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{1,2} [A-Za-z\u0900-\u097F]+ \d{4}"
_MOBILE = r"\+91[-\s]\d{5}[-\s]?\d{5}|\+91-?\d{10}|0\d{10}|\d{5} \d{5}|\d{10}"
_CANDIDATES: tuple[tuple[Label, re.Pattern[str]], ...] = (
    (Label.EMAIL, re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    (Label.IN_UPI_ID, re.compile(r"[a-z0-9][a-z0-9.]{0,63}@[a-z0-9]+")),
    (Label.IN_GSTIN, re.compile(r"[0-9]{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]")),
    (Label.IN_VEHICLE_REG, re.compile(_VEHICLE)),
    (Label.IN_IFSC, re.compile(r"[A-Z]{4}0[A-Z0-9]{6}")),
    (Label.IN_PAN, re.compile(r"[A-Z]{5}\d{4}[A-Z]")),
    (Label.IN_VOTER_ID, re.compile(r"[A-Z]{3}\d{7}")),
    (Label.IN_PASSPORT, re.compile(r"[A-Z]\d{7}")),
    (Label.DATE_OF_BIRTH, re.compile(_DOB)),
    (Label.IN_AADHAAR, re.compile(r"XXXX XXXX \d{4}|\d{4} \d{4} \d{4}|\d{12}")),
    (Label.IN_MOBILE, re.compile(_MOBILE)),
    (Label.IN_PINCODE, re.compile(r"[1-9]\d{5}")),
    (Label.IN_BANK_ACCOUNT, re.compile(r"\d{9,18}")),
)
_PRIORITY = {label: index for index, (label, _) in enumerate(_CANDIDATES)}
_NAME_HINTS: dict[Label, tuple[str, ...]] = {
    Label.IN_AADHAAR: ("aadhaar", "uidai"),
    Label.IN_PAN: ("pan",),
    Label.IN_GSTIN: ("gstin", "gst"),
    Label.IN_UPI_ID: ("upi", "vpa"),
    Label.IN_MOBILE: ("mobile", "phone", "msisdn"),
    Label.IN_PINCODE: ("pincode", "pin_code", "postal"),
    Label.IN_PASSPORT: ("passport",),
    Label.IN_VOTER_ID: ("voter", "epic"),
    Label.IN_IFSC: ("ifsc",),
    Label.IN_VEHICLE_REG: ("vehicle", "reg_no", "registration"),
    Label.IN_BANK_ACCOUNT: ("account", "acct"),
    Label.PERSON_NAME: ("name",),
    Label.POSTAL_ADDRESS: ("address", "addr"),
    Label.EMAIL: ("email", "e-mail"),
    Label.DATE_OF_BIRTH: ("dob", "birth", "date_of_birth"),
}


class Span:
    """A labelled character span inside a string."""

    __slots__ = ("end", "label", "start")

    def __init__(self, label: Label, start: int, end: int) -> None:
        self.label = label
        self.start = start
        self.end = end

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Span):
            return NotImplemented
        return (self.label, self.start, self.end) == (other.label, other.start, other.end)

    def __repr__(self) -> str:
        return f"Span({self.label.value}, {self.start}, {self.end})"


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


class RegexChecksum:
    """Ordered patterns plus validators. ``use_names`` breaks column ties."""

    def __init__(self, *, use_names: bool = False) -> None:
        self.use_names = use_names
        self.name = "regex_checksum+names" if use_names else "regex_checksum"
        self.version = _VERSION

    def classify_values(self, values: list[str]) -> list[Label]:
        return [classify_value(value) for value in values]

    def classify_column(self, name: str, samples: list[str]) -> Label:
        votes = [classify_value(sample) for sample in samples if sample.strip()]
        if not votes:
            return _name_label(name) if self.use_names else Label.NONE
        counts = Counter(votes)
        best = max(counts.values())
        tied = [label for label, count in counts.items() if count == best]
        if len(tied) == 1:
            return tied[0]
        if self.use_names:
            hinted = [label for label in tied if _name_matches(name, label)]
            if len(hinted) == 1:
                return hinted[0]
        return Label.NONE


def find(text: str) -> list[Span]:
    """Return non-overlapping labelled spans, skipping timestamps, UUIDs, and inner tokens."""
    blocked = [
        (match.start(), match.end())
        for pattern in (_ISO_TIMESTAMP, _UUID)
        for match in pattern.finditer(text)
    ]
    found: list[Span] = []
    for label, pattern in _CANDIDATES:
        validator = VALIDATORS[label]
        for match in pattern.finditer(text):
            if not validator(match.group()):
                continue
            if _inside_longer_token(text, match.start(), match.end()):
                continue
            if any(_overlaps(match.start(), match.end(), start, end) for start, end in blocked):
                continue
            found.append(Span(label, match.start(), match.end()))
    found.sort(key=lambda span: (span.start, _PRIORITY[span.label], -(span.end - span.start)))
    kept: list[Span] = []
    for span in found:
        if any(_overlaps(span.start, span.end, earlier.start, earlier.end) for earlier in kept):
            continue
        kept.append(span)
    return kept


def classify_value(value: str) -> Label:
    """Classify one value as a whole token, using the same order as ``find``."""
    text = value.strip()
    if not text:
        return Label.NONE
    spans = find(text)
    covering = [span for span in spans if span.start == 0 and span.end == len(text)]
    if covering:
        return min(covering, key=lambda span: _PRIORITY[span.label]).label
    return Label.NONE


def mask(text: str, token_style: str = "typed") -> str:
    """Replace detected spans. ``typed`` writes ``«in_aadhaar»`` and keeps the rest."""
    if token_style != "typed":
        raise ValueError("token_style must be 'typed'")
    spans = find(text)
    rendered = text
    for span in sorted(spans, key=lambda item: item.start, reverse=True):
        token = f"«{span.label.value.lower()}»"
        rendered = rendered[: span.start] + token + rendered[span.end :]
    return rendered


def detector_by_name(name: str) -> RegexChecksum:
    if name == "regex_checksum":
        return RegexChecksum()
    if name == "regex_checksum+names":
        return RegexChecksum(use_names=True)
    raise ValueError(f"unknown detector {name}")


def _inside_longer_token(text: str, start: int, end: int) -> bool:
    before = start > 0 and text[start - 1].isalnum() and text[start].isalnum()
    after = end < len(text) and text[end - 1].isalnum() and text[end].isalnum()
    return before or after


def _overlaps(start: int, end: int, other_start: int, other_end: int) -> bool:
    return start < other_end and other_start < end


def _name_matches(column: str, label: Label) -> bool:
    tokens = re.split(r"[^a-z0-9]+", column.lower())
    return any(hint in tokens for hint in _NAME_HINTS.get(label, ()))


def _name_label(column: str) -> Label:
    matches = [label for label in _NAME_HINTS if _name_matches(column, label)]
    if len(matches) == 1:
        return matches[0]
    return Label.NONE
