"""Phase 0: reference lists the spec says the generators read."""

from bharat_pii.reference import (
    load_gst_state_codes,
    load_upi_handles,
    load_vehicle_state_codes,
)

_SPEC_UPI_HANDLES = {
    "okaxis",
    "okhdfcbank",
    "oksbi",
    "okicici",
    "ybl",
    "ibl",
    "axl",
    "paytm",
}


def test_gst_state_codes_cover_the_official_numeric_range() -> None:
    codes = load_gst_state_codes()
    by_code = {row.code: row for row in codes}
    assert set(by_code) == {f"{number:02d}" for number in range(1, 39)}
    assert by_code["07"].name == "Delhi"
    assert by_code["27"].name == "Maharashtra"
    assert by_code["26"].name == "Dadra and Nagar Haveli and Daman and Diu"
    assert by_code["36"].name == "Telangana"
    assert by_code["37"].name == "Andhra Pradesh"
    assert by_code["38"].name == "Ladakh"
    assert by_code["25"].status == "legacy"
    assert by_code["28"].status == "legacy"
    assert by_code["27"].status == "current"
    assert all(row.status in {"current", "legacy"} for row in codes)


def test_upi_handles_include_spec_examples_and_are_tokens() -> None:
    handles = load_upi_handles()
    assert set(handles) >= _SPEC_UPI_HANDLES
    assert len(handles) == len(set(handles))
    assert all(handle.islower() and handle.isalnum() for handle in handles)


def test_vehicle_codes_include_current_states_former_codes_and_bh_series() -> None:
    rows = load_vehicle_state_codes()
    by_code = {row.code: row for row in rows}
    current = {code for code, row in by_code.items() if row.status == "current"}
    former = {code for code, row in by_code.items() if row.status == "former"}
    series = {code for code, row in by_code.items() if row.status == "series"}
    assert {
        "AN",
        "AP",
        "AR",
        "AS",
        "BR",
        "CG",
        "CH",
        "DD",
        "DL",
        "GA",
        "GJ",
        "HP",
        "HR",
        "JH",
        "JK",
        "KA",
        "KL",
        "LA",
        "LD",
        "MH",
        "ML",
        "MN",
        "MP",
        "MZ",
        "NL",
        "OD",
        "PB",
        "PY",
        "RJ",
        "SK",
        "TG",
        "TN",
        "TR",
        "UK",
        "UP",
        "WB",
    } <= current
    assert former == {"UA", "OR", "DN", "TS"}
    assert series == {"BH"}
    assert all(len(code) == 2 and code.isalpha() and code.isupper() for code in by_code)
