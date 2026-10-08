"""README composition and image validation.

The opening order and copy follow the result-first editorial amendment
(plan/v1/CHANGE_LOG.md V1-058), which superseded the 2026-10-08 hero-first
opening: the title, the tagline, the ticket-router problem, the recorded Jev
audit with its audit link, the execution and authenticity boundary and the
engineering strip come first, verbatim; then the evidence-card hero, the
badges, the three commands, a selected excerpt of real demo output, the exit
sentence and three links. The application example with its real-world-use
block, the workflow summary, result reading, guarantees and limits, the
architecture summary, the recording, the documentation table, related
projects and the development notes follow. The how-it-works and architecture
figures are linked, not embedded.

Every image in README.md, including each ``<source srcset>`` and ``<img src>``
inside ``<picture>`` markup, must be an absolute same-repository URL that maps
to an existing, declared, implemented asset under ``docs/assets``. There is no
HTTP fetch, no skip and no xfail: a figure whose files are not committed fails
here, by design. Badges from the explicit allowlist are exempt from the file
check only.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

from docs.conftest import ROOT, fences

README = ROOT / "README.md"
ASSETS = ROOT / "docs" / "assets"
AUDIT = ROOT / "docs" / "results" / "jev-audit-2026-10-08"
REPO = "ajaysurya1221/actseal"
RAW_PREFIX = f"https://raw.githubusercontent.com/{REPO}/main/"
BLOB_PREFIX = f"https://github.com/{REPO}/blob/main/"
TREE_PREFIX = f"https://github.com/{REPO}/tree/main/"
BADGES = (
    re.compile(r"^https://img\.shields\.io/"),
    re.compile(rf"^https://github\.com/{re.escape(REPO)}/actions/workflows/[^/]+/badge\.svg$"),
)
#: The verbatim opening, title through the engineering strip (V1-058).
OPENING = (
    "# Actseal\n"
    "\n"
    "**Test a model's action policy. Replay the evidence.**\n"
    "\n"
    "A ticket router needs rules for when to act, abstain, escalate or deny.\n"
    "Actseal measures accepted-action errors and coverage under a frozen policy.\n"
    "\n"
    "**Recorded Jev audit: INCONCLUSIVE.**\n"
    "580 of 639 verification cases received ACT; 24 disagreed with benchmark labels.\n"
    "Fixed benchmark; unreleased producer. "
    f"[Audit and offline replay]({BLOB_PREFIX}docs/results/jev-audit-2026-10-08/README.md)\n"
    "\n"
    "**Boundary:** the application owns execution.\n"
    "Replay checks consistency; it does not authenticate responses or prove label truth.\n"
    "\n"
    f"**Engineering:** [20 ADRs]({TREE_PREFIX}docs/decisions) · "
    f"[11 JSON Schemas]({BLOB_PREFIX}docs/schemas/README.md)\n"
    f"[Mutation harness]({BLOB_PREFIX}tools/check_mutations.py) · "
    f"[1.0.0 release receipt]({BLOB_PREFIX}plan/v1/receipts/postpublish-receipt.json)\n"
    "\n"
)
#: The verbatim start of the Try it section: heading, one line, the commands.
TRY_IT = (
    "## Try it\n"
    "\n"
    "Synthetic demo. macOS/Linux + uv; use a new `./actseal-demo` directory.\n"
    "```bash\n"
    "uvx --python 3.12 actseal demo --out ./actseal-demo\n"
    "uvx --offline --python 3.12 actseal replay ./actseal-demo/fixed/evidence\n"
    "uvx --offline --python 3.12 actseal replay ./actseal-demo/bad/evidence\n"
    "```\n"
)
#: The release gate (tools/check_release.py docs) still requires these two;
#: they now lead the How it works section.
FORMER_TAGLINE = "Frozen policy. Measured risk and coverage. Offline replay."
FORMER_WHY = (
    "A model can choose the right label often and still act on the wrong cases. "
    "Actseal checks a frozen action policy against labelled cases, bounds errors "
    "among accepted actions and coverage across all scheduled cases, and saves "
    "evidence for offline replay."
)
HERO_ALT = (
    "Actseal evidence card. Does this frozen action policy meet its declared risk and "
    "coverage limits? Freeze the policy, run it once against labelled cases, bound the "
    "errors among accepted actions, seal the evidence, replay it with no model call. "
    "Preregistered live audit, 639 verification cases, threshold 0.80: ACT 580 of 639, "
    "24 errors; fixed benchmark, unreleased producer; risk [0.0250, 0.0639] against a "
    "limit of 0.05; coverage [0.879, 0.932]; verdict INCONCLUSIVE (exit 2); replay requires "
    "archived producer d3edbab. Source: docs/results/jev-audit-2026-10-08. Neither PASS nor "
    "BLOCK is claimed."
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
#: The opening (title through the three links) must fit in this many lines.
#: It grew from 40 when the recorded audit, boundary and engineering lines
#: moved above the hero (V1-058).
OPENING_LINES = 48
#: The real-world-use block, verbatim, as a quotation in "Use it in an application".
REAL_WORLD = (
    "> **[Before enabling automatic ticket routing]"
    f"({BLOB_PREFIX}examples/action_gate/README.md)**\n"
    ">\n"
    "> Run the committed action-gate example to see the application boundary. It verifies "
    "a frozen policy, replays the recorded evidence, and routes authored tickets. Only ACT "
    "permits the example application\N{RIGHT SINGLE QUOTATION MARK}s local queue write; "
    "ABSTAIN, ESCALATE and DENY take non-execution paths.\n"
    ">\n"
    "> From a development checkout, run "
    "`uv run --frozen python examples/action_gate/run.py --check`.\n"
    ">\n"
    "> This is a synthetic integration example. The application owns execution; the result "
    "is not evidence of deployment performance.\n"
)
#: The maintainer and assistance disclosure, verbatim, under Development.
DISCLOSURE = (
    "Maintained by Ajay Surya Senthilrajan, with AI pair-programming recorded in commit "
    "trailers. See the tests, design records and release evidence linked here."
)
#: The ARCI/Actseal distinction the Related projects paragraph keeps.
COMPARISON = (
    "gates repeated-trial agent regressions, injects faults and reduces failing fault sets; "
    "Actseal checks a frozen categorical policy\N{RIGHT SINGLE QUOTATION MARK}s "
    "accepted-action risk and coverage"
)
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
    (
        "The released 1.0.0 adapter's accepted evidence uses mocked transports; the "
        "separate audit below used an unreleased benchmark producer."
    ),
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
    (
        "A preregistered audit of Jev on a fixed 16-intent Banking77 subset returned "
        "INCONCLUSIVE: 580/639 verification cases received ACT, with 24 accepted errors."
    ),
    "published with the unreleased benchmark producer snapshot identified explicitly",
    (
        "Its offline replay runs with that archived snapshot and exits 2 (INCONCLUSIVE); the "
        "published 1.0.0 package returns ERROR `integrity.lock` for this bundle"
    ),
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
#: The four architecture files stay committed, declared outputs; the README
#: links the two desktop variants (see LINKED_FIGURES below).
ARCHITECTURE_FILES = (
    "architecture-light.svg",
    "architecture-dark.svg",
    "architecture-mobile-light.svg",
    "architecture-mobile-dark.svg",
)
#: Figures with committed variants. Only the hero is embedded as a picture;
#: the README links the how-it-works and architecture desktop files instead
#: (V1-058 cut: their phone legibility remains unresolved, V1-057).
FIGURES = ("hero", "how-it-works", "architecture")
PICTURE_FIGURES = ("hero",)
LINKED_FIGURES = {"how-it-works": "How it works", "architecture": "Architecture"}
#: Every committed variant of each figure, referenced or not.
FIGURE_VARIANTS = ("-light", "-dark", "-mobile-light", "-mobile-dark")
#: The genuine post-publication recording (Task 14, Decision 2A), one GIF per
#: colour scheme, placed after the architecture section and before the
#: documentation table.
DEMO_FILES = ("demo-light.gif", "demo-dark.gif")
#: The only ``<source media>`` Actseal's README policy allows. Live QA of the
#: public page on 2026-10-08 (innerWidth 1920, dark scheme) found the media
#: lists that combined ``prefers-color-scheme`` with ``max-width`` rewritten to
#: the always-true ``(prefers-color-scheme: light),(prefers-color-scheme: dark)``,
#: so every visitor received the first, mobile-dark source upscaled; bare width
#: queries survived that check. The README therefore adopts GitHub's documented
#: colour-scheme pattern: each picture has exactly this one dark ``<source>``
#: and the light ``<img>``, and selection does not depend on the viewport width.
DARK_MEDIA = "(prefers-color-scheme: dark)"
#: Viewports (CSS px) at which selection is checked: phone, tablet and desktop.
VIEWPORTS = (320, 375, 768, 1200, 1279, 1280, 1366, 1920)
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


def _media_matches(media: str, *, dark: bool) -> bool:
    """Evaluate a media query under Actseal's README policy.

    The policy accepts only a single ``prefers-color-scheme`` feature, the
    pattern GitHub documents for colour-scheme images. An ``and`` combination
    or a comma-separated list fails loudly, because the combined colour-scheme
    and width queries were rewritten on the live page; a bare width query also
    fails, by policy, even though bare width queries survived the 2026-10-08
    check, so that figure selection never depends on the viewport width.
    """
    assert " and " not in media, f"combined media in README: {media}"
    assert "," not in media, f"combined media in README: {media}"
    feature = MEDIA_FEATURE.match(media.strip())
    assert feature is not None, media
    name, value = feature["name"], feature["value"].strip()
    assert name == "prefers-color-scheme", f"unsupported media feature in README: {media}"
    assert value in {"dark", "light"}, media
    return (value == "dark") == dark


def _selected(picture: _Picture, *, dark: bool) -> str:
    """Asset name a browser picks: the first matching ``<source>``, else the ``<img>``."""
    for media, target in picture.sources:
        if _media_matches(media, dark=dark):
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
        figure = next(f for f in PICTURE_FIGURES if name == f"{f}-light.svg")
        by_figure[figure] = block
    assert list(by_figure) == list(PICTURE_FIGURES), list(by_figure)
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


def test_opening_is_verbatim_and_result_first() -> None:
    """Title, tagline, problem, recorded audit, boundary and engineering strip open the file."""
    text = _text()
    assert text.startswith(OPENING)
    assert TRY_IT in text
    assert text.count(OPENING) == 1
    # Nothing is drawn before the recorded result; the hero follows the strip.
    assert "<picture>" not in OPENING
    assert text.index("<picture>") == len(OPENING)


def test_opening_puts_the_result_hero_commands_and_excerpt_before_any_explanation() -> None:
    """Opening copy, hero, badges, commands, excerpt and links, then everything else."""
    text = _text()
    audit = text.index("**Recorded Jev audit: INCONCLUSIVE.**")
    boundary = text.index("**Boundary:**")
    engineering = text.index("**Engineering:**")
    hero = text.index("hero-light.svg")
    badges = [m.start() for m in re.finditer(r"\[!\[", text)]
    try_it = text.index("\n## Try it\n")
    quickstart = text.index(QUICKSTART[0])
    excerpt = text.index("```text")
    links = text.index(OPENING_LINKS)
    application = text.index("\n## Use it in an application\n")
    real_world = text.index(REAL_WORLD)
    workflow = text.index("\n## How it works\n")
    result = text.index("\n## Read a result\n")
    guarantees_and_limits = text.index("\n## Guarantees and limits\n")
    guarantees = text.index("**Guarantees**")
    limits = text.index("**Limits**")
    architecture = text.index("\n## Architecture\n")
    demo = text.index(DEMO_FILES[0])
    table = text.index("docs/stability.md")
    related = text.index("\n## Related projects\n")
    development = text.index("\n## Development\n")
    disclosure = text.index(DISCLOSURE)
    contributing = text.index("Contributions: [CONTRIBUTING]")
    assert len(badges) == 4
    assert audit < boundary < engineering < hero < badges[0] < badges[3] < try_it
    assert try_it < quickstart < excerpt < links
    assert links < application < real_world < workflow < result < guarantees_and_limits
    assert guarantees_and_limits < guarantees < limits < architecture < demo < table
    assert table < related < development < disclosure < contributing
    # Only the hero is drawn before the commands, the excerpt and the links.
    assert text[:links].count("<picture>") == 1
    # The whole opening, through the three links, fits in the first 48 lines.
    assert OPENING_LINKS in text.splitlines()[:OPENING_LINES]


def test_opening_audit_lines_match_the_committed_verdict() -> None:
    """The recorded result in the opening is the committed verdict's, word for word."""
    verdict = json.loads((AUDIT / "evidence" / "verdict.json").read_text(encoding="utf-8"))
    assert verdict["status"] == "INCONCLUSIVE"
    opening = OPENING
    assert f"**Recorded Jev audit: {verdict['status']}.**" in opening
    assert (
        f"{verdict['accepted']} of {verdict['total']} verification cases received ACT; "
        f"{verdict['errors']} disagreed with benchmark labels."
    ) in opening
    assert (AUDIT / "README.md").is_file()


