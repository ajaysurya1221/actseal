"""README v2 composition, executable commands and image validation.

The release-preparation brief puts the synthetic qualification demo, recorded
predictions, sample-size planner and Action before the recorded Jev result.
Historical evidence retains its numbers, provenance and limits. Commands are
extracted from the README and executed with the checked-out interpreter;
these tests do not claim PyPI installation or hosted Action execution.

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
import shlex
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
#: The v2 brief's one-sentence opening.
OPENING = (
    "# Actseal\n"
    "\n"
    "Actseal tells you how much of a categorical decision a model can make alone at your "
    "error limit, with evidence anyone can replay offline.\n"
    "\n"
)
ENGINEERING = (
    f"**Engineering:** [20 ADRs]({TREE_PREFIX}docs/decisions) · "
    f"[16 JSON Schemas]({BLOB_PREFIX}docs/schemas/README.md)\n"
    f"[Mutation harness]({BLOB_PREFIX}tools/check_mutations.py) · "
    f"[1.0.1 release receipt]({BLOB_PREFIX}plan/v1/releases/1.0.1/postpublish-receipt.json)\n"
    "\n"
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
    "limit of 0.05; coverage [0.879, 0.932]; verdict INCONCLUSIVE (exit 2); replay with "
    "packaged registry. Source: docs/results/jev-audit-2026-10-08. Neither PASS nor "
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
#: The synthetic qualification command must appear on the first screen.
OPENING_LINES = 25
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
        "`--provider jev --experimental-provider`. It has no stable compatibility promise."
    ),
    (
        "The released 1.0.0 adapter's accepted evidence uses mocked transports; the "
        "historical audit used an unreleased benchmark producer."
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
        "Its offline replay runs with the packaged registry and exits 2 (INCONCLUSIVE); the "
        "published 1.0.0 and 1.0.1 packages do not approve this producer in their "
        "compatibility registries"
    ),
)
RELATED_REPOSITORIES = (
    "https://github.com/ajaysurya1221/agent-reliability-ci",
    "https://github.com/ajaysurya1221/frontier-scout",
    "https://github.com/ajaysurya1221/dorian",
    "https://github.com/ajaysurya1221/evalopt-graph",
)
QUICKSTART = [
    "uv run --frozen actseal demo --qualify --out ./actseal-qualified-demo",
    "uv run --frozen actseal report ./actseal-qualified-demo --out ./actseal-report",
    "uv run --frozen actseal replay-selection ./actseal-qualified-demo/calibration",
    "uv run --frozen actseal replay ./actseal-qualified-demo/evidence",
]
LEGACY_QUICKSTART = [
    "uvx --python 3.12 actseal demo --out ./actseal-demo",
    "uvx --offline --python 3.12 actseal replay ./actseal-demo/fixed/evidence",
    "uvx --offline --python 3.12 actseal replay ./actseal-demo/bad/evidence",
]
CHECKS = [
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


def _bash_commands() -> list[str]:
    return [
        line.strip()
        for block in fences(README, "bash")
        for line in block.replace("\\\n", " ").splitlines()
        if line.strip()
    ]


def _documented_arguments(command: str) -> list[str]:
    """Replace only the environment launcher; preserve every documented CLI flag."""
    words = shlex.split(command)
    if words[:4] == ["uv", "run", "--frozen", "actseal"]:
        return words[4:]
    if words[:4] == ["uvx", "--python", "3.12", "actseal"]:
        return words[4:]
    assert words[:5] == ["uvx", "--offline", "--python", "3.12", "actseal"], command
    return words[5:]


def _run_documented(
    command: str, cwd: Path, *, json_output: bool = False
) -> subprocess.CompletedProcess[str]:
    arguments = _documented_arguments(command)
    if json_output and "--json" not in arguments:
        arguments.append("--json")
    return _run_actseal(arguments, cwd)


def _recorded_inputs(directory: Path) -> None:
    """Supply complete synthetic splits containing every verbatim JSONL example row."""
    packaged = ROOT / "src" / "actseal" / "demo_data"
    (directory / "contract.toml").write_bytes((packaged / "qualify.toml").read_bytes())
    blocks = fences(README, "jsonl")
    assert len(blocks) == 1
    shown = [json.loads(line) for line in blocks[0].splitlines() if line]
    assert len(shown) == 3
    assert all(set(row) == {"case_id", "choice", "score"} for row in shown)
    overrides = {row["case_id"]: row for row in shown}
    predictions: list[dict[str, object]] = []
    for split, prefix, count in (("calibration", "cal", 64), ("verification", "verify", 100)):
        cases: list[dict[str, str]] = []
        for number in range(1, count + 1):
            case_id = f"{prefix}-{number:03d}"
            prediction = overrides.get(
                case_id, {"case_id": case_id, "choice": "accept", "score": 0.95}
            )
            predictions.append(prediction)
            cases.append(
                {
                    "case_id": case_id,
                    "state": f"Synthetic README {split} case {number}.",
                    "expected_label": str(prediction["choice"]),
                }
            )
        (directory / f"{split}.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in cases), encoding="utf-8"
        )
    assert all(row in predictions for row in shown)
    (directory / "predictions.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in predictions), encoding="utf-8"
    )


def test_all_readme_shell_commands_have_executable_coverage() -> None:
    """Fail on any added command until its execution path is assigned below."""
    commands = _bash_commands()
    assert len(commands) == 10
    assert [_documented_arguments(command)[0] for command in commands] == [
        "demo",
        "report",
        "replay-selection",
        "replay",
        "qualify",
        "plan",
        "replay",
        "demo",
        "replay",
        "replay",
    ]
    inline = re.findall(r"`(uv(?:x)? [^`\n]+)`", _text())
    assert inline == ["uv run --frozen python examples/action_gate/run.py --check"]


def test_synthetic_qualification_quickstart_executes(task_tmpdir: Path) -> None:
    commands = _bash_commands()[:4]
    assert commands == QUICKSTART
    receipts = []
    for command in commands:
        process = _run_documented(command, task_tmpdir, json_output=True)
        assert process.returncode == 0, (command, process.stdout, process.stderr)
        receipts.append(json.loads(process.stdout))
    assert receipts[0]["status"] == "PASS"
    assert receipts[0]["selection"]["threshold"] == 0.95
    assert receipts[2]["status"] == "SELECTED"
    assert receipts[3]["status"] == "PASS"
    for name in ("report.html", "report.md", "badge.json"):
        assert (task_tmpdir / "actseal-report" / name).is_file()


def test_recorded_qualify_command_and_jsonl_execute(task_tmpdir: Path) -> None:
    _recorded_inputs(task_tmpdir)
    process = _run_documented(_bash_commands()[4], task_tmpdir, json_output=True)
    assert process.returncode == 0, (process.stdout, process.stderr)
    receipt = json.loads(process.stdout)
    assert receipt["status"] == "PASS"
    assert receipt["verdict"]["total"] == 100
    lock = json.loads((task_tmpdir / "qualification" / "lock.json").read_text())
    assert lock["model_identity"]["provider"] == "recorded"
    assert lock["model_identity"]["model"] == "my-model"
    assert lock["model_identity"]["revision"] == "my-revision"
    assert "recorded: provider faults not tested" in (process.stdout + process.stderr)


def test_readme_planner_command_collects_nothing(task_tmpdir: Path) -> None:
    process = _run_documented(_bash_commands()[5], task_tmpdir, json_output=True)
    assert process.returncode == 0, (process.stdout, process.stderr)
    receipt = json.loads(process.stdout)
    assert receipt["status"] == "PLANNED"
    assert receipt["verification_cases"] > 0
    assert list(task_tmpdir.iterdir()) == []


def test_readme_audit_replay_uses_packaged_registry() -> None:
    process = _run_documented(_bash_commands()[6], ROOT, json_output=True)
    assert process.returncode == 2, (process.stdout, process.stderr)
    receipt = json.loads(process.stdout)
    verdict = json.loads((AUDIT / "evidence" / "verdict.json").read_text())
    assert receipt["status"] == verdict["status"] == "INCONCLUSIVE"
    for key in ("total", "accepted", "errors", "risk", "coverage"):
        assert receipt[key] == verdict[key]


def test_readme_action_arguments_execute_locally(task_tmpdir: Path) -> None:
    """Exercise the literal YAML argv; this is not a hosted runner claim."""
    _recorded_inputs(task_tmpdir)
    blocks = fences(README, "yaml")
    assert len(blocks) == 1
    block = blocks[0]
    assert "source: checkout" in block
    mode = re.search(r"^\s+mode: (\S+)\s*$", block, re.MULTILINE)
    assert mode is not None
    folded = re.search(r"^\s+args: >-\n(?P<lines>(?: +[^\n]+\n)+)", block, re.MULTILINE)
    assert folded is not None
    arguments = shlex.split(" ".join(line.strip() for line in folded["lines"].splitlines()))
    process = _run_actseal([mode[1], *arguments, "--json"], task_tmpdir)
    assert process.returncode == 0, (process.stdout, process.stderr)
    assert json.loads(process.stdout)["status"] == "PASS"
    assert (task_tmpdir / "ci-qualification" / "evidence" / "verdict.json").is_file()


def test_readme_application_example_command_executes() -> None:
    command = re.findall(r"`(uv run --frozen python [^`\n]+)`", _text())
    assert len(command) == 1
    words = shlex.split(command[0])
    process = subprocess.run(  # noqa: S603 - documented local script, fixed interpreter
        [sys.executable, *words[4:]],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert process.returncode == 0, (process.stdout, process.stderr)


def test_v2_pass_scope_and_provider_limits_are_explicit() -> None:
    section = re.sub(r"\s+", " ", _section("What a PASS means / does not mean"))
    for phrase in (
        "Selection is pre-registered",
        "separate verification cases",
        "alpha/4",
        "recorded predictions do not test provider faults",
        "label truth",
        "deployment",
    ):
        assert phrase in section
    providers = _section("Works with")
    for provider in ("fixture", "recorded", "laya", "jev", "decision-api"):
        assert f"| `{provider}` |" in providers
    assert "any model" in providers
    assert "optional extra" in providers
    assert providers.count("PROVISIONAL") == 2
    assert "No live decision-api server was verified in this release" in providers
    for word in ("guaranteed", "certified", "safe", "best"):
        assert re.search(rf"\b{word}\b", _text(), re.IGNORECASE) is None


def test_opening_is_verbatim_and_qualification_first() -> None:
    """The brief's sentence and a runnable synthetic command lead the v2 README."""
    text = _text()
    assert text.startswith(OPENING)
    assert text.count(OPENING) == 1
    assert text.count(ENGINEERING) == 1
    assert QUICKSTART[0] in text.splitlines()[:OPENING_LINES]
    assert "synthetic" in _section("60-second quickstart (synthetic)").lower()
    assert "2.0.0 is unreleased" in text


