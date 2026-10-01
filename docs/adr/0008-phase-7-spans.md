# 0008 — Exact span match for T3

- Status: accepted
- Date: 2026-09-30

## Context

SPEC.md §1.3 defines T3 as a Hindi, English, or Hinglish sentence with labelled spans. Phase 7 asks for span-level precision and recall for `regex_checksum` and `llm`. It does not define the sentence count or whether a partial overlap counts as a hit.

## Options considered

1. Count any overlapping span with the same label.
2. Count only an exact `(label, start, end)` match, and generate `per_label_count` sentences in each of the three languages.

## Decision

A hit is an exact span. `build_t3` embeds one synthetic identifier per sentence, cycling the personal labels, and does not write the sentences to disk. `regex_checksum` uses `find`. The LLM uses `prompts/llm_spans_v1.txt` and the same budget guard as value classification. When that call is skipped, the sentence has no predicted spans.

## Consequences

A span that covers only part of a gold identifier counts as a miss. Name and address sentences therefore lower regex recall, because `find` does not label those values.
