"""``release-receipt``, ``receipts``, ``candidate`` and ``docs`` gates.

The real repository must fail ``candidate``, ``docs`` and ``receipts`` today
because the v1 documentation, assets and receipts do not exist yet; the
fixture trees show exactly what makes each gate pass.
"""

from __future__ import annotations

import json
import types
from collections.abc import Callable
from pathlib import Path

import pytest
from release_support import (
    ROOT,
    commit_all,
    git,
    load_tool,
    names,
    png_bytes,
    readme_text,
    run_main,
    sha256_hex,
    write_fake_distributions,
    write_release_tree,
    write_sums,
    write_text,
)

VERSION = "1.0.0"
ARTIFACT_DIGEST = "sha256:" + "b" * 64


@pytest.fixture(scope="module")
def tool() -> types.ModuleType:
    return load_tool()


def failure(tool: types.ModuleType, root: Path, command: str) -> str:
    workflow = root / ".github" / "workflows" / "publish-pypi.yml"
    checks: dict[str, Callable[[], None]] = {
        "candidate": lambda: tool.check_candidate(root, workflow),
        "docs": lambda: tool.check_docs(root),
        "receipts": lambda: tool.check_receipts(root),
    }
    with pytest.raises(tool.ReleaseCheckError) as excinfo:
        checks[command]()
    return str(excinfo.value)


# --------------------------------------------------------------------------- #
# release-receipt
# --------------------------------------------------------------------------- #


def build_receipt_document(
    dist: Path, *, tag: str | None = f"v{VERSION}", commit: str | None = "c" * 40
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "kind": "actseal-build-receipt",
        "version": VERSION,
        "tag": tag,
        "ref": f"refs/tags/{tag}" if tag else "refs/heads/main",
        "source_commit": commit,
        "lock_sha256": "d" * 64,
        "workflow_run": {"id": "42", "attempt": "1"},
        "distributions": [
            {
                "filename": name,
                "size": (dist / name).stat().st_size,
                "sha256": sha256_hex((dist / name).read_bytes()),
            }
            for name in names(VERSION)
        ],
    }


def postpublish_document(
    dist: Path, *, ok: bool = True, hashes: dict[str, str] | None = None
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "kind": "actseal-postpublish-receipt",
        "version": VERSION,
        "index": "https://pypi.org",
        "ok": ok,
        "files": [
            {
                "filename": name,
                "sha256": (hashes or {}).get(name, sha256_hex((dist / name).read_bytes())),
                "provenance": {"present": True, "attestations": 1, "publishers": []},
            }
            for name in names(VERSION)
        ],
        "checks": {"demo_exit": 0, "fixed_replay_exit": 0, "bad_replay_exit": 1},
        "note": "Attestation presence and publisher identity were inspected.",
    }


@pytest.fixture
def receipt_inputs(tmp_path: Path) -> dict[str, Path]:
    dist = tmp_path / "dist"
    files = write_fake_distributions(dist, VERSION)
    sums = write_sums(tmp_path / "SHA256SUMS", files)
    build = write_text(tmp_path / "build-receipt.json", json.dumps(build_receipt_document(dist)))
    post = write_text(tmp_path / "postpublish-receipt.json", json.dumps(postpublish_document(dist)))
    return {
        "dist": dist,
        "sums": sums,
        "build": build,
        "post": post,
        "out": tmp_path / "release-receipt.json",
    }


def make_release_receipt(
    tool: types.ModuleType, inputs: dict[str, Path], **overrides: str
) -> dict[str, object]:
    arguments: dict[str, object] = {
        "version": VERSION,
        "dist": inputs["dist"],
        "sums_path": inputs["sums"],
        "build_receipt_path": inputs["build"],
        "postpublish_path": inputs["post"],
        "artifact_id": "987654321",
        "artifact_digest": ARTIFACT_DIGEST,
        "run_id": "42",
        "run_attempt": "1",
        "verify_result": "success",
        "out": inputs["out"],
    }
    arguments.update(overrides)
    document = tool.release_receipt(**arguments)
    return {str(key): value for key, value in document.items()}


