"""``release-receipt``, ``receipts``, ``candidate``, ``assets`` and ``docs`` gates.

Every gate is exercised on deliberately complete and deliberately incomplete
temporary fixtures, so the tests stay valid once the real repository gains its
v1 documentation, assets and receipts. The real checkout is only smoke-run.
"""

from __future__ import annotations

import json
import types
from collections.abc import Callable
from pathlib import Path

import pytest
from release_support import (
    PUBLISHER,
    ROOT,
    STABLE,
    build_receipt_document,
    commit_all,
    git,
    load_tool,
    names,
    picture_markup,
    png_bytes,
    postpublish_document,
    readme_text,
    release_receipt_document,
    run_main,
    sha256_hex,
    write_fake_distributions,
    write_fake_renderer,
    write_incomplete_tree,
    write_json,
    write_release_tree,
    write_sums,
    write_text,
    write_version_sources,
)

VERSION = "1.0.0"
BARE_DIGEST = "b" * 64
RAW = "https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets"


@pytest.fixture(scope="module")
def tool() -> types.ModuleType:
    return load_tool()


def renderer(root: Path) -> str:
    return str(root / "docs" / "assets" / "src" / "render.py")


def failure(tool: types.ModuleType, root: Path, command: str) -> str:
    workflow = root / ".github" / "workflows" / "publish-pypi.yml"
    checks: dict[str, Callable[[], None]] = {
        "candidate": lambda: tool.check_candidate(root, workflow, renderer(root)),
        "assets": lambda: tool.check_assets(root, renderer(root)),
        "docs": lambda: tool.check_docs(root),
        "receipts": lambda: tool.check_receipts(root),
    }
    with pytest.raises(tool.ReleaseCheckError) as excinfo:
        checks[command]()
    return str(excinfo.value)


# --------------------------------------------------------------------------- #
# release-receipt
# --------------------------------------------------------------------------- #


@pytest.fixture
def receipt_inputs(tmp_path: Path) -> dict[str, Path]:
    dist = tmp_path / "dist"
    files = write_fake_distributions(dist, VERSION)
    return {
        "dist": dist,
        "sums": write_sums(tmp_path / "SHA256SUMS", files),
        "build": write_json(
            tmp_path / "build-receipt.json", build_receipt_document(VERSION, files)
        ),
        "post": write_json(
            tmp_path / "postpublish-receipt.json", postpublish_document(VERSION, files)
        ),
        "out": tmp_path / "release-receipt.json",
    }


def files_of(inputs: dict[str, Path]) -> dict[str, Path]:
    return {name: inputs["dist"] / name for name in names(VERSION)}


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
        "artifact_digest": BARE_DIGEST,
        "run_id": "42",
        "run_attempt": "1",
        "verify_result": "success",
        "out": inputs["out"],
    }
    arguments.update(overrides)
    document = tool.release_receipt(**arguments)
    return {str(key): value for key, value in document.items()}


def release_receipt_failure(
    tool: types.ModuleType, inputs: dict[str, Path], **overrides: str
) -> str:
    with pytest.raises(tool.ReleaseCheckError) as excinfo:
        make_release_receipt(tool, inputs, **overrides)
    assert not inputs["out"].exists()
    return str(excinfo.value)


def rewrite(path: Path, mutate: Callable[[dict[str, object]], None]) -> None:
    document = json.loads(path.read_text(encoding="utf-8"))
    mutate(document)
    path.write_text(json.dumps(document), encoding="utf-8")


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
    assert receipt["lock_sha256"] == "d" * 64
    assert receipt["artifact"] == {"id": "987654321", "digest": f"sha256:{BARE_DIGEST}"}
    assert receipt["workflow_run"] == {
        "id": "42",
        "build_attempt": "1",
        "verification_attempt": "1",
        "build_url": "https://github.com/ajaysurya1221/actseal/actions/runs/42/attempts/1",
        "verification_url": "https://github.com/ajaysurya1221/actseal/actions/runs/42/attempts/1",
    }
    verification = receipt["verification"]
    assert isinstance(verification, dict)
    assert verification["verify_matrix"] == "success"
    post = verification["postpublish"]
    assert post["checks"]["bad_replay_exit"] == 1
    assert post["published_metadata"]["version"] == VERSION
    assert [f["provenance"]["publishers"] for f in post["files"]] == [[PUBLISHER], [PUBLISHER]]
    assert json.loads(receipt_inputs["out"].read_text(encoding="utf-8")) == receipt
    assert tool.validate_release_receipt(receipt, VERSION, None)
    assert "pypi-" not in json.dumps(receipt)


def test_rerun_keeps_build_and_verification_attempts_apart(
    tool: types.ModuleType, receipt_inputs: dict[str, Path]
) -> None:
    receipt = make_release_receipt(tool, receipt_inputs, run_attempt="3")
    run = receipt["workflow_run"]
    assert isinstance(run, dict)
    assert (run["build_attempt"], run["verification_attempt"]) == ("1", "3")
    assert run["build_url"].endswith("/attempts/1")
    assert run["verification_url"].endswith("/attempts/3")


