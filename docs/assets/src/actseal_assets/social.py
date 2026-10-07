"""The GitHub social preview: the approved hero composition as one 1280x640 PNG.

The composition is the hero's, unchanged in copy and symbolism: the "Actseal"
wordmark, the approved tagline, one freeze/run/replay loop and the
evidence-boundary caption, stacked on a 1280x640 canvas in the hero's light
palette. Nothing is added: no further claim, no padlock, shield or other
security symbol, no new copy. Every visible string is outlined through the
hero's helpers from the pinned JetBrains Mono files, so the intermediate SVG
carries no ``<text>``; its generic title and description are the hero's.

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
RESVG = "resvg"
PALETTE = hero.LIGHT

# Stacked like the hero's mobile variant, at social-card proportions. The
# motif spans the full text column; the caption keeps the hero's desktop line
# break. All sizes are in SVG units on the 1280x640 canvas.
CANVAS = hero.Canvas(
    name="social",
    width=WIDTH,
    display_width=DISPLAY_WIDTH,
    margin=40,
    text_x=64,
    text_width=1152,
    wordmark=120,
    wordmark_baseline=150,
    tagline=48,
    tagline_baseline=222,
    tagline_step=58,
    caption=36,
    caption_baseline=532,
    caption_step=46,
    caption_lines=hero.DESKTOP_CAPTION_LINES,
    label=36,
    motif_x=64,
    motif_top=330,
    pill_width=320,
    pill_height=80,
    pill_gap=96,
    pill_pad=16,
    loop_drop=60,
)


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
    """The outlined 1280x640 SVG, serialized canonically.

    Reuses the hero's variant builder so the wordmark, tagline, motif and
    caption are drawn by the same code as the banner; only the canvas differs.
    """
    # hero exposes no public composition entry point; its variant builder is
    # reused as-is rather than duplicating the layout code here.
    return svg.serialize_bytes(hero._variant(CANVAS, HEIGHT, PALETTE, fonts))


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
    hero.validate_copy()
    fonts = hero.require_fonts(context)
    resvg = require_resvg(context)
    return {OUTPUT: rasterize(resvg, compose(fonts), context)}
