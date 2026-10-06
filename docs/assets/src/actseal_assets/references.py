"""README and docs image-reference validation.

Every image reference in ``README.md`` and ``docs/*.md`` is classified:

- ``local`` relative paths and ``same-repo`` absolute GitHub/raw URLs for this
  repository are mapped to a path under ``docs/assets`` that must exist, be a
  declared output and belong to an implemented asset;
- ``badge`` URLs from an explicit allowlist are exempt from the file check
  only; they still need alt text;
- any other absolute URL is an error, because an external image is a silent
  false pass that nothing here can validate offline.

HTML is parsed with the standard library ``html.parser`` so quoted ``>``
characters, single quotes, unquoted values and multi-line tags are handled;
``<img src>``, ``<img srcset>`` and ``<source srcset>`` are all inspected.
Markdown inline images and reference-style images (``![alt][label]``,
``![alt][]``, ``![alt]`` with a ``[label]: target`` definition) are resolved;
an unresolved label or an image without a target is an error, never a skip.
``<object>``, ``<embed>``, ``<iframe>`` and ``<video>`` are rejected as
unsupported image syntax. Validation never touches the network. Files under
``docs/assets`` that no asset declares are reported as orphans.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

from .inventory import ASSET_DIR, Asset

REPO_SLUG = "ajaysurya1221/actseal"

MARKDOWN_IMAGE = re.compile(
    r"!\[(?P<alt>[^\]]*)\]"
    r"(?:\(\s*(?P<target>[^)\s]+)(?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*\)"
    r"|\[(?P<label>[^\]]*)\])?"
)
MARKDOWN_DEFINITION = re.compile(
    r"^[ ]{0,3}\[(?P<label>[^\]]+)\]:[ \t]*<?(?P<target>[^\s>]+)>?", re.MULTILINE
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
UNSUPPORTED_TAGS = frozenset({"object", "embed", "iframe", "video"})
SCAN_FILES = ("README.md",)
SCAN_GLOBS = ("docs/*.md",)

LOCAL = "local"
SAME_REPO = "same-repo"
BADGE = "badge"
EXTERNAL = "external"


@dataclass(frozen=True, slots=True)
class Reference:
    """One image reference; ``problem`` is set when the syntax itself is unusable."""

    file: str
    line: int
    target: str
    alt: str | None
    needs_alt: bool
    problem: str | None = None

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


def _normalize_label(label: str) -> str:
    return " ".join(label.split()).casefold()


def _srcset_targets(value: str) -> list[str]:
    targets: list[str] = []
    for candidate in value.split(","):
        parts = candidate.split()
        if parts:
            targets.append(parts[0])
    return targets


class _ImageCollector(HTMLParser):
    """Collect ``img``/``source`` references and unsupported media tags."""

    def __init__(self, file: str) -> None:
        super().__init__(convert_charrefs=True)
        self.file = file
        self.found: list[tuple[int, int, int, Reference]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        line, column = self.getpos()
        values = {key.lower(): (value or "") for key, value in attrs}
        name = tag.lower()
        order = 0

        def add(ref: Reference) -> None:
            nonlocal order
            self.found.append((line, column, order, ref))
            order += 1

        if name in UNSUPPORTED_TAGS:
            target = values.get("src") or values.get("data") or values.get("poster") or ""
            problem = f"<{name}> is unsupported image syntax"
            add(Reference(self.file, line, target, None, needs_alt=False, problem=problem))
        elif name == "img":
            alt = values.get("alt")
            if "src" in values:
                add(Reference(self.file, line, values["src"], alt, needs_alt=True))
            else:
                problem = "<img> has no src attribute"
                add(Reference(self.file, line, "", alt, needs_alt=True, problem=problem))
            for target in _srcset_targets(values.get("srcset", "")):
                add(Reference(self.file, line, target, None, needs_alt=False))
        elif name == "source":
            for target in _srcset_targets(values.get("srcset", "")):
                add(Reference(self.file, line, target, None, needs_alt=False))


def _markdown_definitions(text: str) -> dict[str, str]:
    definitions: dict[str, str] = {}
    for match in MARKDOWN_DEFINITION.finditer(text):
        definitions.setdefault(_normalize_label(match.group("label")), match.group("target"))
    return definitions


def _scan_markdown(file: str, text: str) -> list[tuple[int, int, int, Reference]]:
    definitions = _markdown_definitions(text)
    found: list[tuple[int, int, int, Reference]] = []
    for match in MARKDOWN_IMAGE.finditer(text):
        line = _line_of(text, match.start())
        column = match.start() - text.rfind("\n", 0, match.start()) - 1
        alt = match.group("alt")
        target = match.group("target")
        problem: str | None = None
        if target is None:
            label = match.group("label")
            if not label:
                label = alt
            resolved = definitions.get(_normalize_label(label))
            if resolved is None:
                problem = f"reference image label {label!r} has no definition"
                target = ""
            else:
                target = resolved
        ref = Reference(file, line, target, alt, needs_alt=True, problem=problem)
        found.append((line, column, 0, ref))
    return found


def _scan_text(file: str, text: str) -> list[Reference]:
    found = _scan_markdown(file, text)
    collector = _ImageCollector(file)
    collector.feed(text)
    collector.close()
    found.extend(collector.found)
    return [ref for _, _, _, ref in sorted(found, key=lambda item: item[:3])]


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
    """Return (errors, number of references inspected). Nothing is skipped silently."""
    outputs = declared_outputs(assets)
    errors: list[str] = []
    checked = 0
    for ref in scan_references(root):
        checked += 1
        where = f"{ref.file}:{ref.line}"
        if ref.problem is not None:
            errors.append(f"{where}: {ref.problem}")
            continue
        if ref.needs_alt and not (ref.alt or "").strip():
            errors.append(f"{where}: image {ref.target!r} has no alt text")
        kind = ref.kind
        if kind == BADGE:
            continue
        if kind == EXTERNAL:
            errors.append(f"{where}: {ref.target!r} is an external image, not a recognized badge")
            continue
        if kind == SAME_REPO:
            target = root / (ref.repo_path or "")
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
