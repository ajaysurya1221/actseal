"""Release gating helpers for the Actseal publication pipeline.

Every subcommand exits 0 when its check passes and 1 with one line starting
``release check failed:`` on stderr when it does not; argparse usage errors
exit 2. Only machine-consumable ``key=value`` lines are written to stdout so
the workflow can append them to ``$GITHUB_OUTPUT``. The script depends on the
standard library alone, except that ``workflow`` imports the locked PyYAML
development dependency; ``postpublish`` therefore runs under a bare Python
inside the pinned verification container.

Subcommands:

``workflow``             static contract check of ``publish-pypi.yml``
``metadata``             tag / pyproject / ``__version__`` / uv.lock agreement
``distributions``        exactly one wheel and one sdist, METADATA and
                         PKG-INFO agreement, ``SHA256SUMS`` and build receipt
``verify-distributions`` downloaded bytes equal the recorded checksums
``postpublish``          clean install of the public PyPI files, demo/replay
                         exit codes, published metadata and attestation
                         identity/subject inspection
``release-receipt``      bind artifact identity and verification results
``mirror``               create or update only a draft GitHub release
``assets``               required static assets regenerate byte-identically
``candidate``            Task 20 release gate (fails until v1 assets exist)
``docs``                 Task 08 documentation gate
``receipts``             Task 21 final receipt gate
"""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import io
import json
import math
import os
import re
import shlex
import shutil
import struct
import subprocess
import sys
import tarfile
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_RELATIVE = Path(".github") / "workflows" / "publish-pypi.yml"
PROJECT_NAME = "actseal"
REPOSITORY = "ajaysurya1221/actseal"
PYPI_BASE_URL = "https://pypi.org"
INTEGRITY_ACCEPT = "application/vnd.pypi.integrity.v1+json"
UV_VERSION = "0.12.5"
CONTAINER_IMAGE = "python@sha256:d657ab0ade19f404a6ccc883ab399540de667aff751748ce23c07330c5a89e64"
APPROVED_ACTIONS = frozenset(
    {
        "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
        "astral-sh/setup-uv@c18668ad3cf93ea998bef934396af7bb5c839dc7",
        "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
        "actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c",
        "pypa/gh-action-pypi-publish@dc37677b2e1c63e2034f94d8a5b11f265b73ba33",
    }
)
EXPECTED_JOBS = ("build", "verify", "assets", "publish", "verify-published", "mirror")
WORKFLOW_FILENAME = "publish-pypi.yml"
ENVIRONMENT_NAME = "pypi"
EXPECTED_PUBLISHER = {
    "kind": "GitHub",
    "repository": REPOSITORY,
    "workflow": WORKFLOW_FILENAME,
    "environment": ENVIRONMENT_NAME,
}
IN_TOTO_STATEMENT = "https://in-toto.io/Statement/v1"
# PyPI Publish attestation (https://docs.pypi.org/attestations/publish/v1/): the
# predicate type is fixed and the predicate body is documented as empty.
PYPI_PUBLISH_PREDICATE = "https://docs.pypi.org/attestations/publish/v1"
GITHUB_RUNS_URL = f"https://github.com/{REPOSITORY}/actions/runs"
STABLE_CLASSIFIER = "Development Status :: 5 - Production/Stable"
VERSION_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
SHA256_HEX_RE = re.compile(r"\b[0-9a-f]{64}\b")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SUMS_LINE_RE = re.compile(r"^([0-9a-f]{64})  ([^/\\\s]+)$")
CREDENTIAL_RE = re.compile(r"pypi-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_|Bearer\s")
DISTRIBUTION_COUNT = 2
SHA256_HEX_LENGTH = 64
HTTP_NOT_FOUND = 404
POLL_INTERVAL_S = 15.0
DOWNLOAD_LIMIT_BYTES = 64 * 1024 * 1024
SOCIAL_PREVIEW_SIZE = (1280, 640)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_IHDR_OFFSET = 16
PNG_IHDR_END = 24
COMMAND_TIMEOUT_S = 600.0
# Required static assets by renderer name, with the outputs declared in the
# accepted Task 10 inventory (docs/assets/src/actseal_assets/inventory.py).
# ``demo`` is the approved post-PyPI exception and is deliberately absent.
ASSET_DIR = "docs/assets"
RENDERER_RELATIVE = "docs/assets/src/render.py"
DEFAULT_RENDERER = "uv run --frozen --group assets python docs/assets/src/render.py"
RELEASE_ASSETS: dict[str, tuple[str, ...]] = {
    "hero": ("hero-light.svg", "hero-dark.svg"),
    "how-it-works": (
        "how-it-works-light.svg",
        "how-it-works-dark.svg",
        "how-it-works-mobile-light.svg",
        "how-it-works-mobile-dark.svg",
    ),
    "architecture": ("architecture.svg",),
    "social": ("social.png",),
}
SOCIAL_PREVIEW_FILE = "social.png"
# Exact smoke outcomes the post-publication receipt must record.
EXPECTED_SMOKE = {
    "demo_exit": 0,
    "fixed_replay_exit": 0,
    "bad_replay_exit": 1,
    "demo_bad_status": "BLOCK",
    "demo_fixed_status": "PASS",
    "installed_outside_checkout": True,
}
HTML_ATTRIBUTE_RE = re.compile(r"""\b(href|src|srcset)\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.I)
REQUIRED_DOCS = (
    "docs/quickstart.md",
    "docs/stability.md",
    "docs/versioning.md",
    "docs/migration.md",
    "docs/publishing.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
)
README_DESCRIPTION = (
    "Actseal verifies model-chosen application actions for developers: freeze a "
    "policy, check its recorded decisions, and replay the evidence offline."
)
README_QUICKSTART = (
    "uvx --python 3.12 actseal demo --out ./actseal-demo",
    "uvx --offline --python 3.12 actseal replay ./actseal-demo/fixed/evidence",
    "uvx --offline --python 3.12 actseal replay ./actseal-demo/bad/evidence",
)
RECEIPT_PATHS = {
    "release_receipt": "plan/v1/receipts/release-receipt.json",
    "sha256sums": "plan/v1/receipts/SHA256SUMS",
    "postpublish": "plan/v1/receipts/postpublish-receipt.json",
    "release_notes": "plan/v1/RELEASE_NOTES.md",
    "final_report": "plan/v1/FINAL_REPORT.md",
    "launch": "plan/v1/LAUNCH.md",
}
ATTESTATION_NOTE = (
    "Attestation presence, publisher identity and statement subjects were inspected; "
    "no independent cryptographic verification is claimed."
)
GITHUB_FILE_PREFIXES = {
    "github.com": (f"/{REPOSITORY}/blob/main/", f"/{REPOSITORY}/raw/main/"),
    "raw.githubusercontent.com": (f"/{REPOSITORY}/main/",),
}
MARKDOWN_LINK_RE = re.compile(r"\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


class ReleaseCheckError(Exception):
    """A release gate did not pass; the message is the complete explanation."""


def _out(text: str) -> None:
    sys.stdout.write(text + "\n")
    sys.stdout.flush()


def _err(text: str) -> None:
    sys.stderr.write(text + "\n")
    sys.stderr.flush()


def _require(condition: bool, message: str) -> None:  # noqa: FBT001 - assertion helper
    if not condition:
        raise ReleaseCheckError(message)


def _as_dict(value: object, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReleaseCheckError(f"{where} must be an object")
    return dict(value)


def _as_list(value: object, where: str) -> list[Any]:
    if not isinstance(value, list):
        raise ReleaseCheckError(f"{where} must be a list")
    return list(value)


def _exact_int(value: object, expected: int, where: str) -> None:
    """``True == 1`` in Python; schema versions and counts must be real integers."""
    if type(value) is not int or value != expected:
        raise ReleaseCheckError(f"{where} must be the integer {expected}, got {value!r}")


def _base64_text(value: object, where: str) -> str:
    """A non-empty standard-base64 string (the shape only; nothing is verified)."""
    _require(isinstance(value, str) and bool(value), f"{where} must be a non-empty base64 string")
    try:
        decoded = base64.b64decode(str(value), validate=True)
    except (binascii.Error, ValueError) as error:
        raise ReleaseCheckError(f"{where} is not valid base64 ({error})") from error
    _require(bool(decoded), f"{where} decodes to nothing")
    return str(value)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_version(version: str) -> tuple[int, int, int]:
    match = VERSION_RE.fullmatch(version)
    if match is None:
        raise ReleaseCheckError(f"version {version!r} is not a plain MAJOR.MINOR.PATCH release")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def distribution_names(version: str) -> tuple[str, str]:
    """``(wheel, sdist)`` filenames for ``version``."""
    return f"{PROJECT_NAME}-{version}-py3-none-any.whl", f"{PROJECT_NAME}-{version}.tar.gz"


def _git_probe(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed git invocation with checked arguments
        ["git", "-C", str(root), *args],  # noqa: S607 - git resolved from PATH by design
        capture_output=True,
        text=True,
        check=False,
        timeout=COMMAND_TIMEOUT_S,
    )


def _git(root: Path, *args: str) -> str:
    result = _git_probe(root, *args)
    _require(result.returncode == 0, f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


# --------------------------------------------------------------------------- #
# SHA256SUMS
# --------------------------------------------------------------------------- #


def read_sha256sums(path: Path) -> dict[str, str]:
    """Filename to digest from GNU ``sha256sum`` output; rejects malformed or duplicate lines."""
    _require(path.is_file(), f"checksum file {path} is missing")
    entries: dict[str, str] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        match = SUMS_LINE_RE.fullmatch(line)
        if match is None:
            raise ReleaseCheckError(f"{path}:{number}: malformed SHA256SUMS line {line!r}")
        digest, name = match.group(1), match.group(2)
        _require(name not in entries, f"{path}: duplicate entry for {name}")
        entries[name] = digest
    _require(bool(entries), f"{path} lists no files")
    return entries


def write_sha256sums(path: Path, digests: Mapping[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{digests[name]}  {name}\n" for name in sorted(digests)]
    path.write_text("".join(lines), encoding="utf-8")


def _write_json(path: Path, document: Mapping[str, object]) -> None:
    try:
        encoded = json.dumps(document, indent=2, sort_keys=True, allow_nan=False) + "\n"
    except (TypeError, ValueError) as error:
        raise ReleaseCheckError(f"cannot encode receipt as finite JSON: {error}") from error
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(encoded, encoding="utf-8")


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        _require(key not in result, "receipt JSON contains a duplicate object key")
        result[key] = value
    return result


def _reject_json_constant(_value: str) -> NoReturn:
    raise ReleaseCheckError("receipt JSON contains a nonfinite constant")


def _finite_json_float(value: str) -> float:
    number = float(value)
    _require(math.isfinite(number), "receipt JSON contains a nonfinite number")
    return number


def _require_fields(record: Mapping[str, Any], fields: Iterable[str], where: str) -> None:
    expected = set(fields)
    _require(set(record) == expected, f"{where}: keys must be exactly {sorted(expected)}")


def _read_json(path: Path, description: str) -> dict[str, Any]:
    _require(
        path.is_file(), f"{description} {path} is missing; do not auto-promote missing receipts"
    )
    try:
        document = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
            parse_float=_finite_json_float,
        )
    except (ValueError, UnicodeError) as error:
        raise ReleaseCheckError(f"{description} {path} is not valid JSON: {error}") from error
    _require(isinstance(document, dict), f"{description} {path} must be a JSON object")
    return dict(document)


def _scan_credentials(value: object, where: str) -> None:
    """Fail on anything shaped like a token anywhere inside a JSON document."""
    if isinstance(value, str):
        _require(
            CREDENTIAL_RE.search(value) is None, f"{where} contains a credential-shaped string"
        )
    elif isinstance(value, dict):
        for key, item in value.items():
            _scan_credentials(item, f"{where}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _scan_credentials(item, f"{where}[{index}]")


# --------------------------------------------------------------------------- #
# Version sources
# --------------------------------------------------------------------------- #


def pyproject_version(root: Path) -> str:
    path = root / "pyproject.toml"
    _require(path.is_file(), f"{path} is missing")
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    version = data.get("project", {}).get("version")
    _require(isinstance(version, str), "pyproject.toml has no [project] version")
    return str(version)


def pyproject_classifiers(root: Path) -> list[str]:
    with (root / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)
    classifiers = data.get("project", {}).get("classifiers", [])
    return [str(item) for item in classifiers]


def source_version(root: Path) -> str:
    path = root / "src" / "actseal" / "__init__.py"
    _require(path.is_file(), f"{path} is missing")
    matches = re.findall(r'^__version__ = "([^"]+)"$', path.read_text(encoding="utf-8"), re.M)
    _require(len(matches) == 1, "src/actseal/__init__.py must define __version__ exactly once")
    return str(matches[0])


def lock_version(root: Path) -> str:
    path = root / "uv.lock"
    _require(path.is_file(), f"{path} is missing")
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    own = [
        package
        for package in data.get("package", [])
        if package.get("name") == PROJECT_NAME and package.get("source") == {"editable": "."}
    ]
    _require(len(own) == 1, "uv.lock must contain exactly one editable actseal package entry")
    version = own[0].get("version")
    _require(isinstance(version, str), "uv.lock actseal entry has no version")
    return str(version)


def agreed_version(root: Path) -> str:
    """The single version shared by pyproject, ``__version__`` and the uv.lock self entry."""
    versions = {
        "pyproject.toml": pyproject_version(root),
        "src/actseal/__init__.py": source_version(root),
        "uv.lock": lock_version(root),
    }
    distinct = set(versions.values())
    _require(len(distinct) == 1, f"version sources disagree: {versions}")
    version = distinct.pop()
    parse_version(version)
    return version


# --------------------------------------------------------------------------- #
# workflow
# --------------------------------------------------------------------------- #


def _load_workflow(path: Path) -> dict[Any, Any]:
    import yaml  # type: ignore[import-untyped]  # noqa: PLC0415 - locked dev dependency

    _require(path.is_file(), f"workflow file {path} is missing")
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    _require(isinstance(document, dict), "workflow must be a YAML mapping")
    return dict(document)


def _steps(job: Mapping[str, Any]) -> list[dict[str, Any]]:
    steps = job.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ReleaseCheckError(f"job {job.get('name')!r} has no steps")
    return [dict(step) for step in steps]


def _run_text(job: Mapping[str, Any]) -> str:
    return "\n".join(str(step.get("run", "")) for step in _steps(job))


def _needs(job: Mapping[str, Any]) -> set[str]:
    needs = job.get("needs", [])
    return {needs} if isinstance(needs, str) else set(needs)


def _check_workflow_triggers(document: Mapping[Any, Any]) -> None:
    # PyYAML parses the bare `on:` key as the boolean True.
    triggers = document.get(True, document.get("on"))
    _require(isinstance(triggers, dict), "workflow needs an `on:` mapping")
    _require(
        set(triggers) == {"push", "workflow_dispatch"},
        "workflow triggers must be exactly push and workflow_dispatch",
    )
    _require(triggers["push"] == {"tags": ["v*"]}, "push trigger must be exactly tags: ['v*']")
    _require(
        triggers["workflow_dispatch"] in (None, {}),
        "workflow_dispatch must be rehearsal-only with no inputs",
    )
    _require(
        document.get("permissions") == {"contents": "read"},
        "top-level permissions must be exactly contents: read",
    )
    concurrency = document.get("concurrency", {})
    _require(
        isinstance(concurrency, dict) and concurrency.get("cancel-in-progress") is False,
        "concurrency must set cancel-in-progress: false",
    )
    jobs = document.get("jobs")
    _require(
        isinstance(jobs, dict) and tuple(jobs) == EXPECTED_JOBS,
        f"jobs must be exactly {list(EXPECTED_JOBS)} in order",
    )


def _check_assets_job(job: Mapping[str, Any]) -> None:
    text = _run_text(job)
    _require(
        "uv sync --frozen --group dev --group assets" in text,
        "assets job must install the locked assets dependency group",
    )
    _require(
        "docs/assets/src/setup_tools.py" in text,
        "assets job must fetch the pinned authoring tools with hash verification",
    )
    _require("check_release.py assets" in text, "assets job must run check_release.py assets")
    _require("uv build" not in text, "assets job must not build distributions")


def _check_workflow_pins(jobs: Mapping[str, Any]) -> None:
    build_count = 0
    for name, job in jobs.items():
        for step in _steps(job):
            uses = step.get("uses")
            if uses is not None:
                _require(uses in APPROVED_ACTIONS, f"job {name}: unapproved action {uses!r}")
                if uses.startswith("astral-sh/setup-uv@"):
                    version = str(step.get("with", {}).get("version"))
                    _require(version == UV_VERSION, f"job {name}: setup-uv must pin {UV_VERSION}")
                if uses.startswith("actions/download-artifact@"):
                    options = step.get("with", {})
                    _require(
                        "name" not in options, f"job {name}: download-artifact must not use name:"
                    )
                    _require(
                        str(options.get("artifact-ids", "")).startswith("${{ needs."),
                        f"job {name}: download-artifact must use an upstream artifact ID",
                    )
            run = str(step.get("run", ""))
            if "uv build" in run:
                _require(name == "build", f"job {name}: only the build job may run uv build")
                build_count += run.count("uv build")
        permissions = job.get("permissions", {})
        if name != "publish":
            _require("id-token" not in permissions, f"job {name}: id-token belongs only to publish")
        if name != "mirror":
            _require(
                permissions.get("contents") != "write",
                f"job {name}: contents: write belongs only to mirror",
            )
    _require(build_count == 1, "the workflow must run uv build exactly once")


def _check_build_job(job: Mapping[str, Any]) -> None:
    steps = _steps(job)
    runs = [str(step.get("run", "")) for step in steps]
    docs_steps = [
        (i, step)
        for i, step in enumerate(steps)
        if str(step.get("run", "")).strip() == "uv run --frozen python tools/check_release.py docs"
    ]
    _require(len(docs_steps) == 1, "build job must run the exact docs gate once")
    docs_index, docs_step = docs_steps[0]
    build_index = next(i for i, run in enumerate(runs) if "uv build" in run)
    _require(docs_index < build_index, "docs gate must precede building distributions")
    _require(
        docs_step.get("if") is None and docs_step.get("continue-on-error") in (None, False),
        "docs gate must be unconditional and fail closed",
    )
    distributions_index = next(
        (i for i, run in enumerate(runs) if "check_release.py distributions" in run), None
    )
    _require(distributions_index is not None, "build job must run check_release.py distributions")
    _require(
        any("check_release.py metadata" in run for run in runs),
        "build job must run check_release.py metadata",
    )
    _require(
        any("twine check --strict" in run for run in runs),
        "build job must run twine check --strict",
    )
    uploads = [
        (i, step)
        for i, step in enumerate(steps)
        if str(step.get("uses", "")).startswith("actions/upload-artifact@")
    ]
    dist_uploads = [
        (i, step)
        for i, step in uploads
        if str(step.get("with", {}).get("path", "")).endswith("/dist/")
    ]
    _require(len(dist_uploads) == 1, "build job must upload the dist/ directory exactly once")
    index, upload = dist_uploads[0]
    if distributions_index is None or index <= distributions_index:
        raise ReleaseCheckError("distributions must be validated before upload")
    options = upload.get("with", {})
    _require(options.get("overwrite") is False, "distribution upload must set overwrite: false")
    _require(
        options.get("if-no-files-found") == "error",
        "distribution upload must set if-no-files-found: error",
    )
    _require(
        "${{ github.run_id }}" in str(options.get("name")), "artifact names must be run-unique"
    )


def _check_verify_job(job: Mapping[str, Any]) -> None:
    _require(_needs(job) == {"build"}, "verify job must need exactly build")
    strategy = job.get("strategy", {})
    matrix = strategy.get("matrix", {})
    _require(strategy.get("fail-fast") is False, "verify matrix must set fail-fast: false")
    _require(
        matrix.get("os") == ["ubuntu-latest", "macos-latest"],
        "verify matrix os must be ubuntu-latest and macos-latest",
    )
    _require(
        [str(item) for item in matrix.get("python", [])] == ["3.12", "3.13"],
        "verify matrix python must be 3.12 and 3.13",
    )
    steps = _steps(job)
    downloads = [
        step for step in steps if str(step.get("uses", "")).startswith("actions/download-artifact@")
    ]
    _require(
        any(
            step.get("with", {}).get("artifact-ids") == "${{ needs.build.outputs.artifact-id }}"
            for step in downloads
        ),
        "verify must download the build distributions by artifact ID",
    )
    text = _run_text(job)
    _require(
        "check_release.py verify-distributions" in text,
        "verify must run check_release.py verify-distributions",
    )
    packaging = [step for step in steps if "pytest -m packaging" in str(step.get("run", ""))]
    _require(len(packaging) == 1, "verify must run pytest -m packaging exactly once")
    env = packaging[0].get("env", {})
    dist_dir = str(env.get("ACTSEAL_TEST_DIST", ""))
    _require(
        dist_dir.endswith("/dist"),
        "packaging tests must receive ACTSEAL_TEST_DIST pointing at the downloaded artifact",
    )
    _require(
        str(env.get("ACTSEAL_TEST_WHEEL", ""))
        == f"{dist_dir}/${{{{ needs.build.outputs.wheel }}}}",
        "packaging tests must receive ACTSEAL_TEST_WHEEL inside ACTSEAL_TEST_DIST",
    )
    for required in (
        "ruff check",
        "mypy --strict",
        'pytest -m "not integration and not packaging"',
    ):
        _require(required in text, f"verify must run {required}")


def _check_publish_job(job: Mapping[str, Any]) -> None:
    _require(
        {"build", "verify", "assets"} <= _needs(job), "publish must need build, verify and assets"
    )
    _require(job.get("environment", {}).get("name") == "pypi", "publish must use environment pypi")
    _require(
        job.get("permissions") == {"id-token": "write"},
        "publish permissions must be exactly id-token: write",
    )
    condition = str(job.get("if", ""))
    for clause in ("github.event_name == 'push'", "startsWith(github.ref, 'refs/tags/v')"):
        _require(clause in condition, f"publish condition must contain {clause}")
    steps = _steps(job)
    for step in steps:
        uses = str(step.get("uses", ""))
        _require(not uses.startswith("actions/checkout@"), "publish must not check out source")
        run = str(step.get("run", ""))
        for forbidden in ("uv build", "pip install", "twine upload", "git "):
            _require(forbidden not in run, f"publish must not run {forbidden!r}")
    publishers = [
        step
        for step in steps
        if str(step.get("uses", "")).startswith("pypa/gh-action-pypi-publish@")
    ]
    _require(len(publishers) == 1, "publish must invoke the PyPA action exactly once")
    options = publishers[0].get("with", {})
    _require(options.get("packages-dir") == "dist/", "PyPA action packages-dir must be dist/")
    _require(options.get("attestations") is True, "PyPA action must enable attestations")
    _require(options.get("skip-existing") in (None, False), "skip-existing must stay disabled")
    for forbidden in ("password", "repository-url", "user"):
        _require(forbidden not in options, f"PyPA action must not set {forbidden}")
    _require(
        "sha256sum --check --strict" in _run_text(job),
        "publish must re-check SHA256SUMS before uploading",
    )


def _check_postpublish_jobs(jobs: Mapping[str, Any]) -> None:
    verify_published = jobs["verify-published"]
    _require("publish" in _needs(verify_published), "verify-published must need publish")
    _require(
        verify_published.get("container", {}).get("image") == CONTAINER_IMAGE,
        "verify-published must run in the approved pinned container",
    )
    _require(
        "check_release.py postpublish" in _run_text(verify_published),
        "verify-published must run check_release.py postpublish",
    )
    mirror = jobs["mirror"]
    _require(
        {"build", "verify", "publish", "verify-published"} <= _needs(mirror),
        "mirror must need build, verify, publish and verify-published",
    )
    _require(
        mirror.get("permissions") == {"contents": "write"},
        "mirror permissions must be exactly contents: write",
    )
    text = _run_text(mirror)
    receipt = text.find("check_release.py release-receipt")
    upload = text.find("check_release.py mirror")
    _require(receipt >= 0, "mirror must run check_release.py release-receipt")
    _require(upload > receipt, "mirror must run check_release.py mirror after release-receipt")


def _check_workflow_text(text: str) -> None:
    for forbidden in (
        "skip-existing: true",
        "password:",
        "TWINE_",
        "PYPI_API_TOKEN",
        "--clobber",
        "gh release download",
    ):
        _require(forbidden not in text, f"workflow must not contain {forbidden!r}")
    _require(re.search(r"\b0\.1\.0\b", text) is None, "workflow must not hard-code 0.1.0")
    digests = set(SHA256_HEX_RE.findall(text))
    _require(
        digests == {CONTAINER_IMAGE.split(":")[1]},
        "the only sha256 literal allowed in the workflow is the container digest",
    )


def check_workflow(path: Path) -> None:
    document = _load_workflow(path)
    _check_workflow_triggers(document)
    jobs = document["jobs"]
    _check_workflow_pins(jobs)
    _check_build_job(jobs["build"])
    _check_verify_job(jobs["verify"])
    _check_assets_job(jobs["assets"])
    _check_publish_job(jobs["publish"])
    _check_postpublish_jobs(jobs)
    _check_workflow_text(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# metadata
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ReleaseIdentity:
    version: str
    release: bool


def check_metadata(root: Path, *, ref: str | None, sha: str | None) -> ReleaseIdentity:
    version = agreed_version(root)
    release = False
    if ref is not None:
        if ref.startswith("refs/tags/"):
            release = True
            _require(ref == f"refs/tags/v{version}", f"tag {ref} does not match version {version}")
            _require(
                parse_version(version)[0] >= 1,
                f"release tags require version 1.0.0 or later, not {version}",
            )
            _require(
                STABLE_CLASSIFIER in pyproject_classifiers(root),
                f"release requires classifier {STABLE_CLASSIFIER!r}",
            )
        else:
            _require(ref.startswith("refs/heads/"), f"unsupported ref {ref!r}")
    if sha is not None:
        head = _git(root, "rev-parse", "HEAD")
        _require(head == sha, f"wrong source SHA: HEAD is {head}, workflow saw {sha}")
        if release:
            tag = f"v{version}"
            exists = _git_probe(root, "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}")
            _require(exists.returncode == 0, f"tag {tag} is not present in the checkout")
            target = _git(root, "rev-parse", f"refs/tags/{tag}^{{commit}}")
            _require(target == sha, f"tag {tag} points at {target}, not {sha}")
    return ReleaseIdentity(version, release)


# --------------------------------------------------------------------------- #
# distributions
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Distribution:
    filename: str
    size: int
    sha256: str

    def as_dict(self) -> dict[str, object]:
        return {"filename": self.filename, "size": self.size, "sha256": self.sha256}


def _metadata_fields(text: str, source: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip():
            break
        if ":" in line and not line.startswith((" ", "\t")):
            key, _, value = line.partition(":")
            fields.setdefault(key.strip(), value.strip())
    _require("Name" in fields and "Version" in fields, f"{source} lacks Name/Version headers")
    return fields


def _check_core_metadata(text: str, source: str, version: str) -> None:
    fields = _metadata_fields(text, source)
    _require(fields["Name"] == PROJECT_NAME, f"{source} Name is {fields['Name']!r}")
    _require(
        fields["Version"] == version, f"{source} Version is {fields['Version']!r}, not {version}"
    )


def _toml_project_version(data: bytes, source: str) -> str:
    version = tomllib.loads(data.decode("utf-8")).get("project", {}).get("version")
    _require(isinstance(version, str), f"{source} has no [project] version")
    return str(version)


def check_wheel(path: Path, version: str) -> None:
    _require(zipfile.is_zipfile(path), f"{path.name} is not a zip archive")
    with zipfile.ZipFile(path) as archive:
        metadata = f"{PROJECT_NAME}-{version}.dist-info/METADATA"
        _require(metadata in archive.namelist(), f"{path.name} lacks {metadata}")
        _check_core_metadata(
            archive.read(metadata).decode("utf-8"), f"{path.name} METADATA", version
        )


def _sdist_member(archive: tarfile.TarFile, path: Path, member: str) -> bytes:
    if member not in archive.getnames():
        raise ReleaseCheckError(f"{path.name} lacks {member}")
    handle = archive.extractfile(member)
    if handle is None:
        raise ReleaseCheckError(f"{path.name}: {member} is not a regular file")
    with handle:
        return handle.read()


def _inspect_sdist(archive: tarfile.TarFile, path: Path, version: str) -> None:
    prefix = f"{PROJECT_NAME}-{version}"
    pkg_info = _sdist_member(archive, path, f"{prefix}/PKG-INFO").decode("utf-8")
    _check_core_metadata(pkg_info, f"{path.name} PKG-INFO", version)
    pyproject = _sdist_member(archive, path, f"{prefix}/pyproject.toml")
    inner = _toml_project_version(pyproject, f"{path.name} pyproject.toml")
    _require(inner == version, f"{path.name} pyproject.toml version is {inner!r}")
    lock = tomllib.loads(_sdist_member(archive, path, f"{prefix}/uv.lock").decode("utf-8"))
    own = [p for p in lock.get("package", []) if p.get("name") == PROJECT_NAME]
    _require(
        len(own) == 1 and own[0].get("version") == version,
        f"{path.name} uv.lock self-version does not equal {version}",
    )


def check_sdist(path: Path, version: str) -> None:
    try:
        with tarfile.open(path, mode="r:gz") as archive:
            _inspect_sdist(archive, path, version)
    except (tarfile.TarError, OSError) as error:
        raise ReleaseCheckError(f"{path.name} is not a readable tar.gz archive: {error}") from error


def inspect_distributions(directory: Path, version: str) -> list[Distribution]:
    """The exactly-two expected distribution files in ``directory``, validated."""
    _require(directory.is_dir(), f"distribution directory {directory} is missing")
    wheel, sdist = distribution_names(version)
    present = sorted(path.name for path in directory.iterdir())
    for name in (wheel, sdist):
        _require(name in present, f"missing distribution {name}")
    extra = [name for name in present if name not in (wheel, sdist)]
    _require(not extra, f"unexpected file(s) in packages-dir (only wheel+sdist allowed): {extra}")
    for name in present:
        _require((directory / name).is_file(), f"{name} is not a regular file")
    check_wheel(directory / wheel, version)
    check_sdist(directory / sdist, version)
    return [
        Distribution(name, (directory / name).stat().st_size, sha256_file(directory / name))
        for name in (wheel, sdist)
    ]


def build_receipt(
    root: Path,
    distributions: Sequence[Distribution],
    *,
    version: str,
    ref: str | None,
    sha: str | None,
    run_id: str | None,
    run_attempt: str | None,
) -> dict[str, object]:
    tag = (
        ref.removeprefix("refs/tags/") if ref is not None and ref.startswith("refs/tags/") else None
    )
    workflow_run = {"id": run_id, "attempt": run_attempt} if run_id and run_attempt else None
    return {
        "schema_version": 1,
        "kind": "actseal-build-receipt",
        "version": version,
        "tag": tag,
        "ref": ref,
        "source_commit": sha,
        "lock_sha256": sha256_file(root / "uv.lock"),
        "workflow_run": workflow_run,
        "distributions": [item.as_dict() for item in distributions],
    }


def verify_distributions(directory: Path, version: str, sums_path: Path) -> list[Distribution]:
    """Every file in ``directory`` matches ``SHA256SUMS`` exactly, with nothing stale or extra."""
    expected = read_sha256sums(sums_path)
    names = set(distribution_names(version))
    _require(
        set(expected) == names,
        f"stale checksum file: expected entries for {sorted(names)}, got {sorted(expected)}",
    )
    _require(directory.is_dir(), f"distribution directory {directory} is missing")
    present = {path.name for path in directory.iterdir()}
    _require(
        present == names, f"distribution files {sorted(present)} must be exactly {sorted(names)}"
    )
    results: list[Distribution] = []
    for name in sorted(names):
        path = directory / name
        _require(path.is_file(), f"{name} is not a regular file")
        actual = sha256_file(path)
        _require(
            actual == expected[name], f"altered hash: {name} is {actual}, expected {expected[name]}"
        )
        results.append(Distribution(name, path.stat().st_size, actual))
    return results


# --------------------------------------------------------------------------- #
# postpublish
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class CommandResult:
    argv: tuple[str, ...]
    code: int
    stdout: str
    stderr: str

    def json(self) -> dict[str, Any]:
        try:
            document = json.loads(self.stdout)
        except json.JSONDecodeError as error:
            raise ReleaseCheckError(
                f"{' '.join(self.argv)} did not print JSON: {self.stdout[:200]!r}"
            ) from error
        _require(isinstance(document, dict), f"{' '.join(self.argv)} printed a non-object JSON")
        return dict(document)


def _fetch(url: str, *, accept: str | None = None) -> bytes | None:
    """GET ``url``; ``None`` when the resource does not exist (HTTP 404 or missing file)."""
    headers = {"Accept": accept} if accept else {}
    request = urllib.request.Request(url, headers=headers)  # noqa: S310 - scheme fixed by caller
    try:
        with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
            body = response.read(DOWNLOAD_LIMIT_BYTES + 1)
    except urllib.error.HTTPError as error:
        if error.code == HTTP_NOT_FOUND:
            return None
        raise ReleaseCheckError(f"GET {url} failed with HTTP {error.code}") from error
    except urllib.error.URLError as error:
        if isinstance(error.reason, FileNotFoundError):
            return None
        raise ReleaseCheckError(f"GET {url} failed: {error.reason}") from error
    _require(len(body) <= DOWNLOAD_LIMIT_BYTES, f"GET {url} exceeded {DOWNLOAD_LIMIT_BYTES} bytes")
    return bytes(body)


def _fetch_release_json(base: str, version: str, wait_seconds: float) -> dict[str, Any]:
    url = f"{base}/pypi/{PROJECT_NAME}/{version}/json"
    deadline = time.monotonic() + wait_seconds
    attempt = 0
    while True:
        attempt += 1
        body = _fetch(url)
        if body is not None:
            document = json.loads(body.decode("utf-8"))
            _require(isinstance(document, dict), f"{url} returned a non-object JSON document")
            return dict(document)
        remaining = deadline - time.monotonic()
        _require(
            remaining > 0,
            f"{PROJECT_NAME} {version} is not visible at {url} after {attempt} attempt(s)",
        )
        _err(
            f"attempt {attempt}: {url} not yet available; read-only poll in {POLL_INTERVAL_S:.0f}s"
        )
        time.sleep(min(POLL_INTERVAL_S, remaining))


METADATA_KEYS = frozenset({"name", "version", "summary", "classifiers", "yanked"})


def validate_metadata_record(record: Mapping[str, Any], version: str, where: str) -> None:
    """Strict shape and content of a published-metadata record (PyPI info or a receipt copy)."""
    _require(set(record) == METADATA_KEYS, f"{where}: keys must be exactly {sorted(METADATA_KEYS)}")
    _require(record.get("name") == PROJECT_NAME, f"{where}: project name is {record.get('name')!r}")
    _require(record.get("version") == version, f"{where}: version is {record.get('version')!r}")
    _require(record.get("yanked") is False, f"{where}: release {version} is yanked or not marked")
    classifiers = _as_list(record.get("classifiers"), f"{where}: classifiers")
    _require(
        all(isinstance(item, str) and bool(item) for item in classifiers),
        f"{where}: classifiers must be a list of non-empty strings",
    )
    if parse_version(version)[0] >= 1:
        _require(
            STABLE_CLASSIFIER in classifiers,
            f"{where}: published {version} lacks classifier {STABLE_CLASSIFIER!r}",
        )
    summary = record.get("summary")
    _require(isinstance(summary, str) and bool(summary.strip()), f"{where}: summary is missing")


def _published_metadata(document: Mapping[str, Any], version: str) -> dict[str, object]:
    """The project/version/classifier facts PyPI reports for this exact release."""
    info = _as_dict(document.get("info"), "PyPI release JSON info")
    record = {key: info.get(key) for key in METADATA_KEYS}
    validate_metadata_record(record, version, "PyPI info")
    classifiers = _as_list(record["classifiers"], "PyPI info: classifiers")
    return {
        "name": PROJECT_NAME,
        "version": version,
        "summary": str(record["summary"]),
        "classifiers": sorted(str(item) for item in classifiers),
        "yanked": False,
    }


def _published_files(document: Mapping[str, Any], version: str) -> dict[str, dict[str, Any]]:
    wheel, sdist = distribution_names(version)
    kinds = {wheel: "bdist_wheel", sdist: "sdist"}
    files: dict[str, dict[str, Any]] = {}
    for raw in _as_list(document.get("urls"), "PyPI release JSON urls"):
        entry = _as_dict(raw, "PyPI urls entry")
        filename = str(entry.get("filename"))
        _require(filename not in files, f"PyPI lists {filename} twice")
        files[filename] = entry
    extra = sorted(set(files) - set(kinds))
    _require(not extra, f"PyPI lists unexpected files for {version}: {extra}")
    missing = sorted(set(kinds) - set(files))
    _require(
        not missing,
        f"partial publication: PyPI has {len(files)} of {DISTRIBUTION_COUNT} expected files, "
        f"missing {missing}; nothing will be re-uploaded or rebuilt",
    )
    for filename, entry in files.items():
        _require(entry.get("yanked") is False, f"{filename} is yanked or not marked unyanked")
        _require(
            entry.get("packagetype") == kinds[filename],
            f"{filename} has packagetype {entry.get('packagetype')!r}",
        )
        _require(str(entry.get("url", "")).startswith(("https://", "file://")), f"{filename} URL")
        digest = entry.get("digests", {}).get("sha256")
        _require(
            isinstance(digest, str) and HEX64_RE.fullmatch(digest) is not None,
            f"{filename} lacks a declared sha256",
        )
    return files


def _decode_statement(encoded: object, where: str) -> dict[str, Any]:
    _require(isinstance(encoded, str) and bool(encoded), f"{where}: envelope.statement missing")
    try:
        raw = base64.b64decode(str(encoded), validate=True)
        statement = json.loads(raw.decode("utf-8"))
    except (binascii.Error, ValueError) as error:
        raise ReleaseCheckError(f"{where}: statement is not base64 JSON ({error})") from error
    _require(isinstance(statement, dict), f"{where}: statement is not an object")
    _require(
        statement.get("_type") == IN_TOTO_STATEMENT,
        f"{where}: statement type is {statement.get('_type')!r}",
    )
    _require(
        statement.get("predicateType") == PYPI_PUBLISH_PREDICATE,
        f"{where}: predicateType is {statement.get('predicateType')!r}, "
        f"not the PyPI Publish attestation {PYPI_PUBLISH_PREDICATE}",
    )
    _require(
        statement.get("predicate") in (None, {}),
        f"{where}: the PyPI Publish predicate must be empty, got {statement.get('predicate')!r}",
    )
    return dict(statement)


def _check_verification_material(material: object, where: str) -> None:
    """PEP 740 verification material: base64 certificate and non-empty transparency entries."""
    fields = _as_dict(material, f"{where}: verification_material")
    _base64_text(fields.get("certificate"), f"{where}: verification_material.certificate")
    entries = _as_list(
        fields.get("transparency_entries"), f"{where}: verification_material.transparency_entries"
    )
    _require(bool(entries), f"{where}: verification_material.transparency_entries is empty")
    for number, entry in enumerate(entries):
        _as_dict(entry, f"{where}: transparency entry {number}")


def _statement_subjects(statement: Mapping[str, Any], where: str) -> list[tuple[str, str]]:
    subjects = _as_list(statement.get("subject"), f"{where}: statement subject")
    _require(bool(subjects), f"{where}: statement has no subject")
    pairs: list[tuple[str, str]] = []
    for raw in subjects:
        subject = _as_dict(raw, f"{where}: subject")
        name = subject.get("name")
        digest = subject.get("digest", {})
        sha = digest.get("sha256") if isinstance(digest, dict) else None
        _require(
            isinstance(name, str) and isinstance(sha, str) and HEX64_RE.fullmatch(sha) is not None,
            f"{where}: subject lacks a name or sha256 digest",
        )
        pairs.append((str(name), str(sha)))
    return pairs


def _inspect_bundle(
    bundle: object, *, filename: str, sha256: str, index: int
) -> tuple[dict[str, object], int]:
    where = f"{filename} attestation bundle {index}"
    entry = _as_dict(bundle, where)
    publisher = _as_dict(entry.get("publisher"), f"{where}: publisher")
    identity = {key: publisher.get(key) for key in EXPECTED_PUBLISHER}
    _require(
        identity == EXPECTED_PUBLISHER,
        f"{where}: publisher {identity} is not the expected trusted publisher",
    )
    attestations = _as_list(entry.get("attestations"), f"{where}: attestations")
    _require(bool(attestations), f"{where}: no attestations")
    for number, raw in enumerate(attestations):
        label = f"{where} attestation {number}"
        attestation = _as_dict(raw, label)
        _exact_int(attestation.get("version"), 1, f"{label}: attestation version")
        envelope = _as_dict(attestation.get("envelope"), f"{label}: envelope")
        _base64_text(envelope.get("signature"), f"{label}: envelope.signature")
        _check_verification_material(attestation.get("verification_material"), label)
        subjects = _statement_subjects(_decode_statement(envelope.get("statement"), label), label)
        _require(
            (filename, sha256) in subjects,
            f"{label}: statement subjects {subjects} do not name {filename} with sha256 {sha256}",
        )
    return identity, len(attestations)


def _provenance(base: str, version: str, filename: str, sha256: str) -> dict[str, object]:
    """PEP 740 provenance inspection: publisher identity and statement subjects only.

    Signatures and certificates are recorded as present but are not verified
    here; the receipt note states that distinction.
    """
    url = f"{base}/integrity/{PROJECT_NAME}/{version}/{filename}/provenance"
    body = _fetch(url, accept=INTEGRITY_ACCEPT)
    if body is None:
        return {"present": False, "attestations": 0, "publishers": [], "subject_sha256": None}
    try:
        document = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReleaseCheckError(f"{filename}: provenance is not JSON ({error})") from error
    _require(isinstance(document, dict), f"{filename}: provenance is not an object")
    bundles = document.get("attestation_bundles")
    _require(isinstance(bundles, list) and bool(bundles), f"{filename}: provenance has no bundles")
    publishers: list[dict[str, object]] = []
    count = 0
    for index, bundle in enumerate(bundles):
        identity, attested = _inspect_bundle(bundle, filename=filename, sha256=sha256, index=index)
        publishers.append(identity)
        count += attested
    return {
        "present": True,
        "attestations": count,
        "publishers": publishers,
        "subject_sha256": sha256,
    }


def _wheel_metadata(data: bytes, version: str) -> dict[str, object]:
    """Name, version, summary and classifiers from the wheel's METADATA."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            text = archive.read(f"{PROJECT_NAME}-{version}.dist-info/METADATA").decode("utf-8")
    except (zipfile.BadZipFile, KeyError, UnicodeDecodeError) as error:
        raise ReleaseCheckError(f"downloaded wheel METADATA unreadable: {error}") from error
    fields = _metadata_fields(text, "downloaded wheel METADATA")
    classifiers = sorted(
        line.partition(":")[2].strip()
        for line in text.split("\n\n", 1)[0].splitlines()
        if line.startswith("Classifier:")
    )
    return {
        "name": fields["Name"],
        "version": fields["Version"],
        "summary": fields.get("Summary", ""),
        "classifiers": classifiers,
        "yanked": False,
    }


def _run(argv: Sequence[str], *, cwd: Path, env: Mapping[str, str]) -> CommandResult:
    result = subprocess.run(  # noqa: S603 - fixed binaries inside the fresh environment
        list(argv),
        capture_output=True,
        text=True,
        check=False,
        cwd=str(cwd),
        env=dict(env),
        timeout=COMMAND_TIMEOUT_S,
    )
    return CommandResult(tuple(argv), result.returncode, result.stdout, result.stderr)


def assert_demo_outcomes(
    version: str,
    version_result: CommandResult,
    demo: CommandResult,
    fixed_replay: CommandResult,
    bad_replay: CommandResult,
) -> dict[str, object]:
    """The frozen exit-code and verdict expectations for the installed demo; pure."""
    _require(version_result.code == 0, f"--version exited {version_result.code}")
    _require(
        version_result.stdout.startswith(f"{PROJECT_NAME} {version}"),
        f"--version printed {version_result.stdout!r}",
    )
    _require(demo.code == 0, f"wrong exit code: demo exited {demo.code}, expected 0")
    document = demo.json()
    runs = document.get("runs", {})
    bad_status = runs.get("bad", {}).get("status")
    fixed_status = runs.get("fixed", {}).get("status")
    _require(bad_status == "BLOCK", f"demo bad run status is {bad_status!r}, expected BLOCK")
    _require(fixed_status == "PASS", f"demo fixed run status is {fixed_status!r}, expected PASS")
    _require(
        fixed_replay.code == 0,
        f"wrong exit code: fixed replay exited {fixed_replay.code}, expected 0",
    )
    _require(
        bad_replay.code == 1, f"wrong exit code: bad replay exited {bad_replay.code}, expected 1"
    )
    _require(fixed_replay.json().get("status") == "PASS", "fixed replay status is not PASS")
    _require(bad_replay.json().get("status") == "BLOCK", "bad replay status is not BLOCK")
    return {
        "version_output": version_result.stdout.strip(),
        "demo_exit": demo.code,
        "fixed_replay_exit": fixed_replay.code,
        "bad_replay_exit": bad_replay.code,
        "demo_bad_status": bad_status,
        "demo_fixed_status": fixed_status,
    }


def _clean_env() -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"PYTHONPATH", "VIRTUAL_ENV", "PYTHONHOME", "PYTHONSAFEPATH"}
    }
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _install_and_exercise(
    wheel: Path, *, version: str, workdir: Path, checkout: Path | None, python: str
) -> dict[str, object]:
    venv = workdir / "venv"
    env = _clean_env()
    bootstrap = _run([python, "-m", "venv", str(venv)], cwd=workdir, env=env)
    _require(bootstrap.code == 0, f"venv creation failed: {bootstrap.stderr.strip()}")
    venv_python = venv / "bin" / "python"
    install = _run(
        [
            str(venv_python),
            "-m",
            "pip",
            "install",
            "--no-index",
            "--no-deps",
            "--quiet",
            str(wheel),
        ],
        cwd=workdir,
        env=env,
    )
    _require(install.code == 0, f"wheel installation failed: {install.stderr.strip()}")
    console = venv / "bin" / PROJECT_NAME
    _require(console.is_file(), "installed console script actseal is missing")
    location = _run(
        [str(venv_python), "-c", "import actseal, os; print(os.path.realpath(actseal.__file__))"],
        cwd=workdir,
        env=env,
    )
    _require(location.code == 0, "importing the installed package failed")
    package = Path(location.stdout.strip())
    _require(
        package.is_relative_to(venv.resolve()), f"actseal imported from {package}, not the venv"
    )
    if checkout is not None:
        _require(
            not package.is_relative_to(checkout.resolve()),
            f"actseal imported from inside the checkout: {package}",
        )
    demo_dir = workdir / "demo"
    checks = assert_demo_outcomes(
        version,
        _run([str(console), "--version"], cwd=workdir, env=env),
        _run([str(console), "demo", "--out", str(demo_dir), "--json"], cwd=workdir, env=env),
        _run(
            [str(console), "replay", str(demo_dir / "fixed" / "evidence"), "--json"],
            cwd=workdir,
            env=env,
        ),
        _run(
            [str(console), "replay", str(demo_dir / "bad" / "evidence"), "--json"],
            cwd=workdir,
            env=env,
        ),
    )
    checks["installed_outside_checkout"] = True
    return checks


