"""The hero banner: wordmark, approved tagline and one forward freeze/run/replay sequence.

Every visible string is converted to path data with the pinned JetBrains Mono
files through ``outline.outline_text``; the committed files contain no
``<text>`` and need no font at display time. The renderer refuses to run
without both pinned font files and never substitutes another face: a missing
file raises ``OutlineError`` before any glyph is drawn. The pipeline verifies
the font hashes against ``tools.toml`` before calling ``render``; this module
only checks presence so that a direct call still fails loudly.

Two canvases are rendered, each in a light and a dark palette. The desktop
canvas is 1600x280 and measures 838 CSS px in the README at 1280 px and wider
viewports; its smallest text, the 32-unit step labels, renders at 16.8 px and
the 28-unit desktop label minimum would render at 14.7 px. The mobile canvas
is 720x400 and stacks the same content; it is validated at the narrowest
measured column, 254 CSS px at a 320 px viewport, so its smallest text is
40 units (14.1 rendered px). Line breaks are fixed in this file and every line
is measured with the real glyph advances at render time; a line that would
not fit raises ``ValueError``. Text is never shrunk to fit.

The copy is the approved wordmark and two-line tagline; the 2026-10-08
editorial review removed the caption paragraph from the artwork, and the
evidence limits it carried are stated in the README prose instead. The motif
is one forward sequence of three steps (freeze, run, replay) joined by two
arrows; there is no return arrow, and no padlock, shield, checkmark, badge or
other security symbol.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from . import svg
from .outline import OutlineError, outline_text

if TYPE_CHECKING:
    from .inventory import RenderContext

# Frozen copy. The joined lines must equal the single-string original;
# ``validate_copy`` enforces that before anything is rendered.
WORDMARK = "Actseal"
TAGLINE = "Test model-chosen actions. Replay the evidence."
TAGLINE_LINES: tuple[str, ...] = ("Test model-chosen actions.", "Replay the evidence.")
MOTIF_STEPS: tuple[str, ...] = ("freeze", "run", "replay")

TITLE = "Actseal: test model-chosen actions and replay the evidence"
DESC = (
    "Actseal wordmark with the tagline: Test model-chosen actions. Replay the "
    "evidence. Three steps in one forward sequence, freeze, run and replay, "
    "with one arrow from freeze to run and one from run to replay."
)

# Pinned font files, installed by setup_tools.py and hash-checked by the
# pipeline. Names match the artifacts in tools.toml.
REGULAR_FONT = "JetBrainsMono-Regular.ttf"
BOLD_FONT = "JetBrainsMono-Bold.ttf"

OUTPUTS: tuple[str, ...] = (
    "hero-light.svg",
    "hero-dark.svg",
    "hero-mobile-light.svg",
    "hero-mobile-dark.svg",
)

DESKTOP_WIDTH = 1600
DESKTOP_HEIGHT = 280
MOBILE_WIDTH = 720
MOBILE_HEIGHT = 400
# Measured CSS widths of a README image (838 px at 1280/1366 px viewports,
# 254 px at 320 px); the same values as inventory.py, repeated here because
# inventory imports this module.
DESKTOP_DISPLAY_WIDTH = 838
MOBILE_DISPLAY_WIDTH = 254
# Same floor as checks.MIN_LABEL_PX; outlined assets are exempt from that
# validator, so this module enforces the floor on its own type sizes.
MIN_LABEL_PX = 14.0
# Smallest step-label sizes the editorial specification allows per canvas.
MIN_DESKTOP_LABEL = 28
MIN_MOBILE_LABEL = 40

BORDER = 2
ARROW_STROKE = 3
ARROW_HEAD = 12
ARROW_HALF = 8
ARROW_CLEARANCE = 3
# Baseline offset below the pill's vertical centre for lowercase labels, as a
# fraction of the type size.
LABEL_BASELINE_SHIFT = 0.32
# Ascender allowance above the wordmark baseline and descender allowance below
# the last tagline baseline, as fractions of the type size. The pinned faces
# reach 0.777 em above and 0.18 em below the baseline for this copy; both
# allowances are deliberately larger.
ASCENT = 0.8
DESCENDER = 0.3


@dataclass(frozen=True, slots=True)
class Palette:
    name: str
    canvas: str
    box: str
    border: str
    heading: str
    body: str
    muted: str
    accent: str


LIGHT = Palette(
    name="light",
    canvas="#ffffff",
    box="#f6f8fa",
    border="#d0d7de",
    heading="#1f2328",
    body="#24292f",
    muted="#57606a",
    accent="#0969da",
)
DARK = Palette(
    name="dark",
    canvas="#0d1117",
    box="#161b22",
    border="#30363d",
    heading="#e6edf3",
    body="#c9d1d9",
    muted="#8b949e",
    accent="#58a6ff",
)


@dataclass(frozen=True, slots=True)
class Fonts:
    regular: Path
    bold: Path


@dataclass(frozen=True, slots=True)
class Canvas:
    """Type sizes, baselines and motif geometry for one variant, in SVG units."""

    name: str
    width: int
    display_width: int
    margin: int
    text_x: int
    text_width: int
    wordmark: int
    wordmark_baseline: int
    tagline: int
    tagline_baseline: int
    tagline_step: int
    label: int
    motif_x: int
    motif_top: int
    pill_width: int
    pill_height: int
    pill_gap: int
    pill_pad: int

    @property
    def sizes(self) -> tuple[int, ...]:
        return (self.wordmark, self.tagline, self.label)

    @property
    def motif_width(self) -> int:
        count = len(MOTIF_STEPS)
        return count * self.pill_width + (count - 1) * self.pill_gap

    @property
    def motif_bottom(self) -> int:
        """Lowest extent of the motif: the bottom edge of the pills."""
        return self.motif_top + self.pill_height

    @property
    def text_top(self) -> int:
        """Highest extent of the text block: the wordmark's ascender allowance."""
        return self.wordmark_baseline - math.ceil(self.wordmark * ASCENT)

    @property
    def text_bottom(self) -> int:
        """Lowest extent of the text block: the last tagline line's descender allowance."""
        last = self.tagline_baseline + (len(TAGLINE_LINES) - 1) * self.tagline_step
        return last + math.ceil(self.tagline * DESCENDER)

    def rendered_px(self, size: float) -> float:
        """Size of ``size`` units after scaling the canvas to its display width."""
        return size * min(1.0, self.display_width / self.width)


