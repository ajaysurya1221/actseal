"""Content, mapping, edge, structure and size rules for the architecture figure.

Everything here inspects SVG bytes rendered in memory. These are structural
checks (element tree, measured widths, declared sizes); they are not a review
of rendered pixels, which needs a rasterizer and a human.
"""

from __future__ import annotations

import importlib
import re
import xml.etree.ElementTree as ET
from itertools import pairwise
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from visual.visual_support import REPO_ROOT

SVG_NS = "{http://www.w3.org/2000/svg}"
DESKTOP = ("architecture-light.svg", "architecture-dark.svg")
MOBILE = ("architecture-mobile-light.svg", "architecture-mobile-dark.svg")
ALL = (*DESKTOP, *MOBILE)
GROUP_KEYS = (
    "contracts",
    "cli",
    "providers",
    "normalization",
    "assessment",
    "evidence",
    "replay",
)
#: The approved seven groups and the modules that implement each, from reading
#: the actual sources under ``src/actseal`` (docs/architecture.md boundaries).
EXPECTED_MAPPING = {
    "contracts": {"contract", "records", "errors", "serialization", "locking", "compatibility"},
    "cli": {"cli", "runner", "__init__", "__main__", "demo_data"},
    "providers": {"adapters.base", "adapters.fixture", "adapters.laya"},
    "normalization": {"normalization", "policy"},
    "assessment": {"assessment", "stats", "faults"},
    "evidence": {"evidence"},
    "replay": {"replay"},
}
EXPECTED_EDGES = {
    ("cli", "contracts"),
    ("cli", "providers"),
    ("providers", "normalization"),
    ("normalization", "assessment"),
    ("contracts", "assessment"),
    ("assessment", "evidence"),
    ("evidence", "replay"),
    ("replay", "contracts"),
    ("replay", "assessment"),
}
EXPECTED_LABELS = {
    ("normalization", "assessment"): "decisions",
    ("contracts", "assessment"): "6 synthetic faults",
    ("assessment", "evidence"): "verdict, records, faults",
    ("replay", "contracts"): "lock, inputs",
    ("replay", "assessment"): "recompute",
}
LIVE_LABEL = "live inference"
# Words that would suggest response authentication, proof of inference,
# label truth, tamper resistance or application enforcement.
FORBIDDEN_WORDS = (
    "authentic",
    "proof",
    "prove",
    "proves",
    "proven",
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
    "truth",
    "safe",
    "jev",
)
MAX_GROUPS = 7
DESKTOP_MIN_LABEL = 26
MOBILE_MIN_LABEL = 30
README_DISPLAY_WIDTH = 880
MOBILE_DISPLAY_WIDTH = 360
ARROW_TOLERANCE = 6.0


@pytest.fixture(scope="module")
def arch(kit: ModuleType) -> ModuleType:
    """The architecture module; not yet exported by the package ``__init__``."""
    assert kit.__name__ == "actseal_assets"
    return importlib.import_module("actseal_assets.architecture")


@pytest.fixture(scope="module")
def rendered(kit: ModuleType, arch: ModuleType) -> dict[str, bytes]:
    context = kit.inventory.RenderContext(root=REPO_ROOT, work=Path("/nonexistent"))
    result: dict[str, bytes] = dict(arch.render(context))
    return result


def _tree(data: bytes) -> ET.Element:
    return ET.fromstring(data)  # noqa: S314 - own freshly rendered bytes


def _text(element: ET.Element) -> str:
    return " ".join("".join(element.itertext()).split())


def _texts(root: ET.Element) -> list[str]:
    return [_text(text) for text in root.iter(f"{SVG_NS}text")]


def _top_groups(root: ET.Element) -> list[ET.Element]:
    return [child for child in root if child.tag == f"{SVG_NS}g"]


def _group(root: ET.Element, key: str) -> ET.Element:
    for child in _top_groups(root):
        if child.get("id") == f"group-{key}":
            return child
    msg = f"no group {key}"
    raise AssertionError(msg)


