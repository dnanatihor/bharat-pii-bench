"""Phase 0: label taxonomy matches SPEC.md §2."""

from bharat_pii.labels import Label


def test_labels_match_spec_taxonomy() -> None:
    assert {label.value for label in Label} == {
        "IN_AADHAAR",
        "IN_PAN",
        "IN_GSTIN",
        "IN_UPI_ID",
        "IN_MOBILE",
        "IN_PINCODE",
        "IN_PASSPORT",
        "IN_VOTER_ID",
        "IN_IFSC",
        "IN_VEHICLE_REG",
        "IN_BANK_ACCOUNT",
        "PERSON_NAME",
        "POSTAL_ADDRESS",
        "EMAIL",
        "DATE_OF_BIRTH",
        "NONE",
    }


def test_label_round_trips_from_value() -> None:
    assert Label("IN_PAN") is Label.IN_PAN
    assert Label("NONE") is Label.NONE
