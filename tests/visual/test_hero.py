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
#: The caption paragraph the 2026-10-08 editorial review removed from the
#: artwork; its limits now live in the README prose (tests/docs/test_readme.py).
REMOVED_CAPTION = (
    "Replay cannot authenticate responses, prove inference occurred, or establish label truth."
)
STEPS = ("freeze", "run", "replay")
PINNED_NAMES = ("JetBrainsMono-Regular.ttf", "JetBrainsMono-Bold.ttf")
NOT_FETCHED = (
    "requires jetbrains-mono 2.304; not fetched: JetBrainsMono-Regular.ttf, "
    "JetBrainsMono-Bold.ttf, OFL.txt"
)
# Security symbolism and assurance language the hero must not carry. With the
# caption gone, the negated limit words (authentication, proof of inference,
# label truth) must not appear anywhere in the artwork either.
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
#: Compact canvases from the 2026-10-08 editorial specification.
DESKTOP_SIZE = (1600, 280)
MOBILE_SIZE = (720, 400)
#: Smallest step-label sizes the specification allows (28 desktop, 40 mobile units).
MIN_DESKTOP_LABEL = 28
MIN_MOBILE_LABEL = 40
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
    assert hero.MOTIF_STEPS == STEPS
    assert hero.TAGLINE_LINES == ("Test model-chosen actions.", "Replay the evidence.")
    assert " ".join(hero.TAGLINE_LINES) == TAGLINE
    hero.validate_copy()
    assert TAGLINE in hero.DESC
    for step in STEPS:
        assert step in hero.DESC
    assert "forward sequence" in hero.DESC
    assert hero.TITLE.startswith("Actseal")


def test_caption_paragraph_and_return_arrow_are_gone(kit: ModuleType) -> None:
    """The artwork carries no caption copy and describes no loop back to the start."""
    hero = kit.hero
    for name in ("CAPTION", "DESKTOP_CAPTION_LINES", "MOBILE_CAPTION_LINES"):
        assert not hasattr(hero, name), name
    assert REMOVED_CAPTION not in hero.DESC
    for phrase in ("loop", "back to", "Caption"):
        assert phrase not in hero.DESC, phrase
    for canvas in (hero.DESKTOP, hero.MOBILE):
        assert not hasattr(canvas, "caption"), canvas.name
        assert not hasattr(canvas, "loop_drop"), canvas.name


