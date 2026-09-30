"""Phase 2: seed-stable datasets and name conditions on every T2 column."""

from dataclasses import replace
from pathlib import Path

from bharat_pii.cli import main
from bharat_pii.config import load_bench_config
from bharat_pii.dataset import build_t1, build_t2, with_seed
from bharat_pii.labels import Label
from bharat_pii.validate import VALIDATORS


def _small():
    config = load_bench_config()
    return replace(
        config,
        seed=42,
        per_label_count=10,
        none_count=10,
        column_sample_size=20,
    )


def test_same_seed_builds_identical_datasets() -> None:
    config = _small()
    assert build_t1(config) == build_t1(config)
    assert build_t2(config) == build_t2(with_seed(config, config.seed))
    other = with_seed(config, config.seed + 1)
    assert build_t1(config) != build_t1(other)


def test_t1_counts_splits_and_hard_negative_half() -> None:
    config = _small()
    rows = build_t1(config)
    personal = [label for label in Label if label is not Label.NONE]
    for label in personal:
        group = [row for row in rows if row.label is label]
        assert len(group) == config.per_label_count
        assert sum(row.split == "dev" for row in group) == 2
        assert all(not row.hard_negative for row in group)
    none_rows = [row for row in rows if row.label is Label.NONE]
    assert len(none_rows) == config.none_count
    assert sum(row.hard_negative for row in none_rows) == config.none_count // 2


def test_every_t2_column_has_a_name_condition() -> None:
    columns = build_t2(_small())
    by_label: dict[Label, set[str]] = {}
    for column in columns:
        assert column.name_condition in {"truthful", "obfuscated", "misleading"}
        assert len(column.values) == 20
        by_label.setdefault(column.label, set()).add(column.name_condition)
        if column.name_condition == "truthful" and column.label is Label.IN_AADHAAR:
            assert column.name == "aadhaar_no"
        if column.name_condition == "misleading" and column.label is Label.IN_PAN:
            assert column.name == "customer_ref"
    assert set(by_label) == set(Label)
    expected = {"truthful", "obfuscated", "misleading"}
    assert all(conditions == expected for conditions in by_label.values())


def test_t2_noise_is_null_blank_or_invalid_for_the_label() -> None:
    columns = [column for column in build_t2(_small()) if column.name_condition == "truthful"]
    for column in columns:
        empties = [value for value in column.values if value is None or value == ""]
        assert len(empties) == 1
        if column.label not in VALIDATORS:
            marked = [
                value for value in column.values if isinstance(value, str) and value.endswith("!")
            ]
            assert len(marked) == 1
            continue
        broken = [
            value
            for value in column.values
            if isinstance(value, str) and value != "" and not VALIDATORS[column.label](value)
        ]
        assert len(broken) == 1


def test_generated_directory_is_gitignored() -> None:
    text = Path(".gitignore").read_text(encoding="utf-8")
    assert "data/generated/" in text


def test_generate_cli_writes_parquet(tmp_path: Path) -> None:
    import pyarrow.parquet as pq

    assert main(["generate", "--task", "t2", "--seed", "42", "--out", str(tmp_path)]) == 0
    t2 = pq.read_table(tmp_path / "t2.parquet")
    assert set(t2.column("name_condition").to_pylist()) == {"truthful", "obfuscated", "misleading"}
    again = tmp_path / "again"
    main(["generate", "--task", "t2", "--seed", "42", "--out", str(again)])
    assert pq.read_table(again / "t2.parquet").to_pylist() == t2.to_pylist()
    written = build_t2(with_seed(load_bench_config(), 42))
    assert t2.num_rows == sum(len(column.values) for column in written)
