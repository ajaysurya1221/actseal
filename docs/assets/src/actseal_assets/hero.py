"""The hero: the question Actseal answers beside one recorded audit result.

The composition is an evidence card. The left column carries an eyebrow
(``actseal`` and its category), the thesis question in bold and a one-sentence
subline; the card on the right states one real recorded run, the
preregistered live Jev audit, with its scope, its verdict and exit code, and
the archived producer its replay requires. Nothing on the
canvas is decorative: no wordmark banner, padlock, shield, checkmark, badge
or other security symbol.

Every number on the card is copied from committed files under
``docs/results/jev-audit-2026-10-08/`` and is checked against them by
``tests/visual/test_hero.py``:

- ``evidence/verdict.json``: ``total`` 639, ``accepted`` 580, ``errors`` 24,
  ``risk`` [0.02498087158203282, 0.06393316057415596] (shown to four
  decimals), ``coverage`` [0.8787825228681747, 0.9316794056630708] (shown to
  three decimals) and ``status`` INCONCLUSIVE;
- ``audit_receipt.json``: the same verification verdict under
  ``verification_bundle.verdict`` and the cohort counts under
  ``cohorts.verification`` (639 captured, 580 ACT, 24 wrong ACT);
- ``inputs/preregistration.json``: the frozen contract's ``threshold`` 0.8
  and ``max_risk`` 0.05;
- the CLI's exit-code table (``actseal.cli.EXIT_CODES``): INCONCLUSIVE is
  exit 2, which the audit README's offline replay command reports;
- ``README.md`` of the audit: the producer is the unreleased benchmark
  snapshot ``d3edbab2dfbd44a0e9e272e1671143517832e3b4``, so replay requires
  that archived producer (the published 1.0.0 package returns ERROR
  ``integrity.lock`` for this bundle), and the benchmark is a fixed subset.

Every visible string is converted to path data with the pinned JetBrains Mono
files through ``outline.outline_text``; the committed files contain no
``<text>`` and need no font at display time. Only the pinned Regular and Bold
faces are used. The renderer refuses to run without both pinned font files
and never substitutes another face: a missing file raises ``OutlineError``
before any glyph is drawn. The pipeline verifies the font hashes against
``tools.toml`` before calling ``render``; this module only checks presence so
that a direct call still fails loudly.

Two canvases are rendered, each in a light and a dark palette that differ
only in colour. The desktop canvas is 1600x520: the column and the card side
by side. It is validated at the measured 838 CSS px README image width, where
every run renders at 14 px or more (27-unit body runs at 14.1 px, the 40-unit
card headline at 21.0 px, the 46-unit thesis at 24.1 px). GitHub serves the
desktop file at every viewport width (plan/v1/CHANGE_LOG.md V1-057), so on a
254 CSS px phone column the same file renders its body runs at about 4.3 px
and its thesis at about 7.3 px; the README prose above the hero carries the
same recorded result in text. The mobile canvas is 720 wide and stacks the
column above the card; it stays declared, rendered and validated at 254 CSS
px, where every run reaches 14 px (40 units or more) except the card footer, the
repository path and its disclaimer, which is a reference line: its 30-unit
runs render at 10.6 px, above the 10 px reference floor this module enforces
for that line only.

Line breaks are fixed in this file per canvas and must rejoin, with single
spaces, to the frozen copy; every line is measured with the real glyph
advances at render time, and a line that would not fit its column or the
card raises ``ValueError``. Text is never shrunk to fit. Vertical positions
are derived from the stated sizes, line steps and gaps, and a layout that
would leave the margins, overlap the card or overflow the card raises before
anything is drawn.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from . import svg
from .outline import OutlineError, outline_text

if TYPE_CHECKING:
    from .inventory import RenderContext

# --------------------------------------------------------------------------- #
# Frozen copy
# --------------------------------------------------------------------------- #

WORDMARK = "actseal"
EYEBROW = "actseal · frozen decision policies · risk and coverage · offline replay"
THESIS = "Does this frozen action policy meet its declared risk and coverage limits?"
SUBLINE = (
    "Freeze the policy, run it once against labelled cases, bound the errors among "
    "accepted actions, seal the evidence, replay it with no model call."
)
CARD_LABEL = "PREREGISTERED LIVE AUDIT · 639 VERIFICATION CASES · THRESHOLD 0.80"
CARD_HEADLINE = "ACT 580/639   errors 24"
CARD_SCOPE = "Fixed benchmark; unreleased producer"
CARD_BOUNDS = "risk [0.0250, 0.0639] vs limit 0.05 · coverage [0.879, 0.932]"
CARD_VERDICT = "VERDICT: INCONCLUSIVE (exit 2) → replay requires archived producer d3edbab"
CARD_FOOTER = "docs/results/jev-audit-2026-10-08 · neither PASS nor BLOCK is claimed"

TITLE = "Actseal: does this frozen action policy meet its declared risk and coverage limits?"
DESC = (
    f"{EYEBROW}. {THESIS} {SUBLINE} Evidence card: {CARD_LABEL}. "
    f"ACT 580 of 639, errors 24. {CARD_SCOPE}. "
    f"{CARD_BOUNDS}. {CARD_VERDICT}. {CARD_FOOTER}."
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
DESKTOP_HEIGHT = 520
MOBILE_WIDTH = 720
MOBILE_HEIGHT = 1576
# Measured CSS widths of a README image (838 px at 1280/1366 px viewports,
# 254 px at 320 px); the same values as inventory.py, repeated here because
# inventory imports this module.
DESKTOP_DISPLAY_WIDTH = 838
MOBILE_DISPLAY_WIDTH = 254
# Same floor as checks.MIN_LABEL_PX; outlined assets are exempt from that
# validator, so this module enforces the floor on its own type sizes.
MIN_LABEL_PX = 14.0
# Floor for the one reference line (the card footer: repository path and
# disclaimer), which only the stacked mobile canvas sets below MIN_LABEL_PX.
MIN_REFERENCE_PX = 10.0
# Smallest unit sizes that reach MIN_LABEL_PX: 14 x 1600 / 838 = 26.7 desktop
# units and 14 x 720 / 254 = 39.7 mobile units, rounded up.
MIN_DESKTOP_TEXT = 27
MIN_MOBILE_TEXT = 40

# Ascender allowance above a block's first baseline and descender allowance
# below its last, as fractions of the type size. The pinned faces reach
# 0.73 em (capitals) and 0.61 em (the arrow) above the baseline and 0.18 em
# below it for this copy; both allowances are deliberately larger.
ASCENT = 0.8
DESCENDER = 0.3


@dataclass(frozen=True, slots=True)
class Palette:
    name: str
    canvas: str
    heading: str
    body: str
    muted: str
    accent: str
    card: str
    card_text: str
    card_muted: str
    blue: str
    red: str
    amber: str


# Dark: a light card on the dark ground. Light: an ink card on cream.
DARK = Palette(
    name="dark",
    canvas="#0F1512",
    heading="#F0ECE2",
    body="#C9C4B6",
    muted="#9A978E",
    accent="#6FA2FF",
    card="#F4F1EA",
    card_text="#16211D",
    card_muted="#6B6A65",
    blue="#1F5FD1",
    red="#B8431F",
    amber="#8A5A00",
)
LIGHT = Palette(
    name="light",
    canvas="#F4F1EA",
    heading="#16211D",
    body="#3E3D38",
    muted="#6B6A65",
    accent="#1F5FD1",
    card="#16211D",
    card_text="#E9E4D8",
    card_muted="#A8A396",
    blue="#6FA2FF",
    red="#F0A48A",
    amber="#E8B14A",
)
ROLES: tuple[str, ...] = (
    "heading",
    "body",
    "muted",
    "accent",
    "card_text",
    "card_muted",
    "blue",
    "red",
    "amber",
)


@dataclass(frozen=True, slots=True)
class Highlight:
    """A phrase of one copy block drawn in another colour role, optionally bold."""

    phrase: str
    role: str
    bold: bool = False


@dataclass(frozen=True, slots=True)
class Copy:
    """One frozen block of copy: its text, colour role, weight and highlights."""

    key: str
    text: str
    role: str
    bold: bool = False
    highlights: tuple[Highlight, ...] = ()
    in_card: bool = False
    #: A reference line may render below MIN_LABEL_PX, down to MIN_REFERENCE_PX.
    reference: bool = False


COPY: tuple[Copy, ...] = (
    Copy("eyebrow", EYEBROW, "muted", highlights=(Highlight(WORDMARK, "accent", bold=True),)),
    Copy("thesis", THESIS, "heading", bold=True),
    Copy("subline", SUBLINE, "body"),
    Copy("card-label", CARD_LABEL, "card_muted", in_card=True),
    Copy(
        "card-headline",
        CARD_HEADLINE,
        "card_text",
        bold=True,
        highlights=(Highlight("580/639", "blue", bold=True), Highlight("24", "red", bold=True)),
        in_card=True,
    ),
    Copy("card-scope", CARD_SCOPE, "card_text", in_card=True),
    Copy(
        "card-bounds",
        CARD_BOUNDS,
        "card_text",
        highlights=(Highlight("[0.0250, 0.0639]", "red"),),
        in_card=True,
    ),
    Copy(
        "card-verdict",
        CARD_VERDICT,
        "card_text",
        highlights=(Highlight("VERDICT: INCONCLUSIVE (exit 2)", "amber", bold=True),),
        in_card=True,
    ),
    Copy("card-footer", CARD_FOOTER, "card_muted", in_card=True, reference=True),
)
COLUMN_KEYS: tuple[str, ...] = tuple(c.key for c in COPY if not c.in_card)
CARD_KEYS: tuple[str, ...] = tuple(c.key for c in COPY if c.in_card)


def copy_for(key: str) -> Copy:
    for block in COPY:
        if block.key == key:
            return block
    msg = f"unknown copy block {key!r}"
    raise KeyError(msg)


@dataclass(frozen=True, slots=True)
class Setting:
    """One copy block set on one canvas: fixed line breaks, size, line step and gap above."""

    key: str
    lines: tuple[str, ...]
    size: int
    step: int
    gap: int = 0

    @property
    def above(self) -> int:
        return math.ceil(self.size * ASCENT)

    @property
    def below(self) -> int:
        return math.ceil(self.size * DESCENDER)

    @property
    def box_height(self) -> int:
        """Ascender allowance, the line steps and the descender allowance, in units."""
        return self.above + (len(self.lines) - 1) * self.step + self.below


@dataclass(frozen=True, slots=True)
class Canvas:
    """Geometry and type settings for one variant, in SVG units."""

    name: str
    width: int
    height: int
    display_width: int
    margin: int
    column_x: int
    column_y: int
    column_width: int
    card_x: int
    card_y: int
    card_width: int
    card_height: int
    card_pad: int
    radius: int
    column: tuple[Setting, ...]
    card: tuple[Setting, ...]

    @property
    def settings(self) -> tuple[Setting, ...]:
        return (*self.column, *self.card)

    @property
    def sizes(self) -> tuple[int, ...]:
        return tuple(setting.size for setting in self.settings)

    def setting(self, key: str) -> Setting:
        for setting in self.settings:
            if setting.key == key:
                return setting
        msg = f"{self.name}: no setting for {key!r}"
        raise KeyError(msg)

    @property
    def card_inner_width(self) -> int:
        return self.card_width - 2 * self.card_pad

    @property
    def column_bottom(self) -> int:
        return self.column_y + _stack_height(self.column)

    @property
    def card_content_bottom(self) -> int:
        return self.card_y + self.card_pad + _stack_height(self.card)

    @property
    def side_by_side(self) -> bool:
        return self.column_x + self.column_width <= self.card_x

    def rendered_px(self, size: float) -> float:
        """Size of ``size`` units after scaling the canvas to its display width."""
        return size * min(1.0, self.display_width / self.width)


def _stack_height(settings: tuple[Setting, ...]) -> int:
    return sum(setting.gap + setting.box_height for setting in settings)


@dataclass(frozen=True, slots=True)
class Placed:
    """One setting with its absolute left edge, available width and baselines."""

    setting: Setting
    x: int
    max_width: int
    baselines: tuple[int, ...]
    top: int
    bottom: int


def place(canvas: Canvas) -> tuple[Placed, ...]:
    """Stack the column and the card blocks from their tops; nothing is measured here."""
    placed: list[Placed] = []
    containers = (
        (canvas.column, canvas.column_x, canvas.column_width, canvas.column_y),
        (
            canvas.card,
            canvas.card_x + canvas.card_pad,
            canvas.card_inner_width,
            canvas.card_y + canvas.card_pad,
        ),
    )
    for settings, x, width, top in containers:
        cursor = top
        for setting in settings:
            box_top = cursor + setting.gap
            first = box_top + setting.above
            baselines = tuple(first + i * setting.step for i in range(len(setting.lines)))
            bottom = box_top + setting.box_height
            placed.append(Placed(setting, x, width, baselines, box_top, bottom))
            cursor = bottom
    return tuple(placed)


# The desktop composition: column and card side by side, validated at 838 CSS px.
DESKTOP = Canvas(
    name="desktop",
    width=DESKTOP_WIDTH,
    height=DESKTOP_HEIGHT,
    display_width=DESKTOP_DISPLAY_WIDTH,
    margin=40,
    column_x=64,
    column_y=50,
    column_width=692,
    card_x=804,
    card_y=40,
    card_width=732,
    card_height=440,
    card_pad=26,
    radius=16,
    column=(
        Setting(
            "eyebrow",
            ("actseal · frozen decision policies ·", "risk and coverage · offline replay"),
            27,
            36,
        ),
        Setting(
            "thesis",
            ("Does this frozen action", "policy meet its declared", "risk and coverage limits?"),
            46,
            52,
            gap=30,
        ),
        Setting(
            "subline",
            (
                "Freeze the policy, run it once against",
                "labelled cases, bound the errors among",
                "accepted actions, seal the evidence,",
                "replay it with no model call.",
            ),
            27,
            36,
            gap=30,
        ),
    ),
    card=(
        Setting(
            "card-label",
            ("PREREGISTERED LIVE AUDIT ·", "639 VERIFICATION CASES · THRESHOLD 0.80"),
            27,
            34,
        ),
        Setting("card-headline", (CARD_HEADLINE,), 40, 48, gap=12),
        Setting("card-scope", (CARD_SCOPE,), 27, 34, gap=5),
        Setting(
            "card-bounds",
            ("risk [0.0250, 0.0639] vs limit 0.05 ·", "coverage [0.879, 0.932]"),
            27,
            34,
            gap=12,
        ),
        Setting(
            "card-verdict",
            ("VERDICT: INCONCLUSIVE (exit 2) →", "replay requires archived producer d3edbab"),
            27,
            34,
            gap=12,
        ),
        Setting(
            "card-footer",
            ("docs/results/jev-audit-2026-10-08 ·", "neither PASS nor BLOCK is claimed"),
            27,
            34,
            gap=12,
        ),
    ),
)

# The stacked mobile composition: the column above the card, validated at
# 254 CSS px. Every run is at least 40 units except the 30-unit footer.
MOBILE = Canvas(
    name="mobile",
    width=MOBILE_WIDTH,
    height=MOBILE_HEIGHT,
    display_width=MOBILE_DISPLAY_WIDTH,
    margin=16,
    column_x=28,
    column_y=32,
    column_width=664,
    card_x=16,
    card_y=742,
    card_width=688,
    card_height=803,
    card_pad=26,
    radius=16,
    column=(
        Setting(
            "eyebrow",
            ("actseal · frozen decision", "policies · risk and", "coverage · offline replay"),
            40,
            52,
        ),
        Setting(
            "thesis",
            ("Does this frozen action", "policy meet its declared", "risk and coverage limits?"),
            44,
            54,
            gap=32,
        ),
        Setting(
            "subline",
            (
                "Freeze the policy, run it",
                "once against labelled",
                "cases, bound the errors",
                "among accepted actions,",
                "seal the evidence, replay",
                "it with no model call.",
            ),
            40,
            52,
            gap=32,
        ),
    ),
    card=(
        Setting(
            "card-label",
            ("PREREGISTERED LIVE AUDIT ·", "639 VERIFICATION CASES ·", "THRESHOLD 0.80"),
            40,
            52,
        ),
        Setting("card-headline", (CARD_HEADLINE,), 44, 54, gap=20),
        Setting("card-scope", ("Fixed benchmark;", "unreleased producer"), 40, 52, gap=8),
        Setting(
            "card-bounds",
            ("risk [0.0250, 0.0639]", "vs limit 0.05 ·", "coverage [0.879, 0.932]"),
            40,
            52,
            gap=20,
        ),
        Setting(
            "card-verdict",
            ("VERDICT: INCONCLUSIVE", "(exit 2) → replay requires", "archived producer d3edbab"),
            40,
            52,
            gap=20,
        ),
        Setting(
            "card-footer",
            ("docs/results/jev-audit-2026-10-08 ·", "neither PASS nor BLOCK is claimed"),
            30,
            40,
            gap=20,
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class Fonts:
    regular: Path
    bold: Path


# --------------------------------------------------------------------------- #
# Checks that run before any font is read
# --------------------------------------------------------------------------- #


def _spans_of(copy: Copy) -> list[tuple[int, int, Highlight]]:
    """Character ranges of each highlight in the copy; each phrase must occur once."""
    ranges: list[tuple[int, int, Highlight]] = []
    for highlight in copy.highlights:
        count = copy.text.count(highlight.phrase)
        if count != 1:
            msg = f"{copy.key}: highlight {highlight.phrase!r} occurs {count} times; expected once"
            raise ValueError(msg)
        start = copy.text.index(highlight.phrase)
        ranges.append((start, start + len(highlight.phrase), highlight))
    ranges.sort(key=lambda item: item[0])
    for (_, end, first), (start, _, second) in itertools.pairwise(ranges):
        if start < end:
            msg = f"{copy.key}: highlights {first.phrase!r} and {second.phrase!r} overlap"
            raise ValueError(msg)
    return ranges


def validate_copy(canvases: tuple[Canvas, ...] | None = None) -> None:
    """Every canvas must set every block once, in order, with lines that rejoin to the copy."""
    for copy in COPY:
        if copy.role not in ROLES:
            msg = f"{copy.key}: unknown colour role {copy.role!r}"
            raise ValueError(msg)
        for highlight in copy.highlights:
            if highlight.role not in ROLES:
                msg = f"{copy.key}: unknown colour role {highlight.role!r}"
                raise ValueError(msg)
        _spans_of(copy)
    for canvas in canvases if canvases is not None else (DESKTOP, MOBILE):
        column = tuple(s.key for s in canvas.column)
        card = tuple(s.key for s in canvas.card)
        if column != COLUMN_KEYS or card != CARD_KEYS:
            msg = (
                f"{canvas.name}: blocks {column + card!r} do not match {COLUMN_KEYS + CARD_KEYS!r}"
            )
            raise ValueError(msg)
        for setting in canvas.settings:
            text = copy_for(setting.key).text
            stripped = all(line and line == line.strip() for line in setting.lines)
            if not stripped or " ".join(setting.lines) != text:
                msg = (
                    f"{canvas.name}: {setting.key} lines do not rejoin to the frozen copy: "
                    f"{setting.lines!r}"
                )
                raise ValueError(msg)


def require_readable(canvas: Canvas) -> None:
    """Every run must render at or above its floor at the canvas's display width."""
    for setting in canvas.settings:
        reference = copy_for(setting.key).reference
        floor = MIN_REFERENCE_PX if reference else MIN_LABEL_PX
        rendered = canvas.rendered_px(setting.size)
        if rendered < floor:
            msg = (
                f"{canvas.name}: {setting.key} at {setting.size} units renders at "
                f"{rendered:.1f}px at {canvas.display_width} CSS px; minimum is {floor:g}px"
            )
            raise ValueError(msg)


