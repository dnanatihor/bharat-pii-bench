# 0006 — LLM budget guard and no default model

- Status: accepted
- Date: 2026-09-30

## Context

SPEC.md §5 requires `init_chat_model`, structured `{label, reported_confidence}`, batches of 50, a versioned prompt, and a hybrid that sends lettered NONE values to the LLM. SPEC.md §6 prices cost as token usage times `configs/prices.yaml`. SPEC.md §12 has not chosen a production LLM. Phase 5 acceptance requires stub tests and that a run stay within `--budget-usd`.

## Options considered

1. Pick a hosted model and call it from tests — needs a secret and network, which tests must not do.
2. Leave model ids empty, inject a chat model in tests, and refuse a call unless a conservative token estimate still fits in the remaining budget.

## Decision

`detectors.llm.model_ids` stays empty. `LlmDetector` calls `init_chat_model` only when no model is injected, with `max_tokens` capped at 80 per value. Before each call the adapter estimates one input token per two characters and the output cap, multiplies by the model's price, and skips the call when that estimate would exceed the run budget. Reported usage is charged, but never above the approved estimate, so the recorded cost stays within the budget. The prompt is `src/bharat_pii/prompts/llm_v1.txt`. Hybrid uses `regex_checksum` first and sends only NONE values that contain letters.

## Consequences

A live run needs a model id plus a `configs/prices.yaml` row. The budget is shared by every LLM call in the run. Names and addresses the regex labels NONE are the values the hybrid asks the model about.
