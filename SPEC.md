# Bharat PII Bench — Indian Personal-Data Detection Benchmark and Detector Library

| | |
|---|---|
| Repo name | `bharat-pii-bench` (package `bharat_pii`) |
| Version | 0.1.0 |
| Size | Medium |
| Depends on | nothing; its detector is reused by `mcp-warden` and `governed-rag-reference` |

---

## 0. Using this spec with Cursor

Save as `SPEC.md` at the repo root. Implement one phase at a time from §10 with the prompts in Appendix A.

If this repository was created with the portfolio bootstrap, the prompts below are already filled in per phase in `CURSOR_PROMPTS.md`, and `.cursor/rules/project.mdc` already contains the project rules from Appendix A.

---

## 1. Purpose and scope

### 1.1 What it does

1. A **synthetic data generator** for Indian personal identifiers and hard negatives, at value level and column level.
2. A **benchmark harness** comparing detection approaches: pattern + checksum rules, Microsoft Presidio, a token-classification (NER) model, LLMs, and a hybrid.
3. A **reusable detector library** (`bharat_pii.detect`), the pattern + checksum baseline, packaged for other projects.

### 1.2 Why

Data catalogs classify columns to drive masking and access policies. Many open-source classifiers focus on Western identifier formats, and coverage of Indian identifiers is often thin. With India's Digital Personal Data Protection (DPDP) Act increasing attention on personal-data handling, a transparent benchmark for Indian formats is useful and uncommon.

### 1.3 Tasks

| Task | Input | Output |
|---|---|---|
| T1 value-level | one value string | label |
| T2 column-level | column name + 20 sample values | label |
| T3 span-level (optional, Phase 7) | a sentence in Hindi, English, or Hinglish | labelled spans |

### 1.4 Non-goals

Legal classification under DPDP (the Act does not define sensitivity tiers like earlier drafts; the benchmark treats all labels as personal data except `NONE`), OCR of ID documents, and validating whether an identifier is actually issued.

### 1.5 Responsible data handling

- All data is **synthetic**, generated on the fly from a seed. No scraped or real personal data is ever used.
- Checksum-valid identifiers can coincide with real issued numbers by chance. Therefore **generated datasets are not committed or published**; only the generator and seed are. The README states this.
- Synthetic identifiers are paired with synthetic names only and must never be presented as belonging to real people.

---

## 2. Label taxonomy

| Label | Format summary (generator spec in §3) |
|---|---|
| `IN_AADHAAR` | 12 digits, first digit 2–9, Verhoeff check digit |
| `IN_PAN` | 5 letters + 4 digits + 1 letter; 4th letter is the holder type |
| `IN_GSTIN` | 2-digit state code + PAN + entity char + `Z` + mod-36 check char |
| `IN_UPI_ID` | `local@handle` |
| `IN_MOBILE` | 10 digits starting 6–9, optional +91 / 0 prefix |
| `IN_PINCODE` | 6 digits, first digit 1–9 |
| `IN_PASSPORT` | 1 letter + 7 digits |
| `IN_VOTER_ID` | 3 letters + 7 digits |
| `IN_IFSC` | 4 letters + `0` + 6 alphanumerics |
| `IN_VEHICLE_REG` | state code + district digits + series letters + 4 digits, or BH series |
| `IN_BANK_ACCOUNT` | 9–18 digits (inherently ambiguous) |
| `PERSON_NAME` | Indian names in Latin and Devanagari script |
| `POSTAL_ADDRESS` | Indian addresses in Latin and Devanagari script |
| `EMAIL` | email address |
| `DATE_OF_BIRTH` | dates in several formats including Hindi month names |
| `NONE` | anything else, including hard negatives |

---

## 3. Generators (`bharat_pii.generate`)

Each generator: `generate(rng: random.Random, variant: str | None) -> Sample(value, label, variant, meta)`. Every generator has a matching validator in `bharat_pii.validate`.

