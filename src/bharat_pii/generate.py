"""Synthetic identifier generators. All randomness comes from the supplied RNG."""

import random
import string
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any

from bharat_pii.labels import Label
from bharat_pii.reference import load_gst_state_codes, load_upi_handles, load_vehicle_state_codes
from bharat_pii.validate import (
    ENGLISH_MONTHS,
    HINDI_MONTHS,
    VEHICLE_SERIES_LETTERS,
    gstin_check_character,
    verhoeff_check_digit,
)

_LETTERS = string.ascii_uppercase
_PAN_TYPES = "PCHFATBLJG"
_GSTIN_ENTITY = "123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_PAN_SKU_LETTERS = "DEIKMNOQRSUVWXYZ"


@dataclass(frozen=True, slots=True)
class Sample:
    """One synthetic value and the label the generator assigned."""

    value: str
    label: Label
    variant: str
    meta: Mapping[str, object]


class Generator:
    """A labelled generator with ``generate(rng, variant)`` from SPEC.md §3."""

    def __init__(
        self,
        label: Label,
        variants: tuple[str, ...],
        build: Callable[[random.Random, str], Sample],
    ) -> None:
        self.label = label
        self.variants = variants
        self._build = build

    def generate(self, rng: random.Random, variant: str | None = None) -> Sample:
        chosen = rng.choice(self.variants) if variant is None else variant
        if chosen not in self.variants:
            raise ValueError(f"unknown variant {chosen!r} for {self.label}")
        sample = self._build(rng, chosen)
        if sample.label is not self.label or sample.variant != chosen:
            raise RuntimeError(f"{self.label} generator returned an inconsistent sample")
        return sample


def _meta(**items: object) -> Mapping[str, object]:
    return MappingProxyType(items)


def _aadhaar_number(rng: random.Random) -> str:
    body = str(rng.randrange(2, 10)) + "".join(str(rng.randrange(10)) for _ in range(10))
    return body + verhoeff_check_digit(body)


def _build_aadhaar(rng: random.Random, variant: str) -> Sample:
    number = _aadhaar_number(rng)
    if variant == "plain":
        return Sample(number, Label.IN_AADHAAR, variant, _meta())
    spaced = f"{number[0:4]} {number[4:8]} {number[8:12]}"
    if variant == "spaced":
        return Sample(spaced, Label.IN_AADHAAR, variant, _meta())
    masked = f"XXXX XXXX {number[8:12]}"
    return Sample(masked, Label.IN_AADHAAR, variant, _meta(masked=True))


def _pan_value(rng: random.Random) -> tuple[str, Mapping[str, object]]:
    head = "".join(rng.choice(_LETTERS) for _ in range(3))
    holder = rng.choice(_PAN_TYPES)
    meta: Mapping[str, object] = _meta()
    if holder == "P":
        tail = "".join(rng.choice(_LETTERS) for _ in range(rng.randint(3, 7)))
        surname = rng.choice(_LETTERS) + tail
        fifth = surname[0]
        meta = _meta(surname=surname)
    else:
        fifth = rng.choice(_LETTERS)
    digits = f"{rng.randrange(10000):04d}"
    tail = rng.choice(_LETTERS)
    return f"{head}{holder}{fifth}{digits}{tail}", meta


def _build_pan(rng: random.Random, variant: str) -> Sample:
    value, meta = _pan_value(rng)
    return Sample(value, Label.IN_PAN, variant, meta)


def _build_gstin(rng: random.Random, variant: str) -> Sample:
    state = rng.choice(tuple(row.code for row in load_gst_state_codes()))
    pan, _meta_unused = _pan_value(rng)
    entity = rng.choice(_GSTIN_ENTITY)
    body = f"{state}{pan}{entity}Z"
    return Sample(body + gstin_check_character(body), Label.IN_GSTIN, variant, _meta())


def _build_upi(rng: random.Random, variant: str) -> Sample:
    handle = rng.choice(load_upi_handles())
    if variant == "mobile":
        local = _mobile_digits(rng)
    elif variant == "dotted_name":
        local = f"{_token(rng, 3, 8)}.{_token(rng, 3, 10)}"
    else:
        local = f"{_token(rng, 1, 1)}{_token(rng, 3, 8)}{rng.randrange(100):02d}"
    return Sample(f"{local}@{handle}", Label.IN_UPI_ID, variant, _meta())


def _mobile_digits(rng: random.Random) -> str:
    return str(rng.randrange(6, 10)) + "".join(str(rng.randrange(10)) for _ in range(9))