def test_engineering_strip_counts_match_the_tree() -> None:
    """The strip's numbers are directory counts, not typed claims."""
    decisions = sorted((ROOT / "docs" / "decisions").glob("[0-9][0-9][0-9][0-9]-*.md"))
    schemas = sorted((ROOT / "docs" / "schemas").glob("*.schema.json"))
    assert len(decisions) == 20
    assert len(schemas) == 11
    assert f"[{len(decisions)} ADRs]({TREE_PREFIX}docs/decisions)" in OPENING
    assert f"[{len(schemas)} JSON Schemas]({BLOB_PREFIX}docs/schemas/README.md)" in OPENING
    for relative in ("tools/check_mutations.py", "plan/v1/receipts/postpublish-receipt.json"):
        assert (ROOT / relative).is_file(), relative
        assert f"({BLOB_PREFIX}{relative})" in OPENING


def test_opening_links_promote_the_application_example() -> None:
    text = _text()
    example = f"{BLOB_PREFIX}examples/action_gate/README.md"
    assert (ROOT / "examples" / "action_gate" / "README.md").is_file()
    assert example in OPENING_LINKS
    section = _section("Use it in an application")
    assert f"[action-gate example]({example})" in section
    assert "The application owns execution." in text


def test_real_world_block_is_verbatim_and_linked_to_the_example() -> None:
    section = _section("Use it in an application")
    assert section.lstrip("\n").startswith(REAL_WORLD)
    assert f"({BLOB_PREFIX}examples/action_gate/README.md)" in REAL_WORLD
    assert (ROOT / "examples" / "action_gate" / "run.py").is_file()
    # The block's command is the one the example's own README documents.
    example = (ROOT / "examples" / "action_gate" / "README.md").read_text(encoding="utf-8")
    assert "uv run --frozen python examples/action_gate/run.py --check" in example


