"""Ownership and copy-safety regressions for ``tools/check_mutations.py``.

REVIEW 04 found that the first draft accepted an existing ``--workdir`` and
recursively deleted it. The harness now treats ``--workdir`` as an existing
*parent*, resolves it, refuses a parent equal to or beneath either copied
source directory, creates one uniquely named child it owns and removes only
that child. Copied inputs containing symlinks are refused before any copy.

Nothing here runs the mutation harness or touches the real checkout: every
destructive step happens inside an isolated ``tmp_path`` and a fabricated
miniature repository, and the only real-repository calls are read-only path
resolutions.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path
from types import ModuleType

import pytest

TOOL = Path(__file__).resolve().parents[2] / "tools" / "check_mutations.py"
PREFIX = "actseal-mutants-"


def _load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_mutations_under_test", TOOL)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve annotations through sys.modules
    spec.loader.exec_module(module)
    return module


harness = _load_harness()
HarnessError: type[Exception] = harness.HarnessError


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    """A miniature checkout with the same copied-input layout as the real one."""
    repo = tmp_path / "repo"
    (repo / "src" / "actseal").mkdir(parents=True)
    (repo / "src" / "actseal" / "__init__.py").write_text("VERSION = 1\n", encoding="utf-8")
    (repo / "src" / "actseal" / "stats.py").write_text("TAIL = 4\n", encoding="utf-8")
    (repo / "src" / "actseal" / "__pycache__").mkdir()
    (repo / "src" / "actseal" / "__pycache__" / "stats.pyc").write_bytes(b"\x00")
    (repo / "tests" / "unit").mkdir(parents=True)
    (repo / "tests" / "conftest.py").write_text("# conftest\n", encoding="utf-8")
    (repo / "tests" / "unit" / "test_x.py").write_text("def test_x(): pass\n", encoding="utf-8")
    (repo / "pyproject.toml").write_text("[tool.pytest.ini_options]\n", encoding="utf-8")
    return repo


@pytest.fixture
def parent(tmp_path: Path) -> Path:
    """A caller-owned parent directory holding a sentinel that must survive."""
    directory = tmp_path / "caller-owned"
    directory.mkdir()
    (directory / "sentinel.txt").write_text("keep me\n", encoding="utf-8")
    (directory / "existing-subdir").mkdir()
    return directory


def _assert_parent_intact(parent: Path) -> None:
    assert parent.is_dir()
    assert (parent / "sentinel.txt").read_text(encoding="utf-8") == "keep me\n"
    assert (parent / "existing-subdir").is_dir()


def _children(parent: Path) -> set[str]:
    return {entry.name for entry in parent.iterdir()}


# --------------------------------------------------------------------------- #
# Owned child allocation and release
# --------------------------------------------------------------------------- #


def test_allocate_creates_a_unique_owned_child_beneath_the_parent(
    parent: Path, fake_repo: Path
) -> None:
    before = _children(parent)
    first = harness.allocate_workdir(parent, fake_repo)
    second = harness.allocate_workdir(parent, fake_repo)
    assert first != second
    for child in (first, second):
        assert child.is_dir()
        assert child.parent == parent.resolve()
        assert child.name.startswith(PREFIX)
    assert _children(parent) == before | {first.name, second.name}
    _assert_parent_intact(parent)


def test_release_removes_only_the_child_and_preserves_the_parent(
    parent: Path, fake_repo: Path
) -> None:
    child = harness.allocate_workdir(parent, fake_repo)
    (child / "baseline").mkdir()
    (child / "baseline" / "file.txt").write_text("x", encoding="utf-8")
    before = _children(parent)
    harness.release_workdir(child, keep=False)
    assert not child.exists()
    assert _children(parent) == before - {child.name}
    _assert_parent_intact(parent)


def test_release_refuses_a_directory_the_harness_did_not_create(parent: Path) -> None:
    with pytest.raises(HarnessError, match="did not create"):
        harness.release_workdir(parent, keep=False)
    _assert_parent_intact(parent)
    foreign = parent / "existing-subdir"
    with pytest.raises(HarnessError, match="did not create"):
        harness.release_workdir(foreign, keep=False)
    assert foreign.is_dir()


def test_run_in_owned_workdir_cleans_the_child_after_success(parent: Path, fake_repo: Path) -> None:
    seen: list[Path] = []

    def body(workdir: Path) -> int:
        seen.append(workdir)
        (workdir / "baseline").mkdir()
        return 0

    before = _children(parent)
    assert harness.run_in_owned_workdir(parent, keep=False, repo=fake_repo, body=body) == 0
    assert len(seen) == 1
    assert seen[0].parent == parent.resolve()
    assert not seen[0].exists()
    assert _children(parent) == before
    _assert_parent_intact(parent)


@pytest.mark.parametrize("error", [HarnessError("baseline gate failed"), RuntimeError("boom")])
def test_run_in_owned_workdir_cleans_the_child_after_failure(
    parent: Path, fake_repo: Path, error: Exception
) -> None:
    seen: list[Path] = []

    def body(workdir: Path) -> int:
        seen.append(workdir)
        (workdir / "baseline" / "src").mkdir(parents=True)
        (workdir / "baseline" / "src" / "x.py").write_text("x", encoding="utf-8")
        raise error

    before = _children(parent)
    with pytest.raises(type(error)):
        harness.run_in_owned_workdir(parent, keep=False, repo=fake_repo, body=body)
    assert len(seen) == 1
    assert not seen[0].exists()
    assert _children(parent) == before
    _assert_parent_intact(parent)


def _failing_rmtree(path: Path | str) -> None:
    """A simulated cleanup failure: nothing is removed, an OSError surfaces."""
    raise OSError(f"simulated removal failure for {path}")


def _noop_rmtree(path: Path | str) -> None:
    """A simulated silent partial failure: returns without removing anything."""
    assert Path(path).is_dir()


def test_cleanup_failure_is_loud_and_names_the_retained_child(
    parent: Path, fake_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    child = harness.allocate_workdir(parent, fake_repo)
    (child / "baseline").mkdir()
    monkeypatch.setattr(harness.shutil, "rmtree", _failing_rmtree)
    with pytest.raises(HarnessError, match="cleanup failed") as caught:
        harness.release_workdir(child, keep=False)
    assert str(child) in str(caught.value)
    assert isinstance(caught.value.__cause__, OSError)
    assert child.is_dir()
    assert (child / "baseline").is_dir()
    _assert_parent_intact(parent)


def test_cleanup_that_leaves_the_child_behind_is_reported(
    parent: Path, fake_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    child = harness.allocate_workdir(parent, fake_repo)
    monkeypatch.setattr(harness.shutil, "rmtree", _noop_rmtree)
    with pytest.raises(HarnessError, match="cleanup incomplete") as caught:
        harness.release_workdir(child, keep=False)
    assert str(child) in str(caught.value)
    assert child.is_dir()
    _assert_parent_intact(parent)


def test_cleanup_failure_overrides_a_successful_body(
    parent: Path, fake_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A body that returns the success exit must not yield success when cleanup fails."""
    seen: list[Path] = []

    def body(workdir: Path) -> int:
        seen.append(workdir)
        (workdir / "M01").mkdir()
        return 0  # the harness's EXIT_OK

    assert harness.EXIT_OK == 0
    before = _children(parent)
    monkeypatch.setattr(harness.shutil, "rmtree", _failing_rmtree)
    with pytest.raises(HarnessError, match="cleanup failed") as caught:
        harness.run_in_owned_workdir(parent, keep=False, repo=fake_repo, body=body)
    assert len(seen) == 1
    assert str(seen[0]) in str(caught.value)
    assert seen[0].is_dir()
    assert (seen[0] / "M01").is_dir()
    assert _children(parent) == before | {seen[0].name}
    _assert_parent_intact(parent)