@pytest.mark.parametrize(
    ("digest", "fragment"),
    [
        ("sha256:" + BARE_DIGEST, "bare 64-hex"),
        (BARE_DIGEST[:-1], "bare 64-hex"),
        ("", "bare 64-hex"),
        (BARE_DIGEST.upper(), "bare 64-hex"),
        (BARE_DIGEST + "\n", "bare 64-hex"),
        (" " + BARE_DIGEST, "bare 64-hex"),
        (BARE_DIGEST + " ", "bare 64-hex"),
    ],
)
def test_artifact_digest_must_be_the_actions_bare_hex_output(
    tool: types.ModuleType, receipt_inputs: dict[str, Path], digest: str, fragment: str
) -> None:
    assert fragment in release_receipt_failure(tool, receipt_inputs, artifact_digest=digest)
    assert tool.normalize_artifact_digest(BARE_DIGEST) == f"sha256:{BARE_DIGEST}"


@pytest.mark.parametrize(
    ("value", "pattern"),
    [
        ("a" * 64 + "\n", "HEX64_RE"),
        ("a" * 40 + "\n", "GIT_SHA_RE"),
        ("1.0.0\n", "VERSION_RE"),
        ("\n" + "a" * 64, "HEX64_RE"),
    ],
)
def test_identity_patterns_match_whole_strings_only(
    tool: types.ModuleType, value: str, pattern: str
) -> None:
    assert getattr(tool, pattern).fullmatch(value) is None
    assert getattr(tool, pattern).fullmatch(value.strip()) is not None
    if pattern == "VERSION_RE":
        with pytest.raises(tool.ReleaseCheckError):
            tool.parse_version(value)


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


def set_key(*path: str, value: object) -> Callable[[dict[str, object]], None]:
    def mutate(document: dict[str, object]) -> None:
        target: object = document
        for key in path[:-1]:
            assert isinstance(target, dict)
            target = target[key]
        assert isinstance(target, dict)
        target[path[-1]] = value

    return mutate


def break_first_file(key: str, value: object) -> Callable[[dict[str, object]], None]:
    def mutate(document: dict[str, object]) -> None:
        files = document["files"]
        assert isinstance(files, list)
        files[0][key] = value

    return mutate


@pytest.mark.parametrize(
    ("mutate", "fragment"),
    [
        (set_key("source_commit", value="not-a-sha"), "full 40-hex source commit"),
        (set_key("source_commit", value=None), "full 40-hex source commit"),
        (set_key("source_commit", value="c" * 40 + "\n"), "full 40-hex source commit"),
        (set_key("schema_version", value=True), "schema_version must be the integer 1"),
        (set_key("lock_sha256", value="d" * 64 + "\n"), "lock_sha256 must be a 64-hex"),
        (set_key("lock_sha256", value=None), "lock_sha256 must be a 64-hex"),
        (set_key("distributions", value=[]), "distributions must not be empty"),
        (set_key("tag", value=None), "build receipt tag"),
        (set_key("ref", value="refs/heads/main"), "ref is"),
        (set_key("workflow_run", "id", value="41"), "belongs to run 41"),
        (set_key("workflow_run", "attempt", value="2"), "later than verification attempt"),
        (set_key("workflow_run", value=None), "workflow_run must be an object"),
        (set_key("kind", value="actseal-release-receipt"), "kind is wrong"),
    ],
)
def test_build_receipt_evidence_is_validated(
    tool: types.ModuleType,
    receipt_inputs: dict[str, Path],
    mutate: Callable[[dict[str, object]], None],
    fragment: str,
) -> None:
    rewrite(receipt_inputs["build"], mutate)
    assert fragment in release_receipt_failure(tool, receipt_inputs)


def test_build_inventory_must_match_the_actual_distributions(
    tool: types.ModuleType, receipt_inputs: dict[str, Path]
) -> None:
    def shrink(document: dict[str, object]) -> None:
        inventory = document["distributions"]
        assert isinstance(inventory, list)
        inventory[0]["size"] = inventory[0]["size"] + 1

    rewrite(receipt_inputs["build"], shrink)
    assert "inventory" in release_receipt_failure(tool, receipt_inputs)