DESKTOP = Canvas(
    name="desktop",
    width=DESKTOP_WIDTH,
    display_width=DESKTOP_DISPLAY_WIDTH,
    margin=24,
    text_x=72,
    text_width=760,
    wordmark=104,
    wordmark_baseline=110,
    tagline=44,
    tagline_baseline=180,
    tagline_step=52,
    label=32,
    motif_x=848,
    motif_top=104,
    pill_width=184,
    pill_height=72,
    pill_gap=64,
    pill_pad=16,
)
MOBILE = Canvas(
    name="mobile",
    width=MOBILE_WIDTH,
    display_width=MOBILE_DISPLAY_WIDTH,
    margin=20,
    text_x=20,
    text_width=680,
    wordmark=84,
    wordmark_baseline=108,
    tagline=42,
    tagline_baseline=172,
    tagline_step=52,
    label=40,
    motif_x=20,
    motif_top=276,
    pill_width=200,
    pill_height=76,
    pill_gap=40,
    pill_pad=12,
)


def validate_copy() -> None:
    """The fixed line breaks must reproduce the approved tagline exactly."""
    if " ".join(TAGLINE_LINES) != TAGLINE:
        msg = f"tagline lines do not rejoin to the approved copy: {TAGLINE_LINES!r}"
        raise ValueError(msg)


