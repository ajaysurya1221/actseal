"""Demo GIF renderer: light and dark GIFs from the committed raw recording.

The only input is ``docs/assets/src/demo.cast``, the untouched asciicast v3
file captured under ``docs/assets/src/recording.md`` after the public PyPI
1.0.0 release. This module validates that recording exactly as the procedure
does (v3, the approved 100x40 geometry, 20 to 40 seconds, output events plus
exactly one final ``x`` event with payload ``"0"``, no input, resize or marker
events, the three approved commands and their exit markers in order, no
credential-looking output) and then renders ``demo-light.gif`` and
``demo-dark.gif`` with the pinned agg binary through the reviewed
``tools.agg_command`` (speed 1, idle limit beyond the whole cast, pinned
JetBrains Mono, explicit last-frame duration, one theme per variant). Each
GIF is parsed block by block; its duration is the sum of the encoded frame
delays, never a header field or a configured flag, and must fall inside the
same 20 to 40 second window with at least one frame and strictly fewer than
3,000,000 bytes.

The header's ``command`` field is read as data only; nothing here executes it
or anything else named by the recording. No asset is created by importing
this module: the inventory registers the renderer only once a genuine capture
exists, and until then ``render.py --check`` keeps reporting the demo as
planned. ``tools`` is imported lazily for the same reason as in ``social``:
``inventory`` will import this module, and ``tools`` imports ``inventory``.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from . import checks

if TYPE_CHECKING:
    from .inventory import RenderContext

CAST_SOURCE = "demo.cast"
LIGHT_OUTPUT = "demo-light.gif"
DARK_OUTPUT = "demo-dark.gif"
#: Frozen outputs and the agg theme that renders each; both come from one cast.
THEMES: Mapping[str, str] = {LIGHT_OUTPUT: "github-light", DARK_OUTPUT: "github-dark"}
AGG = "agg"
FONT = "jetbrains-mono"
LAST_FRAME_SECONDS = "3"

# Same values as inventory.DEMO_* because inventory will import this module.
MIN_SECONDS = 20.0
MAX_SECONDS = 40.0
MAX_BYTES = 3_000_000
# Approved capture geometry from recording.md step 4.
COLS = 100
ROWS = 40
CAST_VERSION = 3

#: Recorded output must contain these texts in this order: the helper's printed
#: command lines and exit markers from ``demo_session.py``.
REQUIRED_OUTPUT: tuple[str, ...] = (
    "$ uvx --python 3.12 actseal demo --out ./actseal-demo",
    "exit 0 (expected 0)",
    "$ uvx --offline --python 3.12 actseal replay ./actseal-demo/fixed/evidence",
    "exit 0 (expected 0)",
    "$ uvx --offline --python 3.12 actseal replay ./actseal-demo/bad/evidence",
    "exit 1 (expected 1)",
    "demo-session: all 3 commands exited as expected (0, 0, 1)",
)
OUTPUT_EVENT = "o"
EXIT_EVENT = "x"
EXIT_PAYLOAD = "0"

_GIF_TRAILER = 0x3B
_GIF_EXTENSION = 0x21
_GIF_IMAGE = 0x2C
_GIF_GRAPHIC_CONTROL = 0xF9
_GIF_GCE_LENGTH = 4
_GIF_HEADER_LENGTH = 13
_GIF_IMAGE_DESCRIPTOR_LENGTH = 9
_EVENT_FIELDS = 3


class DemoError(ValueError):
    """The recording or a rendered GIF does not meet the demo contract."""


@dataclass(frozen=True, slots=True)
class CastFacts:
    """What the renderer established about the raw recording."""

    duration: float
    outputs: int


@dataclass(frozen=True, slots=True)
class GifFacts:
    """Measured from the encoded blocks, never from the header."""

    size: int
    frames: int
    delay_centiseconds: int

    @property
    def seconds(self) -> float:
        return self.delay_centiseconds / 100


# --- prerequisites -------------------------------------------------------------


def require_fonts(context: RenderContext) -> None:
    """Every pinned font file must be present; the global check verifies their hashes."""
    from . import tools  # noqa: PLC0415 - circular with inventory; see module docstring

    manifest = tools.load_manifest(tools.default_manifest_path(context.root))
    tool = manifest.get(FONT)
    if tool is None:
        msg = f"{FONT} is not pinned in {tools.default_manifest_path(context.root)}"
        raise tools.ToolError(msg)
    # The hash-pinned font files, as the hero requires; the upstream notice is
    # receipt-verified and enforced by the pipeline's global font check.
    pinned = [artifact.filename for artifact in tool.artifacts if artifact.verify == "sha256"]
    missing = [name for name in pinned if not (context.fonts / name).is_file()]
    if missing:
        msg = (
            f"pinned font file(s) missing from {context.fonts}: {', '.join(missing)}; "
            f"run setup_tools.py --tool {FONT}. No substitute font is used."
        )
        raise tools.ToolError(msg)


def require_agg(context: RenderContext) -> Path:
    """The pinned agg binary must be cached and re-verified; nothing else renders."""
    from . import tools  # noqa: PLC0415 - circular with inventory; see module docstring

    manifest_path = tools.default_manifest_path(context.root)
    tool = tools.load_manifest(manifest_path).get(AGG)
    if tool is None:
        msg = f"{AGG} is not pinned in {manifest_path}"
        raise tools.ToolError(msg)
    return tools.verified_binary(context.root, tool)


def cast_path(context: RenderContext) -> Path:
    path = context.src / CAST_SOURCE
    if path.is_symlink() or not path.is_file():
        msg = f"raw recording {path} is not present; capture it under recording.md first"
        raise DemoError(msg)
    return path


# --- raw cast validation -------------------------------------------------------


def _events(data: bytes) -> list[list[object]]:
    """Every event line after the header as a parsed three-element list."""
    lines = [line for line in data.decode("utf-8").split("\n") if line.strip()]
    events: list[list[object]] = []
    for index, line in enumerate(lines[1:], start=2):
        event = json.loads(line)
        if not isinstance(event, list) or len(event) != _EVENT_FIELDS:
            msg = f"line {index}: event is not a three-element list"
            raise DemoError(msg)
        events.append(event)
    return events


def _require_in_order(output: str, needles: tuple[str, ...]) -> None:
    position = 0
    for needle in needles:
        found = output.find(needle, position)
        if found < 0:
            msg = f"recorded output lacks {needle!r} after the preceding required text"
            raise DemoError(msg)
        position = found + len(needle)


def validate_cast(data: bytes) -> CastFacts:
    """Accept only a recording captured under the approved procedure.

    ``checks.check_cast`` supplies the parse, duration window and credential
    scan. This adds the procedure's stricter rules: asciicast v3 at the
    approved geometry; every event is output except exactly one final exit
    event whose payload is the string ``"0"``; and the approved command and
    exit markers appear in order. The header is data; its ``command`` is
    never executed.
    """
    problems = checks.check_cast(data, min_seconds=MIN_SECONDS, max_seconds=MAX_SECONDS)
    if problems:
        msg = f"{CAST_SOURCE}: " + "; ".join(problems)
        raise DemoError(msg)
    info = checks.parse_cast(data)
    if info.version != CAST_VERSION:
        msg = f"{CAST_SOURCE}: asciicast v{info.version}; the procedure records v{CAST_VERSION}"
        raise DemoError(msg)
    if (info.width, info.height) != (COLS, ROWS):
        msg = (
            f"{CAST_SOURCE}: geometry {info.width}x{info.height}; approved capture is {COLS}x{ROWS}"
        )
        raise DemoError(msg)
    events = _events(data)
    if not events:
        msg = f"{CAST_SOURCE}: recording has no events"
        raise DemoError(msg)
    codes = [event[1] for event in events]
    for index, code in enumerate(codes[:-1], start=2):
        if code != OUTPUT_EVENT:
            msg = (
                f"{CAST_SOURCE}: line {index}: event code {code!r}; only output events "
                "may precede the final exit event"
            )
            raise DemoError(msg)
    last_code, last_payload = events[-1][1], events[-1][2]
    if last_code != EXIT_EVENT:
        msg = (
            f"{CAST_SOURCE}: last event code {last_code!r}; expected a single final "
            f"{EXIT_EVENT!r} exit event"
        )
        raise DemoError(msg)
    if last_payload != EXIT_PAYLOAD:
        msg = f"{CAST_SOURCE}: exit event payload {last_payload!r}; the helper must have exited 0"
        raise DemoError(msg)
    _require_in_order(info.output, REQUIRED_OUTPUT)
    return CastFacts(duration=info.duration, outputs=len(events) - 1)


# --- rendered GIF measurement --------------------------------------------------


def _skip_sub_blocks(data: bytes, position: int) -> int:
    while True:
        if position >= len(data):
            msg = "GIF ends inside a data sub-block sequence"
            raise DemoError(msg)
        length = data[position]
        position += 1
        if length == 0:
            return position
        position += length


def measure_gif(data: bytes) -> GifFacts:
    """Walk every block to the trailer and sum the encoded frame delays.

    The header's logical screen size is irrelevant to duration and is not
    used. A file that ends before its trailer, carries an unknown block or a
    malformed graphic control extension is rejected rather than estimated.
    """
    try:
        checks.gif_dimensions(data)
    except ValueError as exc:
        raise DemoError(str(exc)) from exc
    position = _GIF_HEADER_LENGTH
    flags = data[10]
    if flags & 0x80:
        position += 3 * (2 << (flags & 7))
    frames = 0
    delay = 0
    while True:
        if position >= len(data):
            msg = "GIF ends without a trailer"
            raise DemoError(msg)
        block = data[position]
        position += 1
        if block == _GIF_TRAILER:
            break
        if block == _GIF_EXTENSION:
            if position >= len(data):
                msg = "GIF ends inside an extension introducer"
                raise DemoError(msg)
            label = data[position]
            position += 1
            if label == _GIF_GRAPHIC_CONTROL:
                if position + 1 + _GIF_GCE_LENGTH > len(data) or data[position] != _GIF_GCE_LENGTH:
                    msg = f"malformed graphic control extension at byte {position - 2}"
                    raise DemoError(msg)
                delay += int.from_bytes(data[position + 2 : position + 4], "little")
            position = _skip_sub_blocks(data, position)
        elif block == _GIF_IMAGE:
            if position + _GIF_IMAGE_DESCRIPTOR_LENGTH > len(data):
                msg = "GIF ends inside an image descriptor"
                raise DemoError(msg)
            local = data[position + 8]
            position += _GIF_IMAGE_DESCRIPTOR_LENGTH
            if local & 0x80:
                position += 3 * (2 << (local & 7))
            position += 1  # LZW minimum code size
            position = _skip_sub_blocks(data, position)
            frames += 1
        else:
            msg = f"unexpected GIF block 0x{block:02x} at byte {position - 1}"
            raise DemoError(msg)
    if position != len(data):
        msg = f"{len(data) - position} trailing byte(s) after the GIF trailer"
        raise DemoError(msg)
    return GifFacts(size=len(data), frames=frames, delay_centiseconds=delay)


def validate_gif(data: bytes, name: str) -> GifFacts:
    """Measured duration inside the demo window, at least one frame, under the size cap."""
    try:
        facts = measure_gif(data)
    except DemoError as exc:
        msg = f"{name}: {exc}"
        raise DemoError(msg) from exc
    if facts.frames < 1:
        msg = f"{name}: GIF has no image frames"
        raise DemoError(msg)
    if facts.size >= MAX_BYTES:
        msg = f"{name}: {facts.size} bytes is not below {MAX_BYTES}"
        raise DemoError(msg)
    if not math.isfinite(facts.seconds) or facts.seconds < MIN_SECONDS:
        msg = f"{name}: encoded frame delays sum to {facts.seconds:.2f}s, below {MIN_SECONDS:g}s"
        raise DemoError(msg)
    if facts.seconds > MAX_SECONDS:
        msg = f"{name}: encoded frame delays sum to {facts.seconds:.2f}s, above {MAX_SECONDS:g}s"
        raise DemoError(msg)
    return facts


# --- rendering ------------------------------------------------------------------


def agg_arguments(
    agg: Path, cast: Path, gif: Path, *, duration_seconds: float, font_dir: Path, theme: str
) -> list[str]:
    """The reviewed agg invocation plus the explicit last-frame hold and one theme."""
    from . import tools  # noqa: PLC0415 - circular with inventory; see module docstring

    return tools.agg_command(
        agg,
        cast,
        gif,
        duration_seconds=duration_seconds,
        font_dir=font_dir,
        extra=("--last-frame-duration", LAST_FRAME_SECONDS, "--theme", theme),
    )


def render_variant(
    agg: Path,
    cast: Path,
    facts: CastFacts,
    context: RenderContext,
    name: str,
) -> bytes:
    """Render one GIF into ``context.work`` and validate the bytes that run produced."""
    from . import tools  # noqa: PLC0415 - circular with inventory; see module docstring

    context.work.mkdir(parents=True, exist_ok=True)
    target = context.work / name
    # A stale file from an earlier run must never be mistaken for this run's output.
    target.unlink(missing_ok=True)
    command = agg_arguments(
        agg,
        cast,
        target,
        duration_seconds=facts.duration,
        font_dir=context.fonts,
        theme=THEMES[name],
    )
    tools.run_tool(command)
    if target.is_symlink() or not target.is_file():
        msg = f"{agg} exited 0 but did not write {target}"
        raise tools.ToolError(msg)
    data = target.read_bytes()
    validate_gif(data, name)
    return data


def render(context: RenderContext) -> Mapping[str, bytes]:
    """Both GIF variants from the committed cast, or fail before agg runs."""
    require_fonts(context)
    agg = require_agg(context)
    cast = cast_path(context)
    facts = validate_cast(cast.read_bytes())
    return {name: render_variant(agg, cast, facts, context, name) for name in THEMES}