def test_cli_maps_harness_errors_to_the_nonzero_harness_exit(tmp_path: Path) -> None:
    """Exit mapping only: both calls stop before any tree is allocated or copied."""
    assert harness.cli(["--only", "M99", "--workdir", str(tmp_path)]) == harness.EXIT_HARNESS_ERROR
    assert harness.cli(["--only", "M01", "--workdir", str(harness.REPO / "tests")]) == (
        harness.EXIT_HARNESS_ERROR
    )
    assert harness.EXIT_HARNESS_ERROR != harness.EXIT_OK
    assert list(tmp_path.iterdir()) == []


def test_keep_retains_only_the_owned_child(parent: Path, fake_repo: Path) -> None:
    seen: list[Path] = []

    def body(workdir: Path) -> int:
        seen.append(workdir)
        (workdir / "M01").mkdir()
        return 1

    before = _children(parent)
    assert harness.run_in_owned_workdir(parent, keep=True, repo=fake_repo, body=body) == 1
    kept = seen[0]
    assert kept.is_dir()
    assert kept.parent == parent.resolve()
    assert kept.name.startswith(PREFIX)
    assert (kept / "M01").is_dir()
    assert _children(parent) == before | {kept.name}
    _assert_parent_intact(parent)


def test_default_parent_is_the_system_temporary_directory(fake_repo: Path) -> None:
    child = harness.allocate_workdir(None, fake_repo)
    try:
        assert child.parent == Path(tempfile.gettempdir()).resolve()
        assert child.name.startswith(PREFIX)
    finally:
        harness.release_workdir(child, keep=False)
    assert not child.exists()


