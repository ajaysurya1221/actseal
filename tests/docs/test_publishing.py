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
    assert "project-scoped" in guide
    assert "valid for 15 minutes from creation" in guide
    assert "https://docs.pypi.org/trusted-publishers/" in guide
    assert "expires with the" not in guide  # the corrected 08-token-expiry finding


def test_guide_requires_pre_tag_documentation_finalization() -> None:
    """The normative gate lives in the publishing guide and is permanent.

    The CHANGELOG's own pending paragraph is temporary by design and is
    removed when the entry is finalized before the tag, so it is not asserted
    here; the release-notes receipt field name is permanent and is.
    """
    guide = re.sub(r"\s+", " ", _guide())
    assert "**Pre-tag documentation finalization.**" in guide
    assert "tagged commit is immutable" in guide
    assert "A later task cannot change bytes already tagged or uploaded." in guide
    assert "not part of the published distribution" not in guide
    assert "packages the pre-tag copies of `plan/v1/RELEASE_NOTES.md`" in guide
    assert "cannot alter the already-tagged commit" in guide
    # The release notes are a pre-tag finalization input, not an exception.
    assert "`docs/` **and `plan/v1/RELEASE_NOTES.md`** must be resolved" in guide
    assert "with its pending markers" not in guide
    # Only named publication-receipt placeholders survive the tag.
    assert "may contain **only** named placeholders for the final release receipts" in guide
    assert "populated as the tagged release pipeline completes" in guide
    assert "cannot exist before the upload" not in guide
    # Build-time receipts exist before any upload; post-publication ones do not.
    assert "build-time values that exist once the tagged `build` job has run" in guide
    for receipt in ("hashes and sizes", "artifact ids"):
        assert receipt in guide, receipt
    assert "post-publication values that exist only after the upload" in guide
    for receipt in ("attestation inspection", "PyPI install and smoke results", "recording"):
        assert receipt in guide, receipt
    assert "No other draft, candidate or pending marker may remain." in guide
    notes = (ROOT / "plan" / "v1" / "RELEASE_NOTES.md").read_text(encoding="utf-8")
    assert "`source_commit`" in notes
    assert "source.commit" not in notes


def test_guide_does_not_claim_a_v1_publication() -> None:
    guide = _guide()
    assert "1.0.0 is published" not in guide
    assert "actseal/1.0.0/" not in guide
    assert "v0.1.0 was published on 6 October 2026" in guide  # history, kept