def require_readable(canvas: Canvas) -> None:
    """Every type size must render at or above the label floor at display width."""
    for size in canvas.sizes:
        rendered = canvas.rendered_px(size)
        if rendered < MIN_LABEL_PX:
            msg = (
                f"{canvas.name}: {size} units render at {rendered:.1f}px at "
                f"{canvas.display_width} CSS px; minimum is {MIN_LABEL_PX:g}px"
            )
            raise ValueError(msg)


def require_label_minimum(canvas: Canvas, minimum: int) -> None:
    """The step labels must be at least the specified size for their canvas."""
    if canvas.label < minimum:
        msg = f"{canvas.name}: step labels are {canvas.label} units; minimum is {minimum} units"
        raise ValueError(msg)


def require_fonts(context: RenderContext) -> Fonts:
    """Both pinned font files must be present; nothing is substituted."""
    regular = context.fonts / REGULAR_FONT
    bold = context.fonts / BOLD_FONT
    missing = [path.name for path in (regular, bold) if not path.is_file()]
    if missing:
        msg = (
            f"pinned font file(s) missing from {context.fonts}: {', '.join(missing)}; "
            "run setup_tools.py --tool jetbrains-mono. No substitute font is used."
        )
        raise OutlineError(msg)
    return Fonts(regular=regular, bold=bold)


def _glyphs(
    group: svg.Node,
    font: Path,
    text: str,
    *,
    size: float,
    x: float,
    y: float,
    fill: str,
    max_width: float,
    centered: bool = False,
) -> float:
    """Outline ``text`` into ``group`` and return its advance.

    The string is measured first; one wider than ``max_width`` is an error,
    never scaled down. ``x`` is the left edge, or the centre when ``centered``.
    """
    measured = outline_text(font, text, size=size)
    if measured.advance > max_width:
        msg = (
            f"{text!r} is {measured.advance:.1f} units wide at size {size:g}; "
            f"only {max_width:g} units are available. Text is not shrunk; "
            "change the layout or the line breaks"
        )
        raise ValueError(msg)
    left = x - measured.advance / 2 if centered else x
    placed = outline_text(font, text, size=size, x=left, y=y)
    group.add("path", d=placed.d, fill=fill)
    return measured.advance


def _lines(
    group: svg.Node,
    font: Path,
    lines: tuple[str, ...],
    *,
    size: float,
    x: float,
    baseline: float,
    step: float,
    fill: str,
    max_width: float,
) -> None:
    for index, line in enumerate(lines):
        _glyphs(
            group,
            font,
            line,
            size=size,
            x=x,
            y=baseline + index * step,
            fill=fill,
            max_width=max_width,
        )


def _polygon(points: tuple[tuple[float, float], ...]) -> str:
    return " ".join(f"{svg.fmt(px)},{svg.fmt(py)}" for px, py in points)


def _arrow_right(group: svg.Node, x1: float, x2: float, y: float, color: str) -> None:
    group.add(
        "line",
        x1=x1,
        y1=y,
        x2=x2 - ARROW_HEAD,
        y2=y,
        stroke=color,
        stroke_width=ARROW_STROKE,
    )
    head = ((x2, y), (x2 - ARROW_HEAD, y - ARROW_HALF), (x2 - ARROW_HEAD, y + ARROW_HALF))
    group.add("polygon", points=_polygon(head), fill=color)


def _motif(root: svg.Node, fonts: Fonts, palette: Palette, canvas: Canvas) -> None:
    """Three pills in a row joined by forward arrows; nothing returns to the start."""
    group = root.add("g", id="motif")
    top = canvas.motif_top
    height = canvas.pill_height
    middle = top + height / 2
    for index, step in enumerate(MOTIF_STEPS):
        left = canvas.motif_x + index * (canvas.pill_width + canvas.pill_gap)
        pill = group.add("g", id=f"step-{step}")
        pill.add(
            "rect",
            x=left,
            y=top,
            width=canvas.pill_width,
            height=height,
            rx=height / 2,
            fill=palette.box,
            stroke=palette.border,
            stroke_width=BORDER,
        )
        _glyphs(
            pill,
            fonts.regular,
            step,
            size=canvas.label,
            x=left + canvas.pill_width / 2,
            y=middle + canvas.label * LABEL_BASELINE_SHIFT,
            fill=palette.heading,
            max_width=canvas.pill_width - 2 * canvas.pill_pad,
            centered=True,
        )
        if index + 1 < len(MOTIF_STEPS):
            x1 = left + canvas.pill_width + ARROW_CLEARANCE
            x2 = left + canvas.pill_width + canvas.pill_gap - ARROW_CLEARANCE
            _arrow_right(pill, x1, x2, middle, palette.accent)


