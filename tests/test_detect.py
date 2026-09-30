"""Golden list, span boundaries, and masking for regex_checksum."""

from bharat_pii.detect import RegexChecksum, Span, find, mask
from bharat_pii.labels import Label

_AADHAAR = "234567890124"
_GSTIN = "29AAAAA0300L1Z8"

# Hand-written values. Expected labels follow ordered patterns + validators.
GOLDEN: tuple[tuple[str, Label], ...] = (
    (_AADHAAR, Label.IN_AADHAAR),
    ("2345 6789 0124", Label.IN_AADHAAR),
    ("XXXX XXXX 0124", Label.IN_AADHAAR),
    ("234567890120", Label.IN_BANK_ACCOUNT),
    ("ABCPZ1234F", Label.IN_PAN),
    ("ABCFK8291M", Label.IN_PAN),
    ("ABCHQ1000Z", Label.IN_PAN),
    ("ABCKZ1234F", Label.NONE),
    (_GSTIN, Label.IN_GSTIN),
    ("asha.rao92@oksbi", Label.IN_UPI_ID),
    ("p.s@ybl", Label.IN_UPI_ID),
    ("6000000001@paytm", Label.IN_UPI_ID),
    ("Asha.Rao@oksbi", Label.NONE),
    ("6000000001", Label.IN_MOBILE),
    ("+91 60000 00001", Label.IN_MOBILE),
    ("+91-6000000001", Label.IN_MOBILE),
    ("06000000001", Label.IN_MOBILE),
    ("60000 00001", Label.IN_MOBILE),
    ("5000000001", Label.IN_BANK_ACCOUNT),
    ("100000", Label.IN_PINCODE),
    ("560001", Label.IN_PINCODE),
    ("012345", Label.NONE),
    ("A1234567", Label.IN_PASSPORT),
    ("Z0000001", Label.IN_PASSPORT),
    ("ABC1234567", Label.IN_VOTER_ID),
    ("XYZ7654321", Label.IN_VOTER_ID),
    ("AB1234567", Label.NONE),
    ("ZZZZ0AB12CD", Label.IN_IFSC),
    ("HDFC0000123", Label.IN_IFSC),
    ("ZZZZ1AB12CD", Label.NONE),
    ("MH12AB1234", Label.IN_VEHICLE_REG),
    ("MH 12 AB 1234", Label.IN_VEHICLE_REG),
    ("MH-12-AB-1234", Label.IN_VEHICLE_REG),
    ("22 BH 1234 AA", Label.IN_VEHICLE_REG),
    ("MH12IB1234", Label.NONE),
    ("123456789", Label.IN_BANK_ACCOUNT),
    ("123456789012345678", Label.IN_BANK_ACCOUNT),
    ("12345678", Label.NONE),
    ("asha.rao@example.com", Label.EMAIL),
    ("user@example.in", Label.EMAIL),
    ("not-an-email", Label.NONE),
    ("12/01/1961", Label.DATE_OF_BIRTH),
    ("12-01-1961", Label.DATE_OF_BIRTH),
    ("1961-01-12", Label.DATE_OF_BIRTH),
    ("12 Jan 1961", Label.DATE_OF_BIRTH),
    ("12 जनवरी 1961", Label.DATE_OF_BIRTH),
    ("32/01/1961", Label.NONE),
    ("2024-01-15T10:30:00", Label.NONE),
    ("550e8400-e29b-41d4-a716-446655440000", Label.NONE),
    ("note-12", Label.NONE),
    ("hello", Label.NONE),
    ("INV-2024-00123", Label.NONE),
    ("₹1250", Label.NONE),
    ("192.0.2.10", Label.NONE),
    (f"xx{_AADHAAR}yy", Label.NONE),
    ("Asha Rao", Label.NONE),
    ("आशा राव", Label.NONE),
    ("12 Lake Road, Sample Nagar", Label.NONE),
    ("ABCPZ1234F ", Label.IN_PAN),
    (" " + _AADHAAR + " ", Label.IN_AADHAAR),
    ("SBIN0EXAMPLE", Label.NONE),
    ("DL01AA0001", Label.IN_VEHICLE_REG),
    ("KA01A0001", Label.IN_VEHICLE_REG),
    ("22BH1234AA", Label.IN_VEHICLE_REG),
    ("+916000000001", Label.IN_MOBILE),
    ("9876500000", Label.IN_MOBILE),
    ("400001", Label.IN_PINCODE),
    ("B7654321", Label.IN_PASSPORT),
    ("QRS0000001", Label.IN_VOTER_ID),
    ("ICIC0005678", Label.IN_IFSC),
    ("ABCTC0000A", Label.IN_PAN),
    ("ABCLM1111B", Label.IN_PAN),
    ("ABGPE2222C", Label.IN_PAN),
    ("00ABCDE1234F1Z5", Label.NONE),
    ("col_07", Label.NONE),
    ("order_id", Label.NONE),
    ("customer_ref", Label.NONE),
    ("999999999999", Label.IN_AADHAAR),
    ("XXXXXXXXXXXX", Label.NONE),
    ("12/13/1961", Label.NONE),
    ("1961-13-01", Label.NONE),
    ("otp", Label.NONE),
    ("000000", Label.NONE),
    ("10000", Label.NONE),
    ("abc@okaxis", Label.IN_UPI_ID),
    ("priya.sharma@ybl", Label.IN_UPI_ID),
    ("MH02C1234", Label.IN_VEHICLE_REG),
    ("UP32AB0001", Label.IN_VEHICLE_REG),
    ("GJ1AA0001", Label.IN_VEHICLE_REG),
    ("9" * 9, Label.IN_BANK_ACCOUNT),
    ("9" * 19, Label.NONE),
    ("12 January 1961", Label.NONE),
    ("example@example.com", Label.EMAIL),
    ("ZZZZ0ZZZZZZ", Label.IN_IFSC),
    ("P1234567", Label.IN_PASSPORT),
    ("LMN1234567", Label.IN_VOTER_ID),
    ("TS09Z1234", Label.IN_VEHICLE_REG),
    ("aadhaar_no", Label.NONE),
    ("600000000", Label.IN_BANK_ACCOUNT),
    ("+91 6000000001", Label.IN_MOBILE),
)


