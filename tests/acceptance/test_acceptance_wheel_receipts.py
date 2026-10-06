"""Source-to-wheel and demonstration receipts from a fresh installed environment (``packaging``).

Preparation builds the real wheel with ``uv build --no-sources``, creates a
fresh virtual environment outside the checkout and installs that wheel with
``--no-deps --offline``. Guarded application runs instrument sockets and
prohibited imports BEFORE importing Actseal and report the real installed
package path, which must lie inside that environment and outside the checkout.
The documented quickstart command shapes are checked against the installed
``--help`` output, the console demo is timed against the 60-second target, and
every exit code (0/1/2/3) is exercised through both installed entrypoints with
parseable JSON. No model is loaded or downloaded.

Supplied wheel: when ``ACTSEAL_TEST_WHEEL`` names an existing absolute
``actseal-*.whl`` path, that exact file is installed and ``uv build`` is never
invoked. The release workflow uses this to test the immutable built artifact.
Any other value fails the run; the tests never fall back to rebuilding.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest
from acceptance_support import (
    EXIT_CODES,
    ROOT,
    CliResult,
    Workspace,
    clean_env,
    lock_argv,
    run_cli,
    verify_argv,
    write_workspace,
)

pytestmark = pytest.mark.packaging

DEMO_BUDGET_S = 60.0
DOCUMENTS = (ROOT / "README.md", ROOT / "docs" / "quickstart.md")
OPTIONAL_MODULES = ("laya", "torch", "transformers", "huggingface_hub", "safetensors", "numpy")
DEMO_BLOCKED = ",".join(
    (
        "actseal.adapters.laya",
        *OPTIONAL_MODULES,
        "importlib.metadata",
        "subprocess",
        "multiprocessing",
        "urllib.request",
        "http",
        "ssl",
        "pickle",
        "runpy",
    )
)
REPLAY_BLOCKED = DEMO_BLOCKED.replace("actseal.adapters.laya", "actseal.adapters")

_GUARDED_APP = r"""
import io
import json
import os
import socket
import sys

BLOCKED = tuple(sys.argv[1].split(","))
CHECKOUT = os.path.realpath(sys.argv[2])
VENV = os.path.realpath(sys.argv[3])


def _blocked(name):
    return any(name == root or name.startswith(root + ".") for root in BLOCKED)


class DenyImports:
    def find_spec(self, name, path=None, target=None):
        if _blocked(name):
            raise ImportError("blocked import: " + name)
        return None


sys.meta_path.insert(0, DenyImports())


def _no_network(*_args, **_kwargs):
    raise RuntimeError("network blocked")


socket.socket = _no_network
socket.create_connection = _no_network
socket.getaddrinfo = _no_network
socket.socketpair = _no_network

import actseal  # noqa: E402
from actseal.cli import main  # noqa: E402

buffer = io.StringIO()
real_stdout = sys.stdout
sys.stdout = buffer
try:
    code = main(sys.argv[4:])
finally:
    sys.stdout = real_stdout
