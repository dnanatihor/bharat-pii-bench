"""Label taxonomy from SPEC.md §2."""

from enum import StrEnum


class Label(StrEnum):
    """Personal-data labels. ``NONE`` is the only non-personal label."""

    IN_AADHAAR = "IN_AADHAAR"
    IN_PAN = "IN_PAN"
    IN_GSTIN = "IN_GSTIN"
    IN_UPI_ID = "IN_UPI_ID"
    IN_MOBILE = "IN_MOBILE"
    IN_PINCODE = "IN_PINCODE"
    IN_PASSPORT = "IN_PASSPORT"
    IN_VOTER_ID = "IN_VOTER_ID"
    IN_IFSC = "IN_IFSC"
    IN_VEHICLE_REG = "IN_VEHICLE_REG"
    IN_BANK_ACCOUNT = "IN_BANK_ACCOUNT"
    PERSON_NAME = "PERSON_NAME"
    POSTAL_ADDRESS = "POSTAL_ADDRESS"
    EMAIL = "EMAIL"
    DATE_OF_BIRTH = "DATE_OF_BIRTH"
    NONE = "NONE"