def test_former_opening_lines_lead_the_workflow_section() -> None:
    """The release gate's pinned bold line and description now open How it works."""
    section = _section("How it works")
    assert section.lstrip("\n").startswith(f"**{FORMER_TAGLINE}**\n\n{FORMER_WHY}\n")
    assert _text().count(FORMER_WHY) == 1


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
    assert "The first command downloads the package if needed." in _text()


def test_hero_alt_describes_the_evidence_card_and_the_prose_carries_the_limits() -> None:
    """The alt text states the card's recorded result; the limits stay in the prose."""
    hero_alt = next(alt for target, alt in _html_images().images if "hero-light.svg" in target)
    assert hero_alt == HERO_ALT
    for gone in ("authenticate", "inference", "label truth", "Caption", "loop"):
        assert gone not in hero_alt, gone
    for variant in FIGURE_VARIANTS:
        name = f"hero{variant}.svg"
        svg = (ASSETS / name).read_text(encoding="utf-8")
        assert "Does this frozen action policy meet its declared risk and coverage limits?" in svg
        for number in ("580", "639", "24", "[0.0250, 0.0639]", "[0.879, 0.932]", "INCONCLUSIVE"):
            assert number in svg, (name, number)
        # The standalone card carries the scope and the replay restriction.
        assert "Fixed benchmark; unreleased producer" in svg, name
        assert "replay requires archived producer d3edbab" in svg, name
        assert "replays offline from the sealed bundle" not in svg, name
        assert "Test model-chosen actions" not in svg, name
        assert "Caption" not in svg, name
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
    assert COMPARISON in section
    for repository in RELATED_REPOSITORIES:
        assert f"({repository})" in section, repository


