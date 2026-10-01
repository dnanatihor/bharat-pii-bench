# Benchmark report

Split: `test`. Seed: `42`.

## regex_checksum 0.1.0

- macro-F1: 0.8508
- micro-F1: 0.9115
- hard-negative false-positive rate: 0.2097
- latency p50 per 1,000 values: 0.019015s
- latency p95 per 1,000 values: 0.028312s

### Name sensitivity (T2 macro-F1)

- truthful: 0.8667
- obfuscated: 0.8667
- misleading: 0.8667
- drop_obfuscated: 0.0000
- drop_misleading: 0.0000

## regex_checksum+names 0.1.0

- macro-F1: 0.8508
- micro-F1: 0.9115
- hard-negative false-positive rate: 0.2097
- latency p50 per 1,000 values: 0.029158s
- latency p95 per 1,000 values: 0.054228s

### Name sensitivity (T2 macro-F1)

- truthful: 0.8667
- obfuscated: 0.8667
- misleading: 0.8667
- drop_obfuscated: 0.0000
- drop_misleading: 0.0000