def _rect(group: ET.Element) -> tuple[float, float, float, float]:
    rect = group.find(f"{SVG_NS}rect")
    assert rect is not None
    x, y = float(rect.get("x", "0")), float(rect.get("y", "0"))
    return x, y, x + float(rect.get("width", "0")), y + float(rect.get("height", "0"))


def _edges(root: ET.Element) -> list[ET.Element]:
    return [g for g in root.iter(f"{SVG_NS}g") if g.get("data-source")]


def _points(element: ET.Element) -> list[tuple[float, float]]:
    return [
        (float(pair.split(",")[0]), float(pair.split(",")[1]))
        for pair in element.get("points", "").split()
    ]


def _module_names(group: ET.Element, arch: ModuleType) -> list[str]:
    """Module names drawn in ``group``: accent-coloured body lines split on the separator."""
    names: list[str] = []
    for text in group.iter(f"{SVG_NS}text"):
        if text.get("font-weight") == "bold" or _text(text) == LIVE_LABEL:
            continue
        if text.get("fill") not in {arch.LIGHT.accent, arch.DARK.accent}:
            continue
        names.extend(part.strip() for part in _text(text).split("·"))
    return names


def _runtime_modules() -> set[str]:
    """Dotted names of every ``actseal`` source module in this checkout."""
    package = REPO_ROOT / "src" / "actseal"
    names: set[str] = set()
    for path in package.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        parts = path.relative_to(package).with_suffix("").parts
        if parts[-1] == "__init__" and len(parts) > 1:
            names.add(".".join(parts[:-1]))
        else:
            names.add(".".join(parts))
    return names


def test_renders_exactly_the_declared_outputs(arch: ModuleType, rendered: dict[str, bytes]) -> None:
    assert tuple(rendered) == arch.OUTPUTS == ALL
    prefix = b'<?xml version="1.0" encoding="UTF-8"?>\n<svg'
    assert all(data.startswith(prefix) for data in rendered.values())


def test_rendering_is_deterministic(
    kit: ModuleType, arch: ModuleType, rendered: dict[str, bytes]
) -> None:
    context = kit.inventory.RenderContext(root=REPO_ROOT, work=Path("/nonexistent"))
    assert dict(arch.render(context)) == rendered


def _outputs(kit: ModuleType, arch: ModuleType) -> list[Any]:
    """The four Output declarations this figure will register once accepted."""
    desktop = [
        kit.inventory.Output(
            path=name,
            kind="svg",
            width=arch.DESKTOP_WIDTH,
            height=arch.DESKTOP_HEIGHT,
            display_width=README_DISPLAY_WIDTH,
        )
        for name in DESKTOP
    ]
    mobile = [
        kit.inventory.Output(
            path=name,
            kind="svg",
            width=arch.MOBILE_WIDTH,
            height=arch.mobile_height(),
            display_width=MOBILE_DISPLAY_WIDTH,
        )
        for name in MOBILE
    ]
    return [*desktop, *mobile]


def test_every_output_passes_the_validators(
    kit: ModuleType, arch: ModuleType, rendered: dict[str, bytes]
) -> None:
    for output in _outputs(kit, arch):
        assert kit.checks.check_output(rendered[output.path], output) == [], output.path
    assert arch.DESKTOP_WIDTH == 1600
    assert arch.DESKTOP_HEIGHT == 900
    assert arch.MOBILE_WIDTH == 720
    assert arch.mobile_height() > arch.MOBILE_WIDTH


def test_inventory_registration_is_deferred_until_provider_inclusion(
    kit: ModuleType, arch: ModuleType
) -> None:
    """The asset is declared; attaching this renderer waits for the provider decision."""
    asset = kit.inventory.get_asset("architecture")
    assert asset.task == "13"
    if asset.implemented:
        assert asset.renderer is arch.render
        assert tuple(output.path for output in asset.outputs) == arch.OUTPUTS
    assert all(kit.inventory.is_plain_filename(name) for name in arch.OUTPUTS)