def test_opening_orders_demo_recorded_planner_action_then_scoped_evidence() -> None:
    """The requested learning path precedes the historical audit and reference sections."""
    text = _text()
    audit = text.index("**Recorded Jev audit: INCONCLUSIVE.**")
    engineering = text.index("**Engineering:**")
    hero = text.index("hero-light.svg")
    badges = [m.start() for m in re.finditer(r"\[!\[", text)]
    try_it = text.index("\n## 60-second quickstart (synthetic)\n")
    quickstart = text.index(QUICKSTART[0])
    links = text.index(OPENING_LINKS)
    recorded = text.index("\n## Bring your own predictions\n")
    planner = text.index("\n## Plan before collecting cases\n")
    action = text.index("\n## GitHub Action\n")
    meaning = text.index("\n## What a PASS means / does not mean\n")
    providers = text.index("\n## Works with\n")
    application = text.index("\n## Use it in an application\n")
    real_world = text.index(REAL_WORLD)
    workflow = text.index("\n## How it works\n")
    result = text.index("\n## Read a result\n")
    evidence_and_limits = text.index("\n## Evidence and limits\n")
    checks = text.index("**Checks**")
    limits = text.index("**Limits**")
    architecture = text.index("\n## Architecture\n")
    demo = text.index(DEMO_FILES[0])
    table = text.index("docs/stability.md")
    related = text.index("\n## Related projects\n")
    development = text.index("\n## Development\n")
    disclosure = text.index(DISCLOSURE)
    contributing = text.index("Contributions: [CONTRIBUTING]")
    assert len(badges) == 4
    assert engineering < badges[0] < badges[3] < try_it < quickstart < links
    assert links < recorded < planner < action < meaning < providers < audit < hero
    assert hero < application < real_world < workflow < result < evidence_and_limits
    assert evidence_and_limits < checks < limits < architecture < demo < table
    assert table < related < development < disclosure < contributing
    assert "<picture>" not in text[:quickstart]


