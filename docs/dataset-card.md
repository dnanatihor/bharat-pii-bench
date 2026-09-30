# Dataset card

Synthetic Indian personal-data tasks for Bharat PII Bench. Only the generator and seed are kept. Generated files under `data/generated/` are git-ignored and must not be published.

## Generation

`bpb generate --task t1|t2 --seed 42 [--out data/generated]` reads `configs/bench.yaml` and writes Parquet. The same seed rebuilds the same rows. Everything is produced by `bharat_pii.generate` from `random.Random`; names and addresses use Faker locales `en_IN` and `hi_IN`, seeded from that RNG.

## Tasks

**T1** is one value per row. Each personal label has `per_label_count` rows (default 500). `NONE` has `none_count` rows (default 2,000), and half of those are hard negatives (failed Aadhaar check digits, bad GSTIN check characters, UTR-like strings, OTP-like numbers, PAN-shaped SKUs, invoice numbers, documentation-range IPv4 addresses, currency amounts, and ISO-8601 timestamps). The other half are plain `note-<n>` strings. Within each label, `dev_fraction` (default 0.2) of rows are `dev` and the rest are `test`.

**T2** is one column per label, length `column_sample_size` (default 20). About 5% of cells are null or blank, and about 5% are a malformed value of that label. The same cells are stored three times, once for each name condition: `truthful` (for example `aadhaar_no`), `obfuscated` (for example `col_07`), and `misleading` (for example a PAN column named `customer_ref`).

## Variants

T1 keeps the generator variant on each row: Aadhaar `plain`, `spaced`, and `masked`; mobiles with `+91`, trunk `0`, and spacing; vehicle plates with spaces, hyphens, or the BH series; names and addresses in Latin (`en_IN`) and Devanagari (`hi_IN`); dates as `DD/MM/YYYY`, `DD-MM-YYYY`, `YYYY-MM-DD`, `12 Jan 1961`, and Hindi month names.

## Known limitations

Checksum-valid identifiers can match a real issued number by chance. Format validators overlap: a 12-digit Aadhaar also matches the 9–18 digit bank-account shape, and a 6-digit OTP matches the pincode shape. Masked Aadhaar does not carry a Verhoeff digit. Hard-negative rows are labelled `NONE` even when a format validator would accept them. The benchmark does not say whether an identifier was actually issued.

## No publication

Do not commit, upload, or share `data/generated/`. Publish the generator, the seed, and this card instead.
