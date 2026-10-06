"""Shared helpers for the release-gate tests: tool loader, fixture repositories, fake archives.

Nothing here is a product authority. Fixture trees contain only the files the
checks read, built from the documented shapes, so each negative test can break
exactly one requirement. Real distributions are built only in tests marked
``packaging``; everything else uses hand-made archives and ``file://`` URLs.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import shutil
import struct
import subprocess
import sys
import tarfile
import types
import zipfile
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "check_release.py"
WORKFLOW = ROOT / ".github" / "workflows" / "publish-pypi.yml"
STABLE = "Development Status :: 5 - Production/Stable"
ALPHA = "Development Status :: 3 - Alpha"
CONTAINER_DIGEST = "d657ab0ade19f404a6ccc883ab399540de667aff751748ce23c07330c5a89e64"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def load_tool() -> types.ModuleType:
    """Import ``tools/check_release.py`` as an isolated module object."""
    spec = importlib.util.spec_from_file_location("actseal_check_release", TOOL)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Dataclasses with postponed annotations resolve them through sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_hex(path.read_bytes())


def names(version: str) -> tuple[str, str]:
    return f"actseal-{version}-py3-none-any.whl", f"actseal-{version}.tar.gz"


# --------------------------------------------------------------------------- #
# git
# --------------------------------------------------------------------------- #


def git(root: Path, *args: str) -> str:
    binary = shutil.which("git")
    assert binary is not None, "git is required for the release-gate tests"
    result = subprocess.run(  # noqa: S603 - fixed git invocation with test-owned arguments
        [binary, "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    return result.stdout.strip()


def commit_all(root: Path, message: str = "fixture") -> str:
    if not (root / ".git").exists():
        git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-q", "--allow-empty", "-m", message)
    return git(root, "rev-parse", "HEAD")


# --------------------------------------------------------------------------- #
# Version sources and fixture repositories
# --------------------------------------------------------------------------- #


def write_version_sources(
    root: Path,
    version: str,
    *,
    pyproject: str | None = None,
    source: str | None = None,
    lock: str | None = None,
    classifier: str | None = STABLE,
) -> None:
    """pyproject, ``__version__`` and uv.lock, each overridable to create disagreement."""
    classifiers = json.dumps([classifier] if classifier else [])
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "actseal"\nversion = "{pyproject or version}"\n'
        f"classifiers = {classifiers}\n",
        encoding="utf-8",
    )
    package = root / "src" / "actseal"
    package.mkdir(parents=True, exist_ok=True)
    (package / "__init__.py").write_text(
        f'"""Fixture package."""\n\n__version__ = "{source or version}"\n', encoding="utf-8"
    )
    (root / "uv.lock").write_text(
        'version = 1\n\n[[package]]\nname = "actseal"\n'
        f'version = "{lock or version}"\nsource = {{ editable = "." }}\n',
        encoding="utf-8",
    )


def readme_text(root_link_target: str = "LICENSE") -> str:
    base = "https://github.com/ajaysurya1221/actseal"
    return (
        "# Actseal\n\n"
        "Actseal verifies model-chosen application actions for developers: freeze a "
        "policy, check its recorded decisions, and replay the evidence offline.\n\n"
        "```bash\n"
        "uvx --python 3.12 actseal demo --out ./actseal-demo\n"
        "uvx --offline --python 3.12 actseal replay ./actseal-demo/fixed/evidence\n"
        "uvx --offline --python 3.12 actseal replay ./actseal-demo/bad/evidence\n"
        "```\n\n"
        "[PyPI](https://pypi.org/project/actseal/) · "
        f"[License]({base}/blob/main/{root_link_target})\n\n"
        "Windows is unsupported in 1.x.\n"
    )


def png_bytes(width: int, height: int) -> bytes:
    return (
        PNG_SIGNATURE
        + struct.pack(">I", 13)
        + b"IHDR"
        + struct.pack(">II", width, height)
        + b"\x08\x06\x00\x00\x00"
    )


def write_release_tree(root: Path, version: str = "1.0.0") -> str:
    """A minimal tree satisfying ``docs`` and ``candidate``; returns the HEAD commit."""
    root.mkdir(parents=True, exist_ok=True)
    write_version_sources(root, version)
    (root / "README.md").write_text(readme_text(), encoding="utf-8")
    (root / "LICENSE").write_text("Apache-2.0\n", encoding="utf-8")
    (root / "CHANGELOG.md").write_text(
        f"# Changelog\n\n## v{version} — 2026-10-07\n\n- x\n", encoding="utf-8"
    )
    for name in ("SECURITY.md", "CONTRIBUTING.md"):
        (root / name).write_text(f"# {name}\n", encoding="utf-8")
    docs = root / "docs"
    docs.mkdir(exist_ok=True)
    for name in ("quickstart", "stability", "versioning", "migration"):
        (docs / f"{name}.md").write_text(f"# {name}\n", encoding="utf-8")
    (docs / "publishing.md").write_text("# Publishing\n\nPush a release tag.\n", encoding="utf-8")
    schemas = docs / "schemas"
    schemas.mkdir(exist_ok=True)
    (schemas / "lock.schema.json").write_text("{}\n", encoding="utf-8")
    assets = docs / "assets"
    assets.mkdir(exist_ok=True)
    for name in ("hero-light", "hero-dark", "how-it-works", "architecture"):
        (assets / f"{name}.svg").write_text(
            "<svg xmlns='http://www.w3.org/2000/svg'/>\n", encoding="utf-8"
        )
    (assets / "social-preview.png").write_bytes(png_bytes(1280, 640))
    workflow = root / ".github" / "workflows"
    workflow.mkdir(parents=True, exist_ok=True)
    (workflow / "publish-pypi.yml").write_bytes(WORKFLOW.read_bytes())
    return commit_all(root)


# --------------------------------------------------------------------------- #
# Fake and real distributions
# --------------------------------------------------------------------------- #


def core_metadata(version: str, name: str = "actseal") -> str:
    return f"Metadata-Version: 2.5\nName: {name}\nVersion: {version}\nSummary: fixture\n\nbody\n"


def write_wheel(directory: Path, version: str, *, metadata_version: str | None = None) -> Path:
    path = directory / names(version)[0]
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            f"actseal-{version}.dist-info/METADATA", core_metadata(metadata_version or version)
        )
        archive.writestr("actseal/__init__.py", f'__version__ = "{version}"\n')
    return path


def write_sdist(
    directory: Path,
    version: str,
    *,
    pkg_version: str | None = None,
    pyproject_version: str | None = None,
    lock_version: str | None = None,
) -> Path:
    path = directory / names(version)[1]
    prefix = f"actseal-{version}"
    inner_pyproject = pyproject_version or version
    inner_lock = lock_version or version
    members = {
        "PKG-INFO": core_metadata(pkg_version or version),
        "pyproject.toml": f'[project]\nname = "actseal"\nversion = "{inner_pyproject}"\n',
        "uv.lock": f'version = 1\n\n[[package]]\nname = "actseal"\nversion = "{inner_lock}"\n',
    }
    with tarfile.open(path, "w:gz") as archive:
        for member, text in members.items():
            data = text.encode("utf-8")
            info = tarfile.TarInfo(f"{prefix}/{member}")
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return path


def write_fake_distributions(directory: Path, version: str) -> dict[str, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    return {
        path.name: path
        for path in (write_wheel(directory, version), write_sdist(directory, version))
    }


def write_sums(path: Path, files: Mapping[str, Path]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(f"{sha256_path(files[name])}  {name}\n" for name in sorted(files)), encoding="utf-8"
    )
    return path


def build_real_distributions(directory: Path) -> dict[str, Path]:
    """``uv build --no-sources`` into ``directory`` with uv's ``.gitignore`` marker removed."""
    uv = shutil.which("uv")
    if uv is None:
        pytest.fail("uv is required on PATH to build the distributions under test")
    subprocess.run(  # noqa: S603 - fixed tool invocation with test-owned paths
        [uv, "build", "--no-sources", "--out-dir", str(directory)],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(ROOT),
        timeout=600,
    )
    marker = directory / ".gitignore"
    if marker.exists():
        marker.unlink()
    return {path.name: path for path in sorted(directory.iterdir())}


