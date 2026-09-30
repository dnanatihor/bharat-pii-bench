# 0003 — Phase 2 dataset shape

- Status: accepted
- Date: 2026-09-30

## Context

SPEC.md §4 asks for seed-stable T1 and T2 datasets, a 20/80 dev/test split, and three name conditions on every T2 column. It does not say whether the split is global or per label, or whether the three named copies share values.

## Options considered

1. Shuffle the whole T1 set once and cut 20/80 globally.
2. Split inside each label so every label keeps the same ratio in dev and test.
3. Generate three independent T2 columns per label.
4. Generate one value list per label and store it under all three names.

## Decision

Split inside each label with the dataset seed. Build one T2 value list per label, including the configured null, blank, and malformed cells, and repeat it under truthful, obfuscated, and misleading names. PyArrow writes the Parquet; that module is excluded from mypy because it ships without stubs.

## Consequences

Dev and test stay balanced by label. A later name-sensitivity comparison can hold the cell values fixed. `NONE` columns use the names `notes` and `description` because the config word lists cover personal labels only.