paths = sorted(
    {
        os.path.realpath(module.__file__)
        for name, module in sys.modules.items()
        if name.split(".")[0] == "actseal" and getattr(module, "__file__", None)
    }
)
print(
    json.dumps(
        {
            "code": code,
            "stdout": buffer.getvalue(),
            "blocked_loaded": sorted(name for name in sys.modules if _blocked(name)),
            "package_file": os.path.realpath(actseal.__file__),
            "all_inside_venv": all(path.startswith(VENV + os.sep) for path in paths),
            "any_inside_checkout": any(path.startswith(CHECKOUT + os.sep) for path in paths),
            "module_count": len(paths),
        }
    )
)
"""


# --------------------------------------------------------------------------- #
# Preparation: wheel, fresh environment, installed entrypoints
# --------------------------------------------------------------------------- #


def tool(argv: Sequence[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed tool invocations with test-owned paths
        list(argv),
        capture_output=True,
        text=True,
        check=True,
        cwd=str(cwd),
        env=clean_env(),
        timeout=600,
    )


@pytest.fixture(scope="module")
def outside(tmp_path_factory: pytest.TempPathFactory) -> Path:
    directory = tmp_path_factory.mktemp("acceptance-outside-checkout")
    assert not directory.resolve().is_relative_to(ROOT.resolve())
    return directory


@pytest.fixture(scope="module")
def uv() -> str:
    binary = shutil.which("uv")
    if binary is None:
        pytest.fail("uv is required on PATH to build and install the wheel under test")
    return binary


def supplied_wheel() -> Path | None:
    """The exact wheel named by ``ACTSEAL_TEST_WHEEL``; ``None`` means build one here."""
    raw = os.environ.get("ACTSEAL_TEST_WHEEL")
    if raw is None:
        return None
    path = Path(raw)
    if not path.is_absolute():
        problem = "is not an absolute path"
    elif not path.is_file():
        problem = "is not an existing regular file"
    elif not (path.name.startswith("actseal-") and path.suffix == ".whl"):
        problem = "is not named actseal-*.whl"
    else:
        return path
    pytest.fail(f"ACTSEAL_TEST_WHEEL={raw!r} {problem}; refusing to rebuild")


@pytest.fixture(scope="module")
def wheel(outside: Path, uv: str) -> Path:
    supplied = supplied_wheel()
    if supplied is not None:
        return supplied
    dist = outside / "dist"
    tool([uv, "build", "--no-sources", "--wheel", "--out-dir", str(dist)], cwd=ROOT)
    wheels = sorted(dist.glob("actseal-*.whl"))
    assert len(wheels) == 1, wheels
    return wheels[0]


@dataclass(frozen=True)
class Installed:
    venv: Path
    python: Path
    console: Path

    @property
    def entries(self) -> dict[str, tuple[str, ...]]:
        return {"console": (str(self.console),), "module": (str(self.python), "-m", "actseal")}


@pytest.fixture(scope="module")
def installed(outside: Path, uv: str, wheel: Path) -> Installed:
    venv = outside / "venv"
    tool([uv, "venv", "--python", sys.executable, str(venv)], cwd=outside)
    python = venv / "bin" / "python"
    tool(
        [uv, "pip", "install", "--python", str(python), "--no-deps", "--offline", str(wheel)],
        cwd=outside,
    )
    console = venv / "bin" / "actseal"
    assert console.is_file(), "console script missing: [project.scripts] actseal is required"
    return Installed(venv, python, console)


def guarded(
    installed: Installed, blocked: str, argv: Sequence[str], *, cwd: Path
) -> dict[str, object]:
    result = tool(
        [str(installed.python), "-c", _GUARDED_APP, blocked, str(ROOT), str(installed.venv), *argv],
        cwd=cwd,
    )
    report = json.loads(result.stdout)
    assert isinstance(report, dict)
    assert report["blocked_loaded"] == []
    assert report["all_inside_venv"] is True, report["package_file"]
    assert report["any_inside_checkout"] is False, report["package_file"]
    return {str(key): value for key, value in report.items()}


@dataclass(frozen=True)
class DemoReceipt:
    directory: Path
    document: dict[str, object]
    elapsed_s: float


@pytest.fixture(scope="module")
def console_demo(installed: Installed, outside: Path) -> DemoReceipt:
    """The documented first-run command from the installed console script, timed."""
    out = outside / "quickstart-demo"
    started = time.monotonic()
    result = run_cli((str(installed.console),), ["demo", "--out", str(out), "--json"], cwd=outside)
    elapsed = time.monotonic() - started
    assert result.code == 0, result.stderr
    document = result.json()
    sys.stderr.write(
        f"\ninstalled-wheel console demo: {elapsed:.3f}s wall clock, "
        f"{float(str(document['duration_s'])):.3f}s inside the demo\n"
    )
    return DemoReceipt(out, document, elapsed)


# --------------------------------------------------------------------------- #
# Acceptance 5: installed boundary, documented commands, measured demo
# --------------------------------------------------------------------------- #


def test_installed_package_is_isolated_from_the_checkout(
    installed: Installed, outside: Path
) -> None:
    report = guarded(installed, REPLAY_BLOCKED, ["--version"], cwd=outside)
    assert report["code"] == 0
    assert str(report["stdout"]).startswith("actseal 0.1.0")
    package = Path(str(report["package_file"]))
    assert package.is_relative_to(installed.venv.resolve())
    assert not package.is_relative_to(ROOT.resolve())
    probe = (
        "import importlib.util, json; print(json.dumps({name: importlib.util.find_spec(name) "
        f"is not None for name in {list(OPTIONAL_MODULES)!r}}}))"
    )
    result = tool([str(installed.python), "-c", probe], cwd=outside)
    assert json.loads(result.stdout) == dict.fromkeys(OPTIONAL_MODULES, False)


def documented_commands() -> list[tuple[Path, str, list[str]]]:
    """``actseal`` command lines inside fenced code blocks of the public documents."""
    commands: list[tuple[Path, str, list[str]]] = []
    for document in DOCUMENTS:
        inside = False
        buffered: list[str] = []
        for raw in document.read_text(encoding="utf-8").splitlines():
            if raw.startswith("```"):
                inside = not inside
                continue
            if not inside:
                continue
            if "actseal " in raw and not raw.lstrip().startswith("#"):
                if buffered:
                    commands.append((document, buffered[0], buffered[1:]))
                buffered = [raw.strip()]
            elif buffered and raw.startswith(" "):
                buffered.append(raw.strip())
        if buffered:
            commands.append((document, buffered[0], buffered[1:]))
    return commands


def test_documented_command_shapes_match_the_installed_cli(
    installed: Installed, outside: Path
) -> None:
    commands = documented_commands()
    assert commands, "no actseal command found in README.md or docs/quickstart.md"
    helps: dict[str, str] = {}
    seen_demo = False
    for document, first, continuation in commands:
        tokens = " ".join([first, *continuation]).split()
        tokens = tokens[tokens.index("actseal") + 1 :]  # ignore any `uv run ...` prefix
        subcommand = tokens[0]
        assert subcommand in {"lock", "verify", "replay", "demo"}, (document, first)
        seen_demo = seen_demo or subcommand == "demo"
        if subcommand not in helps:
            result = run_cli((str(installed.console),), [subcommand, "--help"], cwd=outside)
            assert result.code == 0, result.stderr
            helps[subcommand] = result.stdout
        options = {match.group(0) for match in re.finditer(r"--[a-z][a-z0-9-]*", " ".join(tokens))}
        for option in options:
            assert option in helps[subcommand], (document.name, first, option)
        assert "--timeout-seconds" not in helps[subcommand]
    assert seen_demo, "the documented quickstart must include the demo command"


def test_quickstart_demo_from_the_installed_console_is_within_budget(
    console_demo: DemoReceipt, installed: Installed, outside: Path
) -> None:
    assert console_demo.elapsed_s < DEMO_BUDGET_S
    document = console_demo.document
    assert document["ok"] is True
    assert document["demo_only"] is True
    runs = document["runs"]
    assert isinstance(runs, dict)
    assert list(runs) == ["bad", "fixed"]
    for name, status in (("bad", "BLOCK"), ("fixed", "PASS")):
        run = runs[name]
        assert isinstance(run, dict)
        assert run["status"] == status
        assert run["replay_matches"] is True
        assert (run["total"], run["accepted"]) == (128, 128)
        assert run["errors"] == (32 if name == "bad" else 0)
        assert Path(str(run["evidence"])).is_relative_to(console_demo.directory)
        for entry in installed.entries.values():
            replayed = run_cli(
                entry,
                [
                    "replay",
                    str(run["evidence"]),
                    "--expected-lock-sha256",
                    str(run["lock_sha256"]),
                    "--json",
                ],
                cwd=outside,
            )
            assert replayed.code == EXIT_CODES[status], replayed.stderr
            replay_document = replayed.json()
            assert replay_document["status"] == status
            assert replay_document["lock_sha256"] == run["lock_sha256"]
    again = run_cli(
        (str(installed.console),), ["demo", "--out", str(console_demo.directory)], cwd=outside
    )
    assert again.code == 3


@pytest.mark.parametrize("entry_name", ["console", "module"])
def test_installed_entrypoints_exercise_every_exit_code(
    installed: Installed, console_demo: DemoReceipt, outside: Path, tmp_path: Path, entry_name: str
) -> None:
    entry = installed.entries[entry_name]
    runs = console_demo.document["runs"]
    assert isinstance(runs, dict)
    codes: dict[int, CliResult] = {}
    for name, expected in (("bad", 1), ("fixed", 0)):
        result = run_cli(entry, ["replay", str(runs[name]["evidence"]), "--json"], cwd=outside)
        assert result.code == expected, result.stderr
        codes[expected] = result
    workspace: Workspace = write_workspace(tmp_path / "ws", count=6, prefix=f"ins-{entry_name}")
    lock = tmp_path / "lock.json"
    locked = run_cli(entry, [*lock_argv(workspace, lock, "--offline"), "--json"], cwd=tmp_path)
    assert locked.code == 0, locked.stderr
    out = tmp_path / "evidence"
    verified = run_cli(
        entry, [*verify_argv(workspace, lock, out, "--offline"), "--json"], cwd=tmp_path
    )
    assert verified.code == 2, verified.stderr
    assert verified.json()["status"] == "INCONCLUSIVE"
    codes[2] = run_cli(entry, ["replay", str(out), "--json"], cwd=tmp_path)
    assert codes[2].code == 2
    errors = {
        "wrong-anchor": ["replay", str(out), "--expected-lock-sha256", "b" * 64, "--json"],
        "invalid-anchor": ["replay", str(out), "--expected-lock-sha256", "nothex", "--json"],
        "timeout-override": ["replay", str(out), "--timeout-seconds", "5", "--json"],
        "missing-bundle": ["replay", str(tmp_path / "absent"), "--json"],
        "usage": ["verify", "--json"],
    }
    for name, argv in errors.items():
        result = run_cli(entry, argv, cwd=tmp_path)
        assert result.code == 3, (name, result.stderr)
        document = result.json()
        assert document["status"] == "ERROR", name
        assert document["ok"] is False
        reasons = document.get("reasons")
        if reasons is not None:
            assert isinstance(reasons, list)
            assert all(str(reason).startswith("integrity.") for reason in reasons)
        codes[3] = result
    assert sorted(codes) == [0, 1, 2, 3]
    for code, result in codes.items():
        document = result.json()
        assert document["exit_code"] == code
        assert document["ok"] is (code == 0)
        if code < 3:
            assert document["status"] == {0: "PASS", 1: "BLOCK", 2: "INCONCLUSIVE"}[code]


def test_guarded_installed_demo_replay_and_fixture_runs_are_provider_free(
    installed: Installed, tmp_path: Path
) -> None:
    demo = tmp_path / "guarded-demo"
    report = guarded(installed, DEMO_BLOCKED, ["demo", "--out", str(demo), "--json"], cwd=tmp_path)
    assert report["code"] == 0
    document = json.loads(str(report["stdout"]))
    assert document["ok"] is True
    runs = document["runs"]
    for name, expected in (("bad", 1), ("fixed", 0)):
        replayed = guarded(
            installed,
            REPLAY_BLOCKED,
            ["replay", str(runs[name]["evidence"]), "--json"],
            cwd=tmp_path,
        )
        assert replayed["code"] == expected
        assert json.loads(str(replayed["stdout"]))["status"] == runs[name]["status"]
    workspace = write_workspace(tmp_path / "ws", count=9, wrong=[0, 3], prefix="gd")
    lock = tmp_path / "lock.json"
    report = guarded(installed, DEMO_BLOCKED, [*lock_argv(workspace, lock), "--json"], cwd=tmp_path)
    assert report["code"] == 0
    out = tmp_path / "evidence"
    report = guarded(
        installed, DEMO_BLOCKED, [*verify_argv(workspace, lock, out), "--json"], cwd=tmp_path
    )
    assert report["code"] == 2
    verified = json.loads(str(report["stdout"]))
    assert (verified["total"], verified["accepted"], verified["errors"]) == (9, 9, 2)
    replayed = guarded(installed, REPLAY_BLOCKED, ["replay", str(out), "--json"], cwd=tmp_path)
    assert replayed["code"] == 2
    assert json.loads(str(replayed["stdout"]))["lock_sha256"] == verified["lock_sha256"]
    assert os.environ.get("ACTSEAL_ACCEPTANCE_PWNED") is None
