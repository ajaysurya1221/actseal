"""Copy, recorded numbers, declarations, readability floors and fail-loud behaviour of the hero.

The hero is an evidence card (plan/v1/CHANGE_LOG.md V1-058): the thesis
question beside one recorded result, the preregistered live Jev audit. Two
kinds of test live here. The first kind needs no font and no fontTools: exact
copy, the card's numbers against the committed audit files, inventory
declarations, type-size floors, layout limits and the explicit failures when
the pinned fonts are absent. The second kind renders with **unit-double
fonts** built in a temporary directory: every glyph is a plain rectangle with
a 600/1000 em advance. Those doubles exercise the pipeline wiring,
determinism and validators only. They are not the pinned JetBrains Mono
files, they prove nothing about glyph appearance or readability, and nothing
in this module downloads or copies a font.
"""

from __future__ import annotations

import dataclasses
import itertools
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from actseal.cli import EXIT_CODES

SVG_NS = "{http://www.w3.org/2000/svg}"
ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "docs" / "results" / "jev-audit-2026-10-08"
DESKTOP = ("hero-light.svg", "hero-dark.svg")
MOBILE = ("hero-mobile-light.svg", "hero-mobile-dark.svg")
EYEBROW = "actseal · frozen decision policies · risk and coverage · offline replay"
THESIS = "Does this frozen action policy meet its declared risk and coverage limits?"
SUBLINE = (
    "Freeze the policy, run it once against labelled cases, bound the errors among "
    "accepted actions, seal the evidence, replay it with no model call."
)
CARD = {
    "card-label": "PREREGISTERED LIVE AUDIT · 639 VERIFICATION CASES · THRESHOLD 0.80",
    "card-headline": "ACT 580/639   errors 24",
    "card-scope": "Fixed benchmark; unreleased producer",
    "card-bounds": "risk [0.0250, 0.0639] vs limit 0.05 · coverage [0.879, 0.932]",
    "card-verdict": "VERDICT: INCONCLUSIVE (exit 2) → replay requires archived producer d3edbab",
    "card-footer": "docs/results/jev-audit-2026-10-08 · neither PASS nor BLOCK is claimed",
}
COLUMN_KEYS = ("eyebrow", "thesis", "subline")
CARD_KEYS = tuple(CARD)
PINNED_NAMES = ("JetBrainsMono-Regular.ttf", "JetBrainsMono-Bold.ttf")
NOT_FETCHED = (
    "requires jetbrains-mono 2.304; not fetched: JetBrainsMono-Regular.ttf, "
    "JetBrainsMono-Bold.ttf, OFL.txt"
)
# Security symbolism and assurance language the hero must not carry, matched
# as whole words or word starts so that "BLOCK" does not count as "lock".
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
    "authentic",
    "prove",
    "truth",
    "checkmark",
    "badge",
    "lock",
)
MIN_PX = 14.0
REFERENCE_PX = 10.0
#: The side-by-side desktop composition and the stacked mobile canvas.
DESKTOP_SIZE = (1600, 520)
MOBILE_SIZE = (720, 1576)
#: Measured README image widths: 254 CSS px at a 320 px viewport, 838 at 1280+.
NARROWEST = 254
WIDEST = 838
#: Smallest unit sizes that reach 14 px: 26.7 desktop units at 838 CSS px and
#: 39.7 mobile units at 254 CSS px, rounded up.
MIN_DESKTOP_TEXT = 27
MIN_MOBILE_TEXT = 40
UPEM = 1000
ADVANCE = 600


def _tree(data: bytes) -> ET.Element:
    return ET.fromstring(data)  # noqa: S314 - own freshly rendered bytes


def _errors(report: Any) -> list[str]:
    return [finding.message for finding in report.errors]


def _context(kit: ModuleType, root: Path) -> Any:
    return kit.inventory.RenderContext(root=root, work=root / "work")


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


# --- copy, recorded numbers, declarations and floors: no font required ---------