def require_text_minimum(canvas: Canvas, minimum: int) -> None:
    """Every run except the reference line must be at least ``minimum`` units."""
    for setting in canvas.settings:
        if copy_for(setting.key).reference:
            continue
        if setting.size < minimum:
            msg = (
                f"{canvas.name}: {setting.key} is {setting.size} units; minimum is {minimum} units"
            )
            raise ValueError(msg)


def require_layout(canvas: Canvas) -> None:
    """The fixed geometry must stay inside the margins, the card and its own column."""
    problems: list[str] = []
    right = canvas.width - canvas.margin
    bottom = canvas.height - canvas.margin
    if canvas.column_x < canvas.margin or canvas.column_x + canvas.column_width > right:
        problems.append("text column exceeds the canvas width")
    if canvas.card_x < canvas.margin or canvas.card_x + canvas.card_width > right:
        problems.append("card exceeds the canvas width")
    if canvas.card_y < canvas.margin or canvas.card_y + canvas.card_height > bottom:
        problems.append(
            f"card spans {canvas.card_y}..{canvas.card_y + canvas.card_height} units; "
            f"the margins allow {canvas.margin}..{bottom}"
        )
    if canvas.column_y < canvas.margin:
        problems.append(f"text column starts {canvas.column_y} units from the top")
    column_limit = bottom if canvas.side_by_side else canvas.card_y
    if canvas.column_bottom > column_limit:
        problems.append(f"text column needs {canvas.column_bottom} units; limit is {column_limit}")
    if not canvas.side_by_side and canvas.column_bottom > canvas.card_y:
        problems.append("text column overlaps the card")
    card_limit = canvas.card_y + canvas.card_height - canvas.card_pad
    if canvas.card_content_bottom > card_limit:
        problems.append(
            f"card content needs {canvas.card_content_bottom} units; limit is {card_limit}"
        )
    if canvas.card_inner_width <= 0:
        problems.append("card padding leaves no room for text")
    for setting in canvas.settings:
        if setting.gap < 0 or setting.step <= 0 or setting.size <= 0:
            problems.append(f"{setting.key} has a negative gap or a non-positive size or step")
        elif len(setting.lines) > 1 and setting.step < setting.size:
            problems.append(
                f"{setting.key} lines overlap: step {setting.step} < size {setting.size}"
            )
    if problems:
        msg = f"{canvas.name} layout does not fit a {canvas.width}x{canvas.height} canvas: " + (
            "; ".join(problems)
        )
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


