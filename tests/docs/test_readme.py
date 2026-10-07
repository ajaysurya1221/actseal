"""README composition and image validation (PLAN section D).

Every image in README.md, including each ``<source srcset>`` and ``<img src>``
inside ``<picture>`` markup, must be an absolute same-repository URL that maps
to an existing, declared, implemented asset under ``docs/assets``. There is no
HTTP fetch, no skip and no xfail: a figure whose files are not committed yet
(the architecture figure until Task 13 landed; the demo recording until the
Task 14 activation lands) fails here, by design. Badges from the explicit
allowlist are exempt from the file check only.
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
FIGURES = ("hero", "how-it-works", "architecture")
#: The genuine post-publication recording (Task 14, Decision 2A), one GIF per
#: colour scheme, integrated by Task 21 below the frozen opening sequence.
DEMO_FILES = ("demo-light.gif", "demo-dark.gif")
#: Narrowest browser viewport (CSS px) that selects the desktop variants.
#: Read-only measurements of the public repository view at candidate 5e7931a
#: (review 13) gave the README image 838 px at 1280 and 1366 px viewports and
#: only 758 px at 1200; a 1600-unit desktop canvas with 26-unit labels drops
#: below the 14 px floor anywhere under 1280 px, so every narrower viewport
#: selects the vertical variants.
DESKTOP_MIN_VIEWPORT = 1280
MOBILE_MEDIA = f"(max-width: {DESKTOP_MIN_VIEWPORT - 1}px)"
MOBILE_VIEWPORTS = (320, 360, 800, 1000, 1200, DESKTOP_MIN_VIEWPORT - 1)
DESKTOP_VIEWPORTS = (DESKTOP_MIN_VIEWPORT, 1366, 1920)
MEDIA_FEATURE = re.compile(r"^\((?P<name>[a-z-]+):\s*(?P<value>[^)]+)\)$")
MARKDOWN_IMAGE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<target>[^)\s]+)\)")
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]*\]\((?P<target>[^)\s]+)\)")


class _Picture:
    """One ``<picture>`` block: its ``<source>`` rows in order and the ``<img>`` fallback."""

    def __init__(self) -> None:
        self.sources: list[tuple[str, str]] = []  # (media, target) in document order
        self.fallback: str | None = None


class _Images(HTMLParser):
    """Collect every ``img``/``source`` target with the alt text it carries."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.images: list[tuple[str, str | None]] = []  # (target, alt or None for sources)
        self.pictures = 0
        self.picture_blocks: list[_Picture] = []
        self._open: _Picture | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        if tag == "picture":
            self.pictures += 1
            assert self._open is None, "nested <picture>"
            self._open = _Picture()
            self.picture_blocks.append(self._open)
        elif tag == "img":
            assert "src" in values, "<img> without src"
            self.images.append((values["src"], values.get("alt", "")))
            for candidate in values.get("srcset", "").split(","):
                if candidate.strip():
                    self.images.append((candidate.split()[0], None))
            if self._open is not None:
                assert self._open.fallback is None, "two <img> in one <picture>"
                self._open.fallback = values["src"]
        elif tag == "source":
            assert self._open is not None, "<source> outside <picture>"
            assert self._open.fallback is None, "<source> after the <img> fallback is ignored"
            candidates = [c.split()[0] for c in values.get("srcset", "").split(",") if c.strip()]
            assert len(candidates) == 1, values.get("srcset")
            self.images.append((candidates[0], None))
            self._open.sources.append((values.get("media", ""), candidates[0]))
        else:
            assert tag not in {"object", "embed", "iframe", "video"}, tag

    def handle_endtag(self, tag: str) -> None:
        if tag == "picture":
            assert self._open is not None, "</picture> without <picture>"
            assert self._open.fallback is not None, "<picture> without <img>"
            self._open = None


def _media_matches(media: str, *, viewport: int, dark: bool) -> bool:
    """Evaluate the small media-query subset the README is allowed to use.

    Only ``prefers-color-scheme`` and ``max-width``/``min-width`` joined by
    ``and`` are understood; anything else fails loudly rather than being
    silently treated as matching or non-matching.
    """
    for clause in media.split(" and "):
        feature = MEDIA_FEATURE.match(clause.strip())
        assert feature is not None, media
        name, value = feature["name"], feature["value"].strip()
        if name == "prefers-color-scheme":
            assert value in {"dark", "light"}, media
            if (value == "dark") != dark:
                return False
        elif name in {"max-width", "min-width"}:
            assert value.endswith("px"), media
            limit = int(value[: -len("px")])
            if (name == "max-width" and viewport > limit) or (
                name == "min-width" and viewport < limit
            ):
                return False
        else:
            raise AssertionError(f"unsupported media feature in README: {media}")
    return True


def _selected(picture: _Picture, *, viewport: int, dark: bool) -> str:
    """Asset name a browser picks: the first matching ``<source>``, else the ``<img>``."""
    for media, target in picture.sources:
        if _media_matches(media, viewport=viewport, dark=dark):
            return _local_asset(target).name
    assert picture.fallback is not None
    return _local_asset(picture.fallback).name


def _figure_pictures() -> dict[str, _Picture]:
    blocks = _html_images().picture_blocks
    by_figure: dict[str, _Picture] = {}
    for block in blocks:
        assert block.fallback is not None
        name = _local_asset(block.fallback).name
        if name == DEMO_FILES[0]:
            continue  # the recording has no responsive variants; tested separately
        figure = next(f for f in FIGURES if name == f"{f}-light.svg")
        by_figure[figure] = block
    assert list(by_figure) == list(FIGURES), list(by_figure)
    return by_figure