- **Aadhaar:** 11 random digits (first 2–9) + Verhoeff check digit. Variants: `plain` (12 contiguous digits), `spaced` (`NNNN NNNN NNNN`), `masked` (`XXXX XXXX NNNN`; label stays `IN_AADHAAR`, `meta.masked = true`). Docs and tests use generated values or patterns, never hand-typed example numbers.
- **PAN:** letters 1–3 random; letter 4 ∈ {P, C, H, F, A, T, B, L, J, G}; letter 5 = first letter of the synthetic surname when letter 4 is P, else random; 4 digits; 1 random letter.
- **GSTIN:** state code from the valid list in `data/gst_state_codes.csv`, a generated PAN, entity char [1-9A-Z], `Z`, and a check char. Check-char algorithm: charset `0-9A-Z`; for each of the first 14 characters at index *i*, value = charset index × (1 if *i* even else 2); sum += value // 36 + value % 36; check = charset[(36 − sum % 36) % 36]. Phase 1 must confirm the algorithm against a publicly listed valid GSTIN (for example, one published by a government body) in a unit test.
- **UPI ID:** local part from the name (`priya.sharma`, `psharma92`) or a 10-digit mobile; handle from `data/upi_handles.txt` (e.g. `okaxis`, `okhdfcbank`, `oksbi`, `okicici`, `ybl`, `ibl`, `axl`, `paytm`).
- **Mobile:** variants `plain`, `+91 98xxx xxxxx`, `+91-`, `0` prefix, and spaced 5-5.
- **Vehicle registration:** state codes from `data/vehicle_state_codes.txt`; variants with spaces, hyphens, none; BH series `22 BH 1234 AA`.
- **Names / addresses:** `Faker` locales `en_IN` and `hi_IN`; variant records the script.
- **DOB:** `DD/MM/YYYY`, `DD-MM-YYYY`, `YYYY-MM-DD`, `12 Jan 1961`, and Hindi month names (`12 जनवरी 1961`).

**Hard negatives** (label `NONE`): 12-digit numbers that fail Verhoeff (e.g. transaction references), 22-character UTR-like strings, 6-digit OTP-like values, product SKUs shaped like PAN but with an invalid 4th letter, invoice numbers, IPv4 addresses, currency amounts, timestamps, and GSTIN-shaped strings with a wrong check character.

---

## 4. Dataset builder

- **T1:** balanced by label (configurable per-label counts; default 500 each, NONE 2,000 of which half are hard negatives). Split into `dev` (20%) and `test` (80%) by seed.
- **T2:** synthetic columns of 20 values with noise (5% nulls or blanks, 5% malformed values of the same label). The column label is the generating label. Each column appears under three **name conditions**:
  - `truthful` — e.g. `aadhaar_no`, `pan_number`, `customer_mobile`
  - `obfuscated` — e.g. `col_07`, `field_c`
  - `misleading` — e.g. a PAN column named `customer_ref`, an Aadhaar column named `order_id`
- Output: in-memory iterables or local Parquet files under `data/generated/` (git-ignored). A **dataset card** (`docs/dataset-card.md`) documents generation, variants, counts, known limitations, and the no-publication rule.

---

## 5. Detectors

```python
class Detector(Protocol):
    name: str
    version: str
    def classify_values(self, values: list[str]) -> list[Label]: ...
    def classify_column(self, name: str, samples: list[str]) -> Label: ...
```

| Detector | Approach |
|---|---|
| `regex_checksum` | Ordered regex patterns + validators (Verhoeff, GSTIN check char, PAN 4th-letter rule). Column level: majority vote over values; variant `regex_checksum+names` adds column-name keyword hints as a tie-breaker. This is the library detector. |
| `presidio` | `presidio-analyzer` with default recognizers plus any India-specific recognizers shipped in the installed version (the run records which were active). Entity types map to the taxonomy via `configs/presidio_map.yaml`; unmapped → NONE. |
| `ner` | Hugging Face token-classification pipeline; model ID configurable; labels mapped via config. |
| `llm` | `init_chat_model`; structured output `{label, reported_confidence}`; values batched 50 per call; column prompt includes the taxonomy, column name, and samples. Prompt file versioned. |
| `hybrid` | `regex_checksum` first; values it labels NONE that contain letters go to `llm`. |

The library API (`bharat_pii.detect`):

```python
def find(text: str) -> list[Span]                 # spans with label, start, end
def classify_value(value: str) -> Label
def mask(text: str, token_style: str = "typed") -> str   # "«in_aadhaar»" etc.
```

