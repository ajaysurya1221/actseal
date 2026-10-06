"""Forbidden content, dimensions, fonts, raster headers and recordings."""

from __future__ import annotations

import json
from types import ModuleType

import pytest

from visual.visual_support import gif_bytes, make_output, png_bytes, probe_bytes, probe_document


def _render(kit: ModuleType, build: object = None) -> bytes:
    data: bytes = kit.svg.serialize_bytes(build or probe_document(kit))
    return data


def _joined(errors: list[str]) -> str:
    return "\n".join(errors)


def test_valid_figure_has_no_errors(kit: ModuleType) -> None:
    assert kit.checks.check_svg(probe_bytes(kit), make_output(kit)) == []


def test_wrong_dimensions_are_reported(kit: ModuleType) -> None:
    errors = kit.checks.check_svg(probe_bytes(kit, 1600, 401), make_output(kit))
    assert "height='401', expected '400'" in _joined(errors)
    assert "viewBox" in _joined(errors)


def test_script_element_is_forbidden(kit: ModuleType) -> None:
    root = probe_document(kit)
    root.add("script").text("alert(1)")
    errors = kit.checks.check_svg(_render(kit, root), make_output(kit))
    assert "forbidden token '<script'" in _joined(errors)
    assert "forbidden element <script>" in _joined(errors)


def test_style_element_attribute_and_handlers_are_forbidden(kit: ModuleType) -> None:
    root = probe_document(kit)
    root.add("style").text("text { fill: red }")
    root.add("rect", x=0, y=0, width=1, height=1, style="fill:red", onclick="x()")
    joined = _joined(kit.checks.check_svg(_render(kit, root), make_output(kit)))
    assert "forbidden element <style>" in joined
    assert "style attribute" in joined
    assert "event handler attribute 'onclick'" in joined


@pytest.mark.parametrize(
    "href",
    ["https://example.com/font.svg#g", "//cdn.example.com/x.svg", "data:image/svg+xml;base64,AA"],
)
def test_external_resources_are_forbidden(kit: ModuleType, href: str) -> None:
    root = probe_document(kit)
    root.add("use", href=href)
    joined = _joined(kit.checks.check_svg(_render(kit, root), make_output(kit)))
    assert "not a local fragment" in joined
    assert "references an external resource" in joined


def test_local_use_reference_is_allowed(kit: ModuleType) -> None:
    root = probe_document(kit)
    root.add("defs").add("rect", id="unit", width=1, height=1)
    root.add("use", href="#unit", x=5, y=5)
    assert kit.checks.check_svg(_render(kit, root), make_output(kit)) == []


def test_images_gradients_and_url_paint_are_forbidden(kit: ModuleType) -> None:
    root = probe_document(kit)
    root.add("defs").add("linearGradient", id="g")
    root.add("image", href="#x")
    root.add("rect", width=1, height=1, fill="url(#g)")
    joined = _joined(kit.checks.check_svg(_render(kit, root), make_output(kit)))
    assert "forbidden element <linearGradient>" in joined
    assert "forbidden element <image>" in joined
    assert "forbidden token 'url('" in joined


def test_raw_tokens_outside_the_tree_are_caught(kit: ModuleType) -> None:
    text = probe_bytes(kit).decode()
    with_pi = text.replace("<svg", '<?xml-stylesheet href="https://x/y.css"?>\n<svg', 1).encode()
    joined = _joined(kit.checks.check_svg(with_pi, make_output(kit)))
    assert "forbidden token '<?xml-stylesheet'" in joined
    with_doctype = text.replace("<svg", "<!DOCTYPE svg>\n<svg", 1).encode()
    assert "forbidden token '<!doctype'" in _joined(
        kit.checks.check_svg(with_doctype, make_output(kit))
    )


