"""Copy, declarations, readability floors and fail-loud behaviour of the hero banner.

Two kinds of test live here. The first kind needs no font and no fontTools:
exact copy, inventory declarations, type-size floors and the explicit
failures when the pinned fonts are absent. The second kind renders with
**unit-double fonts** built in a temporary directory: every glyph is a plain
rectangle with a 600/1000 em advance. Those doubles exercise the pipeline
wiring, determinism and validators only. They are not the pinned JetBrains
Mono files, they prove nothing about glyph appearance or readability, and
nothing in this module downloads or copies a font.
"""

from __future__ import annotations

import dataclasses
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

SVG_NS = "{http://www.w3.org/2000/svg}"
DESKTOP = ("hero-light.svg", "hero-dark.svg")
MOBILE = ("hero-mobile-light.svg", "hero-mobile-dark.svg")
WORDMARK = "Actseal"
TAGLINE = "Test model-chosen actions. Replay the evidence."
CAPTION = (
    "Replay cannot authenticate responses, prove inference occurred, or establish label truth."
)
STEPS = ("freeze", "run", "replay")
PINNED_NAMES = ("JetBrainsMono-Regular.ttf", "JetBrainsMono-Bold.ttf")
NOT_FETCHED = (
    "requires jetbrains-mono 2.304; not fetched: JetBrainsMono-Regular.ttf, "
    "JetBrainsMono-Bold.ttf, OFL.txt"
)
# Security symbolism and assurance language the hero must not carry. The
# caption deliberately negates authentication, proof of inference and label
# truth, so those three words are permitted only inside the caption.
FORBIDDEN_WORDS = (
    "tamper",
    "secure",
    "security",
    "signed",
    "signature",
    "trust",
    "guarantee",
    "enforce",
    "sandbox",
    "padlock",
    "shield",
    "safe",
    "proof",
    "proven",
    "verified",
    "certified",
)
MIN_PX = 14.0
UPEM = 1000
ADVANCE = 600


def _tree(data: bytes) -> ET.Element:
    return ET.fromstring(data)  # noqa: S314 - own freshly rendered bytes


def _errors(report: Any) -> list[str]:
    return [finding.message for finding in report.errors]


def _context(kit: ModuleType, root: Path) -> Any:
    return kit.inventory.RenderContext(root=root, work=root / "work")


# --- copy, declarations and floors: no font required ---------------------------


def test_copy_is_exact_and_fixed_lines_rejoin(kit: ModuleType) -> None:
    hero = kit.hero
    assert hero.WORDMARK == WORDMARK
    assert hero.TAGLINE == TAGLINE
    assert hero.CAPTION == CAPTION
    assert hero.MOTIF_STEPS == STEPS
    assert " ".join(hero.TAGLINE_LINES) == TAGLINE
    assert " ".join(hero.DESKTOP_CAPTION_LINES) == CAPTION
    assert " ".join(hero.MOBILE_CAPTION_LINES) == CAPTION
    assert len(hero.TAGLINE_LINES) == 2
    assert len(hero.DESKTOP_CAPTION_LINES) == 2
    assert len(hero.MOBILE_CAPTION_LINES) == 3
    hero.validate_copy()
    assert TAGLINE in hero.DESC
    assert CAPTION in hero.DESC
    for step in STEPS:
        assert step in hero.DESC
    assert hero.TITLE.startswith("Actseal")


