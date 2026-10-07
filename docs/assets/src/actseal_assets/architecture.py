"""The architecture figure: seven shipped groups traced to actual modules.

Each group box lists the ``actseal`` modules that implement it, so a reader
can open the package and find every node. The providers drawn are the ones in
the package: the stable recorded fixture adapter, the stable pinned native
Laya adapter and the PROVISIONAL ``experimental.providers.jev`` cloud adapter,
which is selected only by explicit opt-in and carries no stability promise. A
dashed boundary encloses the Laya and Jev nodes, because those are the only
places live inference happens: the fixture adapter reads a recorded file and
the fault campaign is a pure generator, so neither sits inside the boundary.
Nothing here states that the Jev service was exercised; the figure is a
component diagram of the source, not evidence that any provider answered.

Arrows are semantic edges. Each lives inside the ``<g>`` of the group it
leaves and carries ``data-source``/``data-target`` attributes so the exact
edge set can be asserted. The collection path is CLI -> contracts and CLI ->
providers -> normalization/policy -> assessment -> evidence; the fault campaign
is fed from the lock alone (contracts -> assessment); replay reads the bundle
and recomputes through contracts and assessment, which in turn re-normalizes
and re-evaluates every record. No edge joins replay and providers.

Two canvases are rendered in the light and dark palettes shared with the
how-it-works figure. The desktop canvas is 1600 units wide and measures 838
CSS px in the README at 1280 px and wider viewports (labels at least 27
units, 14.1 rendered px); the mobile canvas stacks the groups at 720 units and
is validated at the narrowest measured column, 254 CSS px at a 320 px
viewport (labels at least 40 units, 14.1 rendered px). Notes and arrow labels
wrap on word boundaries where a column is too narrow. Every line is measured
against the conservative width model and the renderer fails rather than
shrinking text. These are structural checks of the SVG bytes; viewing the
rendered pixels is a separate review step.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from . import svg
from .how_it_works import DARK, FONT_STACK, LIGHT, Palette, text_width

if TYPE_CHECKING:
    from .inventory import RenderContext

DESKTOP_WIDTH = 1600
DESKTOP_HEIGHT = 980
MOBILE_WIDTH = 720

OUTPUTS = (
    "architecture-light.svg",
    "architecture-dark.svg",
    "architecture-mobile-light.svg",
    "architecture-mobile-dark.svg",
)

NAME_SEPARATOR = " · "
TITLE_SEPARATOR = " / "
LIVE_LABEL = "live inference"
DESCENDER = 0.25
CANVAS_SLACK = 4


@dataclass(frozen=True, slots=True)
class Group:
    """One semantic group: its id, title phrases, module names and notes."""

    key: str
    title: tuple[str, ...]
    modules: tuple[str, ...]
    notes: tuple[str, ...]
    live: tuple[str, ...] = ()

    @property
    def heading(self) -> str:
        return TITLE_SEPARATOR.join(self.title)


@dataclass(frozen=True, slots=True)
class Edge:
    """A directed semantic edge between two groups; ``label`` may be omitted."""

    key: str
    source: str
    target: str
    label: str | None = None


GROUPS: tuple[Group, ...] = (
    Group(
        "contracts",
        ("Contracts", "locks"),
        ("contract", "records", "errors", "serialization", "locking", "compatibility"),
        ("parse, seal, validate", "no model call"),
    ),
    Group(
        "cli",
        ("CLI", "typed API"),
        ("cli", "runner", "__init__", "__main__", "demo_data"),
        ("lock, verify, replay, demo",),
    ),
    Group(
        "providers",
        ("Providers",),
        ("adapters.base", "adapters.fixture"),
        (
            "fixture: recorded file",
            "laya: pinned checkpoint",
            "jev: PROVISIONAL opt-in",
        ),
        live=("adapters.laya", "experimental.providers.jev"),
    ),
    Group(
        "normalization",
        ("Normalization", "policy"),
        ("normalization", "policy"),
        ("pure; no provider import", "decision per capture"),
    ),
    Group(
        "assessment",
        ("Assessment", "statistics", "faults"),
        ("assessment", "stats", "faults"),
        ("6 synthetic faults; no model call", "recomputes decisions, then the verdict"),
    ),
    Group(
        "evidence",
        ("Evidence",),
        ("evidence",),
        ("7-file bundle, bounded", "atomic publish"),
    ),
    Group(
        "replay",
        ("Replay",),
        ("replay",),
        ("offline; no provider import", "recomputes the verdict"),
    ),
)

EDGES: tuple[Edge, ...] = (
    Edge("cli-contracts", "cli", "contracts"),
    Edge("cli-providers", "cli", "providers"),
    Edge("providers-normalization", "providers", "normalization"),
    Edge("normalization-assessment", "normalization", "assessment", "decisions"),
    Edge("contracts-assessment", "contracts", "assessment", "6 synthetic faults"),
    Edge("assessment-evidence", "assessment", "evidence", "verdict, records, faults"),
    Edge("evidence-replay", "evidence", "replay"),
    Edge("replay-contracts", "replay", "contracts", "lock, inputs"),
    Edge("replay-assessment", "replay", "assessment", "recompute"),
)

TITLE = "Actseal architecture: seven shipped groups and their modules"
DESC = (
    "Seven groups, each listing the actseal modules that implement it. "
    "Contracts and locks: contract, records, errors, serialization, locking and "
    "compatibility parse, seal and validate the lock with no model call. "
    "CLI and typed API: cli, runner, __init__, __main__ and demo_data drive the "
    "lock, verify, replay and demo commands. Providers: adapters.base, "
    "adapters.fixture, adapters.laya and the PROVISIONAL "
    "experimental.providers.jev; the dashed live-inference boundary encloses "
    "the Laya and Jev adapters, because the fixture adapter reads a recorded "
    "file. Fixture and Laya are the stable providers; Jev is an experimental "
    "cloud adapter selected only by explicit opt-in, with no stability promise "
    "and no claim here that its service was exercised. Normalization and "
    "policy: normalization and policy are "
    "pure functions that turn one raw capture into one decision. Assessment, "
    "statistics and faults: assessment, stats and faults; the six fault "
    "scenarios are synthetic, generated from the lock with no model call, and "
    "assessment recomputes every decision before the verdict. Evidence: "
    "evidence writes the seven-file bounded data-only bundle atomically. "
    "Replay: replay reads the bundle and recomputes the verdict offline through "
    "contracts and assessment; no arrow joins replay and providers, and replay "
    "imports no provider module."
)


@dataclass(frozen=True, slots=True)
class Metrics:
    """Type sizes and spacing for one canvas; all values are SVG units."""

    heading: int
    heading_line: int
    body: int
    line: int
    pad: int
    heading_top: int
    divider_gap: int
    body_gap: int
    note_gap: int
    bottom: int
    boundary_pad: int
    boundary_inset: int
    label_gap: int


DESKTOP = Metrics(
    heading=32,
    heading_line=36,
    body=27,
    line=34,
    pad=12,
    heading_top=14,
    divider_gap=12,
    body_gap=8,
    note_gap=10,
    bottom=16,
    boundary_pad=10,
    boundary_inset=8,
    label_gap=12,
)
MOBILE = Metrics(
    heading=44,
    heading_line=50,
    body=40,
    line=52,
    pad=20,
    heading_top=16,
    divider_gap=14,
    body_gap=10,
    note_gap=12,
    bottom=18,
    boundary_pad=12,
    boundary_inset=8,
    label_gap=12,
)

BOX_RADIUS = 10
BOUNDARY_RADIUS = 6
BORDER = 2
DASH = "8 6"
ARROW_STROKE = 3
ARROW_HEAD = 12
ARROW_HALF = 7
ARROW_CLEARANCE = 4

DESKTOP_MARGIN = 16
DESKTOP_COLUMN_GAP = 28
DESKTOP_COLUMNS = 4
DESKTOP_TOP = 24
DESKTOP_ROW_GAPS = (80, 60)
#: Desktop placement. Row 0 is the collection path with the CLI between the
#: two groups it drives; row 1 is the wide assessment box under the CLI,
#: providers and normalization columns; row 2 holds replay under contracts
#: and evidence under assessment's left end. The empty slot under contracts is
#: the channel for replay's two return arrows.
DESKTOP_ROWS: tuple[tuple[tuple[str, int, int], ...], ...] = (
    (("contracts", 0, 1), ("cli", 1, 1), ("providers", 2, 1), ("normalization", 3, 1)),
    (("assessment", 1, 3),),
    (("replay", 0, 1), ("evidence", 1, 1)),
)
#: Fractions of a box width at which vertical arrow segments attach.
LEFT_LANE = 0.2
MID_LANE = 0.5
RIGHT_LANE = 0.8
ASSESSMENT_ENTRY = 80

MOBILE_MARGIN = 36
# Tall enough for a two-line wrapped arrow label between neighbouring boxes.
MOBILE_GAP = 130
MOBILE_TOP = 24
MOBILE_SPINE = 350
MOBILE_OUTER_CHANNEL = 12
MOBILE_INNER_CHANNEL = 24
MOBILE_RIGHT_CHANNEL = 708
MOBILE_PORT = 24
MOBILE_ORDER: tuple[str, ...] = (
    "contracts",
    "cli",
    "providers",
    "normalization",
    "assessment",
    "evidence",
    "replay",
)


def _require_fit(text: str, size: float, max_width: float, *, bold: bool = False) -> None:
    if text_width(text, size, bold=bold) > max_width:
        msg = f"{text!r} does not fit in {max_width:g} units at {size:g}"
        raise ValueError(msg)


def wrap(
    phrases: tuple[str, ...],
    size: float,
    max_width: float,
    *,
    separator: str,
    bold: bool = False,
) -> list[str]:
    """Pack phrases onto lines no wider than ``max_width``; never shrink or cut."""
    lines: list[str] = []
    current = ""
    for phrase in phrases:
        _require_fit(phrase, size, max_width, bold=bold)
        candidate = f"{current}{separator}{phrase}" if current else phrase
        if current and text_width(candidate, size, bold=bold) > max_width:
            lines.append(current)
            current = phrase
        else:
            current = candidate
    lines.append(current)
    return lines


@dataclass(frozen=True, slots=True)
class Layout:
    """Measured content of one group box: every baseline relative to the box top."""

    headings: tuple[tuple[str, int], ...]
    divider: int
    names: tuple[tuple[str, int], ...]
    live: tuple[tuple[str, int], ...]
    boundary: tuple[int, int] | None
    notes: tuple[tuple[str, int], ...]
    height: int


def layout(group: Group, metrics: Metrics, inner: float) -> Layout:
    """Measure ``group`` at ``metrics`` inside ``inner`` units of width."""
    heading_lines = wrap(group.title, metrics.heading, inner, separator=TITLE_SEPARATOR, bold=True)
    y = metrics.heading_top + metrics.heading
    headings: list[tuple[str, int]] = []
    for text in heading_lines:
        headings.append((text, y))
        y += metrics.heading_line
    divider = y - metrics.heading_line + metrics.divider_gap
    y = divider + metrics.body_gap + metrics.body
    names: list[tuple[str, int]] = []
    for text in wrap(group.modules, metrics.body, inner, separator=NAME_SEPARATOR):
        names.append((text, y))
        y += metrics.line
    live: list[tuple[str, int]] = []
    boundary: tuple[int, int] | None = None
    if group.live:
        y += metrics.boundary_pad
        top = y - metrics.body - metrics.boundary_inset
        for text in wrap(group.live, metrics.body, inner, separator=NAME_SEPARATOR):
            live.append((text, y))
            y += metrics.line
        _require_fit(LIVE_LABEL, metrics.body, inner - 2 * metrics.boundary_inset)
        live.append((LIVE_LABEL, y))
        bottom = y + round(metrics.body * DESCENDER) + metrics.boundary_inset
        boundary = (top, bottom)
        y = bottom + metrics.boundary_pad + metrics.body
    y += metrics.note_gap
    notes: list[tuple[str, int]] = []
    for note in group.notes:
        for text in wrap(tuple(note.split(" ")), metrics.body, inner, separator=" "):
            notes.append((text, y))
            y += metrics.line
    last = y - metrics.line
    height = last + round(metrics.body * DESCENDER) + metrics.bottom
    return Layout(
        tuple(headings), divider, tuple(names), tuple(live), boundary, tuple(notes), height
    )


@dataclass(frozen=True, slots=True)
class Box:
    x: float
    y: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2

    @property
    def center_y(self) -> float:
        return self.y + self.height / 2

    def lane(self, fraction: float) -> float:
        return self.x + self.width * fraction


def _group_by_key(key: str) -> Group:
    for group in GROUPS:
        if group.key == key:
            return group
    msg = f"unknown group {key!r}"
    raise ValueError(msg)


def _group_node(group: Group, box: Box, metrics: Metrics, palette: Palette) -> svg.Node:
    inner = box.width - 2 * metrics.pad
    measured = layout(group, metrics, inner)
    node = svg.Node("g", id=f"group-{group.key}", font_family=FONT_STACK)
    node.add(
        "rect",
        x=box.x,
        y=box.y,
        width=box.width,
        height=box.height,
        rx=BOX_RADIUS,
        fill=palette.box,
        stroke=palette.border,
        stroke_width=BORDER,
    )
    left = box.x + metrics.pad
    for text, baseline in measured.headings:
        node.add(
            "text",
            x=left,
            y=box.y + baseline,
            font_size=metrics.heading,
            font_weight="bold",
            fill=palette.heading,
        ).text(text)
    node.add(
        "line",
        x1=left,
        y1=box.y + measured.divider,
        x2=box.right - metrics.pad,
        y2=box.y + measured.divider,
        stroke=palette.border,
        stroke_width=BORDER,
    )
    for text, baseline in measured.names:
        node.add(
            "text", x=left, y=box.y + baseline, font_size=metrics.body, fill=palette.accent
        ).text(text)
    if measured.boundary is not None:
        top, bottom = measured.boundary
        live = node.add("g", id=f"live-boundary-{group.key}")
        live.add(
            "rect",
            x=left - metrics.boundary_inset,
            y=box.y + top,
            width=inner + 2 * metrics.boundary_inset,
            height=bottom - top,
            rx=BOUNDARY_RADIUS,
            fill="none",
            stroke=palette.accent,
            stroke_width=BORDER,
            stroke_dasharray=DASH,
        )
        for text, baseline in measured.live:
            fill = palette.muted if text == LIVE_LABEL else palette.accent
            live.add("text", x=left, y=box.y + baseline, font_size=metrics.body, fill=fill).text(
                text
            )
    for text, baseline in measured.notes:
        node.add(
            "text", x=left, y=box.y + baseline, font_size=metrics.body, fill=palette.muted
        ).text(text)
    return node


Point = tuple[float, float]


def _arrow(node: svg.Node, edge: Edge, points: tuple[Point, ...], color: str) -> svg.Node:
    """An orthogonal polyline whose last segment ends in an arrowhead."""
    *body, last = points
    before = body[-1]
    tx, ty = last
    bx, by = before
    if tx == bx:
        base_y = ty - ARROW_HEAD if ty > by else ty + ARROW_HEAD
        shortened: Point = (tx, base_y)
        head = ((tx, ty), (tx - ARROW_HALF, base_y), (tx + ARROW_HALF, base_y))
    elif ty == by:
        base_x = tx - ARROW_HEAD if tx > bx else tx + ARROW_HEAD
        shortened = (base_x, ty)
        head = ((tx, ty), (base_x, ty - ARROW_HALF), (base_x, ty + ARROW_HALF))
    else:
        msg = f"edge {edge.key}: the final segment must be horizontal or vertical"
        raise ValueError(msg)
    group = node.add("g", id=f"edge-{edge.key}", data_source=edge.source, data_target=edge.target)
    group.add(
        "polyline",
        points=" ".join(f"{svg.fmt(px)},{svg.fmt(py)}" for px, py in (*body, shortened)),
        fill="none",
        stroke=color,
        stroke_width=ARROW_STROKE,
    )
    group.add(
        "polygon", points=" ".join(f"{svg.fmt(px)},{svg.fmt(py)}" for px, py in head), fill=color
    )
    return group


def _label(
    node: svg.Node,
    edge: Edge,
    x: float,
    baseline: float,
    *,
    anchor: str,
    max_width: float,
    metrics: Metrics,
    palette: Palette,
) -> None:
    """Write the edge label, wrapped on word boundaries and centred on ``baseline``."""
    if edge.label is None:
        return
    lines = wrap(tuple(edge.label.split(" ")), metrics.body, max_width, separator=" ")
    first = baseline - (len(lines) - 1) * metrics.line / 2
    for index, line in enumerate(lines):
        node.add(
            "text",
            x=x,
            y=first + index * metrics.line,
            font_size=metrics.body,
            fill=palette.muted,
            text_anchor=anchor,
        ).text(line)


# --------------------------------------------------------------------------- #
# Desktop
# --------------------------------------------------------------------------- #


def _desktop_boxes() -> dict[str, Box]:
    metrics = DESKTOP
    column = (
        DESKTOP_WIDTH - 2 * DESKTOP_MARGIN - (DESKTOP_COLUMNS - 1) * DESKTOP_COLUMN_GAP
    ) / DESKTOP_COLUMNS
    boxes: dict[str, Box] = {}
    y: float = DESKTOP_TOP
    for index, row in enumerate(DESKTOP_ROWS):
        widths = {key: span * column + (span - 1) * DESKTOP_COLUMN_GAP for key, _, span in row}
        height = max(
            layout(_group_by_key(key), metrics, width - 2 * metrics.pad).height
            for key, width in widths.items()
        )
        for key, start, _ in row:
            x = DESKTOP_MARGIN + start * (column + DESKTOP_COLUMN_GAP)
            boxes[key] = Box(x, y, widths[key], height)
        y += height
        if index < len(DESKTOP_ROW_GAPS):
            y += DESKTOP_ROW_GAPS[index]
    if y + DESKTOP_TOP > DESKTOP_HEIGHT - CANVAS_SLACK:
        msg = f"desktop layout needs {y + DESKTOP_TOP:g} units; the canvas is {DESKTOP_HEIGHT}"
        raise ValueError(msg)
    return boxes


def _desktop_route(edge: Edge, boxes: Mapping[str, Box]) -> tuple[tuple[Point, ...], Point, str]:
    """Points of the arrow and ``(label x, label baseline, anchor)`` for one edge."""
    metrics = DESKTOP
    src, dst = boxes[edge.source], boxes[edge.target]
    gap = metrics.label_gap
    half = metrics.body / 2
    if edge.key in {"cli-providers", "cli-contracts", "providers-normalization", "evidence-replay"}:
        y = src.center_y
        if dst.x > src.x:
            points: tuple[Point, ...] = (
                (src.right + ARROW_CLEARANCE, y),
                (dst.x - ARROW_CLEARANCE, y),
            )
        else:
            points = ((src.x - ARROW_CLEARANCE, y), (dst.right + ARROW_CLEARANCE, y))
        return points, ((src.center_x + dst.center_x) / 2, y - gap), "middle"
    if edge.key == "normalization-assessment":
        x = src.center_x
        points = ((x, src.bottom + ARROW_CLEARANCE), (x, dst.y - ARROW_CLEARANCE))
        return points, (x + gap, (src.bottom + dst.y) / 2 + half), "start"
    if edge.key == "contracts-assessment":
        x1, x2 = src.lane(MID_LANE), dst.x + ASSESSMENT_ENTRY
        mid = (src.bottom + dst.y) / 2
        points = (
            (x1, src.bottom + ARROW_CLEARANCE),
            (x1, mid),
            (x2, mid),
            (x2, dst.y - ARROW_CLEARANCE),
        )
        return points, (x1 + gap, mid - gap), "start"
    if edge.key == "assessment-evidence":
        x = dst.center_x
        points = ((x, src.bottom + ARROW_CLEARANCE), (x, dst.y - ARROW_CLEARANCE))
        return points, (x + gap, (src.bottom + dst.y) / 2 + half), "start"
    if edge.key == "replay-contracts":
        x = src.lane(LEFT_LANE)
        points = ((x, src.y - ARROW_CLEARANCE), (x, dst.bottom + ARROW_CLEARANCE))
        return points, (x + gap, (src.y + dst.bottom) / 2 + half), "start"
    if edge.key == "replay-assessment":
        x = src.lane(RIGHT_LANE)
        y = dst.center_y
        points = ((x, src.y - ARROW_CLEARANCE), (x, y), (dst.x - ARROW_CLEARANCE, y))
        return points, (dst.x - ARROW_CLEARANCE, y - gap), "end"
    msg = f"edge {edge.key} has no desktop route"
    raise ValueError(msg)


def _desktop(palette: Palette) -> svg.Node:
    boxes = _desktop_boxes()
    root = svg.document(DESKTOP_WIDTH, DESKTOP_HEIGHT, title=TITLE, desc=DESC)
    root.add("rect", x=0, y=0, width=DESKTOP_WIDTH, height=DESKTOP_HEIGHT, fill=palette.canvas)
    nodes = {
        group.key: root.append(_group_node(group, boxes[group.key], DESKTOP, palette))
        for group in GROUPS
    }
    for edge in EDGES:
        points, (lx, ly), anchor = _desktop_route(edge, boxes)
        color = palette.muted if edge.source == "replay" else palette.accent
        arrow = _arrow(nodes[edge.source], edge, points, color)
        right_edge = DESKTOP_WIDTH - DESKTOP_MARGIN
        max_width = right_edge - lx if anchor == "start" else lx - DESKTOP_MARGIN
        _label(
            arrow,
            edge,
            lx,
            ly,
            anchor=anchor,
            max_width=max_width,
            metrics=DESKTOP,
            palette=palette,
        )
    return root


# --------------------------------------------------------------------------- #
# Mobile
# --------------------------------------------------------------------------- #


def _mobile_layout() -> tuple[dict[str, Box], int]:
    metrics = MOBILE
    width = MOBILE_WIDTH - 2 * MOBILE_MARGIN
    boxes: dict[str, Box] = {}
    y = MOBILE_TOP
    for index, key in enumerate(MOBILE_ORDER):
        height = layout(_group_by_key(key), metrics, width - 2 * metrics.pad).height
        boxes[key] = Box(MOBILE_MARGIN, y, width, height)
        y += height
        if index + 1 < len(MOBILE_ORDER):
            y += MOBILE_GAP
    return boxes, y + MOBILE_TOP


def mobile_height() -> int:
    """Canvas height of the mobile variant, derived from the measured content."""
    return _mobile_layout()[1]


def _mobile_route(edge: Edge, boxes: Mapping[str, Box]) -> tuple[tuple[Point, ...], Point, str]:
    """Spine arrows between neighbours; side channels for the three long edges."""
    metrics = MOBILE
    src, dst = boxes[edge.source], boxes[edge.target]
    gap = metrics.label_gap
    half = metrics.body / 2
    label_x = MOBILE_SPINE + gap
    if edge.key in {
        "cli-contracts",
        "cli-providers",
        "providers-normalization",
        "normalization-assessment",
        "assessment-evidence",
        "evidence-replay",
    }:
        if dst.y > src.y:
            points: tuple[Point, ...] = (
                (MOBILE_SPINE, src.bottom + ARROW_CLEARANCE),
                (MOBILE_SPINE, dst.y - ARROW_CLEARANCE),
            )
            mid = (src.bottom + dst.y) / 2
        else:
            points = (
                (MOBILE_SPINE, src.y - ARROW_CLEARANCE),
                (MOBILE_SPINE, dst.bottom + ARROW_CLEARANCE),
            )
            mid = (src.y + dst.bottom) / 2
        return points, (label_x, mid + half), "start"
    if edge.key == "contracts-assessment":
        y1, y2 = src.bottom - MOBILE_PORT, dst.y + MOBILE_PORT
        points = (
            (src.right + ARROW_CLEARANCE, y1),
            (MOBILE_RIGHT_CHANNEL, y1),
            (MOBILE_RIGHT_CHANNEL, y2),
            (dst.right + ARROW_CLEARANCE, y2),
        )
        return points, (src.right, src.bottom + gap + metrics.body), "end"
    if edge.key == "replay-assessment":
        y1, y2 = src.y + MOBILE_PORT, dst.bottom - MOBILE_PORT
        points = (
            (src.x - ARROW_CLEARANCE, y1),
            (MOBILE_INNER_CHANNEL, y1),
            (MOBILE_INNER_CHANNEL, y2),
            (dst.x - ARROW_CLEARANCE, y2),
        )
        return points, (dst.x, dst.bottom + gap + metrics.body), "start"
    if edge.key == "replay-contracts":
        y1, y2 = src.bottom - MOBILE_PORT, dst.bottom - MOBILE_PORT
        points = (
            (src.x - ARROW_CLEARANCE, y1),
            (MOBILE_OUTER_CHANNEL, y1),
            (MOBILE_OUTER_CHANNEL, y2),
            (dst.x - ARROW_CLEARANCE, y2),
        )
        return points, (dst.x, dst.bottom + gap + metrics.body), "start"
    msg = f"edge {edge.key} has no mobile route"
    raise ValueError(msg)


def _mobile(palette: Palette) -> svg.Node:
    boxes, canvas_height = _mobile_layout()
    root = svg.document(MOBILE_WIDTH, canvas_height, title=TITLE, desc=DESC)
    root.add("rect", x=0, y=0, width=MOBILE_WIDTH, height=canvas_height, fill=palette.canvas)
    nodes = {
        key: root.append(_group_node(_group_by_key(key), boxes[key], MOBILE, palette))
        for key in MOBILE_ORDER
    }
    right_edge = MOBILE_WIDTH - MOBILE_MARGIN
    for edge in EDGES:
        points, (lx, ly), anchor = _mobile_route(edge, boxes)
        color = palette.muted if edge.source == "replay" else palette.accent
        arrow = _arrow(nodes[edge.source], edge, points, color)
        max_width = right_edge - lx if anchor == "start" else lx - MOBILE_MARGIN
        _label(
            arrow, edge, lx, ly, anchor=anchor, max_width=max_width, metrics=MOBILE, palette=palette
        )
    return root


def render(_context: RenderContext) -> Mapping[str, bytes]:
    """Render every declared output; the context is unused (no fonts or tools)."""
    return {
        "architecture-light.svg": svg.serialize_bytes(_desktop(LIGHT)),
        "architecture-dark.svg": svg.serialize_bytes(_desktop(DARK)),
        "architecture-mobile-light.svg": svg.serialize_bytes(_mobile(LIGHT)),
        "architecture-mobile-dark.svg": svg.serialize_bytes(_mobile(DARK)),
    }