def _build_mobile(rng: random.Random, variant: str) -> Sample:
    number = _mobile_digits(rng)
    rendered = {
        "plain": number,
        "plus91_spaced": f"+91 {number[:5]} {number[5:]}",
        "plus91_dash": f"+91-{number}",
        "trunk_zero": f"0{number}",
        "spaced": f"{number[:5]} {number[5:]}",
    }[variant]
    return Sample(rendered, Label.IN_MOBILE, variant, _meta())


def _build_pincode(rng: random.Random, variant: str) -> Sample:
    value = str(rng.randrange(1, 10)) + f"{rng.randrange(100000):05d}"
    return Sample(value, Label.IN_PINCODE, variant, _meta())


def _build_passport(rng: random.Random, variant: str) -> Sample:
    value = rng.choice(_LETTERS) + f"{rng.randrange(10**7):07d}"
    return Sample(value, Label.IN_PASSPORT, variant, _meta())


def _build_voter_id(rng: random.Random, variant: str) -> Sample:
    letters = "".join(rng.choice(_LETTERS) for _ in range(3))
    return Sample(f"{letters}{rng.randrange(10**7):07d}", Label.IN_VOTER_ID, variant, _meta())


def _build_ifsc(rng: random.Random, variant: str) -> Sample:
    bank = "".join(rng.choice(_LETTERS) for _ in range(4))
    tail = "".join(rng.choice(_LETTERS + string.digits) for _ in range(6))
    return Sample(f"{bank}0{tail}", Label.IN_IFSC, variant, _meta())


def _build_vehicle(rng: random.Random, variant: str) -> Sample:
    if variant == "bh":
        year = f"{rng.randrange(100):02d}"
        number = f"{rng.randrange(10000):04d}"
        series = "".join(rng.choice(VEHICLE_SERIES_LETTERS) for _ in range(2))
        return Sample(f"{year} BH {number} {series}", Label.IN_VEHICLE_REG, variant, _meta())
    states = tuple(row.code for row in load_vehicle_state_codes() if row.status != "series")
    state = rng.choice(states)
    district = f"{rng.randrange(1, 100):02d}"
    series = "".join(rng.choice(VEHICLE_SERIES_LETTERS) for _ in range(rng.choice((1, 2))))
    number = f"{rng.randrange(10000):04d}"
    separator = {"plain": "", "spaced": " ", "hyphen": "-"}[variant]
    value = separator.join((state, district, series, number))
    return Sample(value, Label.IN_VEHICLE_REG, variant, _meta())


def _build_bank_account(rng: random.Random, variant: str) -> Sample:
    length = rng.randrange(9, 19)
    value = "".join(str(rng.randrange(10)) for _ in range(length))
    return Sample(value, Label.IN_BANK_ACCOUNT, variant, _meta())


def _build_name(rng: random.Random, variant: str) -> Sample:
    locale = "en_IN" if variant == "latin" else "hi_IN"
    value = _faker_call(rng, locale, "name")
    return Sample(value, Label.PERSON_NAME, variant, _meta(script=variant))


def _build_address(rng: random.Random, variant: str) -> Sample:
    locale = "en_IN" if variant == "latin" else "hi_IN"
    value = _faker_call(rng, locale, "address").replace("\n", ", ")
    return Sample(value, Label.POSTAL_ADDRESS, variant, _meta(script=variant))


def _build_email(rng: random.Random, variant: str) -> Sample:
    local = f"{_token(rng, 3, 10)}.{_token(rng, 3, 10)}"
    return Sample(f"{local}@example.com", Label.EMAIL, variant, _meta())


def _build_dob(rng: random.Random, variant: str) -> Sample:
    year = rng.randrange(1940, 2011)
    month = rng.randrange(1, 13)
    day = rng.randrange(1, 29)
    if variant == "slash":
        value = f"{day:02d}/{month:02d}/{year:04d}"
    elif variant == "dash":
        value = f"{day:02d}-{month:02d}-{year:04d}"
    elif variant == "iso":
        value = f"{year:04d}-{month:02d}-{day:02d}"
    elif variant == "en_month":
        value = f"{day} {ENGLISH_MONTHS[month - 1]} {year}"
    else:
        value = f"{day} {HINDI_MONTHS[month - 1]} {year}"
    return Sample(value, Label.DATE_OF_BIRTH, variant, _meta())


