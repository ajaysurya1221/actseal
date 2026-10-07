"""Support, platform, dependency and security-policy statements match the package."""

from __future__ import annotations

import importlib
import re
from importlib.metadata import distribution
from pathlib import Path

import pytest

from actseal.records import PROVIDERS
from docs.conftest import DOCS, ROOT

SECURITY = ROOT / "SECURITY.md"
AGENTS = ROOT / "AGENTS.md"


def _prose(path: Path) -> str:
    """Document text with every whitespace run collapsed, so wrapping is irrelevant."""
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))


def test_core_metadata_has_no_windows_classifier_and_no_core_dependency() -> None:
    metadata = distribution("actseal").metadata
    classifiers = metadata.get_all("Classifier") or []
    assert "Operating System :: MacOS" in classifiers
    assert "Operating System :: POSIX :: Linux" in classifiers
    assert not any("Windows" in classifier for classifier in classifiers)
    for requirement in metadata.get_all("Requires-Dist") or []:
        assert "extra == 'laya'" in requirement, requirement
    assert metadata["Requires-Python"] == ">=3.12"


@pytest.mark.parametrize(
    "document",
    ["docs/quickstart.md", "docs/providers.md", "docs/faq.md", "CONTRIBUTING.md", "AGENTS.md"],
)
def test_windows_is_stated_as_unsupported(document: str) -> None:
    assert "Windows is unsupported" in _prose(ROOT / document)


def test_zero_dependency_core_claim_is_stated_where_the_core_is_described() -> None:
    assert "imports only the standard library" in _prose(DOCS / "python-api.md")
    assert "depends only on the Python standard library" in _prose(DOCS / "faq.md")
    assert "runtime core stays dependency-free" in _prose(ROOT / "CONTRIBUTING.md")


def test_providers_doc_describes_jev_as_unshipped_and_experimental() -> None:
    """Exact current behaviour: no Jev adapter is installed and the docs say so.

    Integration follow-up (Task 19 inclusion decision): if Jev ships as a
    PROVISIONAL provider, update providers/cli/python-api/faq and replace this
    test with the experimental-flag behaviour; if it is cut, update only the
    deadline sentence. Neither outcome is claimed here.
    """
    assert set(PROVIDERS) == {"fixture", "laya"}
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("actseal.experimental.providers.jev")
    text = _prose(DOCS / "providers.md")
    assert "## Jev: conditional experimental work, not shipped" in text
    assert "deferred to v2" not in text
    assert "the current source ships no Jev adapter" in text
    assert "--provider jev --experimental-provider" in text
    for document in ("python-api.md", "faq.md"):
        prose = _prose(DOCS / document)
        assert "current stable providers" in prose, document
        assert "In the v1.0 scope" in prose, document
        assert "In 1.x the runner accepts only" not in prose, document


def test_security_policy_support_rule_and_reportability_are_preserved() -> None:
    text = _prose(SECURITY)
    assert "https://github.com/ajaysurya1221/actseal/security/advisories/new" in text
    assert "latest 1.x minor release at its latest patch" in text
    assert "not a promise to maintain a 0.1 security branch" in text
    assert "latest v0.1.x release" not in text
    for phrase in (
        "Incorrect statistical verdicts",
        "replay code execution",
        "unbounded parsing",
        "worker-lifecycle defects",
        "A parser or validation defect within these same paths remains reportable",
    ):
        assert phrase in text, phrase
    for phrase in (
        "does not authenticate provider responses",
        "internally coherent same-lock response rewrite",
        "false labels or dishonest sampling history",
    ):
        assert phrase in text, phrase
    for forbidden in ("out of scope", "accepted risk", "will not be fixed", "not reportable"):
        assert forbidden not in text.lower(), forbidden


def test_agents_points_at_the_active_v1_records_that_exist() -> None:
    text = _prose(AGENTS)
    for pointer in (
        "plan/v1/STATE.md",
        "plan/v1/tasks/<id>.md",
        "plan/v1/CHANGE_LOG.md",
        "plan/v1/reviews/",
        "plan/v1/reports/",
        "docs/stability.md",
        "plan/v1/PLAN.md",
    ):
        assert pointer in text, pointer
        concrete = pointer.replace("<id>", "08")
        assert (ROOT / concrete).exists(), concrete
    assert "claude-fable-5-1" in text
    assert "never grants a broader or permanent override" in text
