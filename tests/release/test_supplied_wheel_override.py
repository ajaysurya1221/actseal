"""Supplied release artifacts: the packaging tests install the given bytes and never rebuild.

``ACTSEAL_TEST_WHEEL`` names the wheel and ``ACTSEAL_TEST_DIST`` the artifact
directory that holds it together with the sdist. The two packaging fixture
modules expose ``supplied_wheel()``; ``release_support.supplied_distributions``
is the release-test counterpart. The helper tests here call them in isolation.
The ``packaging``-marked proof replaces ``uv`` on ``PATH`` with a shim that
records any ``uv build`` attempt before any fixture runs, then executes every
packaging test path in a subprocess with the supplied artifacts.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import types
from collections.abc import Mapping
from pathlib import Path

import pytest
from release_support import ROOT, python_script, release_distributions, supplied_distributions

MODULES = {
    "packaging": ROOT / "tests" / "packaging" / "test_wheel.py",
    "acceptance": ROOT / "tests" / "acceptance" / "test_acceptance_wheel_receipts.py",
}
PACKAGING_PATHS = (
    str(MODULES["packaging"]),
    str(MODULES["acceptance"]),
    str(ROOT / "tests" / "release" / "test_check_release_distributions.py"),
)
ONE_NODE = f"{MODULES['packaging']}::test_console_script_is_installed_and_helps"

_SHIM = """
import os
import sys

if len(sys.argv) > 1 and sys.argv[1] == "build":
    with open({marker!r}, "a", encoding="utf-8") as handle:
        handle.write(" ".join(sys.argv[1:]) + "\\n")
    sys.exit(1)
