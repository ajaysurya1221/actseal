"""Glyph outlining with fontTools; skipped in the core environment."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

import pytest

fontBuilder = pytest.importorskip("fontTools.fontBuilder")  # noqa: N816 - fontTools module name
pens = pytest.importorskip("fontTools.pens.ttGlyphPen")

ADVANCE = 600
UPEM = 1000


@pytest.fixture(scope="module")
def square_font(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A one-glyph TrueType font: 'A' is a 500-unit square with a 600-unit advance."""
    builder = fontBuilder.FontBuilder(UPEM, isTTF=True)
    builder.setupGlyphOrder([".notdef", "A"])
    builder.setupCharacterMap({ord("A"): "A"})
    pen = pens.TTGlyphPen(None)
    pen.moveTo((0, 0))
    pen.lineTo((500, 0))
    pen.lineTo((500, 500))
    pen.lineTo((0, 500))
    pen.closePath()
    square = pen.glyph()
    empty = pens.TTGlyphPen(None).glyph()
    builder.setupGlyf({".notdef": empty, "A": square})
    builder.setupHorizontalMetrics({".notdef": (ADVANCE, 0), "A": (ADVANCE, 0)})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable({"familyName": "Probe", "styleName": "Regular"})
    builder.setupOS2()
    builder.setupPost()
    path = tmp_path_factory.mktemp("font") / "Probe.ttf"
    builder.save(str(path))
    return path


def test_outline_is_deterministic_and_scaled(kit: ModuleType, square_font: Path) -> None:
    first = kit.outline.outline_text(square_font, "AA", size=100, x=10, y=200)
    second = kit.outline.outline_text(square_font, "AA", size=100, x=10, y=200)
    assert first == second
    assert first.advance == 120
    assert first.d.startswith("M10 200")
    assert "M70 200" in first.d
    assert "150" in first.d
    assert "<text" not in first.d


def test_tracking_is_applied_after_every_glyph(kit: ModuleType, square_font: Path) -> None:
    spaced = kit.outline.outline_text(square_font, "AA", size=50, tracking=5)
    assert spaced.advance == 70
    assert "M35 0" in spaced.d


def test_missing_glyph_is_an_error_not_a_fallback(kit: ModuleType, square_font: Path) -> None:
    with pytest.raises(kit.outline.OutlineError, match="no glyph for 'B'"):
        kit.outline.outline_text(square_font, "AB", size=50)


def test_missing_font_and_bad_size_are_errors(kit: ModuleType, square_font: Path) -> None:
    with pytest.raises(kit.outline.OutlineError, match="is missing"):
        kit.outline.outline_text(square_font.with_name("none.ttf"), "A", size=50)
    with pytest.raises(kit.outline.OutlineError, match="must be positive"):
        kit.outline.outline_text(square_font, "A", size=0)


def test_outlined_text_passes_the_outlined_check(kit: ModuleType, square_font: Path) -> None:
    glyphs = kit.outline.outline_text(square_font, "AA", size=120, x=40, y=300)
    root = kit.svg.document(1600, 400, title="Probe banner", desc="Outlined probe text.")
    root.add("path", d=glyphs.d, fill="#111111")
    output = kit.inventory.Output(
        path="probe.svg", kind="svg", width=1600, height=400, outlined=True
    )
    assert kit.checks.check_svg(kit.svg.serialize_bytes(root), output) == []


def test_unavailable_fonttools_raises_outline_error(
    kit: ModuleType, square_font: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(sys.modules, "fontTools", None)
    with pytest.raises(kit.outline.OutlineError, match="fontTools is required"):
        kit.outline.outline_text(square_font, "A", size=50)
