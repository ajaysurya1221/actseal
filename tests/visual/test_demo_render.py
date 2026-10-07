"""The demo GIF renderer with synthetic casts and GIFs; nothing is recorded or rendered.

Everything here is a **unit fixture or double**, built under ``tmp_path`` and
labelled where it is built:

- a *synthetic cast* carrying the approved header shape, the helper's printed
  command and exit markers and a final exit event, with authored intervals;
  it is not a recording of anything and is never written under ``docs/assets``
  of the repository;
- a *synthetic GIF* with a valid block structure, a chosen number of frames
  and authored frame delays, no meaningful pixels;
- a binary double for ``tools.verified_binary``, a process double for
  ``tools.run_tool`` that writes the synthetic GIF, and zero-byte font
  stand-ins that satisfy presence only.

The tool cache is pointed at an empty temporary directory so no external
cache is consulted. The real inventory still declares the demo as planned;
pipeline runs below use a temporary asset declaration inside ``tmp_path``.
No test invokes agg, asciinema, uvx or a package.
"""

from __future__ import annotations

import importlib
import json
import math
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from visual.visual_support import SRC_DIR, make_asset, make_output

LIGHT = "demo-light.gif"
DARK = "demo-dark.gif"
OUTPUTS = (LIGHT, DARK)
COMMANDS = (
    "$ uvx --python 3.12 actseal demo --out ./actseal-demo",
    "$ uvx --offline --python 3.12 actseal replay ./actseal-demo/fixed/evidence",
    "$ uvx --offline --python 3.12 actseal replay ./actseal-demo/bad/evidence",
)
EXITS = ("exit 0 (expected 0)", "exit 0 (expected 0)", "exit 1 (expected 1)")
SUMMARY = "demo-session: all 3 commands exited as expected (0, 0, 1)"
PINNED_FONTS = ("JetBrainsMono-Regular.ttf", "JetBrainsMono-Bold.ttf")
FONT_PINS = {
    PINNED_FONTS[0]: "a0bf60ef0f83c5ed4d7a75d45838548b1f6873372dfac88f71804491898d138f",
    PINNED_FONTS[1]: "5590990c82e097397517f275f430af4546e1c45cff408bde4255dad142479dcb",
}


def _short_id(value: object) -> str | None:
    """Parametrize ids: the match text; bytes fixtures never appear in ids or diffs."""
    return value if isinstance(value, str) else "fixture"


@pytest.fixture(autouse=True, scope="session")
def _load_demo_module(kit: ModuleType) -> None:
    """The package init does not import ``demo`` until the inventory registers it.

    Importing the submodule binds ``kit.demo`` for these tests without any
    change to the package.
    """
    importlib.import_module("actseal_assets.demo")
    assert hasattr(kit, "demo")


@pytest.fixture(autouse=True)
def _empty_tool_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No test may consult the operator's tool cache; verification sees an empty one."""
    monkeypatch.setenv("ACTSEAL_ASSET_TOOLS", str(tmp_path / "empty-tool-cache"))


# --- synthetic fixtures ----------------------------------------------------------


def synthetic_events(*, pause: float = 4.0, hold: float = 3.0) -> list[list[object]]:
    """Authored v3 events mirroring the helper's output; a fixture, not a capture."""
    events: list[list[object]] = [
        [0.5, "o", "demo-session: 3 commands; expected exits 0, 0, 1\r\n"],
    ]
    for command, exit_line in zip(COMMANDS, EXITS, strict=True):
        events.append([pause, "o", command + "\r\n"])
        events.append([0.4, "o", "demo: synthetic fixture output line\r\n"])
        events.append([0.3, "o", exit_line + "\r\n"])
        events.append([hold, "o", ""])
    events.append([0.1, "o", SUMMARY + "\r\n"])
    events.append([0.05, "x", "0"])
    return events


def synthetic_cast(
    events: Sequence[Sequence[object]] | None = None,
    *,
    version: int = 3,
    cols: int = 100,
    rows: int = 40,
) -> bytes:
    """A synthetic asciicast; the header command is inert text and never executed."""
    header: dict[str, object] = {
        "version": version,
        "term": {"cols": cols, "rows": rows, "type": "xterm-256color"},
        "timestamp": 0,
        "command": "/synthetic/python /synthetic/demo_session.py",
        "env": {"TERM": "xterm-256color", "LANG": "C.UTF-8"},
    }
    chosen = [list(event) for event in (synthetic_events() if events is None else events)]
    if version == 2:  # v2 header shape and absolute times, used only by the rejection test
        header = {"version": 2, "width": cols, "height": rows}
        clock = 0.0
        for event in chosen:
            stamp = event[0]
            assert isinstance(stamp, int | float)
            clock += float(stamp)
            event[0] = clock
    lines = [json.dumps(header)]
    lines.extend(json.dumps(event) for event in chosen)
    return ("\n".join(lines) + "\n").encode("utf-8")


