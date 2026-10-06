"""Content, terminology, structure and size rules for the how-it-works figure."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from visual.visual_support import REPO_ROOT

SVG_NS = "{http://www.w3.org/2000/svg}"
DESKTOP = ("how-it-works-light.svg", "how-it-works-dark.svg")
MOBILE = ("how-it-works-mobile-light.svg", "how-it-works-mobile-dark.svg")
STAGE_TITLES = ("Freeze", "Run", "Verify", "Seal", "Replay")
DECISIONS = ("ACT", "ABSTAIN", "ESCALATE", "DENY")
VERDICT_EXITS = (("PASS", "0"), ("BLOCK", "1"), ("INCONCLUSIVE", "2"), ("ERROR", "3"))
COMMANDS = ("actseal lock", "actseal verify", "actseal replay")
MODULES = ("locking", "policy", "assessment", "evidence", "replay")
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
)
MAX_GROUPS = 7
DESKTOP_MIN_LABEL = 26
MOBILE_MIN_LABEL = 30


@pytest.fixture(scope="module")
def rendered(kit: ModuleType) -> dict[str, bytes]:
    context = kit.inventory.RenderContext(root=REPO_ROOT, work=Path("/nonexistent"))
    result: dict[str, bytes] = dict(kit.how_it_works.render(context))
    return result


def _tree(data: bytes) -> ET.Element:
    return ET.fromstring(data)  # noqa: S314 - own freshly rendered bytes


def _texts(root: ET.Element) -> list[str]:
    """Visible label strings, one per <text>, with tspans joined by single spaces."""
    return [" ".join("".join(text.itertext()).split()) for text in root.iter(f"{SVG_NS}text")]


def _groups(root: ET.Element) -> list[str]:
    return [child.get("id", "") for child in root if child.tag == f"{SVG_NS}g"]


def test_renders_exactly_the_declared_outputs(kit: ModuleType, rendered: dict[str, bytes]) -> None:
    asset = kit.inventory.get_asset("how-it-works")
    assert asset.implemented
    assert tuple(rendered) == kit.how_it_works.OUTPUTS == tuple(o.path for o in asset.outputs)
    assert set(DESKTOP) | set(MOBILE) == set(rendered)


def test_rendering_is_deterministic(kit: ModuleType, rendered: dict[str, bytes]) -> None:
    context = kit.inventory.RenderContext(root=REPO_ROOT, work=Path("/nonexistent"))
    assert dict(kit.how_it_works.render(context)) == rendered


def test_every_output_passes_the_validators(kit: ModuleType, rendered: dict[str, bytes]) -> None:
    asset = kit.inventory.get_asset("how-it-works")
    for output in asset.outputs:
        assert kit.checks.check_output(rendered[output.path], output) == [], output.path


def test_desktop_canvas_is_final_and_mobile_is_narrow(kit: ModuleType) -> None:
    asset = kit.inventory.get_asset("how-it-works")
    sizes = {o.path: (o.width, o.height, o.display_width) for o in asset.outputs}
    for name in DESKTOP:
        assert sizes[name] == (1600, 400, kit.inventory.README_DISPLAY_WIDTH)
    for name in MOBILE:
        width, height, display = sizes[name]
        assert (width, display) == (720, kit.inventory.MOBILE_DISPLAY_WIDTH)
        assert height is not None
        assert height == kit.how_it_works.mobile_height() > width


@pytest.mark.parametrize("name", [*DESKTOP, *MOBILE])
def test_five_stages_in_order_and_at_most_seven_groups(
    rendered: dict[str, bytes], name: str
) -> None:
    root = _tree(rendered[name])
    groups = _groups(root)
    stages = [g for g in groups if g.startswith("stage-")]
    assert stages == [f"stage-{title.lower()}" for title in STAGE_TITLES]
    assert len(groups) <= MAX_GROUPS
    headings = [
        " ".join("".join(text.itertext()).split())
        for text in root.iter(f"{SVG_NS}text")
        if text.get("font-weight") == "bold"
    ]
    assert headings == [f"{i} {title}" for i, title in enumerate(STAGE_TITLES, start=1)]


@pytest.mark.parametrize("name", [*DESKTOP, *MOBILE])
def test_required_content_is_present(rendered: dict[str, bytes], name: str) -> None:
    labels = _texts(_tree(rendered[name]))
    joined = "\n".join(labels)
    for decision in DECISIONS:
        assert re.search(rf"\b{decision}\b", joined), decision
    for verdict, code in VERDICT_EXITS:
        # The verdict and its exit code share one label, so the pairing is explicit.
        assert any(re.search(rf"\b{verdict} {code}\b", label) for label in labels), verdict
    assert "verdict, exit code:" in labels
    assert "offline; no model call" in labels
    assert "no provider loaded" in labels
    assert "bounded size" in labels
    assert "every file hashed" in labels
    assert "lock.json + sha256" in labels
    assert "+ 6 fault scenarios" in labels
    for command in COMMANDS:
        assert command in joined, command
    for module in MODULES:
        assert re.search(rf"\b{module}\b", joined), module


@pytest.mark.parametrize("name", [*DESKTOP, *MOBILE])
def test_no_authentication_or_enforcement_language(rendered: dict[str, bytes], name: str) -> None:
    root = _tree(rendered[name])
    prose = " ".join(_texts(root))
    title = root.find(f"{SVG_NS}title")
    desc = root.find(f"{SVG_NS}desc")
    assert title is not None
    assert desc is not None
    prose = " ".join([prose, title.text or "", desc.text or ""]).lower()
    for word in FORBIDDEN_WORDS:
        assert not re.search(rf"\b{word}", prose), word
    assert "freeze" in prose
    assert "replay" in prose


def test_description_names_every_stage_and_limit(rendered: dict[str, bytes]) -> None:
    root = _tree(rendered[DESKTOP[0]])
    desc = root.find(f"{SVG_NS}desc")
    assert desc is not None
    text = desc.text or ""
    assert text
    for title in STAGE_TITLES:
        assert title in text
    for decision in DECISIONS:
        assert decision in text
    for verdict, code in VERDICT_EXITS:
        assert f"{verdict} {code}" in text
    assert "offline" in text
    assert "no model call" in text
    assert "size-bounded" in text


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
        assert len(headings) == len(STAGE_TITLES), name
        assert min(labels) >= minimum, name
        assert min(headings) > max(labels), name
        assert not any(element.get("transform") for element in root.iter()), name


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


def test_desktop_and_mobile_carry_the_same_phrases(rendered: dict[str, bytes]) -> None:
    def phrases(name: str) -> set[str]:
        parts: set[str] = set()
        for label in _texts(_tree(rendered[name])):
            parts.update(p.strip() for p in label.split("·"))
        return parts

    desktop, mobile = phrases(DESKTOP[0]), phrases(MOBILE[0])
    # The mobile variant folds each command into the stage label instead of a
    # bracket row, and "actseal replay" absorbs the module name "replay";
    # everything else is identical phrase for phrase.
    assert desktop - mobile == {"replay"}
    assert mobile - desktop == set()


def test_arrows_connect_consecutive_stages_only(rendered: dict[str, bytes]) -> None:
    for name in (*DESKTOP, *MOBILE):
        root = _tree(rendered[name])
        stage_groups = [
            g for g in root if g.tag == f"{SVG_NS}g" and g.get("id", "").startswith("stage-")
        ]
        heads = [len(g.findall(f"{SVG_NS}polygon")) for g in stage_groups]
        assert heads == [1, 1, 1, 1, 0], name
        rects = [g.find(f"{SVG_NS}rect") for g in stage_groups]
        assert all(r is not None for r in rects)
        if name in DESKTOP:
            xs = [float(r.get("x", "0")) for r in rects if r is not None]
            assert xs == sorted(xs)
            assert len({r.get("y") for r in rects if r is not None}) == 1
            assert len({r.get("height") for r in rects if r is not None}) == 1
        else:
            ys = [float(r.get("y", "0")) for r in rects if r is not None]
            assert ys == sorted(ys)
            assert len({r.get("x") for r in rects if r is not None}) == 1


def test_phrases_fit_their_boxes_under_the_width_model(kit: ModuleType) -> None:
    hiw = kit.how_it_works
    assert hiw.text_width("i", 26) < hiw.text_width("W", 26)
    assert hiw.text_width("x", 26, bold=True) > hiw.text_width("x", 26)
    with pytest.raises(ValueError, match="no width metric"):
        hiw.text_width("→", 26)
    item = hiw.Item(("PASS 0", "BLOCK 1", "INCONCLUSIVE 2", "ERROR 3"))
    assert hiw.wrap(item, 26, 260) == ["PASS 0 · BLOCK 1", "INCONCLUSIVE 2", "ERROR 3"]
    assert hiw.wrap(item, 30, 632) == ["PASS 0 · BLOCK 1 · INCONCLUSIVE 2", "ERROR 3"]
    with pytest.raises(ValueError, match="does not fit"):
        hiw.wrap(hiw.Item(("this phrase is far too long for the box",)), 26, 260)


def test_oversized_content_fails_instead_of_shrinking(
    kit: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    hiw = kit.how_it_works
    stages: Any = list(hiw.STAGES)
    stages[0] = hiw.Stage(
        "freeze",
        "Freeze",
        "locking",
        (hiw.Item(("a phrase that cannot possibly fit in one column",)),),
    )
    monkeypatch.setattr(hiw, "STAGES", tuple(stages))
    context = kit.inventory.RenderContext(root=REPO_ROOT, work=Path("/nonexistent"))
    with pytest.raises(ValueError, match="does not fit"):
        hiw.render(context)


def test_too_many_lines_for_the_desktop_canvas_fails(
    kit: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    hiw = kit.how_it_works
    stages: Any = list(hiw.STAGES)
    stages[0] = hiw.Stage(
        "freeze", "Freeze", "locking", tuple(hiw.Item((f"line {i}",)) for i in range(10))
    )
    monkeypatch.setattr(hiw, "STAGES", tuple(stages))
    with pytest.raises(ValueError, match="desktop layout needs"):
        hiw.render(kit.inventory.RenderContext(root=REPO_ROOT, work=Path("/nonexistent")))


def test_committed_assets_match_regeneration_in_this_checkout(kit: ModuleType) -> None:
    """The Task 12 done-when command, run in-process against the real checkout."""
    report = kit.pipeline.run(REPO_ROOT, mode="check", only=("how-it-works",))
    assert [f.message for f in report.errors] == []
    assert report.checked == ["how-it-works"]
    for output in kit.how_it_works.OUTPUTS:
        assert (REPO_ROOT / "docs" / "assets" / output).is_file()