def _demo_picture() -> _Picture:
    blocks = [
        b
        for b in _html_images().picture_blocks
        if b.fallback is not None and _local_asset(b.fallback).name == DEMO_FILES[0]
    ]
    assert len(blocks) == 1, "exactly one demo recording <picture>"
    return blocks[0]


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
    assert html.pictures == 4  # hero, how-it-works, architecture, demo recording
    for target, markdown_alt in markdown:
        assert target.startswith("https://"), target
        assert markdown_alt.strip(), target
    for target, html_alt in html.images:
        assert target.startswith("https://"), target
        if html_alt is not None:
            assert html_alt.strip(), target
    assert sum(1 for _, html_alt in html.images if html_alt is not None) == 4


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
    for figure in FIGURES:
        assert [n for n in names if n.startswith(figure)] == [
            f"{figure}-mobile-dark.svg",
            f"{figure}-mobile-light.svg",
            f"{figure}-dark.svg",
            f"{figure}-light.svg",
        ], figure


# --------------------------------------------------------------------------- #
# Responsive selection at real GitHub widths (review 13, V1-051)
# --------------------------------------------------------------------------- #


def test_every_picture_uses_the_measured_breakpoint_with_dark_before_light() -> None:
    """Source order is what a browser evaluates: dark+mobile, mobile, dark, then the light img.

    A ``<picture>`` takes the first ``<source>`` whose media query matches, so
    the dark mobile row must precede the scheme-agnostic mobile row and the
    dark desktop row must precede the light ``<img>`` fallback. Every width
    clause must be the single measured breakpoint; the historical 600 px
    switch left 800 to 1200 px windows on undersized desktop canvases.
    """
    for figure, picture in _figure_pictures().items():
        assert [(media, _local_asset(target).name) for media, target in picture.sources] == [
            (f"(prefers-color-scheme: dark) and {MOBILE_MEDIA}", f"{figure}-mobile-dark.svg"),
            (MOBILE_MEDIA, f"{figure}-mobile-light.svg"),
            ("(prefers-color-scheme: dark)", f"{figure}-dark.svg"),
        ], figure
        assert picture.fallback is not None
        assert _local_asset(picture.fallback).name == f"{figure}-light.svg"
    assert "600px" not in _text()


def test_viewports_below_1280_select_the_vertical_variants() -> None:
    """320 to 1279 px viewports (254 to under 838 px images) get the mobile files, both schemes."""
    for figure, picture in _figure_pictures().items():
        for viewport in MOBILE_VIEWPORTS:
            assert (
                _selected(picture, viewport=viewport, dark=True) == f"{figure}-mobile-dark.svg"
            ), (
                figure,
                viewport,
            )
            assert (
                _selected(picture, viewport=viewport, dark=False) == f"{figure}-mobile-light.svg"
            ), (
                figure,
                viewport,
            )


def test_viewports_at_1280_and_above_select_the_desktop_variants() -> None:
    """1280 and 1366 px viewports render the README image at 838 px and get the desktop files."""
    for figure, picture in _figure_pictures().items():
        for viewport in DESKTOP_VIEWPORTS:
            assert _selected(picture, viewport=viewport, dark=True) == f"{figure}-dark.svg", (
                figure,
                viewport,
            )
            assert _selected(picture, viewport=viewport, dark=False) == f"{figure}-light.svg", (
                figure,
                viewport,
            )


def test_breakpoint_change_kept_every_picture_full_width_without_new_paths() -> None:
    """The responsive fix changes media queries only: same four files per figure, same width."""
    text = _text()
    assert text.count('width="100%"') == 4  # three figures plus the demo recording
    referenced = {_local_asset(t).name for t, _ in _html_images().images if not _is_badge(t)}
    assert referenced == {
        f"{figure}{variant}.svg"
        for figure in FIGURES
        for variant in ("-light", "-dark", "-mobile-light", "-mobile-dark")
    } | set(DEMO_FILES)


# --------------------------------------------------------------------------- #
# Genuine post-publication demo recording (Task 14 capture, Task 21 integration)
# --------------------------------------------------------------------------- #


def test_demo_recording_sits_below_the_frozen_opening_with_dark_before_light() -> None:
    """The recording is added after the navigation table and never touches the first screen.

    Decision 2A captures the recording from the published PyPI release, so it
    is absent from the tagged tree; the README integrates it below the frozen
    opening sequence (hero, description, badges, how-it-works, quickstart,
    guarantees, limits, architecture, navigation table). One GIF per colour
    scheme, dark ``<source>`` first, light ``<img>`` fallback, no responsive
    width variants, and alt text that states the three exits.
    """
    text = _text()
    links = text.index("docs/stability.md")
    demo = text.index(DEMO_FILES[0])
    assert links < demo < text.index("## Read a result")
    assert text.index("## Watch the recorded demo") < demo
    picture = _demo_picture()
    assert [(media, _local_asset(target).name) for media, target in picture.sources] == [
        ("(prefers-color-scheme: dark)", "demo-dark.gif"),
    ]
    assert picture.fallback is not None
    assert _local_asset(picture.fallback).name == "demo-light.gif"
    alt = next(alt for target, alt in _html_images().images if DEMO_FILES[0] in target)
    assert alt is not None
    for phrase in ("quickstart commands", "PyPI", "1.0.0", "exits 0", "exits 1", "BLOCK", "PASS"):
        assert phrase in alt, phrase
    prose = re.sub(r"\s+", " ", text)
    assert "it is not authenticated model evidence" in prose
    assert "do not contain it" in prose  # absent from the tag and the PyPI page (Decision 2A)
