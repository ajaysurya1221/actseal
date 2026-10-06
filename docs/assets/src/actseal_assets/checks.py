"""Content validators for committed assets.

SVG files are checked structurally (size, title/desc, element allowlist, no
scripts, styles, external resources or gradients, generic font stacks, label
size at display width). PNG and GIF files are checked by header. Asciicast
recordings are parsed for duration, geometry and credential-looking text.
"""

from __future__ import annotations

import json
import math
import re
import struct
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from .inventory import Output
from .svg import DESC_ID, SVG_NS, TITLE_ID

MIN_LABEL_PX = 14.0

ALLOWED_ELEMENTS = frozenset(
    {
        "svg",
        "title",
        "desc",
        "g",
        "rect",
        "path",
        "circle",
        "ellipse",
        "line",
        "polyline",
        "polygon",
        "text",
        "tspan",
        "defs",
        "clipPath",
        "marker",
        "symbol",
        "use",
    }
)
GENERIC_FAMILIES = frozenset(
    {"sans-serif", "serif", "monospace", "system-ui", "ui-monospace", "ui-sans-serif", "ui-serif"}
)
# Raw-text tokens that must never appear, including inside comments or
# processing instructions that the XML parser would otherwise discard.
FORBIDDEN_TOKENS = (
    "<!doctype",
    "<!entity",
    "<?xml-stylesheet",
    "<script",
    "<style",
    "@import",
    "@font-face",
    "url(",
    "javascript:",
)
EXTERNAL_PREFIXES = ("http:", "https:", "//", "data:", "file:", "ftp:")
# Checked on decoded attribute values and element text, so character
# references such as ``u&#114;l(`` cannot smuggle a resource reference past
# the raw-text scan above.
FORBIDDEN_VALUE_TOKENS = (
    "url(",
    "javascript:",
    "@import",
    "@font-face",
    "http:",
    "https:",
    "data:",
    "file:",
    "ftp:",
)
# Element text is prose; only CSS/script resource syntax is forbidden there.
FORBIDDEN_TEXT_TOKENS = ("url(", "javascript:", "@import", "@font-face")
XLINK_NS = "http://www.w3.org/1999/xlink"
_TRANSFORM = re.compile(r"\s*([A-Za-z]+)\s*\(([^()]*)\)\s*,?")
_TRANSFORM_SEPARATORS = re.compile(r"[\s,]+")

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
GIF_SIGNATURES = (b"GIF87a", b"GIF89a")
_PNG_IHDR_OFFSET = 12
_PNG_DIMENSION_OFFSET = 16
_PNG_HEADER_LENGTH = 24
_GIF_HEADER_LENGTH = 10
_CAST_EVENT_FIELDS = 3
_CAST_VERSIONS = frozenset({2, 3})

CREDENTIAL_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"authorization:\s*bearer",
        r"api[_-]?key\s*[=:]\s*\S",
        r"\bsk-[a-z0-9]{8,}",
        r"\bghp_[a-z0-9]{10,}",
        r"\bAKIA[0-9A-Z]{12,}",
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    )
)


class CastError(ValueError):
    """The recording is not a usable asciicast file."""


def _local(tag: str) -> tuple[str, str]:
    if tag.startswith("{"):
        namespace, _, name = tag[1:].partition("}")
        return namespace, name
    return "", tag


def _parse_px(value: str) -> float | None:
    """A finite, positive pixel length; anything else is ``None``."""
    text = value.strip().lower().removesuffix("px").strip()
    try:
        number = float(text)
    except ValueError:
        return None
    if not math.isfinite(number) or number <= 0:
        return None
    return number


def _squish(value: str) -> str:
    """Lower-case with all whitespace removed, for token matching."""
    return "".join(value.split()).lower()


def _forbidden_value_tokens(
    value: str, tokens: tuple[str, ...] = FORBIDDEN_VALUE_TOKENS
) -> list[str]:
    squished = _squish(value)
    return [token for token in tokens if token in squished]