def test_missing_title_or_desc_is_reported(kit: ModuleType) -> None:
    text = probe_bytes(kit).decode()
    without_desc = text.replace('  <desc id="desc">A probe figure for tests.</desc>\n', "")
    joined = _joined(kit.checks.check_svg(without_desc.encode(), make_output(kit)))
    assert "second child must be a non-empty <desc>" in joined
    swapped = text.replace('<title id="title">', '<title id="t">')
    assert "<title> must carry id='title'" in _joined(
        kit.checks.check_svg(swapped.encode(), make_output(kit))
    )


def test_text_requires_generic_font_stack(kit: ModuleType) -> None:
    root = kit.svg.document(1600, 400, title="T", desc="D")
    root.add("text", x=0, y=50, font_size=30).text("no family")
    root.add("text", x=0, y=50, font_size=30, font_family="JetBrains Mono").text("brand only")
    root.add("text", x=0, y=50, font_size=30, font_family="'JetBrains Mono', monospace").text(
        "generic fallback"
    )
    joined = _joined(kit.checks.check_svg(_render(kit, root), make_output(kit)))
    assert "'no family' has no font-family" in joined
    assert "'brand only' font stack 'JetBrains Mono' must end with a generic family" in joined
    assert "generic fallback" not in joined


def test_label_size_is_checked_at_display_width(kit: ModuleType) -> None:
    root = kit.svg.document(1600, 400, title="T", desc="D")
    group = root.add("g", font_family="sans-serif")
    group.add("text", x=0, y=50, font_size=20).text("small")
    group.add("text", x=0, y=90, font_size=26).text("fine")
    group.add("text", x=0, y=90).text("unsized")
    joined = _joined(kit.checks.check_svg(_render(kit, root), make_output(kit)))
    assert "'small' renders at 11.0px at display width; minimum is 14px" in joined
    assert "'fine'" not in joined
    assert "'unsized' has no numeric font-size" in joined
    native = make_output(kit, display_width=None)
    assert kit.checks.check_svg(_render(kit, root), native) == [
        "<text> 'unsized' has no numeric font-size"
    ]


def test_outlined_assets_reject_text(kit: ModuleType) -> None:
    errors = kit.checks.check_svg(probe_bytes(kit), make_output(kit, outlined=True))
    assert errors == ["outlined asset contains <text> 'probe'; text must be converted to paths"]


def test_encoding_and_line_end_rules(kit: ModuleType) -> None:
    data = probe_bytes(kit)
    assert "contains carriage returns" in _joined(
        kit.checks.check_svg(data.replace(b"\n", b"\r\n"), make_output(kit))
    )
    assert "missing final newline" in _joined(
        kit.checks.check_svg(data.rstrip(b"\n"), make_output(kit))
    )
    assert kit.checks.check_svg(b"\xff\xfe<svg/>", make_output(kit)) == ["not valid UTF-8"]
    assert "not well-formed XML" in _joined(kit.checks.check_svg(b"<svg>\n", make_output(kit)))


def test_duplicate_ids_are_reported(kit: ModuleType) -> None:
    root = probe_document(kit)
    root.add("g", id="dup")
    root.add("g", id="dup")
    assert "duplicate id 'dup'" in _joined(
        kit.checks.check_svg(_render(kit, root), make_output(kit))
    )


def test_png_dimensions_and_signature(kit: ModuleType) -> None:
    output = make_output(kit, "social.png", kind="png", width=1280, height=640, display_width=None)
    assert kit.checks.check_png(png_bytes(1280, 640), output) == []
    assert kit.checks.check_png(png_bytes(1200, 630), output) == [
        "dimensions 1200x630, expected 1280x640"
    ]
    assert kit.checks.check_png(b"not a png", output) == ["not a PNG file"]


def test_gif_dimensions_and_size_limit(kit: ModuleType) -> None:
    output = make_output(
        kit, "demo.gif", kind="gif", width=None, height=None, display_width=None, max_bytes=64
    )
    assert kit.checks.check_gif(gif_bytes(800, 500), output) == []
    assert kit.checks.check_gif(gif_bytes(800, 500, padding=64), output) == [
        "size 78 bytes is not below 64"
    ]
    assert kit.checks.check_gif(b"GIF", output) == ["not a GIF file"]
    sized = make_output(kit, "demo.gif", kind="gif", width=800, height=500, display_width=None)
    assert kit.checks.check_gif(gif_bytes(640, 400), sized) == [
        "dimensions 640x400, expected 800x500"
    ]


