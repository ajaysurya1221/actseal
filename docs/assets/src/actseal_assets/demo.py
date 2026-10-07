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
GIF is read up to the byte cap and walked block by block with bounded reads;
its duration is the sum of the frame delays that are actually shown, that is
one graphic control extension per following image, never a header field, a
configured flag or a dangling control. It must fall inside the same 20 to 40
second window with at least one frame and strictly fewer than 3,000,000
bytes. The walk validates structure (headers, colour tables, descriptors,
code sizes, non-empty image data, terminators, trailer); it does not decode
LZW pixels, so a rendered review of the real GIF remains a separate step.

The header's ``command`` field is read as data only; nothing here executes it
or anything else named by the recording. The command and exit markers are
consistency checks on the recorded text; they cannot prove that the commands
ran or that the package came from PyPI. That binding is the separate
post-publication receipt in ``recording.md``. No asset is created by importing
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
#: The recorder captured exactly these names (recording.md steps 1, 2 and 6).
HEADER_ENV_KEYS: frozenset[str] = frozenset({"TERM", "LANG"})

_GIF_SIGNATURES = (b"GIF87a", b"GIF89a")
_GIF_TRAILER = 0x3B
_GIF_EXTENSION = 0x21
_GIF_IMAGE = 0x2C
_GIF_GRAPHIC_CONTROL = 0xF9
_GIF_GCE_LENGTH = 4
_GIF_HEADER_LENGTH = 13
_GIF_IMAGE_DESCRIPTOR_LENGTH = 9
_GIF_MIN_CODE_SIZE = 2
_GIF_MAX_CODE_SIZE = 8
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


def _lines(data: bytes) -> list[str]:
    return [line for line in data.decode("utf-8").split("\n") if line.strip()]


def _header(lines: list[str]) -> dict[str, object]:
    header = json.loads(lines[0])
    if not isinstance(header, dict):
        msg = "header is not a JSON object"
        raise DemoError(msg)
    return header


def _events(lines: list[str]) -> list[list[object]]:
    """Every event line after the header as a parsed three-element list."""
    events: list[list[object]] = []
    for index, line in enumerate(lines[1:], start=2):
        event = json.loads(line)
        if not isinstance(event, list) or len(event) != _EVENT_FIELDS:
            msg = f"line {index}: event is not a three-element list"
            raise DemoError(msg)
        events.append(event)
    return events


def _require_header_env(header: dict[str, object]) -> None:
    """The captured environment must be exactly the procedure's two names."""
    env = header.get("env")
    if not isinstance(env, dict):
        msg = "header lacks an env object; the capture passes --capture-env TERM,LANG"
        raise DemoError(msg)
    keys = set(env)
    if keys != HEADER_ENV_KEYS or not all(isinstance(value, str) for value in env.values()):
        msg = (
            f"header env keys {sorted(keys)}; the approved capture records exactly "
            f"{sorted(HEADER_ENV_KEYS)} with string values"
        )
        raise DemoError(msg)


def _require_in_order(output: str, needles: tuple[str, ...]) -> None:
    position = 0
    for needle in needles:
        found = output.find(needle, position)
        if found < 0:
            msg = f"recorded output lacks {needle!r} after the preceding required text"
            raise DemoError(msg)
        position = found + len(needle)