@pytest.mark.parametrize("name", ALL)
def test_exactly_seven_groups_with_edges_nested_inside_them(
    rendered: dict[str, bytes], name: str
) -> None:
    root = _tree(rendered[name])
    groups = _top_groups(root)
    assert len(groups) == MAX_GROUPS
    assert sorted(g.get("id", "") for g in groups) == sorted(f"group-{k}" for k in GROUP_KEYS)
    # No other top-level containers: the canvas rectangle, title and desc only.
    others = [child.tag for child in root if child.tag != f"{SVG_NS}g"]
    assert others == [f"{SVG_NS}title", f"{SVG_NS}desc", f"{SVG_NS}rect"]
    headings = [_text(t) for t in root.iter(f"{SVG_NS}text") if t.get("font-weight") == "bold"]
    joined = " ".join(headings)
    for phrase in ("Contracts / locks", "CLI / typed API", "Providers", "Normalization", "policy"):
        assert phrase in joined, phrase
    assert "Assessment / statistics / faults" in joined
    assert "Evidence" in joined
    assert "Replay" in joined


@pytest.mark.parametrize("name", ALL)
def test_every_runtime_module_is_drawn_exactly_once(
    arch: ModuleType, rendered: dict[str, bytes], name: str
) -> None:
    root = _tree(rendered[name])
    drawn: list[str] = []
    for key in GROUP_KEYS:
        drawn.extend(_module_names(_group(root, key), arch))
    assert len(drawn) == len(set(drawn)), "a module is drawn twice"
    modules = _runtime_modules()
    assert set(drawn) <= modules, set(drawn) - modules
    # The only undrawn source file is the adapters package marker, whose three
    # members are all drawn.
    assert modules - set(drawn) == {"adapters"}
    assert {"adapters.base", "adapters.fixture", "adapters.laya"} <= set(drawn)


@pytest.mark.parametrize("name", ALL)
def test_modules_sit_in_their_approved_groups(
    arch: ModuleType, rendered: dict[str, bytes], name: str
) -> None:
    root = _tree(rendered[name])
    for key, expected in EXPECTED_MAPPING.items():
        assert set(_module_names(_group(root, key), arch)) == expected, key
    assert set().union(*EXPECTED_MAPPING.values()) == _runtime_modules() - {"adapters"}


@pytest.mark.parametrize("name", ALL)
def test_live_boundary_encloses_only_the_laya_adapter(
    rendered: dict[str, bytes], name: str
) -> None:
    root = _tree(rendered[name])
    boundaries = [g for g in root.iter(f"{SVG_NS}g") if g.get("id", "").startswith("live-boundary")]
    assert len(boundaries) == 1
    boundary = boundaries[0]
    providers = _group(root, "providers")
    assert boundary in list(providers)
    rect = boundary.find(f"{SVG_NS}rect")
    assert rect is not None
    assert rect.get("stroke-dasharray")
    assert rect.get("fill") == "none"
    assert [_text(t) for t in boundary.iter(f"{SVG_NS}text")] == ["adapters.laya", LIVE_LABEL]
    # Everything inside the dashed rectangle geometrically is the Laya node.
    bx, by, bright, bbottom = _rect(boundary)
    for text in providers.iter(f"{SVG_NS}text"):
        x, y = float(text.get("x", "0")), float(text.get("y", "0"))
        size = float(text.get("font-size", "0"))
        inside = bx <= x <= bright and by <= y - size <= bbottom and y <= bbottom
        assert inside == (_text(text) in {"adapters.laya", LIVE_LABEL}), _text(text)
    # The fixture adapter and the fault generator are outside any boundary.
    outside = [_text(t) for t in root.iter(f"{SVG_NS}text") if t not in list(boundary.iter())]
    assert any("adapters.fixture" in label for label in outside)
    assert any("faults" in label for label in outside)
    assert "live model" not in " ".join(_texts(root)).lower()


