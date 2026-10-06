"""README and docs image-reference validation.

Every local image reference in ``README.md`` and ``docs/*.md`` must point at a
declared asset output that exists, and Markdown/HTML images must carry alt
text. Remote badges are ignored. Files under ``docs/assets`` that no asset
declares are reported as orphans.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .inventory import ASSET_DIR, Asset

MARKDOWN_IMAGE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<target>[^)\s]+)(?:\s+\"[^\"]*\")?\)")
HTML_TAG = re.compile(r"<(?P<tag>img|source)\b(?P<body>[^>]*)>", re.IGNORECASE)
HTML_ATTR = re.compile(r"(?P<key>[a-zA-Z-]+)\s*=\s*\"(?P<value>[^\"]*)\"")
SCAN_FILES = ("README.md",)
SCAN_GLOBS = ("docs/*.md",)


@dataclass(frozen=True, slots=True)
class Reference:
    file: str
    line: int
    target: str
    alt: str | None


def _is_remote(target: str) -> bool:
    lowered = target.lower()
    return "://" in lowered or lowered.startswith(("data:", "//", "#", "mailto:"))


def _scan_text(file: str, text: str) -> list[Reference]:
    refs: list[Reference] = []
    for number, line in enumerate(text.split("\n"), start=1):
        refs.extend(
            Reference(file, number, match.group("target"), match.group("alt"))
            for match in MARKDOWN_IMAGE.finditer(line)
        )
        for match in HTML_TAG.finditer(line):
            attrs = {key.lower(): value for key, value in HTML_ATTR.findall(match.group("body"))}
            tag = match.group("tag").lower()
            if tag == "img":
                if "src" in attrs:
                    refs.append(Reference(file, number, attrs["src"], attrs.get("alt")))
            elif "srcset" in attrs:
                refs.extend(
                    Reference(file, number, candidate.split()[0], None)
                    for candidate in attrs["srcset"].split(",")
                    if candidate.strip()
                )
    return refs


def scan_files(root: Path) -> list[Path]:
    files = [root / name for name in SCAN_FILES if (root / name).is_file()]
    for pattern in SCAN_GLOBS:
        files.extend(sorted(path for path in root.glob(pattern) if path.is_file()))
    return files


def scan_references(root: Path) -> list[Reference]:
    refs: list[Reference] = []
    for path in scan_files(root):
        relative = path.relative_to(root).as_posix()
        refs.extend(_scan_text(relative, path.read_text(encoding="utf-8")))
    return refs


def declared_outputs(assets: tuple[Asset, ...]) -> dict[str, Asset]:
    return {output.path: asset for asset in assets for output in asset.outputs}


def check_references(root: Path, assets: tuple[Asset, ...]) -> tuple[list[str], int]:
    """Return (errors, number of local references checked)."""
    outputs = declared_outputs(assets)
    asset_dir = (root / ASSET_DIR).resolve()
    errors: list[str] = []
    checked = 0
    for ref in scan_references(root):
        if _is_remote(ref.target):
            continue
        checked += 1
        where = f"{ref.file}:{ref.line}"
        if ref.alt is not None and not ref.alt.strip():
            errors.append(f"{where}: image {ref.target!r} has empty alt text")
        target = (root / ref.file).parent / ref.target.split("#")[0]
        resolved = target.resolve()
        if not resolved.is_file():
            errors.append(f"{where}: {ref.target!r} does not exist")
            continue
        if asset_dir not in resolved.parents:
            errors.append(f"{where}: {ref.target!r} is outside {ASSET_DIR}")
            continue
        name = resolved.relative_to(asset_dir).as_posix()
        if name not in outputs:
            errors.append(f"{where}: {ref.target!r} is not a declared asset output")
    return errors, checked


def check_orphans(root: Path, assets: tuple[Asset, ...]) -> list[str]:
    """Files directly under docs/assets (excluding src/) must be declared outputs."""
    asset_dir = root / ASSET_DIR
    if not asset_dir.is_dir():
        return []
    outputs = declared_outputs(assets)
    errors: list[str] = []
    for path in sorted(asset_dir.rglob("*")):
        relative = path.relative_to(asset_dir).as_posix()
        if relative == "src" or relative.startswith("src/") or path.is_dir():
            continue
        if path.name.startswith("."):
            continue
        if relative not in outputs:
            errors.append(f"{ASSET_DIR}/{relative} is not declared by any asset")
    return errors
