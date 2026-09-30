# Bharat PII Bench — Synthetic benchmark and detector for Indian personal identifiers

[![CI](https://img.shields.io/badge/CI-lint%20%7C%20types%20%7C%20tests-2ea44f)](.github/workflows/ci.yml)

## Why

Data catalogs classify columns to drive masking and access policies. Many open-source classifiers focus on Western identifier formats, and coverage of Indian identifiers is often thin. India's Digital Personal Data Protection (DPDP) Act has increased attention on personal-data handling, so teams that classify or mask Indian data need a transparent benchmark for those formats.

Generated datasets are synthetic and are not committed or published. Only the generator and the seed are kept.

## Quickstart

Planned for later phases, once `bpb` exists:

```bash
uv run bpb generate --task t1 --seed 42 --out data/generated
uv run bpb run --detectors regex_checksum --task t1 --split test
```

## Licence

Apache-2.0
