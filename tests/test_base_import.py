"""Phase 0: the base library imports with no heavy optional dependencies."""

import ast
import inspect
from pathlib import Path

import bharat_pii.detect as detect
import bharat_pii.validate as validate

_HEAVY = {
    "faker",
    "pandas",
    "pyarrow",
    "matplotlib",
    "presidio_analyzer",
    "transformers",
    "torch",
    "langchain",
    "langchain_core",
}


def _imported_modules(source: str) -> set[str]:
    tree = ast.parse(source)
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".", maxsplit=1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module.split(".", maxsplit=1)[0])
    return modules


def test_detect_and_validate_import() -> None:
    assert detect.__doc__
    assert validate.__doc__


def test_detect_and_validate_do_not_import_heavy_modules() -> None:
    root = Path("src/bharat_pii")
    for filename in ("detect.py", "validate.py"):
        source = (root / filename).read_text(encoding="utf-8")
        assert _imported_modules(source).isdisjoint(_HEAVY)


def test_library_api_signatures_match_spec() -> None:
    find_params = list(inspect.signature(detect.find).parameters)
    assert find_params == ["text"]

    classify_params = list(inspect.signature(detect.classify_value).parameters)
    assert classify_params == ["value"]

    mask_sig = inspect.signature(detect.mask)
    assert list(mask_sig.parameters) == ["text", "token_style"]
    assert mask_sig.parameters["token_style"].default == "typed"

    hints = detect.Detector.__annotations__
    assert "name" in hints
    assert "version" in hints
    assert callable(detect.Detector.classify_values)
    assert callable(detect.Detector.classify_column)
