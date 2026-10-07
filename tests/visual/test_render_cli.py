"""The render.py interface: --write/--check [--only ASSET], exit codes, lazy imports.

Every test here is hermetic: the pinned-tool cache is pointed at an empty,
test-local directory (also for the subprocess checks), so nothing stats or
reads the operator's real cache and no result depends on its contents.
Nothing runs a binary or fontTools; the how-it-works and architecture figures
need neither, so they are the assets a bootstrap repository can write and check.
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

# Five assets are implemented. The how-it-works and architecture figures need
# no pinned input and render anywhere. The hero needs the pinned font; the
# social preview needs the font and the resvg binary; the demo needs the
# font, the agg binary and the committed raw recording; a bootstrap
# repository has none of them. Every other asset is planned.
IMPLEMENTED = ("hero", "how-it-works", "architecture", "social", "demo")
PLANNED = ("where", "matrix", "boundary")
#: A planned asset used where a test needs one that is explicitly not implemented.
PLANNED_EXAMPLE = ("where", "16")
FONT_NOT_FETCHED = (
    "requires jetbrains-mono 2.304; not fetched: JetBrainsMono-Regular.ttf, "
    "JetBrainsMono-Bold.ttf, OFL.txt"
)
SKIPPED = "skipped rendering because prerequisites failed"
HERO_FONT_ERROR = f"[error] hero: {FONT_NOT_FETCHED}"
HERO_SKIPPED = f"[error] hero: {SKIPPED}"
SOCIAL_FONT_ERROR = f"[error] social: {FONT_NOT_FETCHED}"
SOCIAL_SKIPPED = f"[error] social: {SKIPPED}"
DEMO_FONT_ERROR = f"[error] demo: {FONT_NOT_FETCHED}"
DEMO_CAST_MISSING = "[error] demo: source docs/assets/src/demo.cast is not present"
DEMO_SKIPPED = f"[error] demo: {SKIPPED}"
FONTS_INFO = "[info] fonts: jetbrains-mono 2.304 not fetched; run setup_tools.py"
# Hero font + skipped, social resvg + font + skipped, demo agg + font + cast + skipped.
PREREQUISITE_ERRORS = 9
# Four how-it-works outputs and four architecture outputs that a bootstrap
# repository has not committed yet.
WORKFLOW_OUTPUTS = 4
ARCHITECTURE_OUTPUTS = 4
FONT_FREE_OUTPUTS = WORKFLOW_OUTPUTS + ARCHITECTURE_OUTPUTS
FRESH_CHECK_SUMMARY = (
    f"2 asset(s) checked; 3 planned/not implemented; "
    f"{PREREQUISITE_ERRORS + FONT_FREE_OUTPUTS} error(s)"
)
WRITE_SUMMARY = (
    f"2 asset(s) checked; 3 planned/not implemented; {PREREQUISITE_ERRORS} error(s); "
    f"{FONT_FREE_OUTPUTS} file(s) written"
)
CHECKED_SUMMARY = f"2 asset(s) checked; 3 planned/not implemented; {PREREQUISITE_ERRORS} error(s)"


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


def _architecture_outputs(kit: ModuleType) -> list[str]:
    outputs: list[str] = sorted(kit.architecture.OUTPUTS)
    assert len(outputs) == ARCHITECTURE_OUTPUTS
    return outputs


def _font_free_outputs(kit: ModuleType) -> list[str]:
    """Every file a bootstrap repository can write: both font-free figures."""
    return sorted([*_workflow_outputs(kit), *_architecture_outputs(kit)])


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


def _demo_agg_error(kit: ModuleType, cache: Path) -> str:
    tool = kit.tools.load_manifest(MANIFEST)["agg"]
    key = kit.tools.platform_key()
    artifact = tool.artifact_for(key)
    if artifact is None:
        detail = f"agg 1.9.0: no pinned artifact for platform {key}"
    else:
        binary = kit.tools.cached_binary_path(tool, artifact)
        assert binary.is_relative_to(cache)
        assert not binary.exists()
        detail = f"agg 1.9.0 is not cached at {binary}; run setup_tools.py"
    return f"[error] demo: requires agg 1.9.0: {detail}"


def _assert_demo_blocked(kit: ModuleType, cache: Path, out: str) -> None:
    """The demo is implemented but its three inputs are absent; agg never runs."""
    assert _demo_agg_error(kit, cache) in out
    assert DEMO_FONT_ERROR in out
    assert DEMO_CAST_MISSING in out
    assert DEMO_SKIPPED in out
    assert "[ok] demo" not in out
    assert "demo: not implemented" not in out
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


def _assert_architecture_not_committed(kit: ModuleType, out: str) -> None:
    for output in kit.architecture.OUTPUTS:
        assert f"[error] architecture: docs/assets/{output} is not committed; run render.py" in out
    assert "[ok] architecture" not in out
    assert "architecture: not implemented" not in out


def _assert_architecture_matches(kit: ModuleType, out: str) -> None:
    for output in kit.architecture.OUTPUTS:
        assert f"[ok] architecture: docs/assets/{output} matches regeneration (" in out
    assert "[error] architecture" not in out


def test_fresh_check_reports_planned_prerequisites_and_uncommitted_workflow(
    kit: ModuleType, repo: Path, tool_cache: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A bootstrap repository: planned assets informational, hero, social and demo blocked.

    The how-it-works and architecture figures render (two assets checked) but
    their eight outputs are not committed yet; the hero and the social preview
    report their missing pinned inputs and are never counted as checked.
    """
    assert set(IMPLEMENTED) | set(PLANNED) == set(kit.inventory.ASSET_NAMES)
    assert kit.cli.main(["--check"], root=repo) == 1
    out = capsys.readouterr().out
    _assert_planned_informational(out)
    _assert_hero_blocked(out)
    _assert_social_blocked(kit, tool_cache, out)
    _assert_demo_blocked(kit, tool_cache, out)
    _assert_workflow_not_committed(kit, out)
    _assert_architecture_not_committed(kit, out)
    assert FONTS_INFO in out
    assert out.count("[error]") == PREREQUISITE_ERRORS + FONT_FREE_OUTPUTS
    assert out.rstrip().endswith(FRESH_CHECK_SUMMARY)
    assert _asset_files(repo) == []