os.execv({real!r}, [{real!r}, *sys.argv[1:]])
"""


@pytest.fixture(params=sorted(MODULES))
def module(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    path = MODULES[str(request.param)]
    monkeypatch.syspath_prepend(str(path.parent))
    spec = importlib.util.spec_from_file_location(f"supplied_wheel_{request.param}", path)
    assert spec is not None
    assert spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, loaded)
    spec.loader.exec_module(loaded)
    return loaded


@pytest.fixture
def artifacts(tmp_path: Path) -> tuple[Path, Path]:
    """A fake artifact directory holding one wheel and one sdist."""
    dist = tmp_path / "artifact"
    dist.mkdir()
    wheel = dist / "actseal-1.0.0-py3-none-any.whl"
    wheel.write_bytes(b"")
    (dist / "actseal-1.0.0.tar.gz").write_bytes(b"")
    return dist, wheel


def helper_failure(module: types.ModuleType) -> str:
    with pytest.raises(pytest.fail.Exception) as excinfo:
        module.supplied_wheel()
    message = str(excinfo.value)
    assert "refusing to rebuild" in message
    return message


def test_unset_means_build(module: types.ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ACTSEAL_TEST_WHEEL", raising=False)
    monkeypatch.delenv("ACTSEAL_TEST_DIST", raising=False)
    assert module.supplied_wheel() is None
    assert supplied_distributions() is None


def test_valid_absolute_wheel_is_returned(
    module: types.ModuleType, monkeypatch: pytest.MonkeyPatch, artifacts: tuple[Path, Path]
) -> None:
    _, wheel = artifacts
    monkeypatch.delenv("ACTSEAL_TEST_DIST", raising=False)
    monkeypatch.setenv("ACTSEAL_TEST_WHEEL", str(wheel))
    assert module.supplied_wheel() == wheel


def test_paired_dist_and_wheel_are_accepted(
    module: types.ModuleType, monkeypatch: pytest.MonkeyPatch, artifacts: tuple[Path, Path]
) -> None:
    dist, wheel = artifacts
    monkeypatch.setenv("ACTSEAL_TEST_DIST", str(dist))
    monkeypatch.setenv("ACTSEAL_TEST_WHEEL", str(wheel))
    assert module.supplied_wheel() == wheel
    assert supplied_distributions() == dist
    assert sorted(release_distributions(dist.parent / "unused")) == [
        "actseal-1.0.0-py3-none-any.whl",
        "actseal-1.0.0.tar.gz",
    ]
    assert not (dist.parent / "unused").exists()


@pytest.mark.parametrize(
    ("value", "fragment"),
    [
        ("", "not an absolute path"),
        ("dist/actseal-1.0.0-py3-none-any.whl", "not an absolute path"),
        ("{tmp}/absent/actseal-1.0.0-py3-none-any.whl", "not an existing regular file"),
        ("{tmp}", "not an existing regular file"),
        ("{tmp}/other-1.0.0-py3-none-any.whl", "not named actseal-*.whl"),
        ("{tmp}/actseal-1.0.0.tar.gz", "not named actseal-*.whl"),
    ],
)
def test_invalid_wheel_values_fail_instead_of_rebuilding(
    module: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    value: str,
    fragment: str,
) -> None:
    for name in ("other-1.0.0-py3-none-any.whl", "actseal-1.0.0.tar.gz"):
        (tmp_path / name).write_bytes(b"")
    raw = value.format(tmp=tmp_path)
    monkeypatch.delenv("ACTSEAL_TEST_DIST", raising=False)
    monkeypatch.setenv("ACTSEAL_TEST_WHEEL", raw)
    message = helper_failure(module)
    assert fragment in message
    assert repr(raw) in message


def test_dist_without_wheel_fails(
    module: types.ModuleType, monkeypatch: pytest.MonkeyPatch, artifacts: tuple[Path, Path]
) -> None:
    dist, _ = artifacts
    monkeypatch.delenv("ACTSEAL_TEST_WHEEL", raising=False)
    monkeypatch.setenv("ACTSEAL_TEST_DIST", str(dist))
    assert "without ACTSEAL_TEST_WHEEL" in helper_failure(module)
    with pytest.raises(pytest.fail.Exception) as excinfo:
        supplied_distributions()
    assert "must be set together" in str(excinfo.value)


def test_wheel_outside_dist_fails(
    module: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    artifacts: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    dist, wheel = artifacts
    elsewhere = tmp_path / "elsewhere" / wheel.name
    elsewhere.parent.mkdir()
    elsewhere.write_bytes(b"")
    monkeypatch.setenv("ACTSEAL_TEST_DIST", str(dist))
    monkeypatch.setenv("ACTSEAL_TEST_WHEEL", str(elsewhere))
    assert "not inside ACTSEAL_TEST_DIST" in helper_failure(module)
    with pytest.raises(pytest.fail.Exception) as excinfo:
        supplied_distributions()
    assert "not the wheel inside ACTSEAL_TEST_DIST" in str(excinfo.value)


@pytest.mark.parametrize("extra", ["SHA256SUMS", "actseal-1.0.1.tar.gz"])
def test_release_dist_must_hold_exactly_one_wheel_and_one_sdist(
    monkeypatch: pytest.MonkeyPatch, artifacts: tuple[Path, Path], extra: str
) -> None:
    dist, wheel = artifacts
    (dist / extra).write_bytes(b"")
    monkeypatch.setenv("ACTSEAL_TEST_DIST", str(dist))
    monkeypatch.setenv("ACTSEAL_TEST_WHEEL", str(wheel))
    with pytest.raises(pytest.fail.Exception) as excinfo:
        supplied_distributions()
    assert "exactly one wheel and one sdist" in str(excinfo.value)


def test_release_wheel_alone_fails_for_release_tests(
    monkeypatch: pytest.MonkeyPatch, artifacts: tuple[Path, Path]
) -> None:
    _, wheel = artifacts
    monkeypatch.delenv("ACTSEAL_TEST_DIST", raising=False)
    monkeypatch.setenv("ACTSEAL_TEST_WHEEL", str(wheel))
    with pytest.raises(pytest.fail.Exception) as excinfo:
        supplied_distributions()
    assert "must be set together" in str(excinfo.value)


# --------------------------------------------------------------------------- #
# Subprocess proof: with supplied artifacts no packaging path ever calls uv build
# --------------------------------------------------------------------------- #


def run_pytest(
    targets: tuple[str, ...], env: Mapping[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed interpreter invocation with test-owned arguments
        [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "no:cacheprovider",
            "-q",
            "-m",
            "packaging",
            *targets,
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(ROOT),
        env=dict(env),
        timeout=1200,
    )


@pytest.mark.packaging
def test_supplied_artifacts_are_used_by_every_packaging_path_without_rebuilding(
    tmp_path: Path,
) -> None:
    real_uv = shutil.which("uv")
    if real_uv is None:
        pytest.fail("uv is required on PATH")
    files = release_distributions(tmp_path / "dist")
    wheel = next(path for name, path in files.items() if name.endswith(".whl"))
    dist = wheel.parent
    marker = tmp_path / "uv-build-was-called"
    shim_dir = tmp_path / "shim"
    shim_dir.mkdir()
    python_script(shim_dir / "uv", _SHIM.format(marker=str(marker), real=real_uv))
    base = {
        key: value
        for key, value in os.environ.items()
        if key
        not in {
            "PYTHONPATH",
            "VIRTUAL_ENV",
            "PYTHONHOME",
            "ACTSEAL_TEST_WHEEL",
            "ACTSEAL_TEST_DIST",
        }
    }
    base["PATH"] = f"{shim_dir}{os.pathsep}{base.get('PATH', '')}"
    supplied = {**base, "ACTSEAL_TEST_DIST": str(dist), "ACTSEAL_TEST_WHEEL": str(wheel)}

    full = run_pytest(PACKAGING_PATHS, supplied)
    assert full.returncode == 0, full.stdout + full.stderr
    assert " passed" in full.stdout
    assert "deselected" in full.stdout
    assert not marker.exists()

    dist_only = run_pytest((ONE_NODE,), {**base, "ACTSEAL_TEST_DIST": str(dist)})
    assert dist_only.returncode != 0
    assert "without ACTSEAL_TEST_WHEEL" in dist_only.stdout + dist_only.stderr
    assert not marker.exists()

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / wheel.name).write_bytes(wheel.read_bytes())
    foreign = run_pytest(
        (ONE_NODE,),
        {**base, "ACTSEAL_TEST_DIST": str(dist), "ACTSEAL_TEST_WHEEL": str(elsewhere / wheel.name)},
    )
    assert foreign.returncode != 0
    assert "not inside ACTSEAL_TEST_DIST" in foreign.stdout + foreign.stderr
    assert not marker.exists()

    missing = run_pytest((ONE_NODE,), {**base, "ACTSEAL_TEST_WHEEL": str(tmp_path / "absent.whl")})
    assert missing.returncode != 0
    assert "refusing to rebuild" in missing.stdout + missing.stderr
    assert not marker.exists()

    unset = run_pytest((ONE_NODE,), base)
    assert unset.returncode != 0
    assert marker.read_text(encoding="utf-8").startswith("build --no-sources")
