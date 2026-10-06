"""The render.py interface: --write/--check [--only ASSET], exit codes, lazy imports."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

from visual.visual_support import REPO_ROOT, SRC_DIR

RENDER = SRC_DIR / "render.py"


def test_check_on_bootstrap_repository_reports_planned_assets(
    kit: ModuleType, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert kit.cli.main(["--check"], root=repo) == 0
    out = capsys.readouterr().out
    for name in kit.inventory.ASSET_NAMES:
        assert f"[info] {name}: not implemented (planned in Task " in out
    assert out.rstrip().endswith("8 planned/not implemented; 0 error(s)")
    assert "[error]" not in out


def test_only_planned_asset_exits_one(
    kit: ModuleType, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert kit.cli.main(["--check", "--only", "hero"], root=repo) == 1
    out = capsys.readouterr().out
    assert "[error] hero: not implemented (planned in Task 11)" in out
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
    """The script path and --check work in a process where fontTools is unavailable."""
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
    assert result.returncode == 0, result.stderr
    assert "0 error(s)" in result.stdout


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