# --------------------------------------------------------------------------- #
# Unsafe parents and aliases
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "relative",
    [
        "src/actseal",
        "src/actseal/__pycache__",
        "tests",
        "tests/unit",
        "tests/unit/..",
        "tests/unit/../unit",
    ],
)
def test_parents_inside_copied_sources_are_refused_before_allocation(
    fake_repo: Path, relative: str
) -> None:
    unsafe = fake_repo / relative
    assert unsafe.is_dir()
    before = sorted(path for path in fake_repo.rglob("*"))
    with pytest.raises(HarnessError, match="inside copied source"):
        harness.allocate_workdir(unsafe, fake_repo)
    assert sorted(path for path in fake_repo.rglob("*")) == before


def test_symlink_alias_of_a_copied_source_is_refused(tmp_path: Path, fake_repo: Path) -> None:
    alias = tmp_path / "alias-to-tests"
    alias.symlink_to(fake_repo / "tests", target_is_directory=True)
    with pytest.raises(HarnessError, match="inside copied source"):
        harness.safe_parent(alias, fake_repo)
    nested = tmp_path / "alias-to-src"
    nested.symlink_to(fake_repo / "src", target_is_directory=True)
    with pytest.raises(HarnessError, match="inside copied source"):
        harness.safe_parent(nested / "actseal", fake_repo)


def test_symlink_alias_of_a_safe_directory_stays_valid(tmp_path: Path, fake_repo: Path) -> None:
    target = tmp_path / "safe-target"
    target.mkdir()
    alias = tmp_path / "safe-alias"
    alias.symlink_to(target, target_is_directory=True)
    assert harness.safe_parent(alias, fake_repo) == target.resolve()
    child = harness.allocate_workdir(alias, fake_repo)
    try:
        assert child.parent == target.resolve()
    finally:
        harness.release_workdir(child, keep=False)
    assert target.is_dir()
    assert alias.is_symlink()


def test_missing_dangling_or_file_parents_are_refused(tmp_path: Path, fake_repo: Path) -> None:
    with pytest.raises(HarnessError, match="existing directory"):
        harness.safe_parent(tmp_path / "absent", fake_repo)
    regular_file = tmp_path / "file.txt"
    regular_file.write_text("x", encoding="utf-8")
    with pytest.raises(HarnessError, match="existing directory"):
        harness.safe_parent(regular_file, fake_repo)
    dangling = tmp_path / "dangling"
    dangling.symlink_to(tmp_path / "nowhere")
    with pytest.raises(HarnessError, match="dangling symlink"):
        harness.safe_parent(dangling, fake_repo)


def test_real_checkout_sources_are_refused_read_only() -> None:
    """Path resolution only: nothing is created or removed in the real repository."""
    repo = harness.REPO
    for relative in ("src/actseal", "tests", "tests/unit", "tests/properties"):
        with pytest.raises(HarnessError, match="inside copied source"):
            harness.safe_parent(repo / relative, repo)
    assert harness.safe_parent(Path(tempfile.gettempdir()), repo).is_dir()


def test_main_refuses_an_unsafe_workdir_before_allocating_or_copying(tmp_path: Path) -> None:
    """``main`` wiring up to allocation only: no mutant is ever executed here."""
    repo = harness.REPO
    before = sorted(path.name for path in (repo / "tests").iterdir())
    with pytest.raises(HarnessError, match="inside copied source"):
        harness.main(["--only", "M01", "--workdir", str(repo / "tests")])
    assert sorted(path.name for path in (repo / "tests").iterdir()) == before
    with pytest.raises(HarnessError, match="unknown mutant id"):
        harness.main(["--only", "M99", "--workdir", str(tmp_path)])
    assert list(tmp_path.iterdir()) == []


# --------------------------------------------------------------------------- #
# Symlinks inside copied inputs
# --------------------------------------------------------------------------- #