def test_development_section_explains_the_mutation_harness_and_discloses_assistance() -> None:
    """The disclosure sits after the engineering evidence, never in the opening."""
    section = _section("Development")
    assert f"({BLOB_PREFIX}tools/check_mutations.py)" in section
    assert "eight prescribed changes" in section
    assert section.strip().endswith(DISCLOSURE)
    text = _text()
    assert text.count(DISCLOSURE) == 1
    assert DISCLOSURE not in "\n".join(text.splitlines()[:OPENING_LINES])
    assert text.index(DISCLOSURE) > text.index("\n## Related projects\n")
    for absent in ("every line", "badge"):
        assert absent not in section, absent


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
        if target.startswith(TREE_PREFIX):
            relative = target[len(TREE_PREFIX) :].split("#")[0]
            assert ".." not in relative
            assert (ROOT / relative).is_dir(), target


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
    assert html.pictures == 2  # the hero and the demo recording
    for target, markdown_alt in markdown:
        assert target.startswith("https://"), target
        assert markdown_alt.strip(), target
    for target, html_alt in html.images:
        assert target.startswith("https://"), target
        if html_alt is not None:
            assert html_alt.strip(), target
    assert sum(1 for _, html_alt in html.images if html_alt is not None) == 2


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


def _linked_assets() -> set[str]:
    """Names of ``docs/assets`` files the README links (not embeds) through blob URLs."""
    prefix = f"{BLOB_PREFIX}docs/assets/"
    return {
        match["target"][len(prefix) :]
        for match in MARKDOWN_LINK.finditer(_text())
        if match["target"].startswith(prefix)
    }


