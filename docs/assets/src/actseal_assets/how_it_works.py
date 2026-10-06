"""The how-it-works figure: Freeze, Run, Verify, Seal, Replay.

Five stage groups in the approved order, each with its module name, the
inputs or outputs that matter, and the enumerations the contract freezes: the
four per-case decisions, the four run verdicts paired with their exit codes,
the hashed size-bounded bundle and ``offline; no model call``. A sixth group
on the desktop canvas maps the stages to the three CLI commands; the mobile
canvas folds the command into each stage's label instead.

Two canvases are rendered, each in a light and a dark palette. The desktop
canvas is 1600x400 and is displayed at about 880 CSS px in the README, so
every label is at least 26 SVG units (14.3 rendered px) and headings are
larger. The mobile canvas stacks the stages vertically at 720 units wide for
a 360 CSS px column, so its labels are at least 30 units. Nothing is shrunk
to fit: every line is measured against a conservative width model and the
renderer fails explicitly when a phrase would overflow its box.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from . import svg

if TYPE_CHECKING:
    from .inventory import RenderContext

DESKTOP_WIDTH = 1600
DESKTOP_HEIGHT = 400
MOBILE_WIDTH = 720

# Helvetica, Arial and Liberation Sans share metrics, so this stack renders
# with predictable widths on macOS, Windows and Linux before falling back to
# the browser's generic sans-serif face.
FONT_STACK = "Helvetica, Arial, Liberation Sans, sans-serif"
# Multiplied into every measured width so a slightly wider fallback face
# still fits inside its box.
WIDTH_SAFETY = 1.08
BOLD_SAFETY = 1.1
SEPARATOR = " · "

PLAIN = "plain"
ACCENT = "accent"

OUTPUTS = (
    "how-it-works-light.svg",
    "how-it-works-dark.svg",
    "how-it-works-mobile-light.svg",
    "how-it-works-mobile-dark.svg",
)

# Helvetica advance widths per 1000 em for printable ASCII plus the middle
# dot. A character outside this table is an error, never a guess.
_WIDTHS: dict[str, int] = {
    " ": 278, "!": 278, '"': 355, "#": 556, "$": 556, "%": 889, "&": 667, "'": 191,
    "(": 333, ")": 333, "*": 389, "+": 584, ",": 278, "-": 333, ".": 278, "/": 278,
    "0": 556, "1": 556, "2": 556, "3": 556, "4": 556, "5": 556, "6": 556, "7": 556,
    "8": 556, "9": 556, ":": 278, ";": 278, "<": 584, "=": 584, ">": 584, "?": 556,
    "@": 1015, "A": 667, "B": 667, "C": 722, "D": 722, "E": 667, "F": 611, "G": 778,
    "H": 722, "I": 278, "J": 500, "K": 667, "L": 556, "M": 833, "N": 722, "O": 778,
    "P": 667, "Q": 778, "R": 722, "S": 667, "T": 611, "U": 722, "V": 667, "W": 944,
    "X": 667, "Y": 667, "Z": 611, "[": 278, "]": 278, "^": 469, "_": 556, "`": 333,
    "a": 556, "b": 556, "c": 500, "d": 556, "e": 556, "f": 278, "g": 556, "h": 556,
    "i": 222, "j": 222, "k": 500, "l": 222, "m": 833, "n": 556, "o": 556, "p": 556,
    "q": 556, "r": 333, "s": 500, "t": 278, "u": 556, "v": 500, "w": 722, "x": 500,
    "y": 500, "z": 500, "{": 334, "|": 260, "}": 334, "~": 584, "·": 278,
}  # fmt: skip


def text_width(text: str, size: float, *, bold: bool = False) -> float:
    """Conservative rendered width of ``text`` at ``size`` in SVG units."""
    total = 0
    for char in text:
        width = _WIDTHS.get(char)
        if width is None:
            msg = f"no width metric for {char!r} in {text!r}"
            raise ValueError(msg)
        total += width
    factor = WIDTH_SAFETY * (BOLD_SAFETY if bold else 1.0)
    return total / 1000 * size * factor


@dataclass(frozen=True, slots=True)
class Item:
    """One body entry: a run of phrases that may share a line, and its emphasis."""

    phrases: tuple[str, ...]
    emphasis: str = PLAIN


@dataclass(frozen=True, slots=True)
class Stage:
    key: str
    title: str
    module: str
    items: tuple[Item, ...]


@dataclass(frozen=True, slots=True)
class Command:
    label: str
    first: int
    last: int


STAGES: tuple[Stage, ...] = (
    Stage(
        "freeze",
        "Freeze",
        "locking",
        (
            Item(("allowed labels",)),
            Item(("threshold + limits",)),
            Item(("scheduled cases",)),
            Item(("model identity",)),
            Item(("lock.json + sha256",)),
        ),
    ),
    Stage(
        "run",
        "Run",
        "policy",
        (
            Item(("every locked case",)),
            Item(("+ 6 fault scenarios",)),
            Item(("decision per case:",)),
            Item(("ACT", "ABSTAIN", "ESCALATE", "DENY"), ACCENT),
        ),
    ),
    Stage(
        "verify",
        "Verify",
        "assessment",
        (
            Item(("risk + coverage",)),
            Item(("bounds, fault rules",)),
            Item(("verdict, exit code:",)),
            Item(("PASS 0", "BLOCK 1", "INCONCLUSIVE 2", "ERROR 3"), ACCENT),
        ),
    ),
    Stage(
        "seal",
        "Seal",
        "evidence",
        (
            Item(("lock + cases",)),
            Item(("records + faults",)),
            Item(("verdict + manifest",)),
            Item(("every file hashed",)),
            Item(("bounded size",)),
        ),
    ),
    Stage(
        "replay",
        "Replay",
        "replay",
        (
            Item(("offline; no model call",), ACCENT),
            Item(("no provider loaded",)),
            Item(("rechecks every hash",)),
            Item(("recomputes verdict",)),
            Item(("exit codes 0/1/2/3",)),
        ),
    ),
)

COMMANDS: tuple[Command, ...] = (
    Command("actseal lock", 0, 0),
    Command("actseal verify", 1, 3),
    Command("actseal replay", 4, 4),
)

TITLE = "How Actseal works: freeze, run, verify, seal, replay"
DESC = (
    "Five stages in order. Freeze locks the allowed labels, threshold, limits, "
    "scheduled cases and model identity into lock.json with its sha256. "
    "Run decides every locked case plus six fault scenarios with the frozen "
    "policy: ACT, ABSTAIN, ESCALATE or DENY. Verify bounds risk and coverage "
    "and applies the fault rules to reach one verdict and exit code: PASS 0, "
    "BLOCK 1, INCONCLUSIVE 2 or ERROR 3. Seal writes the evidence bundle of "
    "lock, cases, records, faults, verdict and manifest, every file hashed and "
    "size-bounded. Replay recomputes the verdict from the bundle offline with "
    "no model call and no provider loaded, exiting with the same codes. "
    "The lock command performs Freeze, the verify command performs Run, Verify "
    "and Seal, and the replay command performs Replay."
)


@dataclass(frozen=True, slots=True)
class Palette:
    name: str
    canvas: str
    box: str
    border: str
    heading: str
    muted: str
    body: str
    accent: str


LIGHT = Palette(
    name="light",
    canvas="#ffffff",
    box="#f6f8fa",
    border="#d0d7de",
    heading="#1f2328",
    muted="#57606a",
    body="#24292f",
    accent="#0969da",
)
DARK = Palette(
    name="dark",
    canvas="#0d1117",
    box="#161b22",
    border="#30363d",
    heading="#e6edf3",
    muted="#8b949e",
    body="#c9d1d9",
    accent="#58a6ff",
)


@dataclass(frozen=True, slots=True)
class Metrics:
    """Type sizes and spacing for one canvas; all values are SVG units."""

    heading: int
    label: int
    body: int
    line: int
    pad: int
    heading_top: int
    label_gap: int
    divider_gap: int
    body_gap: int
    bottom: int

    @property
    def heading_baseline(self) -> int:
        return self.heading_top + self.heading

    @property
    def label_baseline(self) -> int:
        return self.heading_baseline + self.label_gap + self.label

    @property
    def divider(self) -> int:
        return self.label_baseline + self.divider_gap

    @property
    def body_baseline(self) -> int:
        return self.divider + self.body_gap + self.body

    def box_height(self, lines: int) -> int:
        return self.body_baseline + self.line * (lines - 1) + self.bottom


DESKTOP = Metrics(
    heading=34,
    label=26,
    body=26,
    line=32,
    pad=14,
    heading_top=12,
    label_gap=8,
    divider_gap=14,
    body_gap=6,
    bottom=18,
)
MOBILE = Metrics(
    heading=44,
    label=30,
    body=30,
    line=38,
    pad=20,
    heading_top=18,
    label_gap=10,
    divider_gap=16,
    body_gap=8,
    bottom=26,
)

DESKTOP_MARGIN = 20
DESKTOP_GAP = 30
DESKTOP_TOP = 18
DESKTOP_BRACKET_GAP = 14
DESKTOP_TICK = 6
DESKTOP_LABEL_DROP = 6
DESKTOP_BRACKET_INSET = 8
MOBILE_MARGIN = 24
MOBILE_GAP = 56
MOBILE_TOP = 24
BOX_RADIUS = 10
BORDER = 2
NUMERAL_GAP = 6
ARROW_STROKE = 3
ARROW_HEAD = 12
ARROW_HALF = 8
ARROW_CLEARANCE = 3
DESCENDER = 0.25
CANVAS_SLACK = 4


def wrap(item: Item, size: float, max_width: float) -> list[str]:
    """Pack the phrases of ``item`` onto lines no wider than ``max_width``.

    A single phrase that cannot fit is an error: text is never shrunk.
    """
    lines: list[str] = []
    current = ""
    for phrase in item.phrases:
        _require_fit(phrase, size, max_width)
        candidate = phrase if not current else f"{current}{SEPARATOR}{phrase}"
        if current and text_width(candidate, size) > max_width:
            lines.append(current)
            current = phrase
        else:
            current = candidate
    lines.append(current)
    return lines


def _require_fit(text: str, size: float, max_width: float, *, bold: bool = False) -> None:
    if text_width(text, size, bold=bold) > max_width:
        msg = f"{text!r} does not fit in {max_width:g} units at {size:g}"
        raise ValueError(msg)


def _stage_group(
    stage: Stage,
    index: int,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    metrics: Metrics,
    palette: Palette,
    label: str,
) -> svg.Node:
    inner = width - 2 * metrics.pad
    group = svg.Node("g", id=f"stage-{stage.key}", font_family=FONT_STACK)
    group.add(
        "rect",
        x=x,
        y=y,
        width=width,
        height=height,
        rx=BOX_RADIUS,
        fill=palette.box,
        stroke=palette.border,
        stroke_width=BORDER,
    )
    left = x + metrics.pad
    numeral = str(index + 1)
    _require_fit(f"{numeral} {stage.title}", metrics.heading, inner - NUMERAL_GAP, bold=True)
    heading = group.add(
        "text",
        x=left,
        y=y + metrics.heading_baseline,
        font_size=metrics.heading,
        font_weight="bold",
        fill=palette.heading,
    )
    heading.add("tspan", fill=palette.accent).text(numeral)
    heading.text(" ")
    heading.add("tspan", dx=NUMERAL_GAP).text(stage.title)
    _require_fit(label, metrics.label, inner)
    group.add(
        "text",
        x=left,
        y=y + metrics.label_baseline,
        font_size=metrics.label,
        fill=palette.muted,
    ).text(label)
    group.add(
        "line",
        x1=left,
        y1=y + metrics.divider,
        x2=x + width - metrics.pad,
        y2=y + metrics.divider,
        stroke=palette.border,
        stroke_width=BORDER,
    )
    baseline = y + metrics.body_baseline
    for item in stage.items:
        fill = palette.accent if item.emphasis == ACCENT else palette.body
        for line in wrap(item, metrics.body, inner):
            group.add("text", x=left, y=baseline, font_size=metrics.body, fill=fill).text(line)
            baseline += metrics.line
    return group


def _line_count(stage: Stage, metrics: Metrics, inner: float) -> int:
    return sum(len(wrap(item, metrics.body, inner)) for item in stage.items)


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
    points = " ".join(
        f"{svg.fmt(px)},{svg.fmt(py)}"
        for px, py in (
            (x2, y),
            (x2 - ARROW_HEAD, y - ARROW_HALF),
            (x2 - ARROW_HEAD, y + ARROW_HALF),
        )
    )
    group.add("polygon", points=points, fill=color)


def _arrow_down(group: svg.Node, x: float, y1: float, y2: float, color: str) -> None:
    group.add(
        "line",
        x1=x,
        y1=y1,
        x2=x,
        y2=y2 - ARROW_HEAD,
        stroke=color,
        stroke_width=ARROW_STROKE,
    )
    points = " ".join(
        f"{svg.fmt(px)},{svg.fmt(py)}"
        for px, py in (
            (x, y2),
            (x - ARROW_HALF, y2 - ARROW_HEAD),
            (x + ARROW_HALF, y2 - ARROW_HEAD),
        )
    )
    group.add("polygon", points=points, fill=color)


def _desktop(palette: Palette) -> svg.Node:
    metrics = DESKTOP
    width = DESKTOP_WIDTH
    count = len(STAGES)
    box_width = (width - 2 * DESKTOP_MARGIN - (count - 1) * DESKTOP_GAP) / count
    inner = box_width - 2 * metrics.pad
    lines = max(_line_count(stage, metrics, inner) for stage in STAGES)
    box_height = metrics.box_height(lines)
    top = DESKTOP_TOP
    bracket_y = top + box_height + DESKTOP_BRACKET_GAP + DESKTOP_TICK
    label_baseline = bracket_y + DESKTOP_LABEL_DROP + metrics.label
    bottom = label_baseline + metrics.label * DESCENDER
    if bottom > DESKTOP_HEIGHT - CANVAS_SLACK:
        msg = f"desktop layout needs {bottom:g} units; the canvas is {DESKTOP_HEIGHT}"
        raise ValueError(msg)
    root = svg.document(width, DESKTOP_HEIGHT, title=TITLE, desc=DESC)
    root.add("rect", x=0, y=0, width=width, height=DESKTOP_HEIGHT, fill=palette.canvas)
    xs = [DESKTOP_MARGIN + index * (box_width + DESKTOP_GAP) for index in range(count)]
    for index, stage in enumerate(STAGES):
        group = _stage_group(
            stage,
            index,
            x=xs[index],
            y=top,
            width=box_width,
            height=box_height,
            metrics=metrics,
            palette=palette,
            label=stage.module,
        )
        if index + 1 < count:
            x1 = xs[index] + box_width + ARROW_CLEARANCE
            x2 = xs[index + 1] - ARROW_CLEARANCE
            _arrow_right(group, x1, x2, top + box_height / 2, palette.accent)
        root.append(group)
    commands = root.add("g", id="commands", font_family=FONT_STACK)
    for command in COMMANDS:
        left = xs[command.first] + DESKTOP_BRACKET_INSET
        right = xs[command.last] + box_width - DESKTOP_BRACKET_INSET
        _require_fit(command.label, metrics.label, right - left)
        path = (
            f"M{svg.fmt(left)},{svg.fmt(bracket_y - DESKTOP_TICK)} "
            f"V{svg.fmt(bracket_y)} H{svg.fmt(right)} V{svg.fmt(bracket_y - DESKTOP_TICK)}"
        )
        commands.add("path", d=path, fill="none", stroke=palette.muted, stroke_width=BORDER)
        commands.add(
            "text",
            x=(left + right) / 2,
            y=label_baseline,
            font_size=metrics.label,
            fill=palette.muted,
            text_anchor="middle",
        ).text(command.label)
    return root


def _command_for(index: int) -> Command:
    for command in COMMANDS:
        if command.first <= index <= command.last:
            return command
    msg = f"stage {index} has no command"
    raise ValueError(msg)


def _mobile_label(stage: Stage, command: Command) -> str:
    """``command · module`` unless the module name already is the command's."""
    if stage.module in command.label.split():
        return command.label
    return f"{command.label}{SEPARATOR}{stage.module}"


