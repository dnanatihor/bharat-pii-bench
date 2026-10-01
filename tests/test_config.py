"""Phase 0: config models load the files described in SPEC.md §9."""

from bharat_pii.config import load_bench_config, load_label_map, load_prices
from bharat_pii.labels import Label
from bharat_pii.reference import project_path


def test_bench_config_matches_spec_defaults() -> None:
    config = load_bench_config()
    assert config.seed == 42
    assert config.per_label_count == 500
    assert config.none_count == 2000
    assert config.hard_negative_fraction == 0.5
    assert config.dev_fraction == 0.2
    assert config.test_fraction == 0.8
    assert config.noise.null_or_blank == 0.05
    assert config.noise.malformed == 0.05
    assert config.column_sample_size == 20
    assert config.budget_usd == 5.0
    assert config.detectors.regex_checksum_enabled is True
    assert config.detectors.presidio_enabled is False
    assert config.detectors.ner_enabled is False
    assert config.detectors.ner_model_id == "dslim/bert-base-NER"
    assert config.detectors.llm_enabled is False
    assert config.detectors.llm_model_ids == ()


def test_name_condition_word_lists_include_spec_examples() -> None:
    names = load_bench_config().name_conditions
    assert "aadhaar_no" in names.truthful[Label.IN_AADHAAR]
    assert "pan_number" in names.truthful[Label.IN_PAN]
    assert "customer_mobile" in names.truthful[Label.IN_MOBILE]
    assert names.obfuscated == ("col_07", "field_c")
    assert "order_id" in names.misleading[Label.IN_AADHAAR]
    assert "customer_ref" in names.misleading[Label.IN_PAN]
    personal = set(Label) - {Label.NONE}
    assert personal <= set(names.truthful)
    assert personal <= set(names.misleading)
    assert all(names.truthful[label] for label in personal)
    assert all(names.misleading[label] for label in personal)


def test_presidio_and_ner_maps_use_taxonomy_labels() -> None:
    presidio = load_label_map(project_path("configs", "presidio_map.yaml"))
    ner = load_label_map(project_path("configs", "ner_map.yaml"))
    assert presidio["EMAIL_ADDRESS"] is Label.EMAIL
    assert presidio["PERSON"] is Label.PERSON_NAME
    assert "PHONE_NUMBER" not in presidio
    assert ner["PER"] is Label.PERSON_NAME
    assert all(isinstance(label, Label) for label in {**presidio, **ner}.values())


def test_prices_start_empty_until_models_are_chosen() -> None:
    prices = load_prices()
    assert prices.models == {}