def test_architecture_filenames_are_the_frozen_four() -> None:
    """All four names stay committed, declared outputs; the README links the desktop two."""
    outputs = _implemented_outputs()
    for name in ARCHITECTURE_FILES:
        assert (ASSETS / name).is_file(), name
        assert name in outputs, name
    embedded = {
        _local_asset(target).name
        for target, _ in _html_images().images
        if not _is_badge(target) and "architecture" in target
    }
    assert embedded == set()
    linked = {name for name in _linked_assets() if name.startswith("architecture")}
    assert linked == {"architecture-light.svg", "architecture-dark.svg"}


def test_workflow_and_architecture_figures_are_linked_not_embedded() -> None:
    """Each section links its figure's desktop files, which are committed implemented outputs."""
    outputs = _implemented_outputs()
    assert _linked_assets() == {
        f"{figure}{variant}.svg" for figure in LINKED_FIGURES for variant in ("-light", "-dark")
    }
    for figure, heading in LINKED_FIGURES.items():
        section = _section(heading)
        assert "<picture>" not in section, heading
        for variant in ("-light", "-dark"):
            name = f"{figure}{variant}.svg"
            assert f"({BLOB_PREFIX}docs/assets/{name})" in section, name
            assert (ASSETS / name).is_file(), name
            assert name in outputs, name
    # The prose keeps what the embedded figures used to say.
    workflow = re.sub(r"\s+", " ", _section("How it works"))
    for stage in ("Freeze", "Run", "Verify", "Seal", "Replay"):
        assert f"**{stage}**" in workflow, stage
    assert "recomputes the verdict offline with no model call" in workflow
    assert "never reaches a provider" in _section("Architecture")


