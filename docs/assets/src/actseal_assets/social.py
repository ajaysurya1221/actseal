"""The GitHub social preview: the hero's evidence-card composition as one 1280x640 PNG.

The composition is the hero's, unchanged in copy and structure: the text
column (eyebrow, thesis question, subline) beside the card that states the
recorded preregistered audit, in the hero's light palette (cream ground, ink
card). Only the line breaks, sizes and positions differ, because the card is
re-flowed for the 1280x640 canvas rather than scaled: scaling the 1600-unit
desktop composition down would put its body text below the 14 px floor at the
assumed half-scale display. Nothing is added: no further claim, no padlock,
shield, checkmark, badge or other security symbol, no new copy. Every visible
string is outlined through the hero's helpers from the pinned JetBrains Mono
files, so the intermediate SVG carries no ``<text>``; its title and
description are the hero's.

Rasterization uses only the pinned resvg binary, re-verified against
``tools.toml`` by ``tools.verified_binary`` and run through
``tools.resvg_command`` (explicit size, only the pinned font directory, system
fonts skipped) and ``tools.run_tool``. The renderer fails before drawing when
a pinned font file is missing and before outlining when resvg is not cached
and verified; it never substitutes a font or a rasterizer. Text is measured
with the real glyph advances and never shrunk to fit; a PNG that is not
exactly 1280x640 is an error.

The single output is ``social.png``, an upload-ready file. Attaching it to the
repository's social preview is a manual step this module neither performs nor
records.

``tools`` is imported lazily: it from-imports inventory constants at module
load, and ``inventory`` imports this module to register the renderer, so a
module-level import here would be circular.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING

from . import checks, hero, svg

if TYPE_CHECKING:
    from .inventory import RenderContext

OUTPUT = "social.png"
SOURCE = "social.svg"
# Same values as inventory.SOCIAL_WIDTH / SOCIAL_HEIGHT, repeated here because
# inventory imports this module.
WIDTH = 1280
HEIGHT = 640
# Assumed narrowest display of the card in link unfurls (half scale). Type
# sizes are checked against the 14 px floor at this width; the rendered review
# confirms or corrects the assumption. Nothing here measures a renderer.
DISPLAY_WIDTH = 640
# 14 px at 640 CSS px on the 1280-unit canvas: 28 units. On this card every
# run, the reference footer included, is at least this size.
MIN_TEXT = 28
RESVG = "resvg"
PALETTE = hero.LIGHT

# The hero's column and card, re-flowed for 1280x640: a 484-unit column at
# x 56 and a 644-unit card at x 580, each leaving 56 units at its outer side;
# the column is centred on the card's height.
CANVAS = hero.Canvas(
    name="social",
    width=WIDTH,
    height=HEIGHT,
    display_width=DISPLAY_WIDTH,
    margin=40,
    column_x=56,
    column_y=50,
    column_width=484,
    card_x=580,
    card_y=40,
    card_width=644,
    card_height=560,
    card_pad=26,
    radius=16,
    column=(
        hero.Setting(
            "eyebrow",
            ("actseal · frozen decision", "policies · risk and", "coverage · offline replay"),
            28,
            37,
        ),
        hero.Setting(
            "thesis",
            ("Does this frozen", "action policy meet its", "declared risk and", "coverage limits?"),
            36,
            42,
            gap=26,
        ),
        hero.Setting(
            "subline",
            (
                "Freeze the policy, run it",
                "once against labelled cases,",
                "bound the errors among",
                "accepted actions, seal the",
                "evidence, replay it with no",
                "model call.",
            ),
            28,
            37,
            gap=26,
        ),
    ),
    card=(
        hero.Setting(
            "card-label",
            ("PREREGISTERED LIVE AUDIT · 639", "VERIFICATION CASES · THRESHOLD 0.80"),
            28,
            37,
        ),
        hero.Setting("card-headline", (hero.CARD_HEADLINE,), 36, 42, gap=20),
        hero.Setting("card-scope", ("Fixed benchmark;", "unreleased producer"), 28, 37, gap=6),
        hero.Setting(
            "card-bounds",
            ("risk [0.0250, 0.0639] vs limit", "0.05 · coverage [0.879, 0.932]"),
            28,
            37,
            gap=20,
        ),
        hero.Setting(
            "card-verdict",
            ("VERDICT: INCONCLUSIVE (exit 2)", "→ replay requires archived", "producer d3edbab"),
            28,
            37,
            gap=20,
        ),
        hero.Setting(
            "card-footer",
            ("docs/results/jev-audit-2026-10-08 ·", "neither PASS nor BLOCK is claimed"),
            28,
            37,
            gap=20,
        ),
    ),
)


def require_card_minimum(canvas: hero.Canvas) -> None:
    """Every run on the card, the reference footer included, must reach MIN_TEXT units."""
    for setting in canvas.settings:
        if setting.size < MIN_TEXT:
            msg = f"{canvas.name}: {setting.key} is {setting.size} units; minimum is {MIN_TEXT}"
            raise ValueError(msg)


def require_resvg(context: RenderContext) -> Path:
    """The pinned resvg binary must be cached and re-verified; nothing else rasterizes."""
    from . import tools  # noqa: PLC0415 - circular with inventory; see module docstring

    manifest_path = tools.default_manifest_path(context.root)
    tool = tools.load_manifest(manifest_path).get(RESVG)
    if tool is None:
        msg = f"{RESVG} is not pinned in {manifest_path}"
        raise tools.ToolError(msg)
    return tools.verified_binary(context.root, tool)


def compose(fonts: hero.Fonts) -> bytes:
    """The outlined 1280x640 SVG, serialized canonically, drawn by the hero's code."""
    return svg.serialize_bytes(hero.compose(CANVAS, PALETTE, fonts))


def require_dimensions(data: bytes) -> bytes:
    """``data`` must be a PNG of exactly the social size; anything else is an error."""
    width, height = checks.png_dimensions(data)
    if (width, height) != (WIDTH, HEIGHT):
        msg = (
            f"resvg produced a {width}x{height} PNG; the social preview must be "
            f"exactly {WIDTH}x{HEIGHT}"
        )
        raise ValueError(msg)
    return data


def rasterize(resvg: Path, document: bytes, context: RenderContext) -> bytes:
    """Write the SVG into ``context.work`` and rasterize it with the verified binary."""
    from . import tools  # noqa: PLC0415 - circular with inventory; see module docstring

    context.work.mkdir(parents=True, exist_ok=True)
    source = context.work / SOURCE
    target = context.work / OUTPUT
    # A stale file from an earlier run must never be mistaken for this run's output.
    target.unlink(missing_ok=True)
    source.write_bytes(document)
    command = tools.resvg_command(
        resvg, source, target, width=WIDTH, height=HEIGHT, font_dir=context.fonts
    )
    tools.run_tool(command)
    if not target.is_file():
        msg = f"{resvg} exited 0 but did not write {target}"
        raise tools.ToolError(msg)
    return require_dimensions(target.read_bytes())


def render(context: RenderContext) -> Mapping[str, bytes]:
    """Render ``social.png`` from the pinned fonts and resvg, or fail before drawing."""
    hero.prepare(CANVAS, MIN_TEXT)
    require_card_minimum(CANVAS)
    fonts = hero.require_fonts(context)
    resvg = require_resvg(context)
    return {OUTPUT: rasterize(resvg, compose(fonts), context)}
