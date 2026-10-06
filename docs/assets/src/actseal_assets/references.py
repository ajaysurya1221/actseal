"""README and docs image-reference validation.

Every image reference in ``README.md`` and ``docs/*.md`` is classified:

- ``local`` relative paths and ``same-repo`` absolute GitHub/raw URLs for this
  repository are mapped to a path under ``docs/assets`` that must exist, be a
  declared output and belong to an implemented asset;
- ``badge`` URLs from an explicit allowlist are exempt;
- any other absolute URL is an error, because an external image is a silent
  false pass that nothing here can validate offline.

Markdown images and HTML ``<img>`` (double-quoted, single-quoted or unquoted
attributes, possibly spanning lines) must carry non-empty alt text;
``<source srcset>`` entries are checked for their target only. Validation
never touches the network. Files under ``docs/assets`` that no asset declares
are reported as orphans.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .inventory import ASSET_DIR, Asset

REPO_SLUG = "ajaysurya1221/actseal"

MARKDOWN_IMAGE = re.compile(
    r"!\[(?P<alt>[^\]]*)\]\(\s*(?P<target>[^)\s]+)(?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*\)"
)
HTML_TAG = re.compile(r"<(?P<tag>img|source)\b(?P<body>[^>]*)>", re.IGNORECASE | re.DOTALL)
HTML_ATTR = re.compile(
    r"(?P<key>[A-Za-z-]+)\s*=\s*(?:\"(?P<dq>[^\"]*)\"|'(?P<sq>[^']*)'|(?P<uq>[^\s\"'>]+))",
    re.DOTALL,
)
SAME_REPO_URLS = tuple(
    re.compile(pattern)
    for pattern in (
        rf"^https://raw\.githubusercontent\.com/{re.escape(REPO_SLUG)}/[^/]+/(?P<path>[^?#]+)",
        rf"^https://github\.com/{re.escape(REPO_SLUG)}/(?:blob|raw)/[^/]+/(?P<path>[^?#]+)",
    )
)
BADGE_URLS = tuple(
    re.compile(pattern)
    for pattern in (
        r"^https://img\.shields\.io/",
        rf"^https://github\.com/{re.escape(REPO_SLUG)}/actions/workflows/[^/]+/badge\.svg",
        r"^https://results\.pre-commit\.ci/badge/",
    )
)
SCAN_FILES = ("README.md",)
SCAN_GLOBS = ("docs/*.md",)

LOCAL = "local"
SAME_REPO = "same-repo"
BADGE = "badge"
EXTERNAL = "external"


@dataclass(frozen=True, slots=True)
class Reference:
    file: str
    line: int
    target: str
    alt: str | None
    needs_alt: bool

    @property
    def kind(self) -> str:
        return classify(self.target)

    @property
    def repo_path(self) -> str | None:
        """Repository-relative path for a same-repo absolute URL."""
        for pattern in SAME_REPO_URLS:
            match = pattern.match(self.target)
            if match:
                return match.group("path")
        return None


def classify(target: str) -> str:
    lowered = target.lower()
    if any(pattern.match(target) for pattern in SAME_REPO_URLS):
        return SAME_REPO
    if any(pattern.match(target) for pattern in BADGE_URLS):
        return BADGE
    if "://" in lowered or lowered.startswith(("//", "data:", "mailto:")):
        return EXTERNAL
    return LOCAL


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _attrs(body: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for match in HTML_ATTR.finditer(body):
        value = match.group("dq")
        if value is None:
            value = match.group("sq")
        if value is None:
            value = match.group("uq")
        attrs[match.group("key").lower()] = value or ""
    return attrs


def _scan_text(file: str, text: str) -> list[Reference]:
    found: list[tuple[int, int, Reference]] = []
    for match in MARKDOWN_IMAGE.finditer(text):
        line = _line_of(text, match.start())
        ref = Reference(file, line, match.group("target"), match.group("alt"), needs_alt=True)
        found.append((match.start(), 0, ref))
    for match in HTML_TAG.finditer(text):
        line = _line_of(text, match.start())
        attrs = _attrs(match.group("body"))
        tag = match.group("tag").lower()
        if tag == "img":
            if "src" in attrs:
                ref = Reference(file, line, attrs["src"], attrs.get("alt"), needs_alt=True)
                found.append((match.start(), 0, ref))
        elif "srcset" in attrs:
            for order, candidate in enumerate(attrs["srcset"].split(",")):
                parts = candidate.split()
                if parts:
                    ref = Reference(file, line, parts[0], None, needs_alt=False)
                    found.append((match.start(), order, ref))
    return [ref for _, _, ref in sorted(found, key=lambda item: (item[0], item[1]))]


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


def _check_target(
    root: Path, ref: Reference, target: Path, outputs: dict[str, Asset], where: str
) -> str | None:
    asset_dir = (root / ASSET_DIR).resolve()
    resolved = target.resolve()
    if not resolved.is_file():
        return f"{where}: {ref.target!r} does not exist"
    if asset_dir not in resolved.parents:
        return f"{where}: {ref.target!r} is outside {ASSET_DIR}"
    name = resolved.relative_to(asset_dir).as_posix()
    asset = outputs.get(name)
    if asset is None:
        return f"{where}: {ref.target!r} is not a declared asset output"
    if not asset.implemented:
        return (
            f"{where}: {ref.target!r} belongs to unimplemented asset {asset.name!r} "
            f"(planned in Task {asset.task})"
        )
    return None


def check_references(root: Path, assets: tuple[Asset, ...]) -> tuple[list[str], int]:
    """Return (errors, number of non-badge references checked)."""
    outputs = declared_outputs(assets)
    errors: list[str] = []
    checked = 0
    for ref in scan_references(root):
        kind = ref.kind
        if kind == BADGE:
            continue
        checked += 1
        where = f"{ref.file}:{ref.line}"
        if ref.needs_alt and not (ref.alt or "").strip():
            errors.append(f"{where}: image {ref.target!r} has no alt text")
        if kind == EXTERNAL:
            errors.append(f"{where}: {ref.target!r} is an external image, not a recognized badge")
            continue
        if kind == SAME_REPO:
            repo_path = ref.repo_path or ""
            target = root / repo_path
        else:
            target = (root / ref.file).parent / ref.target.split("#")[0]
        problem = _check_target(root, ref, target, outputs, where)
        if problem is not None:
            errors.append(problem)
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