def transform_scale(value: str) -> float | str:
    """Minimum linear scale applied by an SVG ``transform`` list.

    ``translate`` and ``rotate`` preserve lengths; ``scale`` and ``matrix`` are
    reduced to their smallest axis factor. Skews and anything unparsable return
    an error string so text size under them is never approximated.
    """
    position = 0
    factor = 1.0
    stripped = value.strip()
    while position < len(stripped):
        match = _TRANSFORM.match(stripped, position)
        if match is None:
            return f"unsupported transform syntax {stripped[position:]!r}"
        position = match.end()
        name = match.group(1)
        raw_args = [arg for arg in _TRANSFORM_SEPARATORS.split(match.group(2).strip()) if arg]
        try:
            args = [float(arg) for arg in raw_args]
        except ValueError:
            return f"non-numeric transform argument in {match.group(0).strip()!r}"
        if not all(math.isfinite(arg) for arg in args):
            return f"non-finite transform argument in {match.group(0).strip()!r}"
        if name == "translate" and len(args) in {1, 2}:
            continue
        if name == "rotate" and len(args) in {1, 3}:
            continue
        if name == "scale" and len(args) in {1, 2}:
            step = min(abs(arg) for arg in args)
        elif name == "matrix" and len(args) == 6:  # noqa: PLR2004 - matrix(a b c d e f)
            step = min(math.hypot(args[0], args[1]), math.hypot(args[2], args[3]))
        else:
            return f"unsupported transform {match.group(0).strip()!r}"
        if step <= 0:
            return f"degenerate transform {match.group(0).strip()!r}"
        factor *= step
    return factor


def check_svg(data: bytes, output: Output) -> list[str]:
    """Return problems with ``data`` as the committed SVG described by ``output``."""
    errors: list[str] = []
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return ["not valid UTF-8"]
    if "\r" in text:
        errors.append("contains carriage returns")
    if not text.endswith("\n"):
        errors.append("missing final newline")
    lowered = text.lower()
    errors.extend(f"forbidden token {token!r}" for token in FORBIDDEN_TOKENS if token in lowered)
    try:
        root = ET.fromstring(data)  # noqa: S314 - own committed files; DOCTYPE/ENTITY rejected above
    except ET.ParseError as exc:
        errors.append(f"not well-formed XML: {exc}")
        return errors
    errors.extend(_check_root(root, output))
    errors.extend(_check_tree(root, output))
    return errors


def _check_root(root: ET.Element, output: Output) -> list[str]:
    errors: list[str] = []
    namespace, name = _local(root.tag)
    if (namespace, name) != (SVG_NS, "svg"):
        return [f"root element is {root.tag!r}, expected SVG <svg>"]
    expected = {
        "width": str(output.width),
        "height": str(output.height),
        "viewBox": f"0 0 {output.width} {output.height}",
    }
    for key, value in expected.items():
        actual = root.get(key)
        if actual != value:
            errors.append(f"{key}={actual!r}, expected {value!r}")
    children = list(root)
    first = _local(children[0].tag)[1] if children else None
    second = _local(children[1].tag)[1] if len(children) > 1 else None
    if first != "title" or not (children[0].text or "").strip():
        errors.append("first child must be a non-empty <title>")
    elif children[0].get("id") != TITLE_ID:
        errors.append(f"<title> must carry id={TITLE_ID!r}")
    if second != "desc" or not (children[1].text or "").strip():
        errors.append("second child must be a non-empty <desc>")
    elif children[1].get("id") != DESC_ID:
        errors.append(f"<desc> must carry id={DESC_ID!r}")
    if root.get("role") != "img":
        errors.append('root must declare role="img"')
    return errors


@dataclass(frozen=True, slots=True)
class _Inherited:
    family: str | None
    size: float | None
    scale: float


def _check_tree(root: ET.Element, output: Output) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    display_scale = 1.0
    if output.display_width is not None and output.width:
        display_scale = min(1.0, output.display_width / output.width)
    stack: list[tuple[ET.Element, _Inherited]] = [(root, _Inherited(None, None, 1.0))]
    while stack:
        element, inherited = stack.pop()
        namespace, name = _local(element.tag)
        if namespace != SVG_NS or name not in ALLOWED_ELEMENTS:
            errors.append(f"forbidden element <{name}>")
            continue
        errors.extend(_check_attributes(element, name, seen_ids))
        errors.extend(_check_element_text(element, name))
        size, size_errors = _effective_size(element, name, inherited.size)
        errors.extend(size_errors)
        scale, scale_errors = _effective_scale(element, name, inherited.scale)
        errors.extend(scale_errors)
        current = _Inherited(element.get("font-family", inherited.family), size, scale)
        if name in {"text", "tspan"}:
            errors.extend(_check_text(element, name, current, output, display_scale))
        stack.extend((child, current) for child in reversed(list(element)))
    return errors


def _effective_size(
    element: ET.Element, name: str, inherited: float | None
) -> tuple[float | None, list[str]]:
    raw = element.get("font-size")
    if raw is None:
        return inherited, []
    parsed = _parse_px(raw)
    if parsed is None:
        return None, [f"<{name}> font-size {raw!r} is not a finite positive pixel size"]
    return parsed, []


