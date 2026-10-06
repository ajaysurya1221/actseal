"""Shared helpers for the release-gate tests: tool loader, fixture repositories, fake archives.

Nothing here is a product authority. Fixture trees contain only the files the
checks read, built from the documented shapes, so each negative test can break
exactly one requirement. Real distributions are built only in tests marked
``packaging`` and only when no release artifact is supplied; everything else
uses hand-made archives and ``file://`` URLs.

Supplied release artifacts: ``ACTSEAL_TEST_DIST`` names the downloaded artifact
directory (exactly one wheel and one sdist) and ``ACTSEAL_TEST_WHEEL`` the wheel
inside it. Both must be present together; then ``release_distributions`` returns
those exact files and never calls ``uv build``. Invalid values fail outright.
"""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import io
import json
import os
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
PUBLISHER = {
    "kind": "GitHub",
    "repository": "ajaysurya1221/actseal",
    "workflow": "publish-pypi.yml",
    "environment": "pypi",
}
IN_TOTO = "https://in-toto.io/Statement/v1"
ASSET_OUTPUTS = (
    "hero-light.svg",
    "hero-dark.svg",
    "how-it-works.svg",
    "architecture.svg",
    "social.png",
)
ATTESTATION_NOTE = (
    "Attestation presence, publisher identity and statement subjects were inspected; "
    "no independent cryptographic verification is claimed."
)


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


def readme_text(root_link_target: str = "LICENSE", *, picture: str = "") -> str:
    base = "https://github.com/ajaysurya1221/actseal"
    return (
        "# Actseal\n\n"
        f"{picture}\n"
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


def picture_markup(dark: str, light: str) -> str:
    """The mandated ``<picture>`` block, multi-line, with a quoted ``>`` in the alt text."""
    return (
        "<picture>\n"
        '  <source media="(prefers-color-scheme: dark)"\n'
        f'          srcset="{dark} 1x, {dark} 2x">\n'
        f'  <img alt="Freeze -> Run -> Replay" src="{light}"\n       width="800">\n'
        "</picture>\n"
    )


def png_bytes(width: int, height: int) -> bytes:
    return (
        PNG_SIGNATURE
        + struct.pack(">I", 13)
        + b"IHDR"
        + struct.pack(">II", width, height)
        + b"\x08\x06\x00\x00\x00"
    )


_RENDERER_OK = """
import sys

sys.stdout.write("check: 4 asset(s) checked; 0 planned/not implemented; 0 error(s)\\n")
sys.exit(0)
"""


def write_fake_renderer(root: Path, body: str = _RENDERER_OK) -> Path:
    """``docs/assets/src/render.py`` as an executable script under the current interpreter."""
    return python_script(root / "docs" / "assets" / "src" / "render.py", body, parents=True)


def write_assets(root: Path) -> None:
    assets = root / "docs" / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for name in ASSET_OUTPUTS:
        if name.endswith(".svg"):
            (assets / name).write_text("<svg xmlns='http://www.w3.org/2000/svg'/>\n", "utf-8")
    (assets / "social.png").write_bytes(png_bytes(1280, 640))


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
    write_assets(root)
    write_fake_renderer(root)
    workflow = root / ".github" / "workflows"
    workflow.mkdir(parents=True, exist_ok=True)
    (workflow / "publish-pypi.yml").write_bytes(WORKFLOW.read_bytes())
    return commit_all(root)


def write_incomplete_tree(root: Path) -> str:
    """A deliberately incomplete 0.x/Alpha tree: what the gates must keep rejecting."""
    root.mkdir(parents=True, exist_ok=True)
    write_version_sources(root, "0.1.0", classifier=ALPHA)
    (root / "README.md").write_text(
        "# Actseal\n\nSee [the quickstart](docs/quickstart.md).\n", encoding="utf-8"
    )
    (root / "CHANGELOG.md").write_text("# Changelog\n\n## v0.1.0\n", encoding="utf-8")
    docs = root / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "quickstart.md").write_text("# quickstart\n", encoding="utf-8")
    (docs / "publishing.md").write_text("Run gh workflow run -f publish=true\n", encoding="utf-8")
    workflow = root / ".github" / "workflows"
    workflow.mkdir(parents=True, exist_ok=True)
    (workflow / "publish-pypi.yml").write_bytes(WORKFLOW.read_bytes())
    return commit_all(root)


# --------------------------------------------------------------------------- #
# Fake and real distributions
# --------------------------------------------------------------------------- #


def core_metadata(
    version: str, name: str = "actseal", classifiers: Sequence[str] = (STABLE,)
) -> str:
    lines = [
        "Metadata-Version: 2.5",
        f"Name: {name}",
        f"Version: {version}",
        "Summary: fixture",
        *(f"Classifier: {item}" for item in classifiers),
    ]
    return "\n".join(lines) + "\n\nbody\n"