# --------------------------------------------------------------------------- #
# Fake PyPI index served over file:// URLs
# --------------------------------------------------------------------------- #


def write_fake_index(
    base: Path,
    version: str,
    files: Mapping[str, bytes],
    *,
    provenance_for: Iterable[str] | None = None,
    declared: Mapping[str, str] | None = None,
) -> str:
    """Lay out ``/pypi/actseal/V/json`` and ``/integrity/...`` files; returns the base URL."""
    store = base / "files"
    store.mkdir(parents=True, exist_ok=True)
    urls = []
    for name, data in files.items():
        (store / name).write_bytes(data)
        urls.append(
            {
                "filename": name,
                "url": (store / name).resolve().as_uri(),
                "size": len(data),
                "digests": {"sha256": (declared or {}).get(name, sha256_hex(data))},
            }
        )
    release = base / "pypi" / "actseal" / version
    release.mkdir(parents=True, exist_ok=True)
    (release / "json").write_text(json.dumps({"urls": urls}), encoding="utf-8")
    provenance = {
        "attestation_bundles": [
            {
                "publisher": {
                    "kind": "GitHub",
                    "repository": "ajaysurya1221/actseal",
                    "workflow": "publish-pypi.yml",
                    "environment": "pypi",
                },
                "attestations": [{"version": 1}],
            }
        ]
    }
    for name in files if provenance_for is None else provenance_for:
        target = base / "integrity" / "actseal" / version / name
        target.mkdir(parents=True, exist_ok=True)
        (target / "provenance").write_text(json.dumps(provenance), encoding="utf-8")
    return base.resolve().as_uri()


# --------------------------------------------------------------------------- #
# CLI invocation
# --------------------------------------------------------------------------- #


def run_main(
    tool: types.ModuleType, argv: Sequence[str], capsys: pytest.CaptureFixture[str]
) -> tuple[int, str, str]:
    """``main(argv)`` with captured stdout/stderr; the capture buffer is reset first."""
    capsys.readouterr()
    code = int(tool.main(list(argv)))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def python_script(path: Path, body: str) -> Path:
    """An executable script running under the current interpreter."""
    path.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    path.chmod(0o755)
    return path
