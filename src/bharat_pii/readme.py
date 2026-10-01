"""Rebuild the README leaderboard from committed ``results/`` files."""

import csv
from dataclasses import dataclass
from pathlib import Path

from bharat_pii.labels import Label

START = "<!-- leaderboard:start -->"
END = "<!-- leaderboard:end -->"
_CONDITIONS = ("truthful", "obfuscated", "misleading")


@dataclass(frozen=True, slots=True)
class LeaderRow:
    detector: str
    t1_macro_f1: float | None
    truthful: float | None
    obfuscated: float | None
    misleading: float | None


def update_readme(readme: Path, results: Path) -> str:
    """Replace the marker block. Returns the generated markdown."""
    block = leaderboard(results)
    text = readme.read_text(encoding="utf-8")
    if START not in text or END not in text:
        raise ValueError(f"{readme} is missing leaderboard markers")
    before, rest = text.split(START, maxsplit=1)
    _, after = rest.split(END, maxsplit=1)
    updated = f"{before}{START}\n{block}\n{END}{after}"
    readme.write_text(updated, encoding="utf-8")
    return block


def leaderboard(results: Path) -> str:
    """Markdown table from metrics.csv files. The newest file wins per detector."""
    rows = _rows(results)
    if not rows:
        raise ValueError(f"no metrics.csv under {results}")
    lines = [
        "| Detector | T1 macro-F1 | Truthful | Obfuscated | Misleading "
        "| Drop obfuscated | Drop misleading |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        drop_obfuscated = _drop(row.truthful, row.obfuscated)
        drop_misleading = _drop(row.truthful, row.misleading)
        lines.append(
            "| "
            + " | ".join(
                [
                    row.detector,
                    _cell(row.t1_macro_f1),
                    _cell(row.truthful),
                    _cell(row.obfuscated),
                    _cell(row.misleading),
                    _cell(drop_obfuscated),
                    _cell(drop_misleading),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def _rows(results: Path) -> list[LeaderRow]:
    chosen: dict[str, tuple[float, LeaderRow]] = {}
    for metrics in sorted(results.glob("*/metrics.csv")):
        stamped = metrics.stat().st_mtime
        for detector, row in _summaries(metrics).items():
            current = chosen.get(detector)
            if current is None or stamped >= current[0]:
                chosen[detector] = (stamped, row)
    return [item[1] for item in sorted(chosen.values(), key=lambda item: item[1].detector)]


def _summaries(path: Path) -> dict[str, LeaderRow]:
    grouped: dict[str, list[dict[str, str]]] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            grouped.setdefault(raw["detector"], []).append(raw)
    summaries: dict[str, LeaderRow] = {}
    personal = {label.value for label in Label if label is not Label.NONE}
    for detector, records in grouped.items():
        f1_values = [
            float(record["f1"])
            for record in records
            if record["task"] == "t1" and record["label"] in personal and record["f1"]
        ]
        by_condition = {
            record["label"]: float(record["f1"])
            for record in records
            if record["task"] == "t2" and record["label"] in _CONDITIONS and record["f1"]
        }
        summaries[detector] = LeaderRow(
            detector,
            sum(f1_values) / len(f1_values) if f1_values else None,
            by_condition.get("truthful"),
            by_condition.get("obfuscated"),
            by_condition.get("misleading"),
        )
    return summaries


def _drop(truthful: float | None, other: float | None) -> float | None:
    if truthful is None or other is None:
        return None
    return truthful - other


def _cell(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.4f}"
