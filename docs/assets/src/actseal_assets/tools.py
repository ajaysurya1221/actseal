"""Pinned authoring tools: manifest, hashing, verified execution.

``tools.toml`` records every authoring pin with its license, source commit and
per-platform SHA-256. Binaries live in a cache outside the repository; the
cache path comes from ``ACTSEAL_ASSET_TOOLS`` or defaults to
``~/.cache/actseal-assets``. ``verified_binary`` re-hashes a cached tool
against the pin every time, before anything executes it. fontTools is never
downloaded here: its pin is checked against the committed ``uv.lock``.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import re
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .inventory import FONT_DIR, MANIFEST_FILE, RECEIPT_DIR

CACHE_ENV = "ACTSEAL_ASSET_TOOLS"
DEFAULT_CACHE = Path("~/.cache/actseal-assets")
TOOL_TIMEOUT_SECONDS = 300
PLATFORMS = frozenset({"any", "darwin-arm64", "linux-x86_64"})
KINDS = frozenset({"python", "binary", "font"})
VERIFY_MODES = frozenset({"sha256", "receipt"})
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
FONT_LICENSE_FILE = "OFL.txt"
FONT_LICENSE_MARKERS = ("SIL OPEN FONT LICENSE Version 1.1", "JetBrains Mono")
FONT_FAMILY = "JetBrains Mono"


class ToolError(RuntimeError):
    """A pinned tool is missing, unverified or failed."""


@dataclass(frozen=True, slots=True)
class Artifact:
    platform: str
    url: str
    filename: str
    sha256: str
    verify: str = "sha256"
    member: str | None = None


@dataclass(frozen=True, slots=True)
class Tool:
    name: str
    version: str
    license: str
    license_url: str
    source_url: str
    source_commit: str
    kind: str
    purpose: str
    artifacts: tuple[Artifact, ...]

    def artifact_for(self, platform_key: str) -> Artifact | None:
        for artifact in self.artifacts:
            if artifact.platform in {platform_key, "any"}:
                return artifact
        return None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def platform_key() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    arch = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "x86_64", "amd64": "x86_64"}.get(
        machine, machine
    )
    return f"{system}-{arch}"


def cache_dir() -> Path:
    override = os.environ.get(CACHE_ENV)
    return Path(override).expanduser() if override else DEFAULT_CACHE.expanduser()


def _string(table: dict[str, object], key: str, where: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value:
        msg = f"{where}: {key} must be a non-empty string"
        raise ToolError(msg)
    return value


def _artifact(table: dict[str, object], where: str) -> Artifact:
    member = table.get("member")
    if member is not None and not isinstance(member, str):
        msg = f"{where}: member must be a string"
        raise ToolError(msg)
    verify = table.get("verify", "sha256")
    if not isinstance(verify, str):
        msg = f"{where}: verify must be a string"
        raise ToolError(msg)
    sha = table.get("sha256", "")
    if not isinstance(sha, str):
        msg = f"{where}: sha256 must be a string"
        raise ToolError(msg)
    return Artifact(
        platform=_string(table, "platform", where),
        url=_string(table, "url", where),
        filename=_string(table, "filename", where),
        sha256=sha,
        verify=verify,
        member=member,
    )


def load_manifest(path: Path) -> dict[str, Tool]:
    """Parse ``tools.toml``; raises ToolError on structural problems."""
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        msg = f"cannot read manifest {path}: {exc}"
        raise ToolError(msg) from exc
    tools: dict[str, Tool] = {}
    for name, table in raw.items():
        if not isinstance(table, dict):
            msg = f"{name}: manifest entry must be a table"
            raise ToolError(msg)
        entries = table.get("artifacts", [])
        if not isinstance(entries, list):
            msg = f"{name}: artifacts must be an array of tables"
            raise ToolError(msg)
        artifacts = tuple(
            _artifact(entry, f"{name}.artifacts[{index}]")
            for index, entry in enumerate(entries)
            if isinstance(entry, dict)
        )
        commit = table.get("source_commit", "")
        if not isinstance(commit, str):
            msg = f"{name}: source_commit must be a string"
            raise ToolError(msg)
        tools[name] = Tool(
            name=name,
            version=_string(table, "version", name),
            license=_string(table, "license", name),
            license_url=_string(table, "license_url", name),
            source_url=_string(table, "source_url", name),
            source_commit=commit,
            kind=_string(table, "kind", name),
            purpose=_string(table, "purpose", name),
            artifacts=artifacts,
        )
    return tools


def validate_manifest(tools: dict[str, Tool]) -> list[str]:
    errors: list[str] = []
    for name, tool in tools.items():
        if tool.kind not in KINDS:
            errors.append(f"{name}: unknown kind {tool.kind!r}")
        if tool.kind != "python" and not _HEX40.match(tool.source_commit):
            errors.append(f"{name}: source_commit is not a 40-hex commit")
        if not tool.license_url.startswith("https://"):
            errors.append(f"{name}: license_url must be https")
        if not tool.artifacts:
            errors.append(f"{name}: declares no artifacts")
        for artifact in tool.artifacts:
            where = f"{name}/{artifact.filename}"
            if artifact.platform not in PLATFORMS:
                errors.append(f"{where}: unknown platform {artifact.platform!r}")
            if not artifact.url.startswith("https://"):
                errors.append(f"{where}: url must be https")
            if artifact.verify not in VERIFY_MODES:
                errors.append(f"{where}: unknown verify mode {artifact.verify!r}")
            if artifact.verify == "sha256" and not _HEX64.match(artifact.sha256):
                errors.append(f"{where}: sha256 is not 64 lowercase hex characters")
            if artifact.verify == "receipt" and artifact.sha256:
                errors.append(f"{where}: receipt-verified artifacts must not pin sha256")
    return errors


def check_lock_pin(root: Path, tool: Tool) -> list[str]:
    """The committed uv.lock must carry the same universal-wheel hash as the manifest."""
    lock = root / "uv.lock"
    if not lock.is_file():
        return ["uv.lock is missing"]
    text = lock.read_text(encoding="utf-8")
    errors: list[str] = []
    for artifact in tool.artifacts:
        needle = f'{artifact.filename}", hash = "sha256:{artifact.sha256}"'
        if needle not in text:
            errors.append(
                f"uv.lock does not pin {artifact.filename} at sha256 {artifact.sha256[:12]}…"
            )
    return errors


def receipt_path(root: Path, tool: Tool, platform_name: str) -> Path:
    return root / RECEIPT_DIR / f"{tool.name}-{platform_name}.json"


def load_receipt(path: Path) -> dict[str, object]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        msg = f"cannot read receipt {path}: {exc}"
        raise ToolError(msg) from exc
    if not isinstance(data, dict):
        msg = f"receipt {path} is not a JSON object"
        raise ToolError(msg)
    return data


def cached_binary_path(tool: Tool, artifact: Artifact) -> Path:
    name = artifact.member or artifact.filename
    return cache_dir() / f"{tool.name}-{tool.version}" / Path(name).name


def verified_binary(root: Path, tool: Tool, platform_name: str | None = None) -> Path:
    """Return the cached binary after re-verifying its SHA-256 against the pin.

    Direct downloads are compared with the manifest. Archive members are
    compared with the extraction hash in the setup receipt, whose archive hash
    must in turn match the manifest pin.
    """
    if tool.kind != "binary":
        msg = f"{tool.name} is not a binary tool"
        raise ToolError(msg)
    key = platform_name or platform_key()
    artifact = tool.artifact_for(key)
    if artifact is None:
        msg = f"{tool.name} {tool.version}: no pinned artifact for platform {key}"
        raise ToolError(msg)
    path = cached_binary_path(tool, artifact)
    if not path.is_file():
        msg = f"{tool.name} {tool.version} is not cached at {path}; run setup_tools.py"
        raise ToolError(msg)
    actual = sha256_path(path)
    expected = artifact.sha256
    if artifact.member is not None:
        receipt = load_receipt(receipt_path(root, tool, key))
        if receipt.get("archive_sha256") != artifact.sha256:
            msg = f"{tool.name}: receipt archive hash does not match the manifest pin"
            raise ToolError(msg)
        extracted = receipt.get("extracted_sha256")
        if not isinstance(extracted, str):
            msg = f"{tool.name}: receipt lacks extracted_sha256"
            raise ToolError(msg)
        expected = extracted
    if actual != expected:
        msg = f"{tool.name} at {path}: sha256 {actual[:12]}… does not match pinned {expected[:12]}…"
        raise ToolError(msg)
    return path


def font_paths(root: Path, tool: Tool) -> list[Path]:
    return [root / FONT_DIR / artifact.filename for artifact in tool.artifacts]


def check_fonts(root: Path, tool: Tool) -> tuple[list[str], bool]:
    """Return (errors, present).

    ``present`` is False when no font file has been fetched yet, which is an
    informational state until an implemented asset needs the font. Once any
    font file exists, every pinned file, its hash and the upstream license
    notice must be present.
    """
    font_dir = root / FONT_DIR
    files = [artifact for artifact in tool.artifacts if artifact.verify == "sha256"]
    existing = [artifact for artifact in files if (font_dir / artifact.filename).is_file()]
    if not existing:
        return [], False
    errors: list[str] = []
    for artifact in files:
        path = font_dir / artifact.filename
        if not path.is_file():
            errors.append(f"{FONT_DIR}/{artifact.filename} is missing")
            continue
        actual = sha256_path(path)
        if actual != artifact.sha256:
            errors.append(f"{FONT_DIR}/{artifact.filename}: sha256 does not match the pin")
    errors.extend(check_font_license(root))
    return errors, True


def check_font_license(root: Path) -> list[str]:
    path = root / FONT_DIR / FONT_LICENSE_FILE
    if not path.is_file():
        return [f"{FONT_DIR}/{FONT_LICENSE_FILE} (upstream font notice) is missing"]
    text = path.read_text(encoding="utf-8", errors="replace")
    return [
        f"{FONT_DIR}/{FONT_LICENSE_FILE} lacks {marker!r}"
        for marker in FONT_LICENSE_MARKERS
        if marker not in text
    ]


def agg_command(
    agg: Path,
    cast: Path,
    gif: Path,
    *,
    duration_seconds: float,
    font_dir: Path,
    extra: tuple[str, ...] = (),
) -> list[str]:
    """Build the agg invocation: speed 1 and an idle limit longer than the whole cast."""
    if not math.isfinite(duration_seconds) or duration_seconds <= 0:
        msg = f"recording duration must be positive, got {duration_seconds!r}"
        raise ToolError(msg)
    idle_limit = math.ceil(duration_seconds) + 1
    return [
        str(agg),
        "--speed",
        "1",
        "--idle-time-limit",
        str(idle_limit),
        "--font-dir",
        str(font_dir),
        "--font-family",
        FONT_FAMILY,
        *extra,
        str(cast),
        str(gif),
    ]


def resvg_command(
    resvg: Path,
    svg: Path,
    png: Path,
    *,
    width: int,
    height: int,
    font_dir: Path,
) -> list[str]:
    """Build the resvg invocation with explicit size and only the pinned fonts."""
    return [
        str(resvg),
        "--width",
        str(width),
        "--height",
        str(height),
        "--use-fonts-dir",
        str(font_dir),
        "--skip-system-fonts",
        str(svg),
        str(png),
    ]


def run_tool(
    command: list[str],
    *,
    cwd: Path | None = None,
    timeout: float = TOOL_TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess[bytes]:
    """Run a verified tool with a hard timeout; failures raise ToolError."""
    try:
        result = subprocess.run(  # noqa: S603 - hash-verified binary, argument list built here
            command,
            cwd=cwd,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        msg = f"{command[0]} failed to run: {exc}"
        raise ToolError(msg) from exc
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()[-500:]
        msg = f"{command[0]} exited {result.returncode}: {detail}"
        raise ToolError(msg)
    return result


def default_manifest_path(root: Path) -> Path:
    return root / MANIFEST_FILE
