"""LLM detector. LangChain is imported only when no chat model is injected."""

import importlib
from pathlib import Path
from typing import Any

from bharat_pii.config import ConfigError, ModelPrice, load_bench_config, load_prices
from bharat_pii.cost import OUTPUT_TOKENS_PER_VALUE, Budget, estimate_tokens, token_cost
from bharat_pii.labels import Label
from bharat_pii.vote import majority_label

BATCH_SIZE = 50
PROMPT_VERSION = "llm_v1"
_PROMPT = (Path(__file__).resolve().parents[1] / "prompts" / "llm_v1.txt").read_text(
    encoding="utf-8"
)


class LlmDetector:
    name = "llm"
    version = PROMPT_VERSION
    prompt_version = PROMPT_VERSION

    def __init__(
        self,
        *,
        model: Any | None = None,
        model_id: str | None = None,
        budget: Budget | None = None,
        price: ModelPrice | None = None,
    ) -> None:
        chosen = model_id
        if chosen is None:
            ids = load_bench_config().detectors.llm_model_ids
            if not ids:
                raise ValueError("detectors.llm.model_ids is empty")
            chosen = ids[0]
        self.model_id = chosen
        self._price = price if price is not None else _price_for(chosen)
        self._budget = budget if budget is not None else Budget(load_bench_config().budget_usd)
        self._model = model if model is not None else _load_model(chosen)
        self.cost_usd = 0.0
        self.calls = 0

    def classify_values(self, values: list[str]) -> list[Label]:
        labels: list[Label] = []
        for start in range(0, len(values), BATCH_SIZE):
            batch = values[start : start + BATCH_SIZE]
            labels.extend(self._classify_batch("(none)", batch))
        return labels

    def classify_column(self, name: str, samples: list[str]) -> Label:
        present = [sample for sample in samples if sample.strip()]
        if not present:
            return Label.NONE
        labels = self._classify_batch(name, present[:BATCH_SIZE])
        recognised = [label for label in labels if label is not Label.NONE]
        if not recognised:
            return Label.NONE
        return majority_label(recognised)

    def _classify_batch(self, column_name: str, values: list[str]) -> list[Label]:
        prompt = render_prompt(column_name, values)
        input_tokens, output_tokens = estimate_tokens(prompt, len(values))
        estimate = token_cost(input_tokens, output_tokens, self._price)
        if not self._budget.allows(estimate):
            return [Label.NONE] * len(values)
        response = self._model.invoke(prompt)
        self.calls += 1
        parsed, reported_in, reported_out = _split_response(response)
        charged_in = reported_in if reported_in is not None else input_tokens
        charged_out = reported_out if reported_out is not None else output_tokens
        charged_out = min(charged_out, OUTPUT_TOKENS_PER_VALUE * len(values))
        amount = min(token_cost(charged_in, charged_out, self._price), estimate)
        self._budget.charge(amount)
        self.cost_usd += amount
        return _labels(parsed, len(values))


def render_prompt(column_name: str, values: list[str]) -> str:
    taxonomy = ", ".join(label.value for label in Label)
    listed = "\n".join(f"{index}. {value}" for index, value in enumerate(values, start=1))
    return _PROMPT.format(taxonomy=taxonomy, column_name=column_name, values=listed)


def _price_for(model_id: str) -> ModelPrice:
    prices = load_prices()
    price = prices.models.get(model_id)
    if price is None:
        raise ConfigError(f"configs/prices.yaml has no price for {model_id}")
    return price


def _load_model(model_id: str) -> Any:
    module: Any = importlib.import_module("langchain.chat_models")
    chat: Any = module.init_chat_model(
        model_id,
        temperature=0,
        max_tokens=OUTPUT_TOKENS_PER_VALUE * BATCH_SIZE,
    )
    structured: Any = chat.with_structured_output(_schema(), include_raw=True)
    return structured


def _schema() -> dict[str, object]:
    item = {
        "type": "object",
        "properties": {
            "label": {"type": "string"},
            "reported_confidence": {"type": "number"},
        },
        "required": ["label", "reported_confidence"],
    }
    return {
        "title": "VerdictBatch",
        "type": "object",
        "properties": {"items": {"type": "array", "items": item}},
        "required": ["items"],
    }


def _split_response(response: Any) -> tuple[Any, int | None, int | None]:
    if isinstance(response, dict) and "parsed" in response:
        parsed = response["parsed"]
        raw = response.get("raw")
    else:
        parsed = response
        raw = None
    usage = _usage(raw)
    return parsed, usage[0], usage[1]


def _usage(raw: Any) -> tuple[int | None, int | None]:
    if raw is None:
        return None, None
    if isinstance(raw, dict):
        meta = raw.get("usage_metadata")
    else:
        meta = getattr(raw, "usage_metadata", None)
    if not isinstance(meta, dict):
        return None, None
    input_tokens = meta.get("input_tokens")
    output_tokens = meta.get("output_tokens")
    if not isinstance(input_tokens, int) or not isinstance(output_tokens, int):
        return None, None
    return input_tokens, output_tokens


def _labels(parsed: Any, expected: int) -> list[Label]:
    if isinstance(parsed, dict):
        raw_items: Any = parsed.get("items") or []
    else:
        raw_items = getattr(parsed, "items", None) or []
    labels: list[Label] = []
    for item in raw_items:
        text = item.get("label") if isinstance(item, dict) else getattr(item, "label", "")
        try:
            labels.append(Label(str(text)))
        except ValueError:
            labels.append(Label.NONE)
    if len(labels) < expected:
        labels.extend([Label.NONE] * (expected - len(labels)))
    return labels[:expected]