def test_drifted_line_breaks_are_rejected(kit: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    hero = kit.hero
    monkeypatch.setattr(hero, "TAGLINE_LINES", ("Test model-chosen actions.", "Replay it."))
    with pytest.raises(ValueError, match="tagline lines do not rejoin"):
        hero.validate_copy()


def test_no_security_symbolism_or_assurance_language(kit: ModuleType) -> None:
    hero = kit.hero
    prose = " ".join([hero.TITLE, hero.DESC, hero.WORDMARK, hero.TAGLINE, *hero.MOTIF_STEPS])
    prose = prose.lower()
    for word in FORBIDDEN_WORDS:
        assert not re.search(rf"\b{word}", prose), word
    for word in ("authentic", "prove", "truth", "checkmark", "badge", "lock"):
        assert word not in prose, word


def test_inventory_registers_four_outlined_outputs_and_the_renderer(kit: ModuleType) -> None:
    hero = kit.hero
    asset = kit.inventory.get_asset("hero")
    assert asset.implemented
    assert asset.renderer is hero.render
    assert tuple(o.path for o in asset.outputs) == hero.OUTPUTS == (*DESKTOP, *MOBILE)
    assert asset.needs == ("jetbrains-mono", "fonttools")
    sizes = {o.path: (o.width, o.height, o.display_width, o.outlined) for o in asset.outputs}
    for name in DESKTOP:
        assert sizes[name] == (*DESKTOP_SIZE, kit.inventory.README_DISPLAY_WIDTH, True)
    for name in MOBILE:
        assert sizes[name] == (*MOBILE_SIZE, kit.inventory.MOBILE_DISPLAY_WIDTH, True)
    assert (hero.DESKTOP_WIDTH, hero.DESKTOP_HEIGHT) == DESKTOP_SIZE
    assert (hero.MOBILE_WIDTH, hero.MOBILE_HEIGHT) == MOBILE_SIZE
    assert (kit.inventory.HERO_WIDTH, kit.inventory.HERO_HEIGHT) == DESKTOP_SIZE
    assert (kit.inventory.HERO_MOBILE_WIDTH, kit.inventory.HERO_MOBILE_HEIGHT) == MOBILE_SIZE
    assert (hero.DESKTOP.width, hero.MOBILE.width) == (DESKTOP_SIZE[0], MOBILE_SIZE[0])
    assert kit.inventory.validate_inventory() == []
    # Measured README image widths (REVIEW 13), not the earlier 880/360 assumptions.
    assert hero.DESKTOP_DISPLAY_WIDTH == kit.inventory.README_DISPLAY_WIDTH == 838
    assert hero.MOBILE_DISPLAY_WIDTH == kit.inventory.MOBILE_DISPLAY_WIDTH == 254
    assert hero.MIN_LABEL_PX == kit.checks.MIN_LABEL_PX == MIN_PX


def test_type_sizes_meet_the_floor_at_display_width(kit: ModuleType) -> None:
    hero = kit.hero
    for canvas in (hero.DESKTOP, hero.MOBILE):
        hero.require_readable(canvas)
        smallest = min(canvas.sizes)
        assert smallest == canvas.label, canvas.name
        assert canvas.rendered_px(smallest) >= MIN_PX, canvas.name
        assert canvas.wordmark > canvas.tagline > canvas.label, canvas.name
    assert hero.MIN_DESKTOP_LABEL == MIN_DESKTOP_LABEL
    assert hero.MIN_MOBILE_LABEL == MIN_MOBILE_LABEL
    assert hero.DESKTOP.label >= MIN_DESKTOP_LABEL
    assert hero.MOBILE.label >= MIN_MOBILE_LABEL
    hero.require_label_minimum(hero.DESKTOP, MIN_DESKTOP_LABEL)
    hero.require_label_minimum(hero.MOBILE, MIN_MOBILE_LABEL)
    # The minimum labels, 28 units x 838/1600 and 40 units x 254/720, both clear
    # the floor; 30 mobile units would not (30 x 254/720 = 10.6 px).
    assert hero.DESKTOP.rendered_px(MIN_DESKTOP_LABEL) == pytest.approx(14.665)
    assert hero.MOBILE.rendered_px(MIN_MOBILE_LABEL) == pytest.approx(14.111, abs=0.001)
    assert hero.MOBILE.rendered_px(30) < MIN_PX
    too_small = dataclasses.replace(hero.DESKTOP, label=20)
    with pytest.raises(ValueError, match=r"20 units render at 10.5px .* minimum is 14px"):
        hero.require_readable(too_small)
    old_mobile = dataclasses.replace(hero.MOBILE, label=30)
    with pytest.raises(ValueError, match=r"30 units render at 10.6px at 254 CSS px"):
        hero.require_readable(old_mobile)
    with pytest.raises(ValueError, match="step labels are 26 units; minimum is 28 units"):
        hero.require_label_minimum(dataclasses.replace(hero.DESKTOP, label=26), MIN_DESKTOP_LABEL)


def test_undersized_labels_fail_before_any_font_is_read(
    kit: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The label minimum is enforced by ``render`` itself, before the font check."""
    hero = kit.hero
    monkeypatch.setattr(hero, "MOBILE", dataclasses.replace(hero.MOBILE, label=36))
    with pytest.raises(ValueError, match="mobile: step labels are 36 units; minimum is 40"):
        hero.render(_context(kit, tmp_path))


def test_fixed_geometry_fits_both_canvases(kit: ModuleType) -> None:
    hero = kit.hero
    hero._require_extents(hero.DESKTOP, hero.DESKTOP_HEIGHT)
    hero._require_extents(hero.MOBILE, hero.MOBILE_HEIGHT)
    # Desktop: text column beside the motif, both inside the 280-unit height.
    desktop = hero.DESKTOP
    assert desktop.text_x + desktop.text_width <= desktop.motif_x
    assert desktop.margin <= desktop.text_top < desktop.text_bottom
    assert desktop.text_bottom <= hero.DESKTOP_HEIGHT - desktop.margin
    assert desktop.margin <= desktop.motif_top < desktop.motif_bottom
    assert desktop.motif_bottom <= hero.DESKTOP_HEIGHT - desktop.margin
    # The pills sit on the canvas's vertical centre line.
    assert desktop.motif_top + desktop.pill_height / 2 == hero.DESKTOP_HEIGHT / 2
    # Mobile: wordmark, tagline, then the motif, stacked without overlap.
    mobile = hero.MOBILE
    assert mobile.margin <= mobile.text_top
    assert mobile.text_bottom <= mobile.motif_top
    assert mobile.motif_bottom <= hero.MOBILE_HEIGHT - mobile.margin
    assert mobile.motif_x + mobile.motif_width <= hero.MOBILE_WIDTH - mobile.margin
    crowded = dataclasses.replace(desktop, motif_x=1200)
    with pytest.raises(ValueError, match="motif exceeds the canvas width"):
        hero._require_extents(crowded, hero.DESKTOP_HEIGHT)
    with pytest.raises(ValueError, match="tagline needs 246 units of height"):
        hero._require_extents(desktop, 260)
    with pytest.raises(ValueError, match="motif needs 352 units of height"):
        hero._require_extents(mobile, 360)
    with pytest.raises(ValueError, match="wordmark reaches 2 units from the top"):
        hero._require_extents(dataclasses.replace(desktop, wordmark_baseline=86), 280)
    overlapping = dataclasses.replace(desktop, motif_x=800)
    with pytest.raises(ValueError, match="text column overlaps the motif"):
        hero._require_extents(overlapping, hero.DESKTOP_HEIGHT)


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
    return "".join([hero.WORDMARK, hero.TAGLINE, *hero.MOTIF_STEPS])


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


def _last_step_has_arrow(steps: list[ET.Element]) -> bool:
    """Whether the final step carries an arrow, which would point past the sequence."""
    return steps[-1].find(f"{SVG_NS}line") is not None


@pytest.mark.parametrize(
    ("name", "size"),
    [
        (DESKTOP[0], DESKTOP_SIZE),
        (DESKTOP[1], DESKTOP_SIZE),
        (MOBILE[0], MOBILE_SIZE),
        (MOBILE[1], MOBILE_SIZE),
    ],
)
def test_structure_has_one_forward_motif_and_no_caption(
    rendered: dict[str, bytes], name: str, size: tuple[int, int]
) -> None:
    root = _tree(rendered[name])
    width, height = size
    assert (root.get("width"), root.get("height")) == (str(width), str(height))
    assert root.get("viewBox") == f"0 0 {width} {height}"
    groups = [child.get("id") for child in root if child.tag == f"{SVG_NS}g"]
    assert groups == ["wordmark", "tagline", "motif"]
    motif = root.find(f"{SVG_NS}g[@id='motif']")
    assert motif is not None
    steps = [child for child in motif if child.tag == f"{SVG_NS}g"]
    assert [step.get("id") for step in steps] == [f"step-{step}" for step in STEPS]
    for step in steps:
        assert step.find(f"{SVG_NS}rect") is not None
        assert len(step.findall(f"{SVG_NS}path")) == 1
    # Exactly two forward arrows (freeze to run, run to replay): no return route.
    lines = motif.findall(f".//{SVG_NS}line")
    assert len(lines) == 2
    assert len(motif.findall(f".//{SVG_NS}polygon")) == 2
    assert all(float(a.get("x2", "0")) > float(a.get("x1", "0")) for a in lines)
    assert len({a.get("y1") for a in lines} | {a.get("y2") for a in lines}) == 1
    routes = [p for p in root.iter(f"{SVG_NS}path") if p.get("fill") == "none"]
    assert routes == []
    assert not _last_step_has_arrow(steps)
    # Wordmark, two tagline lines and three step labels; nothing else is drawn.
    glyphs = [p for p in root.iter(f"{SVG_NS}path") if p.get("fill") != "none"]
    assert len(glyphs) == 6
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
    without_hyphen = _all_text(kit).replace("-", "")
    _build_double(fonts / PINNED_NAMES[0], without_hyphen, box=440)
    _build_double(fonts / PINNED_NAMES[1], without_hyphen, box=480)
    with pytest.raises(kit.outline.OutlineError, match="no glyph for '-'"):
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