def test_copy_is_exact_and_every_canvas_rejoins(kit: ModuleType) -> None:
    hero = kit.hero
    assert hero.EYEBROW == EYEBROW
    assert hero.THESIS == THESIS
    assert hero.SUBLINE == SUBLINE
    assert {key: hero.copy_for(key).text for key in CARD_KEYS} == CARD
    assert (hero.COLUMN_KEYS, hero.CARD_KEYS) == (COLUMN_KEYS, CARD_KEYS)
    assert hero.WORDMARK == "actseal"
    assert EYEBROW.startswith(hero.WORDMARK + " · ")
    hero.validate_copy()
    for canvas in (hero.DESKTOP, hero.MOBILE):
        for setting in canvas.settings:
            assert " ".join(setting.lines) == hero.copy_for(setting.key).text, setting.key
    # The desktop thesis takes three lines, as the composition specifies.
    assert len(hero.DESKTOP.setting("thesis").lines) == 3
    assert hero.TITLE.startswith("Actseal")
    assert THESIS.lower().rstrip("?") in hero.TITLE.lower()
    # The description carries every line; the headline is spelled out for screen readers.
    spoken = {**CARD, "card-headline": "ACT 580 of 639, errors 24."}
    for text in (EYEBROW, THESIS, SUBLINE, *spoken.values()):
        assert " ".join(text.split()) in " ".join(hero.DESC.split()), text


def test_card_numbers_match_the_committed_audit(kit: ModuleType) -> None:
    """Every number on the card is the committed audit's, at the precision shown."""
    hero = kit.hero
    verdict = _json(AUDIT / "evidence" / "verdict.json")
    receipt = _json(AUDIT / "audit_receipt.json")
    contract = _json(AUDIT / "inputs" / "preregistration.json")["contract"]
    cohort = receipt["cohorts"]["verification"]
    assert receipt["verification_bundle"]["verdict"] == verdict
    assert (cohort["captured"], cohort["act"], cohort["wrong_act"]) == (
        verdict["total"],
        verdict["accepted"],
        verdict["errors"],
    )
    total, accepted, errors = verdict["total"], verdict["accepted"], verdict["errors"]
    risk = f"[{verdict['risk']['lower']:.4f}, {verdict['risk']['upper']:.4f}]"
    coverage = f"[{verdict['coverage']['lower']:.3f}, {verdict['coverage']['upper']:.3f}]"
    status = verdict["status"]
    assert (
        f"PREREGISTERED LIVE AUDIT · {total} VERIFICATION CASES · "
        f"THRESHOLD {contract['threshold']:.2f}"
    ) == hero.CARD_LABEL
    assert f"ACT {accepted}/{total}   errors {errors}" == hero.CARD_HEADLINE
    assert (
        f"risk {risk} vs limit {contract['max_risk']:.2f} · coverage {coverage}"
    ) == hero.CARD_BOUNDS
    assert hero.CARD_VERDICT.startswith(f"VERDICT: {status} (exit {EXIT_CODES[status]}) → ")
    assert hero.CARD_FOOTER.startswith(f"docs/results/{AUDIT.name} · ")
    # The replay restriction and the scope come from the audit README: the
    # producer is the unreleased snapshot, and 1.0.0 cannot replay the bundle.
    audit_readme = (AUDIT / "README.md").read_text(encoding="utf-8")
    snapshot = re.search(r"unreleased benchmark snapshot\s+`([0-9a-f]{40})`", audit_readme)
    assert snapshot is not None
    assert hero.CARD_VERDICT.endswith(f"→ replay requires archived producer {snapshot[1][:7]}")
    assert "ERROR `integrity.lock`" in audit_readme
    assert hero.CARD_SCOPE == "Fixed benchmark; unreleased producer"
    assert status == "INCONCLUSIVE"
    assert "neither PASS nor BLOCK is claimed" in hero.CARD_FOOTER
    # The bound straddles the limit, which is why neither PASS nor BLOCK holds.
    assert verdict["risk"]["lower"] < contract["max_risk"] < verdict["risk"]["upper"]