def test_picture_references_desktop_variants_and_keeps_mobile_files_declared() -> None:
    """The hero references dark then light; every figure's variants stay committed and declared."""
    names = [_local_asset(t).name for t, _ in _html_images().images if not _is_badge(t)]
    outputs = _implemented_outputs()
    for figure in PICTURE_FIGURES:
        assert [n for n in names if n.startswith(figure)] == [
            f"{figure}-dark.svg",
            f"{figure}-light.svg",
        ], figure
    for figure in FIGURES:
        for variant in FIGURE_VARIANTS:
            name = f"{figure}{variant}.svg"
            assert (ASSETS / name).is_file(), name
            assert name in outputs, name
    assert "-mobile-" not in _text()


# --------------------------------------------------------------------------- #
# Selection as GitHub serves it (live QA 2026-10-08)
# --------------------------------------------------------------------------- #


def test_every_source_uses_only_the_documented_colour_scheme_query() -> None:
    """One dark ``<source>`` then the light ``<img>`` per picture; no width or combined media.

    On the live page the ``<source media>`` lists that combined
    ``prefers-color-scheme`` with ``max-width`` were rewritten into an
    always-true list, so width-based selection served the first source to
    everyone. Actseal's README policy therefore allows only the documented
    colour-scheme query, and the demo recording follows the same rule.
    """
    for figure, picture in _figure_pictures().items():
        assert [(media, _local_asset(target).name) for media, target in picture.sources] == [
            (DARK_MEDIA, f"{figure}-dark.svg"),
        ], figure
        assert picture.fallback is not None
        assert _local_asset(picture.fallback).name == f"{figure}-light.svg"
    for picture in _html_images().picture_blocks:
        assert [media for media, _ in picture.sources] == [DARK_MEDIA]
    text = _text()
    for width_query in ("max-width", "min-width", "1279px", "600px"):
        assert width_query not in text, width_query


def test_every_viewport_selects_the_desktop_variant_for_its_scheme() -> None:
    """Selection depends on the colour scheme only, at phone, tablet and desktop widths."""
    for figure, picture in _figure_pictures().items():
        for viewport in VIEWPORTS:
            # The media queries carry no width feature, so the viewport cannot
            # change the choice; it is iterated to state the intent explicitly.
            assert _selected(picture, dark=True) == f"{figure}-dark.svg", (figure, viewport)
            assert _selected(picture, dark=False) == f"{figure}-light.svg", (figure, viewport)


def test_combined_and_width_media_queries_are_rejected_by_the_policy_model() -> None:
    """The rewritten combined forms and, by policy, a bare width query must fail here."""
    for media in (
        f"{DARK_MEDIA} and (max-width: 1279px)",
        "(max-width: 1279px)",
        "(prefers-color-scheme: light),(prefers-color-scheme: dark)",
    ):
        with pytest.raises(AssertionError, match=r"combined media|unsupported media feature"):
            _media_matches(media, dark=True)
    assert _media_matches(DARK_MEDIA, dark=True)
    assert not _media_matches(DARK_MEDIA, dark=False)


def test_every_picture_stays_full_width_with_two_files_per_picture() -> None:
    """The hero and the recording, each full width, two files each."""
    text = _text()
    assert text.count('width="100%"') == 2  # the hero plus the demo recording
    referenced = {_local_asset(t).name for t, _ in _html_images().images if not _is_badge(t)}
    assert referenced == {
        f"{figure}{variant}.svg" for figure in PICTURE_FIGURES for variant in ("-light", "-dark")
    } | set(DEMO_FILES)


# --------------------------------------------------------------------------- #
# Genuine post-publication demo recording (Task 14 capture, Task 21 integration)
# --------------------------------------------------------------------------- #


def test_demo_recording_sits_below_the_opening_with_dark_before_light() -> None:
    """The recording follows the architecture section and never touches the first screen.

    Decision 2A captures the recording from the published PyPI release, so it
    is absent from the tagged tree; the README places it after the guarantees,
    limits and architecture section and before the documentation table. One
    GIF per colour scheme, dark ``<source>`` first, light ``<img>`` fallback, no
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
    # Absent from the v1.0.0 tag and that version's PyPI page (Decision 2A).
    assert "is absent from the immutable v1.0.0 tag and that version's PyPI description" in prose