@pytest.mark.parametrize("name", ALL)
def test_edges_match_the_module_graph_and_never_join_replay_to_providers(
    rendered: dict[str, bytes], name: str
) -> None:
    root = _tree(rendered[name])
    edges = _edges(root)
    pairs = {(e.get("data-source", ""), e.get("data-target", "")) for e in edges}
    assert pairs == EXPECTED_EDGES
    assert len(edges) == len(EXPECTED_EDGES)
    for edge in edges:
        source = edge.get("data-source", "")
        parent = _group(root, source)
        assert edge in list(parent), edge.get("id")
        assert len(edge.findall(f"{SVG_NS}polyline")) == 1
        assert len(edge.findall(f"{SVG_NS}polygon")) == 1
        labels = [_text(t) for t in edge.findall(f"{SVG_NS}text")]
        expected = EXPECTED_LABELS.get((source, edge.get("data-target", "")))
        assert labels == ([expected] if expected else []), edge.get("id")
    # Replay reads the bundle and recomputes through contracts and assessment.
    assert {t for s, t in pairs if s == "replay"} == {"contracts", "assessment"}
    assert {s for s, t in pairs if t == "replay"} == {"evidence"}
    assert not any("providers" in pair and "replay" in pair for pair in pairs)
    # Providers are reached only from the CLI and feed only normalization; the
    # fault campaign comes from the lock, never from a provider.
    assert {pair for pair in pairs if "providers" in pair} == {
        ("cli", "providers"),
        ("providers", "normalization"),
    }
    assert ("contracts", "assessment") in pairs


Point = tuple[float, float]
Segment = tuple[Point, Point]


def _segments(root: ET.Element) -> list[tuple[str, Segment]]:
    """Every drawn arrow segment (shaft segments plus the head) keyed by edge id."""
    segments: list[tuple[str, Segment]] = []
    for edge in _edges(root):
        polyline = edge.find(f"{SVG_NS}polyline")
        polygon = edge.find(f"{SVG_NS}polygon")
        assert polyline is not None
        assert polygon is not None
        points = [*_points(polyline), _points(polygon)[0]]
        key = edge.get("id", "")
        segments.extend((key, (a, b)) for a, b in pairwise(points))
    return segments


def _crosses(a: Segment, b: Segment) -> bool:
    """Whether two axis-aligned segments overlap collinearly or cross in their interiors."""
    (ax1, ay1), (ax2, ay2) = a
    (bx1, by1), (bx2, by2) = b
    a_vertical = ax1 == ax2
    b_vertical = bx1 == bx2
    if a_vertical and b_vertical:
        if ax1 != bx1:
            return False
        lo, hi = max(min(ay1, ay2), min(by1, by2)), min(max(ay1, ay2), max(by1, by2))
        return lo < hi
    if not a_vertical and not b_vertical:
        if ay1 != by1:
            return False
        lo, hi = max(min(ax1, ax2), min(bx1, bx2)), min(max(ax1, ax2), max(bx1, bx2))
        return lo < hi
    if not a_vertical:
        return _crosses(b, a)
    # ``a`` is vertical at ax1; ``b`` is horizontal at by1.
    return min(ay1, ay2) < by1 < max(ay1, ay2) and min(bx1, bx2) < ax1 < max(bx1, bx2)


@pytest.mark.parametrize("name", ALL)
def test_arrows_are_orthogonal_touch_their_targets_and_do_not_cross(
    rendered: dict[str, bytes], name: str
) -> None:
    root = _tree(rendered[name])
    rects = {key: _rect(_group(root, key)) for key in GROUP_KEYS}
    for edge in _edges(root):
        polyline = edge.find(f"{SVG_NS}polyline")
        polygon = edge.find(f"{SVG_NS}polygon")
        assert polyline is not None
        assert polygon is not None
        points = _points(polyline)
        tip = _points(polygon)[0]
        for a, b in pairwise(points):
            assert a[0] == b[0] or a[1] == b[1], edge.get("id")
        start = points[0]
        assert _touches(rects[edge.get("data-source", "")], start), (edge.get("id"), start)
        assert _touches(rects[edge.get("data-target", "")], tip), (edge.get("id"), tip)
        # No segment passes through the interior of any box.
        for a, b in pairwise([*points, tip]):
            for key, (rx1, ry1, rx2, ry2) in rects.items():
                lo_x, hi_x = min(a[0], b[0]), max(a[0], b[0])
                lo_y, hi_y = min(a[1], b[1]), max(a[1], b[1])
                inside = hi_x > rx1 + 1 and lo_x < rx2 - 1 and hi_y > ry1 + 1 and lo_y < ry2 - 1
                assert not inside, (edge.get("id"), key)
    segments = _segments(root)
    for i, (key_a, segment_a) in enumerate(segments):
        for key_b, segment_b in segments[i + 1 :]:
            if key_a == key_b:
                continue
            assert not _crosses(segment_a, segment_b), (key_a, key_b)


