"""``distributions`` and ``verify-distributions``: two files, agreeing metadata, exact hashes.

Unit tests use hand-made archives. The ``packaging``-marked tests build the real
distributions once and run the complete ``distributions`` → ``verify-distributions``
→ ``postpublish`` chain against a ``file://`` index, exactly as the workflow does.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest
from release_support import (
    PUBLISHER,
    ROOT,
    load_tool,
    names,
    release_distributions,
    run_main,
    sha256_path,
    write_fake_distributions,
    write_fake_index,
    write_sdist,
    write_sums,
    write_version_sources,
    write_wheel,
)

VERSION = "1.0.0"


@pytest.fixture(scope="module")
def tool() -> types.ModuleType:
    return load_tool()


@pytest.fixture
def fake_dist(tmp_path: Path) -> Path:
    directory = tmp_path / "dist"
    write_fake_distributions(directory, VERSION)
    return directory


def failure(tool: types.ModuleType, directory: Path, version: str = VERSION) -> str:
    with pytest.raises(tool.ReleaseCheckError) as excinfo:
        tool.inspect_distributions(directory, version)
    return str(excinfo.value)


# --------------------------------------------------------------------------- #
# distributions (hand-made archives)
# --------------------------------------------------------------------------- #


def test_two_agreeing_distributions_pass(tool: types.ModuleType, fake_dist: Path) -> None:
    result = tool.inspect_distributions(fake_dist, VERSION)
    assert [item.filename for item in result] == list(names(VERSION))
    assert all(item.size == (fake_dist / item.filename).stat().st_size for item in result)
    assert all(item.sha256 == sha256_path(fake_dist / item.filename) for item in result)


@pytest.mark.parametrize("index", [0, 1])
def test_missing_distribution_fails(tool: types.ModuleType, fake_dist: Path, index: int) -> None:
    (fake_dist / names(VERSION)[index]).unlink()
    assert f"missing distribution {names(VERSION)[index]}" in failure(tool, fake_dist)


@pytest.mark.parametrize(
    "extra", ["SHA256SUMS", "build-receipt.json", ".gitignore", "actseal-1.0.1.tar.gz"]
)
def test_any_extra_file_in_packages_dir_fails(
    tool: types.ModuleType, fake_dist: Path, extra: str
) -> None:
    (fake_dist / extra).write_text("x\n", encoding="utf-8")
    assert "only wheel+sdist allowed" in failure(tool, fake_dist)


def test_wrong_requested_version_fails(tool: types.ModuleType, fake_dist: Path) -> None:
    assert "missing distribution" in failure(tool, fake_dist, "1.0.1")


def test_wheel_metadata_version_mismatch_fails(tool: types.ModuleType, tmp_path: Path) -> None:
    write_wheel(tmp_path, VERSION, metadata_version="1.0.1")
    write_sdist(tmp_path, VERSION)
    assert "METADATA Version is '1.0.1'" in failure(tool, tmp_path)


@pytest.mark.parametrize(
    ("field", "fragment"),
    [
        ("pkg_version", "PKG-INFO Version is '1.0.1'"),
        ("pyproject_version", "pyproject.toml version is '1.0.1'"),
        ("lock_version", "uv.lock self-version does not equal"),
    ],
)
def test_sdist_internal_version_mismatch_fails(
    tool: types.ModuleType, tmp_path: Path, field: str, fragment: str
) -> None:
    write_wheel(tmp_path, VERSION)
    write_sdist(tmp_path, VERSION, **{field: "1.0.1"})
    assert fragment in failure(tool, tmp_path)


def test_corrupt_archives_fail(tool: types.ModuleType, tmp_path: Path) -> None:
    wheel, sdist = names(VERSION)
    (tmp_path / wheel).write_bytes(b"not a zip")
    write_sdist(tmp_path, VERSION)
    assert "not a zip archive" in failure(tool, tmp_path)
    write_wheel(tmp_path, VERSION)
    (tmp_path / sdist).write_bytes(b"not a tarball")
    assert "tar.gz archive" in failure(tool, tmp_path)


def test_cli_writes_sums_receipt_and_outputs(
    tool: types.ModuleType, fake_dist: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    write_version_sources(root, VERSION)
    sums = tmp_path / "meta" / "SHA256SUMS"
    receipt = tmp_path / "meta" / "build-receipt.json"
    argv = [
        "--root",
        str(root),
        "distributions",
        str(fake_dist),
        "--version",
        VERSION,
        "--ref",
        f"refs/tags/v{VERSION}",
        "--sha",
        "a" * 40,
        "--run-id",
        "123",
        "--run-attempt",
        "1",
        "--sha256sums",
        str(sums),
        "--build-receipt",
        str(receipt),
    ]
    code, out, err = run_main(tool, argv, capsys)
    assert (code, err) == (0, "")
    wheel, sdist = names(VERSION)
    assert out == f"wheel={wheel}\nsdist={sdist}\n"
    assert tool.read_sha256sums(sums) == {
        name: sha256_path(fake_dist / name) for name in (wheel, sdist)
    }
    document = json.loads(receipt.read_text(encoding="utf-8"))
    assert document["kind"] == "actseal-build-receipt"
    assert (document["version"], document["tag"], document["source_commit"]) == (
        VERSION,
        f"v{VERSION}",
        "a" * 40,
    )
    assert document["workflow_run"] == {"id": "123", "attempt": "1"}
    assert document["lock_sha256"] == sha256_path(root / "uv.lock")
    assert [d["filename"] for d in document["distributions"]] == [wheel, sdist]
    assert "artifact" not in document


# --------------------------------------------------------------------------- #
# verify-distributions
# --------------------------------------------------------------------------- #


@pytest.fixture
def verified(tool: types.ModuleType, fake_dist: Path, tmp_path: Path) -> tuple[Path, Path]:
    files = {name: fake_dist / name for name in names(VERSION)}
    sums = write_sums(tmp_path / "SHA256SUMS", files)
    assert len(tool.verify_distributions(fake_dist, VERSION, sums)) == 2
    return fake_dist, sums


def verify_failure(
    tool: types.ModuleType, directory: Path, sums: Path, version: str = VERSION
) -> str:
    with pytest.raises(tool.ReleaseCheckError) as excinfo:
        tool.verify_distributions(directory, version, sums)
    return str(excinfo.value)


def test_altered_byte_fails(tool: types.ModuleType, verified: tuple[Path, Path]) -> None:
    directory, sums = verified
    wheel = directory / names(VERSION)[0]
    data = bytearray(wheel.read_bytes())
    data[-1] ^= 0x01
    wheel.write_bytes(bytes(data))
    assert "altered hash" in verify_failure(tool, directory, sums)


def test_stale_checksums_from_another_version_fail(
    tool: types.ModuleType, verified: tuple[Path, Path]
) -> None:
    directory, sums = verified
    assert "stale checksum file" in verify_failure(tool, directory, sums, "1.0.1")


def test_missing_or_extra_file_fails(tool: types.ModuleType, verified: tuple[Path, Path]) -> None:
    directory, sums = verified
    (directory / "extra.txt").write_text("x\n", encoding="utf-8")
    assert "must be exactly" in verify_failure(tool, directory, sums)
    (directory / "extra.txt").unlink()
    (directory / names(VERSION)[1]).unlink()
    assert "must be exactly" in verify_failure(tool, directory, sums)


def test_malformed_checksum_lines_fail(
    tool: types.ModuleType, verified: tuple[Path, Path], tmp_path: Path
) -> None:
    directory, sums = verified
    bad = tmp_path / "bad-sums"
    bad.write_text(sums.read_text(encoding="utf-8").replace("  ", " ", 1), encoding="utf-8")
    assert "malformed SHA256SUMS line" in verify_failure(tool, directory, bad)
    bad.write_text(sums.read_text(encoding="utf-8") * 2, encoding="utf-8")
    assert "duplicate entry" in verify_failure(tool, directory, bad)
    bad.write_text("", encoding="utf-8")
    assert "lists no files" in verify_failure(tool, directory, bad)


def test_cli_verify_distributions(
    tool: types.ModuleType, verified: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    directory, sums = verified
    argv = ["verify-distributions", str(directory), "--version", VERSION, "--sha256sums", str(sums)]
    assert run_main(tool, argv, capsys) == (0, "", "")


# --------------------------------------------------------------------------- #
# Real distributions: the workflow chain end to end (packaging marker)
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def real_dist(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The supplied release artifacts when ``ACTSEAL_TEST_DIST`` is set, else one local build."""
    files = release_distributions(tmp_path_factory.mktemp("real-dist") / "dist")
    return next(iter(files.values())).parent


