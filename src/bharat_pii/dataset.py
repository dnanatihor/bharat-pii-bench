"""Build the T1 and T2 datasets described in SPEC.md §4."""

import random
from dataclasses import dataclass, replace

from bharat_pii.config import BenchConfig, NameConditions
from bharat_pii.generate import GENERATORS, HARD_NEGATIVE, Generator
from bharat_pii.labels import Label
from bharat_pii.validate import VALIDATORS

_BY_LABEL: dict[Label, Generator] = {
    generator.label: generator for generator in GENERATORS if generator.label is not Label.NONE
}


@dataclass(frozen=True, slots=True)
class ValueExample:
    value: str
    label: Label
    variant: str
    split: str
    hard_negative: bool


@dataclass(frozen=True, slots=True)
class ColumnExample:
    """One labelled column under one name condition."""

    name: str
    label: Label
    name_condition: str
    values: tuple[str | None, ...]


def build_t1(config: BenchConfig) -> tuple[ValueExample, ...]:
    """Balanced value-level rows, then a seed-stable dev/test split inside each label."""
    rng = random.Random(config.seed)
    grouped: dict[Label, list[tuple[str, str, bool]]] = {}
    for label, generator in _BY_LABEL.items():
        grouped[label] = [
            _record(generator, rng, hard_negative=False) for _ in range(config.per_label_count)
        ]
    n_hard = int(config.none_count * config.hard_negative_fraction + 0.5)
    n_hard = min(n_hard, config.none_count)
    none_rows = [_hard_negative(rng, index) for index in range(n_hard)]
    none_rows.extend(_plain_none(rng) for _ in range(config.none_count - n_hard))
    grouped[Label.NONE] = none_rows
    rows: list[ValueExample] = []
    for label in Label:
        rows.extend(_with_splits(label, grouped[label], config, rng))
    return tuple(rows)


def build_t2(config: BenchConfig) -> tuple[ColumnExample, ...]:
    """One column per label, copied under each name condition.

    The values are shared so later name-sensitivity comparisons differ only in the name.
    """
    rng = random.Random(config.seed)
    columns: list[ColumnExample] = []
    names = config.name_conditions
    for label in Label:
        values = _column_values(label, config, rng)
        for condition in ("truthful", "obfuscated", "misleading"):
            columns.append(
                ColumnExample(
                    name=_column_name(label, condition, names, rng),
                    label=label,
                    name_condition=condition,
                    values=values,
                )
            )
    return tuple(columns)


def with_seed(config: BenchConfig, seed: int) -> BenchConfig:
    return replace(config, seed=seed)


def _record(
    generator: Generator,
    rng: random.Random,
    *,
    hard_negative: bool,
) -> tuple[str, str, bool]:
    sample = generator.generate(rng, None)
    return sample.value, sample.variant, hard_negative


def _hard_negative(rng: random.Random, index: int) -> tuple[str, str, bool]:
    variant = HARD_NEGATIVE.variants[index % len(HARD_NEGATIVE.variants)]
    sample = HARD_NEGATIVE.generate(rng, variant)
    return sample.value, sample.variant, True


def _plain_none(rng: random.Random) -> tuple[str, str, bool]:
    return f"note-{rng.randrange(1_000_000)}", "plain", False


def _with_splits(
    label: Label,
    group: list[tuple[str, str, bool]],
    config: BenchConfig,
    rng: random.Random,
) -> list[ValueExample]:
    order = list(range(len(group)))
    rng.shuffle(order)
    n_dev = int(len(group) * config.dev_fraction + 1e-9)
    dev_indexes = set(order[:n_dev])
    rows: list[ValueExample] = []
    for index, (value, variant, hard_negative) in enumerate(group):
        split = "dev" if index in dev_indexes else "test"
        rows.append(
            ValueExample(
                value=value,
                label=label,
                variant=variant,
                split=split,
                hard_negative=hard_negative,
            )
        )
    return rows


def _column_values(label: Label, config: BenchConfig, rng: random.Random) -> tuple[str | None, ...]:
    size = config.column_sample_size
    n_null = int(size * config.noise.null_or_blank + 0.5)
    n_bad = int(size * config.noise.malformed + 0.5)
    indexes = list(range(size))
    rng.shuffle(indexes)
    null_at = set(indexes[:n_null])
    bad_at = set(indexes[n_null : n_null + n_bad])
    cells: list[str | None] = []
    for index in range(size):
        if index in null_at:
            cells.append(None if index % 2 == 0 else "")
            continue
        generated = _cell(label, rng)
        cells.append(_break(label, generated) if index in bad_at else generated)
    return tuple(cells)


def _cell(label: Label, rng: random.Random) -> str:
    if label is Label.NONE:
        return _plain_none(rng)[0]
    return _BY_LABEL[label].generate(rng, None).value


def _break(label: Label, value: str) -> str:
    broken = f"{value}!"
    validator = VALIDATORS.get(label)
    if validator is None or not validator(broken):
        return broken
    return "??"


def _column_name(
    label: Label,
    condition: str,
    names: NameConditions,
    rng: random.Random,
) -> str:
    if condition == "obfuscated":
        return rng.choice(names.obfuscated)
    pool = names.truthful if condition == "truthful" else names.misleading
    if label is Label.NONE:
        return "notes" if condition == "truthful" else "description"
    return rng.choice(pool[label])
