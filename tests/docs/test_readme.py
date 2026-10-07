"""README composition and image validation (PLAN section D).

Every image in README.md, including each ``<source srcset>`` and ``<img src>``
inside ``<picture>`` markup, must be an absolute same-repository URL that maps
to an existing, declared, implemented asset under ``docs/assets``. There is no
HTTP fetch, no skip and no xfail: a figure whose files are not committed yet
(the architecture figure until Task 13 lands) fails here, by design. Badges
from the explicit allowlist are exempt from the file check only.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

from docs.conftest import ROOT, fences

README = ROOT / "README.md"
ASSETS = ROOT / "docs" / "assets"
REPO = "ajaysurya1221/actseal"
RAW_PREFIX = f"https://raw.githubusercontent.com/{REPO}/main/"
BLOB_PREFIX = f"https://github.com/{REPO}/blob/main/"
BADGES = (
    re.compile(r"^https://img\.shields\.io/"),
    re.compile(rf"^https://github\.com/{re.escape(REPO)}/actions/workflows/[^/]+/badge\.svg$"),
)
DESCRIPTION = (
    "Actseal verifies model-chosen application actions for developers: freeze a "
    "policy, check its recorded decisions, and replay the evidence offline."
)
QUICKSTART = [
    "uvx --python 3.12 actseal demo --out ./actseal-demo",
    "uvx --offline --python 3.12 actseal replay ./actseal-demo/fixed/evidence",
    "uvx --offline --python 3.12 actseal replay ./actseal-demo/bad/evidence",
]
GUARANTEES = [
    "Complete scheduled-case and required fault evidence is checked.",
    "PASS requires the frozen risk/coverage bounds and fault rules to pass.",
    "Supported evidence is recomputed offline without calling a model.",
]
LIMITS = [
    "Hashes and replay cannot authenticate coherently rewritten responses.",
    "They cannot prove inference occurred or that labels are true.",
    (
        "Population claims require the stated sampling assumptions; "
        "Actseal does not enforce application execution."
    ),
]
ARCHITECTURE_FILES = (
    "architecture-light.svg",
    "architecture-dark.svg",
    "architecture-mobile-light.svg",
    "architecture-mobile-dark.svg",
)
MARKDOWN_IMAGE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<target>[^)\s]+)\)")
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]*\]\((?P<target>[^)\s]+)\)")


class _Images(HTMLParser):
    """Collect every ``img``/``source`` target with the alt text it carries."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.images: list[tuple[str, str | None]] = []  # (target, alt or None for sources)
        self.pictures = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        if tag == "picture":
            self.pictures += 1
        elif tag == "img":
            assert "src" in values, "<img> without src"
            self.images.append((values["src"], values.get("alt", "")))
            for candidate in values.get("srcset", "").split(","):
                if candidate.strip():
                    self.images.append((candidate.split()[0], None))
        elif tag == "source":
            for candidate in values.get("srcset", "").split(","):
                if candidate.strip():
                    self.images.append((candidate.split()[0], None))
        else:
            assert tag not in {"object", "embed", "iframe", "video"}, tag


def _text() -> str:
    return README.read_text(encoding="utf-8")


def _html_images() -> _Images:
    parser = _Images()
    parser.feed(_text())
    parser.close()
    return parser


def _markdown_images() -> list[tuple[str, str]]:
    return [(m["target"], m["alt"]) for m in MARKDOWN_IMAGE.finditer(_text())]


def _is_badge(target: str) -> bool:
    return any(pattern.match(target) for pattern in BADGES)


def _local_asset(target: str) -> Path:
    assert target.startswith(RAW_PREFIX + "docs/assets/"), target
    name = target[len(RAW_PREFIX + "docs/assets/") :]
    assert "/" not in name, target
    assert ".." not in name, target
    return ASSETS / name


def _implemented_outputs() -> set[str]:
    """Outputs of implemented assets, read from the committed inventory source."""
    inventory = (ASSETS / "src" / "actseal_assets" / "inventory.py").read_text(encoding="utf-8")
    outputs: set[str] = set()
    for block in re.split(r"\n    Asset\(", inventory)[1:]:
        if "renderer=" in block:
            outputs.update(re.findall(r"\"([A-Za-z0-9-]+\.(?:svg|png|gif))\"", block))
    return outputs


# --------------------------------------------------------------------------- #
# Opening order and approved copy
# --------------------------------------------------------------------------- #


def test_opening_order_follows_plan_section_d() -> None:
    text = _text()
    hero = text.index("hero-light.svg")
    description = text.index(DESCRIPTION)
    badges = [m.start() for m in re.finditer(r"\[!\[", text)]
    workflow = text.index("how-it-works-light.svg")
    quickstart = text.index(QUICKSTART[0])
    guarantees = text.index("**Guarantees**")
    limits = text.index("**Limits**")
    architecture = text.index("architecture-light.svg")
    links = text.index("docs/stability.md")
    assert len(badges) == 4
    assert hero < description < badges[0] < badges[3] < workflow < quickstart
    assert quickstart < guarantees < limits < architecture < links
    assert text.index(DESCRIPTION) == text.index(DESCRIPTION.split(":", maxsplit=1)[0])