def _mobile_layout() -> tuple[list[int], list[int], int]:
    """Box tops, box heights and the canvas height of the stacked variant."""
    metrics = MOBILE
    box_width = MOBILE_WIDTH - 2 * MOBILE_MARGIN
    inner = box_width - 2 * metrics.pad
    tops: list[int] = []
    heights: list[int] = []
    y = MOBILE_TOP
    for index, stage in enumerate(STAGES):
        height = metrics.box_height(_line_count(stage, metrics, inner))
        tops.append(y)
        heights.append(height)
        y += height
        if index + 1 < len(STAGES):
            y += MOBILE_GAP
    return tops, heights, y + MOBILE_TOP


def mobile_height() -> int:
    """Canvas height of the mobile variant, derived from the wrapped content."""
    return _mobile_layout()[2]


def _mobile(palette: Palette) -> svg.Node:
    metrics = MOBILE
    box_width = MOBILE_WIDTH - 2 * MOBILE_MARGIN
    tops, heights, canvas_height = _mobile_layout()
    root = svg.document(MOBILE_WIDTH, canvas_height, title=TITLE, desc=DESC)
    root.add("rect", x=0, y=0, width=MOBILE_WIDTH, height=canvas_height, fill=palette.canvas)
    for index, stage in enumerate(STAGES):
        group = _stage_group(
            stage,
            index,
            x=MOBILE_MARGIN,
            y=tops[index],
            width=box_width,
            height=heights[index],
            metrics=metrics,
            palette=palette,
            label=_mobile_label(stage, _command_for(index)),
        )
        if index + 1 < len(STAGES):
            y1 = tops[index] + heights[index] + ARROW_CLEARANCE
            y2 = tops[index + 1] - ARROW_CLEARANCE
            _arrow_down(group, MOBILE_WIDTH / 2, y1, y2, palette.accent)
        root.append(group)
    return root


def render(_context: RenderContext) -> Mapping[str, bytes]:
    """Render every declared output; the context is unused (no fonts or tools)."""
    return {
        "how-it-works-light.svg": svg.serialize_bytes(_desktop(LIGHT)),
        "how-it-works-dark.svg": svg.serialize_bytes(_desktop(DARK)),
        "how-it-works-mobile-light.svg": svg.serialize_bytes(_mobile(LIGHT)),
        "how-it-works-mobile-dark.svg": svg.serialize_bytes(_mobile(DARK)),
    }