def _touches(rect: tuple[float, float, float, float], point: tuple[float, float]) -> bool:
    x1, y1, x2, y2 = rect
    px, py = point
    near_vertical_edge = min(abs(px - x1), abs(px - x2)) <= ARROW_TOLERANCE and y1 <= py <= y2
    near_horizontal_edge = min(abs(py - y1), abs(py - y2)) <= ARROW_TOLERANCE and x1 <= px <= x2
    return near_vertical_edge or near_horizontal_edge


@pytest.mark.parametrize("name", ALL)
def test_text_fits_inside_its_box_under_the_width_model(
    arch: ModuleType, rendered: dict[str, bytes], name: str
) -> None:
    root = _tree(rendered[name])
    width = float(root.get("width", "0"))
    for key in GROUP_KEYS:
        group = _group(root, key)
        x1, y1, x2, y2 = _rect(group)
        edge_texts = {t for e in _edges(group) for t in e.iter(f"{SVG_NS}text")}
        for text in group.iter(f"{SVG_NS}text"):
            size = float(text.get("font-size", "0"))
            bold = text.get("font-weight") == "bold"
            measured = arch.text_width(_text(text), size, bold=bold)
            x, y = float(text.get("x", "0")), float(text.get("y", "0"))
            if text in edge_texts:
                anchor = text.get("text-anchor", "start")
                left = {"start": x, "middle": x - measured / 2, "end": x - measured}[anchor]
                assert left >= 0, (_text(text), name)
                assert left + measured <= width, (_text(text), name)
                continue
            assert text.get("text-anchor") is None
            assert x1 < x, (_text(text), name)
            assert x + measured <= x2, (_text(text), name)
            assert y1 < y - size, (_text(text), name)
            assert y <= y2, (_text(text), name)


Rect = tuple[float, float, float, float]


def _text_boxes(root: ET.Element, arch: ModuleType) -> list[tuple[str, Rect]]:
    """Conservative bounding boxes of every label under the width model."""
    boxes: list[tuple[str, Rect]] = []
    for text in root.iter(f"{SVG_NS}text"):
        size = float(text.get("font-size", "0"))
        bold = text.get("font-weight") == "bold"
        measured = arch.text_width(_text(text), size, bold=bold)
        x, y = float(text.get("x", "0")), float(text.get("y", "0"))
        anchor = text.get("text-anchor", "start")
        left = {"start": x, "middle": x - measured / 2, "end": x - measured}[anchor]
        boxes.append((_text(text), (left, y - size * 0.75, left + measured, y + size * 0.25)))
    return boxes


def _overlaps(a: Rect, b: Rect) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


@pytest.mark.parametrize("name", ALL)
def test_labels_do_not_overlap_each_other_or_any_arrow(
    arch: ModuleType, rendered: dict[str, bytes], name: str
) -> None:
    root = _tree(rendered[name])
    boxes = _text_boxes(root, arch)
    for i, (label_a, box_a) in enumerate(boxes):
        for label_b, box_b in boxes[i + 1 :]:
            assert not _overlaps(box_a, box_b), (label_a, label_b, name)
    for key, ((x1, y1), (x2, y2)) in _segments(root):
        segment = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
        for label, box in boxes:
            assert not _overlaps(segment, box), (key, label, name)
    # Dashed live boundary and dividers keep clear of text too.
    for line in root.iter(f"{SVG_NS}line"):
        x1, y1 = float(line.get("x1", "0")), float(line.get("y1", "0"))
        x2, y2 = float(line.get("x2", "0")), float(line.get("y2", "0"))
        for label, box in boxes:
            assert not _overlaps((x1, y1, x2, y2), box), ("divider", label, name)