@pytest.mark.parametrize(
    ("mutate", "fragment"),
    [
        (set_key("ok", value=False), "did not record ok: true"),
        (set_key("checks", "demo_exit", value=99), "demo_exit is 99"),
        (set_key("checks", "bad_replay_exit", value=0), "bad_replay_exit is 0"),
        (set_key("checks", "fixed_replay_exit", value=1), "fixed_replay_exit is 1"),
        (set_key("checks", "demo_bad_status", value="PASS"), "demo_bad_status is 'PASS'"),
        (
            set_key("checks", "installed_outside_checkout", value=False),
            "installed_outside_checkout",
        ),
        (set_key("checks", "version_output", value="actseal 0.1.0"), "version_output is"),
        (set_key("checks", "demo_exit", value=True), "demo_exit is True"),
        (set_key("note", value="Signatures were cryptographically verified."), "not verbatim"),
        (set_key("published_metadata", "classifiers", value=[]), "lacks classifier"),
        (set_key("published_metadata", "classifiers", value=STABLE), "classifiers must be a list"),
        (set_key("published_metadata", "version", value="1.0.1"), "version is '1.0.1'"),
        (set_key("published_metadata", "yanked", value=True), "is yanked"),
        (set_key("published_metadata", "summary", value=" "), "summary is missing"),
        (set_key("published_metadata", "extra", value="x"), "keys must be exactly"),
        (set_key("index", value="file:///not-pypi"), "not official https://pypi.org"),
        (set_key("index", value="https://test.pypi.org"), "not official https://pypi.org"),
        (set_key("schema_version", value=True), "schema_version must be the integer 1"),
        (break_first_file("url", "https://example.invalid/x.whl"), "not an official PyPI file URL"),
        (break_first_file("sha256", "e" * 64), "inventory"),
        (break_first_file("size", 1), "inventory"),
        (break_first_file("declared_sha256", "e" * 64), "declared digest"),
        (break_first_file("matches_build", False), "matches_build"),
        (break_first_file("provenance", {"present": False}), "provenance not present"),
        (
            break_first_file(
                "provenance",
                {
                    "present": True,
                    "attestations": 0,
                    "publishers": [PUBLISHER],
                    "subject_sha256": None,
                },
            ),
            "no attestations inspected",
        ),
        (
            break_first_file(
                "provenance",
                {
                    "present": True,
                    "attestations": True,
                    "publishers": [PUBLISHER],
                    "subject_sha256": None,
                },
            ),
            "no attestations inspected (True)",
        ),
        (
            break_first_file(
                "provenance",
                {
                    "present": True,
                    "attestations": 1,
                    "publishers": [{**PUBLISHER, "repository": "someone/else"}],
                    "subject_sha256": None,
                },
            ),
            "not the expected trusted publisher",
        ),
        (
            break_first_file(
                "provenance",
                {
                    "present": True,
                    "attestations": 1,
                    "publishers": [PUBLISHER],
                    "subject_sha256": "0" * 64,
                },
            ),
            "subject digest differs",
        ),
    ],
)
def test_postpublish_evidence_is_validated(
    tool: types.ModuleType,
    receipt_inputs: dict[str, Path],
    mutate: Callable[[dict[str, object]], None],
    fragment: str,
) -> None:
    rewrite(receipt_inputs["post"], mutate)
    assert fragment in release_receipt_failure(tool, receipt_inputs)


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
        ({"run_id": "x"}, "must be numeric"),
        ({"run_attempt": "0x1"}, "must be numeric"),
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
    rewrite(
        receipt_inputs["post"],
        set_key("index", value="pypi-AgEIcHlwaS5vcmcCJDAwMDAwMDAwLTAwMDAtMDAwMA"),
    )
    assert "credential-shaped" in release_receipt_failure(tool, receipt_inputs)
    rewrite(receipt_inputs["post"], set_key("index", value="https://pypi.org"))
    rewrite(
        receipt_inputs["build"], set_key("ref", value="Bearer ghp_abcdefghijklmnopqrstuvwxyz0123")
    )
    assert "credential-shaped" in release_receipt_failure(tool, receipt_inputs)


# --------------------------------------------------------------------------- #
# receipts gate
# --------------------------------------------------------------------------- #


PATCH = "1.0.1"
HISTORICAL_PATHS = {
    "release_receipt": "plan/v1/receipts/release-receipt.json",
    "sha256sums": "plan/v1/receipts/SHA256SUMS",
    "postpublish": "plan/v1/receipts/postpublish-receipt.json",
    "release_notes": "plan/v1/RELEASE_NOTES.md",
    "final_report": "plan/v1/FINAL_REPORT.md",
    "launch": "plan/v1/LAUNCH.md",
}
PATCH_PATHS = {
    "release_receipt": "plan/v1/releases/1.0.1/release-receipt.json",
    "sha256sums": "plan/v1/releases/1.0.1/SHA256SUMS",
    "postpublish": "plan/v1/releases/1.0.1/postpublish-receipt.json",
    "release_notes": "plan/v1/releases/1.0.1/RELEASE_NOTES.md",
    "final_report": "plan/v1/releases/1.0.1/FINAL_REPORT.md",
}
PATCH_RECEIPTS = ("release_receipt", "sha256sums", "postpublish")


def write_release_documents(
    root: Path, paths: dict[str, str], version: str, hash_lines: list[str]
) -> None:
    """Release notes and final report (plus the 1.0.0 launch draft) for ``version``."""
    notes = [
        f"# Actseal {version}",
        f"![how-it-works]({RAW}/how-it-works-light.svg)",
        f"https://pypi.org/project/actseal/{version}/",
        *hash_lines,
    ]
    write_text(root / paths["release_notes"], "\n".join(notes) + "\n")
    write_text(root / paths["final_report"], "# Final report\n\nWorkflow run 42.\n")
    if "launch" in paths:
        write_text(root / paths["launch"], "# Launch\n\nThis post remains a DRAFT.\n")


def write_receipt_tree(
    root: Path, tool: types.ModuleType, version: str = VERSION
) -> dict[str, object]:
    """A tree whose receipts and documents sit at ``receipt_paths(version)``."""
    paths = tool.receipt_paths(version)
    write_release_tree(root, version)
    dist = root / "scratch-dist"
    files = write_fake_distributions(dist, version)
    write_sums(root / paths["sha256sums"], files)
    write_json(root / paths["postpublish"], postpublish_document(version, files))
    receipt = release_receipt_document(version, files)
    write_json(root / paths["release_receipt"], receipt)
    hash_lines = [
        f"- `{name}` sha256 `{sha256_hex(files[name].read_bytes())}`" for name in names(version)
    ]
    write_release_documents(root, paths, version, hash_lines)
    for path in dist.iterdir():
        path.unlink()
    dist.rmdir()
    commit_all(root, "receipts")
    return receipt