def _validate_smoke_checks(checks: object, version: str, where: str) -> None:
    """The recorded smoke outcomes must be exactly the frozen expectations."""
    checks = _as_dict(checks, f"{where}: checks")
    _require_fields(checks, {*EXPECTED_SMOKE, "version_output"}, f"{where}: checks")
    _require(
        checks.get("version_output") == f"{PROJECT_NAME} {version}",
        f"{where}: version_output is {checks.get('version_output')!r}",
    )
    for key, expected in EXPECTED_SMOKE.items():
        _require(
            key in checks and checks[key] == expected and type(checks[key]) is type(expected),
            f"{where}: {key} is {checks.get(key)!r}, expected {expected!r}",
        )


def postpublish(
    *,
    version: str,
    sums_path: Path,
    workdir: Path,
    out: Path,
    checkout: Path | None,
    base_url: str,
    wait_seconds: float,
    python: str,
    allow_missing_attestations: bool,
) -> dict[str, object]:
    parse_version(version)
    expected = read_sha256sums(sums_path)
    _require(
        set(expected) == set(distribution_names(version)),
        f"SHA256SUMS does not describe {version}: {sorted(expected)}",
    )
    workdir = workdir.resolve()
    if checkout is not None:
        _require(
            not workdir.is_relative_to(checkout.resolve()),
            f"workdir {workdir} must lie outside the checkout {checkout}",
        )
    _require(not workdir.exists(), f"workdir {workdir} already exists; use a fresh directory")
    workdir.mkdir(parents=True)
    base = base_url.rstrip("/")
    document = _fetch_release_json(base, version, wait_seconds)
    published = _published_metadata(document, version)
    files = _published_files(document, version)
    downloads = workdir / "downloads"
    downloads.mkdir()
    receipts: list[dict[str, object]] = []
    for filename in sorted(files):
        entry = files[filename]
        url = str(entry.get("url"))
        body = _fetch(url)
        if body is None:
            raise ReleaseCheckError(f"{filename} is listed but {url} does not exist")
        actual = hashlib.sha256(body).hexdigest()
        declared = str(entry.get("digests", {}).get("sha256"))
        _require(
            actual == expected[filename],
            f"{filename}: downloaded sha256 {actual} differs from build",
        )
        _require(
            actual == declared,
            f"{filename}: PyPI declares sha256 {declared}, bytes hash to {actual}",
        )
        (downloads / filename).write_bytes(body)
        provenance = _provenance(base, version, filename, actual)
        _require(
            bool(provenance["present"]) or allow_missing_attestations,
            f"{filename}: PyPI has no provenance/attestations for this file",
        )
        receipts.append(
            {
                "filename": filename,
                "url": url,
                "size": len(body),
                "sha256": actual,
                "declared_sha256": declared,
                "matches_build": True,
                "provenance": provenance,
            }
        )
    wheel = downloads / distribution_names(version)[0]
    wheel_metadata = _wheel_metadata(wheel.read_bytes(), version)
    _require(
        wheel_metadata == published,
        f"published metadata {published} differs from wheel METADATA {wheel_metadata}",
    )
    checks = _install_and_exercise(
        wheel, version=version, workdir=workdir, checkout=checkout, python=python
    )
    receipt: dict[str, object] = {
        "schema_version": 1,
        "kind": "actseal-postpublish-receipt",
        "version": version,
        "index": base,
        "ok": True,
        "published_metadata": published,
        "files": receipts,
        "checks": checks,
        "note": ATTESTATION_NOTE,
    }
    _scan_credentials(receipt, "postpublish receipt")
    _write_json(out, receipt)
    return receipt


