"""Optional-extra checks. These download models and are skipped unless ``-m heavy``."""

import pytest

from bharat_pii.detect import detector_by_name
from bharat_pii.labels import Label

pytestmark = pytest.mark.heavy


def test_presidio_lists_shipped_recognizers() -> None:
    detector = detector_by_name("presidio")
    recognizers = getattr(detector, "active_recognizers", ())
    assert recognizers
    assert all(isinstance(name, str) and name for name in recognizers)
    assert detector.classify_values(["user@example.com"]) == [Label.EMAIL]


def test_ner_maps_a_person_name() -> None:
    detector = detector_by_name("ner")
    assert detector.version == "dslim/bert-base-NER"
    assert detector.classify_values(["John Smith lives in London"]) == [Label.PERSON_NAME]
