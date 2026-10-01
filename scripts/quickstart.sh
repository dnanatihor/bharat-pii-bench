#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv sync --frozen --group dev --extra bench
uv run bpb generate --task t1 --seed 42 --out data/generated
uv run bpb generate --task t2 --seed 42 --out data/generated
uv run bpb run --detectors regex_checksum,regex_checksum+names --task both --split test --out results
uv run bpb readme