# --------------------------------------------------------------------------- #
# release-receipt
# --------------------------------------------------------------------------- #


def _digits(value: object, where: str) -> str:
    _require(
        isinstance(value, str) and re.fullmatch(r"[1-9][0-9]*", value) is not None,
        f"{where} must be numeric: a positive ASCII numeric string without leading zeros",
    )
    return str(value)


def _hex64(value: object, where: str) -> str:
    _require(
        isinstance(value, str) and HEX64_RE.fullmatch(value) is not None,
        f"{where} must be a 64-hex sha256",
    )
    return str(value)


def _distribution_inventory(items: object, where: str) -> list[Distribution]:
    """Strictly typed ``[{filename, size, sha256}]`` entries, sorted by filename."""
    entries = _as_list(items, f"{where}: distributions")
    _require(bool(entries), f"{where}: distributions must not be empty")
    result: list[Distribution] = []
    for raw in entries:
        item = _as_dict(raw, f"{where}: distribution entry")
        _require_fields(item, {"filename", "size", "sha256"}, f"{where}: distribution entry")
        filename = item.get("filename")
        size = item.get("size")
        _require(isinstance(filename, str) and bool(filename), f"{where}: filename missing")
        if type(size) is not int or size <= 0:
            raise ReleaseCheckError(f"{where}: size must be a positive integer")
        result.append(Distribution(str(filename), size, _hex64(item.get("sha256"), where)))
    _require(
        len({item.filename for item in result}) == len(result), f"{where}: duplicate filenames"
    )
    return sorted(result, key=lambda item: item.filename)


