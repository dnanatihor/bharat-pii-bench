"""LLM cost from token usage and ``configs/prices.yaml``."""

from bharat_pii.config import ModelPrice

# One token per two characters over-estimates real tokenisers.
# Output is capped at this many tokens per classified value.
OUTPUT_TOKENS_PER_VALUE = 80


class Budget:
    """Shared spend for one run. A call is allowed only when its estimate fits."""

    def __init__(self, limit_usd: float) -> None:
        if limit_usd < 0:
            raise ValueError("budget must be >= 0")
        self.limit_usd = limit_usd
        self.spent_usd = 0.0

    def allows(self, estimate_usd: float) -> bool:
        return self.spent_usd + estimate_usd <= self.limit_usd + 1e-9

    def charge(self, amount_usd: float) -> None:
        self.spent_usd += amount_usd


def token_cost(input_tokens: int, output_tokens: int, price: ModelPrice) -> float:
    """USD for one model call."""
    return (
        input_tokens * price.input_per_million_usd + output_tokens * price.output_per_million_usd
    ) / 1_000_000


def estimate_tokens(prompt: str, value_count: int) -> tuple[int, int]:
    """Upper bound used before a call so the run cannot plan past the budget."""
    input_tokens = max(1, (len(prompt) + 1) // 2)
    output_tokens = OUTPUT_TOKENS_PER_VALUE * value_count
    return input_tokens, output_tokens