def _effective_scale(element: ET.Element, name: str, inherited: float) -> tuple[float, list[str]]:
    raw = element.get("transform")
    if raw is None:
        return inherited, []
    result = transform_scale(raw)
    if isinstance(result, str):
        return inherited, [f"<{name}> transform: {result}"]
    return inherited * result, []


def _check_element_text(element: ET.Element, name: str) -> list[str]:
    """Decoded text and tail content must not carry resource syntax."""
    errors: list[str] = []
    for part in (element.text, element.tail):
        if not part:
            continue
        errors.extend(
            f"<{name}> text contains forbidden resource syntax {token!r}"
            for token in _forbidden_value_tokens(part, FORBIDDEN_TEXT_TOKENS)
        )
    return errors


def _check_attributes(element: ET.Element, name: str, seen_ids: set[str]) -> list[str]:
    errors: list[str] = []
    for raw_key, value in element.attrib.items():
        key_namespace, key = _local(raw_key)
        lowered = value.strip().lower()
        if key.lower().startswith("on"):
            errors.append(f"<{name}> carries event handler attribute {key!r}")
        if key == "style":
            errors.append(f"<{name}> uses a style attribute; use presentation attributes")
        if key == "href":
            if key_namespace not in {"", XLINK_NS}:
                errors.append(f"<{name}> href in unexpected namespace {key_namespace!r}")
            if not value.startswith("#"):
                errors.append(f"<{name}> href {value!r} is not a local fragment")
        if lowered.startswith(EXTERNAL_PREFIXES):
            errors.append(f"<{name}> attribute {key}={value!r} references an external resource")
        errors.extend(
            f"<{name}> attribute {key}={value!r} contains forbidden resource syntax {token!r}"
            for token in _forbidden_value_tokens(value)
        )
        if key == "id":
            if value in seen_ids:
                errors.append(f"duplicate id {value!r}")
            seen_ids.add(value)
    return errors


def _check_text(
    element: ET.Element,
    name: str,
    inherited: _Inherited,
    output: Output,
    scale: float,
) -> list[str]:
    content = (element.text or "").strip()
    if output.outlined:
        return [f"outlined asset contains <{name}> {content!r}; text must be converted to paths"]
    if not content:
        return []
    errors: list[str] = []
    if inherited.family is None:
        errors.append(f"<{name}> {content!r} has no font-family")
    else:
        last = inherited.family.split(",")[-1].strip().strip("'\"").lower()
        if last not in GENERIC_FAMILIES:
            errors.append(
                f"<{name}> {content!r} font stack {inherited.family!r} "
                "must end with a generic family"
            )
    if inherited.size is None:
        errors.append(f"<{name}> {content!r} has no finite positive font-size")
    else:
        rendered = inherited.size * inherited.scale * scale
        if not math.isfinite(rendered) or rendered < MIN_LABEL_PX:
            errors.append(
                f"<{name}> {content!r} renders at {rendered:.1f}px at display width "
                f"(transform scale {inherited.scale:g}); minimum is {MIN_LABEL_PX:g}px"
            )
    return errors


def png_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < _PNG_HEADER_LENGTH or not data.startswith(PNG_SIGNATURE):
        msg = "not a PNG file"
        raise ValueError(msg)
    if data[_PNG_IHDR_OFFSET:_PNG_DIMENSION_OFFSET] != b"IHDR":
        msg = "PNG without leading IHDR chunk"
        raise ValueError(msg)
    width, height = struct.unpack(">II", data[_PNG_DIMENSION_OFFSET:_PNG_HEADER_LENGTH])
    return int(width), int(height)


def gif_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < _GIF_HEADER_LENGTH or not data.startswith(GIF_SIGNATURES):
        msg = "not a GIF file"
        raise ValueError(msg)
    width, height = struct.unpack("<HH", data[6:_GIF_HEADER_LENGTH])
    return int(width), int(height)


def _check_raster(data: bytes, output: Output, dimensions: tuple[int, int]) -> list[str]:
    errors: list[str] = []
    width, height = dimensions
    expected = (output.width, output.height)
    if None not in expected and (width, height) != expected:
        errors.append(f"dimensions {width}x{height}, expected {output.width}x{output.height}")
    if output.max_bytes is not None and len(data) >= output.max_bytes:
        errors.append(f"size {len(data)} bytes is not below {output.max_bytes}")
    return errors


def check_png(data: bytes, output: Output) -> list[str]:
    try:
        dimensions = png_dimensions(data)
    except ValueError as exc:
        return [str(exc)]
    return _check_raster(data, output, dimensions)


def check_gif(data: bytes, output: Output) -> list[str]:
    try:
        dimensions = gif_dimensions(data)
    except ValueError as exc:
        return [str(exc)]
    return _check_raster(data, output, dimensions)