def _make_link(link: Path, target: Path) -> None:
    link.symlink_to(target, target_is_directory=target.is_dir())


@pytest.mark.parametrize(
    "link_relative",
    [
        "src/actseal/leak.py",
        "src/actseal/sub",
        "tests/unit/leak.py",
        "tests/linked-dir",
    ],
)
def test_symlinks_inside_copied_inputs_are_refused_before_any_copy(
    tmp_path: Path, fake_repo: Path, link_relative: str
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("outside", encoding="utf-8")
    link = fake_repo / link_relative
    _make_link(
        link, outside if link_relative.endswith(("sub", "linked-dir")) else outside / "secret.txt"
    )
    with pytest.raises(HarnessError, match="symlink inside copied inputs"):
        harness.refuse_symlinks(fake_repo)
    child = tmp_path / "child"
    child.mkdir()
    with pytest.raises(HarnessError, match="symlink inside copied inputs"):
        harness.make_tree(child, "baseline", fake_repo)
    assert not (child / "baseline").exists()


def test_symlinked_copied_directory_or_file_is_refused(tmp_path: Path, fake_repo: Path) -> None:
    moved = tmp_path / "moved-tests"
    (fake_repo / "tests").rename(moved)
    _make_link(fake_repo / "tests", moved)
    with pytest.raises(HarnessError, match="copied input is a symlink: tests"):
        harness.refuse_symlinks(fake_repo)
    (fake_repo / "tests").unlink()
    moved.rename(fake_repo / "tests")

    real_toml = tmp_path / "real.toml"
    (fake_repo / "pyproject.toml").rename(real_toml)
    _make_link(fake_repo / "pyproject.toml", real_toml)
    with pytest.raises(HarnessError, match=r"copied input is a symlink: pyproject\.toml"):
        harness.refuse_symlinks(fake_repo)


def test_recursive_symlink_inside_copied_inputs_is_refused(tmp_path: Path, fake_repo: Path) -> None:
    loop = fake_repo / "tests" / "unit" / "loop"
    loop.symlink_to(fake_repo / "tests", target_is_directory=True)
    with pytest.raises(HarnessError, match="symlink inside copied inputs: tests/unit/loop"):
        harness.refuse_symlinks(fake_repo)
    child = tmp_path / "child"
    child.mkdir()
    with pytest.raises(HarnessError):
        harness.make_tree(child, "baseline", fake_repo)
    assert not (child / "baseline").exists()


def test_symlinks_inside_ignored_caches_do_not_block_the_copy(
    tmp_path: Path, fake_repo: Path
) -> None:
    outside = tmp_path / "outside.pyc"
    outside.write_bytes(b"\x01")
    _make_link(fake_repo / "src" / "actseal" / "__pycache__" / "linked.pyc", outside)
    harness.refuse_symlinks(fake_repo)
    child = tmp_path / "child"
    child.mkdir()
    tree = harness.make_tree(child, "baseline", fake_repo)
    assert tree == child / "baseline"
    assert (tree / "src" / "actseal" / "stats.py").read_text(encoding="utf-8") == "TAIL = 4\n"
    assert (tree / "tests" / "unit" / "test_x.py").is_file()
    assert (tree / "pyproject.toml").is_file()
    assert (tree / "actseal_mutation_probe.py").is_file()
    assert not (tree / "src" / "actseal" / "__pycache__").exists()
    assert not (tree / "src" / "actseal" / "linked.pyc").exists()
    copied = {path.relative_to(tree).as_posix() for path in tree.rglob("*") if path.is_file()}
    assert copied == {
        "src/actseal/__init__.py",
        "src/actseal/stats.py",
        "tests/conftest.py",
        "tests/unit/test_x.py",
        "pyproject.toml",
        "actseal_mutation_probe.py",
    }
    assert not any(path.is_symlink() for path in tree.rglob("*"))


def test_tracked_digest_matches_the_copy_and_ignores_caches(
    tmp_path: Path, fake_repo: Path
) -> None:
    digest = harness.tracked_source_digest(fake_repo)
    assert set(digest) == {
        "src/actseal/__init__.py",
        "src/actseal/stats.py",
        "tests/conftest.py",
        "tests/unit/test_x.py",
        "pyproject.toml",
    }
    child = tmp_path / "child"
    child.mkdir()
    tree = harness.make_tree(child, "copy", fake_repo)
    for relative, expected in digest.items():
        assert harness.sha256_file(tree / relative) == expected
