"""``check_release.py workflow``: the committed file passes; each rule rejects its mutation."""

from __future__ import annotations

import types
from pathlib import Path

import pytest
from release_support import CONTAINER_DIGEST, WORKFLOW, load_tool, run_main

CHECKOUT_PIN = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"


@pytest.fixture(scope="module")
def tool() -> types.ModuleType:
    return load_tool()


@pytest.fixture(scope="module")
def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_committed_workflow_passes(
    tool: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run_main(tool, ["workflow"], capsys) == (0, "", "")
    assert run_main(tool, ["workflow", "--path", str(WORKFLOW)], capsys)[0] == 0


def test_missing_workflow_fails(
    tool: types.ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, _, err = run_main(tool, ["workflow", "--path", str(tmp_path / "absent.yml")], capsys)
    assert code == 1
    assert err.startswith("release check failed: workflow file")


MUTATIONS: dict[str, tuple[str, str, str]] = {
    "extra-tag-pattern": ("      - 'v*'\n", "      - 'v*'\n      - 'release-*'\n", "push trigger"),
    "dispatch-input": (
        "  workflow_dispatch:\n",
        "  workflow_dispatch:\n    inputs:\n      publish:\n        type: boolean\n",
        "rehearsal-only",
    ),
    "top-level-write": (
        "permissions:\n  contents: read\n\nconcurrency",
        "permissions:\n  contents: write\n\nconcurrency",
        "top-level permissions",
    ),
    "cancel-in-progress": (
        "cancel-in-progress: false",
        "cancel-in-progress: true",
        "cancel-in-progress",
    ),
    "renamed-job": ("  mirror:\n", "  mirror2:\n", "jobs must be exactly"),
    "floating-action-tag": (CHECKOUT_PIN, "actions/checkout@v4", "unapproved action"),
    "uv-version": ("version: '0.12.5'", "version: '0.13.0'", "setup-uv must pin 0.12.5"),
    "second-build": (
        "run: uv run --frozen pytest -m packaging",
        "run: |\n          uv build --no-sources\n          uv run --frozen pytest -m packaging",
        "only the build job may run uv build",
    ),
    "download-by-name": (
        "artifact-ids: ${{ needs.build.outputs.artifact-id }}",
        "name: distributions",
        "must not use name:",
    ),
    "id-token-in-verify": (
        "    permissions:\n      contents: read\n    env:\n      UV_PYTHON",
        "    permissions:\n      contents: read\n      id-token: write\n    env:\n      UV_PYTHON",
        "id-token belongs only to publish",
    ),
    "checkout-in-publish": (
        "      - name: Download the exact verified distributions by artifact ID",
        (
            f"      - uses: {CHECKOUT_PIN}\n"
            "      - name: Download the exact verified distributions by artifact ID"
        ),
        "publish must not check out source",
    ),
    "wrong-environment": (
        "environment:\n      name: pypi",
        "environment:\n      name: release",
        "environment pypi",
    ),
    "skip-existing": (
        "skip-existing: false",
        "skip-existing: true",
        "skip-existing must stay disabled",
    ),
    "api-token-fallback": (
        "          attestations: true\n",
        "          attestations: true\n          password: ${{ secrets.PYPI_API_TOKEN }}\n",
        "must not set password",
    ),
    "container-digest": (CONTAINER_DIGEST, "f" * 64, "approved pinned container"),
    "mirror-read-only": (
        "    permissions:\n      contents: write\n    steps:",
        "    permissions:\n      contents: read\n    steps:",
        "mirror permissions must be exactly contents: write",
    ),
    "hard-coded-version": (
        "name: Publish to PyPI\n",
        "name: Publish to PyPI\n# pins 0.1.0\n",
        "hard-code 0.1.0",
    ),
    "hard-coded-hash": (
        "name: Publish to PyPI\n",
        f"name: Publish to PyPI\n# {'a' * 64}\n",
        "only sha256 literal",
    ),
    "clobber": ("name: Publish to PyPI\n", "name: Publish to PyPI\n# --clobber\n", "'--clobber'"),
    "no-supplied-wheel": (
        "ACTSEAL_TEST_WHEEL: ${{ runner.temp }}/dist/${{ needs.build.outputs.wheel }}",
        "ACTSEAL_OTHER: unrelated",
        "ACTSEAL_TEST_WHEEL",
    ),
    "matrix-os": ("os: [ubuntu-latest, macos-latest]", "os: [ubuntu-latest]", "verify matrix os"),
    "fail-fast": ("fail-fast: false", "fail-fast: true", "fail-fast"),
    "publish-condition": (
        "github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v') && needs",
        "needs",
        "publish condition must contain",
    ),
    "no-verify-distributions": (
        "check_release.py verify-distributions",
        "check_release.py verify_distributions",
        "verify must run check_release.py verify-distributions",
    ),
    "overwrite-artifact": (
        "compression-level: 0\n          overwrite: false",
        "compression-level: 0\n          overwrite: true",
        "overwrite: false",
    ),
    "mirror-before-receipt": (
        "check_release.py release-receipt",
        "check_release.py release_receipt",
        "mirror must run check_release.py release-receipt",
    ),
    "publish-without-assets": (
        "needs: [build, verify, assets]\n    if: github.event_name",
        "needs: [build, verify]\n    if: github.event_name",
        "publish must need build, verify and assets",
    ),
    "assets-job-renamed": ("  assets:\n", "  assets2:\n", "jobs must be exactly"),
    "assets-gate-missing": (
        "run: uv run --frozen python tools/check_release.py assets",
        "run: uv run --frozen python tools/check_release.py workflow",
        "assets job must run check_release.py assets",
    ),
    "assets-no-tool-fetch": ("setup_tools.py", "setup.py", "fetch the pinned authoring tools"),
    "assets-no-group": (
        "uv sync --frozen --group dev --group assets",
        "uv sync --frozen --group dev",
        "locked assets dependency group",
    ),
    "no-supplied-dist": (
        "          ACTSEAL_TEST_DIST: ${{ runner.temp }}/dist\n",
        "",
        "ACTSEAL_TEST_DIST",
    ),
    "wheel-outside-dist": (
        "ACTSEAL_TEST_WHEEL: ${{ runner.temp }}/dist/${{ needs.build.outputs.wheel }}",
        "ACTSEAL_TEST_WHEEL: ${{ runner.temp }}/other/${{ needs.build.outputs.wheel }}",
        "inside ACTSEAL_TEST_DIST",
    ),
}


@pytest.mark.parametrize("name", sorted(MUTATIONS))
def test_each_contract_rule_rejects_its_mutation(
    tool: types.ModuleType,
    workflow_text: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    name: str,
) -> None:
    old, new, fragment = MUTATIONS[name]
    assert old in workflow_text, name
    mutated = tmp_path / "publish-pypi.yml"
    mutated.write_text(workflow_text.replace(old, new), encoding="utf-8")
    code, out, err = run_main(tool, ["workflow", "--path", str(mutated)], capsys)
    assert code == 1, name
    assert out == ""
    assert err.startswith("release check failed: ")
    assert fragment in err, (name, err)