def total_seconds(events: Sequence[Sequence[object]]) -> float:
    total = 0.0
    for event in events:
        stamp = event[0]
        assert isinstance(stamp, int | float)
        total += float(stamp)
    return total


def _sub_blocks(payload: bytes) -> bytes:
    out = bytearray()
    for start in range(0, len(payload), 255):
        chunk = payload[start : start + 255]
        out += bytes([len(chunk)]) + chunk
    out += b"\x00"
    return bytes(out)


def synthetic_gif(
    delays_cs: Sequence[int],
    *,
    width: int = 8,
    height: int = 4,
    padding: int = 0,
    global_table: bool = True,
    local_table: bool = False,
    trailer: bool = True,
    trailing_junk: bytes = b"",
) -> bytes:
    """A structurally complete GIF with one frame per delay; a fixture, not a render.

    Pixel data is a two-byte LZW stream that decoders treat as an empty
    image; only the block structure and the graphic control delays matter.
    ``padding`` appends an application extension of that many bytes so size
    bounds can be exercised without more frames.
    """
    flags = 0x80 if global_table else 0x00  # 2-colour global table when present
    data = bytearray(b"GIF89a")
    data += width.to_bytes(2, "little") + height.to_bytes(2, "little")
    data += bytes([flags, 0x00, 0x00])
    if global_table:
        data += b"\x00\x00\x00\xff\xff\xff"
    if padding:
        data += b"\x21\xff\x0bSYNTHETIC00" + _sub_blocks(b"\x00" * padding)
    for delay in delays_cs:
        data += b"\x21\xf9\x04\x00" + int(delay).to_bytes(2, "little") + b"\x00\x00"
        local_flags = 0x80 if local_table else 0x00
        data += b"\x2c" + (0).to_bytes(4, "little")
        data += width.to_bytes(2, "little") + height.to_bytes(2, "little") + bytes([local_flags])
        if local_table:
            data += b"\x00\x00\x00\xff\xff\xff"
        data += b"\x02" + _sub_blocks(b"\x44\x01")
    if trailer:
        data += b"\x3b"
    data += trailing_junk
    return bytes(data)


#: 20 frames of 1.25 s: 25 s measured, inside the window.
GOOD_DELAYS = (125,) * 20
GOOD_GIF = synthetic_gif(GOOD_DELAYS)
ONE_FRAME = synthetic_gif((100,))


# --- doubles --------------------------------------------------------------------


def _context(kit: ModuleType, root: Path) -> Any:
    return kit.inventory.RenderContext(root=root, work=root / "work")


def _font_stand_ins(kit: ModuleType, root: Path) -> Path:
    """Zero-byte files under the pinned font names: presence only, never read."""
    fonts: Path = root / kit.inventory.FONT_DIR
    fonts.mkdir(parents=True, exist_ok=True)
    for name in PINNED_FONTS:
        (fonts / name).write_bytes(b"")
    return fonts


def _write_cast(kit: ModuleType, root: Path, data: bytes | None = None) -> Path:
    """The synthetic cast at the source path inside the temporary repository only."""
    path: Path = root / kit.inventory.SOURCE_DIR / kit.demo.CAST_SOURCE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(synthetic_cast() if data is None else data)
    return path


def _binary_double(kit: ModuleType, monkeypatch: pytest.MonkeyPatch, path: Path) -> list[str]:
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
    produce: bytes | dict[str, bytes] | None = GOOD_GIF,
    fail: Exception | None = None,
) -> list[list[str]]:
    """Replace ``tools.run_tool``; writes the synthetic GIF to the command's last argument."""
    commands: list[list[str]] = []

    def run_tool(
        command: list[str], *, cwd: Path | None = None, timeout: float = 0.0
    ) -> subprocess.CompletedProcess[bytes]:
        del cwd, timeout
        commands.append(list(command))
        if fail is not None:
            raise fail
        target = Path(command[-1])
        data = produce.get(target.name) if isinstance(produce, dict) else produce
        if data is not None:
            target.write_bytes(data)
        return subprocess.CompletedProcess(command, 0, b"", b"")

    monkeypatch.setattr(kit.tools, "run_tool", run_tool)
    return commands


