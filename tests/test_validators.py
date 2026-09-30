"""Hand-written positive and negative examples for each label."""

import pytest

from bharat_pii.labels import Label
from bharat_pii.validate import (
    VALIDATORS,
    gstin_check_character,
    is_valid_aadhaar,
    is_valid_bank_account,
    is_valid_gstin,
    verhoeff_valid,
)

# Synthetic Verhoeff vector (check digit 4). Not a published identifier.
_AADHAAR = "234567890124"

# Published as a sample in the NIC e-way bill API docs
# (docs.ewaybillgst.gov.in, Generate E-Way Bill, API v1.03).
# Used only to confirm the GSTIN check character.
_PUBLIC_GSTIN = "29AAAAA0300L1Z8"


def test_public_gstin_confirms_the_check_character() -> None:
    assert gstin_check_character(_PUBLIC_GSTIN[:14]) == _PUBLIC_GSTIN[14]
    assert is_valid_gstin(_PUBLIC_GSTIN)


@pytest.mark.parametrize(
    ("label", "value"),
    [
        (Label.IN_AADHAAR, _AADHAAR),
        (Label.IN_AADHAAR, "2345 6789 0124"),
        (Label.IN_AADHAAR, "XXXX XXXX 0124"),
        (Label.IN_PAN, "ABCPZ1234F"),
        (Label.IN_GSTIN, _PUBLIC_GSTIN),
        (Label.IN_UPI_ID, "asha.rao92@oksbi"),
        (Label.IN_MOBILE, "6000000001"),
        (Label.IN_MOBILE, "+91 60000 00001"),
        (Label.IN_MOBILE, "+91-6000000001"),
        (Label.IN_MOBILE, "06000000001"),
        (Label.IN_MOBILE, "60000 00001"),
        (Label.IN_PINCODE, "100000"),
        (Label.IN_PASSPORT, "A1234567"),
        (Label.IN_VOTER_ID, "ABC1234567"),
        (Label.IN_IFSC, "ZZZZ0AB12CD"),
        (Label.IN_VEHICLE_REG, "MH12AB1234"),
        (Label.IN_VEHICLE_REG, "MH 12 AB 1234"),
        (Label.IN_VEHICLE_REG, "MH-12-AB-1234"),
        (Label.IN_VEHICLE_REG, "22 BH 1234 AA"),
        (Label.IN_BANK_ACCOUNT, "123456789"),
        (Label.IN_BANK_ACCOUNT, "123456789012345678"),
        (Label.PERSON_NAME, "Asha Rao"),
        (Label.PERSON_NAME, "आशा राव"),
        (Label.POSTAL_ADDRESS, "12 Lake Road, Sample Nagar"),
        (Label.EMAIL, "asha.rao@example.com"),
        (Label.DATE_OF_BIRTH, "12/01/1961"),
        (Label.DATE_OF_BIRTH, "12-01-1961"),
        (Label.DATE_OF_BIRTH, "1961-01-12"),
        (Label.DATE_OF_BIRTH, "12 Jan 1961"),
        (Label.DATE_OF_BIRTH, "12 जनवरी 1961"),
    ],
)
def test_hand_written_positives(label: Label, value: str) -> None:
    assert VALIDATORS[label](value)


@pytest.mark.parametrize(
    ("label", "value"),
    [
        (Label.IN_AADHAAR, "234567890120"),
        (Label.IN_AADHAAR, "123456789012"),
        (Label.IN_AADHAAR, "23456789012"),
        (Label.IN_PAN, "ABCKZ1234F"),
        (Label.IN_PAN, "ABCPZ123F"),
        (Label.IN_GSTIN, _PUBLIC_GSTIN[:-1] + "0"),
        (Label.IN_UPI_ID, "asha.rao92@notahandle"),
        (Label.IN_UPI_ID, "Asha.Rao@oksbi"),
        (Label.IN_MOBILE, "5000000001"),
        (Label.IN_MOBILE, "600000000"),
        (Label.IN_PINCODE, "012345"),
        (Label.IN_PINCODE, "10000"),
        (Label.IN_PASSPORT, "AB123456"),
        (Label.IN_VOTER_ID, "AB1234567"),
        (Label.IN_IFSC, "ZZZZ1AB12CD"),
        (Label.IN_VEHICLE_REG, "MH12IB1234"),
        (Label.IN_VEHICLE_REG, "22BH 1234 AA"),
        (Label.IN_BANK_ACCOUNT, "12345678"),
        (Label.IN_BANK_ACCOUNT, "1234567890123456789"),
        (Label.PERSON_NAME, "Asha2"),
        (Label.POSTAL_ADDRESS, "ABCPZ1234F"),
        (Label.EMAIL, "not-an-email"),
        (Label.DATE_OF_BIRTH, "32/01/1961"),
        (Label.DATE_OF_BIRTH, "1961-13-01"),
        (Label.DATE_OF_BIRTH, "12 January 1961"),
    ],
)
def test_hand_written_negatives(label: Label, value: str) -> None:
    assert not VALIDATORS[label](value)


def test_synthetic_aadhaar_passes_verhoeff() -> None:
    assert verhoeff_valid(_AADHAAR)
    assert is_valid_aadhaar(_AADHAAR)
    assert is_valid_bank_account(_AADHAAR)


def test_every_personal_label_has_a_validator() -> None:
    assert set(VALIDATORS) == set(Label) - {Label.NONE}