def _require_same_inventory(
    actual: Sequence[Distribution], recorded: Sequence[Distribution], where: str
) -> None:
    expected = sorted(actual, key=lambda item: item.filename)
    _require(
        list(recorded) == expected,
        f"{where} inventory {[d.as_dict() for d in recorded]} differs from the verified "
        f"distributions {[d.as_dict() for d in expected]}",
    )


def _workflow_run(value: object, where: str) -> tuple[str, str]:
    run = _as_dict(value, f"{where}: workflow_run")
    _require_fields(run, {"id", "attempt"}, f"{where}: workflow_run")
    return _digits(run.get("id"), f"{where} run id"), _digits(
        run.get("attempt"), f"{where} run attempt"
    )


def validate_build_receipt(
    build: Mapping[str, Any], version: str, distributions: Sequence[Distribution]
) -> dict[str, str]:
    """Typed validation of the build receipt; returns source commit, lock hash, run id/attempt."""
    where = "build receipt"
    _require_fields(
        build,
        {
            "schema_version",
            "kind",
            "version",
            "tag",
            "ref",
            "source_commit",
            "lock_sha256",
            "workflow_run",
            "distributions",
        },
        where,
    )
    _scan_credentials(dict(build), where)
    _exact_int(build.get("schema_version"), 1, f"{where}: schema_version")
    _require(build.get("kind") == "actseal-build-receipt", f"{where}: kind is wrong")
    _require(build.get("version") == version, f"{where}: version differs from {version}")
    _require(build.get("tag") == f"v{version}", f"{where} tag is {build.get('tag')!r}")
    _require(build.get("ref") == f"refs/tags/v{version}", f"{where}: ref is {build.get('ref')!r}")
    commit = build.get("source_commit")
    _require(
        isinstance(commit, str) and GIT_SHA_RE.fullmatch(commit) is not None,
        f"{where} lacks a full 40-hex source commit",
    )
    lock = _hex64(build.get("lock_sha256"), f"{where} lock_sha256")
    run_id, attempt = _workflow_run(build.get("workflow_run"), where)
    inventory = _distribution_inventory(build.get("distributions"), where)
    _require(
        {item.filename for item in inventory} == set(distribution_names(version)),
        f"{where}: distributions must be exactly the wheel and sdist for {version}",
    )
    _require_same_inventory(distributions, inventory, where)
    return {"source_commit": str(commit), "lock_sha256": lock, "run_id": run_id, "attempt": attempt}


