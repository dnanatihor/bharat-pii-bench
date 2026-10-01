"""Run the baseline detector and write the SPEC.md §6 artefacts."""

import csv
import json
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from bharat_pii.config import BenchConfig, load_bench_config
from bharat_pii.cost import Budget
from bharat_pii.dataset import ColumnExample, build_t1, build_t2, with_seed
from bharat_pii.detect import Detector, detector_by_name
from bharat_pii.labels import Label
from bharat_pii.metrics import (
    hard_negative_false_positive_rate,
    name_sensitivity,
    percentile,
    score,
)
from bharat_pii.plots import plot_confusion


@dataclass(frozen=True, slots=True)
class RunPaths:
    run_id: str
    directory: Path


def run_baseline(
    config: BenchConfig,
    *,
    detectors: tuple[str, ...] = ("regex_checksum",),
    tasks: tuple[str, ...] = ("t1", "t2"),
    split: str = "test",
    out_root: Path = Path("results"),
    budget_usd: float | None = None,
) -> RunPaths:
    """Score T1 and T2 and write metrics, a report, a confusion plot, and run.json."""
    run_id = uuid.uuid4().hex[:12]
    directory = out_root / run_id
    plots = directory / "plots"
    plots.mkdir(parents=True, exist_ok=True)
    t1 = tuple(row for row in build_t1(config) if row.split == split) if "t1" in tasks else ()
    t2 = build_t2(config) if "t2" in tasks else ()
    rows: list[dict[str, str]] = []
    sections: list[str] = [
        "# Benchmark report",
        "",
        f"Split: `{split}`. Seed: `{config.seed}`.",
        "",
    ]
    budget = Budget(config.budget_usd if budget_usd is None else budget_usd)
    loaded: list[Detector] = []
    for detector_name in detectors:
        detector = detector_by_name(detector_name, budget=budget)
        loaded.append(detector)
        sections.append(f"## {detector.name} {detector.version}")
        sections.append("")
        active = _active_recognizers(detector)
        if active:
            sections.append("### Active Presidio recognizers")
            sections.append("")
            sections.extend(f"- {recognizer}" for recognizer in active)
            sections.append("")
        if t1:
            values = [row.value for row in t1]
            predicted, per_thousand = _classify_timed(detector, values)
            card = score([row.label for row in t1], predicted)
            flags = [row.hard_negative for row in t1]
            fpr = hard_negative_false_positive_rate(flags, predicted)
            plot = plots / f"confusion_{detector.name}_t1.png"
            plot_confusion(card.confusion, plot)
            sections.append(f"- macro-F1: {card.macro_f1:.4f}")
            sections.append(f"- micro-F1: {card.micro_f1:.4f}")
            sections.append(f"- hard-negative false-positive rate: {fpr:.4f}")
            sections.append(f"- latency p50 per 1,000 values: {per_thousand['p50']:.6f}s")
            sections.append(f"- latency p95 per 1,000 values: {per_thousand['p95']:.6f}s")
            cost = _cost_usd(detector)
            if cost is not None and values:
                per_thousand_cost = cost / len(values) * 1000
                sections.append(f"- cost per 1,000 values: ${per_thousand_cost:.6f}")
            sections.append("")
            for item in card.per_label:
                rows.append(
                    {
                        "detector": detector.name,
                        "task": "t1",
                        "label": item.label.value,
                        "precision": f"{item.precision:.6f}",
                        "recall": f"{item.recall:.6f}",
                        "f1": f"{item.f1:.6f}",
                        "support": str(item.support),
                    }
                )
        if t2:
            _write_t2(detector, t2, rows, sections)
    (directory / "report.md").write_text("\n".join(sections) + "\n", encoding="utf-8")
    _write_csv(directory / "metrics.csv", rows)
    recognizers = [name for detector in loaded for name in _active_recognizers(detector)]
    model_ids = [model_id for detector in loaded if (model_id := _model_id(detector))]
    prompt_versions = [version for detector in loaded if (version := _prompt_version(detector))]
    (directory / "run.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "seed": config.seed,
                "split": split,
                "detectors": list(detectors),
                "versions": {detector.name: detector.version for detector in loaded},
                "model_ids": model_ids,
                "prompt_version": prompt_versions[0] if prompt_versions else None,
                "active_presidio_recognizers": recognizers,
                "cost_usd": budget.spent_usd,
                "budget_usd": budget.limit_usd,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return RunPaths(run_id, directory)


def default_config(seed: int | None = None) -> BenchConfig:
    config = load_bench_config()
    if seed is None:
        return config
    return with_seed(config, seed)


def _write_t2(
    detector: Detector,
    columns: tuple[ColumnExample, ...],
    rows: list[dict[str, str]],
    sections: list[str],
) -> None:
    by_condition: dict[str, list[tuple[Label, Label]]] = defaultdict(list)
    for column in columns:
        predicted = detector.classify_column(column.name, [cell or "" for cell in column.values])
        by_condition[column.name_condition].append((column.label, predicted))
    f1_by_condition: dict[str, float] = {}
    for condition, pairs in by_condition.items():
        card = score([actual for actual, _ in pairs], [guess for _, guess in pairs])
        f1_by_condition[condition] = card.macro_f1
        rows.append(
            {
                "detector": detector.name,
                "task": "t2",
                "label": condition,
                "precision": "",
                "recall": "",
                "f1": f"{card.macro_f1:.6f}",
                "support": str(len(pairs)),
            }
        )
    drops = name_sensitivity(f1_by_condition)
    sections.append("### Name sensitivity (T2 macro-F1)")
    sections.append("")
    for key, value in drops.items():
        sections.append(f"- {key}: {value:.4f}")
    sections.append("")


def _classify_timed(
    detector: Detector,
    values: list[str],
) -> tuple[list[Label], dict[str, float]]:
    predicted: list[Label] = []
    seconds_per_thousand: list[float] = []
    chunk = 200
    for start in range(0, len(values), chunk):
        batch = values[start : start + chunk]
        started = time.perf_counter()
        predicted.extend(detector.classify_values(batch))
        elapsed = time.perf_counter() - started
        seconds_per_thousand.append(elapsed / len(batch) * 1000)
    return predicted, {
        "p50": percentile(seconds_per_thousand, 50),
        "p95": percentile(seconds_per_thousand, 95),
    }


def _active_recognizers(detector: Detector) -> tuple[str, ...]:
    raw = getattr(detector, "active_recognizers", ())
    if not isinstance(raw, tuple):
        return ()
    return tuple(str(item) for item in raw)


def _cost_usd(detector: Detector) -> float | None:
    raw = getattr(detector, "cost_usd", None)
    if isinstance(raw, int | float):
        return float(raw)
    return None


def _prompt_version(detector: Detector) -> str:
    raw = getattr(detector, "prompt_version", "")
    return raw if isinstance(raw, str) else ""


def _model_id(detector: Detector) -> str:
    raw = getattr(detector, "model_id", "")
    return raw if isinstance(raw, str) else ""


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = ["detector", "task", "label", "precision", "recall", "f1", "support"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