def write_wheel(
    directory: Path,
    version: str,
    *,
    metadata_version: str | None = None,
    classifiers: Sequence[str] = (STABLE,),
) -> Path:
    path = directory / names(version)[0]
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            f"actseal-{version}.dist-info/METADATA",
            core_metadata(metadata_version or version, classifiers=classifiers),
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


def wheel_info(wheel: bytes) -> dict[str, object]:
    """PyPI ``info`` fields that must agree with the wheel's own METADATA."""
    with zipfile.ZipFile(io.BytesIO(wheel)) as archive:
        metadata = next(n for n in archive.namelist() if n.endswith(".dist-info/METADATA"))
        header = archive.read(metadata).decode("utf-8").split("\n\n", 1)[0]
    fields: dict[str, str] = {}
    classifiers: list[str] = []
    for line in header.splitlines():
        key, _, value = line.partition(":")
        if key == "Classifier":
            classifiers.append(value.strip())
        else:
            fields.setdefault(key, value.strip())
    return {
        "name": fields["Name"],
        "version": fields["Version"],
        "summary": fields.get("Summary", ""),
        "classifiers": classifiers,
        "yanked": False,
    }


def supplied_distributions() -> Path | None:
    """The release artifact directory from ``ACTSEAL_TEST_DIST``; ``None`` means build locally."""
    dist = os.environ.get("ACTSEAL_TEST_DIST")
    wheel = os.environ.get("ACTSEAL_TEST_WHEEL")
    if dist is None and wheel is None:
        return None
    if dist is None or wheel is None:
        pytest.fail(
            "ACTSEAL_TEST_DIST and ACTSEAL_TEST_WHEEL must be set together "
            f"(ACTSEAL_TEST_DIST={dist!r}, ACTSEAL_TEST_WHEEL={wheel!r}); refusing to rebuild"
        )
    directory = Path(dist)
    if not directory.is_absolute() or not directory.is_dir():
        pytest.fail(f"ACTSEAL_TEST_DIST={dist!r} is not an existing absolute directory")
    present = sorted(path.name for path in directory.iterdir())
    wheels = [n for n in present if n.startswith("actseal-") and n.endswith(".whl")]
    sdists = [n for n in present if n.startswith("actseal-") and n.endswith(".tar.gz")]
    if len(present) != 2 or len(wheels) != 1 or len(sdists) != 1:
        pytest.fail(
            f"ACTSEAL_TEST_DIST={dist!r} must hold exactly one wheel and one sdist: {present}"
        )
    if Path(wheel).resolve() != (directory / wheels[0]).resolve():
        pytest.fail(f"ACTSEAL_TEST_WHEEL={wheel!r} is not the wheel inside ACTSEAL_TEST_DIST")
    return directory


def release_distributions(directory: Path) -> dict[str, Path]:
    """The supplied release artifacts, or a local ``uv build --no-sources`` into ``directory``."""
    supplied = supplied_distributions()
    if supplied is not None:
        return {path.name: path for path in sorted(supplied.iterdir())}
    uv = shutil.which("uv")
    if uv is None:
        pytest.fail("uv is required on PATH to build the distributions under test")
    directory.mkdir(parents=True, exist_ok=True)
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
# Fake PyPI index served over file:// URLs, with PEP 740 attestation bundles
# --------------------------------------------------------------------------- #


def statement(filename: str, sha256: str, *, kind: str = IN_TOTO) -> str:
    document = {
        "_type": kind,
        "subject": [{"name": filename, "digest": {"sha256": sha256}}],
        "predicateType": "https://docs.pypi.org/attestations/publish/v1",
        "predicate": None,
    }
    return base64.b64encode(json.dumps(document).encode("utf-8")).decode("ascii")


def attestation(encoded_statement: str) -> dict[str, object]:
    return {
        "version": 1,
        "verification_material": {"certificate": "MIIB", "transparency_entries": [{}]},
        "envelope": {"statement": encoded_statement, "signature": "MEUCIQ"},
    }