def prepare(canvas: Canvas, minimum: int) -> None:
    """Every font-free check for one canvas, in the order ``render`` applies them."""
    validate_copy((canvas,))
    require_text_minimum(canvas, minimum)
    require_readable(canvas)
    require_layout(canvas)


# --------------------------------------------------------------------------- #
# Drawing
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class Span:
    text: str
    role: str
    bold: bool


def line_spans(copy: Copy, lines: tuple[str, ...]) -> list[list[Span]]:
    """Split each line into colour spans; a highlight may continue onto the next line."""
    ranges = _spans_of(copy)
    result: list[list[Span]] = []
    offset = 0
    for line in lines:
        start, end = offset, offset + len(line)
        cuts = {start, end}
        for low, high, _ in ranges:
            cuts.update(point for point in (low, high) if start < point < end)
        points = sorted(cuts)
        spans: list[Span] = []
        for low, high in itertools.pairwise(points):
            role, bold = copy.role, copy.bold
            for h_low, h_high, highlight in ranges:
                if h_low <= low and high <= h_high:
                    role, bold = highlight.role, highlight.bold or copy.bold
            spans.append(Span(copy.text[low:high], role, bold))
        result.append(spans)
        offset = end + 1  # the single space each line break replaces
    return result


def _measure(fonts: Fonts, spans: list[Span], size: float) -> float:
    return sum(
        outline_text(fonts.bold if span.bold else fonts.regular, span.text, size=size).advance
        for span in spans
    )