def test_release_receipt_binds_artifact_identity_and_results(
    tool: types.ModuleType, receipt_inputs: dict[str, Path]
) -> None:
    receipt = make_release_receipt(tool, receipt_inputs)
    assert receipt["kind"] == "actseal-release-receipt"
    assert (receipt["version"], receipt["tag"], receipt["source_commit"]) == (
        VERSION,
        f"v{VERSION}",
        "c" * 40,
    )
    assert receipt["artifact"] == {"id": "987654321", "digest": ARTIFACT_DIGEST}
    assert receipt["workflow_run"] == {
        "id": "42",
        "attempt": "1",
        "url": "https://github.com/ajaysurya1221/actseal/actions/runs/42/attempts/1",
    }
    verification = receipt["verification"]
    assert isinstance(verification, dict)
    assert verification["verify_matrix"] == "success"
    assert verification["postpublish"]["checks"]["bad_replay_exit"] == 1
    assert json.loads(receipt_inputs["out"].read_text(encoding="utf-8")) == receipt
    assert "pypi-" not in json.dumps(receipt)


def release_receipt_failure(
    tool: types.ModuleType, inputs: dict[str, Path], **overrides: str
) -> str:
    with pytest.raises(tool.ReleaseCheckError) as excinfo:
        make_release_receipt(tool, inputs, **overrides)
    assert not inputs["out"].exists()
    return str(excinfo.value)


@pytest.mark.parametrize("verify_result", ["failure", "skipped", "cancelled", ""])
def test_non_success_verify_matrix_fails(
    tool: types.ModuleType, receipt_inputs: dict[str, Path], verify_result: str
) -> None:
    assert "verify matrix result" in release_receipt_failure(
        tool, receipt_inputs, verify_result=verify_result
    )


def test_missing_postpublish_receipt_is_not_promoted(
    tool: types.ModuleType, receipt_inputs: dict[str, Path]
) -> None:
    receipt_inputs["post"].unlink()
    assert "do not auto-promote missing receipts" in release_receipt_failure(tool, receipt_inputs)


def test_postpublish_not_ok_or_mismatched_hash_fails(
    tool: types.ModuleType, receipt_inputs: dict[str, Path]
) -> None:
    dist = receipt_inputs["dist"]
    receipt_inputs["post"].write_text(
        json.dumps(postpublish_document(dist, ok=False)), encoding="utf-8"
    )
    assert "did not record ok: true" in release_receipt_failure(tool, receipt_inputs)
    altered = {names(VERSION)[0]: "e" * 64}
    receipt_inputs["post"].write_text(
        json.dumps(postpublish_document(dist, hashes=altered)), encoding="utf-8"
    )
    assert "post-publication hashes differ" in release_receipt_failure(tool, receipt_inputs)


def test_build_receipt_without_tag_or_commit_fails(
    tool: types.ModuleType, receipt_inputs: dict[str, Path]
) -> None:
    dist = receipt_inputs["dist"]
    receipt_inputs["build"].write_text(
        json.dumps(build_receipt_document(dist, tag=None)), encoding="utf-8"
    )
    assert "build receipt tag" in release_receipt_failure(tool, receipt_inputs)
    receipt_inputs["build"].write_text(
        json.dumps(build_receipt_document(dist, commit=None)), encoding="utf-8"
    )
    assert "lacks a source commit" in release_receipt_failure(tool, receipt_inputs)


def test_altered_distribution_bytes_fail(
    tool: types.ModuleType, receipt_inputs: dict[str, Path]
) -> None:
    wheel = receipt_inputs["dist"] / names(VERSION)[0]
    wheel.write_bytes(wheel.read_bytes() + b"\0")
    assert "altered hash" in release_receipt_failure(tool, receipt_inputs)


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"artifact_id": "latest"}, "numeric Actions artifact ID"),
        ({"artifact_id": ""}, "numeric Actions artifact ID"),
        ({"artifact_digest": "b" * 64}, "sha256:<hex>"),
        ({"run_id": "x"}, "must be numeric"),
    ],
)
def test_malformed_artifact_identity_fails(
    tool: types.ModuleType,
    receipt_inputs: dict[str, Path],
    overrides: dict[str, str],
    fragment: str,
) -> None:
    assert fragment in release_receipt_failure(tool, receipt_inputs, **overrides)


def test_credential_shaped_strings_are_rejected(
    tool: types.ModuleType, receipt_inputs: dict[str, Path]
) -> None:
    document = postpublish_document(receipt_inputs["dist"])
    document["note"] = "token pypi-AgEIcHlwaS5vcmcCJDAwMDAwMDAwLTAwMDAtMDAwMA"
    receipt_inputs["post"].write_text(json.dumps(document), encoding="utf-8")
    assert "credential-shaped" in release_receipt_failure(tool, receipt_inputs)


