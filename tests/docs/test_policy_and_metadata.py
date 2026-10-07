"""Support, platform, dependency and security-policy statements match the package."""

from __future__ import annotations

import importlib
import re
from importlib.metadata import distribution
from pathlib import Path

import pytest

import actseal.cli as cli_module
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


def test_providers_doc_distinguishes_stable_providers_from_provisional_jev() -> None:
    """Exact current behaviour: fixture/laya are stable; Jev is a PROVISIONAL opt-in.

    The experimental module is installed and importable, admitted in
    ``records.PROVIDERS`` and registered behind ``--experimental-provider``.
    Documentation must say so without claiming a stable, default or
    live-verified provider: the only Jev evidence in this source is mocked
    transport coverage, and final inclusion remains a separate review.
    """
    assert set(PROVIDERS) == {"fixture", "laya", "jev"}
    assert cli_module._PROVIDERS == ("fixture", "laya")
    assert cli_module._EXPERIMENTAL_PROVIDERS == ("jev",)
    module = importlib.import_module("actseal.experimental.providers.jev")
    assert module.API_KEY_ENV == "JEV_API_KEY"
    text = _prose(DOCS / "providers.md")
    assert "## Jev: PROVISIONAL experimental provider, explicit opt-in only" in text
    for phrase in (
        "--provider jev --experimental-provider",
        "`JEV_API_KEY`",
        "No live Jev request has been made or verified",
        "mocked",
        "not part of the default quickstart, demo or stable provider set",
        "`replay` never imports",
        "`--offline`",
        "`--responses`",
        "may change or be removed in any release",
    ):
        assert phrase in text, phrase
    for stale in (
        "ships no Jev adapter",
        "not shipped",
        "deferred to v2",
        "the stable provider set is exactly",
        "exactly two",
        "only those two",
    ):
        assert stale not in text, stale
    for document in ("python-api.md", "faq.md"):
        prose = _prose(DOCS / document)
        assert "current stable providers" in prose, document
        assert "In the v1.0 scope" in prose, document
        assert "PROVISIONAL" in prose, document
        assert "--experimental-provider" in prose, document
        assert "In 1.x the runner accepts only" not in prose, document
        assert "accepts only those two" not in prose, document
        assert "accepts exactly these two" not in prose, document
        assert "not shipped" not in prose, document
    cli_prose = _prose(DOCS / "cli.md")
    assert "--provider jev --experimental-provider" in cli_prose
    assert "PROVISIONAL" in cli_prose
    stability = _prose(DOCS / "stability.md")
    assert "`--provider jev --experimental-provider`" in stability
    assert "not part of this task's deliverable" not in stability


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