def _doubled(
    kit: ModuleType,
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    cast: bytes | None = b"",
    produce: bytes | dict[str, bytes] | None = GOOD_GIF,
    fail: Exception | None = None,
) -> tuple[Any, Path, list[str], list[list[str]]]:
    """All doubles over ``repo``; ``cast=b""`` means the default synthetic cast, ``None`` none."""
    _font_stand_ins(kit, repo)
    if cast is not None:
        _write_cast(kit, repo, cast or None)
    binary = repo / "doubled-cache" / "agg"
    binaries = _binary_double(kit, monkeypatch, binary)
    commands = _process_double(kit, monkeypatch, produce=produce, fail=fail)
    return _context(kit, repo), binary, binaries, commands


# --- declarations ---------------------------------------------------------------


def test_outputs_themes_and_bounds_are_frozen(kit: ModuleType) -> None:
    demo = kit.demo
    assert tuple(demo.THEMES) == OUTPUTS
    assert demo.THEMES == {LIGHT: "github-light", DARK: "github-dark"}
    assert demo.CAST_SOURCE == "demo.cast"
    assert (demo.MIN_SECONDS, demo.MAX_SECONDS) == (
        kit.inventory.DEMO_MIN_SECONDS,
        kit.inventory.DEMO_MAX_SECONDS,
    )
    assert demo.MAX_BYTES == kit.inventory.DEMO_GIF_MAX_BYTES == 3_000_000
    assert (demo.COLS, demo.ROWS) == (100, 40)
    assert demo.LAST_FRAME_SECONDS == "3"
    expected = (COMMANDS[0], EXITS[0], COMMANDS[1], EXITS[1], COMMANDS[2], EXITS[2], SUMMARY)
    assert expected == demo.REQUIRED_OUTPUT


def test_markers_match_the_helper_exactly(kit: ModuleType) -> None:
    demo_session = importlib.import_module("demo_session")  # on sys.path through load_kit

    assert kit.demo.REQUIRED_OUTPUT[-1] == SUMMARY
    assert tuple(f"$ {step.label}" for step in demo_session.STEPS) == COMMANDS
    assert (
        tuple(
            f"exit {step.expected_exit} (expected {step.expected_exit})"
            for step in demo_session.STEPS
        )
        == EXITS
    )


def test_inventory_still_declares_the_demo_as_planned(kit: ModuleType) -> None:
    """Registration waits for a genuine capture; this preparation changes nothing there."""
    asset = kit.inventory.get_asset("demo")
    assert not asset.implemented
    assert asset.renderer is None
    assert [output.path for output in asset.outputs] == ["demo.gif"]
    assert asset.sources[0].path == kit.demo.CAST_SOURCE
    assert asset.needs == ("agg", "jetbrains-mono")
    assets_dir = SRC_DIR.parent
    assert not (SRC_DIR / "demo.cast").exists()
    assert not any(assets_dir.glob("demo*.gif"))