def test_recorded_audit_lines_match_the_committed_verdict() -> None:
    """The real-data result retains the committed verdict's counts and provenance."""
    verdict = json.loads((AUDIT / "evidence" / "verdict.json").read_text(encoding="utf-8"))
    assert verdict["status"] == "INCONCLUSIVE"
    opening = _section("Recorded real-data example")
    assert f"**Recorded Jev audit: {verdict['status']}.**" in opening
    assert (
        f"{verdict['accepted']} of {verdict['total']} verification cases received ACT; "
        f"{verdict['errors']} disagreed with benchmark labels."
    ) in opening
    for interval in ("risk", "coverage"):
        values = verdict[interval]
        assert f"[{values['lower']}, {values['upper']}]" in opening
    assert "Fixed benchmark; unreleased producer" in opening
    assert "unreleased producer `d3edbab`" in opening
    assert "Its offline replay runs with that archived snapshot" not in _text()
    assert "replay requires archived producer" not in _text()
    assert (AUDIT / "README.md").is_file()


def test_engineering_strip_counts_match_the_tree() -> None:
    """The strip's numbers are directory counts, not typed claims."""
    decisions = sorted((ROOT / "docs" / "decisions").glob("[0-9][0-9][0-9][0-9]-*.md"))
    schemas = sorted((ROOT / "docs" / "schemas").glob("*.schema.json"))
    assert len(decisions) == 20
    assert len(schemas) == 16
    assert f"[{len(decisions)} ADRs]({TREE_PREFIX}docs/decisions)" in ENGINEERING
    assert f"[{len(schemas)} JSON Schemas]({BLOB_PREFIX}docs/schemas/README.md)" in ENGINEERING
    for relative in ("tools/check_mutations.py", "plan/v1/releases/1.0.1/postpublish-receipt.json"):
        assert (ROOT / relative).is_file(), relative
        assert f"({BLOB_PREFIX}{relative})" in ENGINEERING


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
    assert text.index("## Watch the recorded demo") < text.index(EXCERPT_INTRO)
    assert text.index(EXCERPT_INTRO) < text.index("```text")
    assert "selected output" in EXCERPT_INTRO  # the excerpt is labelled as a selection
    assert _appear_in_order(_cast_output_lines(), excerpt)


