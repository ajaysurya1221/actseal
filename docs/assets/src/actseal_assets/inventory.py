"""Declared asset inventory: names, outputs, sources and renderers.

Every asset name from the approved interface contract is declared here before
its figure exists. A ``renderer`` of ``None`` means the figure is planned but
not implemented; ``render.py --check`` reports it as such and never counts it
as passed. Later tasks attach a renderer and finalize provisional dimensions.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from . import how_it_works

ASSET_DIR = "docs/assets"
SOURCE_DIR = "docs/assets/src"
FONT_DIR = "docs/assets/src/fonts"
RECEIPT_DIR = "docs/assets/src/receipts"
MANIFEST_FILE = "docs/assets/src/tools.toml"

# Assumed CSS width of GitHub's README column at a 1366 px viewport. The
# ten-second acceptance screenshot confirms or corrects it; nothing here
# measures it. Labels are checked against this width, not against the
# native SVG size.
README_DISPLAY_WIDTH = 880
MOBILE_DISPLAY_WIDTH = 360

SOCIAL_WIDTH = 1280
SOCIAL_HEIGHT = 640
DEMO_GIF_MAX_BYTES = 3_000_000
DEMO_MIN_SECONDS = 20.0
DEMO_MAX_SECONDS = 40.0

HERO_WIDTH = 1600
HERO_HEIGHT = 400


@dataclass(frozen=True, slots=True)
class RenderContext:
    """Paths available to a renderer. ``work`` is discarded after rendering."""

    root: Path
    work: Path

    @property
    def src(self) -> Path:
        return self.root / SOURCE_DIR

    @property
    def fonts(self) -> Path:
        return self.root / FONT_DIR


Renderer = Callable[[RenderContext], Mapping[str, bytes]]


@dataclass(frozen=True, slots=True)
class Output:
    """One committed file under ``docs/assets``."""

    path: str
    kind: str
    width: int | None
    height: int | None
    display_width: int | None = None
    outlined: bool = False
    max_bytes: int | None = None


@dataclass(frozen=True, slots=True)
class Source:
    """One committed input under ``docs/assets/src`` that ``--check`` validates."""

    path: str
    kind: str
    min_seconds: float | None = None
    max_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class Asset:
    name: str
    priority: str
    task: str
    summary: str
    outputs: tuple[Output, ...]
    sources: tuple[Source, ...] = ()
    needs: tuple[str, ...] = ()
    renderer: Renderer | None = None

    @property
    def implemented(self) -> bool:
        return self.renderer is not None


OUTPUT_KINDS = frozenset({"svg", "png", "gif"})
SOURCE_KINDS = frozenset({"cast"})
# A committed file name: no directories, no leading dot, no traversal, ASCII only.
PLAIN_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*(?:\.[A-Za-z0-9_-]+)*$")


def is_plain_filename(name: str) -> bool:
    return bool(PLAIN_FILENAME.match(name)) and ".." not in name


def _svg(
    path: str,
    width: int,
    height: int,
    *,
    outlined: bool = False,
    display_width: int = README_DISPLAY_WIDTH,
) -> Output:
    return Output(
        path=path,
        kind="svg",
        width=width,
        height=height,
        display_width=display_width,
        outlined=outlined,
    )


def _mobile_svg(path: str, width: int, height: int) -> Output:
    """A vertical variant displayed in a 360 CSS px column."""
    return _svg(path, width, height, display_width=MOBILE_DISPLAY_WIDTH)


# Heights other than the hero, how-it-works and social preview are
# provisional; the task that implements each figure finalizes them together
# with its renderer.
ASSETS: tuple[Asset, ...] = (
    Asset(
        name="hero",
        priority="P1",
        task="11",
        summary="Wordmark, approved tagline and one freeze/run/replay motif; outlined text.",
        outputs=(
            _svg("hero-light.svg", HERO_WIDTH, HERO_HEIGHT, outlined=True),
            _svg("hero-dark.svg", HERO_WIDTH, HERO_HEIGHT, outlined=True),
        ),
        needs=("jetbrains-mono", "fonttools"),
    ),
    Asset(
        name="how-it-works",
        priority="P1",
        task="12",
        summary="Freeze, Run, Verify, Seal, Replay with decisions, verdicts and exit codes.",
        outputs=(
            _svg(
                "how-it-works-light.svg",
                how_it_works.DESKTOP_WIDTH,
                how_it_works.DESKTOP_HEIGHT,
            ),
            _svg(
                "how-it-works-dark.svg",
                how_it_works.DESKTOP_WIDTH,
                how_it_works.DESKTOP_HEIGHT,
            ),
            _mobile_svg(
                "how-it-works-mobile-light.svg",
                how_it_works.MOBILE_WIDTH,
                how_it_works.mobile_height(),
            ),
            _mobile_svg(
                "how-it-works-mobile-dark.svg",
                how_it_works.MOBILE_WIDTH,
                how_it_works.mobile_height(),
            ),
        ),
        renderer=how_it_works.render,
    ),
    Asset(
        name="architecture",
        priority="P1",
        task="13",
        summary="At most seven shipped groups traced to modules; replay never reaches providers.",
        outputs=(_svg("architecture.svg", 1600, 900),),
    ),
    Asset(
        name="demo",
        priority="P1",
        task="14",
        summary="Genuine PyPI demo, fixed replay and bad replay rendered from the raw cast.",
        outputs=(
            Output(
                path="demo.gif",
                kind="gif",
                width=None,
                height=None,
                max_bytes=DEMO_GIF_MAX_BYTES,
            ),
        ),
        sources=(
            Source(
                path="demo.cast",
                kind="cast",
                min_seconds=DEMO_MIN_SECONDS,
                max_seconds=DEMO_MAX_SECONDS,
            ),
        ),
        needs=("agg", "jetbrains-mono"),
    ),
    Asset(
        name="social",
        priority="required",
        task="15",
        summary="GitHub social preview from the banner composition.",
        outputs=(Output(path="social.png", kind="png", width=SOCIAL_WIDTH, height=SOCIAL_HEIGHT),),
        needs=("resvg", "jetbrains-mono", "fonttools"),
    ),
    Asset(
        name="where",
        priority="P2",
        task="16",
        summary="Application, Actseal policy gate, application action execution.",
        outputs=(_svg("where-it-sits.svg", 1600, 480),),
    ),
    Asset(
        name="matrix",
        priority="P2",
        task="17",
        summary="Four per-case decisions and four whole-run verdicts with exit codes.",
        outputs=(_svg("decision-verdict-matrix.svg", 1600, 560),),
    ),
    Asset(
        name="boundary",
        priority="P2",
        task="18",
        summary="Consistency and recomputation versus authenticity, inference and label truth.",
        outputs=(_svg("evidence-boundary.svg", 1600, 560),),
    ),
)

ASSET_NAMES: tuple[str, ...] = tuple(asset.name for asset in ASSETS)


def get_asset(name: str, assets: tuple[Asset, ...] = ASSETS) -> Asset:
    for asset in assets:
        if asset.name == name:
            return asset
    msg = f"unknown asset {name!r}; expected one of {', '.join(a.name for a in assets)}"
    raise KeyError(msg)


def validate_inventory(assets: tuple[Asset, ...] = ASSETS) -> list[str]:
    """Structural problems in an inventory, independent of the file system."""
    errors: list[str] = []
    names = [asset.name for asset in assets]
    if len(set(names)) != len(names):
        errors.append("duplicate asset names in inventory")
    paths: list[str] = []
    for asset in assets:
        if not asset.outputs:
            errors.append(f"{asset.name}: declares no outputs")
        for output in asset.outputs:
            paths.append(output.path)
            if output.kind not in OUTPUT_KINDS:
                errors.append(f"{asset.name}: unsupported output kind {output.kind!r}")
            if not output.path.endswith(f".{output.kind}"):
                errors.append(f"{asset.name}: {output.path} does not end with .{output.kind}")
            if not is_plain_filename(output.path):
                errors.append(f"{asset.name}: output {output.path!r} must be a plain filename")
        for source in asset.sources:
            if source.kind not in SOURCE_KINDS:
                errors.append(f"{asset.name}: unsupported source kind {source.kind!r}")
            if not is_plain_filename(source.path):
                errors.append(f"{asset.name}: source {source.path!r} must be a plain filename")
    if len(set(paths)) != len(paths):
        errors.append("duplicate output paths in inventory")
    return errors