def _require_extents(canvas: Canvas, height: int) -> None:
    """The fixed geometry must stay inside the canvas margins without overlap."""
    problems: list[str] = []
    if canvas.text_x + canvas.text_width > canvas.width - canvas.margin:
        problems.append("text column exceeds the canvas width")
    if canvas.motif_x + canvas.motif_width > canvas.width - canvas.margin:
        problems.append("motif exceeds the canvas width")
    if canvas.text_top < canvas.margin:
        problems.append(f"wordmark reaches {canvas.text_top} units from the top")
    if canvas.text_bottom > height - canvas.margin:
        problems.append(f"tagline needs {canvas.text_bottom} units of height")
    if canvas.motif_top < canvas.margin:
        problems.append(f"motif starts {canvas.motif_top} units from the top")
    if canvas.motif_bottom > height - canvas.margin:
        problems.append(f"motif needs {canvas.motif_bottom} units of height")
    beside = canvas.text_x + canvas.text_width <= canvas.motif_x
    below = canvas.text_bottom <= canvas.motif_top
    if not (beside or below):
        problems.append("text column overlaps the motif")
    if problems:
        msg = f"{canvas.name} layout does not fit a {canvas.width}x{height} canvas: " + "; ".join(
            problems
        )
        raise ValueError(msg)


def _text_blocks(root: svg.Node, fonts: Fonts, palette: Palette, canvas: Canvas) -> None:
    wordmark = root.add("g", id="wordmark")
    _glyphs(
        wordmark,
        fonts.bold,
        WORDMARK,
        size=canvas.wordmark,
        x=canvas.text_x,
        y=canvas.wordmark_baseline,
        fill=palette.heading,
        max_width=canvas.text_width,
    )
    _lines(
        root.add("g", id="tagline"),
        fonts.regular,
        TAGLINE_LINES,
        size=canvas.tagline,
        x=canvas.text_x,
        baseline=canvas.tagline_baseline,
        step=canvas.tagline_step,
        fill=palette.body,
        max_width=canvas.text_width,
    )


def _variant(canvas: Canvas, height: int, palette: Palette, fonts: Fonts) -> svg.Node:
    require_readable(canvas)
    _require_extents(canvas, height)
    root = svg.document(canvas.width, height, title=TITLE, desc=DESC)
    root.add("rect", x=0, y=0, width=canvas.width, height=height, fill=palette.canvas)
    _text_blocks(root, fonts, palette, canvas)
    _motif(root, fonts, palette, canvas)
    return root


def render(context: RenderContext) -> Mapping[str, bytes]:
    """Render every declared output from the pinned fonts, or fail before drawing."""
    validate_copy()
    require_label_minimum(DESKTOP, MIN_DESKTOP_LABEL)
    require_label_minimum(MOBILE, MIN_MOBILE_LABEL)
    fonts = require_fonts(context)
    return {
        "hero-light.svg": svg.serialize_bytes(_variant(DESKTOP, DESKTOP_HEIGHT, LIGHT, fonts)),
        "hero-dark.svg": svg.serialize_bytes(_variant(DESKTOP, DESKTOP_HEIGHT, DARK, fonts)),
        "hero-mobile-light.svg": svg.serialize_bytes(_variant(MOBILE, MOBILE_HEIGHT, LIGHT, fonts)),
        "hero-mobile-dark.svg": svg.serialize_bytes(_variant(MOBILE, MOBILE_HEIGHT, DARK, fonts)),
    }