def test_receipts_gate_fails_on_an_incomplete_tree(tool: types.ModuleType, tmp_path: Path) -> None:
    write_incomplete_tree(tmp_path)
    message = failure(tool, tmp_path, "receipts")
    assert "plan/v1/receipts/release-receipt.json" in message
    assert "plan/v1/RELEASE_NOTES.md" in message


def test_receipts_gate_passes_on_a_complete_fixture(tool: types.ModuleType, tmp_path: Path) -> None:
    write_receipt_tree(tmp_path, tool)
    tool.check_receipts(tmp_path)


def test_receipt_paths_keep_1_0_0_history_and_give_later_versions_their_own_directory(
    tool: types.ModuleType,
) -> None:
    assert tool.receipt_paths("1.0.0") == HISTORICAL_PATHS
    assert tool.receipt_paths(PATCH) == PATCH_PATHS
    assert "launch" not in tool.receipt_paths(PATCH)  # a patch release has no launch post
    assert set(tool.receipt_paths("1.1.0").values()) == {
        path.replace("1.0.1", "1.1.0") for path in PATCH_PATHS.values()
    }
    assert tool.receipt_paths("0.1.0") == HISTORICAL_PATHS  # unchanged pre-1.0 resolution
    with pytest.raises(tool.ReleaseCheckError, match=r"not a plain MAJOR\.MINOR\.PATCH"):
        tool.receipt_paths("1.0.1/../../x")


def test_receipts_gate_passes_on_a_complete_1_0_1_fixture(
    tool: types.ModuleType, tmp_path: Path
) -> None:
    write_receipt_tree(tmp_path, tool, PATCH)
    tool.check_receipts(tmp_path)
    assert not (tmp_path / "plan" / "v1" / "receipts").exists()
    assert not (tmp_path / "plan" / "v1" / "LAUNCH.md").exists()


def test_a_1_0_1_tree_carrying_only_1_0_0_receipts_names_the_missing_1_0_1_paths(
    tool: types.ModuleType, tmp_path: Path
) -> None:
    write_receipt_tree(tmp_path, tool, VERSION)
    write_version_sources(tmp_path, PATCH)
    commit_all(tmp_path, "bump to 1.0.1 without 1.0.1 receipts")
    message = failure(tool, tmp_path, "receipts")
    assert "missing required files" in message
    for path in PATCH_PATHS.values():
        assert path in message, path
    assert "do not auto-promote missing receipts" in message
    for path in HISTORICAL_PATHS.values():
        assert (tmp_path / path).is_file(), path  # present, but not accepted for 1.0.1


def test_pre_publication_1_0_1_tree_fails_only_on_its_missing_receipts(
    tool: types.ModuleType, tmp_path: Path
) -> None:
    """Notes and report exist with named placeholders; only the receipts are absent."""
    write_release_tree(tmp_path, PATCH)
    hash_lines = ["- `actseal-1.0.1-py3-none-any.whl` sha256 `<<build.wheel.sha256>>`"]
    write_release_documents(tmp_path, PATCH_PATHS, PATCH, hash_lines)
    report = tmp_path / PATCH_PATHS["final_report"]
    report.write_text("# Final report\n\nWorkflow run <<build.run_id>>.\n", encoding="utf-8")
    commit_all(tmp_path, "pre-tag notes")
    message = failure(tool, tmp_path, "receipts")
    assert "receipts gate has 3 unmet requirement(s)" in message
    for key in PATCH_RECEIPTS:
        assert PATCH_PATHS[key] in message, key
    for key in ("release_notes", "final_report"):
        assert PATCH_PATHS[key] not in message, key
    assert "release notes cannot be checked against missing receipts" in message
    for absent in ("PyPI link", "how-it-works", "placeholders", "launch"):
        assert absent not in message, absent


@pytest.mark.parametrize("document", ["release_notes", "final_report"])
def test_unfilled_placeholders_fail_the_final_receipt_gate(
    tool: types.ModuleType, tmp_path: Path, document: str
) -> None:
    write_receipt_tree(tmp_path, tool, PATCH)
    path = tmp_path / PATCH_PATHS[document]
    path.write_text(
        path.read_text(encoding="utf-8") + "Recording: <<post.recording>>.\n", encoding="utf-8"
    )
    message = failure(tool, tmp_path, "receipts")
    assert "keep unfilled placeholders: ['<<post.recording>>']" in message


def test_1_0_1_release_notes_and_report_are_cross_checked(
    tool: types.ModuleType, tmp_path: Path
) -> None:
    write_receipt_tree(tmp_path, tool, PATCH)
    notes = tmp_path / PATCH_PATHS["release_notes"]
    original = notes.read_text(encoding="utf-8")
    notes.write_text(original.replace("/1.0.1/", "/1.0.0/"), encoding="utf-8")
    assert "release notes lack the PyPI link" in failure(tool, tmp_path, "receipts")
    notes.write_text(original + f"\nAlso `{'9' * 64}`.\n", encoding="utf-8")
    assert "claim hashes absent from receipts" in failure(tool, tmp_path, "receipts")
    notes.write_text(original, encoding="utf-8")
    report = tmp_path / PATCH_PATHS["final_report"]
    report.write_text("# Final report\n", encoding="utf-8")
    assert "omits the workflow run id" in failure(tool, tmp_path, "receipts")


RELEASES = ROOT / "plan" / "v1" / "releases"
PLACEHOLDER_SECTION = "## Placeholders filled after publication"


def committed_releases() -> list[str]:
    return sorted(path.name for path in RELEASES.iterdir() if path.is_dir())


@pytest.mark.parametrize("version", committed_releases())
def test_committed_release_documents_name_every_placeholder_once(
    tool: types.ModuleType, version: str
) -> None:
    """Pre-publication notes list each placeholder once; filled notes keep none.

    The gate rejects a full SHA-256 that no receipt holds, so while the
    receipts are absent the notes may not carry any 64-hex value at all.
    """
    paths = tool.receipt_paths(version)
    assert "launch" not in paths
    notes = (ROOT / paths["release_notes"]).read_text(encoding="utf-8")
    report = (ROOT / paths["final_report"]).read_text(encoding="utf-8")
    assert f"https://pypi.org/project/actseal/{version}/" in notes
    assert "how-it-works" in notes
    used = set(tool.PLACEHOLDER_RE.findall(notes)) | set(tool.PLACEHOLDER_RE.findall(report))
    if not used:
        assert PLACEHOLDER_SECTION not in notes
        return
    assert not (ROOT / paths["release_receipt"]).exists()
    assert tool.SHA256_HEX_RE.findall(notes) == []
    assert "<<build.run_id>>" in report  # the gate needs the run id in the report
    body, section, table = notes.partition(PLACEHOLDER_SECTION)
    assert section, "placeholders need their fill table"
    assert "\n## " not in table, "the fill table must be the last section"
    rows = [line for line in table.splitlines() if line.startswith("| `<<")]
    listed = [row.split("|")[1].strip().strip("`") for row in rows]
    assert len(listed) == len(set(listed)), "each placeholder is listed once"
    assert set(listed) == used
    assert set(tool.PLACEHOLDER_RE.findall(body)) | set(tool.PLACEHOLDER_RE.findall(report)) == set(
        listed
    ), "every listed placeholder is used"
    for marker in ("PENDING", "DRAFT", "TODO", "TBD", "nreleased"):
        assert marker not in notes + report, marker


RUNS = "https://github.com/ajaysurya1221/actseal/actions/runs"


@pytest.mark.parametrize(
    ("mutate", "fragment"),
    [
        (set_key("workflow_run", "build_url", value=f"{RUNS}/41/attempts/1"), "build_url is"),
        (set_key("workflow_run", "build_url", value=f"{RUNS}/42/attempts/2"), "build_url is"),
        (set_key("workflow_run", "build_url", value=None), "build_url is"),
        (
            set_key("workflow_run", "verification_url", value="https://evil.invalid/42/attempts/1"),
            "verification_url is",
        ),
        (set_key("workflow_run", "verification_url", value=None), "verification_url is"),
        (set_key("schema_version", value=True), "schema_version must be the integer 1"),
        (set_key("source_commit", value="c" * 40 + "\n"), "full 40-hex commit"),
        (set_key("artifact", "digest", value="sha256:" + "b" * 64 + "\n"), "sha256:<64 hex>"),
        (set_key("verification", "postpublish", "index", value="file:///not-pypi"), "not official"),
        (
            set_key("verification", "postpublish", "published_metadata", "yanked", value=True),
            "is yanked",
        ),
        (
            set_key(
                "verification", "postpublish", "published_metadata", "classifiers", value=STABLE
            ),
            "classifiers must be a list",
        ),
    ],
)
def test_release_receipt_identity_and_metadata_are_revalidated_strictly(
    tool: types.ModuleType,
    tmp_path: Path,
    mutate: Callable[[dict[str, object]], None],
    fragment: str,
) -> None:
    receipt = write_receipt_tree(tmp_path, tool)
    document = {str(key): value for key, value in receipt.items()}
    mutate(document)
    with pytest.raises(tool.ReleaseCheckError) as excinfo:
        tool.validate_release_receipt(document, VERSION, None)
    assert fragment in str(excinfo.value)
    rewrite(tmp_path / tool.receipt_paths(VERSION)["release_receipt"], mutate)
    assert fragment in failure(tool, tmp_path, "receipts")


def test_release_note_claims_must_map_to_receipts(tool: types.ModuleType, tmp_path: Path) -> None:
    write_receipt_tree(tmp_path, tool)
    notes = tmp_path / tool.receipt_paths(VERSION)["release_notes"]
    notes.write_text(
        notes.read_text(encoding="utf-8") + f"\nAlso `{'9' * 64}`.\n", encoding="utf-8"
    )
    assert "claim hashes absent from receipts" in failure(tool, tmp_path, "receipts")