def _cast_v2(*events: tuple[float, str]) -> bytes:
    header = {"version": 2, "width": 100, "height": 30}
    lines = [json.dumps(header)] + [json.dumps([time, "o", text]) for time, text in events]
    return ("\n".join(lines) + "\n").encode()


def _cast_v3(*events: tuple[float, str]) -> bytes:
    header = {"version": 3, "term": {"cols": 100, "rows": 30}}
    lines = [json.dumps(header)] + [json.dumps([gap, "o", text]) for gap, text in events]
    return ("\n".join(lines) + "\n").encode()


def test_cast_v2_uses_absolute_times(kit: ModuleType) -> None:
    info = kit.checks.parse_cast(_cast_v2((0.5, "$ a\n"), (25.0, "done\n")))
    assert (info.version, info.width, info.height) == (2, 100, 30)
    assert info.duration == 25.0
    assert info.output == "$ a\ndone\n"


def test_cast_v3_sums_relative_intervals(kit: ModuleType) -> None:
    info = kit.checks.parse_cast(_cast_v3((0.5, "$ a\n"), (10.0, "x"), (12.25, "done\n")))
    assert info.version == 3
    assert info.duration == 22.75


def test_cast_duration_bounds(kit: ModuleType) -> None:
    short = _cast_v2((5.0, "x"))
    assert kit.checks.check_cast(short, min_seconds=20, max_seconds=40) == [
        "duration 5.00s is below 20s"
    ]
    long = _cast_v2((41.0, "x"))
    assert kit.checks.check_cast(long, min_seconds=20, max_seconds=40) == [
        "duration 41.00s exceeds 40s"
    ]
    assert kit.checks.check_cast(_cast_v2((30.0, "x")), min_seconds=20, max_seconds=40) == []


def test_cast_credentials_and_required_text(kit: ModuleType) -> None:
    leaked = _cast_v2((1.0, "Authorization: Bearer abc\n"), (30.0, "sk-abcdefghijkl\n"))
    errors = kit.checks.check_cast(leaked, min_seconds=None, max_seconds=None)
    assert len(errors) == 2
    assert all("credential pattern" in error for error in errors)
    missing = kit.checks.check_cast(
        _cast_v2((30.0, "fixed: PASS\n")),
        min_seconds=None,
        max_seconds=None,
        required_text=("fixed: PASS", "bad: BLOCK"),
    )
    assert missing == ["recorded output lacks required text 'bad: BLOCK'"]


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (b"", "recording is empty"),
        (b"{\n", "header: invalid JSON"),
        (b'{"version": 1, "width": 1, "height": 1}\n', "unsupported asciicast version 1"),
        (b'{"version": 2, "width": 0, "height": 1}\n', "header width is not a positive integer"),
        (b'{"version": 3}\n', "v3 header lacks a term object"),
        (b'{"version": 2, "width": 1, "height": 1}\n[1, "o"]\n', "not a three-element list"),
        (b'{"version": 2, "width": 1, "height": 1}\n[-1, "o", "x"]\n', "invalid timestamp"),
    ],
)
def test_cast_parse_errors(kit: ModuleType, data: bytes, message: str) -> None:
    errors = kit.checks.check_cast(data, min_seconds=None, max_seconds=None)
    assert len(errors) == 1
    assert message in errors[0]


def test_check_output_dispatches_on_kind(kit: ModuleType) -> None:
    assert kit.checks.check_output(probe_bytes(kit), make_output(kit)) == []
    assert kit.checks.check_output(b"", make_output(kit, "x.bmp", kind="bmp")) == [
        "unsupported output kind 'bmp'"
    ]