def test_module_imports_lazily_and_without_an_inventory_cycle() -> None:
    program = (
        "import sys\n"
        f"sys.path.insert(0, {str(SRC_DIR)!r})\n"
        "import actseal_assets.demo\n"
        "print('ok')\n"
    )
    result = subprocess.run(  # noqa: S603 - fixed interpreter and literal script
        [sys.executable, "-c", program], capture_output=True, text=True, check=False, timeout=120
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"
    text = (SRC_DIR / "actseal_assets" / "demo.py").read_text(encoding="utf-8")
    assert "if TYPE_CHECKING:\n    from .inventory import RenderContext" in text
    assert "from . import tools  # noqa: PLC0415" in text
    assert "\nfrom . import tools\n" not in text
    assert "\nfrom .inventory import" not in text


# --- cast validation -------------------------------------------------------------


def test_synthetic_cast_passes_and_reports_facts(kit: ModuleType) -> None:
    events = synthetic_events()
    facts = kit.demo.validate_cast(synthetic_cast(events))
    assert facts.duration == pytest.approx(total_seconds(events))
    assert 20.0 <= facts.duration <= 40.0
    assert facts.outputs == len(events) - 1
    assert kit.checks.check_cast(synthetic_cast(events), min_seconds=20, max_seconds=40) == []


@pytest.mark.parametrize(
    ("data", "match"),
    [
        (b"", "recording is empty"),
        (b"\xff\xfe", "not UTF-8"),
        (b"{}\n", "unsupported asciicast version"),
        (synthetic_cast(version=2), r"asciicast v2; the procedure records v3"),
        (synthetic_cast(cols=80), r"geometry 80x40; approved capture is 100x40"),
        (synthetic_cast(rows=24), r"geometry 100x24"),
        (synthetic_cast(synthetic_events(pause=1.0, hold=0.5)), r"duration .* is below 20s"),
        (synthetic_cast(synthetic_events(pause=10.0, hold=5.0)), r"duration .* exceeds 40s"),
    ],
    ids=_short_id,
)
def test_malformed_or_out_of_window_casts_are_rejected(
    kit: ModuleType, data: bytes, match: str
) -> None:
    with pytest.raises(kit.demo.DemoError, match=match):
        kit.demo.validate_cast(data)


def _with_event(events: list[list[object]], index: int, event: list[object]) -> list[list[object]]:
    copy = [list(e) for e in events]
    copy.insert(index, event)
    return copy


def test_input_resize_marker_and_unknown_events_are_rejected(kit: ModuleType) -> None:
    base = synthetic_events()
    for code, payload in (("i", "q"), ("r", "120x40"), ("m", "marker"), ("z", "")):
        events = _with_event(base, 3, [0.0, code, payload])
        with pytest.raises(kit.demo.DemoError, match=rf"line 5: event code {code!r}"):
            kit.demo.validate_cast(synthetic_cast(events))


def test_exit_event_must_be_single_final_and_zero(kit: ModuleType) -> None:
    base = synthetic_events()
    without_exit = base[:-1]
    with pytest.raises(
        kit.demo.DemoError, match=r"last event code 'o'; expected a single final 'x'"
    ):
        kit.demo.validate_cast(synthetic_cast(without_exit))
    nonzero = [*base[:-1], [0.05, "x", "1"]]
    with pytest.raises(kit.demo.DemoError, match=r"exit event payload '1'"):
        kit.demo.validate_cast(synthetic_cast(nonzero))
    integer_payload = [*base[:-1], [0.05, "x", 0]]
    with pytest.raises(kit.demo.DemoError, match=r"exit event payload 0;"):
        kit.demo.validate_cast(synthetic_cast(integer_payload))
    early_exit = _with_event(base, 2, [0.0, "x", "0"])
    with pytest.raises(kit.demo.DemoError, match=r"line 4: event code 'x'"):
        kit.demo.validate_cast(synthetic_cast(early_exit))
    header_only = synthetic_cast([])
    with pytest.raises(kit.demo.DemoError, match=r"below 20s"):
        kit.demo.validate_cast(header_only)


def test_required_markers_must_appear_in_order(kit: ModuleType) -> None:
    base = synthetic_events()
    swapped = [list(e) for e in base]
    # Swap the fixed and bad replay command lines so the order is wrong.
    first = next(i for i, e in enumerate(swapped) if e[2] == COMMANDS[1] + "\r\n")
    second = next(i for i, e in enumerate(swapped) if e[2] == COMMANDS[2] + "\r\n")
    swapped[first][2], swapped[second][2] = swapped[second][2], swapped[first][2]
    # Every marker is still present, so only the ordered search can reject this:
    # after the (now later) fixed command, no further "exit 0" line follows.
    with pytest.raises(kit.demo.DemoError, match=r"lacks 'exit 0 \(expected 0\)' after"):
        kit.demo.validate_cast(synthetic_cast(swapped))
    assert kit.checks.check_cast(synthetic_cast(swapped), min_seconds=20, max_seconds=40) == []
    missing_summary = [e for e in base if e[2] != SUMMARY + "\r\n"]
    with pytest.raises(kit.demo.DemoError, match="lacks 'demo-session: all 3 commands"):
        kit.demo.validate_cast(synthetic_cast(missing_summary))
    wrong_exit = [
        [e[0], e[1], str(e[2]).replace("exit 1 (expected 1)", "exit 0 (expected 1)")] for e in base
    ]
    with pytest.raises(kit.demo.DemoError, match=r"lacks 'exit 1 \(expected 1\)'"):
        kit.demo.validate_cast(synthetic_cast(wrong_exit))


def test_credential_looking_output_is_rejected(kit: ModuleType) -> None:
    events = _with_event(synthetic_events(), 1, [0.0, "o", "Authorization: Bearer abc\r\n"])
    with pytest.raises(kit.demo.DemoError, match="credential pattern"):
        kit.demo.validate_cast(synthetic_cast(events))


def test_header_command_is_never_executed(kit: ModuleType, tmp_path: Path) -> None:
    marker = tmp_path / "executed"
    data = synthetic_cast().replace(
        b"/synthetic/python /synthetic/demo_session.py", f"touch {marker}".encode()
    )
    kit.demo.validate_cast(data)
    assert not marker.exists()
    text = (SRC_DIR / "actseal_assets" / "demo.py").read_text(encoding="utf-8")
    for forbidden in ("subprocess", "os.system", "shell=", "eval(", "exec("):
        assert forbidden not in text


# --- GIF measurement -------------------------------------------------------------


def test_measure_sums_frame_delays_not_header_fields(kit: ModuleType) -> None:
    facts = kit.demo.measure_gif(GOOD_GIF)
    assert (facts.frames, facts.delay_centiseconds) == (20, 2500)
    assert facts.seconds == 25.0
    assert facts.size == len(GOOD_GIF)
    huge_canvas = synthetic_gif((100,) * 3, width=1920, height=1080)
    assert kit.demo.measure_gif(huge_canvas).seconds == 3.0
    mixed = synthetic_gif((5, 300, 95), local_table=True, global_table=False, padding=600)
    measured = kit.demo.measure_gif(mixed)
    assert (measured.frames, measured.delay_centiseconds) == (3, 400)


@pytest.mark.parametrize(
    ("data", "match"),
    [
        (b"", "not a GIF file"),
        (b"GIF89a" + b"\x00" * 3, "not a GIF file"),
        (b"\x89PNG\r\n\x1a\n" + b"\x00" * 20, "not a GIF file"),
        (synthetic_gif((100,), trailer=False), "ends without a trailer"),
        (synthetic_gif((100,), trailing_junk=b"\x00"), "1 trailing byte"),
        (ONE_FRAME[:-6], "ends inside"),
        (ONE_FRAME.replace(b"\x21\xf9\x04", b"\x21\xf9\x05"), "malformed graphic control"),
        (ONE_FRAME.replace(b"\x2c", b"\x2d", 1), r"unexpected GIF block 0x2d"),
    ],
    ids=_short_id,
)
def test_malformed_gifs_are_rejected_not_estimated(
    kit: ModuleType, data: bytes, match: str
) -> None:
    with pytest.raises(kit.demo.DemoError, match=match):
        kit.demo.measure_gif(data)


@pytest.mark.parametrize(
    ("data", "match"),
    [
        (synthetic_gif(()), "has no image frames"),
        (synthetic_gif((100,) * 19), r"sum to 19\.00s, below 20s"),
        (synthetic_gif((100,) * 41), r"sum to 41\.00s, above 40s"),
        (synthetic_gif((0,) * 30), r"sum to 0\.00s, below 20s"),
        (synthetic_gif(GOOD_DELAYS, padding=3_000_000), "bytes is not below 3000000"),
        (ONE_FRAME.replace(b"\x21\xf9\x04", b"\x21\xf9\x05"), "malformed graphic control"),
    ],
    ids=_short_id,
)
def test_validate_gif_enforces_frames_duration_and_size(
    kit: ModuleType, data: bytes, match: str
) -> None:
    with pytest.raises(kit.demo.DemoError, match=rf"{LIGHT}: .*{match}"):
        kit.demo.validate_gif(data, LIGHT)


def test_validate_gif_accepts_the_window_edges(kit: ModuleType) -> None:
    assert kit.demo.validate_gif(synthetic_gif((100,) * 20), DARK).seconds == 20.0
    assert kit.demo.validate_gif(synthetic_gif((100,) * 40), DARK).seconds == 40.0
    nearly_full = synthetic_gif(GOOD_DELAYS, padding=2_980_000)
    assert len(nearly_full) < 3_000_000
    assert kit.demo.validate_gif(nearly_full, LIGHT).size == len(nearly_full)


# --- prerequisites fail before anything runs --------------------------------------


def test_missing_fonts_fail_before_agg_or_cast(
    kit: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    binaries = _binary_double(kit, monkeypatch, repo / "never")
    commands = _process_double(kit, monkeypatch)
    with pytest.raises(kit.tools.ToolError, match=r"pinned font file\(s\) missing") as missing:
        kit.demo.render(_context(kit, repo))
    assert "JetBrainsMono-Regular.ttf, JetBrainsMono-Bold.ttf" in str(missing.value)
    assert "No substitute font is used" in str(missing.value)
    assert binaries == []
    assert commands == []
    assert not (repo / "work").exists()


def test_missing_agg_fails_against_the_real_pin_and_empty_cache(
    kit: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _font_stand_ins(kit, repo)
    _write_cast(kit, repo)
    commands = _process_double(kit, monkeypatch)
    with pytest.raises(kit.tools.ToolError, match=r"agg 1\.9\.0") as missing:
        kit.demo.render(_context(kit, repo))
    assert "empty-tool-cache" in str(missing.value) or "no pinned artifact" in str(missing.value)
    assert commands == []
    assert not (repo / "work").exists()


def test_tampered_agg_is_refused_by_the_real_verifier(
    kit: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _font_stand_ins(kit, repo)
    _write_cast(kit, repo)
    commands = _process_double(kit, monkeypatch)
    manifest = kit.tools.load_manifest(repo / kit.inventory.MANIFEST_FILE)
    artifact = manifest["agg"].artifact_for(kit.tools.platform_key())
    if artifact is None:
        pytest.skip("no agg pin for this platform; verification fails earlier")
    cached = kit.tools.cached_binary_path(manifest["agg"], artifact)
    cached.parent.mkdir(parents=True)
    cached.write_bytes(b"not the pinned agg")
    with pytest.raises(kit.tools.ToolError, match="does not match pinned"):
        kit.demo.render(_context(kit, repo))
    assert commands == []


def test_unpinned_tools_are_errors(
    kit: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _font_stand_ins(kit, repo)
    monkeypatch.setattr(kit.demo, "AGG", "not-a-pinned-tool")
    with pytest.raises(kit.tools.ToolError, match="not-a-pinned-tool is not pinned in"):
        kit.demo.render(_context(kit, repo))
    monkeypatch.setattr(kit.demo, "FONT", "not-a-pinned-font")
    with pytest.raises(kit.tools.ToolError, match="not-a-pinned-font is not pinned in"):
        kit.demo.render(_context(kit, repo))


def test_missing_cast_fails_before_agg_runs(
    kit: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context, _, binaries, commands = _doubled(kit, repo, monkeypatch, cast=None)
    with pytest.raises(kit.demo.DemoError, match=r"raw recording .*demo\.cast is not present"):
        kit.demo.render(context)
    assert binaries == ["agg"]
    assert commands == []


def test_symlinked_cast_is_refused(
    kit: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    context, _, _, commands = _doubled(kit, repo, monkeypatch, cast=None)
    elsewhere = tmp_path / "elsewhere.cast"
    elsewhere.write_bytes(synthetic_cast())
    (repo / kit.inventory.SOURCE_DIR / "demo.cast").symlink_to(elsewhere)
    with pytest.raises(kit.demo.DemoError, match="is not present"):
        kit.demo.render(context)
    assert commands == []


def test_invalid_cast_fails_before_agg_runs(
    kit: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    short = synthetic_cast(synthetic_events(pause=1.0, hold=0.5))
    context, _, _, commands = _doubled(kit, repo, monkeypatch, cast=short)
    with pytest.raises(kit.demo.DemoError, match="below 20s"):
        kit.demo.render(context)
    assert commands == []
    assert not (repo / "work").exists()


# --- rendering through the doubles -------------------------------------------------


def test_render_produces_both_variants_from_one_cast(
    kit: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context, binary, binaries, commands = _doubled(kit, repo, monkeypatch)
    rendered = dict(kit.demo.render(context))
    assert tuple(rendered) == OUTPUTS
    assert rendered[LIGHT] == GOOD_GIF
    assert rendered[DARK] == GOOD_GIF
    assert binaries == ["agg"]
    assert len(commands) == 2
    cast = repo / kit.inventory.SOURCE_DIR / "demo.cast"
    duration = total_seconds(synthetic_events())
    for command, name in zip(commands, OUTPUTS, strict=True):
        expected = kit.tools.agg_command(
            binary,
            cast,
            context.work / name,
            duration_seconds=duration,
            font_dir=context.fonts,
            extra=("--last-frame-duration", "3", "--theme", kit.demo.THEMES[name]),
        )
        assert command == expected
        idle_limit = str(math.ceil(duration) + 1)
        assert command[:5] == [str(binary), "--speed", "1", "--idle-time-limit", idle_limit]
        assert float(command[4]) > duration
        assert command[command.index("--font-dir") + 1] == str(context.fonts)
        assert command[command.index("--font-family") + 1] == "JetBrains Mono"
        assert command[command.index("--last-frame-duration") + 1] == "3"
        assert command[command.index("--theme") + 1] == kit.demo.THEMES[name]
        assert "--select" not in command
        assert "--cols" not in command
        assert "--rows" not in command
        assert command[-2:] == [str(cast), str(context.work / name)]
    assert (context.work / LIGHT).read_bytes() == GOOD_GIF
    assert all("work" in path.parts for path in repo.rglob("*.gif"))


def test_render_is_deterministic_with_the_doubles(
    kit: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context, *_ = _doubled(kit, repo, monkeypatch)
    first = dict(kit.demo.render(context))
    second = dict(kit.demo.render(context))
    assert first == second
    asset = _temporary_asset(kit)
    _, problems = kit.pipeline._render_twice(asset, context)
    assert problems == []


def test_tool_failure_propagates_unchanged(
    kit: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    failure = kit.tools.ToolError("agg exited 1: transient double failure")
    context, *_ = _doubled(kit, repo, monkeypatch, fail=failure)
    with pytest.raises(kit.tools.ToolError) as raised:
        kit.demo.render(context)
    assert raised.value is failure
    assert not (context.work / LIGHT).exists()


def test_process_that_writes_nothing_is_an_error_even_with_a_stale_file(
    kit: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context, *_ = _doubled(kit, repo, monkeypatch, produce=None)
    stale = context.work / LIGHT
    stale.parent.mkdir(parents=True)
    stale.write_bytes(GOOD_GIF)
    with pytest.raises(kit.tools.ToolError, match=r"exited 0 but did not write .*demo-light\.gif"):
        kit.demo.render(context)
    assert not stale.exists()


def test_stale_symlink_target_is_not_accepted(
    kit: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    context, *_ = _doubled(kit, repo, monkeypatch, produce=None)
    context.work.mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere.gif"
    elsewhere.write_bytes(GOOD_GIF)
    (context.work / LIGHT).symlink_to(elsewhere)
    with pytest.raises(kit.tools.ToolError, match="did not write"):
        kit.demo.render(context)


@pytest.mark.parametrize(
    ("produce", "match"),
    [
        ({LIGHT: GOOD_GIF, DARK: synthetic_gif((100,) * 19)}, rf"{DARK}: .*19\.00s, below 20s"),
        ({LIGHT: synthetic_gif((100,) * 41), DARK: GOOD_GIF}, rf"{LIGHT}: .*41\.00s, above 40s"),
        ({LIGHT: GOOD_GIF, DARK: synthetic_gif(())}, rf"{DARK}: GIF has no image frames"),
        ({LIGHT: b"not a gif", DARK: GOOD_GIF}, rf"{LIGHT}: not a GIF file"),
        ({LIGHT: GOOD_GIF, DARK: synthetic_gif(GOOD_DELAYS, trailer=False)}, "without a trailer"),
        (
            {LIGHT: GOOD_GIF, DARK: synthetic_gif(GOOD_DELAYS, padding=3_000_000)},
            "bytes is not below 3000000",
        ),
    ],
    ids=_short_id,
)
def test_wrong_output_from_agg_is_an_error(
    kit: ModuleType,
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    produce: dict[str, bytes],
    match: str,
) -> None:
    context, *_ = _doubled(kit, repo, monkeypatch, produce=produce)
    with pytest.raises(kit.demo.DemoError, match=match):
        kit.demo.render(context)


# --- pipeline wiring with a temporary declaration ------------------------------------


def _temporary_asset(kit: ModuleType) -> Any:
    """What the inventory entry will look like once a genuine cast exists; test-only here."""
    outputs = tuple(
        make_output(kit, name, kind="gif", width=None, height=None, max_bytes=3_000_000)
        for name in OUTPUTS
    )
    source = kit.inventory.Source(path="demo.cast", kind="cast", min_seconds=20, max_seconds=40)
    return make_asset(
        kit,
        name="demo",
        outputs=outputs,
        sources=(source,),
        needs=("agg", "jetbrains-mono"),
        renderer=kit.demo.render,
        task="14",
    )


def _install_doubles(
    kit: ModuleType,
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    produce: bytes | dict[str, bytes] | None = GOOD_GIF,
) -> list[list[str]]:
    """Re-pin the manifest copy inside ``repo`` to the zero-byte font stand-ins.

    Unit doubles only; the repository's own ``tools.toml`` is untouched and a
    notice with the required markers is written beside the stand-ins.
    """
    _, _, _, commands = _doubled(kit, repo, monkeypatch, produce=produce)
    manifest = repo / kit.inventory.MANIFEST_FILE
    text = manifest.read_text(encoding="utf-8")
    fonts = repo / kit.inventory.FONT_DIR
    for name, pin in FONT_PINS.items():
        text = text.replace(pin, kit.tools.sha256_bytes((fonts / name).read_bytes()))
    manifest.write_text(text, encoding="utf-8")
    (fonts / "OFL.txt").write_text(
        "Copyright 2020 The JetBrains Mono Project Authors\n"
        "SIL OPEN FONT LICENSE Version 1.1 - 26 February 2007\n",
        encoding="utf-8",
    )
    return commands


def _errors(report: Any) -> list[str]:
    return [finding.message for finding in report.errors]


def test_write_then_check_round_trip_with_doubles(
    kit: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pipeline wiring only; the GIFs written here are synthetic fixtures inside tmp_path."""
    commands = _install_doubles(kit, repo, monkeypatch)
    asset = _temporary_asset(kit)
    written = kit.pipeline.run(repo, mode="write", only=("demo",), assets=(asset,))
    assert _errors(written) == []
    assert written.written == list(OUTPUTS)
    assert written.checked == ["demo"]
    assert len(commands) == 4  # two variants, rendered twice for the determinism check
    for name in OUTPUTS:
        assert (repo / "docs" / "assets" / name).read_bytes() == GOOD_GIF
    checked = kit.pipeline.run(repo, mode="check", only=("demo",), assets=(asset,))
    assert _errors(checked) == []
    assert checked.checked == ["demo"]
    messages = [f.message for f in checked.findings]
    assert "source docs/assets/src/demo.cast validated" in messages
    assert f"docs/assets/{LIGHT} matches regeneration ({len(GOOD_GIF)} bytes)" in messages
    assert f"docs/assets/{DARK} matches regeneration ({len(GOOD_GIF)} bytes)" in messages
    assert checked.lines()[-1] == "check: 1 asset(s) checked; 0 planned/not implemented; 0 error(s)"


def test_check_fails_on_missing_or_stale_committed_outputs(
    kit: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_doubles(kit, repo, monkeypatch)
    asset = _temporary_asset(kit)
    missing = kit.pipeline.run(repo, mode="check", only=("demo",), assets=(asset,))
    assert _errors(missing) == [
        f"docs/assets/{LIGHT} is not committed; run render.py --write",
        f"docs/assets/{DARK} is not committed; run render.py --write",
    ]
    assert missing.checked == ["demo"]
    (repo / "docs" / "assets").mkdir(parents=True, exist_ok=True)
    (repo / "docs" / "assets" / LIGHT).write_bytes(GOOD_GIF)
    (repo / "docs" / "assets" / DARK).write_bytes(synthetic_gif((100,) * 25))
    stale = kit.pipeline.run(repo, mode="check", only=("demo",), assets=(asset,))
    errors = _errors(stale)
    assert len(errors) == 1
    assert errors[0].startswith(f"docs/assets/{DARK} differs at byte ")


def test_pipeline_reports_cast_and_gif_failures_without_writing(
    kit: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commands = _install_doubles(kit, repo, monkeypatch, produce=synthetic_gif((100,) * 19))
    asset = _temporary_asset(kit)
    report = kit.pipeline.run(repo, mode="write", only=("demo",), assets=(asset,))
    assert _errors(report) == [
        f"render failed: {LIGHT}: encoded frame delays sum to 19.00s, below 20s"
    ]
    assert report.written == []
    assert len(commands) == 1
    _write_cast(kit, repo, synthetic_cast(rows=24))
    bad_cast = kit.pipeline.run(repo, mode="write", only=("demo",), assets=(asset,))
    assert _errors(bad_cast) == [
        "render failed: demo.cast: geometry 100x24; approved capture is 100x40"
    ]
    assert not any((repo / "docs" / "assets").glob("*.gif"))


def test_pipeline_blocks_demo_in_a_bootstrap_repository(kit: ModuleType, repo: Path) -> None:
    """The temporary declaration where neither the font, agg nor cast exists."""
    asset = _temporary_asset(kit)
    report = kit.pipeline.run(repo, mode="check", only=("demo",), assets=(asset,))
    errors = _errors(report)
    assert errors[0].startswith("requires agg 1.9.0: ")
    assert errors[1].startswith("requires jetbrains-mono 2.304; not fetched")
    assert errors[2] == "source docs/assets/src/demo.cast is not present"
    assert errors[3] == "skipped rendering because prerequisites failed"
    assert report.checked == []
    assert report.written == []
