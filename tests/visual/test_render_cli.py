"""The render.py interface: --write/--check [--only ASSET], exit codes, lazy imports.

Every test here is hermetic: the pinned-tool cache is pointed at an empty,
test-local directory (also for the subprocess checks), so nothing stats or
reads the operator's real cache and no result depends on its contents.
Nothing runs a renderer, a binary or fontTools.
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

# Two assets are implemented but need pinned inputs a bootstrap repository has
# not fetched: the hero needs the font; the social preview needs the font and
# the resvg binary. Every other asset on this branch is planned.
IMPLEMENTED = ("hero", "social")
PLANNED = ("how-it-works", "architecture", "demo", "where", "matrix", "boundary")
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
BOOTSTRAP_SUMMARY = "0 asset(s) checked; 6 planned/not implemented; 5 error(s)"


@pytest.fixture(autouse=True)
def tool_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An empty, test-local pinned-tool cache; the operator's cache is never consulted."""
    cache = tmp_path / "empty-tool-cache"
    monkeypatch.setenv(CACHE_ENV, str(cache))
    return cache


def _subprocess_env(cache: Path) -> dict[str, str]:
    return {**os.environ, CACHE_ENV: str(cache)}


def _asset_files(repo: Path) -> list[Path]:
    """Every file under ``docs/assets`` other than the ``src`` tree; must stay empty."""
    asset_dir = repo / "docs" / "assets"
    if not asset_dir.is_dir():
        return []
    return sorted(path for path in asset_dir.iterdir() if path.name != "src")


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


@pytest.mark.parametrize("mode", ["--check", "--write"])
def test_bootstrap_repository_reports_planned_assets_and_missing_prerequisites(
    kit: ModuleType, repo: Path, tool_cache: Path, mode: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """Planned assets stay informational; the implemented assets fail on absent inputs.

    The hero reports its missing pinned font; the social preview reports the
    uncached resvg binary and the missing font. Nothing is rendered or
    written for either and neither is counted as checked, in either mode.
    """
    assert set(IMPLEMENTED) | set(PLANNED) == set(kit.inventory.ASSET_NAMES)
    assert kit.cli.main([mode], root=repo) == 1
    out = capsys.readouterr().out
    for name in PLANNED:
        assert f"[info] {name}: not implemented (planned in Task " in out
        assert f"[error] {name}" not in out
    _assert_hero_blocked(out)
    _assert_social_blocked(kit, tool_cache, out)
    assert FONTS_INFO in out
    assert out.count("[error]") == 5
    expected = BOOTSTRAP_SUMMARY
    if mode == "--write":
        expected += "; 0 file(s) written"
    assert out.rstrip().endswith(expected)
    assert _asset_files(repo) == []


def test_only_implemented_hero_without_font_exits_one(
    kit: ModuleType, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert kit.cli.main(["--check", "--only", "hero"], root=repo) == 1
    out = capsys.readouterr().out
    _assert_hero_blocked(out)
    assert "social" not in out
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


def test_render_script_runs_without_fonttools(
    kit: ModuleType, repo: Path, tool_cache: Path
) -> None:
    """Import, global checks and prerequisite reporting work without fontTools.

    The only errors are the missing pinned inputs of the two implemented
    assets, reported by the pipeline before any outlining or tool run;
    nothing raises or imports fontTools, and the empty test cache is the only
    cache consulted.
    """
    script = (
        "import sys\n"
        "sys.modules['fontTools'] = None\n"
        f"sys.path.insert(0, {str(SRC_DIR)!r})\n"
        "from actseal_assets import cli\n"
        f"raise SystemExit(cli.main(['--check'], root={str(repo)!r}))\n"
    )
    result = subprocess.run(  # noqa: S603 - fixed interpreter and literal script, no user input
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
        env=_subprocess_env(tool_cache),
    )
    assert result.returncode == 1, result.stderr
    assert result.stderr == ""
    _assert_hero_blocked(result.stdout)
    _assert_social_blocked(kit, tool_cache, result.stdout)
    for name in PLANNED:
        assert f"[info] {name}: not implemented (planned in Task " in result.stdout
    assert "[ok] references: 0 image reference(s) checked" in result.stdout
    assert result.stdout.count("[error]") == 5
    assert result.stdout.rstrip().endswith(BOOTSTRAP_SUMMARY)
    assert _asset_files(repo) == []


def test_render_script_check_of_planned_asset_runs_without_fonttools(
    repo: Path, tool_cache: Path
) -> None:
    """A font-independent path completes without fontTools.

    The explicit planned-asset request is the only error; neither implemented
    asset nor its prerequisites are touched.
    """
    script = (
        "import sys\n"
        "sys.modules['fontTools'] = None\n"
        f"sys.path.insert(0, {str(SRC_DIR)!r})\n"
        "from actseal_assets import cli\n"
        f"raise SystemExit(cli.main(['--check', '--only', 'architecture'], root={str(repo)!r}))\n"
    )
    result = subprocess.run(  # noqa: S603 - fixed interpreter and literal script, no user input
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
        env=_subprocess_env(tool_cache),
    )
    assert result.returncode == 1, result.stderr
    assert result.stderr == ""
    assert "[error] architecture: not implemented (planned in Task 13)" in result.stdout
    assert "hero" not in result.stdout
    assert "social" not in result.stdout
    summary = "0 asset(s) checked; 1 planned/not implemented; 1 error(s)"
    assert result.stdout.rstrip().endswith(summary)


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
