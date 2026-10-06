"""``postpublish`` unit tests: exit-code table, hash comparison, provenance and partial publication.

No network and no real wheel: the index is served over ``file://`` URLs and the
installed-demo expectations are exercised through the pure ``assert_demo_outcomes``.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest
from release_support import load_tool, names, sha256_hex, write_fake_index, write_sums, write_text

VERSION = "1.0.0"


@pytest.fixture(scope="module")
def tool() -> types.ModuleType:
    return load_tool()


def result(
    tool: types.ModuleType,
    code: int,
    document: dict[str, object] | None = None,
    stdout: str | None = None,
) -> object:
    text = stdout if stdout is not None else json.dumps(document or {}) + "\n"
    return tool.CommandResult(("actseal",), code, text, "")


def demo_document(bad: str = "BLOCK", fixed: str = "PASS") -> dict[str, object]:
    return {"ok": True, "runs": {"bad": {"status": bad}, "fixed": {"status": fixed}}}


def outcomes(
    tool: types.ModuleType,
    *,
    version_code: int = 0,
    version_text: str = f"actseal {VERSION}\n",
    demo_code: int = 0,
    demo: dict[str, object] | None = None,
    fixed_code: int = 0,
    fixed_status: str = "PASS",
    bad_code: int = 1,
    bad_status: str = "BLOCK",
) -> dict[str, object]:
    checks = tool.assert_demo_outcomes(
        VERSION,
        result(tool, version_code, stdout=version_text),
        result(tool, demo_code, demo or demo_document()),
        result(tool, fixed_code, {"status": fixed_status}),
        result(tool, bad_code, {"status": bad_status}),
    )
    return {str(key): value for key, value in checks.items()}


def test_expected_outcomes_pass(tool: types.ModuleType) -> None:
    checks = outcomes(tool)
    assert checks == {
        "version_output": f"actseal {VERSION}",
        "demo_exit": 0,
        "fixed_replay_exit": 0,
        "bad_replay_exit": 1,
        "demo_bad_status": "BLOCK",
        "demo_fixed_status": "PASS",
    }


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"version_code": 1}, "--version exited 1"),
        ({"version_text": "actseal 0.1.0\n"}, "--version printed"),
        ({"demo_code": 1}, "wrong exit code: demo exited 1"),
        ({"demo_code": 3}, "wrong exit code: demo exited 3"),
        ({"fixed_code": 1}, "wrong exit code: fixed replay exited 1"),
        ({"bad_code": 0}, "wrong exit code: bad replay exited 0"),
        ({"bad_code": 3}, "wrong exit code: bad replay exited 3"),
        ({"demo": demo_document(bad="PASS")}, "demo bad run status is 'PASS'"),
        ({"demo": demo_document(fixed="BLOCK")}, "demo fixed run status is 'BLOCK'"),
        ({"fixed_status": "BLOCK"}, "fixed replay status is not PASS"),
        ({"bad_status": "INCONCLUSIVE"}, "bad replay status is not BLOCK"),
    ],
)
def test_every_wrong_exit_code_or_verdict_fails(
    tool: types.ModuleType, overrides: dict[str, object], fragment: str
) -> None:
    with pytest.raises(tool.ReleaseCheckError) as excinfo:
        outcomes(tool, **overrides)  # type: ignore[arg-type]
    assert fragment in str(excinfo.value)


def test_non_json_output_fails(tool: types.ModuleType) -> None:
    with pytest.raises(tool.ReleaseCheckError) as excinfo:
        tool.assert_demo_outcomes(
            VERSION,
            result(tool, 0, stdout=f"actseal {VERSION}\n"),
            result(tool, 0, stdout="not json\n"),
            result(tool, 0, {"status": "PASS"}),
            result(tool, 1, {"status": "BLOCK"}),
        )
    assert "did not print JSON" in str(excinfo.value)


# --------------------------------------------------------------------------- #
# Index inspection over file:// (fails before any installation)
# --------------------------------------------------------------------------- #


@pytest.fixture
def published(tmp_path: Path) -> tuple[dict[str, bytes], Path]:
    wheel, sdist = names(VERSION)
    files = {wheel: b"wheel-bytes", sdist: b"sdist-bytes"}
    store = tmp_path / "built"
    store.mkdir()
    for name, data in files.items():
        (store / name).write_bytes(data)
    sums = write_sums(tmp_path / "SHA256SUMS", {name: store / name for name in files})
    return files, sums


def run_postpublish(
    tool: types.ModuleType, base: str, sums: Path, tmp_path: Path, *, allow_missing: bool = False
) -> str:
    with pytest.raises(tool.ReleaseCheckError) as excinfo:
        tool.postpublish(
            version=VERSION,
            sums_path=sums,
            workdir=tmp_path / "work",
            out=tmp_path / "receipt.json",
            checkout=None,
            base_url=base,
            wait_seconds=0,
            python=sys.executable,
            allow_missing_attestations=allow_missing,
        )
    assert not (tmp_path / "receipt.json").exists()
    return str(excinfo.value)


def test_partial_publication_is_a_loud_failure(
    tool: types.ModuleType, published: tuple[dict[str, bytes], Path], tmp_path: Path
) -> None:
    files, sums = published
    wheel = names(VERSION)[0]
    base = write_fake_index(tmp_path / "index", VERSION, {wheel: files[wheel]})
    message = run_postpublish(tool, base, sums, tmp_path)
    assert "partial publication: PyPI has 1 of 2 expected files" in message
    assert "nothing will be re-uploaded or rebuilt" in message


def test_unexpected_published_file_fails(
    tool: types.ModuleType, published: tuple[dict[str, bytes], Path], tmp_path: Path
) -> None:
    files, sums = published
    base = write_fake_index(
        tmp_path / "index", VERSION, {**files, "actseal-1.0.0-py3-none-win_amd64.whl": b"x"}
    )
    assert "unexpected files" in run_postpublish(tool, base, sums, tmp_path)


def test_release_not_visible_fails_after_waiting(
    tool: types.ModuleType, published: tuple[dict[str, bytes], Path], tmp_path: Path
) -> None:
    _, sums = published
    base = write_fake_index(tmp_path / "index", "9.9.9", {})
    assert "not visible" in run_postpublish(tool, base, sums, tmp_path)


def test_downloaded_bytes_differing_from_the_build_fail(
    tool: types.ModuleType, published: tuple[dict[str, bytes], Path], tmp_path: Path
) -> None:
    files, sums = published
    wheel, sdist = names(VERSION)
    base = write_fake_index(tmp_path / "index", VERSION, {wheel: b"tampered", sdist: files[sdist]})
    assert "downloaded sha256" in run_postpublish(tool, base, sums, tmp_path)


def test_declared_digest_differing_from_the_bytes_fails(
    tool: types.ModuleType, published: tuple[dict[str, bytes], Path], tmp_path: Path
) -> None:
    files, sums = published
    wheel = names(VERSION)[0]
    base = write_fake_index(tmp_path / "index", VERSION, files, declared={wheel: "0" * 64})
    assert "PyPI declares sha256" in run_postpublish(tool, base, sums, tmp_path)


def test_missing_provenance_fails_unless_explicitly_allowed(
    tool: types.ModuleType, published: tuple[dict[str, bytes], Path], tmp_path: Path
) -> None:
    files, sums = published
    base = write_fake_index(tmp_path / "index", VERSION, files, provenance_for=[names(VERSION)[1]])
    assert "no provenance/attestations" in run_postpublish(tool, base, sums, tmp_path)
    assert tool._provenance(base, VERSION, names(VERSION)[0]) == {
        "present": False,
        "attestations": 0,
        "publishers": [],
    }
    present = tool._provenance(base, VERSION, names(VERSION)[1])
    assert present["present"] is True
    assert present["attestations"] == 1
    assert present["publishers"] == [
        {
            "kind": "GitHub",
            "repository": "ajaysurya1221/actseal",
            "workflow": "publish-pypi.yml",
            "environment": "pypi",
        }
    ]


def test_sums_for_another_version_or_existing_workdir_fail(
    tool: types.ModuleType, published: tuple[dict[str, bytes], Path], tmp_path: Path
) -> None:
    files, _ = published
    base = write_fake_index(tmp_path / "index", VERSION, files)
    stale = write_text(tmp_path / "stale", f"{sha256_hex(b'x')}  actseal-0.9.0.tar.gz\n")
    assert "does not describe 1.0.0" in run_postpublish(tool, base, stale, tmp_path)
    _, sums = published
    (tmp_path / "work").mkdir()
    assert "already exists" in run_postpublish(tool, base, sums, tmp_path)


def test_workdir_inside_checkout_is_refused(
    tool: types.ModuleType, published: tuple[dict[str, bytes], Path], tmp_path: Path
) -> None:
    files, sums = published
    base = write_fake_index(tmp_path / "index", VERSION, files)
    with pytest.raises(tool.ReleaseCheckError) as excinfo:
        tool.postpublish(
            version=VERSION,
            sums_path=sums,
            workdir=tmp_path / "checkout" / "work",
            out=tmp_path / "receipt.json",
            checkout=tmp_path / "checkout",
            base_url=base,
            wait_seconds=0,
            python=sys.executable,
            allow_missing_attestations=False,
        )
    assert "must lie outside the checkout" in str(excinfo.value)
