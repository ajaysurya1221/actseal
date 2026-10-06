"""``ACTSEAL_TEST_WHEEL``: the packaging fixtures install the supplied wheel and never rebuild.

Both ``tests/packaging/test_wheel.py`` and
``tests/acceptance/test_acceptance_wheel_receipts.py`` expose ``supplied_wheel()``.
The helper tests here call it in isolation. The ``packaging``-marked test
replaces ``uv`` on ``PATH`` with a shim that records any ``uv build`` and runs the
real packaging tests in a subprocess with and without a valid override.
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
from release_support import ROOT, build_real_distributions, python_script

MODULES = {
    "packaging": ROOT / "tests" / "packaging" / "test_wheel.py",
    "acceptance": ROOT / "tests" / "acceptance" / "test_acceptance_wheel_receipts.py",
}
NODE_IDS = (
    f"{MODULES['packaging']}::test_console_script_is_installed_and_helps",
    f"{MODULES['acceptance']}::test_installed_package_is_isolated_from_the_checkout",
)

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


def helper_failure(module: types.ModuleType) -> str:
    with pytest.raises(pytest.fail.Exception) as excinfo:
        module.supplied_wheel()
    message = str(excinfo.value)
    assert "ACTSEAL_TEST_WHEEL" in message
    assert "refusing to rebuild" in message
    return message


def test_unset_means_build(module: types.ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ACTSEAL_TEST_WHEEL", raising=False)
    assert module.supplied_wheel() is None


def test_valid_absolute_wheel_is_returned(
    module: types.ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    wheel = tmp_path / "actseal-1.0.0-py3-none-any.whl"
    wheel.write_bytes(b"")
    monkeypatch.setenv("ACTSEAL_TEST_WHEEL", str(wheel))
    assert module.supplied_wheel() == wheel


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
def test_invalid_values_fail_instead_of_rebuilding(
    module: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    value: str,
    fragment: str,
) -> None:
    for name in ("other-1.0.0-py3-none-any.whl", "actseal-1.0.0.tar.gz"):
        (tmp_path / name).write_bytes(b"")
    raw = value.format(tmp=tmp_path)
    monkeypatch.setenv("ACTSEAL_TEST_WHEEL", raw)
    message = helper_failure(module)
    assert fragment in message
    assert repr(raw) in message


# --------------------------------------------------------------------------- #
# Subprocess proof: the real packaging tests never call `uv build` when supplied
# --------------------------------------------------------------------------- #


def run_pytest(
    node_ids: tuple[str, ...], env: Mapping[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed interpreter invocation with test-owned arguments
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q", *node_ids],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(ROOT),
        env=dict(env),
        timeout=900,
    )


@pytest.mark.packaging
def test_supplied_wheel_is_installed_without_rebuilding(tmp_path: Path) -> None:
    real_uv = shutil.which("uv")
    if real_uv is None:
        pytest.fail("uv is required on PATH to build the wheel under test")
    files = build_real_distributions(tmp_path / "dist")
    wheel = next(path for name, path in files.items() if name.endswith(".whl"))
    marker = tmp_path / "uv-build-was-called"
    shim_dir = tmp_path / "shim"
    shim_dir.mkdir()
    python_script(shim_dir / "uv", _SHIM.format(marker=str(marker), real=real_uv))
    base = {
        key: value
        for key, value in os.environ.items()
        if key not in {"PYTHONPATH", "VIRTUAL_ENV", "PYTHONHOME", "ACTSEAL_TEST_WHEEL"}
    }
    base["PATH"] = f"{shim_dir}{os.pathsep}{base.get('PATH', '')}"

    supplied = run_pytest(NODE_IDS, {**base, "ACTSEAL_TEST_WHEEL": str(wheel)})
    assert supplied.returncode == 0, supplied.stdout + supplied.stderr
    assert "2 passed" in supplied.stdout
    assert not marker.exists()

    missing = run_pytest(NODE_IDS[:1], {**base, "ACTSEAL_TEST_WHEEL": str(tmp_path / "absent.whl")})
    assert missing.returncode != 0
    assert "ACTSEAL_TEST_WHEEL" in missing.stdout + missing.stderr
    assert "refusing to rebuild" in missing.stdout + missing.stderr
    assert not marker.exists()

    relative = run_pytest(NODE_IDS[:1], {**base, "ACTSEAL_TEST_WHEEL": "dist/actseal.whl"})
    assert relative.returncode != 0
    assert "not an absolute path" in relative.stdout + relative.stderr
    assert not marker.exists()

    unset = run_pytest(NODE_IDS[:1], base)
    assert unset.returncode != 0
    assert marker.read_text(encoding="utf-8").startswith("build --no-sources")
