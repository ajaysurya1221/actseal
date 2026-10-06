"""docs/python-api.md: documented names exist, signatures match, examples run."""

from __future__ import annotations

import importlib
import inspect
import re
import subprocess
import sys
from pathlib import Path

import pytest

import actseal
from docs.conftest import DOCS, fences, table_rows

GUIDE = DOCS / "python-api.md"
_DEFAULT_NAMES = {"134217728": "MAX_JSON_BYTES"}


def _resolve(dotted: str) -> object:
    """Import the longest module prefix of ``dotted``, then walk attributes."""
    parts = dotted.split(".")
    for length in range(len(parts), 0, -1):
        try:
            target: object = importlib.import_module(".".join(parts[:length]))
        except ModuleNotFoundError:
            continue
        for part in parts[length:]:
            target = getattr(target, part)
        return target
    raise AssertionError(dotted)


def _public(module_name: str) -> set[str]:
    """``__all__`` of a module, or its non-underscore names for the one module without it."""
    module = _resolve(module_name)
    exported = getattr(module, "__all__", None)
    if exported is None:
        return {name for name in vars(module) if not name.startswith("_")}
    return set(exported)


def _normalize(signature: str) -> str:
    text = signature.replace("'", "")
    for literal, name in _DEFAULT_NAMES.items():
        text = text.replace(literal, name)
    return re.sub(r"\s+", " ", text)


def _signature_rows() -> list[tuple[str, str]]:
    rows = table_rows(GUIDE.read_text(encoding="utf-8"), "Function")
    return [(row[0].strip("`"), row[1].strip("`")) for row in rows]


@pytest.mark.parametrize(("dotted", "documented"), _signature_rows(), ids=lambda value: value)
def test_documented_signatures_match_the_installed_package(dotted: str, documented: str) -> None:
    target = _resolve(dotted)
    assert _normalize(str(inspect.signature(target))) == _normalize(documented)  # type: ignore[arg-type]


def test_signature_table_covers_every_public_function_in_the_manifest() -> None:
    """Every documented module function (not records/constants) appears in the table."""
    documented = {dotted for dotted, _ in _signature_rows()}
    modules = {
        "actseal.contract",
        "actseal.locking",
        "actseal.policy",
        "actseal.normalization",
        "actseal.faults",
        "actseal.assessment",
        "actseal.evidence",
        "actseal.replay",
        "actseal.compatibility",
        "actseal.serialization",
        "actseal.runner",
        "actseal.cli",
    }
    expected = {"actseal.stats.clopper_pearson_tail", "actseal.adapters.fixture.validate_timeout"}
    for module_name in modules:
        module = _resolve(module_name)
        for name in module.__all__:  # type: ignore[attr-defined]
            if inspect.isfunction(getattr(module, name)):
                expected.add(f"{module_name}.{name}")
    assert expected <= documented, sorted(expected - documented)


def test_surface_table_names_exist_and_are_exported() -> None:
    rows = table_rows(GUIDE.read_text(encoding="utf-8"), "Group")
    checked = 0
    for row in rows:
        modules = [cell.strip().strip("`") for cell in row[1].split(",")]
        names = re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)`", row[2])
        assert names, row[0]
        for name in names:
            owners = [module_name for module_name in modules if name in _public(module_name)]
            assert owners, (row[0], name)
            checked += 1
    assert checked > 60
    for name in ("Option", "Verdict", "SchemaError", "canonical_json"):
        assert name in actseal.__all__


def test_examples_run_in_order_against_a_fresh_demo(demo_workspace: Path) -> None:
    """Every ``python`` fence executes, in document order, from one working directory."""
    snippets = fences(GUIDE, "python")
    assert len(snippets) >= 6
    for index, code in enumerate(snippets):
        script = demo_workspace / f"example_{index}.py"
        script.write_text(code, encoding="utf-8")
        result = subprocess.run(  # noqa: S603 - fixed interpreter and documentation text
            [sys.executable, str(script)],
            cwd=demo_workspace,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        assert result.returncode == 0, (index, result.stderr[-2000:])
        assert result.stderr == "", index
    assert (demo_workspace / "recheck.lock.json").is_file()
    assert (demo_workspace / "recheck-evidence" / "verdict.json").is_file()


def test_runtime_example_binds_the_request_first_and_refuses_foreign_captures() -> None:
    """The documented live gate checks request binding first and proves the negative path."""
    runtime = next(code for code in fences(GUIDE, "python") if "def route_ticket" in code)
    binding = runtime.index("capture.request_sha256 != request_sha256(request)")
    assert binding < runtime.index("normalize(capture")
    assert binding < runtime.index("evaluate(")
    assert "foreign = CapturedOutcome(request_sha256(other)" in runtime
    refusal = 'raise AssertionError("a capture for another request must never be evaluated")'
    assert refusal in runtime
    assert runtime.count('assert executed == ["live-001->billing"]') == 3


def test_examples_do_not_import_optional_or_private_names() -> None:
    for code in fences(GUIDE, "python"):
        assert "laya" not in code
        assert "experimental" not in code
        assert not re.search(r"from actseal[.\w]* import [^\n]*\b_", code)
