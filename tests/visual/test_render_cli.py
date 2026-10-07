"""The render.py interface: --write/--check [--only ASSET], exit codes, lazy imports.

Every test here is hermetic: the pinned-tool cache is pointed at an empty,
test-local directory (also for the subprocess checks), so nothing stats or
reads the operator's real cache and no result depends on its contents.
Nothing runs a binary or fontTools; the how-it-works figure needs neither,
so it is the one asset a bootstrap repository can write and check.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

from visual.visual_support import MANIFEST, REPO_ROOT, SRC_DIR

RENDER = SRC_DIR / "render.py"
CACHE_ENV = "ACTSEAL_ASSET_TOOLS"

# Three assets are implemented. The how-it-works figure needs no pinned input
# and renders anywhere. The hero needs the pinned font; the social preview
# needs the font and the resvg binary; a bootstrap repository has fetched
# neither. Every other asset is planned.
IMPLEMENTED = ("hero", "how-it-works", "social")
PLANNED = ("architecture", "demo", "where", "matrix", "boundary")
FONT_NOT_FETCHED = (
    "requires jetbrains-mono 2.304; not fetched: JetBrainsMono-Regular.ttf, "
    "JetBrainsMono-Bold.ttf, OFL.txt"
)
SKIPPED = "skipped rendering because prerequisites failed"
HERO_FONT_ERROR = f"[error] hero: {FONT_NOT_FETCHED}"
HERO_SKIPPED = f"[error] hero: {SKIPPED}"
SOCIAL_FONT_ERROR = f"[error] social: {FONT_NOT_FETCHED}"
SOCIAL_SKIPPED = f"[error] social: {SKIPPED}"
FONTS_INFO = "[info] fonts: jetbrains-mono 2.304 not fetched; run setup_tools.py"
# Hero font + skipped, social resvg + font + skipped.
PREREQUISITE_ERRORS = 5
# Four how-it-works outputs that a bootstrap repository has not committed yet.
WORKFLOW_OUTPUTS = 4
FRESH_CHECK_SUMMARY = (
    f"1 asset(s) checked; 5 planned/not implemented; "
    f"{PREREQUISITE_ERRORS + WORKFLOW_OUTPUTS} error(s)"
)
WRITE_SUMMARY = (
    f"1 asset(s) checked; 5 planned/not implemented; {PREREQUISITE_ERRORS} error(s); "
    f"{WORKFLOW_OUTPUTS} file(s) written"
)
CHECKED_SUMMARY = f"1 asset(s) checked; 5 planned/not implemented; {PREREQUISITE_ERRORS} error(s)"


@pytest.fixture(autouse=True)
def tool_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An empty, test-local pinned-tool cache; the operator's cache is never consulted."""
    cache = tmp_path / "empty-tool-cache"
    monkeypatch.setenv(CACHE_ENV, str(cache))
    return cache


def _subprocess_env(cache: Path) -> dict[str, str]:
    return {**os.environ, CACHE_ENV: str(cache)}


def _asset_files(repo: Path) -> list[str]:
    """Every file name under ``docs/assets`` other than the ``src`` tree."""
    asset_dir = repo / "docs" / "assets"
    if not asset_dir.is_dir():
        return []
    return sorted(path.name for path in asset_dir.iterdir() if path.name != "src")


def _workflow_outputs(kit: ModuleType) -> list[str]:
    outputs: list[str] = sorted(kit.how_it_works.OUTPUTS)
    assert len(outputs) == WORKFLOW_OUTPUTS
    return outputs


def _social_resvg_error(kit: ModuleType, cache: Path) -> str:
    """The exact resvg diagnostic for this platform against the empty test cache."""
    tool = kit.tools.load_manifest(MANIFEST)["resvg"]
    key = kit.tools.platform_key()
    artifact = tool.artifact_for(key)
    if artifact is None:
        detail = f"resvg 0.48.1: no pinned artifact for platform {key}"
    else:
        binary = kit.tools.cached_binary_path(tool, artifact)
        assert binary.is_relative_to(cache)
        assert not binary.exists()
        detail = f"resvg 0.48.1 is not cached at {binary}; run setup_tools.py"
    return f"[error] social: requires resvg 0.48.1: {detail}"


def _assert_hero_blocked(out: str) -> None:
    assert HERO_FONT_ERROR in out
    assert HERO_SKIPPED in out
    assert "[ok] hero" not in out
    assert "hero: not implemented" not in out


def _assert_social_blocked(kit: ModuleType, cache: Path, out: str) -> None:
    assert _social_resvg_error(kit, cache) in out
    assert SOCIAL_FONT_ERROR in out
    assert SOCIAL_SKIPPED in out
    assert "[ok] social" not in out
    assert "social: not implemented" not in out
    assert "render failed" not in out


def _assert_planned_informational(out: str) -> None:
    for name in PLANNED:
        assert f"[info] {name}: not implemented (planned in Task " in out
        assert f"[error] {name}" not in out


def _assert_workflow_not_committed(kit: ModuleType, out: str) -> None:
    for output in kit.how_it_works.OUTPUTS:
        assert f"[error] how-it-works: docs/assets/{output} is not committed; run render.py" in out
    assert "[ok] how-it-works" not in out