def _validate_postpublish_files(
    files: object,
    version: str,
    distributions: Sequence[Distribution],
    where: str,
    *,
    official_index: bool,
) -> None:
    entries = _as_list(files, f"{where}: files")
    inventory_entries: list[dict[str, object]] = []
    for raw in entries:
        entry = _as_dict(raw, f"{where}: file entry")
        _require_fields(
            entry,
            {"filename", "url", "size", "sha256", "declared_sha256", "matches_build", "provenance"},
            f"{where}: file entry",
        )
        inventory_entries.append({key: entry[key] for key in ("filename", "size", "sha256")})
    recorded = _distribution_inventory(inventory_entries, where)
    _require(
        {item.filename for item in recorded} == set(distribution_names(version)),
        f"{where}: files must be exactly the wheel and sdist for {version}",
    )
    _require_same_inventory(distributions, recorded, where)
    for raw in entries:
        entry = _as_dict(raw, f"{where}: file entry")
        filename = str(entry.get("filename"))
        label = f"{where} {filename}"
        url = entry.get("url")
        _require(isinstance(url, str) and bool(url), f"{label}: url missing")
        if official_index:
            _require(
                str(url).startswith("https://files.pythonhosted.org/"),
                f"{label}: url {url!r} is not an official PyPI file URL",
            )
        _require(entry.get("declared_sha256") == entry.get("sha256"), f"{label}: declared digest")
        _require(entry.get("matches_build") is True, f"{label}: matches_build is not true")
        provenance = _as_dict(entry.get("provenance"), f"{label}: provenance")
        _require(provenance.get("present") is True, f"{label}: provenance not present")
        _require_fields(
            provenance,
            {"present", "attestations", "publishers", "subject_sha256"},
            f"{label}: provenance",
        )
        count = provenance.get("attestations")
        if type(count) is not int or count < 1:
            raise ReleaseCheckError(f"{label}: no attestations inspected ({count!r})")
        publishers = _as_list(provenance.get("publishers"), f"{label}: publishers")
        _require(
            bool(publishers) and all(publisher == EXPECTED_PUBLISHER for publisher in publishers),
            f"{label}: publishers are not the expected trusted publisher",
        )
        _require(count >= len(publishers), f"{label}: attestation count is below publisher count")
        _require(
            provenance.get("subject_sha256") == entry.get("sha256"),
            f"{label}: attestation subject digest differs from the file digest",
        )