def _block(
    root: svg.Node, fonts: Fonts, palette: Palette, placed: Placed, *, canvas_name: str
) -> None:
    setting = placed.setting
    copy = copy_for(setting.key)
    group = root.add("g", id=setting.key)
    for line, spans, baseline in zip(
        setting.lines, line_spans(copy, setting.lines), placed.baselines, strict=True
    ):
        width = _measure(fonts, spans, setting.size)
        if width > placed.max_width:
            msg = (
                f"{canvas_name}: {line!r} is {width:.1f} units wide at size {setting.size}; "
                f"only {placed.max_width} units are available. Text is not shrunk; "
                "change the layout or the line breaks"
            )
            raise ValueError(msg)
        x = float(placed.x)
        for span in spans:
            font = fonts.bold if span.bold else fonts.regular
            outline = outline_text(font, span.text, size=setting.size, x=x, y=baseline)
            if outline.d:
                group.add("path", d=outline.d, fill=getattr(palette, span.role))
            x += outline.advance


def compose(canvas: Canvas, palette: Palette, fonts: Fonts) -> svg.Node:
    """Draw one variant: ground, the text column, then the card and its blocks."""
    root = svg.document(canvas.width, canvas.height, title=TITLE, desc=DESC)
    root.add("rect", x=0, y=0, width=canvas.width, height=canvas.height, fill=palette.canvas)
    placed = place(canvas)
    column = root.add("g", id="column")
    for item in placed[: len(canvas.column)]:
        _block(column, fonts, palette, item, canvas_name=canvas.name)
    card = root.add("g", id="card")
    card.add(
        "rect",
        x=canvas.card_x,
        y=canvas.card_y,
        width=canvas.card_width,
        height=canvas.card_height,
        rx=canvas.radius,
        fill=palette.card,
    )
    for item in placed[len(canvas.column) :]:
        _block(card, fonts, palette, item, canvas_name=canvas.name)
    return root


def render(context: RenderContext) -> Mapping[str, bytes]:
    """Render every declared output from the pinned fonts, or fail before drawing."""
    prepare(DESKTOP, MIN_DESKTOP_TEXT)
    prepare(MOBILE, MIN_MOBILE_TEXT)
    fonts = require_fonts(context)
    return {
        "hero-light.svg": svg.serialize_bytes(compose(DESKTOP, LIGHT, fonts)),
        "hero-dark.svg": svg.serialize_bytes(compose(DESKTOP, DARK, fonts)),
        "hero-mobile-light.svg": svg.serialize_bytes(compose(MOBILE, LIGHT, fonts)),
        "hero-mobile-dark.svg": svg.serialize_bytes(compose(MOBILE, DARK, fonts)),
    }