def test_write_then_check_writes_only_the_workflow_and_keeps_prerequisite_errors(
    kit: ModuleType, repo: Path, tool_cache: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Global --write produces exactly the eight font-free files; hero/social/demo stay blocked."""
    assert kit.cli.main(["--write"], root=repo) == 1
    written = capsys.readouterr().out
    _assert_planned_informational(written)
    _assert_hero_blocked(written)
    _assert_social_blocked(kit, tool_cache, written)
    _assert_demo_blocked(kit, tool_cache, written)
    for output in kit.how_it_works.OUTPUTS:
        assert f"[ok] how-it-works: wrote docs/assets/{output} (" in written
    for output in kit.architecture.OUTPUTS:
        assert f"[ok] architecture: wrote docs/assets/{output} (" in written
    assert written.count("[error]") == PREREQUISITE_ERRORS
    assert written.rstrip().endswith(WRITE_SUMMARY)
    assert _asset_files(repo) == _font_free_outputs(kit)

    assert kit.cli.main(["--check"], root=repo) == 1
    checked = capsys.readouterr().out
    _assert_planned_informational(checked)
    _assert_hero_blocked(checked)
    _assert_social_blocked(kit, tool_cache, checked)
    _assert_demo_blocked(kit, tool_cache, checked)
    _assert_workflow_matches(kit, checked)
    _assert_architecture_matches(kit, checked)
    assert checked.count("[error]") == PREREQUISITE_ERRORS
    assert checked.rstrip().endswith(CHECKED_SUMMARY)
    assert _asset_files(repo) == _font_free_outputs(kit)


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
    assert "architecture" not in out
    assert out.rstrip().endswith("1 asset(s) checked; 0 planned/not implemented; 0 error(s)")
    assert _asset_files(repo) == _workflow_outputs(kit)


def test_architecture_only_write_then_check_passes(
    kit: ModuleType, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The architecture figure needs no pinned input: it writes and checks in a bootstrap repo."""
    assert kit.cli.main(["--write", "--only", "architecture"], root=repo) == 0
    written = capsys.readouterr().out
    assert "[error]" not in written
    assert written.rstrip().endswith(
        "1 asset(s) checked; 0 planned/not implemented; 0 error(s); 4 file(s) written"
    )
    assert kit.cli.main(["--check", "--only", "architecture"], root=repo) == 0
    out = capsys.readouterr().out
    assert "[error]" not in out
    _assert_architecture_matches(kit, out)
    assert "hero" not in out
    assert "social" not in out
    assert "how-it-works" not in out
    assert out.rstrip().endswith("1 asset(s) checked; 0 planned/not implemented; 0 error(s)")
    assert _asset_files(repo) == _architecture_outputs(kit)


def test_only_implemented_hero_without_font_exits_one(
    kit: ModuleType, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert kit.cli.main(["--check", "--only", "hero"], root=repo) == 1
    out = capsys.readouterr().out
    _assert_hero_blocked(out)
    assert "social" not in out
    assert "how-it-works" not in out
    assert "architecture" not in out
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
    assert "architecture" not in out
    assert "demo" not in out
    assert out.count("[error]") == 3
    expected = "0 asset(s) checked; 0 planned/not implemented; 3 error(s)"
    if mode == "--write":
        expected += "; 0 file(s) written"
    assert out.rstrip().endswith(expected)
    assert _asset_files(repo) == []


def test_only_planned_asset_exits_one(
    kit: ModuleType, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    name, task = PLANNED_EXAMPLE
    assert kit.cli.main(["--check", "--only", name], root=repo) == 1
    out = capsys.readouterr().out
    assert f"[error] {name}: not implemented (planned in Task {task})" in out
    assert "hero" not in out
    assert "social" not in out
    assert "how-it-works" not in out
    assert "architecture" not in out


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

    Both font-free figures are written and then match; the only errors are the
    missing pinned inputs of the hero and the social preview, reported before
    any outlining or tool run; nothing raises or imports fontTools, and the
    empty test cache is the only cache consulted.
    """
    written = _run_without_fonttools(repo, tool_cache, ["--write"])
    assert written.rstrip().endswith("exit=1")
    _assert_hero_blocked(written)
    _assert_social_blocked(kit, tool_cache, written)
    _assert_demo_blocked(kit, tool_cache, written)
    _assert_planned_informational(written)
    assert written.count("[error]") == PREREQUISITE_ERRORS
    assert WRITE_SUMMARY in written
    assert _asset_files(repo) == _font_free_outputs(kit)

    checked = _run_without_fonttools(repo, tool_cache, ["--check"])
    assert checked.rstrip().endswith("exit=1")
    _assert_hero_blocked(checked)
    _assert_social_blocked(kit, tool_cache, checked)
    _assert_demo_blocked(kit, tool_cache, checked)
    _assert_workflow_matches(kit, checked)
    _assert_architecture_matches(kit, checked)
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
    name, task = PLANNED_EXAMPLE
    out = _run_without_fonttools(repo, tool_cache, ["--check", "--only", name])
    assert out.rstrip().endswith("exit=1")
    assert f"[error] {name}: not implemented (planned in Task {task})" in out
    assert "hero" not in out
    assert "social" not in out
    assert "how-it-works" not in out
    assert "architecture" not in out
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
