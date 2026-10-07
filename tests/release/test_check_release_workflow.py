"""``check_release.py workflow``: the committed file passes; each rule rejects its mutation."""

from __future__ import annotations

import types
from pathlib import Path

import pytest
from release_support import CONTAINER_DIGEST, ROOT, WORKFLOW, load_tool, run_main

CHECKOUT_PIN = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
SETUP_UV_PIN = "astral-sh/setup-uv@c18668ad3cf93ea998bef934396af7bb5c839dc7"


@pytest.mark.parametrize(
    ("filename", "regenerate"),
    [
        ("ci.yml", "uv run --frozen --group assets python docs/assets/src/render.py --check"),
        ("publish-pypi.yml", "uv run --frozen python tools/check_release.py assets"),
    ],
)
def test_asset_jobs_provision_pinned_inputs_before_fail_closed_regeneration(
    tool: types.ModuleType, filename: str, regenerate: str
) -> None:
    """Inspect YAML only: never download tools or execute the renderer in this test."""
    workflow = tool._load_workflow(ROOT / ".github" / "workflows" / filename)
    job = workflow["jobs"]["assets"]
    assert "if" not in job
    assert "continue-on-error" not in job
    steps = tool._steps(job)
    assert [step["uses"] for step in steps if "uses" in step] == [CHECKOUT_PIN, SETUP_UV_PIN]
    assert steps[0]["with"]["persist-credentials"] is False
    assert steps[1]["with"]["version"] == "0.12.5"
    assert steps[1]["with"]["python-version"] == "3.12"
    runs = [str(step.get("run", "")).strip() for step in steps]
    install = "uv sync --frozen --group dev --group assets"
    provision = (
        "uv run --frozen python docs/assets/src/setup_tools.py --tool jetbrains-mono\n"
        "uv run --frozen python docs/assets/src/setup_tools.py --tool resvg\n"
        "uv run --frozen python docs/assets/src/setup_tools.py --tool agg"
    )
    probe = "uv run --frozen python tools/check_release.py agg-version"
    for command in (install, provision, probe, regenerate):
        assert runs.count(command) == 1
        step = steps[runs.index(command)]
        assert "if" not in step
        assert "continue-on-error" not in step
        assert "shell" not in step  # Keep GitHub's fail-closed bash invocation.
    assert runs.index(install) < runs.index(provision) < runs.index(probe) < runs.index(regenerate)
    assert sum("setup_tools.py" in run for run in runs) == 1
    assert sum("agg-version" in run for run in runs) == 1
    assert provision.count("\n") == 2  # exactly three provisioning commands
    if filename == "ci.yml":
        tests = "uv run --frozen --group assets pytest tests/visual"
        assert runs.count(tests) == 1
        assert runs.index(install) < runs.index(tests) < runs.index(provision)
    # The same strict rule the publish checker applies also holds for the ordinary job.
    tool._check_assets_job(job, regenerate)


CI_ASSET_MUTATIONS: dict[str, tuple[str, str, str]] = {
    "agg-provision-omitted": (
        "          uv run --frozen python docs/assets/src/setup_tools.py --tool agg\n",
        "",
        "exact provision command once",
    ),
    "provision-reordered": (
        (
            "setup_tools.py --tool resvg\n          uv run --frozen python docs/assets/src/"
            "setup_tools.py --tool agg\n"
        ),
        (
            "setup_tools.py --tool agg\n          uv run --frozen python docs/assets/src/"
            "setup_tools.py --tool resvg\n"
        ),
        "exact provision command once",
    ),
    "probe-omitted": (
        "        run: uv run --frozen python tools/check_release.py agg-version\n",
        "        run: echo skipped\n",
        "exact probe command once",
    ),
    "probe-conditional": (
        "        run: uv run --frozen python tools/check_release.py agg-version\n",
        (
            "        if: runner.os == 'Linux'\n"
            "        run: uv run --frozen python tools/check_release.py agg-version\n"
        ),
        "probe step must not set if",
    ),
    "probe-ignored-failure": (
        "        run: uv run --frozen python tools/check_release.py agg-version\n",
        (
            "        continue-on-error: true\n"
            "        run: uv run --frozen python tools/check_release.py agg-version\n"
        ),
        "probe step must not set continue-on-error",
    ),
    "probe-shell-escape": (
        "        run: uv run --frozen python tools/check_release.py agg-version\n",
        "        run: uv run --frozen python tools/check_release.py agg-version || true\n",
        "exact probe command once",
    ),
    "probe-duplicated": (
        "        run: uv run --frozen python tools/check_release.py agg-version\n",
        (
            "        run: uv run --frozen python tools/check_release.py agg-version\n"
            "      - name: Probe again\n"
            "        run: uv run --frozen python tools/check_release.py agg-version\n"
        ),
        "exact probe command once",
    ),
    "provision-shell": (
        (
            "      - name: Fetch pinned authoring fonts and tools with hash verification\n"
            "        run: |"
        ),
        (
            "      - name: Fetch pinned authoring fonts and tools with hash verification\n"
            "        shell: bash {0}\n        run: |"
        ),
        "provision step must not set shell",
    ),
    "probe-after-regeneration": (
        (
            "      - name: Probe the pinned Linux recording renderer (hash-verified, fail-closed)\n"
            "        # Proves the approved agg pin runs here; it does not render a GIF.\n"
            "        run: uv run --frozen python tools/check_release.py agg-version\n"
        ),
        "",
        "in that order",
    ),
    "job-conditional": (
        "  assets:\n    name: assets (committed references and regeneration)\n",
        (
            "  assets:\n    if: github.event_name == 'push'\n"
            "    name: assets (committed references and regeneration)\n"
        ),
        "assets job must be unconditional",
    ),
}


@pytest.mark.parametrize("name", sorted(CI_ASSET_MUTATIONS))
def test_ordinary_asset_job_rejects_each_provisioning_escape(
    tool: types.ModuleType, tmp_path: Path, name: str
) -> None:
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    old, new, fragment = CI_ASSET_MUTATIONS[name]
    assert old in text, name
    mutated = tmp_path / "ci.yml"
    if name == "probe-after-regeneration":
        regenerate = (
            "        run: uv run --frozen --group assets python docs/assets/src/render.py --check\n"
        )
        assert text.count(regenerate) == 1
        new_text = text.replace(old, "").replace(regenerate, regenerate + old)
    else:
        new_text = text.replace(old, new)
    mutated.write_text(new_text, encoding="utf-8")
    job = tool._load_workflow(mutated)["jobs"]["assets"]
    with pytest.raises(tool.ReleaseCheckError) as excinfo:
        tool._check_assets_job(
            job, "uv run --frozen --group assets python docs/assets/src/render.py --check"
        )
    assert fragment in str(excinfo.value), (name, str(excinfo.value))


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
    "docs-gate-missing": (
        "run: uv run --frozen python tools/check_release.py docs",
        "run: uv run --frozen python tools/check_release.py workflow",
        "exact docs gate once",
    ),
    "docs-gate-conditional": (
        "      - name: Validate release documentation before building\n",
        "      - name: Validate release documentation before building\n        if: false\n",
        "unconditional and fail closed",
    ),
    "docs-gate-ignored": (
        "      - name: Validate release documentation before building\n",
        (
            "      - name: Validate release documentation before building\n"
            "        continue-on-error: true\n"
        ),
        "unconditional and fail closed",
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
        "exact regenerate command once",
    ),
    "assets-no-tool-fetch": ("setup_tools.py", "setup.py", "exact provision command once"),
    "assets-agg-provision-omitted": (
        "          uv run --frozen python docs/assets/src/setup_tools.py --tool agg\n",
        "",
        "exact provision command once",
    ),
    "assets-provision-reordered": (
        (
            "setup_tools.py --tool resvg\n          uv run --frozen python docs/assets/src/"
            "setup_tools.py --tool agg\n"
        ),
        (
            "setup_tools.py --tool agg\n          uv run --frozen python docs/assets/src/"
            "setup_tools.py --tool resvg\n"
        ),
        "exact provision command once",
    ),
    "assets-probe-omitted": (
        "        run: uv run --frozen python tools/check_release.py agg-version\n",
        "        run: echo skipped\n",
        "exact probe command once",
    ),
    "assets-probe-conditional": (
        "        run: uv run --frozen python tools/check_release.py agg-version\n",
        (
            "        if: runner.os == 'Linux'\n"
            "        run: uv run --frozen python tools/check_release.py agg-version\n"
        ),
        "probe step must not set if",
    ),
    "assets-probe-ignored-failure": (
        "        run: uv run --frozen python tools/check_release.py agg-version\n",
        (
            "        continue-on-error: true\n"
            "        run: uv run --frozen python tools/check_release.py agg-version\n"
        ),
        "probe step must not set continue-on-error",
    ),
    "assets-probe-shell-escape": (
        "        run: uv run --frozen python tools/check_release.py agg-version\n",
        "        run: uv run --frozen python tools/check_release.py agg-version || true\n",
        "exact probe command once",
    ),
    "assets-probe-duplicated": (
        "        run: uv run --frozen python tools/check_release.py agg-version\n",
        (
            "        run: uv run --frozen python tools/check_release.py agg-version\n"
            "      - name: Probe again\n"
            "        run: uv run --frozen python tools/check_release.py agg-version\n"
        ),
        "exact probe command once",
    ),
    "assets-job-conditional": (
        "  assets:\n    name: assets (regenerate required static assets)\n",
        (
            "  assets:\n    if: github.event_name == 'push'\n"
            "    name: assets (regenerate required static assets)\n"
        ),
        "assets job must be unconditional",
    ),
    "assets-job-ignores-failure": (
        "  assets:\n    name: assets (regenerate required static assets)\n",
        (
            "  assets:\n    continue-on-error: true\n"
            "    name: assets (regenerate required static assets)\n"
        ),
        "assets job must not ignore failures",
    ),
    "assets-regenerate-before-probe": (
        (
            "      - name: Probe the pinned Linux recording renderer (hash-verified, fail-closed)\n"
            "        # Proves the approved agg pin runs here; it does not render a GIF.\n"
            "        run: uv run --frozen python tools/check_release.py agg-version\n"
            "      - name: Regenerate and compare the required static assets\n"
            "        run: uv run --frozen python tools/check_release.py assets\n"
        ),
        (
            "      - name: Regenerate and compare the required static assets\n"
            "        run: uv run --frozen python tools/check_release.py assets\n"
            "      - name: Probe the pinned Linux recording renderer (hash-verified, fail-closed)\n"
            "        # Proves the approved agg pin runs here; it does not render a GIF.\n"
            "        run: uv run --frozen python tools/check_release.py agg-version\n"
        ),
        "in that order",
    ),
    "assets-no-group": (
        "uv sync --frozen --group dev --group assets",
        "uv sync --frozen --group dev",
        "exact install command once",
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


def test_docs_gate_cannot_move_after_the_build(
    tool: types.ModuleType,
    workflow_text: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    gate = (
        "      - name: Validate release documentation before building\n"
        "        run: uv run --frozen python tools/check_release.py docs\n"
    )
    after_build = "      - name: Validate the built distributions and record checksums\n"
    assert workflow_text.count(gate) == workflow_text.count(after_build) == 1
    mutated = tmp_path / "publish-pypi.yml"
    mutated.write_text(
        workflow_text.replace(gate, "").replace(after_build, gate + after_build),
        encoding="utf-8",
    )
    code, out, err = run_main(tool, ["workflow", "--path", str(mutated)], capsys)
    assert code == 1
    assert out == ""
    assert "docs gate must precede building distributions" in err