def test_receipt_cross_checks_fail(tool: types.ModuleType, tmp_path: Path) -> None:
    write_receipt_tree(tmp_path, tool)
    sums = tmp_path / tool.receipt_paths(VERSION)["sha256sums"]
    original = sums.read_text(encoding="utf-8")
    sums.write_text(original.replace("a", "b", 1), encoding="utf-8")
    assert "SHA256SUMS receipt differs" in failure(tool, tmp_path, "receipts")
    sums.write_text(original, encoding="utf-8")
    receipt = tmp_path / tool.receipt_paths(VERSION)["release_receipt"]
    rewrite(receipt, set_key("verification", "postpublish", "checks", "demo_exit", value=99))
    assert "demo_exit is 99" in failure(tool, tmp_path, "receipts")
    rewrite(receipt, set_key("verification", "postpublish", "checks", "demo_exit", value=0))
    rewrite(receipt, set_key("source_commit", value="not-a-sha"))
    assert "full 40-hex commit" in failure(tool, tmp_path, "receipts")
    rewrite(receipt, set_key("source_commit", value="c" * 40))
    report = tmp_path / tool.receipt_paths(VERSION)["final_report"]
    report.write_text("# Final report\n", encoding="utf-8")
    assert "omits the workflow run id" in failure(tool, tmp_path, "receipts")
    report.write_text("# Final report\n\nWorkflow run 42.\n", encoding="utf-8")
    launch = tmp_path / tool.receipt_paths(VERSION)["launch"]
    launch.write_text("# Launch\n\nPosted.\n", encoding="utf-8")
    assert "must remain a draft" in failure(tool, tmp_path, "receipts")


# --------------------------------------------------------------------------- #
# docs gate
# --------------------------------------------------------------------------- #


def test_docs_gate_fails_on_an_incomplete_tree(tool: types.ModuleType, tmp_path: Path) -> None:
    write_incomplete_tree(tmp_path)
    message = failure(tool, tmp_path, "docs")
    assert "docs/stability.md" in message
    assert "absolute https:// links" in message
    assert "still documents" in message


def test_docs_gate_passes_on_the_fixture_tree(tool: types.ModuleType, tmp_path: Path) -> None:
    write_release_tree(tmp_path)
    tool.check_docs(tmp_path)


def test_opening_copy_is_the_same_in_the_gate_the_fixture_and_the_readme(
    tool: types.ModuleType,
) -> None:
    """The gate's approved opening, the fixture README and the real README cannot drift."""
    real = (Path(__file__).resolve().parents[2] / "README.md").read_text(encoding="utf-8")
    for copy in (tool.README_TAGLINE, tool.README_DESCRIPTION):
        assert copy in readme_text()
        assert copy in real
    assert "verifies model-chosen application actions" not in tool.README_DESCRIPTION


def test_html_picture_markup_with_absolute_same_repo_sources_passes(
    tool: types.ModuleType, tmp_path: Path
) -> None:
    write_release_tree(tmp_path)
    picture = picture_markup(f"{RAW}/hero-dark.svg", f"{RAW}/hero-light.svg")
    (tmp_path / "README.md").write_text(readme_text(picture=picture), encoding="utf-8")
    tool.check_docs(tmp_path)
    targets = tool.link_targets(picture)
    assert targets.count(f"{RAW}/hero-dark.svg") == 2
    assert f"{RAW}/hero-light.svg" in targets


@pytest.mark.parametrize(
    ("picture", "fragment"),
    [
        (picture_markup("docs/assets/hero-dark.svg", f"{RAW}/hero-light.svg"), "absolute https://"),
        (picture_markup(f"{RAW}/hero-dark.svg", "docs/assets/hero-light.svg"), "absolute https://"),
        (
            picture_markup(f"{RAW}/missing-dark.svg", f"{RAW}/hero-light.svg"),
            "links to missing file",
        ),
        (
            picture_markup(f"{RAW}/hero-dark.svg", f"{RAW}/missing-light.svg"),
            "links to missing file",
        ),
        ('<a href="docs/quickstart.md">quickstart</a>\n', "absolute https://"),
        ("<img src='docs/assets/hero-light.svg' alt=\"a > b\">\n", "absolute https://"),
    ],
)
def test_html_link_forms_are_not_skipped(
    tool: types.ModuleType, tmp_path: Path, picture: str, fragment: str
) -> None:
    write_release_tree(tmp_path)
    (tmp_path / "README.md").write_text(readme_text(picture=picture), encoding="utf-8")
    assert fragment in failure(tool, tmp_path, "docs")


BLOB = "https://github.com/ajaysurya1221/actseal/blob/main"


@pytest.mark.parametrize(
    "markup",
    [
        f"See [the quickstart]({BLOB}/docs/quickstart.md#one-command-first-run).\n",
        f"See [the quickstart]({BLOB}/docs/quickstart.md?plain=1#top).\n",
        f"See [the quickstart]({BLOB}/docs/quick%73tart.md#anchor).\n",
        f"![hero]({RAW}/hero-light.svg?raw=true)\n",
        (
            f'<a\n   href="{BLOB}/docs/quickstart.md#one-command-first-run"\n'
            '   title="a > b">docs</a>\n'
        ),
        f"<a href='{BLOB}/docs/quickstart.md#x'>docs</a>\n",
    ],
)
def test_same_repository_links_with_anchors_and_encoding_resolve(
    tool: types.ModuleType, tmp_path: Path, markup: str
) -> None:
    write_release_tree(tmp_path)
    (tmp_path / "README.md").write_text(readme_text(picture=markup), encoding="utf-8")
    tool.check_docs(tmp_path)