def validate_postpublish_receipt(
    post: Mapping[str, Any],
    version: str,
    distributions: Sequence[Distribution],
    *,
    official_index: bool,
) -> None:
    """Strict post-publication receipt; ``official_index`` requires the real PyPI (promotion)."""
    where = "post-publication receipt"
    _require_fields(
        post,
        {
            "schema_version",
            "kind",
            "version",
            "index",
            "ok",
            "published_metadata",
            "files",
            "checks",
            "note",
        },
        where,
    )
    _scan_credentials(dict(post), where)
    _exact_int(post.get("schema_version"), 1, f"{where}: schema_version")
    _require(post.get("kind") == "actseal-postpublish-receipt", f"{where}: kind is wrong")
    _require(post.get("version") == version, f"{where}: version differs from {version}")
    _require(post.get("ok") is True, f"{where} did not record ok: true")
    index = post.get("index")
    _require(isinstance(index, str) and bool(index), f"{where}: index missing")
    if official_index:
        _require(
            index == PYPI_BASE_URL, f"{where}: index is {index!r}, not official {PYPI_BASE_URL}"
        )
    metadata = _as_dict(post.get("published_metadata"), f"{where}: published_metadata")
    validate_metadata_record(metadata, version, f"{where}: published_metadata")
    _validate_postpublish_files(
        post.get("files"), version, distributions, where, official_index=official_index
    )
    _validate_smoke_checks(post.get("checks"), version, where)
    _require(post.get("note") == ATTESTATION_NOTE, f"{where}: attestation note is not verbatim")


def normalize_artifact_digest(value: str) -> str:
    """upload-artifact emits a bare 64-hex digest; the receipt stores ``sha256:<hex>``."""
    _require(
        HEX64_RE.fullmatch(value) is not None,
        f"artifact digest {value!r} must be the action's bare 64-hex sha256 output",
    )
    return f"sha256:{value}"


def release_receipt(
    *,
    version: str,
    dist: Path,
    sums_path: Path,
    build_receipt_path: Path,
    postpublish_path: Path,
    artifact_id: str,
    artifact_digest: str,
    run_id: str,
    run_attempt: str,
    verify_result: str,
    out: Path,
) -> dict[str, object]:
    parse_version(version)
    distributions = verify_distributions(dist, version, sums_path)
    build = validate_build_receipt(
        _read_json(build_receipt_path, "build receipt"), version, distributions
    )
    post = _read_json(postpublish_path, "post-publication receipt")
    validate_postpublish_receipt(post, version, distributions, official_index=True)
    _require(
        verify_result == "success",
        f"verify matrix result was {verify_result!r}; every cell must succeed",
    )
    _digits(artifact_id, "numeric Actions artifact ID")
    digest = normalize_artifact_digest(artifact_digest)
    _digits(run_id, "run id")
    _digits(run_attempt, "run attempt")
    _require(
        build["run_id"] == run_id,
        f"build receipt belongs to run {build['run_id']}, not this run {run_id}",
    )
    _require(
        int(build["attempt"]) <= int(run_attempt),
        f"build attempt {build['attempt']} is later than verification attempt {run_attempt}",
    )
    runs = f"{GITHUB_RUNS_URL}/{run_id}/attempts/"
    receipt: dict[str, object] = {
        "schema_version": 1,
        "kind": "actseal-release-receipt",
        "version": version,
        "tag": f"v{version}",
        "source_commit": build["source_commit"],
        "lock_sha256": build["lock_sha256"],
        "workflow_run": {
            "id": run_id,
            "build_attempt": build["attempt"],
            "verification_attempt": run_attempt,
            "build_url": runs + build["attempt"],
            "verification_url": runs + run_attempt,
        },
        "artifact": {"id": artifact_id, "digest": digest},
        "distributions": [item.as_dict() for item in distributions],
        "verification": {
            "verify_matrix": verify_result,
            "postpublish": {
                "index": post["index"],
                "published_metadata": post["published_metadata"],
                "files": post["files"],
                "checks": post["checks"],
                "note": post["note"],
            },
        },
        "note": "Contains no credentials.",
    }
    validate_release_receipt(receipt, version, distributions)
    _write_json(out, receipt)
    return receipt


