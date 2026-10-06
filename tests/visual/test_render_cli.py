"""The render.py interface: --write/--check [--only ASSET], exit codes, lazy imports."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

from visual.visual_support import REPO_ROOT, SRC_DIR

RENDER = SRC_DIR / "render.py"

# The hero is implemented but needs the pinned font, which a bootstrap
# repository has not fetched. Every other asset on this branch is planned.
IMPLEMENTED_NEEDING_FONTS = ("hero",)
PLANNED = ("how-it-works", "architecture", "demo", "social", "where", "matrix", "boundary")
HERO_FONT_ERROR = (
    "[error] hero: requires jetbrains-mono 2.304; not fetched: JetBrainsMono-Regular.ttf, "
    "JetBrainsMono-Bold.ttf, OFL.txt"
)
HERO_SKIPPED = "[error] hero: skipped rendering because prerequisites failed"


def _hero_files(repo: Path) -> list[Path]:
    asset_dir = repo / "docs" / "assets"
    return sorted(asset_dir.glob("hero*")) if asset_dir.is_dir() else []


@pytest.mark.parametrize("mode", ["--check", "--write"])
def test_bootstrap_repository_reports_planned_assets_and_missing_hero_font(
    kit: ModuleType, repo: Path, mode: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """Planned assets stay informational; the implemented hero fails on its absent font.

    Nothing is rendered or written for the hero and it is never counted as
    checked, in either mode.
    """
    assert set(IMPLEMENTED_NEEDING_FONTS) | set(PLANNED) == set(kit.inventory.ASSET_NAMES)
    assert kit.cli.main([mode], root=repo) == 1
    out = capsys.readouterr().out
    for name in PLANNED:
        assert f"[info] {name}: not implemented (planned in Task " in out
        assert f"[error] {name}" not in out
    assert HERO_FONT_ERROR in out
    assert HERO_SKIPPED in out
    assert "[ok] hero" not in out
    assert "[info] fonts: jetbrains-mono 2.304 not fetched; run setup_tools.py" in out
    expected = "0 asset(s) checked; 7 planned/not implemented; 2 error(s)"
    if mode == "--write":
        expected += "; 0 file(s) written"
    assert out.rstrip().endswith(expected)
    assert _hero_files(repo) == []


def test_only_implemented_hero_without_font_exits_one(
    kit: ModuleType, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert kit.cli.main(["--check", "--only", "hero"], root=repo) == 1
    out = capsys.readouterr().out
    assert HERO_FONT_ERROR in out
    assert HERO_SKIPPED in out
    assert "hero: not implemented" not in out
    assert out.rstrip().endswith("0 asset(s) checked; 0 planned/not implemented; 2 error(s)")
    assert _hero_files(repo) == []


def test_only_planned_asset_exits_one(
    kit: ModuleType, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert kit.cli.main(["--check", "--only", "architecture"], root=repo) == 1
    out = capsys.readouterr().out
    assert "[error] architecture: not implemented (planned in Task 13)" in out
    assert "hero" not in out
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


def test_render_script_runs_without_fonttools(repo: Path) -> None:
    """Import, global checks and prerequisite reporting work without fontTools.

    The only errors are the hero's missing pinned font, reported by the
    pipeline before any outlining; nothing raises or imports fontTools.
    """
    script = (
        "import sys\n"
        "sys.modules['fontTools'] = None\n"
        f"sys.path.insert(0, {str(SRC_DIR)!r})\n"
        "from actseal_assets import cli\n"
        f"raise SystemExit(cli.main(['--check'], root={str(repo)!r}))\n"
    )
    result = subprocess.run(  # noqa: S603 - fixed interpreter and literal script, no user input
        [sys.executable, "-c", script], capture_output=True, text=True, check=False, timeout=120
    )
    assert result.returncode == 1, result.stderr
    assert result.stderr == ""
    assert HERO_FONT_ERROR in result.stdout
    assert HERO_SKIPPED in result.stdout
    assert "[ok] references: 0 image reference(s) checked" in result.stdout
    summary = "0 asset(s) checked; 7 planned/not implemented; 2 error(s)"
    assert result.stdout.rstrip().endswith(summary)
    assert _hero_files(repo) == []


def test_render_script_check_of_planned_asset_runs_without_fonttools(repo: Path) -> None:
    """A font-independent path completes without fontTools.

    The explicit planned-asset request is the only error; the hero and its
    font requirement are not touched.
    """
    script = (
        "import sys\n"
        "sys.modules['fontTools'] = None\n"
        f"sys.path.insert(0, {str(SRC_DIR)!r})\n"
        "from actseal_assets import cli\n"
        f"raise SystemExit(cli.main(['--check', '--only', 'architecture'], root={str(repo)!r}))\n"
    )
    result = subprocess.run(  # noqa: S603 - fixed interpreter and literal script, no user input
        [sys.executable, "-c", script], capture_output=True, text=True, check=False, timeout=120
    )
    assert result.returncode == 1, result.stderr
    assert result.stderr == ""
    assert "[error] architecture: not implemented (planned in Task 13)" in result.stdout
    assert "hero" not in result.stdout
    summary = "0 asset(s) checked; 1 planned/not implemented; 1 error(s)"
    assert result.stdout.rstrip().endswith(summary)


def test_render_script_help(repo: Path) -> None:
    result = subprocess.run(  # noqa: S603 - fixed interpreter and repository script
        [sys.executable, str(RENDER), "--help"],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
        cwd=repo,
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
