"""Composition, wiring and fail-loud behaviour of the social preview, without resvg or fonts.

Nothing here runs resvg, reads a font file, fetches anything or produces an
asset. Three kinds of **unit double** stand in for the authentic inputs, each
labelled where it is built:

- zero-byte files under the pinned font *names* satisfy the presence check
  only; they hold none of the pinned font's bytes and are never read;
- an outline double replaces ``hero.outline_text`` with rectangle path data at
  the nominal 0.6 em monospace advance, so no fontTools import happens;
- a binary double replaces ``tools.verified_binary`` with a fixed path and a
  process double replaces ``tools.run_tool``, writing only a PNG header of the
  requested size.

Every byte they yield is a transient test fixture inside a temporary
directory, never social output or evidence. The tool cache is pointed at an
empty temporary directory so no external cache is consulted. The in-process
pipeline runs below are unit tests of the wiring, not the Task 15 done-when
command, which stays unrun until the authentic font and resvg exist.
"""

from __future__ import annotations

import dataclasses
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from visual.visual_support import make_output, png_bytes

SVG_NS = "{http://www.w3.org/2000/svg}"
OUTPUT = "social.png"
WIDTH = 1280
HEIGHT = 640
WORDMARK = "Actseal"
TAGLINE = "Test model-chosen actions. Replay the evidence."
STEPS = ("freeze", "run", "replay")
PINNED_NAMES = ("JetBrainsMono-Regular.ttf", "JetBrainsMono-Bold.ttf")
FONT_NOT_FETCHED = (
    "requires jetbrains-mono 2.304; not fetched: JetBrainsMono-Regular.ttf, "
    "JetBrainsMono-Bold.ttf, OFL.txt"
)
SKIPPED = "skipped rendering because prerequisites failed"
MIN_PX = 14.0
# Nominal JetBrains Mono advance; the outline double uses it for every glyph.
ADVANCE_EM = 0.6
# Transient fixture: signature and IHDR only, the size the renderer must demand.
HEADER_PNG = png_bytes(WIDTH, HEIGHT)


def _tree(data: bytes) -> ET.Element:
    return ET.fromstring(data)  # noqa: S314 - own freshly rendered bytes


def _errors(report: Any) -> list[str]:
    return [finding.message for finding in report.errors]


def _context(kit: ModuleType, root: Path) -> Any:
    return kit.inventory.RenderContext(root=root, work=root / "work")


@pytest.fixture(autouse=True)
def _empty_tool_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No test may consult the operator's tool cache; verification sees an empty one."""
    monkeypatch.setenv("ACTSEAL_ASSET_TOOLS", str(tmp_path / "empty-tool-cache"))


# --- unit doubles -------------------------------------------------------------


def _font_name_stand_ins(kit: ModuleType, root: Path) -> Path:
    """Zero-byte files under the pinned font names: presence only, never read.

    Unit double. These carry none of the pinned font's glyphs, metrics or
    bytes; the outline double below means nothing ever opens them.
    """
    fonts: Path = root / kit.inventory.FONT_DIR
    fonts.mkdir(parents=True, exist_ok=True)
    for name in PINNED_NAMES:
        (fonts / name).write_bytes(b"")
    return fonts