def test_drifted_line_breaks_are_rejected(kit: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    hero = kit.hero
    monkeypatch.setattr(hero, "MOBILE_CAPTION_LINES", ("Replay cannot authenticate responses.",))
    with pytest.raises(ValueError, match="mobile caption lines do not rejoin"):
        hero.validate_copy()


def test_no_security_symbolism_or_assurance_language(kit: ModuleType) -> None:
    hero = kit.hero
    prose = " ".join(
        [hero.TITLE, hero.DESC, hero.WORDMARK, hero.TAGLINE, hero.CAPTION, *hero.MOTIF_STEPS]
    ).lower()
    for word in FORBIDDEN_WORDS:
        assert not re.search(rf"\b{word}", prose), word
    outside_caption = prose.replace(CAPTION.lower(), "")
    for word in ("authentic", "prove", "truth"):
        assert word not in outside_caption, word


def test_inventory_registers_four_outlined_outputs_and_the_renderer(kit: ModuleType) -> None:
    hero = kit.hero
    asset = kit.inventory.get_asset("hero")
    assert asset.implemented
    assert asset.renderer is hero.render
    assert tuple(o.path for o in asset.outputs) == hero.OUTPUTS == (*DESKTOP, *MOBILE)
    assert asset.needs == ("jetbrains-mono", "fonttools")
    sizes = {o.path: (o.width, o.height, o.display_width, o.outlined) for o in asset.outputs}
    for name in DESKTOP:
        assert sizes[name] == (1600, 400, kit.inventory.README_DISPLAY_WIDTH, True)
    for name in MOBILE:
        assert sizes[name] == (720, hero.mobile_height(), kit.inventory.MOBILE_DISPLAY_WIDTH, True)
    assert hero.mobile_height() == 561
    assert kit.inventory.validate_inventory() == []
    assert hero.DESKTOP_DISPLAY_WIDTH == kit.inventory.README_DISPLAY_WIDTH
    assert hero.MOBILE_DISPLAY_WIDTH == kit.inventory.MOBILE_DISPLAY_WIDTH
    assert hero.MIN_LABEL_PX == kit.checks.MIN_LABEL_PX == MIN_PX


def test_type_sizes_meet_the_floor_at_display_width(kit: ModuleType) -> None:
    hero = kit.hero
    for canvas in (hero.DESKTOP, hero.MOBILE):
        hero.require_readable(canvas)
        smallest = min(canvas.sizes)
        assert canvas.rendered_px(smallest) >= MIN_PX, canvas.name
        assert canvas.wordmark > canvas.tagline > canvas.caption, canvas.name
        assert canvas.label >= canvas.caption, canvas.name
    assert hero.DESKTOP.rendered_px(hero.DESKTOP.caption) == pytest.approx(15.4)
    assert hero.MOBILE.rendered_px(hero.MOBILE.caption) == pytest.approx(15.0)
    too_small = dataclasses.replace(hero.DESKTOP, caption=20)
    with pytest.raises(ValueError, match=r"20 units render at 11.0px .* minimum is 14px"):
        hero.require_readable(too_small)


def test_fixed_geometry_fits_both_canvases(kit: ModuleType) -> None:
    hero = kit.hero
    hero._require_extents(hero.DESKTOP, hero.DESKTOP_HEIGHT)
    hero._require_extents(hero.MOBILE, hero.mobile_height())
    assert hero.DESKTOP.text_x + hero.DESKTOP.text_width < hero.DESKTOP.motif_x
    assert hero.MOBILE.motif_bottom < hero.MOBILE.caption_baseline - hero.MOBILE.caption
    crowded = dataclasses.replace(hero.DESKTOP, motif_x=1200)
    with pytest.raises(ValueError, match="motif exceeds the canvas width"):
        hero._require_extents(crowded, hero.DESKTOP_HEIGHT)
    with pytest.raises(ValueError, match="caption needs"):
        hero._require_extents(hero.MOBILE, 400)


def test_missing_pinned_fonts_fail_before_any_outlining(kit: ModuleType, tmp_path: Path) -> None:
    """No fontTools import, no outlining and no substitute when the pinned files are absent."""
    hero = kit.hero
    context = _context(kit, tmp_path)
    with pytest.raises(kit.outline.OutlineError) as absent:
        hero.render(context)
    message = str(absent.value)
    assert "JetBrainsMono-Regular.ttf, JetBrainsMono-Bold.ttf" in message
    assert "setup_tools.py --tool jetbrains-mono" in message
    assert "No substitute font is used" in message
    fonts = tmp_path / kit.inventory.FONT_DIR
    fonts.mkdir(parents=True)
    (fonts / "JetBrainsMono-Regular.ttf").write_bytes(b"present but unverified")
    with pytest.raises(kit.outline.OutlineError, match=r"missing from .*: JetBrainsMono-Bold.ttf;"):
        hero.require_fonts(context)
    assert not (tmp_path / "docs" / "assets" / "hero-light.svg").exists()


def test_pipeline_blocks_the_hero_without_the_pinned_fonts(kit: ModuleType, repo: Path) -> None:
    """The real hero declaration in a repository whose fonts were never fetched."""
    asset = kit.inventory.get_asset("hero")
    for mode in ("check", "write"):
        report = kit.pipeline.run(repo, mode=mode, only=("hero",), assets=(asset,))
        assert _errors(report) == [NOT_FETCHED, "skipped rendering because prerequisites failed"]
        assert report.checked == []
        assert report.written == []
        assert report.planned == []
    assert not any((repo / "docs" / "assets").glob("hero*"))


def test_done_when_command_exits_one_without_the_pinned_fonts(
    kit: ModuleType, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """In-process form of ``render.py --check --only hero`` before the font approval."""
    assert kit.cli.main(["--check", "--only", "hero"], root=repo) == 1
    out = capsys.readouterr().out
    assert f"[error] hero: {NOT_FETCHED}" in out
    assert "[error] hero: skipped rendering because prerequisites failed" in out
    assert "[ok] hero" not in out
    assert out.rstrip().endswith("0 asset(s) checked; 0 planned/not implemented; 2 error(s)")


# --- rendering with unit-double fonts: fontTools only ---------------------------


def _build_double(path: Path, charset: str, *, box: int) -> None:
    """A TrueType unit double: every character is a rectangle with a 600-unit advance.

    This is a test stand-in with the pinned file *name* only. It carries none
    of the pinned font's glyphs, metrics or bytes.
    """
    font_builder = pytest.importorskip("fontTools.fontBuilder")
    tt_glyph_pen = pytest.importorskip("fontTools.pens.ttGlyphPen")
    names = {char: f"uni{ord(char):04X}" for char in sorted(set(charset))}
    builder = font_builder.FontBuilder(UPEM, isTTF=True)
    builder.setupGlyphOrder([".notdef", *names.values()])
    builder.setupCharacterMap({ord(char): name for char, name in names.items()})
    glyphs: dict[str, Any] = {".notdef": tt_glyph_pen.TTGlyphPen(None).glyph()}
    for char, name in names.items():
        pen = tt_glyph_pen.TTGlyphPen(None)
        if not char.isspace():
            pen.moveTo((80, 0))
            pen.lineTo((80 + box, 0))
            pen.lineTo((80 + box, 500))
            pen.lineTo((80, 500))
            pen.closePath()
        glyphs[name] = pen.glyph()
    builder.setupGlyf(glyphs)
    builder.setupHorizontalMetrics(dict.fromkeys(glyphs, (ADVANCE, 0)))
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable({"familyName": "Unit Double", "styleName": "Regular"})
    builder.setupOS2()
    builder.setupPost()
    builder.save(str(path))


def _all_text(kit: ModuleType) -> str:
    hero = kit.hero
    return "".join([hero.WORDMARK, hero.TAGLINE, hero.CAPTION, *hero.MOTIF_STEPS])


@pytest.fixture(scope="module")
def doubles_root(kit: ModuleType, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A repository root whose fonts directory holds unit doubles under the pinned names."""
    root = tmp_path_factory.mktemp("hero-doubles")
    fonts = root / kit.inventory.FONT_DIR
    fonts.mkdir(parents=True)
    _build_double(fonts / PINNED_NAMES[0], _all_text(kit), box=440)
    _build_double(fonts / PINNED_NAMES[1], _all_text(kit), box=480)
    return root


@pytest.fixture(scope="module")
def rendered(kit: ModuleType, doubles_root: Path) -> dict[str, bytes]:
    result: dict[str, bytes] = dict(kit.hero.render(_context(kit, doubles_root)))
    return result


def test_renders_exactly_the_declared_outputs_deterministically(
    kit: ModuleType, doubles_root: Path, rendered: dict[str, bytes]
) -> None:
    assert tuple(rendered) == kit.hero.OUTPUTS
    assert dict(kit.hero.render(_context(kit, doubles_root))) == rendered


def test_every_output_is_outlined_and_passes_the_validators(
    kit: ModuleType, rendered: dict[str, bytes]
) -> None:
    asset = kit.inventory.get_asset("hero")
    for output in asset.outputs:
        data = rendered[output.path]
        assert kit.checks.check_output(data, output) == [], output.path
        assert b"<text" not in data
        assert b"font-family" not in data
        assert b"transform" not in data
        root = _tree(data)
        title = root.find(f"{SVG_NS}title")
        desc = root.find(f"{SVG_NS}desc")
        assert title is not None
        assert desc is not None
        assert title.text == kit.hero.TITLE
        assert desc.text == kit.hero.DESC


@pytest.mark.parametrize(
    ("name", "glyph_paths"),
    [(DESKTOP[0], 8), (DESKTOP[1], 8), (MOBILE[0], 9), (MOBILE[1], 9)],
)
def test_structure_has_one_motif_and_every_line_as_a_path(
    rendered: dict[str, bytes], name: str, glyph_paths: int
) -> None:
    root = _tree(rendered[name])
    groups = [child.get("id") for child in root if child.tag == f"{SVG_NS}g"]
    assert groups == ["wordmark", "tagline", "motif", "caption"]
    motif = root.find(f"{SVG_NS}g[@id='motif']")
    assert motif is not None
    steps = [child for child in motif if child.tag == f"{SVG_NS}g"]
    assert [step.get("id") for step in steps] == [f"step-{step}" for step in STEPS]
    for step in steps:
        assert step.find(f"{SVG_NS}rect") is not None
        assert len(step.findall(f"{SVG_NS}path")) == 1
    # Two forward arrows plus the return arrow closing the loop.
    assert len(motif.findall(f".//{SVG_NS}polygon")) == 3
    routes = [p for p in motif.findall(f"{SVG_NS}path") if p.get("fill") == "none"]
    assert len(routes) == 1
    glyphs = [p for p in root.iter(f"{SVG_NS}path") if p.get("fill") != "none"]
    assert len(glyphs) == glyph_paths
    assert all((p.get("d") or "").startswith("M") for p in glyphs)
    xs = [float(r.get("x", "0")) for r in motif.iter(f"{SVG_NS}rect")]
    assert xs == sorted(xs)
    assert len({r.get("y") for r in motif.iter(f"{SVG_NS}rect")}) == 1


def test_light_and_dark_differ_only_in_color(rendered: dict[str, bytes]) -> None:
    for light_name, dark_name in (DESKTOP, MOBILE):
        assert rendered[light_name] != rendered[dark_name]
        light, dark = _tree(rendered[light_name]), _tree(rendered[dark_name])
        for a, b in zip(light.iter(), dark.iter(), strict=True):
            assert a.tag == b.tag
            assert (a.text or "").strip() == (b.text or "").strip()
            for key in a.attrib:
                if key in {"fill", "stroke"}:
                    continue
                assert a.get(key) == b.get(key), (a.tag, key)
        canvas = light.find(f"{SVG_NS}rect")
        assert canvas is not None
        assert canvas.get("fill") == "#ffffff"
        dark_canvas = dark.find(f"{SVG_NS}rect")
        assert dark_canvas is not None
        assert dark_canvas.get("fill") == "#0d1117"


def test_overflowing_line_fails_instead_of_shrinking(
    kit: ModuleType, doubles_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hero = kit.hero
    monkeypatch.setattr(hero, "DESKTOP", dataclasses.replace(hero.DESKTOP, text_width=300))
    with pytest.raises(ValueError, match=r"units wide at size 104; only 300 units are available"):
        hero.render(_context(kit, doubles_root))


def test_missing_glyph_in_the_font_is_an_error(kit: ModuleType, tmp_path: Path) -> None:
    fonts = tmp_path / kit.inventory.FONT_DIR
    fonts.mkdir(parents=True)
    without_comma = _all_text(kit).replace(",", "")
    _build_double(fonts / PINNED_NAMES[0], without_comma, box=440)
    _build_double(fonts / PINNED_NAMES[1], without_comma, box=480)
    with pytest.raises(kit.outline.OutlineError, match="no glyph for ','"):
        kit.hero.render(_context(kit, tmp_path))


def _install_doubles(kit: ModuleType, repo: Path, doubles_root: Path) -> None:
    """Point the copied manifest at the unit doubles so the pipeline's pin check passes."""
    manifest = repo / "docs" / "assets" / "src" / "tools.toml"
    text = manifest.read_text(encoding="utf-8")
    pins = {
        PINNED_NAMES[0]: "a0bf60ef0f83c5ed4d7a75d45838548b1f6873372dfac88f71804491898d138f",
        PINNED_NAMES[1]: "5590990c82e097397517f275f430af4546e1c45cff408bde4255dad142479dcb",
    }
    fonts = repo / kit.inventory.FONT_DIR
    fonts.mkdir(parents=True)
    for name, pin in pins.items():
        data = (doubles_root / kit.inventory.FONT_DIR / name).read_bytes()
        (fonts / name).write_bytes(data)
        text = text.replace(pin, kit.tools.sha256_bytes(data))
    manifest.write_text(text, encoding="utf-8")
    (fonts / "OFL.txt").write_text(
        "Copyright 2020 The JetBrains Mono Project Authors\n"
        "SIL OPEN FONT LICENSE Version 1.1 - 26 February 2007\n",
        encoding="utf-8",
    )


def test_write_then_check_round_trip_with_unit_doubles(
    kit: ModuleType, repo: Path, doubles_root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Pipeline wiring only: the doubles stand in for the pinned files by name and hash."""
    _install_doubles(kit, repo, doubles_root)
    asset = kit.inventory.get_asset("hero")
    written = kit.pipeline.run(repo, mode="write", only=("hero",), assets=(asset,))
    assert _errors(written) == []
    assert written.written == list(kit.hero.OUTPUTS)
    checked = kit.pipeline.run(repo, mode="check", only=("hero",), assets=(asset,))
    assert _errors(checked) == []
    assert checked.checked == ["hero"]
    assert kit.cli.main(["--check", "--only", "hero"], root=repo) == 0
    out = capsys.readouterr().out
    assert "[ok] fonts: jetbrains-mono 2.304 present with upstream notice" in out
    for name in kit.hero.OUTPUTS:
        assert f"[ok] hero: docs/assets/{name} matches regeneration (" in out
