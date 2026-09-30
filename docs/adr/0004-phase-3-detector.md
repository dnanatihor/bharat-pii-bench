# 0004 — Phase 3 baseline detector

- Status: accepted
- Date: 2026-09-30

## Context

`regex_checksum` classifies a whole value with ordered patterns and the Phase 1 validators. Several formats overlap, and names and addresses have no checksum.

## Options considered

1. Let a 12-digit string that fails Verhoeff become `IN_BANK_ACCOUNT`.
2. Refuse every 12-digit string that is not a valid Aadhaar.
3. Add name and address dictionaries to the baseline.

## Decision

A more specific validator wins: valid Aadhaar before the 9–18 digit bank pattern, a 10-digit number starting 6–9 before a bank account, and GSTIN before the PAN inside it. A 12-digit miss and a 6-digit OTP can therefore score as bank account and pincode. The hard-negative false-positive rate reports that overlap. `find` drops matches inside longer alphanumeric tokens, ISO-8601 timestamps, and UUIDs. Names and addresses stay `NONE` unless column-name hints break a tie in `regex_checksum+names`.

## Consequences

The golden list expects this order, including `NONE` for free-text names and addresses. Later detectors can cover those labels without changing the checksum rules.
