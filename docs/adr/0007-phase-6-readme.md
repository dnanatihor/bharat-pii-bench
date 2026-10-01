# 0007 — Leaderboard source and TestPyPI publish

- Status: accepted
- Date: 2026-09-30

## Context

SPEC.md Appendix B requires a short README whose results are produced by `bpb readme` from committed runs, a Quickstart CI job, a placeholder demo, and a library publish to TestPyPI.

## Options considered

1. Type the leaderboard by hand — forbidden by Appendix B.3.
2. Generate it from `results/*/metrics.csv`, keep one real checksum run in git, and publish with `uv publish` to TestPyPI on release.

## Decision

`bpb readme` replaces the marker block from the newest metrics file for each detector. The committed run is a real `bpb run` of `regex_checksum` and `regex_checksum+names` on the default seed and test split. `.github/workflows/release.yml` builds the package and publishes to `https://test.pypi.org/legacy/` with trusted publishing. `docs/demo.gif` is a placeholder until a person records the demo.

## Consequences

A new committed run changes the README only when someone runs `bpb readme`. Quickstart writes another results directory and refreshes the same scores. The first TestPyPI upload still needs the GitHub trusted-publisher environment `testpypi` on the host that owns the project name.