@pytest.mark.parametrize(
    ("markup", "fragment"),
    [
        (f"[gone]({BLOB}/docs/absent.md#anchor)\n", "links to missing file docs/absent.md"),
        (f"[gone]({BLOB}/docs/abs%65nt.md)\n", "links to missing file docs/absent.md"),
        (
            f'<a\n   href="{BLOB}/docs/absent.md#x">docs</a>\n',
            "links to missing file docs/absent.md",
        ),
        ("[local](docs/quickstart.md#one-command-first-run)\n", "absolute https://"),
        ("[local](#top)\n", "absolute https://"),
        (f"[escape]({BLOB}/docs/../pyproject.toml)\n", "links to missing file"),
    ],
)
def test_anchors_do_not_hide_missing_or_relative_targets(
    tool: types.ModuleType, tmp_path: Path, markup: str, fragment: str
) -> None:
    write_release_tree(tmp_path)
    (tmp_path / "README.md").write_text(readme_text(picture=markup), encoding="utf-8")
    assert fragment in failure(tool, tmp_path, "docs")


def test_same_repository_path_parsing(tool: types.ModuleType) -> None:
    assert tool.same_repository_path(f"{BLOB}/docs/quickstart.md#a?b") == "docs/quickstart.md"
    assert tool.same_repository_path(f"{RAW}/hero-light.svg") == "docs/assets/hero-light.svg"
    assert tool.same_repository_path("https://github.com/other/repo/blob/main/x.md") is None
    assert tool.same_repository_path("https://pypi.org/project/actseal/") is None
    assert tool.same_repository_path(f"{BLOB}/") is None


def test_relative_docs_links_with_anchors_and_encoding_resolve(
    tool: types.ModuleType, tmp_path: Path
) -> None:
    write_release_tree(tmp_path)
    quickstart = tmp_path / "docs" / "quickstart.md"
    quickstart.write_text(
        "# quickstart\n\n[s](stability.md#promise) [v](versi%6Fning.md?x=1) "
        '<a\n href="migration.md#from-0-1">m</a>\n',
        encoding="utf-8",
    )
    tool.check_docs(tmp_path)
    quickstart.write_text("# quickstart\n\n[gone](absent.md#promise)\n", encoding="utf-8")
    assert "broken relative links" in failure(tool, tmp_path, "docs")