def test_excerpt_and_exit_summary_match_executable_demo_behaviour(task_tmpdir: Path) -> None:
    """The checked-out package prints the excerpt and the stated exits and statuses.

    This runs the three command shapes through ``python -m actseal`` from the
    locked environment, not the PyPI release the ``uvx`` commands resolve.
    """
    commands = _bash_commands()
    for command in LEGACY_QUICKSTART:
        assert command in commands
    demo = _run_documented(LEGACY_QUICKSTART[0], task_tmpdir)
    assert demo.returncode == 0, demo.stderr
    assert _appear_in_order(demo.stdout.splitlines(), _excerpt())
    observed: dict[str, object] = {"demo": demo.returncode}
    for run, command in zip(("fixed", "bad"), LEGACY_QUICKSTART[1:], strict=True):
        replay = _run_documented(command, task_tmpdir, json_output=True)
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
        # The standalone card retains provenance and names the packaged replay path.
        assert "Fixed benchmark; unreleased producer" in svg, name
        assert "replay with packaged registry" in svg, name
        assert "replay requires archived producer d3edbab" not in svg, name
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


def test_quickstart_checks_and_limits_are_verbatim() -> None:
    text = _text()
    assert fences(README, "bash")[0].strip().splitlines() == QUICKSTART
    for line in CHECKS + LIMITS:
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
