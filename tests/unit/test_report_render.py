"""Presentation reads already-replayed values without changing their meaning."""

from __future__ import annotations

import json
import re
from dataclasses import replace
from html.parser import HTMLParser
from pathlib import Path

import pytest

from actseal.records import Interval, Option, Status
from actseal.report import ReportData, render_report
from actseal.selection import GridPoint, SelectionResult
from conftest import make_lock, make_verdict


def example(*, selection: bool = True) -> ReportData:
    return ReportData(
        lock=make_lock(),
        verdict=replace(make_verdict(), total=100, accepted=80, errors=2),
        manifest_sha256="2" * 64,
        selection=(
            SelectionResult(
                0.9,
                "selected",
                (
                    GridPoint(0.5, 100, 20, 0.1),
                    GridPoint(0.9, 80, 2, 0.85),
                    GridPoint(1.0, 0, 0, 0.0),
                ),
            )
            if selection
            else None
        ),
        selection_plan=(
            {
                "grid": [0.5, 0.9, 1.0],
                "target_pass_probability": 0.8,
                "selection_tail": 0.05,
                "n_verify": 100,
            }
            if selection
            else None
        ),
        calibration_total=100 if selection else None,
        calibration_manifest_sha256="3" * 64 if selection else None,
    )


class Document(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[str] = []
        self.attributes: list[tuple[str, str | None]] = []
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag)
        self.attributes.extend(attrs)

    def handle_data(self, data: str) -> None:
        self.text.append(data)