def _outline_double(kit: ModuleType, monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """Replace ``hero.outline_text`` with rectangles at a 0.6 em advance.

    Unit double. Records ``(font file name, text)`` per call and never imports
    fontTools, so these tests also run in the core environment.
    """
    calls: list[tuple[str, str]] = []
    fmt = kit.svg.fmt

    def outline_text(
        font_path: Path,
        text: str,
        *,
        size: float,
        x: float = 0.0,
        y: float = 0.0,
        tracking: float = 0.0,
    ) -> Any:
        calls.append((font_path.name, text))
        advance = len(text) * ADVANCE_EM * size + len(text) * tracking
        d = f"M{fmt(x)} {fmt(y)} h{fmt(advance)} v{fmt(-0.7 * size)} h{fmt(-advance)} Z"
        return kit.outline.Outline(d, advance)

    monkeypatch.setattr(kit.hero, "outline_text", outline_text)
    return calls


def _binary_double(kit: ModuleType, monkeypatch: pytest.MonkeyPatch, path: Path) -> list[str]:
    """Replace ``tools.verified_binary`` with a fixed path; records the tool names asked for."""
    calls: list[str] = []

    def verified_binary(_root: Path, tool: Any, _platform: str | None = None) -> Path:
        calls.append(tool.name)
        return path

    monkeypatch.setattr(kit.tools, "verified_binary", verified_binary)
    return calls


def _process_double(
    kit: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    *,
    produce: bytes | None = HEADER_PNG,
    fail: Exception | None = None,
) -> list[list[str]]:
    """Replace ``tools.run_tool``; records commands and writes ``produce`` to the PNG path.

    Unit double. ``produce`` is a transient header-only PNG fixture, not a
    rendered image. ``None`` simulates a run that writes nothing; ``fail``
    is raised instead of running.
    """
    commands: list[list[str]] = []

    def run_tool(
        command: list[str], *, cwd: Path | None = None, timeout: float = 0.0
    ) -> subprocess.CompletedProcess[bytes]:
        del cwd, timeout
        commands.append(list(command))
        if fail is not None:
            raise fail
        if produce is not None:
            Path(command[-1]).write_bytes(produce)
        return subprocess.CompletedProcess(command, 0, b"", b"")

    monkeypatch.setattr(kit.tools, "run_tool", run_tool)
    return commands


@dataclasses.dataclass(slots=True)
class Doubled:
    """Everything a doubled render records, for assertions."""

    context: Any
    binary: Path
    outlines: list[tuple[str, str]]
    binaries: list[str]
    commands: list[list[str]]


def _doubled(
    kit: ModuleType,
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    produce: bytes | None = HEADER_PNG,
    fail: Exception | None = None,
) -> Doubled:
    """All three doubles over a ``repo`` root, which carries the real manifest copy."""
    _font_name_stand_ins(kit, root)
    binary = root / "doubled-cache" / "resvg"
    return Doubled(
        context=_context(kit, root),
        binary=binary,
        outlines=_outline_double(kit, monkeypatch),
        binaries=_binary_double(kit, monkeypatch, binary),
        commands=_process_double(kit, monkeypatch, produce=produce, fail=fail),
    )


# --- copy, declarations and floors: no doubles required -----------------------


def test_social_reuses_the_approved_copy_and_declares_one_png(kit: ModuleType) -> None:
    social = kit.social
    assert social.OUTPUT == OUTPUT
    assert (social.WIDTH, social.HEIGHT) == (WIDTH, HEIGHT)
    assert (social.WIDTH, social.HEIGHT) == (
        kit.inventory.SOCIAL_WIDTH,
        kit.inventory.SOCIAL_HEIGHT,
    )
    assert social.PALETTE is kit.hero.LIGHT
    assert isinstance(social.CANVAS, kit.hero.Canvas)
    # No social-specific copy exists: wordmark, tagline, motif steps, title and
    # description all come from the hero module, and like the hero the card
    # carries no caption paragraph.
    for name in ("WORDMARK", "TAGLINE", "CAPTION", "MOTIF_STEPS", "TITLE", "DESC"):
        assert not hasattr(social, name), name
    assert not hasattr(social.CANVAS, "caption")
    assert kit.hero.WORDMARK == WORDMARK
    assert kit.hero.TAGLINE == TAGLINE
    assert kit.hero.MOTIF_STEPS == STEPS


def test_inventory_registers_the_social_renderer_without_other_changes(kit: ModuleType) -> None:
    asset = kit.inventory.get_asset("social")
    assert asset.implemented
    assert asset.renderer is kit.social.render
    assert asset.task == "15"
    assert asset.priority == "required"
    assert asset.needs == ("resvg", "jetbrains-mono", "fonttools")
    assert asset.sources == ()
    assert len(asset.outputs) == 1
    output = asset.outputs[0]
    assert (output.path, output.kind, output.width, output.height) == (OUTPUT, "png", WIDTH, HEIGHT)
    assert output.display_width is None
    assert output.outlined is False
    assert output.max_bytes is None
    assert kit.inventory.validate_inventory() == []
    assert kit.inventory.get_asset("hero").renderer is kit.hero.render


def test_type_sizes_meet_the_floor_and_geometry_fits_the_card(kit: ModuleType) -> None:
    social, hero = kit.social, kit.hero
    canvas = social.CANVAS
    assert (canvas.width, canvas.display_width) == (WIDTH, social.DISPLAY_WIDTH)
    hero.require_readable(canvas)
    hero._require_extents(canvas, social.HEIGHT)
    assert min(canvas.sizes) == canvas.label
    assert canvas.rendered_px(min(canvas.sizes)) >= MIN_PX
    assert canvas.rendered_px(canvas.label) == pytest.approx(34.0)
    assert canvas.wordmark > canvas.tagline > canvas.label
    # Stacked order: wordmark, tagline, then the motif.
    assert canvas.margin <= canvas.text_top
    assert canvas.wordmark_baseline < canvas.tagline_baseline
    assert canvas.text_bottom < canvas.motif_top
    assert canvas.motif_bottom <= social.HEIGHT - canvas.margin
    # The block is centred: the space above the wordmark's cap height and
    # below the pills differs by less than one unit, and the pill row leaves
    # the same 85 units at each side.
    above = canvas.wordmark_baseline - 0.73 * canvas.wordmark
    below = social.HEIGHT - canvas.motif_bottom
    assert abs(above - below) < 1
    assert canvas.motif_x == canvas.text_x == WIDTH - (canvas.motif_x + canvas.motif_width) == 85
    assert canvas.text_x + canvas.text_width <= WIDTH - canvas.margin
    too_small = dataclasses.replace(canvas, label=26)
    with pytest.raises(ValueError, match=r"26 units render at 13.0px .* minimum is 14px"):
        hero.require_readable(too_small)
    with pytest.raises(ValueError, match="motif needs 540 units of height"):
        hero._require_extents(canvas, 560)


def test_card_is_the_desktop_hero_composition_at_three_quarters(kit: ModuleType) -> None:
    """Every size, stroke and vertical offset is the hero's times SCALE, to whole units."""
    social, hero = kit.social, kit.hero
    card, desktop = social.CANVAS, hero.DESKTOP
    assert social.SCALE == 0.75
    for name in (
        "wordmark",
        "tagline",
        "label",
        "tagline_step",
        "text_width",
        "pill_width",
        "pill_height",
        "pill_gap",
        "pill_pad",
        "border",
        "arrow_stroke",
        "arrow_head",
        "arrow_half",
        "arrow_clearance",
    ):
        expected = social.SCALE * getattr(desktop, name)
        assert abs(getattr(card, name) - expected) <= 1.5, name
    assert card.motif_width == social.SCALE * desktop.motif_width
    for top, bottom in (
        ("wordmark_baseline", "tagline_baseline"),
        ("tagline_baseline", "motif_top"),
    ):
        offset = getattr(card, bottom) - getattr(card, top)
        assert offset == social.SCALE * (getattr(desktop, bottom) - getattr(desktop, top))


def test_exact_png_dimensions_are_required(kit: ModuleType) -> None:
    social = kit.social
    good = png_bytes(WIDTH, HEIGHT)
    assert social.require_dimensions(good) is good
    with pytest.raises(
        ValueError, match="1280x639 PNG; the social preview must be exactly 1280x640"
    ):
        social.require_dimensions(png_bytes(WIDTH, HEIGHT - 1))
    with pytest.raises(ValueError, match="not a PNG file"):
        social.require_dimensions(b"<svg/>")


# --- missing inputs: fail before drawing, nothing substituted ------------------


def test_missing_pinned_fonts_fail_before_resvg_or_outlining(
    kit: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outlines = _outline_double(kit, monkeypatch)
    binaries = _binary_double(kit, monkeypatch, repo / "never")
    commands = _process_double(kit, monkeypatch)
    with pytest.raises(kit.outline.OutlineError) as absent:
        kit.social.render(_context(kit, repo))
    message = str(absent.value)
    assert "JetBrainsMono-Regular.ttf, JetBrainsMono-Bold.ttf" in message
    assert "setup_tools.py --tool jetbrains-mono" in message
    assert "No substitute font is used" in message
    assert outlines == []
    assert binaries == []
    assert commands == []
    assert not (repo / "work").exists()


def test_missing_resvg_fails_before_outlining(
    kit: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real verification against the real pin and an empty cache: no outline, SVG or process."""
    _font_name_stand_ins(kit, repo)
    outlines = _outline_double(kit, monkeypatch)
    commands = _process_double(kit, monkeypatch)
    with pytest.raises(kit.tools.ToolError, match=r"resvg 0\.48\.1") as missing:
        kit.social.render(_context(kit, repo))
    message = str(missing.value)
    assert "empty-tool-cache" in message or "no pinned artifact" in message
    assert outlines == []
    assert commands == []
    assert not (repo / "work").exists()


def test_unpinned_resvg_is_an_error(
    kit: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _font_name_stand_ins(kit, repo)
    monkeypatch.setattr(kit.social, "RESVG", "not-a-pinned-tool")
    with pytest.raises(kit.tools.ToolError, match="not-a-pinned-tool is not pinned in"):
        kit.social.render(_context(kit, repo))


def test_pipeline_blocks_social_in_a_bootstrap_repository(kit: ModuleType, repo: Path) -> None:
    """The real declaration where neither the font nor resvg was fetched."""
    asset = kit.inventory.get_asset("social")
    for mode in ("check", "write"):
        report = kit.pipeline.run(repo, mode=mode, only=("social",), assets=(asset,))
        errors = _errors(report)
        assert len(errors) == 3
        assert errors[0].startswith("requires resvg 0.48.1: ")
        assert errors[1:] == [FONT_NOT_FETCHED, SKIPPED]
        assert report.checked == []
        assert report.written == []
        assert report.planned == []
    assert not any((repo / "docs" / "assets").glob("social*"))


def test_in_process_check_of_social_exits_one_without_inputs(
    kit: ModuleType, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """In-process form of ``render.py --check --only social``; not the done-when command."""
    assert kit.cli.main(["--check", "--only", "social"], root=repo) == 1
    out = capsys.readouterr().out
    assert "[error] social: requires resvg 0.48.1: " in out
    assert f"[error] social: {FONT_NOT_FETCHED}" in out
    assert f"[error] social: {SKIPPED}" in out
    assert "[ok] social" not in out
    assert "social: not implemented" not in out
    assert out.rstrip().endswith("0 asset(s) checked; 0 planned/not implemented; 3 error(s)")


# --- composition and wiring with unit doubles ---------------------------------


def test_render_returns_exactly_social_png_from_the_process_double(
    kit: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    doubled = _doubled(kit, repo, monkeypatch)
    rendered = dict(kit.social.render(doubled.context))
    assert tuple(rendered) == (OUTPUT,)
    assert rendered[OUTPUT] == png_bytes(WIDTH, HEIGHT)
    assert doubled.binaries == ["resvg"]
    assert len(doubled.commands) == 1


def test_resvg_command_is_wired_with_exact_size_and_pinned_fonts_only(
    kit: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    doubled = _doubled(kit, repo, monkeypatch)
    kit.social.render(doubled.context)
    work = doubled.context.work
    source, target = work / "social.svg", work / OUTPUT
    (command,) = doubled.commands
    assert command == kit.tools.resvg_command(
        doubled.binary, source, target, width=WIDTH, height=HEIGHT, font_dir=doubled.context.fonts
    )
    assert command[0] == str(doubled.binary)
    assert command[command.index("--width") + 1] == "1280"
    assert command[command.index("--height") + 1] == "640"
    assert command[command.index("--use-fonts-dir") + 1] == str(doubled.context.fonts)
    assert "--skip-system-fonts" in command
    assert command[-2:] == [str(source), str(target)]
    assert source.is_file()
    assert source.read_bytes() == kit.social.compose(kit.hero.require_fonts(doubled.context))


def test_intermediate_svg_is_the_hero_composition_outlined_on_the_card(
    kit: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    doubled = _doubled(kit, repo, monkeypatch)
    kit.social.render(doubled.context)
    data = (doubled.context.work / "social.svg").read_bytes()
    probe = make_output(
        kit, "social.svg", width=WIDTH, height=HEIGHT, display_width=640, outlined=True
    )
    assert kit.checks.check_output(data, probe) == []
    assert b"<text" not in data
    assert b"font-family" not in data
    assert b"transform" not in data
    root = _tree(data)
    assert (root.get("width"), root.get("height")) == ("1280", "640")
    assert root.get("viewBox") == "0 0 1280 640"
    title = root.find(f"{SVG_NS}title")
    desc = root.find(f"{SVG_NS}desc")
    assert title is not None
    assert desc is not None
    assert title.text == kit.hero.TITLE
    assert desc.text == kit.hero.DESC
    canvas = root.find(f"{SVG_NS}rect")
    assert canvas is not None
    assert (canvas.get("width"), canvas.get("height"), canvas.get("fill")) == (
        "1280",
        "640",
        "#ffffff",
    )
    groups = [child.get("id") for child in root if child.tag == f"{SVG_NS}g"]
    assert groups == ["wordmark", "tagline", "motif"]
    motif = root.find(f"{SVG_NS}g[@id='motif']")
    assert motif is not None
    steps = [child for child in motif if child.tag == f"{SVG_NS}g"]
    assert [step.get("id") for step in steps] == [f"step-{step}" for step in STEPS]
    for step in steps:
        assert step.find(f"{SVG_NS}rect") is not None
        assert len(step.findall(f"{SVG_NS}path")) == 1
    # Two forward arrows and no return route, exactly as in the hero.
    lines = motif.findall(f".//{SVG_NS}line")
    assert len(lines) == 2
    assert all(float(a.get("x2", "0")) > float(a.get("x1", "0")) for a in lines)
    assert len(motif.findall(f".//{SVG_NS}polygon")) == 2
    routes = [p for p in root.iter(f"{SVG_NS}path") if p.get("fill") == "none"]
    assert routes == []
    glyphs = [p for p in root.iter(f"{SVG_NS}path") if p.get("fill") != "none"]
    # Wordmark, two tagline lines and three labels.
    assert len(glyphs) == 6
    assert all((p.get("d") or "").startswith("M") for p in glyphs)
    xs = [float(r.get("x", "0")) for r in motif.iter(f"{SVG_NS}rect")]
    assert xs == sorted(xs)
    assert len({r.get("y") for r in motif.iter(f"{SVG_NS}rect")}) == 1


def test_every_outlined_string_is_approved_copy(
    kit: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    doubled = _doubled(kit, repo, monkeypatch)
    kit.social.render(doubled.context)
    hero = kit.hero
    approved = {
        (PINNED_NAMES[1], WORDMARK),
        *((PINNED_NAMES[0], line) for line in hero.TAGLINE_LINES),
        *((PINNED_NAMES[0], step) for step in STEPS),
    }
    assert set(doubled.outlines) == approved
    # Each string is measured once and placed once.
    assert len(doubled.outlines) == 2 * len(approved)
    assert " ".join(hero.TAGLINE_LINES) == TAGLINE


def test_render_is_deterministic_with_the_doubles(
    kit: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    doubled = _doubled(kit, repo, monkeypatch)
    first = dict(kit.social.render(doubled.context))
    first_svg = (doubled.context.work / "social.svg").read_bytes()
    second = dict(kit.social.render(doubled.context))
    assert first == second
    assert (doubled.context.work / "social.svg").read_bytes() == first_svg
    asset = kit.inventory.get_asset("social")
    _, problems = kit.pipeline._render_twice(asset, doubled.context)
    assert problems == []


def test_overflowing_line_fails_instead_of_shrinking(
    kit: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    doubled = _doubled(kit, repo, monkeypatch)
    narrow = dataclasses.replace(kit.social.CANVAS, text_width=400)
    monkeypatch.setattr(kit.social, "CANVAS", narrow)
    with pytest.raises(ValueError, match=r"units wide at size 135; only 400 units are available"):
        kit.social.render(doubled.context)
    assert doubled.commands == []
    assert not (doubled.context.work / OUTPUT).exists()


# --- failure propagation from the rasterizer ---------------------------------


def test_tool_failure_propagates_unchanged(
    kit: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    failure = kit.tools.ToolError("resvg exited 1: transient double failure")
    doubled = _doubled(kit, repo, monkeypatch, fail=failure)
    with pytest.raises(kit.tools.ToolError, match="exited 1: transient double failure") as raised:
        kit.social.render(doubled.context)
    assert raised.value is failure
    assert not (doubled.context.work / OUTPUT).exists()


def test_process_that_writes_nothing_is_an_error_even_with_a_stale_file(
    kit: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    doubled = _doubled(kit, repo, monkeypatch, produce=None)
    stale = doubled.context.work / OUTPUT
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"stale bytes from an earlier run")
    with pytest.raises(kit.tools.ToolError, match=r"exited 0 but did not write .*social\.png"):
        kit.social.render(doubled.context)
    assert not stale.exists()


@pytest.mark.parametrize(
    ("produce", "match"),
    [
        (png_bytes(1200, 630), "1200x630 PNG; the social preview must be exactly 1280x640"),
        (png_bytes(WIDTH, HEIGHT - 1), "1280x639 PNG"),
        (b"not a png at all", "not a PNG file"),
    ],
)
def test_wrong_output_from_the_rasterizer_is_an_error(
    kit: ModuleType,
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    produce: bytes,
    match: str,
) -> None:
    doubled = _doubled(kit, repo, monkeypatch, produce=produce)
    with pytest.raises(ValueError, match=match):
        kit.social.render(doubled.context)


# --- pipeline wiring with unit doubles -----------------------------------------


def _install_doubles(
    kit: ModuleType,
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    produce: bytes | None = HEADER_PNG,
) -> Doubled:
    """Point the copied manifest at the stand-in font files so the pin check passes.

    Unit doubles only: the manifest copy inside ``repo`` is re-pinned to the
    zero-byte stand-ins' hash and a notice with the required markers is
    written. The repository's own ``tools.toml`` is untouched.
    """
    doubled = _doubled(kit, repo, monkeypatch, produce=produce)
    manifest = repo / kit.inventory.MANIFEST_FILE
    text = manifest.read_text(encoding="utf-8")
    pins = {
        PINNED_NAMES[0]: "a0bf60ef0f83c5ed4d7a75d45838548b1f6873372dfac88f71804491898d138f",
        PINNED_NAMES[1]: "5590990c82e097397517f275f430af4546e1c45cff408bde4255dad142479dcb",
    }
    fonts = repo / kit.inventory.FONT_DIR
    for name, pin in pins.items():
        text = text.replace(pin, kit.tools.sha256_bytes((fonts / name).read_bytes()))
    manifest.write_text(text, encoding="utf-8")
    (fonts / "OFL.txt").write_text(
        "Copyright 2020 The JetBrains Mono Project Authors\n"
        "SIL OPEN FONT LICENSE Version 1.1 - 26 February 2007\n",
        encoding="utf-8",
    )
    return doubled


def test_write_then_check_round_trip_with_unit_doubles(
    kit: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Pipeline wiring only; the PNG written here is a header-only fixture, not an asset."""
    doubled = _install_doubles(kit, repo, monkeypatch)
    asset = kit.inventory.get_asset("social")
    written = kit.pipeline.run(repo, mode="write", only=("social",), assets=(asset,))
    assert _errors(written) == []
    assert written.written == [OUTPUT]
    assert written.checked == ["social"]
    target = repo / "docs" / "assets" / OUTPUT
    assert target.read_bytes() == png_bytes(WIDTH, HEIGHT)
    assert kit.checks.png_dimensions(target.read_bytes()) == (WIDTH, HEIGHT)
    # Two renders per run: the pipeline's determinism comparison.
    assert doubled.binaries == ["resvg"] * 3
    assert len(doubled.commands) == 2
    checked = kit.pipeline.run(repo, mode="check", only=("social",), assets=(asset,))
    assert _errors(checked) == []
    assert checked.checked == ["social"]
    assert kit.cli.main(["--check", "--only", "social"], root=repo) == 0
    out = capsys.readouterr().out
    assert "[ok] fonts: jetbrains-mono 2.304 present with upstream notice" in out
    assert f"[ok] social: docs/assets/{OUTPUT} matches regeneration (" in out
    assert out.rstrip().endswith("1 asset(s) checked; 0 planned/not implemented; 0 error(s)")


def test_pipeline_reports_a_rasterizer_failure_without_writing(
    kit: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_doubles(kit, repo, monkeypatch, produce=png_bytes(1200, 630))
    asset = kit.inventory.get_asset("social")
    report = kit.pipeline.run(repo, mode="write", only=("social",), assets=(asset,))
    assert _errors(report) == [
        "render failed: resvg produced a 1200x630 PNG; the social preview must be exactly 1280x640"
    ]
    assert report.checked == []
    assert report.written == []
    assert not (repo / "docs" / "assets" / OUTPUT).exists()
