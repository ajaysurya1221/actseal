"""Deterministic SVG serialization."""

from __future__ import annotations

from types import ModuleType

import pytest

from visual.visual_support import make_output, probe_bytes, probe_document


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1, "1"),
        (1.0, "1"),
        (0.1234, "0.123"),
        (-0.0001, "0"),
        (12.5, "12.5"),
        ("auto", "auto"),
        (1599.9996, "1600"),
    ],
)
def test_fmt_is_canonical(kit: ModuleType, value: float | str, expected: str) -> None:
    assert kit.svg.fmt(value) == expected


def test_fmt_rejects_booleans_and_non_finite(kit: ModuleType) -> None:
    with pytest.raises(TypeError, match="boolean"):
        kit.svg.fmt(True)
    with pytest.raises(ValueError, match="non-finite"):
        kit.svg.fmt(float("inf"))


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("font_size", "font-size"),
        ("class_", "class"),
        ("xlink__href", "xlink:href"),
        ("viewBox", "viewBox"),
        ("aria_labelledby", "aria-labelledby"),
    ],
)
def test_attribute_names(kit: ModuleType, key: str, expected: str) -> None:
    assert kit.svg.attr_name(key) == expected


def test_serialization_is_byte_identical_across_runs(kit: ModuleType) -> None:
    assert probe_bytes(kit) == probe_bytes(kit)


def test_attribute_order_does_not_change_output(kit: ModuleType) -> None:
    first = kit.svg.Node("rect", x=1, y=2, width=3, height=4)
    second = kit.svg.Node("rect", height=4, width=3, y=2, x=1)
    assert kit.svg.serialize(first) == kit.svg.serialize(second)
    assert kit.svg.serialize(first).splitlines()[1] == '<rect height="4" width="3" x="1" y="2"/>'


def test_document_has_title_desc_and_viewbox(kit: ModuleType) -> None:
    text = kit.svg.serialize(probe_document(kit))
    lines = text.split("\n")
    assert lines[0] == '<?xml version="1.0" encoding="UTF-8"?>'
    assert 'viewBox="0 0 1600 400"' in lines[1]
    assert 'role="img"' in lines[1]
    assert 'aria-labelledby="title desc"' in lines[1]
    assert lines[2] == '  <title id="title">Probe</title>'
    assert lines[3] == '  <desc id="desc">A probe figure for tests.</desc>'
    assert text.endswith("\n")
    assert "\r" not in text


def test_document_requires_title_and_desc(kit: ModuleType) -> None:
    with pytest.raises(ValueError, match="non-empty"):
        kit.svg.document(10, 10, title=" ", desc="x")


def test_text_and_attributes_are_escaped(kit: ModuleType) -> None:
    node = kit.svg.Node("text", data_note='say "hi" & <bye>').text("a < b & c")
    line = kit.svg.serialize(node).split("\n")[1]
    assert line == "<text data-note='say \"hi\" &amp; &lt;bye&gt;'>a &lt; b &amp; c</text>"


def test_mixed_content_stays_on_one_line(kit: ModuleType) -> None:
    node = kit.svg.Node("text", x=0, y=0).text("one ")
    node.add("tspan", fill="#000").text("two")
    assert kit.svg.serialize(node).split("\n")[1] == (
        '<text x="0" y="0">one <tspan fill="#000">two</tspan></text>'
    )


def test_serialized_document_passes_the_validator(kit: ModuleType) -> None:
    assert kit.checks.check_svg(probe_bytes(kit), make_output(kit)) == []