def test_quickstart_guarantees_and_limits_are_verbatim() -> None:
    text = _text()
    assert fences(README, "bash")[0].strip().splitlines() == QUICKSTART
    for line in GUARANTEES + LIMITS:
        assert f"- {line}" in text, line
    assert "exits 1" in text
    assert "Windows is unsupported" in text
    assert "https://pypi.org/project/actseal/" in text


def test_readme_claims_no_publication_state_or_stale_version() -> None:
    text = _text()
    for stale in ("actseal==0.1.0", "v0.1.0 supports", "Jev is deferred", "0.17 seconds"):
        assert stale not in text, stale
    # The included experimental provider is named with its opt-in and its
    # evidence status; the status may change when a live receipt is accepted.
    assert "PROVISIONAL" in text
    assert "--provider jev --experimental-provider" in text
    assert "live" in text
    assert "demo.gif" not in text  # the genuine recording is added by Task 21
    assert "1.0.0 is published" not in text


# --------------------------------------------------------------------------- #
# Links and images: absolute, same-repository, locally resolvable
# --------------------------------------------------------------------------- #


def test_every_link_is_absolute_and_same_repo_links_resolve() -> None:
    for match in MARKDOWN_LINK.finditer(_text()):
        target = match["target"]
        assert target.startswith("https://"), target
        if target.startswith(BLOB_PREFIX):
            relative = target[len(BLOB_PREFIX) :].split("#")[0]
            assert ".." not in relative
            assert (ROOT / relative).is_file(), target


def test_navigation_links_the_release_notes_absolutely_and_labels_their_state() -> None:
    """The link is permanent; its draft wording must track the notes' actual state.

    While ``plan/v1/RELEASE_NOTES.md`` carries its DRAFT status marker the label
    must say so; once the notes are finalized the label must drop the draft
    wording. Neither state is forced on the notes themselves.
    """
    text = _text()
    target = f"{BLOB_PREFIX}plan/v1/RELEASE_NOTES.md"
    match = re.search(rf"\[(?P<label>[^\]]*)\]\({re.escape(target)}\)", text)
    assert match is not None, "README navigation must link the release notes absolutely"
    notes_path = ROOT / "plan" / "v1" / "RELEASE_NOTES.md"
    assert notes_path.is_file()
    label = match["label"]
    assert label.startswith("release notes"), label
    notes_are_draft = "DRAFT" in notes_path.read_text(encoding="utf-8")
    assert ("draft" in label) == notes_are_draft, (label, notes_are_draft)


def test_hero_alt_text_states_the_three_evidence_limits() -> None:
    """The hero already draws its caption; the alt text must carry it too."""
    hero_alt = next(alt for target, alt in _html_images().images if "hero-light.svg" in target)
    assert hero_alt is not None
    for limit in ("authenticate responses", "prove inference occurred", "label truth"):
        assert limit in hero_alt, limit
    svg = (ASSETS / "hero-light.svg").read_text(encoding="utf-8")
    caption = (
        "Replay cannot authenticate responses, prove inference occurred, or establish label truth."
    )
    assert caption in svg
    assert caption in hero_alt


def test_every_image_has_alt_text_and_is_absolute() -> None:
    html = _html_images()
    markdown = _markdown_images()
    assert html.pictures == 3  # hero, how-it-works, architecture
    for target, markdown_alt in markdown:
        assert target.startswith("https://"), target
        assert markdown_alt.strip(), target
    for target, html_alt in html.images:
        assert target.startswith("https://"), target
        if html_alt is not None:
            assert html_alt.strip(), target
    assert sum(1 for _, html_alt in html.images if html_alt is not None) == 3


def test_every_image_resolves_to_a_committed_implemented_asset() -> None:
    """No HTTP, no skip: a referenced figure whose files are not committed fails here."""
    outputs = _implemented_outputs()
    assert {"hero-light.svg", "how-it-works-light.svg", "social.png"} <= outputs
    missing: list[str] = []
    targets = [t for t, _ in _html_images().images] + [t for t, _ in _markdown_images()]
    for target in targets:
        if _is_badge(target):
            continue
        path = _local_asset(target)
        if not path.is_file():
            missing.append(path.name)
            continue
        assert path.name in outputs, f"{path.name} is not an implemented asset output"
    assert not missing, f"README references uncommitted figure files: {sorted(set(missing))}"


def test_architecture_filenames_are_the_frozen_four() -> None:
    """The names are frozen now; their outputs arrive with Task 13."""
    referenced = {
        _local_asset(target).name
        for target, _ in _html_images().images
        if not _is_badge(target) and "architecture" in target
    }
    assert referenced == set(ARCHITECTURE_FILES)


def test_picture_variants_cover_light_dark_desktop_and_mobile() -> None:
    names = [_local_asset(t).name for t, _ in _html_images().images if not _is_badge(t)]
    for figure in ("hero", "how-it-works", "architecture"):
        assert [n for n in names if n.startswith(figure)] == [
            f"{figure}-mobile-dark.svg",
            f"{figure}-mobile-light.svg",
            f"{figure}-dark.svg",
            f"{figure}-light.svg",
        ], figure
