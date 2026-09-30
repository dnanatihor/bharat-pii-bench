"""Validators for Indian identifier formats.

These functions check shape and checksums. They do not decide whether a
value was generated as a hard negative; that label is a generation choice.
"""

import functools
import re
import unicodedata
from collections.abc import Callable
from datetime import datetime

from bharat_pii.labels import Label
from bharat_pii.reference import load_gst_state_codes, load_upi_handles, load_vehicle_state_codes

_GSTIN_CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_PAN_TYPES = frozenset("PCHFATBLJG")
_ENGLISH_MONTHS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)
_HINDI_MONTHS = (
    "जनवरी",
    "फरवरी",
    "मार्च",
    "अप्रैल",
    "मई",
    "जून",
    "जुलाई",
    "अगस्त",
    "सितंबर",
    "अक्टूबर",
    "नवंबर",
    "दिसंबर",
)
_VEHICLE_SERIES = "ABCDEFGHJKLMNPQRSTUVWXYZ"

_D = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
    (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
    (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
    (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
    (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
    (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
    (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
    (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
)
_P = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
    (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
    (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
    (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
    (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
)
_INV = (0, 4, 3, 2, 1, 5, 6, 7, 8, 9)


def verhoeff_check_digit(digits: str) -> str:
    """Return the Verhoeff check digit for ``digits`` (not including it)."""
    checksum = 0
    for index, char in enumerate(reversed(digits)):
        checksum = _D[checksum][_P[(index + 1) % 8][int(char)]]
    return str(_INV[checksum])


def verhoeff_valid(digits: str) -> bool:
    """Return whether ``digits`` carries a valid Verhoeff check digit."""
    if not digits.isdigit():
        return False
    checksum = 0
    for index, char in enumerate(reversed(digits)):
        checksum = _D[checksum][_P[index % 8][int(char)]]
    return checksum == 0


def gstin_check_character(body: str) -> str:
    """Check character for the first 14 GSTIN characters.

    Index *i* is zero-based from the left. Even indexes use factor 1 and odd
    indexes use factor 2, which matches the GSTN walk from the right.
    """
    if len(body) != 14 or any(char not in _GSTIN_CHARSET for char in body):
        raise ValueError("GSTIN body must be 14 characters from the GSTIN charset")
    total = 0
    for index, char in enumerate(body):
        factor = 1 if index % 2 == 0 else 2
        value = _GSTIN_CHARSET.index(char) * factor
        total += value // 36 + value % 36
    return _GSTIN_CHARSET[(36 - total % 36) % 36]


def is_valid_aadhaar(value: str) -> bool:
    """Accept a plain or spaced 12-digit Aadhaar, or a masked ``XXXX XXXX NNNN``."""
    if re.fullmatch(r"XXXX XXXX \d{4}", value):
        return True
    digits = value.replace(" ", "")
    if not re.fullmatch(r"[2-9]\d{11}", digits):
        return False
    if value != digits and not re.fullmatch(r"\d{4} \d{4} \d{4}", value):
        return False
    return verhoeff_valid(digits)


def is_valid_pan(value: str) -> bool:
    """PAN structure, including the holder-type set for the fourth letter."""
    if not re.fullmatch(r"[A-Z]{5}\d{4}[A-Z]", value):
        return False
    return value[3] in _PAN_TYPES


def is_valid_gstin(value: str) -> bool:
    """GSTIN structure, state code, embedded PAN, and check character."""
    if not re.fullmatch(r"[0-9]{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]", value):
        return False
    if value[:2] not in _gst_codes():
        return False
    if not is_valid_pan(value[2:12]):
        return False
    return value[14] == gstin_check_character(value[:14])


def is_valid_upi_id(value: str) -> bool:
    local, separator, handle = value.partition("@")
    if not separator or handle not in _upi_handles():
        return False
    return re.fullmatch(r"[a-z0-9][a-z0-9.]{0,63}", local) is not None and ".." not in local


def is_valid_mobile(value: str) -> bool:
    compact = value.replace(" ", "").replace("-", "")
    if compact.startswith("+91"):
        number = compact[3:]
    elif compact.startswith("0"):
        number = compact[1:]
    else:
        number = compact
    return re.fullmatch(r"[6-9]\d{9}", number) is not None


def is_valid_pincode(value: str) -> bool:
    return re.fullmatch(r"[1-9]\d{5}", value) is not None


def is_valid_passport(value: str) -> bool:
    return re.fullmatch(r"[A-Z]\d{7}", value) is not None


def is_valid_voter_id(value: str) -> bool:
    return re.fullmatch(r"[A-Z]{3}\d{7}", value) is not None


def is_valid_ifsc(value: str) -> bool:
    return re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", value) is not None


def is_valid_vehicle_reg(value: str) -> bool:
    states = "|".join(sorted(_vehicle_states()))
    series = _VEHICLE_SERIES
    state_plate = rf"(?:{states})(?P<sep>[ -]?)\d{{1,2}}(?P=sep)[{series}]{{1,3}}(?P=sep)\d{{4}}"
    bharat = rf"\d{{2}}(?P<sep>[ -]?)BH(?P=sep)\d{{4}}(?P=sep)[{series}]{{1,2}}"
    return re.fullmatch(state_plate, value) is not None or re.fullmatch(bharat, value) is not None


def is_valid_bank_account(value: str) -> bool:
    """9–18 digits. This format overlaps other numeric identifiers."""
    return re.fullmatch(r"\d{9,18}", value) is not None


def is_valid_person_name(value: str) -> bool:
    if len(value) < 2 or any(char.isdigit() for char in value):
        return False
    if not any(char.isalpha() for char in value):
        return False
    return all(_name_character(char) for char in value)


def _name_character(char: str) -> bool:
    if char in " .'’":
        return True
    if char.isalpha():
        return True
    return unicodedata.category(char).startswith("M")


def is_valid_postal_address(value: str) -> bool:
    has_break = " " in value or "," in value
    return len(value) >= 12 and any(char.isalpha() for char in value) and has_break


def is_valid_email(value: str) -> bool:
    return re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", value) is not None


def is_valid_date_of_birth(value: str) -> bool:
    for pattern in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        if _parsed_date(value, pattern):
            return True
    english = "|".join(_ENGLISH_MONTHS)
    hindi = "|".join(_HINDI_MONTHS)
    month_patterns = (
        rf"(\d{{1,2}}) ({english}) (\d{{4}})",
        rf"(\d{{1,2}}) ({hindi}) (\d{{4}})",
    )
    for month_pattern in month_patterns:
        match = re.fullmatch(month_pattern, value)
        if match is None:
            continue
        day = int(match.group(1))
        year = int(match.group(3))
        month_name = match.group(2)
        month = _month_number(month_name)
        if month is not None and _calendar_date(year, month, day):
            return True
    return False


ENGLISH_MONTHS = _ENGLISH_MONTHS
HINDI_MONTHS = _HINDI_MONTHS
VEHICLE_SERIES_LETTERS = _VEHICLE_SERIES

VALIDATORS: dict[Label, Callable[[str], bool]] = {
    Label.IN_AADHAAR: is_valid_aadhaar,
    Label.IN_PAN: is_valid_pan,
    Label.IN_GSTIN: is_valid_gstin,
    Label.IN_UPI_ID: is_valid_upi_id,
    Label.IN_MOBILE: is_valid_mobile,
    Label.IN_PINCODE: is_valid_pincode,
    Label.IN_PASSPORT: is_valid_passport,
    Label.IN_VOTER_ID: is_valid_voter_id,
    Label.IN_IFSC: is_valid_ifsc,
    Label.IN_VEHICLE_REG: is_valid_vehicle_reg,
    Label.IN_BANK_ACCOUNT: is_valid_bank_account,
    Label.PERSON_NAME: is_valid_person_name,
    Label.POSTAL_ADDRESS: is_valid_postal_address,
    Label.EMAIL: is_valid_email,
    Label.DATE_OF_BIRTH: is_valid_date_of_birth,
}


def _month_number(name: str) -> int | None:
    if name in _ENGLISH_MONTHS:
        return _ENGLISH_MONTHS.index(name) + 1
    if name in _HINDI_MONTHS:
        return _HINDI_MONTHS.index(name) + 1
    return None


def _parsed_date(value: str, pattern: str) -> bool:
    try:
        parsed = datetime.strptime(value, pattern)
    except ValueError:
        return False
    return parsed.strftime(pattern) == value or _unpadded_match(value, parsed, pattern)


def _unpadded_match(value: str, parsed: datetime, pattern: str) -> bool:
    if pattern == "%d/%m/%Y":
        return value == f"{parsed.day}/{parsed.month}/{parsed.year}"
    if pattern == "%d-%m-%Y":
        return value == f"{parsed.day}-{parsed.month}-{parsed.year}"
    return False


def _calendar_date(year: int, month: int, day: int) -> bool:
    try:
        datetime(year, month, day)
    except ValueError:
        return False
    return 1900 <= year <= 2100


@functools.lru_cache(maxsize=1)
def _gst_codes() -> frozenset[str]:
    return frozenset(row.code for row in load_gst_state_codes())


@functools.lru_cache(maxsize=1)
def _upi_handles() -> frozenset[str]:
    return frozenset(load_upi_handles())


@functools.lru_cache(maxsize=1)
def _vehicle_states() -> frozenset[str]:
    return frozenset(row.code for row in load_vehicle_state_codes() if row.status != "series")