# --------------------------------------------------------------------------- #
# receipts gate
# --------------------------------------------------------------------------- #


def write_receipt_tree(root: Path, tool: types.ModuleType) -> dict[str, object]:
    write_release_tree(root, VERSION)
    dist = root / "scratch-dist"
    files = write_fake_distributions(dist, VERSION)
    write_sums(root / tool.RECEIPT_PATHS["sha256sums"], files)
    post = postpublish_document(dist)
    write_text(root / tool.RECEIPT_PATHS["postpublish"], json.dumps(post))
    receipt = {
        "schema_version": 1,
        "kind": "actseal-release-receipt",
        "version": VERSION,
        "tag": f"v{VERSION}",
        "source_commit": "c" * 40,
        "lock_sha256": "d" * 64,
        "workflow_run": {"id": "42", "attempt": "1"},
        "artifact": {"id": "987654321", "digest": ARTIFACT_DIGEST},
        "distributions": [
            {
                "filename": name,
                "size": files[name].stat().st_size,
                "sha256": sha256_hex(files[name].read_bytes()),
            }
            for name in names(VERSION)
        ],
        "verification": {"verify_matrix": "success", "postpublish": post},
    }
    write_text(root / tool.RECEIPT_PATHS["release_receipt"], json.dumps(receipt))
    notes = [
        f"# Actseal {VERSION}",
        "![how-it-works](https://raw.githubusercontent.com/x/how-it-works.svg)",
    ]
    notes.append(f"https://pypi.org/project/actseal/{VERSION}/")
    notes.extend(
        f"- `{name}` sha256 `{sha256_hex(files[name].read_bytes())}`" for name in names(VERSION)
    )
    write_text(root / tool.RECEIPT_PATHS["release_notes"], "\n".join(notes) + "\n")
    write_text(root / tool.RECEIPT_PATHS["final_report"], "# Final report\n\nWorkflow run 42.\n")
    write_text(root / tool.RECEIPT_PATHS["launch"], "# Launch\n\nThis post remains a DRAFT.\n")
    for path in dist.iterdir():
        path.unlink()
    dist.rmdir()
    commit_all(root, "receipts")
    return receipt


def test_receipts_gate_fails_on_the_real_repository(tool: types.ModuleType) -> None:
    message = failure(tool, ROOT, "receipts")
    assert "plan/v1/receipts/release-receipt.json" in message
    assert "plan/v1/RELEASE_NOTES.md" in message


def test_receipts_gate_passes_on_a_complete_fixture(tool: types.ModuleType, tmp_path: Path) -> None:
    write_receipt_tree(tmp_path, tool)
    tool.check_receipts(tmp_path)


def test_release_note_claims_must_map_to_receipts(tool: types.ModuleType, tmp_path: Path) -> None:
    write_receipt_tree(tmp_path, tool)
    notes = tmp_path / tool.RECEIPT_PATHS["release_notes"]
    notes.write_text(
        notes.read_text(encoding="utf-8") + f"\nAlso `{'9' * 64}`.\n", encoding="utf-8"
    )
    assert "claim hashes absent from receipts" in failure(tool, tmp_path, "receipts")


def test_receipt_cross_checks_fail(tool: types.ModuleType, tmp_path: Path) -> None:
    write_receipt_tree(tmp_path, tool)
    sums = tmp_path / tool.RECEIPT_PATHS["sha256sums"]
    sums.write_text(sums.read_text(encoding="utf-8").replace("a", "b", 1), encoding="utf-8")
    assert "SHA256SUMS receipt differs" in failure(tool, tmp_path, "receipts")
    write_receipt_tree(tmp_path / "second", tool)
    report = tmp_path / "second" / tool.RECEIPT_PATHS["final_report"]
    report.write_text("# Final report\n", encoding="utf-8")
    assert "omits the workflow run id" in failure(tool, tmp_path / "second", "receipts")
    report.write_text("# Final report\n\nWorkflow run 42.\n", encoding="utf-8")
    launch = tmp_path / "second" / tool.RECEIPT_PATHS["launch"]
    launch.write_text("# Launch\n\nPosted.\n", encoding="utf-8")
    assert "must remain a draft" in failure(tool, tmp_path / "second", "receipts")


# --------------------------------------------------------------------------- #
# docs gate
# --------------------------------------------------------------------------- #


