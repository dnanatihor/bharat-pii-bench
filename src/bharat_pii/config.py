"""Typed models for the YAML files in SPEC.md §9."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml

from bharat_pii.labels import Label
from bharat_pii.reference import project_path


class ConfigError(ValueError):
    """A configuration file is missing a required field or has the wrong type."""


@dataclass(frozen=True, slots=True)
class NoiseRates:
    null_or_blank: float
    malformed: float


@dataclass(frozen=True, slots=True)
class NameConditions:
    truthful: dict[Label, tuple[str, ...]]
    obfuscated: tuple[str, ...]
    misleading: dict[Label, tuple[str, ...]]


@dataclass(frozen=True, slots=True)
class DetectorSettings:
    regex_checksum_enabled: bool
    presidio_enabled: bool
    ner_enabled: bool
    ner_model_id: str
    llm_enabled: bool
    llm_model_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BenchConfig:
    seed: int
    per_label_count: int
    none_count: int
    hard_negative_fraction: float
    dev_fraction: float
    test_fraction: float
    noise: NoiseRates
    column_sample_size: int
    name_conditions: NameConditions
    detectors: DetectorSettings
    budget_usd: float


@dataclass(frozen=True, slots=True)
class ModelPrice:
    input_per_million_usd: float
    output_per_million_usd: float


@dataclass(frozen=True, slots=True)
class PricesConfig:
    models: dict[str, ModelPrice]


def load_bench_config(path: Path | None = None) -> BenchConfig:
    """Load ``configs/bench.yaml``."""
    source = path if path is not None else project_path("configs", "bench.yaml")
    raw = _load_mapping(source)
    _reject_unknown(raw, _BENCH_KEYS, source)
    splits = _mapping(raw, "splits", source)
    _reject_unknown(splits, {"dev", "test"}, source)
    noise = _mapping(raw, "noise", source)
    _reject_unknown(noise, {"null_or_blank", "malformed"}, source)
    names = _mapping(raw, "name_conditions", source)
    _reject_unknown(names, {"truthful", "obfuscated", "misleading"}, source)
    detectors = _mapping(raw, "detectors", source)
    _reject_unknown(detectors, {"regex_checksum", "presidio", "ner", "llm"}, source)
    dev_fraction = _fraction(_number(splits, "dev", source))
    test_fraction = _fraction(_number(splits, "test", source))
    if abs((dev_fraction + test_fraction) - 1.0) > 1e-9:
        raise ConfigError(f"{source}: dev and test fractions must sum to 1")
    return BenchConfig(
        seed=_positive_int(raw, "seed", source),
        per_label_count=_positive_int(raw, "per_label_count", source),
        none_count=_positive_int(raw, "none_count", source),
        hard_negative_fraction=_fraction(_number(raw, "hard_negative_fraction", source)),
        dev_fraction=dev_fraction,
        test_fraction=test_fraction,
        noise=NoiseRates(
            null_or_blank=_fraction(_number(noise, "null_or_blank", source)),
            malformed=_fraction(_number(noise, "malformed", source)),
        ),
        column_sample_size=_positive_int(raw, "column_sample_size", source),
        name_conditions=NameConditions(
            truthful=_label_word_lists(_mapping(names, "truthful", source), source),
            obfuscated=_word_list(names, "obfuscated", source),
            misleading=_label_word_lists(_mapping(names, "misleading", source), source),
        ),
        detectors=_detector_settings(detectors, source),
        budget_usd=_non_negative(_number(raw, "budget_usd", source), source, "budget_usd"),
    )


def load_label_map(path: Path) -> dict[str, Label]:
    """Load a recognizer-or-model label map. Values must be taxonomy labels."""
    raw = _load_mapping(path)
    mapped: dict[str, Label] = {}
    for key, value in raw.items():
        if not isinstance(value, str):
            raise ConfigError(f"{path}: label for {key} must be a string")
        try:
            mapped[key] = Label(value)
        except ValueError as exc:
            raise ConfigError(f"{path}: unknown label {value}") from exc
    return mapped


def load_prices(path: Path | None = None) -> PricesConfig:
    """Load ``configs/prices.yaml`` (USD per one million tokens)."""
    source = path if path is not None else project_path("configs", "prices.yaml")
    raw = _load_mapping(source)
    _reject_unknown(raw, {"models"}, source)
    models_raw = raw.get("models", {})
    if not isinstance(models_raw, dict):
        raise ConfigError(f"{source}: models must be a mapping")
    models: dict[str, ModelPrice] = {}
    for key, value in models_raw.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            raise ConfigError(f"{source}: invalid price entry {key}")
        entry = cast(dict[object, object], value)
        models[key] = ModelPrice(
            input_per_million_usd=_price_field(entry, "input_per_million_usd", source),
            output_per_million_usd=_price_field(entry, "output_per_million_usd", source),
        )
    return PricesConfig(models=models)


_BENCH_KEYS = {
    "seed",
    "per_label_count",
    "none_count",
    "hard_negative_fraction",
    "splits",
    "noise",
    "column_sample_size",
    "name_conditions",
    "detectors",
    "budget_usd",
}


def _detector_settings(raw: dict[str, object], source: Path) -> DetectorSettings:
    regex = _mapping(raw, "regex_checksum", source)
    presidio = _mapping(raw, "presidio", source)
    ner = _mapping(raw, "ner", source)
    llm = _mapping(raw, "llm", source)
    _reject_unknown(regex, {"enabled"}, source)
    _reject_unknown(presidio, {"enabled"}, source)
    _reject_unknown(ner, {"enabled", "model_id"}, source)
    _reject_unknown(llm, {"enabled", "model_ids"}, source)
    model_ids = llm.get("model_ids", [])
    if not isinstance(model_ids, list) or not all(isinstance(item, str) for item in model_ids):
        raise ConfigError(f"{source}: llm.model_ids must be a list of strings")
    model_id = ner.get("model_id", "")
    if not isinstance(model_id, str):
        raise ConfigError(f"{source}: ner.model_id must be a string")
    return DetectorSettings(
        regex_checksum_enabled=_bool(regex, "enabled", source),
        presidio_enabled=_bool(presidio, "enabled", source),
        ner_enabled=_bool(ner, "enabled", source),
        ner_model_id=model_id,
        llm_enabled=_bool(llm, "enabled", source),
        llm_model_ids=tuple(model_ids),
    )


def _label_word_lists(raw: dict[str, object], source: Path) -> dict[Label, tuple[str, ...]]:
    listed: dict[Label, tuple[str, ...]] = {}
    for key, value in raw.items():
        try:
            label = Label(key)
        except ValueError as exc:
            raise ConfigError(f"{source}: unknown label {key}") from exc
        if (
            not isinstance(value, list)
            or not value
            or not all(isinstance(item, str) and item for item in value)
        ):
            raise ConfigError(f"{source}: {key} must be a non-empty list of strings")
        listed[label] = tuple(value)
    return listed


def _word_list(raw: dict[str, object], key: str, source: Path) -> tuple[str, ...]:
    value = raw.get(key)
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(item, str) and item for item in value)
    ):
        raise ConfigError(f"{source}: {key} must be a non-empty list of strings")
    return tuple(value)


def _load_mapping(path: Path) -> dict[str, object]:
    document: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    if document is None:
        document = {}
    if not isinstance(document, dict):
        raise ConfigError(f"{path} must be a mapping")
    mapping: dict[str, object] = {}
    for key, value in document.items():
        if not isinstance(key, str):
            raise ConfigError(f"{path}: keys must be strings")
        mapping[key] = cast(object, value)
    return mapping


def _mapping(raw: dict[str, object], key: str, source: Path) -> dict[str, object]:
    value = raw.get(key)
    if not isinstance(value, dict):
        raise ConfigError(f"{source}: {key} must be a mapping")
    nested: dict[str, object] = {}
    for item_key, item_value in value.items():
        if not isinstance(item_key, str):
            raise ConfigError(f"{source}: {key} keys must be strings")
        nested[item_key] = cast(object, item_value)
    return nested


def _reject_unknown(raw: dict[str, object], allowed: set[str], source: Path) -> None:
    unknown = set(raw) - allowed
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ConfigError(f"{source}: unknown keys: {names}")


def _number(raw: dict[str, object], key: str, source: Path) -> float:
    value = raw.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{source}: {key} must be a number")
    return float(value)


def _positive_int(raw: dict[str, object], key: str, source: Path) -> int:
    value = raw.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ConfigError(f"{source}: {key} must be a positive integer")
    return value


def _bool(raw: dict[str, object], key: str, source: Path) -> bool:
    value = raw.get(key)
    if not isinstance(value, bool):
        raise ConfigError(f"{source}: {key} must be a boolean")
    return value


def _fraction(value: float) -> float:
    if value < 0.0 or value > 1.0:
        raise ConfigError(f"fraction out of range: {value}")
    return value


def _non_negative(value: float, source: Path, key: str) -> float:
    if value < 0.0:
        raise ConfigError(f"{source}: {key} must be >= 0")
    return value


def _price_field(raw: dict[object, object], key: str, source: Path) -> float:
    value = raw.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or float(value) < 0.0:
        raise ConfigError(f"{source}: {key} must be a non-negative number")
    return float(value)
