# 0005 — Presidio and NER model defaults

- Status: accepted
- Date: 2026-09-30

## Context

SPEC.md §5 adds a Presidio adapter and a configurable Hugging Face NER adapter. SPEC.md §12 left the NER model open. Reports must list the recognizers that actually ran.

## Options considered

1. Leave `detectors.ner.model_id` empty and require every caller to pass a model — the bench cannot run `ner` as configured.
2. Default to `dslim/bert-base-NER`, a public English token-classification model whose `PER` group maps to `PERSON_NAME`. India-specific identifiers stay with the pattern and Presidio recognizers.

## Decision

Use `dslim/bert-base-NER`. The Presidio adapter registers every shipped recognizer class whose name starts with `In`, in addition to Presidio's default registry. Coarse Presidio types (`PHONE_NUMBER`, `DATE_TIME`, `LOCATION`) stay unmapped, so they become `NONE`. Both adapters are imported only when requested, so the base install still does not load Presidio or torch.

## Consequences

A `ner` run downloads that model. A different model needs a matching `configs/ner_map.yaml`. Presidio's own NER still needs its language model; if that model is absent, the heavy test fails and a pattern-only engine has to be wired in.