def test_docs_gate_fails_on_the_real_repository_today(tool: types.ModuleType) -> None:
    message = failure(tool, ROOT, "docs")
    assert "docs/stability.md" in message
    assert "absolute https:// links" in message


def test_docs_gate_passes_on_the_fixture_tree(tool: types.ModuleType, tmp_path: Path) -> None:
    write_release_tree(tmp_path)
    tool.check_docs(tmp_path)


@pytest.mark.parametrize(
    ("mutation", "fragment"),
    [
        (lambda root: (root / "docs" / "stability.md").unlink(), "missing required files"),
        (
            lambda root: (root / "README.md").write_text(
                readme_text().replace("https://pypi.org/project/actseal/", "docs/x.md"),
                encoding="utf-8",
            ),
            "absolute https:// links",
        ),
        (
            lambda root: (root / "README.md").write_text(readme_text("MISSING"), encoding="utf-8"),
            "links to missing file",
        ),
        (
            lambda root: (root / "README.md").write_text(
                readme_text().replace("Windows", "Linux"), encoding="utf-8"
            ),
            "Windows",
        ),
        (
            lambda root: (root / "README.md").write_text(
                readme_text().replace("--offline ", ""), encoding="utf-8"
            ),
            "lacks quickstart command",
        ),
        (
            lambda root: (root / "docs" / "quickstart.md").write_text(
                "[gone](missing.md)\n", encoding="utf-8"
            ),
            "broken relative links",
        ),
        (
            lambda root: (root / "docs" / "publishing.md").write_text(
                "Run gh workflow run -f publish=true\n", encoding="utf-8"
            ),
            "still documents",
        ),
        (
            lambda root: (root / "CHANGELOG.md").write_text("## v0.1.0\n", encoding="utf-8"),
            "no heading for 1.0.0",
        ),
    ],
)
def test_each_docs_rule_rejects_its_mutation(
    tool: types.ModuleType, tmp_path: Path, mutation: object, fragment: str
) -> None:
    write_release_tree(tmp_path)
    assert callable(mutation)
    mutation(tmp_path)
    assert fragment in failure(tool, tmp_path, "docs")


# --------------------------------------------------------------------------- #
# candidate gate
# --------------------------------------------------------------------------- #


def test_candidate_fails_clearly_on_the_real_repository_today(
    tool: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, err = run_main(tool, ["candidate"], capsys)
    assert (code, out) == (1, "")
    assert err.startswith("release check failed: candidate gate has ")
    assert "release candidate version must be >= 1.0.0" in err
    assert "docs/schemas/" in err
    assert "docs/assets/social-preview.png" in err


def test_candidate_passes_on_a_complete_clean_fixture(
    tool: types.ModuleType, tmp_path: Path
) -> None:
    write_release_tree(tmp_path)
    tool.check_candidate(tmp_path, tmp_path / ".github" / "workflows" / "publish-pypi.yml")


def test_candidate_rejects_dirty_tree_wrong_png_and_misplaced_tag(
    tool: types.ModuleType, tmp_path: Path
) -> None:
    head = write_release_tree(tmp_path)
    (tmp_path / "scratch.txt").write_text("x\n", encoding="utf-8")
    assert "working tree must be clean" in failure(tool, tmp_path, "candidate")
    (tmp_path / "scratch.txt").unlink()
    (tmp_path / "docs" / "assets" / "social-preview.png").write_bytes(png_bytes(1200, 630))
    commit_all(tmp_path, "wrong png")
    assert "social preview is (1200, 630)" in failure(tool, tmp_path, "candidate")
    (tmp_path / "docs" / "assets" / "social-preview.png").write_bytes(png_bytes(1280, 640))
    commit_all(tmp_path, "right png")
    git(tmp_path, "tag", f"v{VERSION}", head)
    assert "does not point at HEAD" in failure(tool, tmp_path, "candidate")


def test_candidate_lists_every_unmet_requirement(tool: types.ModuleType, tmp_path: Path) -> None:
    write_release_tree(tmp_path, version="0.9.0")
    (tmp_path / "docs" / "schemas" / "lock.schema.json").unlink()
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n\n## v0.8.0\n", encoding="utf-8")
    commit_all(tmp_path, "regress")
    message = failure(tool, tmp_path, "candidate")
    assert "must be >= 1.0.0, not 0.9.0" in message
    assert "docs/schemas/ must contain JSON schemas" in message
    assert "no heading for 0.9.0" in message