def validate_release_receipt(
    receipt: Mapping[str, Any], version: str, distributions: Sequence[Distribution] | None
) -> list[Distribution]:
    """Typed validation of a release receipt; returns its distribution inventory."""
    where = "release receipt"
    _require_fields(
        receipt,
        {
            "schema_version",
            "kind",
            "version",
            "tag",
            "source_commit",
            "lock_sha256",
            "workflow_run",
            "artifact",
            "distributions",
            "verification",
            "note",
        },
        where,
    )
    _scan_credentials(dict(receipt), where)
    _exact_int(receipt.get("schema_version"), 1, f"{where}: schema_version")
    _require(receipt.get("kind") == "actseal-release-receipt", f"{where}: kind is wrong")
    _require(receipt.get("version") == version, f"{where}: version is not {version}")
    _require(receipt.get("tag") == f"v{version}", f"{where} tag is {receipt.get('tag')!r}")
    commit = receipt.get("source_commit")
    _require(
        isinstance(commit, str) and GIT_SHA_RE.fullmatch(commit) is not None,
        f"{where}: source_commit must be a full 40-hex commit",
    )
    _hex64(receipt.get("lock_sha256"), f"{where} lock_sha256")
    run = _as_dict(receipt.get("workflow_run"), f"{where}: workflow_run")
    _require_fields(
        run,
        {"id", "build_attempt", "verification_attempt", "build_url", "verification_url"},
        f"{where}: workflow_run",
    )
    run_id = _digits(run.get("id"), f"{where} run id")
    build_attempt = _digits(run.get("build_attempt"), f"{where} build attempt")
    verification_attempt = _digits(run.get("verification_attempt"), f"{where} verification attempt")
    _require(
        int(build_attempt) <= int(verification_attempt),
        f"{where}: build attempt later than verification attempt",
    )
    for key, attempt in (("build_url", build_attempt), ("verification_url", verification_attempt)):
        expected_url = f"{GITHUB_RUNS_URL}/{run_id}/attempts/{attempt}"
        _require(
            run.get(key) == expected_url,
            f"{where}: {key} is {run.get(key)!r}, expected {expected_url}",
        )
    artifact = _as_dict(receipt.get("artifact"), f"{where}: artifact")
    _require_fields(artifact, {"id", "digest"}, f"{where}: artifact")
    _digits(artifact.get("id"), f"{where} artifact id")
    digest = artifact.get("digest")
    _require(
        isinstance(digest, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", digest) is not None,
        f"{where}: artifact digest must be sha256:<64 hex>",
    )
    inventory = _distribution_inventory(receipt.get("distributions"), where)
    _require(
        {item.filename for item in inventory} == set(distribution_names(version)),
        f"{where}: distributions must be exactly the wheel and sdist for {version}",
    )
    if distributions is not None:
        _require_same_inventory(distributions, inventory, where)
    verification = _as_dict(receipt.get("verification"), f"{where}: verification")
    _require_fields(verification, {"verify_matrix", "postpublish"}, f"{where}: verification")
    _require(
        verification.get("verify_matrix") == "success", f"{where}: verify matrix is not success"
    )
    post = _as_dict(verification.get("postpublish"), f"{where}: verification.postpublish")
    _require_fields(
        post,
        {"index", "published_metadata", "files", "checks", "note"},
        f"{where}: verification.postpublish",
    )
    embedded = {
        "schema_version": 1,
        "kind": "actseal-postpublish-receipt",
        "version": version,
        "ok": True,
        **post,
    }
    validate_postpublish_receipt(embedded, version, inventory, official_index=True)
    _require(receipt.get("note") == "Contains no credentials.", f"{where}: note is not verbatim")
    return inventory


# --------------------------------------------------------------------------- #
# mirror
# --------------------------------------------------------------------------- #


def _gh(binary: str, *args: str, check: bool = True) -> CommandResult:
    result = _run([binary, *args], cwd=Path.cwd(), env=dict(os.environ))
    if check:
        _require(result.code == 0, f"gh {' '.join(args[:2])} failed: {result.stderr.strip()}")
    return result


def _release_notes(version: str) -> str:
    return (
        f"Draft release for Actseal {version}. Final release notes wait for the real PyPI "
        "recording and receipt review. Distributions are identical to the PyPI upload; "
        "see SHA256SUMS and release-receipt.json.\n"
    )


def mirror(
    *, tag: str, dist: Path, sums_path: Path, receipt_path: Path, gh_binary: str
) -> list[str]:
    """Create or update only a draft release whose assets are byte-identical; never clobber."""
    version = tag.removeprefix("v")
    _require(
        tag == f"v{version}" and VERSION_RE.fullmatch(version) is not None, f"invalid tag {tag!r}"
    )
    distributions = verify_distributions(dist, version, sums_path)
    receipt = _read_json(receipt_path, "release receipt")
    validate_release_receipt(receipt, version, distributions)
    assets = {item.filename: dist / item.filename for item in distributions}
    assets["SHA256SUMS"] = sums_path
    assets["release-receipt.json"] = receipt_path
    view = _gh(gh_binary, "release", "view", tag, "--json", "isDraft,tagName,assets", check=False)
    actions: list[str] = []
    if view.code != 0:
        _require(
            "not found" in view.stderr.lower(), f"gh release view failed: {view.stderr.strip()}"
        )
        notes = dist.parent / f"release-notes-{tag}.md"
        notes.write_text(_release_notes(version), encoding="utf-8")
        _gh(
            gh_binary,
            "release",
            "create",
            tag,
            "--draft",
            "--verify-tag",
            "--title",
            f"Actseal {version}",
            "--notes-file",
            str(notes),
        )
        actions.append(f"created draft release {tag}")
        existing: dict[str, bool] = {}
    else:
        document = json.loads(view.stdout)
        _require(
            document.get("isDraft") is True,
            f"release {tag} is already published; refusing to modify",
        )
        existing = {str(asset.get("name")): True for asset in document.get("assets", [])}
    to_upload: list[str] = []
    for name, path in assets.items():
        if name not in existing:
            to_upload.append(name)
            continue
        scratch = dist.parent / f"mirror-compare-{name}"
        shutil.rmtree(scratch, ignore_errors=True)
        scratch.mkdir()
        _gh(gh_binary, "release", "download", tag, "--pattern", name, "--dir", str(scratch))
        downloaded = scratch / name
        _require(downloaded.is_file(), f"could not download existing asset {name}")
        _require(
            sha256_file(downloaded) == sha256_file(path),
            f"asset {name} already exists with different bytes; refusing to overwrite",
        )
        actions.append(f"asset {name} already identical; skipped")
    if to_upload:
        _gh(gh_binary, "release", "upload", tag, *(str(assets[name]) for name in to_upload))
        actions.extend(f"uploaded {name}" for name in to_upload)
    for action in actions:
        _err(action)
    return actions


# --------------------------------------------------------------------------- #
# docs / candidate / receipts
# --------------------------------------------------------------------------- #


def _collect(checks: Iterable[Callable[[], None]]) -> list[str]:
    failures: list[str] = []
    for check in checks:
        try:
            check()
        except ReleaseCheckError as error:
            failures.append(str(error))
    return failures


def _raise_all(failures: Sequence[str], gate: str) -> None:
    if failures:
        raise ReleaseCheckError(
            f"{gate} gate has {len(failures)} unmet requirement(s):\n  - " + "\n  - ".join(failures)
        )


def _changelog_has_version(root: Path, version: str) -> None:
    path = root / "CHANGELOG.md"
    _require(path.is_file(), "CHANGELOG.md is missing")
    pattern = re.compile(rf"^## \[?v?{re.escape(version)}\]?(\s|$)", re.M)
    _require(
        pattern.search(path.read_text(encoding="utf-8")) is not None,
        f"CHANGELOG.md has no heading for {version}",
    )


def link_targets(text: str) -> list[str]:
    """Every Markdown link/image target plus HTML ``href``, ``src`` and ``srcset`` URLs.

    HTML attributes are matched across lines and inside quoted values, so
    ``<picture>`` markup with ``>`` characters in alt text is handled.
    """
    targets = list(MARKDOWN_LINK_RE.findall(text))
    for match in HTML_ATTRIBUTE_RE.finditer(text):
        attribute = match.group(1).lower()
        value = match.group(2) if match.group(2) is not None else match.group(3)
        if attribute == "srcset":
            targets.extend(
                candidate.strip().split()[0] for candidate in value.split(",") if candidate.strip()
            )
        else:
            targets.append(value.strip())
    return targets


def _document_targets(path: Path) -> list[str]:
    return link_targets(path.read_text(encoding="utf-8"))


def same_repository_path(target: str) -> str | None:
    """The repository-relative path named by an absolute same-repo URL, or ``None``.

    The URL is parsed, so fragments and query strings are ignored and
    percent-encoding in the path is decoded before the local file is checked.
    """
    parsed = urllib.parse.urlsplit(target)
    if parsed.scheme != "https" or parsed.hostname not in GITHUB_FILE_PREFIXES:
        return None
    path = urllib.parse.unquote(parsed.path)
    for prefix in GITHUB_FILE_PREFIXES[parsed.hostname]:
        if path.startswith(prefix) and len(path) > len(prefix):
            return path[len(prefix) :]
    return None


def _local_target(document: Path, target: str) -> Path:
    """Resolve a relative document link: drop fragment/query, decode percent-encoding."""
    parsed = urllib.parse.urlsplit(target)
    return (document.parent / urllib.parse.unquote(parsed.path)).resolve()


def _check_readme_links(root: Path) -> None:
    readme = root / "README.md"
    _require(readme.is_file(), "README.md is missing")
    targets = _document_targets(readme)
    relative = [t for t in targets if not t.startswith("https://")]
    _require(
        not relative,
        f"README.md must use absolute https:// links (PyPI long description): {relative}",
    )
    for target in targets:
        relative_path = same_repository_path(target)
        if relative_path is not None:
            _require(
                ".." not in Path(relative_path).parts and (root / relative_path).is_file(),
                f"README.md links to missing file {relative_path}",
            )


def _check_readme_copy(root: Path) -> None:
    text = (root / "README.md").read_text(encoding="utf-8")
    _require(README_DESCRIPTION in text, "README.md lacks the approved one-sentence description")
    for line in README_QUICKSTART:
        _require(line in text, f"README.md lacks quickstart command {line!r}")
    _require(
        f"{PYPI_BASE_URL}/project/{PROJECT_NAME}/" in text, "README.md lacks the PyPI project link"
    )


def _check_windows_statement(root: Path) -> None:
    candidates = [root / "README.md", *sorted((root / "docs").glob("*.md"))]
    _require(
        any(p.is_file() and "Windows" in p.read_text(encoding="utf-8") for p in candidates),
        "README.md or docs/*.md must state that Windows is unsupported",
    )


def _check_relative_links(root: Path) -> None:
    documents = [
        root / name for name in ("README.md", "CHANGELOG.md", "SECURITY.md", "CONTRIBUTING.md")
    ]
    documents.extend(sorted((root / "docs").rglob("*.md")))
    broken: list[str] = []
    for document in documents:
        if not document.is_file():
            continue
        for target in _document_targets(document):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            if not _local_target(document, target).exists():
                broken.append(f"{document.relative_to(root)} -> {target}")
    _require(not broken, f"broken relative links: {broken}")


def _check_publishing_doc(root: Path) -> None:
    path = root / "docs" / "publishing.md"
    _require(path.is_file(), "docs/publishing.md is missing")
    text = path.read_text(encoding="utf-8")
    for stale in ("-f publish=", "publish=true"):
        _require(stale not in text, f"docs/publishing.md still documents {stale!r}")
    _require("tag" in text, "docs/publishing.md must describe the tag-triggered release")


def _check_required_files(root: Path, names: Iterable[str]) -> None:
    missing = [name for name in names if not (root / name).is_file()]
    _require(not missing, f"missing required files: {missing}")


def check_docs(root: Path) -> None:
    version = agreed_version(root)
    failures = _collect(
        [
            lambda: _check_required_files(root, REQUIRED_DOCS),
            lambda: _check_readme_links(root),
            lambda: _check_readme_copy(root),
            lambda: _check_windows_statement(root),
            lambda: _check_relative_links(root),
            lambda: _check_publishing_doc(root),
            lambda: _changelog_has_version(root, version),
        ]
    )
    _raise_all(failures, "docs")


def png_dimensions(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:PNG_IHDR_END]
    _require(header.startswith(PNG_SIGNATURE), f"{path} is not a PNG file")
    width, height = struct.unpack(">II", header[PNG_IHDR_OFFSET:PNG_IHDR_END])
    return int(width), int(height)


def required_asset_files() -> tuple[str, ...]:
    return tuple(
        f"{ASSET_DIR}/{output}" for outputs in RELEASE_ASSETS.values() for output in outputs
    )


def _check_release_assets(root: Path) -> None:
    _check_required_files(root, required_asset_files())
    for relative in required_asset_files():
        path = root / relative
        if relative.endswith(".svg"):
            _require("<svg" in path.read_text(encoding="utf-8"), f"{relative} is not an SVG")
    size = png_dimensions(root / ASSET_DIR / SOCIAL_PREVIEW_FILE)
    _require(
        size == SOCIAL_PREVIEW_SIZE, f"social preview is {size}, must be {SOCIAL_PREVIEW_SIZE}"
    )


def check_assets(root: Path, renderer: str = DEFAULT_RENDERER) -> None:
    """Required static assets exist and the pinned renderer regenerates them byte-identically.

    A toolchain without implemented renderers fails here: ``--only`` on a planned
    asset is an error in the accepted renderer, and the outputs must exist first.
    """
    _require((root / RENDERER_RELATIVE).is_file(), f"{RENDERER_RELATIVE} is missing")
    _check_release_assets(root)
    argv = [*shlex.split(renderer), "--check"]
    for name in RELEASE_ASSETS:
        argv.extend(("--only", name))
    result = _run(argv, cwd=root, env=_clean_env())
    _require(
        result.code == 0,
        f"asset regeneration check failed (exit {result.code}):\n{result.stdout}{result.stderr}",
    )
    # The accepted renderer reports a planned asset as "[level] name: not implemented".
    _require(
        re.search(r"^\[\w+\] [\w-]+: not implemented", result.stdout, re.M) is None,
        "asset regeneration check reported a required asset as not implemented",
    )


def _check_schemas(root: Path) -> None:
    schemas = root / "docs" / "schemas"
    _require(
        schemas.is_dir() and any(schemas.glob("*.json")), "docs/schemas/ must contain JSON schemas"
    )


def _check_release_version(root: Path) -> None:
    version = agreed_version(root)
    _require(
        parse_version(version)[0] >= 1, f"release candidate version must be >= 1.0.0, not {version}"
    )
    _require(
        STABLE_CLASSIFIER in pyproject_classifiers(root),
        f"pyproject.toml must declare {STABLE_CLASSIFIER!r}",
    )


def _check_clean_tree(root: Path) -> None:
    status = _git(root, "status", "--porcelain")
    _require(status == "", "git working tree must be clean")
    version = agreed_version(root)
    tag = f"v{version}"
    probe = _git_probe(root, "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}^{{commit}}")
    if probe.returncode == 0:
        head = _git(root, "rev-parse", "HEAD")
        _require(probe.stdout.strip() == head, f"tag {tag} exists but does not point at HEAD")


def check_candidate(root: Path, workflow_path: Path, renderer: str = DEFAULT_RENDERER) -> None:
    failures = _collect(
        [
            lambda: _check_release_version(root),
            lambda: check_workflow(workflow_path),
            lambda: check_docs(root),
            lambda: _changelog_has_version(root, agreed_version(root)),
            lambda: _check_required_files(
                root, ("docs/stability.md", "docs/versioning.md", "docs/migration.md")
            ),
            lambda: _check_schemas(root),
            lambda: check_assets(root, renderer),
            lambda: _check_clean_tree(root),
        ]
    )
    _raise_all(failures, "candidate")


def _check_receipt_documents(root: Path, version: str) -> None:
    receipt = _read_json(root / RECEIPT_PATHS["release_receipt"], "release receipt")
    post = _read_json(root / RECEIPT_PATHS["postpublish"], "post-publication receipt")
    inventory = validate_release_receipt(receipt, version, None)
    validate_postpublish_receipt(post, version, inventory, official_index=True)
    sums = read_sha256sums(root / RECEIPT_PATHS["sha256sums"])
    recorded = {item.filename: item.sha256 for item in inventory}
    _require(sums == recorded, "SHA256SUMS receipt differs from release receipt distributions")


def _check_release_notes(root: Path, version: str) -> None:
    notes_path = root / RECEIPT_PATHS["release_notes"]
    _require(notes_path.is_file(), f"{RECEIPT_PATHS['release_notes']} is missing")
    notes = notes_path.read_text(encoding="utf-8")
    receipt_text = (root / RECEIPT_PATHS["release_receipt"]).read_text(encoding="utf-8")
    post_text = (root / RECEIPT_PATHS["postpublish"]).read_text(encoding="utf-8")
    receipt = _read_json(root / RECEIPT_PATHS["release_receipt"], "release receipt")
    for distribution in receipt.get("distributions", []):
        for key in ("filename", "sha256"):
            _require(
                str(distribution.get(key)) in notes, f"release notes omit {distribution.get(key)}"
            )
    _require(
        f"{PYPI_BASE_URL}/project/{PROJECT_NAME}/{version}/" in notes,
        "release notes lack the PyPI link",
    )
    _require("how-it-works" in notes, "release notes must include the how-it-works figure")
    unmapped = [
        h for h in SHA256_HEX_RE.findall(notes) if h not in receipt_text and h not in post_text
    ]
    _require(not unmapped, f"release notes claim hashes absent from receipts: {unmapped}")
    run_id = str(receipt.get("workflow_run", {}).get("id"))
    _require(run_id.isdigit(), "release receipt lacks a numeric workflow run id")
    final_report = root / RECEIPT_PATHS["final_report"]
    _require(final_report.is_file(), f"{RECEIPT_PATHS['final_report']} is missing")
    _require(
        run_id in final_report.read_text(encoding="utf-8"), "final report omits the workflow run id"
    )
    launch = root / RECEIPT_PATHS["launch"]
    _require(launch.is_file(), f"{RECEIPT_PATHS['launch']} is missing")
    _require(
        "draft" in launch.read_text(encoding="utf-8").lower(), "launch post must remain a draft"
    )


def check_receipts(root: Path) -> None:
    version = agreed_version(root)
    failures = _collect(
        [
            lambda: _check_required_files(root, RECEIPT_PATHS.values()),
            lambda: _check_receipt_documents(root, version),
            lambda: _check_release_notes(root, version),
        ]
    )
    _raise_all(failures, "receipts")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="check_release.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="repository root")
    commands = parser.add_subparsers(dest="command", required=True)

    workflow = commands.add_parser("workflow")
    workflow.add_argument("--path", type=Path)

    metadata = commands.add_parser("metadata")
    metadata.add_argument("--ref")
    metadata.add_argument("--sha")

    distributions = commands.add_parser("distributions")
    distributions.add_argument("directory", type=Path)
    distributions.add_argument("--version", required=True)
    distributions.add_argument("--ref")
    distributions.add_argument("--sha")
    distributions.add_argument("--run-id")
    distributions.add_argument("--run-attempt")
    distributions.add_argument("--sha256sums", type=Path)
    distributions.add_argument("--build-receipt", type=Path)

    verify = commands.add_parser("verify-distributions")
    verify.add_argument("directory", type=Path)
    verify.add_argument("--version", required=True)
    verify.add_argument("--sha256sums", type=Path, required=True)

    post = commands.add_parser("postpublish")
    post.add_argument("--version", required=True)
    post.add_argument("--sha256sums", type=Path, required=True)
    post.add_argument("--workdir", type=Path, required=True)
    post.add_argument("--out", type=Path, required=True)
    post.add_argument("--checkout", type=Path)
    post.add_argument("--pypi-base-url", default=PYPI_BASE_URL)
    post.add_argument("--wait-seconds", type=float, default=600.0)
    post.add_argument("--python", default=sys.executable)
    post.add_argument("--allow-missing-attestations", action="store_true")

    receipt = commands.add_parser("release-receipt")
    receipt.add_argument("--version", required=True)
    receipt.add_argument("--dist", type=Path, required=True)
    receipt.add_argument("--sha256sums", type=Path, required=True)
    receipt.add_argument("--build-receipt", type=Path, required=True)
    receipt.add_argument("--postpublish", type=Path, required=True)
    receipt.add_argument("--artifact-id", required=True)
    receipt.add_argument("--artifact-digest", required=True)
    receipt.add_argument("--run-id", required=True)
    receipt.add_argument("--run-attempt", required=True)
    receipt.add_argument("--verify-result", required=True)
    receipt.add_argument("--out", type=Path, required=True)

    mirror_parser = commands.add_parser("mirror")
    mirror_parser.add_argument("--tag", required=True)
    mirror_parser.add_argument("--dist", type=Path, required=True)
    mirror_parser.add_argument("--sha256sums", type=Path, required=True)
    mirror_parser.add_argument("--release-receipt", type=Path, required=True)
    mirror_parser.add_argument("--gh", default="gh")

    for name in ("candidate", "assets"):
        gate = commands.add_parser(name)
        gate.add_argument(
            "--renderer",
            default=DEFAULT_RENDERER,
            help="command prefix that runs render.py (default: %(default)s)",
        )
    for name in ("docs", "receipts"):
        commands.add_parser(name)
    return parser


def _dispatch(args: argparse.Namespace) -> None:
    root: Path = args.root.resolve()
    workflow_path = root / WORKFLOW_RELATIVE
    if args.command == "workflow":
        check_workflow(args.path if args.path is not None else workflow_path)
    elif args.command == "metadata":
        identity = check_metadata(root, ref=args.ref, sha=args.sha)
        _out(f"version={identity.version}")
        _out(f"release={'true' if identity.release else 'false'}")
    elif args.command == "distributions":
        _run_distributions(root, args)
    elif args.command == "verify-distributions":
        verify_distributions(args.directory, args.version, args.sha256sums)
    elif args.command == "postpublish":
        postpublish(
            version=args.version,
            sums_path=args.sha256sums,
            workdir=args.workdir,
            out=args.out,
            checkout=args.checkout,
            base_url=args.pypi_base_url,
            wait_seconds=args.wait_seconds,
            python=args.python,
            allow_missing_attestations=args.allow_missing_attestations,
        )
    elif args.command == "release-receipt":
        release_receipt(
            version=args.version,
            dist=args.dist,
            sums_path=args.sha256sums,
            build_receipt_path=args.build_receipt,
            postpublish_path=args.postpublish,
            artifact_id=args.artifact_id,
            artifact_digest=args.artifact_digest,
            run_id=args.run_id,
            run_attempt=args.run_attempt,
            verify_result=args.verify_result,
            out=args.out,
        )
    elif args.command == "mirror":
        mirror(
            tag=args.tag,
            dist=args.dist,
            sums_path=args.sha256sums,
            receipt_path=args.release_receipt,
            gh_binary=args.gh,
        )
    elif args.command == "candidate":
        check_candidate(root, workflow_path, args.renderer)
    elif args.command == "assets":
        check_assets(root, args.renderer)
    elif args.command == "docs":
        check_docs(root)
    else:
        check_receipts(root)


def _run_distributions(root: Path, args: argparse.Namespace) -> None:
    parse_version(args.version)
    distributions = inspect_distributions(args.directory, args.version)
    if args.sha256sums is not None:
        write_sha256sums(args.sha256sums, {d.filename: d.sha256 for d in distributions})
    if args.build_receipt is not None:
        receipt = build_receipt(
            root,
            distributions,
            version=args.version,
            ref=args.ref,
            sha=args.sha,
            run_id=args.run_id,
            run_attempt=args.run_attempt,
        )
        _write_json(args.build_receipt, receipt)
    wheel, sdist = distribution_names(args.version)
    _out(f"wheel={wheel}")
    _out(f"sdist={sdist}")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        _dispatch(args)
    except ReleaseCheckError as error:
        _err(f"release check failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
