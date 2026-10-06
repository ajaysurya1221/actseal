"""Deterministic SVG construction and serialization.

A tiny element tree with canonical number formatting, sorted attributes,
two-space indentation and LF line ends. Rendering the same figure twice yields
identical bytes, which is what ``render.py --check`` compares.
"""

from __future__ import annotations

import math
from xml.sax.saxutils import escape, quoteattr

SVG_NS = "http://www.w3.org/2000/svg"
XML_DECLARATION = '<?xml version="1.0" encoding="UTF-8"?>'
TITLE_ID = "title"
DESC_ID = "desc"
_PRECISION = 3

Scalar = str | int | float


def fmt(value: Scalar) -> str:
    """Format a number canonically: at most three decimals, no trailing zeros."""
    if isinstance(value, bool):
        msg = "boolean attribute values are ambiguous; pass a string"
        raise TypeError(msg)
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return str(value)
    if not math.isfinite(value):
        msg = f"non-finite number {value!r} cannot be serialized"
        raise ValueError(msg)
    text = f"{value:.{_PRECISION}f}".rstrip("0").rstrip(".")
    if text in {"-0", ""}:
        return "0"
    return text


def attr_name(key: str) -> str:
    """Map a Python keyword to an attribute name.

    ``font_size`` becomes ``font-size``, ``xlink__href`` becomes ``xlink:href``
    and a trailing underscore is dropped (``class_`` becomes ``class``).
    """
    return key.rstrip("_").replace("__", ":").replace("_", "-")


class Node:
    """One SVG element with string attributes and ordered children."""

    __slots__ = ("attrs", "children", "tag")

    def __init__(self, tag: str, **attrs: Scalar) -> None:
        self.tag = tag
        self.attrs: dict[str, str] = {}
        self.children: list[Node | str] = []
        self.set(**attrs)

    def set(self, **attrs: Scalar) -> Node:
        for key, value in attrs.items():
            self.attrs[attr_name(key)] = fmt(value)
        return self

    def add(self, tag: str, **attrs: Scalar) -> Node:
        child = Node(tag, **attrs)
        self.children.append(child)
        return child

    def append(self, child: Node) -> Node:
        self.children.append(child)
        return child

    def text(self, value: str) -> Node:
        self.children.append(value)
        return self


def document(width: int, height: int, *, title: str, desc: str) -> Node:
    """Create a root ``<svg>`` with explicit size, viewBox, title and description."""
    if not title.strip() or not desc.strip():
        msg = "title and desc must be non-empty"
        raise ValueError(msg)
    root = Node(
        "svg",
        xmlns=SVG_NS,
        width=width,
        height=height,
        viewBox=f"0 0 {width} {height}",
        role="img",
        aria_labelledby=f"{TITLE_ID} {DESC_ID}",
    )
    root.add("title", id=TITLE_ID).text(title)
    root.add("desc", id=DESC_ID).text(desc)
    return root


def serialize(root: Node) -> str:
    """Serialize a tree to canonical text ending with a single newline."""
    lines = [XML_DECLARATION]
    _emit(root, 0, lines)
    return "\n".join(lines) + "\n"


def serialize_bytes(root: Node) -> bytes:
    return serialize(root).encode("utf-8")


def _open_tag(node: Node) -> str:
    attrs = "".join(f" {key}={quoteattr(value)}" for key, value in sorted(node.attrs.items()))
    return f"<{node.tag}{attrs}"


def _inline(node: Node) -> str:
    """Serialize mixed content on one line so text whitespace is exact."""
    if not node.children:
        return f"{_open_tag(node)}/>"
    body = "".join(
        escape(child) if isinstance(child, str) else _inline(child) for child in node.children
    )
    return f"{_open_tag(node)}>{body}</{node.tag}>"


def _emit(node: Node, depth: int, lines: list[str]) -> None:
    pad = "  " * depth
    if not node.children or any(isinstance(child, str) for child in node.children):
        lines.append(pad + _inline(node))
        return
    lines.append(f"{pad}{_open_tag(node)}>")
    for child in node.children:
        if isinstance(child, Node):
            _emit(child, depth + 1, lines)
    lines.append(f"{pad}</{node.tag}>")