def test_relative_html_sources_in_docs_must_resolve(tool: types.ModuleType, tmp_path: Path) -> None:
    write_release_tree(tmp_path)
    quickstart = tmp_path / "docs" / "quickstart.md"
    quickstart.write_text(
        '# quickstart\n\n<img src="assets/hero-light.svg" alt="x">\n', encoding="utf-8"
    )
    tool.check_docs(tmp_path)
    quickstart.write_text(
        '# quickstart\n\n<img src="assets/absent.svg"\n alt="x">\n', encoding="utf-8"
    )
    assert "broken relative links" in failure(tool, tmp_path, "docs")


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
            lambda root: (root / "README.md").write_text(
                readme_text().replace("Offline replay.**", "Replay.**"), encoding="utf-8"
            ),
            "lacks the approved bold opening line",
        ),
        (
            lambda root: (root / "README.md").write_text(
                readme_text().replace("still act on the wrong cases", "act"), encoding="utf-8"
            ),
            "lacks the approved opening description",
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
# assets gate
# --------------------------------------------------------------------------- #


def test_assets_gate_passes_when_outputs_exist_and_renderer_agrees(
    tool: types.ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_release_tree(tmp_path)
    tool.check_assets(tmp_path, renderer(tmp_path))
    argv = ["--root", str(tmp_path), "assets", "--renderer", renderer(tmp_path)]
    assert run_main(tool, argv, capsys) == (0, "", "")


def test_assets_gate_requires_the_toolchain(tool: types.ModuleType, tmp_path: Path) -> None:
    write_release_tree(tmp_path)
    (tmp_path / "docs" / "assets" / "src" / "render.py").unlink()
    assert "render.py is missing" in failure(tool, tmp_path, "assets")


def test_assets_gate_requires_every_required_output(tool: types.ModuleType, tmp_path: Path) -> None:
    write_release_tree(tmp_path)
    (tmp_path / "docs" / "assets" / "social.png").unlink()
    assert "docs/assets/social.png" in failure(tool, tmp_path, "assets")
    (tmp_path / "docs" / "assets" / "social.png").write_bytes(png_bytes(1200, 630))
    assert "social preview is (1200, 630)" in failure(tool, tmp_path, "assets")
    (tmp_path / "docs" / "assets" / "social.png").write_bytes(png_bytes(1280, 640))
    (tmp_path / "docs" / "assets" / "hero-dark.svg").write_text("not svg\n", encoding="utf-8")
    assert "hero-dark.svg is not an SVG" in failure(tool, tmp_path, "assets")


@pytest.mark.parametrize(
    "name",
    [
        "how-it-works-light.svg",
        "how-it-works-dark.svg",
        "how-it-works-mobile-light.svg",
        "how-it-works-mobile-dark.svg",
    ],
)
def test_assets_gate_rejects_each_missing_workflow_variant(
    tool: types.ModuleType, tmp_path: Path, name: str
) -> None:
    write_release_tree(tmp_path)
    (tmp_path / "docs" / "assets" / name).unlink()
    assert f"docs/assets/{name}" in failure(tool, tmp_path, "assets")


@pytest.mark.parametrize(
    "name",
    ["hero-light.svg", "hero-dark.svg", "hero-mobile-light.svg", "hero-mobile-dark.svg"],
)
def test_assets_gate_rejects_each_missing_hero_variant(
    tool: types.ModuleType, tmp_path: Path, name: str
) -> None:
    write_release_tree(tmp_path)
    (tmp_path / "docs" / "assets" / name).unlink()
    assert f"docs/assets/{name}" in failure(tool, tmp_path, "assets")


@pytest.mark.parametrize(
    "name",
    [
        "architecture-light.svg",
        "architecture-dark.svg",
        "architecture-mobile-light.svg",
        "architecture-mobile-dark.svg",
    ],
)
def test_assets_gate_rejects_each_missing_architecture_variant(
    tool: types.ModuleType, tmp_path: Path, name: str
) -> None:
    write_release_tree(tmp_path)
    (tmp_path / "docs" / "assets" / name).unlink()
    assert f"docs/assets/{name}" in failure(tool, tmp_path, "assets")


def test_assets_gate_fails_when_the_renderer_reports_errors(
    tool: types.ModuleType, tmp_path: Path
) -> None:
    write_release_tree(tmp_path)
    write_fake_renderer(
        tmp_path,
        'import sys\nsys.stdout.write("[error] hero: differs at byte 3\\n")\nsys.exit(1)\n',
    )
    message = failure(tool, tmp_path, "assets")
    assert "asset regeneration check failed (exit 1)" in message
    assert "differs at byte 3" in message


def test_assets_gate_rejects_a_zero_implemented_bootstrap(
    tool: types.ModuleType, tmp_path: Path
) -> None:
    write_release_tree(tmp_path)
    write_fake_renderer(
        tmp_path,
        "import sys\n"
        'sys.stdout.write("[info] hero: not implemented (planned in Task 11)\\n")\n'
        "sys.exit(0)\n",
    )
    assert "not implemented" in failure(tool, tmp_path, "assets")


def test_assets_gate_passes_only_the_required_asset_names(
    tool: types.ModuleType, tmp_path: Path
) -> None:
    write_release_tree(tmp_path)
    log = tmp_path / "renderer-argv.json"
    write_fake_renderer(
        tmp_path,
        f"import json, sys\nopen({str(log)!r}, 'w').write(json.dumps(sys.argv[1:]))\nsys.exit(0)\n",
    )
    tool.check_assets(tmp_path, renderer(tmp_path))
    argv = json.loads(log.read_text(encoding="utf-8"))
    assert argv[0] == "--check"
    assert argv[1::2] == ["--only"] * 4
    assert argv[2::2] == ["hero", "how-it-works", "architecture", "social"]
    assert "demo" not in argv


# --------------------------------------------------------------------------- #
# candidate gate
# --------------------------------------------------------------------------- #


def test_candidate_fails_clearly_on_an_incomplete_tree(
    tool: types.ModuleType, tmp_path: Path
) -> None:
    write_incomplete_tree(tmp_path)
    message = failure(tool, tmp_path, "candidate")
    assert message.startswith("candidate gate has ")
    assert "release candidate version must be >= 1.0.0, not 0.1.0" in message
    assert "docs/stability.md" in message
    assert "docs/schemas/ must contain JSON schemas" in message
    assert "render.py is missing" in message


def test_candidate_passes_on_a_complete_clean_fixture(
    tool: types.ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_release_tree(tmp_path)
    tool.check_candidate(
        tmp_path, tmp_path / ".github" / "workflows" / "publish-pypi.yml", renderer(tmp_path)
    )
    argv = ["--root", str(tmp_path), "candidate", "--renderer", renderer(tmp_path)]
    assert run_main(tool, argv, capsys) == (0, "", "")


def test_candidate_rejects_dirty_tree_wrong_png_and_misplaced_tag(
    tool: types.ModuleType, tmp_path: Path
) -> None:
    head = write_release_tree(tmp_path)
    (tmp_path / "scratch.txt").write_text("x\n", encoding="utf-8")
    assert "working tree must be clean" in failure(tool, tmp_path, "candidate")
    (tmp_path / "scratch.txt").unlink()
    (tmp_path / "docs" / "assets" / "social.png").write_bytes(png_bytes(1200, 630))
    commit_all(tmp_path, "wrong png")
    assert "social preview is (1200, 630)" in failure(tool, tmp_path, "candidate")
    (tmp_path / "docs" / "assets" / "social.png").write_bytes(png_bytes(1280, 640))
    commit_all(tmp_path, "right png")
    git(tmp_path, "tag", f"v{VERSION}", head)
    assert "does not point at HEAD" in failure(tool, tmp_path, "candidate")


def test_candidate_lists_every_unmet_requirement(tool: types.ModuleType, tmp_path: Path) -> None:
    write_release_tree(tmp_path, version="0.9.0")
    (tmp_path / "docs" / "schemas" / "lock.schema.json").unlink()
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n\n## v0.8.0\n", encoding="utf-8")
    write_fake_renderer(tmp_path, "import sys\nsys.exit(1)\n")
    commit_all(tmp_path, "regress")
    message = failure(tool, tmp_path, "candidate")
    assert "must be >= 1.0.0, not 0.9.0" in message
    assert "docs/schemas/ must contain JSON schemas" in message
    assert "no heading for 0.9.0" in message
    assert "asset regeneration check failed" in message


def test_candidate_on_the_real_checkout_is_a_clear_verdict(
    tool: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    """Valid before and after the v1 assets land: exit 0, or exit 1 with the gate's report."""
    code, out, err = run_main(tool, ["candidate"], capsys)
    assert out == ""
    assert code in (0, 1)
    if code == 1:
        assert err.startswith("release check failed: candidate gate has ")