`find` must not match inside longer alphanumeric tokens and must avoid ISO-8601 timestamps and UUIDs.

---

## 6. Metrics and outputs

- Per-label precision, recall, F1; macro-F1 and micro-F1.
- Confusion matrix (heatmap PNG).
- **Hard-negative false-positive rate.**
- **Name sensitivity** (T2): macro-F1 for truthful, obfuscated, and misleading conditions, and the drop between them. This shows which detectors rely on column names rather than values.
- Latency p50/p95 per 1,000 values; cost per 1,000 values for LLM detectors (token usage × `configs/prices.yaml`).
- Outputs per run under `results/<run_id>/`: `metrics.csv`, `report.md`, `plots/`, `run.json` (seed, versions, model IDs, prompt version, active Presidio recognizers). `bpb readme` regenerates a leaderboard section in the README between markers.

CLI:

```
bpb generate --task t1|t2 --seed 42 [--out data/generated]
bpb run --detectors regex_checksum,presidio,llm --task t1|t2 --split test [--budget-usd 5]
bpb report RUN_DIR
bpb readme
```

---

## 7. Library packaging

- `pip install bharat-pii` installs only the generator-free detector library (`detect`, `validate`) with no heavy dependencies.
- Extras: `[bench]` (generators, harness, Faker, pandas, plots), `[presidio]`, `[ner]`, `[llm]`.
- Semantic versioning; the detector's behaviour changes only with a version bump and a changelog entry.

---

## 8. Testing

- **Property tests** (`hypothesis`): every generated Aadhaar passes Verhoeff; every Aadhaar hard negative fails it; every GSTIN check char validates; every PAN matches structure; generators are deterministic for a seed.
- **Validator tests** with hand-written positive and negative examples per label.
- **Detector tests:** `regex_checksum` achieves 100% on a hand-written golden list of 100 values; `find()` does not match inside timestamps, UUIDs, or longer tokens; masking preserves surrounding text.
- **Harness tests:** metrics match hand-computed values; stub LLM detector exercises batching and budget.
- Presidio and NER tests are marked `@pytest.mark.heavy` (model downloads) and skipped by default.

---

## 9. Configuration

`configs/bench.yaml`: seed, per-label counts, noise rates, name-condition word lists, detector settings, LLM model IDs, and budget. `configs/presidio_map.yaml`, `configs/ner_map.yaml`, and `configs/prices.yaml` as described above.

---

## 10. Phases and acceptance criteria

**Phase 0 — Scaffold.** Taxonomy, config models, data files (state codes, UPI handles, vehicle codes), packaging with extras. *Accept:* tooling passes; `pip install -e .` without extras imports `bharat_pii.detect`. *Baseline:* the repository baseline in Appendix B.1 is in place, including a README stub with the project name, one-line value proposition, Why, and a planned Quickstart; the CI workflow's commands pass locally.

**Phase 1 — Generators and validators.** §3. *Accept:* property tests pass; the GSTIN algorithm is confirmed against a public example.

**Phase 2 — Dataset builder.** §4 and the dataset card. *Accept:* same seed → identical datasets; name conditions present for every T2 column; `data/generated/` is git-ignored.

**Phase 3 — Baseline detector and harness.** `regex_checksum`, library API, metrics, reports. *Accept:* golden-list test at 100%; a full T1 + T2 run produces `report.md` and plots.

**Phase 4 — Presidio and NER.** Adapters and mappings. *Accept:* heavy tests pass locally; reports list active recognizers.

**Phase 5 — LLM and hybrid.** Adapters, batching, cost tracking, budget guard. *Accept:* stub-model tests pass; a real run stays within `--budget-usd`.

**Phase 6 — Leaderboard and release.** `bpb readme`, release workflow for the library. *Accept:* README leaderboard generated from committed results; the library publishes to TestPyPI. *README:* README.md satisfies Appendix B.2 and B.3; a CI job runs the Quickstart on a fresh checkout and passes; all example output comes from real runs.

**Phase 7 (optional) — T3 span detection.** Hinglish and Hindi sentences with embedded identifiers; span-level metrics. *Accept:* span-level precision/recall reported for `regex_checksum` and `llm`.

---

