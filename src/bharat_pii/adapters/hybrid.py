"""Regex first. Values it leaves as NONE, when they contain letters, go to the LLM."""

from bharat_pii.adapters.llm import LlmDetector
from bharat_pii.detect import RegexChecksum
from bharat_pii.labels import Label
from bharat_pii.vote import majority_label


class HybridDetector:
    name = "hybrid"
    version = "regex_checksum+llm_v1"

    def __init__(self, llm: LlmDetector | None = None) -> None:
        self._regex = RegexChecksum()
        self._llm = llm if llm is not None else LlmDetector()
        self.model_id = self._llm.model_id
        self.prompt_version = self._llm.prompt_version

    @property
    def cost_usd(self) -> float:
        return self._llm.cost_usd

    def classify_values(self, values: list[str]) -> list[Label]:
        base = self._regex.classify_values(values)
        pending = [
            index
            for index, (value, label) in enumerate(zip(values, base, strict=True))
            if label is Label.NONE and any(character.isalpha() for character in value)
        ]
        if not pending:
            return base
        revised = self._llm.classify_values([values[index] for index in pending])
        labels = list(base)
        for index, label in zip(pending, revised, strict=True):
            labels[index] = label
        return labels

    def classify_column(self, name: str, samples: list[str]) -> Label:
        labels = self.classify_values(samples)
        if not any(sample.strip() for sample in samples):
            return Label.NONE
        return majority_label(labels)