@pytest.mark.parametrize("name", ALL)
def test_no_authentication_enforcement_or_jev_language(
    rendered: dict[str, bytes], name: str
) -> None:
    root = _tree(rendered[name])
    title = root.find(f"{SVG_NS}title")
    desc = root.find(f"{SVG_NS}desc")
    assert title is not None
    assert desc is not None
    prose = " ".join([*_texts(root), title.text or "", desc.text or ""]).lower()
    for word in FORBIDDEN_WORDS:
        assert not re.search(rf"\b{word}", prose), word
    assert "fixture" in prose
    assert "laya" in prose
    assert "no model call" in prose
    assert "offline" in prose


def test_description_names_every_group_module_and_limit(
    arch: ModuleType, rendered: dict[str, bytes]
) -> None:
    root = _tree(rendered[DESKTOP[0]])
    desc = root.find(f"{SVG_NS}desc")
    assert desc is not None
    text = desc.text or ""
    for group in arch.GROUPS:
        for module in (*group.modules, *group.live):
            assert module in text, module
    for phrase in (
        "Seven groups",
        "encloses only the Laya adapter",
        "fixture adapter reads a recorded file",
        "six fault scenarios are synthetic",
        "no model call",
        "recomputes the verdict offline",
        "no arrow joins replay and providers",
        "replay imports no provider module",
        "The shipped providers are fixture and Laya.",
    ):
        assert phrase in text, phrase
    assert text == arch.DESC
    assert (title := root.find(f"{SVG_NS}title")) is not None
    assert title.text == arch.TITLE


@pytest.mark.parametrize(
    ("names", "minimum"), [(DESKTOP, DESKTOP_MIN_LABEL), (MOBILE, MOBILE_MIN_LABEL)]
)
def test_labels_meet_the_minimum_size_and_headings_are_larger(
    rendered: dict[str, bytes], names: tuple[str, ...], minimum: int
) -> None:
    for name in names:
        root = _tree(rendered[name])
        texts = list(root.iter(f"{SVG_NS}text"))
        headings = [float(t.get("font-size", "0")) for t in texts if t.get("font-weight") == "bold"]
        labels = [float(t.get("font-size", "0")) for t in texts if t.get("font-weight") != "bold"]
        assert len(headings) >= MAX_GROUPS, name
        assert min(labels) >= minimum, name
        assert min(headings) > max(labels), name
        assert not any(element.get("transform") for element in root.iter()), name
        for text in texts:
            family = text.get("font-family")
            assert family is None or family.split(",")[-1].strip() == "sans-serif"


def test_light_and_dark_differ_only_in_color(rendered: dict[str, bytes]) -> None:
    for light_name, dark_name in (DESKTOP, MOBILE):
        light, dark = _tree(rendered[light_name]), _tree(rendered[dark_name])
        assert rendered[light_name] != rendered[dark_name]
        for a, b in zip(light.iter(), dark.iter(), strict=True):
            assert a.tag == b.tag
            assert (a.text or "").strip() == (b.text or "").strip()
            for key in a.attrib:
                if key in {"fill", "stroke"}:
                    continue
                assert a.get(key) == b.get(key), (a.tag, key)