def validate_cast(data: bytes) -> CastFacts:
    """Accept only a recording whose structure matches the approved procedure.

    ``checks.check_cast`` supplies the parse, duration window and credential
    scan. This adds the procedure's stricter rules: asciicast v3 at the
    approved geometry; a header ``env`` with exactly ``TERM`` and ``LANG``;
    every event is an output event with a string payload except exactly one
    final exit event whose payload is the string ``"0"``; and the approved
    command and exit markers appear in order. The header is data; its
    ``command`` is never executed. Passing here is structural consistency,
    not proof of execution or of PyPI provenance.
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
    try:
        lines = _lines(data)
        _require_header_env(_header(lines))
        events = _events(lines)
    except DemoError as exc:
        msg = f"{CAST_SOURCE}: {exc}"
        raise DemoError(msg) from exc
    if not events:
        msg = f"{CAST_SOURCE}: recording has no events"
        raise DemoError(msg)
    for index, event in enumerate(events[:-1], start=2):
        code, payload = event[1], event[2]
        if code != OUTPUT_EVENT:
            msg = (
                f"{CAST_SOURCE}: line {index}: event code {code!r}; only output events "
                "may precede the final exit event"
            )
            raise DemoError(msg)
        if not isinstance(payload, str):
            msg = f"{CAST_SOURCE}: line {index}: output payload is not a string"
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


class _Reader:
    """Bounded cursor over GIF bytes; every read past the end is a DemoError."""

    __slots__ = ("data", "position")

    def __init__(self, data: bytes) -> None:
        self.data = data
        self.position = 0

    def take(self, count: int, what: str) -> bytes:
        end = self.position + count
        if end > len(self.data):
            msg = f"GIF ends inside {what} at byte {self.position}"
            raise DemoError(msg)
        chunk = self.data[self.position : end]
        self.position = end
        return chunk

    def byte(self, what: str) -> int:
        return self.take(1, what)[0]

    def skip_colour_table(self, flags: int, what: str) -> None:
        if flags & 0x80:
            self.take(3 * (2 << (flags & 7)), f"the {what} colour table")

    def skip_sub_blocks(self, what: str) -> int:
        """Consume sub-blocks through the terminator; return the payload byte count."""
        total = 0
        while True:
            length = self.byte(f"{what} sub-block length")
            if length == 0:
                return total
            self.take(length, f"a {what} sub-block")
            total += length

    @property
    def exhausted(self) -> bool:
        return self.position == len(self.data)


def _graphic_control(reader: _Reader) -> int:
    """A fixed graphic control extension: size 4, four bytes, terminator; returns the delay."""
    at = reader.position - 2
    size = reader.byte("a graphic control extension")
    if size != _GIF_GCE_LENGTH:
        msg = f"malformed graphic control extension at byte {at}: block size {size}"
        raise DemoError(msg)
    body = reader.take(_GIF_GCE_LENGTH, "a graphic control extension")
    terminator = reader.byte("a graphic control extension terminator")
    if terminator != 0:
        msg = f"malformed graphic control extension at byte {at}: no terminator"
        raise DemoError(msg)
    return int.from_bytes(body[1:3], "little")


def _image(reader: _Reader) -> None:
    """One image descriptor, optional local table, code size and non-empty data."""
    at = reader.position - 1
    descriptor = reader.take(_GIF_IMAGE_DESCRIPTOR_LENGTH, "an image descriptor")
    width = int.from_bytes(descriptor[4:6], "little")
    height = int.from_bytes(descriptor[6:8], "little")
    if width == 0 or height == 0:
        msg = f"image at byte {at} has zero size {width}x{height}"
        raise DemoError(msg)
    reader.skip_colour_table(descriptor[8], "local")
    code_size = reader.byte("an LZW minimum code size")
    if not _GIF_MIN_CODE_SIZE <= code_size <= _GIF_MAX_CODE_SIZE:
        msg = f"image at byte {at} has LZW minimum code size {code_size}; expected 2 to 8"
        raise DemoError(msg)
    if reader.skip_sub_blocks("image data") == 0:
        msg = f"image at byte {at} has no image data"
        raise DemoError(msg)


def measure_gif(data: bytes) -> GifFacts:
    """Walk every block to the trailer and sum the delays of displayed frames.

    Structure only: signature, logical screen descriptor, colour tables,
    extensions, image descriptors, code sizes, sub-blocks, terminators and
    the trailer are all bounded and validated; LZW pixels are not decoded.
    Exactly one graphic control extension may precede an image; its delay
    counts for that image alone. A duplicate or dangling control, an image
    without data, an unknown block, truncation or trailing bytes is rejected
    rather than estimated. The logical screen size is never used as duration.
    """
    if len(data) > MAX_BYTES:
        msg = f"{len(data)} bytes is not below {MAX_BYTES}; not parsed"
        raise DemoError(msg)
    if data[:6] not in _GIF_SIGNATURES:
        msg = "not a GIF file"
        raise DemoError(msg)
    reader = _Reader(data)
    header = reader.take(_GIF_HEADER_LENGTH, "the header")
    reader.skip_colour_table(header[10], "global")
    frames = 0
    delay = 0
    pending: int | None = None
    while True:
        block = reader.byte("the block stream")
        if block == _GIF_TRAILER:
            break
        if block == _GIF_EXTENSION:
            label = reader.byte("an extension introducer")
            if label == _GIF_GRAPHIC_CONTROL:
                if pending is not None:
                    msg = f"duplicate graphic control extension at byte {reader.position - 2}"
                    raise DemoError(msg)
                pending = _graphic_control(reader)
            else:
                reader.skip_sub_blocks("extension")
        elif block == _GIF_IMAGE:
            _image(reader)
            frames += 1
            delay += pending or 0
            pending = None
        else:
            msg = f"unexpected GIF block 0x{block:02x} at byte {reader.position - 1}"
            raise DemoError(msg)
    if pending is not None:
        msg = "dangling graphic control extension with no following image"
        raise DemoError(msg)
    if not reader.exhausted:
        msg = f"{len(data) - reader.position} trailing byte(s) after the GIF trailer"
        raise DemoError(msg)
    return GifFacts(size=len(data), frames=frames, delay_centiseconds=delay)


def read_bounded(path: Path) -> bytes:
    """Read at most the cap plus one byte, so an oversized file is refused unread."""
    with path.open("rb") as handle:
        data = handle.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        msg = f"{path.name}: at least {len(data)} bytes is not below {MAX_BYTES}; not parsed"
        raise DemoError(msg)
    return data


def validate_gif(data: bytes, name: str) -> GifFacts:
    """Size cap first, then structure, then at least one frame inside the window."""
    if len(data) >= MAX_BYTES:
        msg = f"{name}: {len(data)} bytes is not below {MAX_BYTES}"
        raise DemoError(msg)
    try:
        facts = measure_gif(data)
    except DemoError as exc:
        msg = f"{name}: {exc}"
        raise DemoError(msg) from exc
    if facts.frames < 1:
        msg = f"{name}: GIF has no image frames"
        raise DemoError(msg)
    if not math.isfinite(facts.seconds) or facts.seconds < MIN_SECONDS:
        msg = f"{name}: displayed frame delays sum to {facts.seconds:.2f}s, below {MIN_SECONDS:g}s"
        raise DemoError(msg)
    if facts.seconds > MAX_SECONDS:
        msg = f"{name}: displayed frame delays sum to {facts.seconds:.2f}s, above {MAX_SECONDS:g}s"
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
    cast: Path,
    facts: CastFacts,
    context: RenderContext,
    name: str,
) -> bytes:
    """Render one GIF into ``context.work`` and validate the bytes that run produced.

    The pinned agg binary is re-hashed immediately before this execution, so
    a cache changed between variants is refused rather than run.
    """
    from . import tools  # noqa: PLC0415 - circular with inventory; see module docstring

    context.work.mkdir(parents=True, exist_ok=True)
    target = context.work / name
    # A stale file from an earlier run must never be mistaken for this run's output.
    target.unlink(missing_ok=True)
    agg = require_agg(context)
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
    data = read_bounded(target)
    validate_gif(data, name)
    return data


def render(context: RenderContext) -> Mapping[str, bytes]:
    """Both GIF variants from the committed cast, or fail before agg runs.

    agg is verified once here so a missing or tampered cache fails before
    the cast is parsed, and again inside each variant immediately before it
    executes.
    """
    require_fonts(context)
    require_agg(context)
    cast = cast_path(context)
    facts = validate_cast(cast.read_bytes())
    return {name: render_variant(cast, facts, context, name) for name in THEMES}
