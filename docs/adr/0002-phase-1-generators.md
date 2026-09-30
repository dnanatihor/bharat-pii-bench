# 0002 — Phase 1 generators and validators

- Status: accepted
- Date: 2026-09-30

## Context

SPEC.md §3 defines each generator as `generate(rng, variant)` and asks property tests for Verhoeff, GSTIN check characters, PAN structure, and seed determinism. A few shapes overlap, and masked Aadhaar cannot carry a Verhoeff digit.

## Options considered

1. Validators reject every overlapping format (for example, an OTP is not a pincode).
2. Validators check format and checksum only. The generator assigns `NONE` when the value is a hard negative.

## Decision

Validators check format and checksum. A 6-digit OTP can match the pincode format, and a 12-digit Aadhaar matches the 9–18 digit bank-account format. The hard-negative generator still labels those values `NONE`.

Verhoeff applies to full 12-digit Aadhaar numbers. The masked variant `XXXX XXXX NNNN` is valid as a presentation of `IN_AADHAAR` with `meta.masked` set, and it is excluded from the Verhoeff property.

Vehicle series letters omit `I` and `O`, matching the plates described by MoRTH. Faker is imported only inside name and address generation and is seeded from the caller’s `random.Random`. The GSTIN check character is confirmed against `29AAAAA0300L1Z8`, a sample published in the NIC e-way bill API documentation.

## Consequences

Phase 3 has to order patterns so an ambiguous digit string is not claimed by the wrong label. Names and addresses need the `bench` extra because they use Faker.