def _assert_workflow_matches(kit: ModuleType, out: str) -> None:
    for output in kit.how_it_works.OUTPUTS:
        assert f"[ok] how-it-works: docs/assets/{output} matches regeneration (" in out
    assert "[error] how-it-works" not in out


def test_fresh_check_reports_planned_prerequisites_and_uncommitted_workflow(
    kit: ModuleType, repo: Path, tool_cache: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A bootstrap repository: planned assets informational, hero and social blocked.

    The how-it-works figure renders (one asset checked) but its four outputs
    are not committed yet; the hero and the social preview report their
    missing pinned inputs and are never counted as checked.
    """
    assert set(IMPLEMENTED) | set(PLANNED) == set(kit.inventory.ASSET_NAMES)
    assert kit.cli.main(["--check"], root=repo) == 1
    out = capsys.readouterr().out
    _assert_planned_informational(out)
    _assert_hero_blocked(out)
    _assert_social_blocked(kit, tool_cache, out)
    _assert_workflow_not_committed(kit, out)
    assert FONTS_INFO in out
    assert out.count("[error]") == PREREQUISITE_ERRORS + WORKFLOW_OUTPUTS
    assert out.rstrip().endswith(FRESH_CHECK_SUMMARY)
    assert _asset_files(repo) == []


def test_write_then_check_writes_only_the_workflow_and_keeps_prerequisite_errors(
    kit: ModuleType, repo: Path, tool_cache: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Global --write produces exactly the four workflow files; hero and social stay blocked."""
    assert kit.cli.main(["--write"], root=repo) == 1
    written = capsys.readouterr().out
    _assert_planned_informational(written)
    _assert_hero_blocked(written)
    _assert_social_blocked(kit, tool_cache, written)
    for output in kit.how_it_works.OUTPUTS:
        assert f"[ok] how-it-works: wrote docs/assets/{output} (" in written
    assert written.count("[error]") == PREREQUISITE_ERRORS
    assert written.rstrip().endswith(WRITE_SUMMARY)
    assert _asset_files(repo) == _workflow_outputs(kit)

    assert kit.cli.main(["--check"], root=repo) == 1
    checked = capsys.readouterr().out
    _assert_planned_informational(checked)
    _assert_hero_blocked(checked)
    _assert_social_blocked(kit, tool_cache, checked)
    _assert_workflow_matches(kit, checked)
    assert checked.count("[error]") == PREREQUISITE_ERRORS
    assert checked.rstrip().endswith(CHECKED_SUMMARY)
    assert _asset_files(repo) == _workflow_outputs(kit)


def test_workflow_only_write_then_check_passes(
    kit: ModuleType, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert kit.cli.main(["--write", "--only", "how-it-works"], root=repo) == 0
    written = capsys.readouterr().out
    assert "[error]" not in written
    assert written.rstrip().endswith(
        "1 asset(s) checked; 0 planned/not implemented; 0 error(s); 4 file(s) written"
    )
    assert kit.cli.main(["--check", "--only", "how-it-works"], root=repo) == 0
    out = capsys.readouterr().out
    assert "[error]" not in out
    _assert_workflow_matches(kit, out)
    assert "hero" not in out
    assert "social" not in out
    assert out.rstrip().endswith("1 asset(s) checked; 0 planned/not implemented; 0 error(s)")
    assert _asset_files(repo) == _workflow_outputs(kit)


def test_only_implemented_hero_without_font_exits_one(
    kit: ModuleType, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert kit.cli.main(["--check", "--only", "hero"], root=repo) == 1
    out = capsys.readouterr().out
    _assert_hero_blocked(out)
    assert "social" not in out
    assert "how-it-works" not in out
    assert out.rstrip().endswith("0 asset(s) checked; 0 planned/not implemented; 2 error(s)")
    assert _asset_files(repo) == []


@pytest.mark.parametrize("mode", ["--check", "--write"])
def test_only_implemented_social_without_prerequisites_exits_one(
    kit: ModuleType, repo: Path, tool_cache: Path, mode: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """The social preview alone: resvg and font diagnostics, nothing checked or written."""
    assert kit.cli.main([mode, "--only", "social"], root=repo) == 1
    out = capsys.readouterr().out
    _assert_social_blocked(kit, tool_cache, out)
    assert "hero" not in out
    assert "how-it-works" not in out
    assert out.count("[error]") == 3
    expected = "0 asset(s) checked; 0 planned/not implemented; 3 error(s)"
    if mode == "--write":
        expected += "; 0 file(s) written"
    assert out.rstrip().endswith(expected)
    assert _asset_files(repo) == []


def test_only_planned_asset_exits_one(
    kit: ModuleType, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert kit.cli.main(["--check", "--only", "architecture"], root=repo) == 1
    out = capsys.readouterr().out
    assert "[error] architecture: not implemented (planned in Task 13)" in out
    assert "hero" not in out
    assert "social" not in out
    assert "how-it-works" not in out


@pytest.mark.parametrize(
    "argv",
    [[], ["--write", "--check"], ["--check", "--only", "logo"], ["--check", "--bogus"]],
)
def test_usage_errors_exit_two(
    kit: ModuleType, repo: Path, argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert kit.cli.main(argv, root=repo) == 2
    assert "usage: render.py" in capsys.readouterr().err


def test_repository_root_resolves_to_the_checkout(kit: ModuleType) -> None:
    assert kit.cli.repository_root() == REPO_ROOT
    assert (REPO_ROOT / "docs" / "assets" / "src" / "render.py").is_file()


def _run_without_fonttools(repo: Path, cache: Path, argv: list[str]) -> str:
    """Run ``cli.main(argv)`` in a process where fontTools is unavailable; return stdout.

    The caller receives the exit status on the last line as ``exit=N`` so a
    non-zero status can be asserted without hiding the output.
    """
    script = (
        "import sys\n"
        "sys.modules['fontTools'] = None\n"
        f"sys.path.insert(0, {str(SRC_DIR)!r})\n"
        "from actseal_assets import cli\n"
        f"status = cli.main({argv!r}, root={str(repo)!r})\n"
        "print(f'exit={status}')\n"
    )
    result = subprocess.run(  # noqa: S603 - fixed interpreter and literal script, no user input
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
        env=_subprocess_env(cache),
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    return result.stdout


def test_render_script_runs_without_fonttools(
    kit: ModuleType, repo: Path, tool_cache: Path
) -> None:
    """Global --write then --check work without fontTools.

    The workflow figure is written and then matches; the only errors are the
    missing pinned inputs of the hero and the social preview, reported before
    any outlining or tool run; nothing raises or imports fontTools, and the
    empty test cache is the only cache consulted.
    """
    written = _run_without_fonttools(repo, tool_cache, ["--write"])
    assert written.rstrip().endswith("exit=1")
    _assert_hero_blocked(written)
    _assert_social_blocked(kit, tool_cache, written)
    _assert_planned_informational(written)
    assert written.count("[error]") == PREREQUISITE_ERRORS
    assert WRITE_SUMMARY in written
    assert _asset_files(repo) == _workflow_outputs(kit)

    checked = _run_without_fonttools(repo, tool_cache, ["--check"])
    assert checked.rstrip().endswith("exit=1")
    _assert_hero_blocked(checked)
    _assert_social_blocked(kit, tool_cache, checked)
    _assert_workflow_matches(kit, checked)
    assert "[ok] references: 0 image reference(s) checked" in checked
    assert checked.count("[error]") == PREREQUISITE_ERRORS
    assert CHECKED_SUMMARY in checked


def test_render_script_workflow_only_passes_without_fonttools(
    kit: ModuleType, repo: Path, tool_cache: Path
) -> None:
    """The font-independent figure writes and checks cleanly without fontTools."""
    written = _run_without_fonttools(repo, tool_cache, ["--write", "--only", "how-it-works"])
    assert written.rstrip().endswith("exit=0")
    assert "[error]" not in written
    checked = _run_without_fonttools(repo, tool_cache, ["--check", "--only", "how-it-works"])
    assert checked.rstrip().endswith("exit=0")
    assert "[error]" not in checked
    _assert_workflow_matches(kit, checked)
    assert "hero" not in checked
    assert "social" not in checked
    assert _asset_files(repo) == _workflow_outputs(kit)


def test_render_script_check_of_planned_asset_runs_without_fonttools(
    repo: Path, tool_cache: Path
) -> None:
    """The explicit planned-asset request is the only error; implemented assets are untouched."""
    out = _run_without_fonttools(repo, tool_cache, ["--check", "--only", "architecture"])
    assert out.rstrip().endswith("exit=1")
    assert "[error] architecture: not implemented (planned in Task 13)" in out
    assert "hero" not in out
    assert "social" not in out
    assert "how-it-works" not in out
    assert "0 asset(s) checked; 1 planned/not implemented; 1 error(s)" in out


def test_render_script_help(repo: Path, tool_cache: Path) -> None:
    result = subprocess.run(  # noqa: S603 - fixed interpreter and repository script
        [sys.executable, str(RENDER), "--help"],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
        cwd=repo,
        env=_subprocess_env(tool_cache),
    )
    assert result.returncode == 0
    assert "--write" in result.stdout
    assert "--check" in result.stdout
    assert "--only ASSET" in result.stdout


def test_package_does_not_import_fonttools_eagerly() -> None:
    script = (
        "import sys\n"
        f"sys.path.insert(0, {str(SRC_DIR)!r})\n"
        "import actseal_assets\n"
        "print('fontTools' in sys.modules)\n"
    )
    result = subprocess.run(  # noqa: S603 - fixed interpreter and literal script, no user input
        [sys.executable, "-c", script], capture_output=True, text=True, check=False, timeout=120
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False"


def test_runtime_package_has_no_asset_toolchain_dependency() -> None:
    package = REPO_ROOT / "src" / "actseal"
    offenders = [
        path
        for path in package.rglob("*.py")
        if "actseal_assets" in path.read_text(encoding="utf-8")
        or "fontTools" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []
