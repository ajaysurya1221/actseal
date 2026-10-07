"""README composition and image validation.

The opening order and copy follow the 2026-10-08 editorial review, which
superseded the PLAN section D opening: compact hero, the bold line and one
paragraph on why, badges, the three commands, a selected excerpt of real demo
output and three links come first; the workflow figure, guarantees and limits,
architecture, recording, documentation table and related projects follow.

Every image in README.md, including each ``<source srcset>`` and ``<img src>``
inside ``<picture>`` markup, must be an absolute same-repository URL that maps
to an existing, declared, implemented asset under ``docs/assets``. There is no
HTTP fetch, no skip and no xfail: a figure whose files are not committed yet
(the architecture figure until Task 13 landed; the demo recording until the
Task 14 activation lands) fails here, by design. Badges from the explicit
allowlist are exempt from the file check only.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
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
TAGLINE = "Frozen policy. Measured risk and coverage. Offline replay."
WHY = (
    "A model can choose the right label often and still act on the wrong cases. "
    "Actseal checks a frozen action policy against labelled cases, bounds errors "
    "among accepted actions and coverage across all scheduled cases, and saves "
    "evidence for offline replay."
)
HERO_ALT = (
    "Actseal. Test model-chosen actions. Replay the evidence. Three steps: freeze, run, replay."
)
EXCERPT_INTRO = "Expected result from synthetic fixtures, showing selected output:"
EXIT_SUMMARY = (
    "Demo exit: `{demo}`. Fixed replay: `{fixed_status}` / `{fixed}`. "
    "Bad replay: `{bad_status}` / `{bad}`."
)
OPENING_LINKS = (
    f"[Use it in an application]({BLOB_PREFIX}examples/action_gate/README.md) · "
    f"[Read the limits]({BLOB_PREFIX}docs/threat-model.md) · "
    f"[Quickstart]({BLOB_PREFIX}docs/quickstart.md)"
)
#: The opening (hero through the three links) must fit in this many lines.
OPENING_LINES = 40
#: The retained raw recording; the excerpt's lines must be lines of its output.
CAST = ASSETS / "src" / "demo.cast"
#: Limit and scope statements carried over from the earlier README; each must
#: survive somewhere in the prose (compared with whitespace collapsed).
SURVIVING_STATEMENTS = (
    "The third command intentionally exits 1.",
    "Windows is unsupported.",
    (
        "The Jev adapter is PROVISIONAL and requires explicit opt-in: "
        "`--provider jev --experimental-provider`. It has no 1.x compatibility promise."
    ),
    "no live audit result is accepted",
    "Replay never imports a provider",
    "the packaged demonstration establishes no population or model-quality result",
    "The packaged demo and action-gate example are synthetic (`evidence_scope=demo`).",
    (
        "Population interpretation requires independent cases and one prespecified attempt "
        "under a fixed policy. Do not retry until PASS."
    ),
    (
        "Actseal supports one categorical question with 2\N{EN DASH}16 labels and a frozen "
        "allowlist and threshold."
    ),
    (
        "The runtime core uses only the Python standard library on Python 3.12 and 3.13, "
        "macOS and Linux."
    ),
    "Native Laya support is limited to the documented tested CPU configurations.",
    "it does not execute, intercept or enforce the application's action",
    "it is not a statement that the answer is correct",
    "it never relabels the bad run",
    "it is not authenticated model evidence",
)
RELATED_REPOSITORIES = (
    "https://github.com/ajaysurya1221/agent-reliability-ci",
    "https://github.com/ajaysurya1221/frontier-scout",
    "https://github.com/ajaysurya1221/dorian",
    "https://github.com/ajaysurya1221/evalopt-graph",
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
#: colour scheme, placed after the architecture figure and before the
#: documentation table.
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
    """Outputs of implemented assets, read from the committed inventory source.

    Only ``Asset`` blocks that bind a ``renderer=`` count. Literal output names
    are read from the block; the activated ``demo`` asset declares its two GIFs
    through ``demo.THEMES``, whose names are the literal ``LIGHT_OUTPUT`` and
    ``DARK_OUTPUT`` constants in ``demo.py``. Planned assets still contribute
    nothing, so a README reference to one still fails.
    """
    src = ASSETS / "src" / "actseal_assets"
    inventory = (src / "inventory.py").read_text(encoding="utf-8")
    outputs: set[str] = set()
    for block in re.split(r"\n    Asset\(", inventory)[1:]:
        if "renderer=" not in block:
            continue
        outputs.update(re.findall(r"\"([A-Za-z0-9-]+\.(?:svg|png|gif))\"", block))
        if "for name in demo.THEMES" in block:
            demo = (src / "demo.py").read_text(encoding="utf-8")
            outputs.update(
                re.findall(r"^(?:LIGHT|DARK)_OUTPUT = \"([A-Za-z0-9-]+\.gif)\"$", demo, re.M)
            )
    return outputs


# --------------------------------------------------------------------------- #
# Opening order and approved copy
# --------------------------------------------------------------------------- #


def _prose() -> str:
    """README text outside ``<picture>`` blocks, with whitespace collapsed."""
    without_pictures = re.sub(r"<picture>.*?</picture>", " ", _text(), flags=re.DOTALL)
    return re.sub(r"\s+", " ", without_pictures)


def _section(heading: str) -> str:
    """Body of the ``## heading`` section up to the next second-level heading."""
    text = _text()
    start = text.index(f"\n## {heading}\n") + len(f"\n## {heading}\n")
    end = text.find("\n## ", start)
    return text[start:] if end == -1 else text[start:end]


def _excerpt() -> list[str]:
    """Lines of the first ``text`` fence: the selected demo output."""
    blocks = fences(README, "text")
    assert blocks, "README must show a selected excerpt of the demo output"
    return blocks[0].strip().splitlines()


def _cast_output_lines() -> list[str]:
    """Every terminal output line of the retained raw recording, in order."""
    rows = CAST.read_text(encoding="utf-8").splitlines()
    header = json.loads(rows[0])
    assert isinstance(header, dict)
    assert header["version"] == 3
    output = ""
    for row in rows[1:]:
        event = json.loads(row)
        if event[1] == "o":
            output += event[2]
    return [line.rstrip("\r") for line in output.split("\n")]


def _appear_in_order(lines: list[str], wanted: list[str]) -> bool:
    """Whether every ``wanted`` line is a whole line of ``lines``, in the same order."""
    position = 0
    for line in wanted:
        if line not in lines[position:]:
            return False
        position = lines.index(line, position) + 1
    return True


def _run_actseal(arguments: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed interpreter and literal arguments
        [sys.executable, "-m", "actseal", *arguments],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


def test_opening_puts_commands_and_a_result_before_any_explanatory_figure() -> None:
    """Hero, bold line, why, badges, commands, excerpt and links, then everything else."""
    text = _text()
    hero = text.index("hero-light.svg")
    tagline = text.index(f"**{TAGLINE}**")
    why = text.index(WHY)
    badges = [m.start() for m in re.finditer(r"\[!\[", text)]
    try_it = text.index("\n## Try it\n")
    quickstart = text.index(QUICKSTART[0])
    excerpt = text.index("```text")
    links = text.index(OPENING_LINKS)
    application = text.index("\n## Use it in an application\n")
    workflow = text.index("how-it-works-light.svg")
    result = text.index("\n## Read a result\n")
    guarantees_and_limits = text.index("\n## Guarantees and limits\n")
    guarantees = text.index("**Guarantees**")
    limits = text.index("**Limits**")
    architecture = text.index("architecture-light.svg")
    demo = text.index(DEMO_FILES[0])
    table = text.index("docs/stability.md")
    related = text.index("\n## Related projects\n")
    contributing = text.index("Contributions: [CONTRIBUTING]")
    assert len(badges) == 4
    assert hero < tagline < why < badges[0] < badges[3] < try_it < quickstart < excerpt < links
    assert links < application < workflow < result < guarantees_and_limits < guarantees < limits
    assert limits < architecture < demo < table < related < contributing
    # Nothing but the hero is drawn before the commands, the excerpt and the links.
    assert text[:links].count("<picture>") == 1
    # The whole opening, through the three links, fits in the first 40 lines.
    assert OPENING_LINKS in text.splitlines()[:OPENING_LINES]
    assert text.count(WHY) == 1


def test_opening_links_promote_the_application_example() -> None:
    text = _text()
    example = f"{BLOB_PREFIX}examples/action_gate/README.md"
    assert (ROOT / "examples" / "action_gate" / "README.md").is_file()
    assert example in OPENING_LINKS
    assert f"[action-gate example]({example})" in _section("Use it in an application")
    assert "The application owns execution." in text


def test_excerpt_is_selected_output_of_the_retained_recording() -> None:
    """Each excerpt line is a whole line the recorded demo printed, in the printed order."""
    text = _text()
    excerpt = _excerpt()
    assert excerpt == [
        "[bad] expected BLOCK, observed BLOCK, replay BLOCK (match)",
        "[fixed] expected PASS, observed PASS, replay PASS (match)",
        "result: success",
    ]
    assert text.index(EXCERPT_INTRO) < text.index("```text") < text.index(OPENING_LINKS)
    assert "selected output" in EXCERPT_INTRO  # the excerpt is labelled as a selection
    assert _appear_in_order(_cast_output_lines(), excerpt)


def test_excerpt_and_exit_summary_match_executable_demo_behaviour(task_tmpdir: Path) -> None:
    """The checked-out package prints the excerpt and the stated exits and statuses.

    This runs the three command shapes through ``python -m actseal`` from the
    locked environment, not the PyPI release the ``uvx`` commands resolve.
    """
    demo = _run_actseal(["demo", "--out", "./actseal-demo"], task_tmpdir)
    assert demo.returncode == 0, demo.stderr
    assert _appear_in_order(demo.stdout.splitlines(), _excerpt())
    observed: dict[str, object] = {"demo": demo.returncode}
    for run in ("fixed", "bad"):
        replay = _run_actseal(["replay", f"./actseal-demo/{run}/evidence", "--json"], task_tmpdir)
        receipt = json.loads(replay.stdout)
        assert receipt["exit_code"] == replay.returncode
        observed[run] = replay.returncode
        observed[f"{run}_status"] = receipt["status"]
    summary = EXIT_SUMMARY.format(**observed)
    assert summary == EXIT_SUMMARY.format(
        demo=0, fixed_status="PASS", fixed=0, bad_status="BLOCK", bad=1
    )
    assert summary in _text()


def test_hero_alt_describes_the_artwork_and_the_prose_carries_the_limits() -> None:
    """The caption left the artwork; its three limits must stay in the README prose."""
    hero_alt = next(alt for target, alt in _html_images().images if "hero-light.svg" in target)
    assert hero_alt == HERO_ALT
    for gone in ("authenticate", "inference", "label truth", "Caption", "loop"):
        assert gone not in hero_alt, gone
    for variant in ("-light", "-dark", "-mobile-light", "-mobile-dark"):
        name = f"hero{variant}.svg"
        svg = (ASSETS / name).read_text(encoding="utf-8")
        assert "Test model-chosen actions. Replay the evidence." in svg, name
        assert "Replay cannot authenticate" not in svg, name
        assert "Caption" not in svg, name
        for step in ("freeze", "run", "replay"):
            assert step in svg, (name, step)
    prose = _prose()
    for limit in (
        "cannot authenticate coherently rewritten responses",
        "cannot prove inference occurred",
        "that labels are true",
    ):
        assert limit in prose, limit


def test_scope_and_limit_statements_survive_in_the_prose() -> None:
    prose = _prose()
    for statement in SURVIVING_STATEMENTS:
        assert statement in prose, statement


def test_related_projects_are_three_sentences_naming_four_repositories() -> None:
    section = _section("Related projects").strip()
    assert "\n\n" not in section  # one paragraph
    # A sentence ends at a full stop followed by whitespace or the end; the
    # dots inside link targets are followed by other characters.
    assert len(re.findall(r"\.(?=\s|$)", section)) == 3, section
    assert section.endswith("against supplied evidence.")
    for repository in RELATED_REPOSITORIES:
        assert f"({repository})" in section, repository


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


def test_demo_recording_sits_below_the_opening_with_dark_before_light() -> None:
    """The recording follows the architecture figure and never touches the first screen.

    Decision 2A captures the recording from the published PyPI release, so it
    is absent from the tagged tree; the README places it after the guarantees,
    limits and architecture figure and before the documentation table. One GIF
    per colour scheme, dark ``<source>`` first, light ``<img>`` fallback, no
    responsive width variants, and alt text that states the three exits.
    """
    text = _text()
    demo = text.index(DEMO_FILES[0])
    assert text.index(OPENING_LINKS) < text.index("**Limits**") < demo
    assert text.index("architecture-light.svg") < demo < text.index("docs/stability.md")
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
