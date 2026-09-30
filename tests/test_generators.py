"""Property tests for SPEC.md §3 and §8."""

import random

from hypothesis import given, settings
from hypothesis import strategies as st

from bharat_pii.generate import (
    AADHAAR,
    DATE_OF_BIRTH,
    EMAIL,
    GENERATORS,
    GSTIN,
    HARD_NEGATIVE,
    PAN,
    PERSON_NAME,
    POSTAL_ADDRESS,
    VEHICLE_REG,
    Generator,
)
from bharat_pii.labels import Label
from bharat_pii.validate import (
    VALIDATORS,
    is_valid_gstin,
    is_valid_pan,
    is_valid_pincode,
    verhoeff_valid,
)


def _seeds() -> st.SearchStrategy[int]:
    return st.integers(min_value=0, max_value=1_000_000)


@settings(max_examples=40)
@given(seed=_seeds(), variant=st.sampled_from(AADHAAR.variants) | st.none())
def test_generated_aadhaar_passes_verhoeff_unless_masked(seed: int, variant: str | None) -> None:
    sample = AADHAAR.generate(random.Random(seed), variant)
    assert sample.label is Label.IN_AADHAAR
    if sample.meta.get("masked") is True:
        assert sample.variant == "masked"
        assert sample.value.startswith("XXXX XXXX ")
        assert VALIDATORS[Label.IN_AADHAAR](sample.value)
        return
    digits = sample.value.replace(" ", "")
    assert verhoeff_valid(digits)
    assert digits[0] in "23456789"
    assert VALIDATORS[Label.IN_AADHAAR](sample.value)


@settings(max_examples=30)
@given(seed=_seeds())
def test_aadhaar_hard_negatives_fail_verhoeff(seed: int) -> None:
    sample = HARD_NEGATIVE.generate(random.Random(seed), "aadhaar")
    assert sample.label is Label.NONE
    assert len(sample.value) == 12 and sample.value.isdigit()
    assert sample.value[0] in "23456789"
    assert not verhoeff_valid(sample.value)


@settings(max_examples=30)
@given(seed=_seeds())
def test_generated_gstin_check_character_validates(seed: int) -> None:
    sample = GSTIN.generate(random.Random(seed), None)
    assert is_valid_gstin(sample.value)
    assert is_valid_pan(sample.value[2:12])


@settings(max_examples=20)
@given(seed=_seeds())
def test_gstin_hard_negatives_fail_the_check_character(seed: int) -> None:
    sample = HARD_NEGATIVE.generate(random.Random(seed), "gstin")
    assert sample.label is Label.NONE
    assert len(sample.value) == 15
    assert not is_valid_gstin(sample.value)


@settings(max_examples=40)
@given(seed=_seeds())
def test_generated_pan_matches_structure(seed: int) -> None:
    sample = PAN.generate(random.Random(seed), None)
    assert is_valid_pan(sample.value)
    if sample.value[3] == "P":
        surname = sample.meta["surname"]
        assert isinstance(surname, str)
        assert sample.value[4] == surname[0]


@settings(deadline=None, max_examples=15)
@given(
    seed=_seeds(),
    generator=st.sampled_from(GENERATORS),
)
def test_generators_are_deterministic_for_a_seed(seed: int, generator: Generator) -> None:
    left = generator.generate(random.Random(seed), None)
    right = generator.generate(random.Random(seed), None)
    assert left == right


@settings(deadline=None, max_examples=8)
@given(seed=_seeds(), variant=st.sampled_from(PERSON_NAME.variants))
def test_generated_names_match_their_script(seed: int, variant: str) -> None:
    sample = PERSON_NAME.generate(random.Random(seed), variant)
    assert VALIDATORS[Label.PERSON_NAME](sample.value)
    assert sample.meta["script"] == variant
    has_devanagari = any("\u0900" <= char <= "\u097f" for char in sample.value)
    assert has_devanagari is (variant == "devanagari")


@settings(deadline=None, max_examples=8)
@given(seed=_seeds(), variant=st.sampled_from(POSTAL_ADDRESS.variants))
def test_generated_addresses_validate(seed: int, variant: str) -> None:
    sample = POSTAL_ADDRESS.generate(random.Random(seed), variant)
    assert VALIDATORS[Label.POSTAL_ADDRESS](sample.value)
    assert sample.meta["script"] == variant


@settings(max_examples=20)
@given(seed=_seeds(), variant=st.sampled_from(VEHICLE_REG.variants))
def test_vehicle_variants_include_separators_and_bh(seed: int, variant: str) -> None:
    sample = VEHICLE_REG.generate(random.Random(seed), variant)
    assert VALIDATORS[Label.IN_VEHICLE_REG](sample.value)
    if variant == "bh":
        assert " BH " in sample.value
    elif variant == "spaced":
        assert " " in sample.value
    elif variant == "hyphen":
        assert "-" in sample.value


@settings(max_examples=10)
@given(seed=_seeds())
def test_remaining_generators_match_their_validators(seed: int) -> None:
    for generator in GENERATORS:
        if generator.label is Label.NONE:
            continue
        variant = generator.variants[0]
        sample = generator.generate(random.Random(seed), variant)
        assert sample.label is generator.label
        assert VALIDATORS[sample.label](sample.value)


def test_hard_negative_shapes() -> None:
    rng = random.Random(7)
    negatives = {
        variant: HARD_NEGATIVE.generate(rng, variant).value for variant in HARD_NEGATIVE.variants
    }
    assert len(negatives["utr"]) == 22
    assert len(negatives["otp"]) == 6 and negatives["otp"].isdigit()
    assert not is_valid_pan(negatives["pan_sku"])
    assert negatives["invoice"].startswith("INV-")
    assert negatives["ipv4"].startswith("192.0.2.")
    assert negatives["currency"].startswith("₹")
    assert "T" in negatives["timestamp"]
    assert is_valid_pincode(negatives["otp"]) or negatives["otp"].startswith("0")


def test_email_and_dob_variants_validate() -> None:
    rng = random.Random(3)
    assert VALIDATORS[Label.EMAIL](EMAIL.generate(rng, None).value)
    for variant in DATE_OF_BIRTH.variants:
        sample = DATE_OF_BIRTH.generate(random.Random(3), variant)
        assert VALIDATORS[Label.DATE_OF_BIRTH](sample.value)


def test_unknown_variant_is_rejected() -> None:
    try:
        AADHAAR.generate(random.Random(0), "courier")
    except ValueError:
        return
    raise AssertionError("expected ValueError")
