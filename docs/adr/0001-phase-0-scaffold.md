# 0001 — Phase 0 scaffold layout

- Status: accepted
- Date: 2026-09-30

## Context

Phase 0 needs a taxonomy, config models, public reference lists, and a package whose base install imports `bharat_pii.detect` with no heavy extras. SPEC.md names the files and the extras, and leaves the YAML shape and the code/status of historical identifiers unspecified.

## Options considered

1. Pydantic models and PyYAML in the base install — validation is convenient; Pydantic is another runtime dependency the detector does not need.
2. Dataclasses plus PyYAML in the base install — the config models stay typed, and detect/validate do not import YAML.
3. Dataclasses and a hand-rolled YAML parser — avoids the dependency, and duplicates a parser.

## Decision

Use dataclasses and PyYAML. PyYAML is a base dependency because the config models ship with the library. `detect` and `validate` do not import it. Generators, pandas, plotting, Presidio, transformers, torch, and LangChain stay in extras.

GST codes `01`–`38` come from the GST state-code list, with `25` (Daman and Diu) and `28` (Andhra Pradesh before division) marked `legacy`. Vehicle codes are the current two-letter codes, former codes that remain valid on existing plates (`UA`, `OR`, `DN`, `TS`), and `BH` marked `series`. UPI suffixes are public PSP handles, including the examples in SPEC.md §3.

`find`, `classify_value`, and `mask` expose the SPEC.md §5 signatures and raise `NotImplementedError` until Phase 3. Validators stay an importable module until Phase 1.

## Consequences

Later phases extend these models instead of replacing them. A historical GST or plate code can be filtered by `status` when generators need only codes issued today. NER labels and token prices stay empty until SPEC.md §12 chooses models.
