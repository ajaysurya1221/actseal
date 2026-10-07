"""The quickstart's three commands match the approved plan and the installed package.

The PyPI commands cannot be executed here without a network download. The
executable check therefore runs the *equivalent* commands (``python -m actseal``
from the locked environment) against the checked-out package; that is a check
of the promised behaviour, not a PyPI publication receipt (Tasks 20/14).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from docs.conftest import DOCS, ROOT, fences, table_rows

QUICKSTART = DOCS / "quickstart.md"
PLAN = ROOT / "plan" / "v1" / "PLAN.md"

EXPECTED_COMMANDS = [
    "uvx --python 3.12 actseal demo --out ./actseal-demo",
    "uvx --offline --python 3.12 actseal replay ./actseal-demo/fixed/evidence",
    "uvx --offline --python 3.12 actseal replay ./actseal-demo/bad/evidence",
]


def test_three_commands_match_plan_section_d_verbatim() -> None:
    documented = fences(QUICKSTART, "bash")[0].strip().splitlines()
    assert documented == EXPECTED_COMMANDS
    plan_text = PLAN.read_text(encoding="utf-8")
    assert "\n".join(EXPECTED_COMMANDS) in plan_text


def test_quickstart_is_version_neutral_and_claims_no_publication_state() -> None:
    """The page must stay correct before and after the 1.0.0 tag without edits."""
    text = QUICKSTART.read_text(encoding="utf-8")
    for command in EXPECTED_COMMANDS:
        assert "--from" not in command
    stale_claims = (
        "not yet on",
        "release candidate",
        "At the time of writing",
        "currently published",
    )
    for stale in stale_claims:
        assert stale not in text, stale
    assert "--from" in text  # the exact-pin form is documented alongside the unpinned form
    assert "Windows is unsupported" in text
    assert "stability.md" in text


def _run(arguments: list[str], cwd: Path) -> tuple[int, dict[str, object]]:
    result = subprocess.run(  # noqa: S603 - fixed interpreter and literal arguments
        [sys.executable, "-m", "actseal", *arguments, "--json"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert result.stderr == ""
    document = json.loads(result.stdout)
    assert isinstance(document, dict)
    return result.returncode, document


def test_candidate_package_matches_the_documented_exits_and_outputs(task_tmpdir: Path) -> None:
    """Candidate verification: the same three command shapes via ``python -m actseal``."""
    code, demo = _run(["demo", "--out", "./actseal-demo"], task_tmpdir)
    assert code == 0
    assert demo["status"] == "PASS"
    runs = demo["runs"]
    assert isinstance(runs, dict)
    assert runs["bad"]["status"] == "BLOCK"
    assert runs["fixed"]["status"] == "PASS"

    code, fixed = _run(["replay", "./actseal-demo/fixed/evidence"], task_tmpdir)
    assert (code, fixed["status"]) == (0, "PASS")
    code, bad = _run(["replay", "./actseal-demo/bad/evidence"], task_tmpdir)
    assert (code, bad["status"]) == (1, "BLOCK")

    rows = table_rows(QUICKSTART.read_text(encoding="utf-8"), "Expected observation")
    observed = {
        "Status": (
            f"{runs['bad']['status']} (exit {bad['exit_code']})",
            f"{runs['fixed']['status']} (exit {fixed['exit_code']})",
        ),
        "ACT / total": (
            f"{runs['bad']['accepted']} / {runs['bad']['total']}",
            f"{runs['fixed']['accepted']} / {runs['fixed']['total']}",
        ),
        "Wrong ACT / ACT": (
            f"{runs['bad']['errors']} / {runs['bad']['accepted']}",
            f"{runs['fixed']['errors']} / {runs['fixed']['accepted']}",
        ),
        "Fresh replay": ("Matching BLOCK", "Matching PASS"),
    }
    assert {row[0]: (row[1], row[2]) for row in rows} == observed

    layout = table_rows(QUICKSTART.read_text(encoding="utf-8"), "Path under `actseal-demo/`")
    for row in layout:
        for name in (cell.strip().strip("`") for cell in row[0].split(",")):
            assert (task_tmpdir / "actseal-demo" / name).exists(), name
    code, exists = _run(["demo", "--out", "./actseal-demo"], task_tmpdir)
    assert (code, exists["error"]) == (3, "destination already exists")
