"""docs/publishing.md describes the reviewed workflow, not the retired manual one."""

from __future__ import annotations

import re

from docs.conftest import DOCS, ROOT

GUIDE = DOCS / "publishing.md"
WORKFLOW = ROOT / ".github" / "workflows" / "publish-pypi.yml"


def _guide() -> str:
    return GUIDE.read_text(encoding="utf-8")


def _workflow() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_no_retired_publish_input_remains() -> None:
    text = _guide()
    for stale in ("-f publish=", "publish=true", "publish=false", "publish unchecked"):
        assert stale not in text, stale
    assert "inputs:" not in _workflow()


def test_guide_matches_the_workflow_triggers_and_gates() -> None:
    guide = _guide()
    workflow = _workflow()
    assert "workflow_dispatch:" in workflow
    assert re.search(r"tags:\n\s+- 'v\*'", workflow)
    assert "`workflow_dispatch`" in guide
    assert "no inputs" in guide
    assert "tag matching `v*`" in guide
    assert "name: pypi" in workflow
    assert "`pypi` environment" in guide
    assert "approv" in guide
    assert "skip-existing: false" in workflow
    assert "`skip-existing: false`" in guide
    assert "id-token: write" in workflow
    assert "`id-token: write`" in guide
    assert "artifact-ids:" in workflow
    assert "by ID" in guide
    assert "sha256sum --check --strict" in workflow
    assert "`sha256sum --check --strict`" in guide
    for job in ("build", "verify", "assets", "publish", "verify-published", "mirror"):
        assert f"  {job}:" in workflow, job
        assert f"`{job}`" in guide, job


def test_guide_states_rehearsal_never_uploads_and_recovery_rules() -> None:
    guide = _guide()
    assert "never upload" in guide.lower() or "can never upload" in guide
    assert "Rehearsal results are candidate checks" in guide
    assert "never labelled public PyPI receipts" in guide
    assert "## Failure and partial-publication recovery" in guide
    assert "do not rerun the job" in guide
    assert "published\n  bytes are never replaced" in guide or "never replaced" in guide
    assert "not independent cryptographic verification" in guide
    assert "draft" in guide


def test_guide_describes_oidc_exchange_not_token_absence() -> None:
    guide = _guide()
    assert "No token or secret is involved" not in guide
    assert "No PyPI API token is stored" in guide
    assert "short-lived GitHub OIDC token" in guide
    assert "temporary upload" in guide
    assert "expires with the" in guide


def test_guide_requires_pre_tag_documentation_finalization() -> None:
    guide = re.sub(r"\s+", " ", _guide())
    assert "**Pre-tag documentation finalization.**" in guide
    assert "tagged commit is immutable" in guide
    assert "A later task cannot change bytes already tagged or uploaded." in guide
    changelog = re.sub(r"\s+", " ", (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"))
    assert "resolved to the shipped facts **before** the release build" in changelog
    assert "immutable `v1.0.0` tag" in changelog
    notes = (ROOT / "plan" / "v1" / "RELEASE_NOTES.md").read_text(encoding="utf-8")
    assert "`source_commit`" in notes
    assert "source.commit" not in notes


def test_guide_does_not_claim_a_v1_publication() -> None:
    guide = _guide()
    assert "1.0.0 is published" not in guide
    assert "actseal/1.0.0/" not in guide
    assert "v0.1.0 was published on 6 October 2026" in guide  # history, kept