## 11. Conventions

Python 3.11+, `mypy --strict`, `ruff`. No real personal data anywhere. Generated datasets are never committed. Every result has a `run.json`. Numbers in the README come only from generated reports.

---

## 12. Open decisions

1. **Publication approach** — confirm that publishing the generator but not the datasets is the right balance.
2. **Models** — which NER model and which LLMs to include, and the budget.
3. **Additional labels** — e.g. driving licence (formats vary by state), ABHA health ID, ration card.
4. **Name availability** on GitHub and PyPI.

---

## Appendix A — Cursor prompts

<!-- bootstrap:phase-prompt -->
```
Read SPEC.md. Implement Phase N from §10 only. Satisfy every acceptance criterion for Phase N, write tests first where the spec gives expected outputs, and do not start later phases. If anything is ambiguous, list the ambiguity and stop.
```

<!-- bootstrap:review-prompt -->
```
Review the Phase N implementation against SPEC.md. For each acceptance criterion in §10, state whether it is met and which test proves it. List every divergence from the spec. Do not fix anything yet.
```

Project rules:

<!-- bootstrap:rules -->
```
- Only synthetic data. Never add real identifiers to code, tests, or docs, except a publicly listed GSTIN used solely to verify the check-char algorithm.
- Generated datasets stay under data/generated/ and are git-ignored.
- The base library (bharat_pii.detect, bharat_pii.validate) must not import heavy optional dependencies.
```

---

## Appendix B — Repository baseline and README

### B.1 Repository baseline (Phase 0)

- `README.md` stub (items 1, 4, and a planned Quickstart from B.2), `CHANGELOG.md` (Keep a Changelog format with an `[Unreleased]` section), `LICENSE` (Apache-2.0), `.gitignore`, and `docs/adr/` with a template. The portfolio bootstrap creates these; if the repository was created by hand, create them in Phase 0.
- `pyproject.toml` managed by `uv`, with `ruff` (lint and format) and `mypy --strict` configured there.
- `.pre-commit-config.yaml` running ruff, ruff-format, and basic hygiene hooks (trailing whitespace, end of file, YAML and JSON checks). Pin hook versions to the latest releases at Phase 0.
- `.github/workflows/ci.yml` running lint, type-check, and tests with `uv` on every push and pull request, plus the `web/` build and tests where the project has a UI. Add the CI badge to the README.
- Conventional commit messages, semantic versioning, and a CHANGELOG entry for every release.

### B.2 README requirements (Phase 6)

The README is a deliverable of Phase 6. Sections, in order:

1. `# <Name> — <one-line value proposition>`
2. Badges: CI, licence, PyPI (libraries only)
3. Demo: `![demo](docs/demo.gif)` (placeholder until recorded; see B.3)
4. Why: 2–3 sentences on the problem and who has it
5. Quickstart: one command that works on a fresh machine
6. How it works: Mermaid architecture diagram and a short walkthrough
7. Results / example output: real output from the tool (see B.3)
8. Design decisions: links to `docs/adr/`
9. Roadmap: only things not yet built
10. Licence

Rules:

- Every command in the README must run. A CI job executes the Quickstart on a fresh checkout.
- All example output comes from a real run on the repository's fixtures, never written by hand.
- Keep it under about 150 lines; longer material goes in `docs/`.

### B.3 Demo and results for this project

- **Demo:** The leaderboard chart, plus an optional terminal recording of `bpb run` on the dev split.
- **Results / example output:** The leaderboard generated by `bpb readme`, including the name-sensitivity comparison.

The demo is recorded by a person, not generated. For terminal demos, Cursor may write a `docs/demo.tape` script for `vhs`, which records terminal sessions as GIFs; re-record whenever the output changes.

README prompt for Phase 6:

<!-- bootstrap:readme-prompt -->
```
Read SPEC.md, including Appendix B. Write README.md following Appendix B.2 exactly, with the demo and results content from B.3. Take the Quickstart commands from what actually works in this repository, and add a CI job that runs them on a fresh checkout. For "Results / example output", run the tool on the included fixtures and paste the real output; do not invent any output. Leave docs/demo.gif as a placeholder with a TODO. Keep it under 150 lines and move anything longer into docs/.
```