def _build_hard_negative(rng: random.Random, variant: str) -> Sample:
    value = {
        "aadhaar": _bad_aadhaar(rng),
        "utr": "".join(rng.choice(_LETTERS + string.digits) for _ in range(22)),
        "otp": f"{rng.randrange(10**6):06d}",
        "pan_sku": _pan_sku(rng),
        "invoice": f"INV-{rng.randrange(2018, 2027)}-{rng.randrange(100000):05d}",
        "ipv4": f"192.0.2.{rng.randrange(1, 255)}",
        "currency": f"₹{rng.randrange(1, 100000):,}",
        "timestamp": _timestamp(rng),
        "gstin": _bad_gstin(rng),
    }[variant]
    return Sample(value, Label.NONE, variant, _meta(negative=variant))


def _bad_aadhaar(rng: random.Random) -> str:
    number = _aadhaar_number(rng)
    last = (int(number[-1]) + 1 + rng.randrange(9)) % 10
    return number[:-1] + str(last)


def _pan_sku(rng: random.Random) -> str:
    head = "".join(rng.choice(_LETTERS) for _ in range(3))
    fourth = rng.choice(_PAN_SKU_LETTERS)
    rest = rng.choice(_LETTERS) + f"{rng.randrange(10000):04d}" + rng.choice(_LETTERS)
    return f"{head}{fourth}{rest}"


def _bad_gstin(rng: random.Random) -> str:
    valid = _build_gstin(rng, "plain").value
    charset = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    wrong = charset[(charset.index(valid[-1]) + 1) % 36]
    return valid[:-1] + wrong


def _timestamp(rng: random.Random) -> str:
    moment = datetime(
        rng.randrange(2000, 2026),
        rng.randrange(1, 13),
        rng.randrange(1, 29),
        rng.randrange(24),
        rng.randrange(60),
        rng.randrange(60),
    )
    return moment.strftime("%Y-%m-%dT%H:%M:%S")


def _token(rng: random.Random, low: int, high: int) -> str:
    length = low if low == high else rng.randint(low, high)
    return "".join(rng.choice(string.ascii_lowercase) for _ in range(length))


def _faker_call(rng: random.Random, locale: str, method: str) -> str:
    from faker import Faker

    fake: Any = Faker(locale)
    fake.seed_instance(rng.randrange(1, 2**31))
    produced: Any = getattr(fake, method)()
    return str(produced)


AADHAAR = Generator(Label.IN_AADHAAR, ("plain", "spaced", "masked"), _build_aadhaar)
PAN = Generator(Label.IN_PAN, ("plain",), _build_pan)
GSTIN = Generator(Label.IN_GSTIN, ("plain",), _build_gstin)
UPI_ID = Generator(Label.IN_UPI_ID, ("dotted_name", "compact_name", "mobile"), _build_upi)
MOBILE = Generator(
    Label.IN_MOBILE,
    ("plain", "plus91_spaced", "plus91_dash", "trunk_zero", "spaced"),
    _build_mobile,
)
PINCODE = Generator(Label.IN_PINCODE, ("plain",), _build_pincode)
PASSPORT = Generator(Label.IN_PASSPORT, ("plain",), _build_passport)
VOTER_ID = Generator(Label.IN_VOTER_ID, ("plain",), _build_voter_id)
IFSC = Generator(Label.IN_IFSC, ("plain",), _build_ifsc)
VEHICLE_REG = Generator(Label.IN_VEHICLE_REG, ("plain", "spaced", "hyphen", "bh"), _build_vehicle)
BANK_ACCOUNT = Generator(Label.IN_BANK_ACCOUNT, ("plain",), _build_bank_account)
PERSON_NAME = Generator(Label.PERSON_NAME, ("latin", "devanagari"), _build_name)
POSTAL_ADDRESS = Generator(Label.POSTAL_ADDRESS, ("latin", "devanagari"), _build_address)
EMAIL = Generator(Label.EMAIL, ("plain",), _build_email)
DATE_OF_BIRTH = Generator(
    Label.DATE_OF_BIRTH,
    ("slash", "dash", "iso", "en_month", "hi_month"),
    _build_dob,
)
HARD_NEGATIVE = Generator(
    Label.NONE,
    (
        "aadhaar",
        "utr",
        "otp",
        "pan_sku",
        "invoice",
        "ipv4",
        "currency",
        "timestamp",
        "gstin",
    ),
    _build_hard_negative,
)

GENERATORS: tuple[Generator, ...] = (
    AADHAAR,
    PAN,
    GSTIN,
    UPI_ID,
    MOBILE,
    PINCODE,
    PASSPORT,
    VOTER_ID,
    IFSC,
    VEHICLE_REG,
    BANK_ACCOUNT,
    PERSON_NAME,
    POSTAL_ADDRESS,
    EMAIL,
    DATE_OF_BIRTH,
    HARD_NEGATIVE,
)