def test_drifted_line_breaks_are_rejected(kit: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    hero = kit.hero
    thesis = dataclasses.replace(
        hero.DESKTOP.column[1], lines=("Does this frozen action", "policy meet its limits?")
    )
    drifted = dataclasses.replace(
        hero.DESKTOP, column=(hero.DESKTOP.column[0], thesis, hero.DESKTOP.column[2])
    )
    with pytest.raises(ValueError, match="desktop: thesis lines do not rejoin"):
        hero.validate_copy((drifted,))
    padded = dataclasses.replace(
        thesis, lines=(*hero.DESKTOP.column[1].lines[:-1], "risk and coverage limits? ")
    )
    with pytest.raises(ValueError, match="thesis lines do not rejoin"):
        hero.validate_copy(
            (
                dataclasses.replace(
                    hero.DESKTOP, column=(hero.DESKTOP.column[0], padded, hero.DESKTOP.column[2])
                ),
            )
        )
    reordered = dataclasses.replace(hero.MOBILE, card=tuple(reversed(hero.MOBILE.card)))
    with pytest.raises(ValueError, match=r"mobile: blocks .* do not match"):
        hero.validate_copy((reordered,))
    monkeypatch.setattr(
        hero,
        "COPY",
        tuple(
            dataclasses.replace(c, highlights=(hero.Highlight("0.0", "red"),))
            if c.key == "card-bounds"
            else c
            for c in hero.COPY
        ),
    )
    with pytest.raises(ValueError, match=r"card-bounds: highlight '0.0' occurs \d+ times"):
        hero.validate_copy()


def test_highlights_are_split_into_spans_across_line_breaks(kit: ModuleType) -> None:
    hero = kit.hero
    verdict = hero.copy_for("card-verdict")
    mobile = hero.line_spans(verdict, hero.MOBILE.setting("card-verdict").lines)
    assert [(s.text, s.role, s.bold) for s in mobile[0]] == [
        ("VERDICT: INCONCLUSIVE", "amber", True)
    ]
    assert [(s.text, s.role, s.bold) for s in mobile[1]] == [
        ("(exit 2)", "amber", True),
        (" → replay requires", "card_text", False),
    ]
    assert [(s.text, s.role) for s in mobile[2]] == [("archived producer d3edbab", "card_text")]
    headline = hero.line_spans(hero.copy_for("card-headline"), (CARD["card-headline"],))
    assert [(s.text, s.role, s.bold) for s in headline[0]] == [
        ("ACT ", "card_text", True),
        ("580/639", "blue", True),
        ("   errors ", "card_text", True),
        ("24", "red", True),
    ]
    eyebrow = hero.line_spans(hero.copy_for("eyebrow"), hero.DESKTOP.setting("eyebrow").lines)
    assert [(s.text, s.role, s.bold) for s in eyebrow[0]] == [
        ("actseal", "accent", True),
        (" · frozen decision policies ·", "muted", False),
    ]
    for canvas in (hero.DESKTOP, hero.MOBILE):
        for setting in canvas.settings:
            spans = hero.line_spans(hero.copy_for(setting.key), setting.lines)
            assert ["".join(s.text for s in line) for line in spans] == list(setting.lines)


def test_no_security_symbolism_or_assurance_language(kit: ModuleType) -> None:
    hero = kit.hero
    prose = " ".join([hero.TITLE, hero.DESC, *(c.text for c in hero.COPY)]).lower()
    for word in FORBIDDEN_WORDS:
        assert not re.search(rf"\b{word}", prose), word
    # "BLOCK" is a verdict name, not a padlock: the word-start rule lets it through.
    assert "block" in prose


def test_palettes_follow_the_specified_colours(kit: ModuleType) -> None:
    hero = kit.hero
    assert (hero.DARK.canvas, hero.DARK.heading, hero.DARK.accent, hero.DARK.card) == (
        "#0F1512",
        "#F0ECE2",
        "#6FA2FF",
        "#F4F1EA",
    )
    assert (hero.DARK.card_text, hero.DARK.blue, hero.DARK.red, hero.DARK.amber) == (
        "#16211D",
        "#1F5FD1",
        "#B8431F",
        "#8A5A00",
    )
    assert (hero.LIGHT.canvas, hero.LIGHT.heading, hero.LIGHT.accent, hero.LIGHT.card) == (
        "#F4F1EA",
        "#16211D",
        "#1F5FD1",
        "#16211D",
    )
    assert (hero.LIGHT.card_text, hero.LIGHT.blue, hero.LIGHT.red, hero.LIGHT.amber) == (
        "#E9E4D8",
        "#6FA2FF",
        "#F0A48A",
        "#E8B14A",
    )
    for palette in (hero.DARK, hero.LIGHT):
        for role in hero.ROLES:
            assert re.fullmatch(r"#[0-9A-F]{6}", getattr(palette, role)), (palette.name, role)


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
    assert (hero.DESKTOP.width, hero.DESKTOP.height) == DESKTOP_SIZE
    assert (hero.MOBILE.width, hero.MOBILE.height) == MOBILE_SIZE
    assert kit.inventory.validate_inventory() == []
    assert hero.DESKTOP_DISPLAY_WIDTH == kit.inventory.README_DISPLAY_WIDTH == WIDEST
    assert hero.MOBILE_DISPLAY_WIDTH == kit.inventory.MOBILE_DISPLAY_WIDTH == NARROWEST
    assert hero.DESKTOP.display_width == WIDEST
    assert hero.MOBILE.display_width == NARROWEST
    assert hero.MIN_LABEL_PX == kit.checks.MIN_LABEL_PX == MIN_PX


def test_type_sizes_meet_the_floor_at_display_width(kit: ModuleType) -> None:
    hero = kit.hero
    assert hero.MIN_DESKTOP_TEXT == MIN_DESKTOP_TEXT
    assert hero.MIN_MOBILE_TEXT == MIN_MOBILE_TEXT
    assert hero.MIN_REFERENCE_PX == REFERENCE_PX
    for canvas, minimum in ((hero.DESKTOP, MIN_DESKTOP_TEXT), (hero.MOBILE, MIN_MOBILE_TEXT)):
        hero.require_readable(canvas)
        hero.require_text_minimum(canvas, minimum)
        # The minimum clears the floor and one unit less does not.
        assert canvas.rendered_px(minimum) >= MIN_PX
        assert canvas.rendered_px(minimum - 1) < MIN_PX
    # Desktop: every run, the footer included, reaches 14 px at 838 CSS px.
    assert all(hero.DESKTOP.rendered_px(size) >= MIN_PX for size in hero.DESKTOP.sizes)
    # Mobile: every run reaches 14 px at 254 CSS px except the reference footer,
    # the only Copy marked as a reference line, which reaches 10 px.
    assert [c.key for c in hero.COPY if c.reference] == ["card-footer"]
    for setting in hero.MOBILE.settings:
        rendered = hero.MOBILE.rendered_px(setting.size)
        floor = REFERENCE_PX if setting.key == "card-footer" else MIN_PX
        assert rendered >= floor, setting.key
    assert hero.MOBILE.rendered_px(hero.MOBILE.setting("card-footer").size) == pytest.approx(
        10.583, abs=0.001
    )
    # The thesis and the card headline lead each composition.
    for canvas in (hero.DESKTOP, hero.MOBILE):
        thesis = canvas.setting("thesis").size
        headline = canvas.setting("card-headline").size
        body = canvas.setting("subline").size
        assert thesis > body, canvas.name
        assert headline > body, canvas.name
    smaller = dataclasses.replace(
        hero.DESKTOP,
        card=(
            *hero.DESKTOP.card[:3],
            dataclasses.replace(hero.DESKTOP.card[3], size=26),
            *hero.DESKTOP.card[4:],
        ),
    )
    with pytest.raises(
        ValueError,
        match=r"desktop: card-bounds at 26 units renders at 13.6px at 838 CSS px; minimum is 14px",
    ):
        hero.require_readable(smaller)
    with pytest.raises(ValueError, match="desktop: card-bounds is 26 units; minimum is 27 units"):
        hero.require_text_minimum(smaller, MIN_DESKTOP_TEXT)
    footer = dataclasses.replace(hero.MOBILE.card[-1], size=28)
    tiny_footer = dataclasses.replace(hero.MOBILE, card=(*hero.MOBILE.card[:-1], footer))
    with pytest.raises(
        ValueError,
        match=r"mobile: card-footer at 28 units renders at 9.9px at 254 CSS px; minimum is 10px",
    ):
        hero.require_readable(tiny_footer)
    # The reference line is the only exemption from the unit minimum.
    hero.require_text_minimum(tiny_footer, MIN_MOBILE_TEXT)
    thesis = dataclasses.replace(hero.MOBILE.column[1], size=39)
    small_thesis = dataclasses.replace(
        hero.MOBILE, column=(hero.MOBILE.column[0], thesis, hero.MOBILE.column[2])
    )
    with pytest.raises(ValueError, match=r"mobile: thesis at 39 units renders at 13\.8px"):
        hero.require_readable(small_thesis)


def test_text_sizes_at_both_measured_widths(kit: ModuleType) -> None:
    """Nominal CSS px of the desktop runs at 838 and 254 px image widths.

    GitHub serves the desktop file at every width (V1-057), so the 254 px row is
    what a phone shows; the README prose carries the same result in text.
    """
    desktop = kit.hero.DESKTOP
    sizes = {s.key: s.size for s in desktop.settings}
    assert sizes == {
        "eyebrow": 27,
        "thesis": 46,
        "subline": 27,
        "card-label": 27,
        "card-headline": 40,
        "card-scope": 27,
        "card-bounds": 27,
        "card-verdict": 27,
        "card-footer": 27,
    }
    at_838 = {key: size * WIDEST / desktop.width for key, size in sizes.items()}
    at_254 = {key: size * NARROWEST / desktop.width for key, size in sizes.items()}
    assert at_838["thesis"] == pytest.approx(24.0925)
    assert at_838["card-headline"] == pytest.approx(20.95)
    assert at_838["subline"] == pytest.approx(14.14125)
    assert at_254["thesis"] == pytest.approx(7.3025)
    assert at_254["card-headline"] == pytest.approx(6.35)
    assert at_254["subline"] == pytest.approx(4.28625)
    assert all(px >= MIN_PX for px in at_838.values())
    assert [desktop.rendered_px(size) for size in sizes.values()] == pytest.approx(
        list(at_838.values())
    )


def test_undersized_text_fails_before_any_font_is_read(
    kit: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The floors are enforced by ``render`` itself, before the font check."""
    hero = kit.hero
    thesis = dataclasses.replace(hero.MOBILE.column[1], size=36)
    monkeypatch.setattr(
        hero,
        "MOBILE",
        dataclasses.replace(
            hero.MOBILE, column=(hero.MOBILE.column[0], thesis, hero.MOBILE.column[2])
        ),
    )
    with pytest.raises(ValueError, match="mobile: thesis is 36 units; minimum is 40 units"):
        hero.render(_context(kit, tmp_path))
    label = dataclasses.replace(hero.DESKTOP.card[0], size=24)
    monkeypatch.setattr(
        hero, "DESKTOP", dataclasses.replace(hero.DESKTOP, card=(label, *hero.DESKTOP.card[1:]))
    )
    with pytest.raises(ValueError, match="desktop: card-label is 24 units; minimum is 27 units"):
        hero.render(_context(kit, tmp_path))


def test_fixed_geometry_fits_both_canvases(kit: ModuleType) -> None:
    hero = kit.hero
    desktop, mobile = hero.DESKTOP, hero.MOBILE
    hero.require_layout(desktop)
    hero.require_layout(mobile)
    # Desktop: the column beside the card, 48 units apart, 64 units from each side.
    assert desktop.side_by_side
    assert desktop.card_x - (desktop.column_x + desktop.column_width) == 48
    assert desktop.column_x == DESKTOP_SIZE[0] - (desktop.card_x + desktop.card_width) == 64
    assert desktop.card_y == DESKTOP_SIZE[1] - (desktop.card_y + desktop.card_height) == 40
    # The column is centred on the card within one unit; the card content fills it.
    column_middle = (desktop.column_y + desktop.column_bottom) / 2
    card_middle = desktop.card_y + desktop.card_height / 2
    assert abs(column_middle - card_middle) <= 1
    assert desktop.card_content_bottom == desktop.card_y + desktop.card_height - desktop.card_pad
    # Mobile: the column above the card.
    assert not mobile.side_by_side
    assert mobile.column_bottom < mobile.card_y
    assert mobile.card_content_bottom == mobile.card_y + mobile.card_height - mobile.card_pad
    assert mobile.card_y + mobile.card_height <= MOBILE_SIZE[1] - mobile.margin
    # Every block box stays in its container and the boxes never overlap.
    for canvas in (desktop, mobile):
        placed = hero.place(canvas)
        column, card = placed[: len(canvas.column)], placed[len(canvas.column) :]
        for first, second in itertools.pairwise(placed):
            if (first in column) == (second in column):
                assert first.bottom <= second.top, (canvas.name, first.setting.key)
        for item in card:
            assert item.x == canvas.card_x + canvas.card_pad
            assert item.max_width == canvas.card_inner_width
        for item in column:
            assert item.x == canvas.column_x
            assert item.max_width == canvas.column_width
    # The widest lines fit at the nominal 0.6 em advance.
    for canvas in (desktop, mobile):
        for item in hero.place(canvas):
            widest = max(len(line) for line in item.setting.lines) * 0.6 * item.setting.size
            assert widest <= item.max_width, (canvas.name, item.setting.key)
    with pytest.raises(ValueError, match="text column needs 501 units; limit is 480"):
        hero.require_layout(dataclasses.replace(desktop, column_y=80))
    with pytest.raises(ValueError, match="card content needs 464 units; limit is 444"):
        hero.require_layout(dataclasses.replace(desktop, card_pad=36, card_x=794, card_width=752))
    with pytest.raises(ValueError, match="card exceeds the canvas width"):
        hero.require_layout(dataclasses.replace(desktop, card_x=900))
    with pytest.raises(ValueError, match="text column overlaps the card"):
        hero.require_layout(dataclasses.replace(mobile, card_y=700))
    with pytest.raises(
        ValueError, match=r"card spans 742\.\.1572 units; the margins allow 16\.\.1560"
    ):
        hero.require_layout(dataclasses.replace(mobile, card_height=830))
    with pytest.raises(ValueError, match="text column starts 10 units from the top"):
        hero.require_layout(dataclasses.replace(mobile, column_y=10))


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
    return "".join(c.text for c in kit.hero.COPY)


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
    ("name", "size", "canvas_name"),
    [
        (DESKTOP[0], DESKTOP_SIZE, "DESKTOP"),
        (DESKTOP[1], DESKTOP_SIZE, "DESKTOP"),
        (MOBILE[0], MOBILE_SIZE, "MOBILE"),
        (MOBILE[1], MOBILE_SIZE, "MOBILE"),
    ],
)
def test_structure_is_one_text_column_and_one_evidence_card(
    kit: ModuleType, rendered: dict[str, bytes], name: str, size: tuple[int, int], canvas_name: str
) -> None:
    hero = kit.hero
    canvas = getattr(hero, canvas_name)
    root = _tree(rendered[name])
    width, height = size
    assert (root.get("width"), root.get("height")) == (str(width), str(height))
    assert root.get("viewBox") == f"0 0 {width} {height}"
    groups = [child.get("id") for child in root if child.tag == f"{SVG_NS}g"]
    assert groups == ["column", "card"]
    column = root.find(f"{SVG_NS}g[@id='column']")
    card = root.find(f"{SVG_NS}g[@id='card']")
    assert column is not None
    assert card is not None
    assert [g.get("id") for g in column] == list(COLUMN_KEYS)
    card_rect, *card_blocks = list(card)
    assert card_rect.tag == f"{SVG_NS}rect"
    assert [g.get("id") for g in card_blocks] == list(CARD_KEYS)
    assert (card_rect.get("x"), card_rect.get("y")) == (str(canvas.card_x), str(canvas.card_y))
    assert (card_rect.get("width"), card_rect.get("height")) == (
        str(canvas.card_width),
        str(canvas.card_height),
    )
    assert card_rect.get("rx") == str(canvas.radius)
    # One path per non-blank colour span; no arrows, strokes or open routes.
    for block in [*column, *card_blocks]:
        setting = canvas.setting(block.get("id"))
        spans = hero.line_spans(hero.copy_for(setting.key), setting.lines)
        expected = sum(1 for line in spans for span in line if span.text.strip())
        paths = block.findall(f"{SVG_NS}path")
        assert len(paths) == expected, setting.key
        assert all((p.get("d") or "").startswith("M") for p in paths)
    assert root.findall(f".//{SVG_NS}line") == []
    assert root.findall(f".//{SVG_NS}polygon") == []
    assert [p for p in root.iter(f"{SVG_NS}path") if p.get("fill") == "none"] == []
    assert [e for e in root.iter() if e.get("stroke")] == []


def test_highlight_colours_follow_each_palette(kit: ModuleType, rendered: dict[str, bytes]) -> None:
    hero = kit.hero
    for names, palette in (
        ((DESKTOP[0], MOBILE[0]), hero.LIGHT),
        ((DESKTOP[1], MOBILE[1]), hero.DARK),
    ):
        for name in names:
            root = _tree(rendered[name])
            fills = {
                g.get("id"): {p.get("fill") for p in g.findall(f"{SVG_NS}path")}
                for g in root.iter(f"{SVG_NS}g")
                if g.get("id") not in {"column", "card"}
            }
            assert fills["eyebrow"] == {palette.accent, palette.muted}, name
            assert fills["thesis"] == {palette.heading}, name
            assert fills["subline"] == {palette.body}, name
            assert fills["card-label"] == {palette.card_muted}, name
            assert fills["card-headline"] == {palette.card_text, palette.blue, palette.red}, name
            assert fills["card-bounds"] == {palette.card_text, palette.red}, name
            assert fills["card-verdict"] == {palette.amber, palette.card_text}, name
            assert fills["card-footer"] == {palette.card_muted}, name
            ground = root.find(f"{SVG_NS}rect")
            assert ground is not None
            assert ground.get("fill") == palette.canvas
            card = root.find(f"{SVG_NS}g[@id='card']/{SVG_NS}rect")
            assert card is not None
            assert card.get("fill") == palette.card


def test_light_and_dark_differ_only_in_color(rendered: dict[str, bytes]) -> None:
    for light_name, dark_name in (DESKTOP, MOBILE):
        assert rendered[light_name] != rendered[dark_name]
        light, dark = _tree(rendered[light_name]), _tree(rendered[dark_name])
        for a, b in zip(light.iter(), dark.iter(), strict=True):
            assert a.tag == b.tag
            assert (a.text or "").strip() == (b.text or "").strip()
            assert set(a.attrib) == set(b.attrib)
            for key in a.attrib:
                if key in {"fill", "stroke"}:
                    continue
                assert a.get(key) == b.get(key), (a.tag, key)


def test_overflowing_line_fails_instead_of_shrinking(
    kit: ModuleType, doubles_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hero = kit.hero
    monkeypatch.setattr(hero, "DESKTOP", dataclasses.replace(hero.DESKTOP, column_width=300))
    with pytest.raises(
        ValueError,
        match=r"desktop: 'actseal · frozen decision policies ·' is 583.2 units wide at size 27; "
        r"only 300 units are available",
    ):
        hero.render(_context(kit, doubles_root))


def test_missing_glyph_in_the_font_is_an_error(kit: ModuleType, tmp_path: Path) -> None:
    fonts = tmp_path / kit.inventory.FONT_DIR
    fonts.mkdir(parents=True)
    without_arrow = _all_text(kit).replace("→", "")
    _build_double(fonts / PINNED_NAMES[0], without_arrow, box=440)
    _build_double(fonts / PINNED_NAMES[1], without_arrow, box=480)
    with pytest.raises(kit.outline.OutlineError, match="no glyph for '→'"):
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