@pytest.mark.packaging
def test_real_build_validates_then_verifies(
    tool: types.ModuleType, real_dist: Path, tmp_path: Path
) -> None:
    version = tool.agreed_version(ROOT)
    result = tool.inspect_distributions(real_dist, version)
    assert [item.filename for item in result] == list(names(version))
    sums = tmp_path / "SHA256SUMS"
    tool.write_sha256sums(sums, {item.filename: item.sha256 for item in result})
    assert tool.verify_distributions(real_dist, version, sums) == result
    copy = tmp_path / "copy"
    copy.mkdir()
    for item in result:
        (copy / item.filename).write_bytes((real_dist / item.filename).read_bytes())
    assert tool.verify_distributions(copy, version, sums) == result


@pytest.mark.packaging
def test_real_postpublish_chain_against_a_fake_index(
    tool: types.ModuleType, real_dist: Path, tmp_path: Path
) -> None:
    version = tool.agreed_version(ROOT)
    files = {path.name: path.read_bytes() for path in sorted(real_dist.iterdir())}
    sums = write_sums(tmp_path / "SHA256SUMS", {name: real_dist / name for name in files})
    base = write_fake_index(tmp_path / "index", version, files)
    out = tmp_path / "postpublish-receipt.json"
    receipt = tool.postpublish(
        version=version,
        sums_path=sums,
        workdir=tmp_path / "work",
        out=out,
        checkout=ROOT,
        base_url=base,
        wait_seconds=0,
        python=sys.executable,
        allow_missing_attestations=False,
    )
    assert receipt["ok"] is True
    assert json.loads(out.read_text(encoding="utf-8")) == receipt
    checks = receipt["checks"]
    assert (checks["demo_exit"], checks["fixed_replay_exit"], checks["bad_replay_exit"]) == (
        0,
        0,
        1,
    )
    assert (checks["demo_bad_status"], checks["demo_fixed_status"]) == ("BLOCK", "PASS")
    assert checks["version_output"] == f"actseal {version}"
    assert checks["installed_outside_checkout"] is True
    recorded = {item["filename"]: item["sha256"] for item in receipt["files"]}
    assert recorded == {name: sha256_path(real_dist / name) for name in files}
    for item in receipt["files"]:
        provenance = item["provenance"]
        assert provenance["present"] is True
        assert provenance["attestations"] == 1
        assert provenance["publishers"] == [PUBLISHER]
        assert provenance["subject_sha256"] == item["sha256"]
    assert receipt["published_metadata"]["version"] == version
    assert "no independent cryptographic verification" in receipt["note"]
    # The file:// index is the isolated chain, not promotion: official_index stays off.
    tool.validate_postpublish_receipt(
        receipt, version, tool.inspect_distributions(real_dist, version), official_index=False
    )
    with pytest.raises(tool.ReleaseCheckError) as excinfo:
        tool.validate_postpublish_receipt(
            receipt, version, tool.inspect_distributions(real_dist, version), official_index=True
        )
    assert "not official https://pypi.org" in str(excinfo.value)
    demo = tmp_path / "work" / "demo"
    assert (demo / "bad" / "evidence" / "manifest.json").is_file()
    assert (demo / "fixed" / "evidence" / "manifest.json").is_file()


@pytest.mark.packaging
def test_real_postpublish_refuses_partial_publication(
    tool: types.ModuleType, real_dist: Path, tmp_path: Path
) -> None:
    version = tool.agreed_version(ROOT)
    wheel_name, _ = names(version)
    sums = write_sums(tmp_path / "SHA256SUMS", {name: real_dist / name for name in names(version)})
    base = write_fake_index(
        tmp_path / "index", version, {wheel_name: (real_dist / wheel_name).read_bytes()}
    )
    with pytest.raises(tool.ReleaseCheckError) as excinfo:
        tool.postpublish(
            version=version,
            sums_path=sums,
            workdir=tmp_path / "work",
            out=tmp_path / "receipt.json",
            checkout=ROOT,
            base_url=base,
            wait_seconds=0,
            python=sys.executable,
            allow_missing_attestations=False,
        )
    message = str(excinfo.value)
    assert "partial publication: PyPI has 1 of 2 expected files" in message
    assert "nothing will be re-uploaded or rebuilt" in message
    assert not (tmp_path / "receipt.json").exists()
    assert not (tmp_path / "work" / "venv").exists()