def test_golden_list_has_100_values_and_scores_perfectly() -> None:
    assert len(GOLDEN) == 100
    detector = RegexChecksum()
    predicted = detector.classify_values([value for value, _ in GOLDEN])
    mismatches = [
        (value, label.value, guess.value)
        for (value, label), guess in zip(GOLDEN, predicted, strict=True)
        if guess is not label
    ]
    assert mismatches == []


def test_find_skips_timestamps_uuids_and_longer_tokens() -> None:
    timestamp = "logged 2024-01-15T10:30:00 ok"
    uuid = "id 550e8400-e29b-41d4-a716-446655440000 end"
    longer = f"xx{_AADHAAR}yy"
    assert find(timestamp) == []
    assert find(uuid) == []
    assert find(longer) == []
    spans = find(f"id {_AADHAAR} end")
    assert spans == [Span(Label.IN_AADHAAR, 3, 3 + len(_AADHAAR))]


def test_mask_preserves_surrounding_text() -> None:
    text = f"call {_AADHAAR} today"
    assert mask(text) == "call «in_aadhaar» today"
    assert mask(text, token_style="typed") == "call «in_aadhaar» today"


def test_column_majority_and_name_tie_break() -> None:
    plain = RegexChecksum()
    named = RegexChecksum(use_names=True)
    values = [_AADHAAR, "2345 6789 0124", "hello"]
    assert plain.classify_column("col_07", values) is Label.IN_AADHAAR
    tied = [_AADHAAR, "ABCPZ1234F"]
    assert plain.classify_column("col_07", tied) is Label.NONE
    assert named.classify_column("pan_number", tied) is Label.IN_PAN