def test_desktop_and_mobile_carry_the_same_content(
    arch: ModuleType, rendered: dict[str, bytes]
) -> None:
    def content(name: str) -> tuple[set[str], set[str], set[str], set[tuple[str, str]]]:
        root = _tree(rendered[name])
        names = {m for key in GROUP_KEYS for m in _module_names(_group(root, key), arch)}
        edge_texts = {_text(t) for e in _edges(root) for t in e.iter(f"{SVG_NS}text")}
        # Headings and module runs wrap differently per canvas, so phrases are
        # compared after splitting on the two separators.
        phrases = {
            part.strip()
            for label in _texts(root)
            if label not in edge_texts
            for part in re.split(r"[·/]", label)
        }
        pairs = {(e.get("data-source", ""), e.get("data-target", "")) for e in _edges(root)}
        return names, phrases, edge_texts, pairs

    assert content(DESKTOP[0]) == content(MOBILE[0])
    desktop_order = [g.get("id") for g in _top_groups(_tree(rendered[DESKTOP[0]]))]
    mobile_order = [g.get("id") for g in _top_groups(_tree(rendered[MOBILE[0]]))]
    assert desktop_order == [f"group-{g.key}" for g in arch.GROUPS]
    assert mobile_order == [f"group-{k}" for k in arch.MOBILE_ORDER]
    # Mobile stacks the boxes in one column; desktop keeps three rows.
    mobile_rects = [_rect(_group(_tree(rendered[MOBILE[0]]), k)) for k in arch.MOBILE_ORDER]
    assert [r[1] for r in mobile_rects] == sorted(r[1] for r in mobile_rects)
    assert len({(r[0], r[2]) for r in mobile_rects}) == 1
    desktop_rects = [_rect(_group(_tree(rendered[DESKTOP[0]]), k)) for k in GROUP_KEYS]
    assert len({r[1] for r in desktop_rects}) == 3


def test_width_model_and_wrapping(arch: ModuleType) -> None:
    assert arch.wrap(("a", "b"), 26, 1000, separator=" · ") == ["a · b"]
    names = ("contract", "records", "errors", "serialization", "locking", "compatibility")
    desktop = arch.wrap(names, 26, 326, separator=" · ")
    assert desktop == ["contract · records · errors", "serialization · locking", "compatibility"]
    mobile = arch.wrap(names, 30, 608, separator=" · ")
    assert mobile == ["contract · records · errors · serialization", "locking · compatibility"]
    with pytest.raises(ValueError, match="does not fit"):
        arch.wrap(("this single phrase is far too long for the column",), 26, 200, separator=" · ")
    # The desktop column cannot hold the two-word heading on one line; the
    # mobile column can.
    bold = arch.wrap(("Normalization", "policy"), 32, 326, separator=" / ", bold=True)
    assert bold == ["Normalization", "policy"]
    assert arch.wrap(("Normalization", "policy"), 36, 608, separator=" / ", bold=True) == [
        "Normalization / policy"
    ]


def test_oversized_content_fails_instead_of_shrinking(
    kit: ModuleType, arch: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    groups: Any = list(arch.GROUPS)
    groups[-1] = arch.Group(
        "replay", ("Replay",), ("replay",), ("a note that cannot possibly fit in one column",)
    )
    monkeypatch.setattr(arch, "GROUPS", tuple(groups))
    context = kit.inventory.RenderContext(root=REPO_ROOT, work=Path("/nonexistent"))
    with pytest.raises(ValueError, match="does not fit"):
        arch.render(context)


def test_too_many_lines_for_the_desktop_canvas_fails(
    kit: ModuleType, arch: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    groups: Any = list(arch.GROUPS)
    notes = tuple(f"note {i}" for i in range(12))
    groups[-1] = arch.Group("replay", ("Replay",), ("replay",), notes)
    monkeypatch.setattr(arch, "GROUPS", tuple(groups))
    with pytest.raises(ValueError, match="desktop layout needs"):
        arch.render(kit.inventory.RenderContext(root=REPO_ROOT, work=Path("/nonexistent")))


def test_an_edge_with_a_diagonal_final_segment_is_rejected(arch: ModuleType) -> None:
    node = arch.svg.Node("g")
    edge = arch.Edge("probe", "cli", "contracts")
    with pytest.raises(ValueError, match="horizontal or vertical"):
        arch._arrow(node, edge, ((0.0, 0.0), (10.0, 10.0)), "#000000")


def test_toolchain_sources_are_reused_not_modified(arch: ModuleType, kit: ModuleType) -> None:
    """The figure imports the reviewed palette, font stack and width model."""
    assert arch.LIGHT is kit.how_it_works.LIGHT
    assert arch.DARK is kit.how_it_works.DARK
    assert arch.FONT_STACK == kit.how_it_works.FONT_STACK
    assert arch.text_width is kit.how_it_works.text_width