def provenance_document(
    filename: str,
    sha256: str,
    *,
    publisher: Mapping[str, object] | None = None,
    attestations: Sequence[Mapping[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "attestation_bundles": [
            {
                "publisher": dict(PUBLISHER if publisher is None else publisher),
                "attestations": list(
                    attestations
                    if attestations is not None
                    else [attestation(statement(filename, sha256))]
                ),
            }
        ]
    }


def write_fake_index(
    base: Path,
    version: str,
    files: Mapping[str, bytes],
    *,
    provenance_for: Iterable[str] | None = None,
    declared: Mapping[str, str] | None = None,
    info: Mapping[str, object] | None = None,
    provenance: Mapping[str, object] | None = None,
    yanked: Iterable[str] = (),
) -> str:
    """Lay out ``/pypi/actseal/V/json`` and ``/integrity/...`` files; returns the base URL."""
    store = base / "files"
    store.mkdir(parents=True, exist_ok=True)
    urls = []
    wheel_name = names(version)[0]
    for name, data in files.items():
        (store / name).write_bytes(data)
        urls.append(
            {
                "filename": name,
                "url": (store / name).resolve().as_uri(),
                "size": len(data),
                "digests": {"sha256": (declared or {}).get(name, sha256_hex(data))},
                "packagetype": "bdist_wheel" if name.endswith(".whl") else "sdist",
                "yanked": name in set(yanked),
            }
        )
    if info is None:
        wheel = files.get(wheel_name)
        info = (
            wheel_info(wheel)
            if wheel is not None and zipfile.is_zipfile(io.BytesIO(wheel))
            else {
                "name": "actseal",
                "version": version,
                "summary": "fixture",
                "classifiers": [STABLE],
                "yanked": False,
            }
        )
    release = base / "pypi" / "actseal" / version
    release.mkdir(parents=True, exist_ok=True)
    (release / "json").write_text(json.dumps({"info": info, "urls": urls}), encoding="utf-8")
    for name in files if provenance_for is None else provenance_for:
        target = base / "integrity" / "actseal" / version / name
        target.mkdir(parents=True, exist_ok=True)
        document = (
            provenance
            if provenance is not None
            else provenance_document(name, sha256_hex(files[name]))
        )
        (target / "provenance").write_text(json.dumps(document), encoding="utf-8")
    return base.resolve().as_uri()


# --------------------------------------------------------------------------- #
# Receipt documents the release-receipt and receipts gates accept
# --------------------------------------------------------------------------- #


def postpublish_document(
    version: str, files: Mapping[str, Path], *, index: str = "https://pypi.org"
) -> dict[str, object]:
    """A post-publication receipt exactly as ``postpublish`` records a good release."""
    return {
        "schema_version": 1,
        "kind": "actseal-postpublish-receipt",
        "version": version,
        "index": index,
        "ok": True,
        "published_metadata": {
            "name": "actseal",
            "version": version,
            "summary": "fixture",
            "classifiers": [STABLE],
            "yanked": False,
        },
        "files": [
            {
                "filename": name,
                "url": f"{index}/packages/{name}",
                "size": files[name].stat().st_size,
                "sha256": sha256_path(files[name]),
                "declared_sha256": sha256_path(files[name]),
                "matches_build": True,
                "provenance": {
                    "present": True,
                    "attestations": 1,
                    "publishers": [dict(PUBLISHER)],
                    "subject_sha256": sha256_path(files[name]),
                },
            }
            for name in sorted(files)
        ],
        "checks": {
            "version_output": f"actseal {version}",
            "demo_exit": 0,
            "fixed_replay_exit": 0,
            "bad_replay_exit": 1,
            "demo_bad_status": "BLOCK",
            "demo_fixed_status": "PASS",
            "installed_outside_checkout": True,
        },
        "note": ATTESTATION_NOTE,
    }


def build_receipt_document(
    version: str,
    files: Mapping[str, Path],
    *,
    run_id: str = "42",
    attempt: str = "1",
    commit: str = "c" * 40,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "kind": "actseal-build-receipt",
        "version": version,
        "tag": f"v{version}",
        "ref": f"refs/tags/v{version}",
        "source_commit": commit,
        "lock_sha256": "d" * 64,
        "workflow_run": {"id": run_id, "attempt": attempt},
        "distributions": [
            {
                "filename": name,
                "size": files[name].stat().st_size,
                "sha256": sha256_path(files[name]),
            }
            for name in sorted(files)
        ],
    }


def release_receipt_document(
    version: str,
    files: Mapping[str, Path],
    *,
    run_id: str = "42",
    build_attempt: str = "1",
    verification_attempt: str = "1",
    artifact_id: str = "987654321",
    digest: str = "sha256:" + "b" * 64,
) -> dict[str, object]:
    post = postpublish_document(version, files)
    runs = f"https://github.com/ajaysurya1221/actseal/actions/runs/{run_id}/attempts/"
    return {
        "schema_version": 1,
        "kind": "actseal-release-receipt",
        "version": version,
        "tag": f"v{version}",
        "source_commit": "c" * 40,
        "lock_sha256": "d" * 64,
        "workflow_run": {
            "id": run_id,
            "build_attempt": build_attempt,
            "verification_attempt": verification_attempt,
            "build_url": runs + build_attempt,
            "verification_url": runs + verification_attempt,
        },
        "artifact": {"id": artifact_id, "digest": digest},
        "distributions": [
            {
                "filename": name,
                "size": files[name].stat().st_size,
                "sha256": sha256_path(files[name]),
            }
            for name in sorted(files)
        ],
        "verification": {
            "verify_matrix": "success",
            "postpublish": {
                key: post[key] for key in ("index", "published_metadata", "files", "checks", "note")
            },
        },
        "note": "Contains no credentials.",
    }


# --------------------------------------------------------------------------- #
# CLI invocation and small file helpers
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


def write_json(path: Path, document: Mapping[str, object]) -> Path:
    return write_text(path, json.dumps(document))


def python_script(path: Path, body: str, *, parents: bool = False) -> Path:
    """An executable script running under the current interpreter."""
    if parents:
        path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    path.chmod(0o755)
    return path
