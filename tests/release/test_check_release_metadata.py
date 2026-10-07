"""``check_release.py metadata``: tag/pyproject/``__version__``/uv.lock/source-SHA agreement."""

from __future__ import annotations

import types
from pathlib import Path

import pytest
from release_support import (
    ALPHA,
    STABLE,
    commit_all,
    git,
    load_tool,
    run_main,
    write_version_sources,
)


@pytest.fixture(scope="module")
def tool() -> types.ModuleType:
    return load_tool()


@pytest.fixture
def repo(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "repo"
    root.mkdir()
    write_version_sources(root, "1.0.0")
    head = commit_all(root)
    git(root, "tag", "v1.0.0")
    return root, head


def failure(tool: types.ModuleType, root: Path, **kwargs: str | None) -> str:
    with pytest.raises(tool.ReleaseCheckError) as excinfo:
        tool.check_metadata(root, ref=kwargs.get("ref"), sha=kwargs.get("sha"))
    return str(excinfo.value)


def test_agreeing_sources_release_tag_and_sha_pass(
    tool: types.ModuleType, repo: tuple[Path, str]
) -> None:
    root, head = repo
    identity = tool.check_metadata(root, ref="refs/tags/v1.0.0", sha=head)
    assert (identity.version, identity.release) == ("1.0.0", True)
    rehearsal = tool.check_metadata(root, ref="refs/heads/main", sha=head)
    assert (rehearsal.version, rehearsal.release) == ("1.0.0", False)
    assert tool.check_metadata(root, ref=None, sha=None).release is False


@pytest.mark.parametrize("field", ["pyproject", "source", "lock"])
def test_any_disagreeing_version_source_fails(
    tool: types.ModuleType, tmp_path: Path, field: str
) -> None:
    write_version_sources(tmp_path, "1.0.0", **{field: "1.0.1"})
    assert "version sources disagree" in failure(tool, tmp_path)


def test_wrong_tag_for_version_fails(tool: types.ModuleType, repo: tuple[Path, str]) -> None:
    root, head = repo
    assert "does not match version 1.0.0" in failure(tool, root, ref="refs/tags/v1.0.1", sha=head)


def test_wrong_source_sha_fails(tool: types.ModuleType, repo: tuple[Path, str]) -> None:
    root, _ = repo
    assert "wrong source SHA" in failure(tool, root, ref="refs/heads/main", sha="0" * 40)


def test_tag_pointing_at_another_commit_fails(
    tool: types.ModuleType, repo: tuple[Path, str]
) -> None:
    root, _ = repo
    (root / "extra.txt").write_text("x\n", encoding="utf-8")
    newer = commit_all(root, "second")
    assert "points at" in failure(tool, root, ref="refs/tags/v1.0.0", sha=newer)


def test_release_tag_absent_from_checkout_fails(tool: types.ModuleType, tmp_path: Path) -> None:
    write_version_sources(tmp_path, "1.0.0")
    head = commit_all(tmp_path)
    assert "not present in the checkout" in failure(
        tool, tmp_path, ref="refs/tags/v1.0.0", sha=head
    )


def test_zero_major_release_tag_is_refused(tool: types.ModuleType, tmp_path: Path) -> None:
    write_version_sources(tmp_path, "0.9.0")
    assert "1.0.0 or later" in failure(tool, tmp_path, ref="refs/tags/v0.9.0")


def test_release_without_stable_classifier_fails(tool: types.ModuleType, tmp_path: Path) -> None:
    write_version_sources(tmp_path, "1.0.0", classifier=ALPHA)
    assert STABLE in failure(tool, tmp_path, ref="refs/tags/v1.0.0")
    assert tool.check_metadata(tmp_path, ref="refs/heads/main", sha=None).release is False


@pytest.mark.parametrize("version", ["1.0", "1.0.0rc1", "01.0.0", "1.0.0.post1", "v1.0.0"])
def test_non_release_version_strings_are_rejected(
    tool: types.ModuleType, tmp_path: Path, version: str
) -> None:
    write_version_sources(tmp_path, version)
    assert "not a plain MAJOR.MINOR.PATCH" in failure(tool, tmp_path)


def test_unsupported_ref_fails(tool: types.ModuleType, repo: tuple[Path, str]) -> None:
    root, _ = repo
    assert "unsupported ref" in failure(tool, root, ref="refs/pull/7/merge")


def test_cli_prints_outputs_for_the_real_repository(
    tool: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, err = run_main(
        tool, ["metadata", "--ref", "refs/heads/claude/v1-09-release"], capsys
    )
    assert (code, err) == (0, "")
    lines = out.splitlines()
    assert lines[0].startswith("version=")
    assert lines[1] == "release=false"
    assert tool.VERSION_RE.match(lines[0].removeprefix("version=")) is not None
