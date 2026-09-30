"""Phase 0: packaging declares the base library and the spec's extras."""

import tomllib
from pathlib import Path


def test_extras_and_base_dependencies() -> None:
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["name"] == "bharat-pii"
    assert project["version"] == "0.1.0"
    assert project["requires-python"] == ">=3.11"
    base = project["dependencies"]
    assert base == ["pyyaml>=6.0.2"]
    extras = project["optional-dependencies"]
    assert set(extras) == {"bench", "presidio", "ner", "llm"}
    bench = " ".join(extras["bench"])
    assert "faker" in bench
    assert "pandas" in bench
    assert "matplotlib" in bench
    joined_base = " ".join(base)
    for heavy in (
        "faker",
        "pandas",
        "matplotlib",
        "presidio",
        "transformers",
        "torch",
        "langchain",
    ):
        assert heavy not in joined_base
