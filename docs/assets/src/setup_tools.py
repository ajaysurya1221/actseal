"""Fetch pinned authoring tools and fonts with SHA-256 verification.

    uv run --frozen python docs/assets/src/setup_tools.py [--tool NAME ...] [--cache DIR]

This is explicit setup, separate from unit tests, and the only place in the
toolchain that touches the network. Fonts and the upstream font notice are
placed under ``docs/assets/src/fonts``; binaries go to the cache directory
(``ACTSEAL_ASSET_TOOLS`` or ``~/.cache/actseal-assets``) and are never
committed. Archives are retained beside their extracted member so later
verification can re-derive the executable from the pinned bytes. A receipt
per tool and platform is written under ``docs/assets/src/receipts`` with the
verified hashes and source URLs only; receipts are records, not trust anchors.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import stat
import sys
import urllib.request
from collections.abc import Sequence
from pathlib import Path

from actseal_assets import tools
from actseal_assets.inventory import FONT_DIR

DOWNLOAD_TIMEOUT = 120
MAX_DOWNLOAD_BYTES = 64 * 1024 * 1024


def repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def download(url: str) -> bytes:
    if not url.startswith("https://"):
        msg = f"refusing non-https download {url}"
        raise tools.ToolError(msg)
    request = urllib.request.Request(url, headers={"User-Agent": "actseal-assets-setup"})  # noqa: S310 - https enforced above
    try:
        with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response:  # noqa: S310 - https enforced above
            data = bytes(response.read(MAX_DOWNLOAD_BYTES + 1))
    except OSError as exc:
        msg = f"download failed for {url}: {exc}"
        raise tools.ToolError(msg) from exc
    if len(data) > MAX_DOWNLOAD_BYTES:
        msg = f"download exceeds {MAX_DOWNLOAD_BYTES} bytes: {url}"
        raise tools.ToolError(msg)
    return data


def verify(data: bytes, artifact: tools.Artifact) -> str:
    actual = tools.sha256_bytes(data)
    if artifact.verify == "sha256" and actual != artifact.sha256:
        msg = (
            f"{artifact.filename}: downloaded sha256 {actual} does not match "
            f"pinned {artifact.sha256}; nothing was installed"
        )
        raise tools.ToolError(msg)
    return actual


def install_binary(tool: tools.Tool, artifact: tools.Artifact, data: bytes) -> dict[str, object]:
    """Install a verified download; archives are retained beside their member."""
    target = tools.cached_binary_path(tool, artifact)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = data
    record: dict[str, object] = {
        "filename": artifact.filename,
        "url": artifact.url,
        "sha256": tools.sha256_bytes(data),
    }
    if artifact.member is not None:
        payload = tools.extract_member(data, artifact.filename, artifact.member)
        archive = tools.cached_archive_path(tool, artifact)
        archive.write_bytes(data)
        record["archive_sha256"] = record["sha256"]
        record["archive_retained"] = str(archive)
        record["extracted_sha256"] = tools.sha256_bytes(payload)
    target.write_bytes(payload)
    target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    record["installed"] = str(target)
    return record


def install_font_file(root: Path, artifact: tools.Artifact, data: bytes) -> dict[str, object]:
    target = root / FONT_DIR / artifact.filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return {
        "filename": artifact.filename,
        "url": artifact.url,
        "sha256": tools.sha256_bytes(data),
        "installed": (Path(FONT_DIR) / artifact.filename).as_posix(),
    }


def write_receipt(
    root: Path, tool: tools.Tool, platform_name: str, body: dict[str, object]
) -> Path:
    path = tools.receipt_path(root, tool, platform_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    receipt: dict[str, object] = {
        "tool": tool.name,
        "version": tool.version,
        "license": tool.license,
        "source_url": tool.source_url,
        "source_commit": tool.source_commit,
        "platform": platform_name,
        "retrieved": dt.datetime.now(dt.UTC).date().isoformat(),
        **body,
    }
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def setup_tool(root: Path, tool: tools.Tool, platform_name: str) -> list[str]:
    """Fetch one tool; returns human-readable lines. Raises ToolError on any failure."""
    if tool.kind == "python":
        problems = tools.check_lock_pin(root, tool)
        if problems:
            raise tools.ToolError("; ".join(problems))
        return [f"{tool.name} {tool.version}: pinned in uv.lock; install with --group assets"]
    if tool.kind == "font":
        records = []
        for artifact in tool.artifacts:
            data = download(artifact.url)
            verify(data, artifact)
            records.append(install_font_file(root, artifact, data))
        receipt = write_receipt(root, tool, "any", {"files": records})
        return [f"{tool.name} {tool.version}: {len(records)} file(s) installed; receipt {receipt}"]
    binary = tool.artifact_for(platform_name)
    if binary is None:
        msg = f"{tool.name} {tool.version}: no pinned artifact for platform {platform_name}"
        raise tools.ToolError(msg)
    data = download(binary.url)
    verify(data, binary)
    record = install_binary(tool, binary, data)
    receipt = write_receipt(root, tool, platform_name, record)
    verified = tools.verified_binary(root, tool, platform_name)
    return [f"{tool.name} {tool.version}: installed {verified}; receipt {receipt}"]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="setup_tools.py", description="Fetch pinned authoring tools with hash verification."
    )
    parser.add_argument("--tool", action="append", default=[], metavar="NAME")
    parser.add_argument("--root", type=Path, default=None, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = args.root or repository_root()
    try:
        manifest = tools.load_manifest(tools.default_manifest_path(root))
    except tools.ToolError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 1
    problems = tools.validate_manifest(manifest)
    if problems:
        sys.stderr.write("error: manifest invalid:\n" + "\n".join(problems) + "\n")
        return 1
    selected = args.tool or list(manifest)
    unknown = [name for name in selected if name not in manifest]
    if unknown:
        sys.stderr.write(f"error: unknown tool(s): {', '.join(unknown)}\n")
        return 2
    platform_name = tools.platform_key()
    status = 0
    for name in selected:
        try:
            lines = setup_tool(root, manifest[name], platform_name)
        except tools.ToolError as exc:
            sys.stderr.write(f"error: {exc}\n")
            status = 1
            continue
        sys.stdout.write("\n".join(lines) + "\n")
    return status


if __name__ == "__main__":
    sys.exit(main())