def check_output(data: bytes, output: Output) -> list[str]:
    """Dispatch on the declared kind."""
    if output.kind == "svg":
        return check_svg(data, output)
    if output.kind == "png":
        return check_png(data, output)
    if output.kind == "gif":
        return check_gif(data, output)
    return [f"unsupported output kind {output.kind!r}"]


@dataclass(frozen=True, slots=True)
class CastInfo:
    version: int
    width: int
    height: int
    duration: float
    events: int
    output: str


def parse_cast(data: bytes) -> CastInfo:
    """Parse an asciicast v2 (absolute times) or v3 (relative intervals) file."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        msg = "recording is not UTF-8"
        raise CastError(msg) from exc
    lines = [line for line in text.split("\n") if line.strip()]
    if not lines:
        msg = "recording is empty"
        raise CastError(msg)
    header = _load_json(lines[0], "header")
    if not isinstance(header, dict):
        msg = "header is not a JSON object"
        raise CastError(msg)
    version = header.get("version")
    if version not in _CAST_VERSIONS:
        msg = f"unsupported asciicast version {version!r}"
        raise CastError(msg)
    width, height = _cast_geometry(header, int(version))
    clock = 0.0
    output: list[str] = []
    for index, line in enumerate(lines[1:], start=2):
        event = _load_json(line, f"line {index}")
        if not isinstance(event, list) or len(event) != _CAST_EVENT_FIELDS:
            msg = f"line {index}: event is not a three-element list"
            raise CastError(msg)
        stamp, code, payload = event
        seconds = _cast_seconds(stamp, index)
        if version == 3:  # noqa: PLR2004 - v3 stores intervals
            clock += seconds
            if not math.isfinite(clock):
                msg = f"line {index}: accumulated time overflowed to {clock!r}"
                raise CastError(msg)
        else:
            if seconds < clock:
                msg = f"line {index}: timestamp {seconds!r} precedes previous {clock!r}"
                raise CastError(msg)
            clock = seconds
        if code == "o" and isinstance(payload, str):
            output.append(payload)
    return CastInfo(int(version), width, height, clock, len(lines) - 1, "".join(output))


def _cast_seconds(stamp: object, index: int) -> float:
    """A finite, non-negative event time; JSON NaN/Infinity and huge ints are rejected."""
    if isinstance(stamp, bool) or not isinstance(stamp, int | float):
        msg = f"line {index}: invalid timestamp {stamp!r}"
        raise CastError(msg)
    try:
        seconds = float(stamp)
    except OverflowError as exc:
        msg = f"line {index}: timestamp {stamp!r} cannot be represented"
        raise CastError(msg) from exc
    if not math.isfinite(seconds) or seconds < 0:
        msg = f"line {index}: invalid timestamp {stamp!r}"
        raise CastError(msg)
    return seconds


def _cast_geometry(header: dict[str, object], version: int) -> tuple[int, int]:
    if version == 3:  # noqa: PLR2004
        term = header.get("term")
        if not isinstance(term, dict):
            msg = "v3 header lacks a term object"
            raise CastError(msg)
        source: dict[str, object] = term
        keys = ("cols", "rows")
    else:
        source = header
        keys = ("width", "height")
    values: list[int] = []
    for key in keys:
        value = source.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            msg = f"header {key} is not a positive integer"
            raise CastError(msg)
        values.append(value)
    return values[0], values[1]


def _load_json(line: str, what: str) -> object:
    try:
        return json.loads(line)
    except json.JSONDecodeError as exc:
        msg = f"{what}: invalid JSON ({exc.msg})"
        raise CastError(msg) from exc


def check_cast(
    data: bytes,
    *,
    min_seconds: float | None,
    max_seconds: float | None,
    required_text: tuple[str, ...] = (),
) -> list[str]:
    """Problems with a raw recording: parse errors, duration, credentials, markers."""
    try:
        info = parse_cast(data)
    except CastError as exc:
        return [str(exc)]
    errors: list[str] = []
    if min_seconds is not None and info.duration < min_seconds:
        errors.append(f"duration {info.duration:.2f}s is below {min_seconds:g}s")
    if max_seconds is not None and info.duration > max_seconds:
        errors.append(f"duration {info.duration:.2f}s exceeds {max_seconds:g}s")
    errors.extend(
        f"output matches credential pattern {pattern.pattern!r}"
        for pattern in CREDENTIAL_PATTERNS
        if pattern.search(info.output)
    )
    errors.extend(
        f"recorded output lacks required text {needle!r}"
        for needle in required_text
        if needle not in info.output
    )
    return errors
