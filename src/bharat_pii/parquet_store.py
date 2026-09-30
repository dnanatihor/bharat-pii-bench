"""Parquet output. PyArrow has no type stubs, so this module is unchecked."""

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from bharat_pii.dataset import ColumnExample, ValueExample


def write_parquet(rows: tuple[ValueExample, ...] | tuple[ColumnExample, ...], path: Path) -> None:
    """Write rows to Parquet under ``path`` (parent directories are created)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if rows and isinstance(rows[0], ValueExample):
        values = tuple(row for row in rows if isinstance(row, ValueExample))
        table = pa.table(
            {
                "value": [row.value for row in values],
                "label": [row.label.value for row in values],
                "variant": [row.variant for row in values],
                "split": [row.split for row in values],
                "hard_negative": [row.hard_negative for row in values],
            }
        )
    else:
        columns = tuple(row for row in rows if isinstance(row, ColumnExample))
        column_id: list[str] = []
        name: list[str] = []
        label: list[str] = []
        condition: list[str] = []
        position: list[int] = []
        value: list[str | None] = []
        for column in columns:
            for index, cell in enumerate(column.values):
                column_id.append(f"{column.label.value}:{column.name_condition}")
                name.append(column.name)
                label.append(column.label.value)
                condition.append(column.name_condition)
                position.append(index)
                value.append(cell)
        table = pa.table(
            {
                "column_id": column_id,
                "name": name,
                "label": label,
                "name_condition": condition,
                "position": position,
                "value": value,
            }
        )
    pq.write_table(table, path)