def test_report_is_deterministic_with_only_three_files(tmp_path: Path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    render_report(example(), first)
    render_report(example(), second)
    assert sorted(path.name for path in first.iterdir()) == [
        "badge.json",
        "report.html",
        "report.md",
    ]
    for path in first.iterdir():
        content = path.read_bytes()
        assert content == (second / path.name).read_bytes()
        assert str(tmp_path).encode() not in content


def test_report_presents_given_verdict_and_selection_without_reassessment(tmp_path: Path) -> None:
    # Deliberately contradictory supplied limits prove the renderer does not assess.
    data = example()
    data = replace(data, verdict=replace(data.verdict, risk=Interval(0.4, 0.6)))
    render_report(data, tmp_path / "report")
    html = (tmp_path / "report" / "report.html").read_text()
    document = Document()
    document.feed(html)
    text = " ".join(document.text)
    assert "PASS" in text
    assert "[0.4, 0.6]" in text
    assert "80" in text
    assert "2" in text
    assert "descriptive, not verified" in text
    assert "0.9" in document.text
    assert "0.85" in document.text
    assert "not estimated" in text
    assert "fixed benchmark" in text
    assert "one prespecified attempt" in text
    assert "label truth" in text
    assert "deployment behaviour" in text
    assert "svg" in document.tags
    assert text.index("Risk limit") < text.index("Accepted") < text.index("Selected threshold")
    assert text.index("Selected threshold") < text.index("Model identity")
    assert (
        html.index("<h2>Model identity")
        < html.index("<h2>Provider scope")
        < html.index("<h2>SHA-256")
    )
    assert html.index("<h2>SHA-256") < html.index("<h2>Replay commands")


@pytest.mark.parametrize(
    ("max_risk", "alpha", "risk_text", "confidence_text"),
    [(0.05, 0.05, "5.0%", "95.0%"), (0.025, 0.01, "2.5%", "99.0%")],
)
def test_pass_headline_uses_stored_lower_bound_and_contract_values(
    tmp_path: Path, max_risk: float, alpha: float, risk_text: str, confidence_text: str
) -> None:
    data = example()
    contract = replace(
        data.lock.contract,
        limits=replace(data.lock.contract.limits, max_risk=max_risk, alpha=alpha),
        policy=replace(data.lock.contract.policy, threshold=0.910000000001),
    )
    # Counts, upper bounds and the descriptive selection cannot replace stored inputs.
    data = replace(
        data,
        lock=replace(data.lock, contract=contract),
        verdict=replace(data.verdict, coverage=Interval(0.81234, 0.9876)),
    )
    render_report(data, tmp_path / "report")
    headline = (
        f"At a risk limit of {risk_text} ({confidence_text} confidence), the policy acted "
        "alone on at least 81.2% of cases in this benchmark at threshold 0.910000000001."
    )
    html = (tmp_path / "report" / "report.html").read_text()
    markdown = (tmp_path / "report" / "report.md").read_text()
    assert f"<h1>PASS</h1>\n<p>{headline}</p>" in html
    assert markdown.startswith(f"# Actseal: PASS\n\n{headline}\n\n")
    assert json.loads((tmp_path / "report" / "badge.json").read_text())["message"] == (
        f"PASS · ≥81.2% alone @ ≤{risk_text} risk"
    )


@pytest.mark.parametrize("status", ["BLOCK", "INCONCLUSIVE", "ERROR"])
def test_nonpass_headline_makes_no_automation_claim(tmp_path: Path, status: Status) -> None:
    data = example()
    verdict = (
        replace(
            data.verdict,
            status=status,
            total=0,
            accepted=0,
            errors=0,
            risk=Interval(0, 1),
            coverage=Interval(0, 1),
        )
        if status == "ERROR"
        else replace(data.verdict, status=status)
    )
    render_report(replace(data, verdict=verdict), tmp_path / "report")
    headline = (
        "At a risk limit of 5.0% (95.0% confidence), this benchmark did not show "
        "that the policy met the limit."
    )
    html = (tmp_path / "report" / "report.html").read_text()
    markdown = (tmp_path / "report" / "report.md").read_text()
    assert f"<h1>{status}</h1>\n<p>{headline}</p>" in html
    assert markdown.startswith(f"# Actseal: {status}\n\n{headline}\n\n")
    assert "alone" not in headline
    assert "at least" not in headline
    assert json.loads((tmp_path / "report" / "badge.json").read_text())["message"] == status


def test_tables_round_to_four_decimal_places_without_padding(tmp_path: Path) -> None:
    data = example()
    data = replace(data, verdict=replace(data.verdict, risk=Interval(0.012345, 0.123456)))
    render_report(data, tmp_path / "report")
    html = (tmp_path / "report" / "report.html").read_text()
    markdown = (tmp_path / "report" / "report.md").read_text()
    assert "<td>Risk interval</td><td>[0.0123, 0.1235]</td>" in html
    assert "| Risk interval | \\[0.0123, 0.1235\\] |" in markdown
    assert "<td>Confidence (1 - alpha)</td><td>95.0%</td>" in html
    assert "<td>Risk limit</td><td>0.05</td>" in html
    assert "<td>1</td><td>0</td><td>0</td><td>0</td><td>0</td>" in html
    assert not re.search(r"\d\.\d{5,}", markdown)


def test_html_and_markdown_escape_hostile_values(tmp_path: Path) -> None:
    hostile = '<img src="https://host.invalid/pixel" onerror="alert(1)"> [x](https://host.invalid)'
    data = example()
    question = replace(
        data.lock.contract.question,
        options=(Option(hostile, "Hostile label"), Option("other", "Other label")),
    )
    lock = replace(
        data.lock,
        contract=replace(
            data.lock.contract,
            question=question,
            policy=replace(
                data.lock.contract.policy, known_labels=question.labels, allowed_labels=(hostile,)
            ),
        ),
        model_identity=replace(
            data.lock.model_identity, model=hostile, revision="`<script>x</script>`"
        ),
        verification_cases=tuple(
            replace(case, expected_label=hostile) for case in data.lock.verification_cases
        ),
    )
    render_report(replace(data, lock=lock), tmp_path / "report", attestation_ref=hostile)
    html = (tmp_path / "report" / "report.html").read_text()
    markdown = (tmp_path / "report" / "report.md").read_text()
    document = Document()
    document.feed(html)
    assert "img" not in document.tags
    assert "script" not in document.tags
    assert all(not name.startswith("on") for name, _ in document.attributes)
    assert all(name not in {"src", "href", "srcset"} for name, _ in document.attributes)
    assert hostile in " ".join(document.text)
    assert "&lt;img" in html
    assert "&lt;script&gt;" in html
    assert "<img" not in markdown
    assert "<script" not in markdown
    assert "[x](https://host.invalid)" not in markdown


@pytest.mark.parametrize(
    ("status", "color"),
    [("PASS", "brightgreen"), ("BLOCK", "red"), ("INCONCLUSIVE", "yellow"), ("ERROR", "lightgrey")],
)
def test_badge_retains_verdict_status(tmp_path: Path, status: Status, color: str) -> None:
    data = example(selection=False)
    if status == "ERROR":
        verdict = replace(
            data.verdict,
            status=status,
            total=0,
            accepted=0,
            errors=0,
            risk=Interval(0, 1),
            coverage=Interval(0, 1),
        )
    else:
        verdict = replace(data.verdict, status=status)
    render_report(replace(data, verdict=verdict), tmp_path / "report")
    assert json.loads((tmp_path / "report" / "badge.json").read_bytes()) == {
        "schemaVersion": 1,
        "label": "Actseal",
        "message": "PASS · ≥50.0% alone @ ≤5.0% risk" if status == "PASS" else status,
        "color": color,
    }


def test_attestation_requires_caller_reference(tmp_path: Path) -> None:
    render_report(example(), tmp_path / "local")
    render_report(example(), tmp_path / "referenced", attestation_ref="run-123 / digest-abc")
    for name in ("report.html", "report.md"):
        local = (tmp_path / "local" / name).read_text()
        referenced = (tmp_path / "referenced" / name).read_text()
        assert "checksummed, not attested" in local
        assert "attested" in referenced
        assert "run-123 / digest-abc" in referenced
        assert "Actseal verifies no signature" in local
        assert "Actseal verifies no signature" in referenced


def test_plain_bundle_commands_and_provider_note(tmp_path: Path) -> None:
    data = example(selection=False)
    lock = replace(data.lock, model_identity=replace(data.lock.model_identity, provider="recorded"))
    render_report(replace(data, lock=lock), tmp_path / "report")
    text = (tmp_path / "report" / "report.md").read_text()
    assert "recorded: provider faults not tested" in text
    assert f"actseal replay . --expected-lock-sha256 {'1' * 64}" in text
    assert "replay-selection" not in text
    assert "descriptive, not verified" not in text


def test_qualification_replay_commands_and_hashes(tmp_path: Path) -> None:
    render_report(example(), tmp_path / "report")
    text = (tmp_path / "report" / "report.md").read_text()
    assert f"actseal replay evidence --expected-lock-sha256 {'1' * 64}" in text
    assert "actseal replay-selection calibration" in text
    for digit in "123":
        assert digit * 64 in text


def test_templates_and_outputs_do_not_make_prohibited_claims(tmp_path: Path) -> None:
    render_report(example(), tmp_path / "report")
    source = Path(__file__).resolve().parents[2] / "src" / "actseal" / "report.py"
    for path in (source, *(tmp_path / "report").iterdir()):
        assert not re.search(
            r"\b(?:guaranteed|certified|safe|best)\b", path.read_text(), re.IGNORECASE
        )


def test_existing_destination_is_preserved(tmp_path: Path) -> None:
    destination = tmp_path / "report"
    destination.mkdir()
    (destination / "keep").write_text("unchanged")
    with pytest.raises(FileExistsError):
        render_report(example(), destination)
    assert list(destination.iterdir()) == [destination / "keep"]
    assert (destination / "keep").read_text() == "unchanged"
