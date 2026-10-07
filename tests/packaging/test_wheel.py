"""Clean-wheel packaging acceptance (marker ``packaging``).

Builds a real wheel with ``uv build --no-sources``, creates a fresh virtual
environment from the current interpreter, installs that wheel with no
dependencies and no index access, changes to a directory outside the
checkout, and exercises both installed entry points. Optional provider
dependencies must be absent from that environment (the test checks the
venv, so a Laya stack in the development environment cannot make it pass),
``actseal`` must import from the venv rather than the source tree, and the
demo and replay must work with live-provider imports and sockets denied.
The measured demo duration is reported in the test output; the documented
60-second fixture-workflow target is asserted against the console-script run.

Prerequisites: ``uv`` on PATH and a supported platform (macOS/Linux, needed by
the exclusive bundle publication). Network use: preparing the build tool
(``uv build`` fetching the pinned ``hatchling`` build backend) may need network
unless uv's cache already holds it. The venv uses the current interpreter and
the wheel installs with ``--no-deps --offline``. Dedicated isolation tests
replace sockets and deny provider imports; the console timing and entrypoint
checks run ordinarily and do not independently establish network isolation.

Supplied wheel: when ``ACTSEAL_TEST_WHEEL`` names an existing absolute
``actseal-*.whl`` path, that exact file is installed and ``uv build`` is never
invoked. The release workflow uses this to test the immutable built artifact.
Any other value fails the run; the tests never fall back to rebuilding.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
from collections.abc import Sequence
from pathlib import Path

import pytest

pytestmark = pytest.mark.packaging

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples" / "support_triage"
#: Reviewed two-entry registry (V1-037); wheel and sdist must ship it byte for byte.
REGISTRY = ROOT / "src" / "actseal" / "compatibility_registry.json"
#: Retained action-gate archive produced by the approved original producer.
ARCHIVE_EVIDENCE = ROOT / "examples" / "action_gate" / "recorded" / "a5fe090202f7" / "evidence"
ARCHIVE_LOCK_SHA256 = "cb009be0039afefd995f6eac3a8bd9767d6bf026a73273b47e87a51fc9fbd715"
RESOURCE_NAMES = tuple(
    f"{run}{suffix}"
    for run in ("bad", "fixed")
    for suffix in (".toml", "_calibration.jsonl", "_verification.jsonl", "_responses.jsonl")
)
OPTIONAL_MODULES = ("laya", "torch", "transformers", "huggingface_hub", "safetensors", "numpy")
DEMO_BUDGET_S = 60.0

_ISOLATED = r"""
import json
import socket
import sys

BLOCKED = tuple(sys.argv[1].split(","))


def _blocked(name):
    return any(name == root or name.startswith(root + ".") for root in BLOCKED)


class DenyImports:
    def find_spec(self, name, path=None, target=None):
        if _blocked(name):
            raise ImportError(f"blocked import: {name}")
        return None


sys.meta_path.insert(0, DenyImports())


def _no_network(*_args, **_kwargs):
    raise RuntimeError("network blocked")


socket.socket = _no_network
socket.create_connection = _no_network
socket.getaddrinfo = _no_network
socket.socketpair = _no_network

import io  # noqa: E402

from actseal.cli import main  # noqa: E402

buffer = io.StringIO()
real_stdout = sys.stdout
sys.stdout = buffer
try:
    code = main(sys.argv[2:])
finally:
    sys.stdout = real_stdout
loaded = sorted(name for name in sys.modules if _blocked(name))
print(json.dumps({"code": code, "stdout": buffer.getvalue(), "blocked_loaded": loaded}))
"""

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
    )
)
REPLAY_BLOCKED = DEMO_BLOCKED.replace("actseal.adapters.laya", "actseal.adapters")


def clean_env() -> dict[str, str]:
    """No PYTHONPATH, no virtual-environment hints from the development environment."""
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"PYTHONPATH", "VIRTUAL_ENV", "PYTHONHOME", "PYTHONSAFEPATH"}
    }
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run(
    argv: Sequence[str], *, cwd: Path, check: bool = True, timeout: float = 600.0
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed tool invocations with test-owned paths
        list(argv),
        capture_output=True,
        text=True,
        check=check,
        cwd=str(cwd),
        env=clean_env(),
        timeout=timeout,
    )


@pytest.fixture(scope="module")
def outside(tmp_path_factory: pytest.TempPathFactory) -> Path:
    directory = tmp_path_factory.mktemp("outside-checkout")
    assert not directory.resolve().is_relative_to(ROOT.resolve())
    return directory


def supplied_wheel() -> Path | None:
    """The exact wheel named by ``ACTSEAL_TEST_WHEEL``; ``None`` means build one here.

    ``ACTSEAL_TEST_DIST`` (the downloaded release artifact directory) may only
    appear together with ``ACTSEAL_TEST_WHEEL``, and the wheel must live inside it.
    """
    raw = os.environ.get("ACTSEAL_TEST_WHEEL")
    dist = os.environ.get("ACTSEAL_TEST_DIST")
    if raw is None:
        if dist is not None:
            pytest.fail(
                f"ACTSEAL_TEST_DIST={dist!r} set without ACTSEAL_TEST_WHEEL; refusing to rebuild"
            )
        return None
    path = Path(raw)
    if not path.is_absolute():
        problem = "is not an absolute path"
    elif not path.is_file():
        problem = "is not an existing regular file"
    elif not (path.name.startswith("actseal-") and path.suffix == ".whl"):
        problem = "is not named actseal-*.whl"
    elif dist is not None and path.resolve().parent != Path(dist).resolve():
        problem = f"is not inside ACTSEAL_TEST_DIST={dist!r}"
    else:
        return path
    pytest.fail(f"ACTSEAL_TEST_WHEEL={raw!r} {problem}; refusing to rebuild")


@pytest.fixture(scope="module")
def wheel(outside: Path) -> Path:
    supplied = supplied_wheel()
    if supplied is not None:
        return supplied
    uv = shutil.which("uv")
    if uv is None:
        pytest.fail("uv is required on PATH to build the wheel under test")
    dist = outside / "dist"
    run([uv, "build", "--no-sources", "--wheel", "--out-dir", str(dist)], cwd=ROOT)
    wheels = sorted(dist.glob("actseal-*.whl"))
    assert len(wheels) == 1, wheels
    return wheels[0]


@pytest.fixture(scope="module")
def venv(outside: Path, wheel: Path) -> Path:
    uv = shutil.which("uv")
    assert uv is not None
    directory = outside / "venv"
    run([uv, "venv", "--python", sys.executable, str(directory)], cwd=outside)
    python = directory / "bin" / "python"
    run(
        [uv, "pip", "install", "--python", str(python), "--no-deps", "--offline", str(wheel)],
        cwd=outside,
    )
    return directory


def python(venv: Path) -> Path:
    return venv / "bin" / "python"


def console(venv: Path) -> Path:
    return venv / "bin" / "actseal"


def site_package(venv: Path) -> Path:
    result = run(
        [str(python(venv)), "-c", "import actseal, os; print(os.path.dirname(actseal.__file__))"],
        cwd=venv.parent,
    )
    return Path(result.stdout.strip())


# --------------------------------------------------------------------------- #
# Installed contents and isolation
# --------------------------------------------------------------------------- #


def test_actseal_imports_from_the_venv_not_the_source_tree(venv: Path, outside: Path) -> None:
    package = site_package(venv)
    assert package.resolve().is_relative_to(venv.resolve())
    assert not package.resolve().is_relative_to(ROOT.resolve())
    del outside


def test_optional_dependencies_are_absent(venv: Path, outside: Path) -> None:
    script = (
        "import importlib.util, json, sys; "
        "print(json.dumps({name: importlib.util.find_spec(name) is not None for name in "
        + repr(list(OPTIONAL_MODULES))
        + "}))"
    )
    result = run([str(python(venv)), "-c", script], cwd=outside)
    assert json.loads(result.stdout) == dict.fromkeys(OPTIONAL_MODULES, False)


def test_wheel_ships_every_demo_asset_byte_identically(venv: Path) -> None:
    installed = site_package(venv) / "demo_data"
    assert installed.is_dir()
    for name in RESOURCE_NAMES:
        assert (installed / name).read_bytes() == (EXAMPLES / name).read_bytes(), name
    assert (installed / "__init__.py").is_file()


def test_installed_fingerprint_equals_the_checkout_fingerprint(venv: Path, outside: Path) -> None:
    script = "from actseal.serialization import implementation_fingerprint as f; print(f())"
    installed = run([str(python(venv)), "-c", script], cwd=outside).stdout.strip()
    checkout = run([sys.executable, "-c", script], cwd=ROOT).stdout.strip()
    assert len(installed) == 64
    assert installed == checkout


# --------------------------------------------------------------------------- #
# Reviewed registry bytes (V1-037) in the wheel and the sdist
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def sdist(outside: Path) -> Path:
    """The exact sdist in ``ACTSEAL_TEST_DIST`` when a wheel is supplied; otherwise build one."""
    dist = os.environ.get("ACTSEAL_TEST_DIST")
    if supplied_wheel() is not None:
        if dist is None:
            pytest.fail(
                "ACTSEAL_TEST_WHEEL set without ACTSEAL_TEST_DIST; the sdist registry check "
                "needs the built source distribution and never rebuilds"
            )
        archives = sorted(Path(dist).glob("actseal-*.tar.gz"))
        assert len(archives) == 1, archives
        return archives[0]
    uv = shutil.which("uv")
    if uv is None:
        pytest.fail("uv is required on PATH to build the sdist under test")
    out = outside / "dist-sdist"
    run([uv, "build", "--no-sources", "--sdist", "--out-dir", str(out)], cwd=ROOT)
    archives = sorted(out.glob("actseal-*.tar.gz"))
    assert len(archives) == 1, archives
    return archives[0]


def test_wheel_ships_the_reviewed_registry_byte_identically(venv: Path, outside: Path) -> None:
    installed = site_package(venv) / "compatibility_registry.json"
    assert installed.is_file()
    assert installed.read_bytes() == REGISTRY.read_bytes()
    document = json.loads(installed.read_text(encoding="utf-8"))
    assert document["schema_version"] == 1
    assert len(document["implementations"]) == 2
    script = (
        "from actseal.compatibility import load_registry as l; "
        "from actseal.serialization import implementation_fingerprint as f; "
        "r = l(); print(r.engine_for(f()), len(r.implementations))"
    )
    result = run([str(python(venv)), "-c", script], cwd=outside)
    assert result.stdout.strip() == "actseal-choice-v1 2"


def test_sdist_ships_the_reviewed_registry_byte_identically(sdist: Path) -> None:
    with tarfile.open(sdist, "r:gz") as archive:
        members = [
            member
            for member in archive.getmembers()
            if member.isfile() and member.name.endswith("/src/actseal/compatibility_registry.json")
        ]
        assert len(members) == 1, [member.name for member in members]
        extracted = archive.extractfile(members[0])
        assert extracted is not None
        data = extracted.read()
    assert data == REGISTRY.read_bytes()


def test_installed_wheel_replays_the_retained_archive_outside_the_checkout(
    venv: Path, outside: Path
) -> None:
    """Dual registration in the installed registry reproduces the stored PASS, bytes untouched.

    The archive is copied outside the checkout; the installed interpreter
    replays it with adapters, the experimental package, transports and
    sockets denied, anchored by the externally trusted lock digest.
    """
    copy = outside / "retained-archive" / "evidence"
    shutil.copytree(ARCHIVE_EVIDENCE, copy)
    originals = {path.name: path.read_bytes() for path in ARCHIVE_EVIDENCE.iterdir()}
    blocked = REPLAY_BLOCKED + ",actseal.experimental"
    argv = ["replay", str(copy), "--expected-lock-sha256", ARCHIVE_LOCK_SHA256, "--json"]
    result = run([str(python(venv)), "-c", _ISOLATED, blocked, *argv], cwd=outside)
    report = json.loads(result.stdout)
    assert report["blocked_loaded"] == []
    assert report["code"] == 0
    document = json.loads(report["stdout"])
    assert document["status"] == "PASS"
    assert document["reasons"] == ["contract.satisfied"]
    assert (document["total"], document["accepted"], document["errors"]) == (160, 136, 1)
    assert document["lock_sha256"] == ARCHIVE_LOCK_SHA256
    wrong = ["replay", str(copy), "--expected-lock-sha256", "0" * 64, "--json"]
    result = run([str(python(venv)), "-c", _ISOLATED, blocked, *wrong], cwd=outside)
    report = json.loads(result.stdout)
    assert report["code"] == 3
    assert json.loads(report["stdout"])["reasons"] == ["integrity.expected_lock"]
    console_result = run([str(console(venv)), *argv], cwd=outside, check=False)
    assert console_result.returncode == 0
    assert json.loads(console_result.stdout)["lock_sha256"] == ARCHIVE_LOCK_SHA256
    assert {path.name: path.read_bytes() for path in copy.iterdir()} == originals
    assert {path.name: path.read_bytes() for path in ARCHIVE_EVIDENCE.iterdir()} == originals


# --------------------------------------------------------------------------- #
# Entry points
# --------------------------------------------------------------------------- #


def test_console_script_is_installed_and_helps(venv: Path, outside: Path) -> None:
    script = console(venv)
    assert script.is_file(), "console script missing: [project.scripts] actseal is required"
    result = run([str(script), "--help"], cwd=outside, check=False)
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("usage: actseal")
    assert run([str(script)], cwd=outside, check=False).returncode == 3


def test_module_entrypoint_helps(venv: Path, outside: Path) -> None:
    result = run([str(python(venv)), "-m", "actseal", "--help"], cwd=outside, check=False)
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("usage: actseal")
    result = run([str(python(venv)), "-m", "actseal", "replay"], cwd=outside, check=False)
    assert result.returncode == 3


# --------------------------------------------------------------------------- #
# Demo and replay from the installed wheel
# --------------------------------------------------------------------------- #


def test_installed_demo_and_replay_with_providers_and_network_denied(
    venv: Path, outside: Path
) -> None:
    demo = outside / "demo-isolated"
    result = run(
        [str(python(venv)), "-c", _ISOLATED, DEMO_BLOCKED, "demo", "--out", str(demo), "--json"],
        cwd=outside,
    )
    report = json.loads(result.stdout)
    assert report["blocked_loaded"] == []
    assert report["code"] == 0
    document = json.loads(report["stdout"])
    assert document["ok"] is True
    assert document["runs"]["bad"]["status"] == "BLOCK"
    assert document["runs"]["fixed"]["status"] == "PASS"
    assert document["runs"]["bad"]["errors"] == 32
    assert document["runs"]["fixed"]["errors"] == 0
    for name, expected in (("bad", 1), ("fixed", 0)):
        bundle = demo / name / "evidence"
        result = run(
            [str(python(venv)), "-c", _ISOLATED, REPLAY_BLOCKED, "replay", str(bundle), "--json"],
            cwd=outside,
        )
        report = json.loads(result.stdout)
        assert report["blocked_loaded"] == []
        assert report["code"] == expected
        replayed = json.loads(report["stdout"])
        assert replayed["status"] == document["runs"][name]["status"]
        assert replayed["lock_sha256"] == document["runs"][name]["lock_sha256"]


def test_console_demo_fixture_workflow_within_budget(venv: Path, outside: Path) -> None:
    script = console(venv)
    assert script.is_file(), "console script missing: [project.scripts] actseal is required"
    demo = outside / "demo-console"
    started = time.monotonic()
    result = run([str(script), "demo", "--out", str(demo), "--json"], cwd=outside, check=False)
    elapsed = time.monotonic() - started
    assert result.returncode == 0, result.stderr
    document = json.loads(result.stdout)
    assert document["ok"] is True
    sys.stderr.write(
        f"\ninstalled-wheel demo: {elapsed:.3f}s wall clock, "
        f"{document['duration_s']:.3f}s inside the demo\n"
    )
    assert elapsed < DEMO_BUDGET_S
    for name in ("bad", "fixed"):
        bundle = demo / name / "evidence"
        replayed = run([str(script), "replay", str(bundle), "--json"], cwd=outside, check=False)
        assert replayed.returncode == (1 if name == "bad" else 0)
        assert json.loads(replayed.stdout)["status"] == document["runs"][name]["status"]
    second = outside / "demo-console-again"
    assert (
        run([str(script), "demo", "--out", str(second)], cwd=outside, check=False).returncode == 0
    )
    first_files = sorted(p.relative_to(demo) for p in demo.rglob("*") if p.is_file())
    assert first_files == sorted(p.relative_to(second) for p in second.rglob("*") if p.is_file())
    assert all((demo / p).read_bytes() == (second / p).read_bytes() for p in first_files)
    assert run([str(script), "demo", "--out", str(demo)], cwd=outside, check=False).returncode == 3
