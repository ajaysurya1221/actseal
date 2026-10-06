"""Glyph outlining for banner text.

Converts a string to SVG path data using the pinned font file, so committed
banners contain no ``<text>`` and need no font at display time. fontTools is
imported lazily; nothing else in the toolchain depends on it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .svg import fmt


class OutlineError(RuntimeError):
    """A glyph could not be outlined; nothing is substituted silently."""


@dataclass(frozen=True, slots=True)
class Outline:
    d: str
    advance: float


def outline_text(
    font_path: Path,
    text: str,
    *,
    size: float,
    x: float = 0.0,
    y: float = 0.0,
    tracking: float = 0.0,
) -> Outline:
    """Return path data for ``text`` with its baseline at ``y`` starting at ``x``.

    Glyphs are placed by advance width plus ``tracking``; kerning is not
    applied. Characters without a glyph raise ``OutlineError``.
    """
    try:
        from fontTools import (  # type: ignore[import-untyped]  # noqa: PLC0415 - optional authoring dependency
            ttLib,
        )
        from fontTools.pens import (  # type: ignore[import-untyped]  # noqa: PLC0415 - optional authoring dependency
            svgPathPen,
            transformPen,
        )
    except ImportError as exc:
        msg = "fontTools is required for outlining; install the assets dependency group"
        raise OutlineError(msg) from exc
    if size <= 0:
        msg = f"font size must be positive, got {size!r}"
        raise OutlineError(msg)
    if not font_path.is_file():
        msg = f"font file {font_path} is missing; run setup_tools.py"
        raise OutlineError(msg)
    font = ttLib.TTFont(str(font_path))
    cmap = font.getBestCmap()
    glyph_set = font.getGlyphSet()
    units_per_em = int(font["head"].unitsPerEm)
    metrics = font["hmtx"]
    scale = size / units_per_em
    parts: list[str] = []
    pen_x = x
    for char in text:
        name = cmap.get(ord(char))
        if name is None:
            msg = f"{font_path.name} has no glyph for {char!r} (U+{ord(char):04X})"
            raise OutlineError(msg)
        pen = svgPathPen.SVGPathPen(glyph_set, ntos=fmt)
        transform = transformPen.TransformPen(pen, (scale, 0, 0, -scale, pen_x, y))
        glyph_set[name].draw(transform)
        commands = str(pen.getCommands())
        if commands:
            parts.append(commands)
        advance_units = int(metrics[name][0])
        pen_x += advance_units * scale + tracking
    return Outline(" ".join(parts), pen_x - x)
