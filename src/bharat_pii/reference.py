"""Load public reference lists (state codes and UPI handles)."""

import csv
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path


class ReferenceDataError(ValueError):
    """A reference file is missing or does not match its expected shape."""


@dataclass(frozen=True, slots=True)
class GstStateCode:
    code: str
    name: str
    status: str


@dataclass(frozen=True, slots=True)
class VehicleStateCode:
    code: str
    name: str
    status: str


def project_path(*parts: str) -> Path:
    """Resolve a path from the repository, then from packaged data files."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file():
            candidate = parent.joinpath(*parts)
            if candidate.exists():
                return candidate
    resource = files("bharat_pii").joinpath(*parts)
    if resource.is_file():
        return Path(str(resource))
    raise ReferenceDataError("missing reference file: " + "/".join(parts))


def load_gst_state_codes(path: Path | None = None) -> tuple[GstStateCode, ...]:
    """Load ``data/gst_state_codes.csv``."""
    source = path if path is not None else project_path("data", "gst_state_codes.csv")
    rows: list[GstStateCode] = []
    with source.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["code", "name", "status"]:
            raise ReferenceDataError("gst_state_codes.csv columns must be code,name,status")
        for raw in reader:
            code = raw["code"].strip()
            name = raw["name"].strip()
            status = raw["status"].strip()
            if (
                len(code) != 2
                or not code.isdigit()
                or not name
                or status not in {"current", "legacy"}
            ):
                raise ReferenceDataError(f"invalid GST state row: {code}")
            rows.append(GstStateCode(code=code, name=name, status=status))
    if not rows:
        raise ReferenceDataError("gst_state_codes.csv is empty")
    return tuple(rows)


def load_upi_handles(path: Path | None = None) -> tuple[str, ...]:
    """Load ``data/upi_handles.txt`` (one public PSP suffix per line)."""
    source = path if path is not None else project_path("data", "upi_handles.txt")
    handles: list[str] = []
    for line in source.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        if not text.isalnum() or text != text.lower():
            raise ReferenceDataError(f"invalid UPI handle: {text}")
        handles.append(text)
    if not handles:
        raise ReferenceDataError("upi_handles.txt is empty")
    return tuple(handles)


def load_vehicle_state_codes(path: Path | None = None) -> tuple[VehicleStateCode, ...]:
    """Load ``data/vehicle_state_codes.txt`` (code,name,status)."""
    source = path if path is not None else project_path("data", "vehicle_state_codes.txt")
    rows: list[VehicleStateCode] = []
    allowed = {"current", "former", "series"}
    for line in source.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        code, name, status = _split_vehicle_row(text)
        if len(code) != 2 or not code.isalpha() or code != code.upper() or status not in allowed:
            raise ReferenceDataError(f"invalid vehicle state row: {text}")
        if not name:
            raise ReferenceDataError(f"invalid vehicle state row: {text}")
        rows.append(VehicleStateCode(code=code, name=name, status=status))
    if not rows:
        raise ReferenceDataError("vehicle_state_codes.txt is empty")
    return tuple(rows)


def _split_vehicle_row(text: str) -> tuple[str, str, str]:
    parts = text.split(",")
    if len(parts) != 3:
        raise ReferenceDataError(f"invalid vehicle state row: {text}")
    return parts[0].strip(), parts[1].strip(), parts[2].strip()
