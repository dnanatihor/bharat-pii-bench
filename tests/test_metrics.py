"""Hand-computed precision, recall, F1, and related summaries."""

from bharat_pii.labels import Label
from bharat_pii.metrics import (
    hard_negative_false_positive_rate,
    name_sensitivity,
    percentile,
    score,
)


def test_precision_recall_and_f1_match_hand_computation() -> None:
    aadhaar = Label.IN_AADHAAR
    pan = Label.IN_PAN
    none = Label.NONE
    # A: tp 1, fp 1, fn 1 -> precision 0.5, recall 0.5, f1 0.5, support 2
    # P: tp 1, fp 0, fn 0 -> precision 1, recall 1, f1 1, support 1
    card = score([aadhaar, aadhaar, pan, none], [aadhaar, none, pan, aadhaar])
    by_label = {item.label: item for item in card.per_label}
    assert by_label[aadhaar].precision == 0.5
    assert by_label[aadhaar].recall == 0.5
    assert by_label[aadhaar].f1 == 0.5
    assert by_label[aadhaar].support == 2
    assert by_label[pan].f1 == 1.0
    assert card.confusion[(aadhaar, aadhaar)] == 1
    assert card.confusion[(none, aadhaar)] == 1
    # Micro uses personal labels only: tp 2, predicted positive 3, support 3.
    assert card.micro_f1 == 2 * (2 / 3) * (2 / 3) / ((2 / 3) + (2 / 3))


def test_hard_negative_rate_and_name_drop() -> None:
    rate = hard_negative_false_positive_rate(
        [True, True, False],
        [Label.NONE, Label.IN_PAN, Label.IN_AADHAAR],
    )
    assert rate == 0.5
    drops = name_sensitivity({"truthful": 0.9, "obfuscated": 0.6, "misleading": 0.4})
    assert abs(drops["drop_obfuscated"] - 0.3) < 1e-9
    assert abs(drops["drop_misleading"] - 0.5) < 1e-9


def test_percentile_uses_nearest_rank() -> None:
    assert percentile([1, 2, 3, 4], 50) == 2
    assert percentile([1, 2, 3, 4], 100) == 4
