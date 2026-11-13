"""Deterministic presentation of values already validated and replayed by the CLI.

This module is excluded from the implementation fingerprint. It never evaluates
a policy, selects a threshold, computes a bound, or issues a verdict. Empirical
calibration ratios below are chart coordinates only, not verification statistics.
"""

from __future__ import annotations

import errno
import html
import json
import os
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

from actseal.errors import SchemaError
from actseal.evidence import _check_path_text, _exclusive_rename, _write_file
from actseal.records import PlanLock, Verdict
from actseal.selection import SelectionResult

__all__ = ["ReportData", "render_report"]

_SCOPE_SENTENCE: Final = (
    "This result describes a fixed benchmark under one prespecified attempt; "
    "it is not proof of label truth or deployment behaviour."
)
_CHART_LABEL: Final = "Calibration risk-coverage chart — descriptive, not verified"
_SIGNATURE_NOTE: Final = (
    "Actseal verifies no signature. An attestation reference is supplied by the caller; "
    "it does not establish label truth or deployment behaviour."
)
_BADGE_COLORS: Final = {
    "PASS": "brightgreen",
    "BLOCK": "red",
    "INCONCLUSIVE": "yellow",
    "ERROR": "lightgrey",
}
_CSS: Final = """
:root { color-scheme: light; font-family: system-ui, sans-serif; color: #202b38;
        background: #eef2f5; line-height: 1.55; }
* { box-sizing: border-box; }
body { margin: 0; padding: 2rem 1rem; }
main { max-width: 900px; margin: auto; background: #fff; padding: 2.5rem;
       border: 1px solid #d6dfe7; border-radius: 16px; }
h1 { font-size: 3rem; line-height: 1.15; margin: .4rem 0 1rem; }
h2 { font-size: 1.25rem; margin: 2rem 0 .8rem; }
p { margin: .7rem 0; }
.eyebrow { text-transform: uppercase; letter-spacing: .12em; font-size: .8rem; }
.scope, .note { color: #465769; }
.scope { max-width: 70ch; }
table { border-collapse: collapse; width: 100%; margin: .8rem 0; }
th, td { text-align: left; padding: .65rem .75rem; vertical-align: top;
         border-bottom: 1px solid #dce3e9; overflow-wrap: anywhere; }
th { font-weight: 600; background: #f3f6f8; }
td:first-child { width: 35%; }
.table-wrap { overflow-x: auto; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; background: #f3f6f8;
      border: 1px solid #dce3e9; padding: 1rem; border-radius: 6px; }
svg { display: block; width: 100%; height: auto; background: #f8fafb; }
svg text { font-size: 13px; fill: #304456; }
.axis { stroke: #657889; stroke-width: 1.5; }
.grid { stroke: #dce3e9; stroke-width: 1; }
.curve { stroke: #2563a6; stroke-width: 2; fill: none; }
.point { fill: #2563a6; stroke: #fff; stroke-width: 1.5; }
footer { margin-top: 2rem; border-top: 1px solid #dce3e9; padding-top: 1rem; }
@media (max-width: 600px) { body { padding: .5rem; } main { padding: 1rem; }
  h1 { font-size: 2.3rem; } th, td { padding: .5rem; } }
@media print { body { background: #fff; padding: 0; } main { border: 0; padding: 0; } }
"""


@dataclass(frozen=True)
class ReportData:
    """Display inputs; their validation and replay belong to the calling command."""

    lock: PlanLock
    verdict: Verdict
    manifest_sha256: str
    selection: SelectionResult | None = None
    selection_plan: Mapping[str, object] | None = None
    calibration_total: int | None = None
    calibration_manifest_sha256: str | None = None


def _number(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".")


_PERCENT_NOISE = 1e-9  # float error from scaling a share by 100, far below any locked digit


def _exact(value: float) -> str:
    """A locked parameter, never rounded: four decimals only when that is exact."""
    text = _number(value)
    return text if float(text) == value else repr(value)


def _percent(share: float) -> str:
    """A locked share as a percentage, one decimal only when that is exact."""
    scaled = share * 100
    text = f"{scaled:.1f}"
    return text if abs(float(text) - scaled) < _PERCENT_NOISE else f"{scaled:.10g}"


def _headline(data: ReportData) -> str:
    limits = data.lock.contract.limits
    context = (
        f"At a risk limit of {_percent(limits.max_risk)}% "
        f"({_percent(1 - limits.alpha)}% confidence), "
    )
    if data.verdict.status == "PASS":
        return (
            f"{context}the policy acted alone on at least {data.verdict.coverage.lower * 100:.1f}% "
            f"of cases in this benchmark at threshold {data.lock.contract.policy.threshold}."
        )
    return f"{context}this benchmark did not show that the policy met the limit."


def _html_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    head = "".join(f'<th scope="col">{html.escape(value)}</th>' for value in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{html.escape(value)}</td>" for value in row) + "</tr>"
        for row in rows
    )
    return (
        f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead>'
        f"<tbody>{body}</tbody></table></div>"
    )


def _markdown_text(value: str) -> str:
    escaped = value
    for char in "\\`*_{}[]()#+!|~":
        escaped = escaped.replace(char, "\\" + char)
    return html.escape(escaped, quote=True).replace("\r", "&#13;").replace("\n", "&#10;")


def _markdown_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    return "\n".join(
        [
            "| " + " | ".join(_markdown_text(value) for value in headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
            *("| " + " | ".join(_markdown_text(value) for value in row) + " |" for row in rows),
        ]
    )


def _selection_rows(data: ReportData) -> list[tuple[str, ...]]:
    if data.selection is None or not data.calibration_total:
        return []
    return [
        (
            _exact(point.threshold),
            str(point.accepted),
            str(point.errors),
            _number(point.predicted_pass_probability),
            _number(point.accepted / data.calibration_total),
            _number(point.errors / point.accepted) if point.accepted else "not estimated",
        )
        for point in data.selection.points
    ]


def _chart_points(data: ReportData) -> list[tuple[float, float, float]]:
    if data.selection is None or not data.calibration_total:
        return []
    return [
        (point.threshold, point.accepted / data.calibration_total, point.errors / point.accepted)
        for point in data.selection.points
        if point.accepted
    ]


def _svg_chart(data: ReportData) -> str:
    parts = [
        '<svg viewBox="0 0 720 330" role="img" aria-labelledby="chart-title chart-description">',
        f'<title id="chart-title">{html.escape(_CHART_LABEL)}</title>',
        (
            '<desc id="chart-description">Empirical calibration error share among accepted cases '
            "against accepted share of all calibration cases. Zero-accepted points have no "
            "estimated risk and are omitted from the plot.</desc>"
        ),
    ]
    for tick in range(6):
        ratio = tick / 5
        x, y = 70 + 610 * ratio, 260 - 220 * ratio
        parts.extend(
            (
                f'<line class="grid" x1="70" y1="{y:.2f}" x2="680" y2="{y:.2f}"/>',
                f'<text x="58" y="{y + 4:.2f}" text-anchor="end">{ratio:.1f}</text>',
                f'<text x="{x:.2f}" y="282" text-anchor="middle">{ratio:.1f}</text>',
            )
        )
    parts.extend(
        (
            '<line class="axis" x1="70" y1="40" x2="70" y2="260"/>',
            '<line class="axis" x1="70" y1="260" x2="680" y2="260"/>',
            (
                '<text x="375" y="315" text-anchor="middle">'
                "Empirical coverage (accepted / calibration total)</text>"
            ),
            (
                '<text x="18" y="150" text-anchor="middle" transform="rotate(-90 18 150)">'
                "Empirical risk (errors / accepted)</text>"
            ),
        )
    )
    points = _chart_points(data)
    coordinates = " ".join(
        f"{70 + 610 * coverage:.2f},{260 - 220 * risk:.2f}" for _, coverage, risk in points
    )
    if points:
        parts.append(f'<polyline class="curve" points="{coordinates}"/>')
    for threshold, coverage, risk in points:
        parts.append(
            f'<circle class="point" cx="{70 + 610 * coverage:.2f}" '
            f'cy="{260 - 220 * risk:.2f}" r="5"><title>'
            f"Threshold {_exact(threshold)}; coverage {_number(coverage)}; risk {_number(risk)}"
            "</title></circle>"
        )
    parts.append("</svg>")
    return "\n".join(parts)


def _text_chart(data: ReportData) -> str:
    width, height = 40, 10
    cells = [[" " for _ in range(width + 1)] for _ in range(height + 1)]
    for _, coverage, risk in _chart_points(data):
        cells[round((1 - risk) * height)][round(coverage * width)] = "o"
    lines = ["Empirical risk (errors / accepted)"]
    lines.extend(f"{1 - row / height:3.1f} |{''.join(cells[row])}" for row in range(height + 1))
    lines.extend(
        (
            "    +" + "-" * (width + 1),
            "     0.0" + " " * (width - 6) + "1.0",
            "     Empirical coverage (accepted / calibration total)",
        )
    )
    return "\n".join(lines)


def _identity_rows(data: ReportData) -> list[tuple[str, str]]:
    identity = data.lock.model_identity
    rows = [
        ("Provider", identity.provider),
        ("Model", identity.model),
        ("Revision", identity.revision),
        ("Adapter version", identity.adapter_version),
        ("Normalizer version", identity.normalizer_version),
        ("Producer implementation SHA-256", data.lock.implementation_sha256),
        ("Replay engine", data.lock.replay_engine_version),
        ("Contract", data.lock.contract.name),
        ("Population", data.lock.contract.population),
        ("Labels", ", ".join(option.label for option in data.lock.contract.question.options)),
        ("Allowed labels", ", ".join(data.lock.contract.policy.allowed_labels)),
    ]
    rows.extend((f"Artifact: {name}", value) for name, value in sorted(identity.artifact_hashes))
    rows.extend((f"Runtime: {name}", value) for name, value in sorted(identity.runtime))
    return rows


def _provider_notes(data: ReportData) -> list[str]:
    notes = [f"Evidence scope: {data.verdict.evidence_scope}"]
    if data.lock.model_identity.provider == "recorded":
        notes.append("recorded: provider faults not tested")
    notes.append(
        "The six canonical fault checks are synthetic; "
        "they do not demonstrate live provider behaviour."
    )
    if data.verdict.evidence_scope == "demo":
        notes.append("Authored examples; repeated replay cannot turn them into a population study.")
    else:
        notes.append(
            "Population interpretation requires independent IID outcomes from the declared "
            "distribution under the fixed policy and operating regime."
        )
    return notes


def _replay_commands(data: ReportData) -> tuple[str, ...]:
    bundle = "evidence" if data.selection is not None else "."
    commands: tuple[str, ...] = (
        f"actseal replay {bundle} --expected-lock-sha256 {data.lock.sha256}",
    )
    if data.selection is not None:
        commands += ("actseal replay-selection calibration",)
    return commands


def _documents(data: ReportData, attestation_ref: str | None) -> dict[str, bytes]:
    if data.selection is not None and (
        data.selection_plan is None
        or data.calibration_total is None
        or data.calibration_manifest_sha256 is None
    ):
        raise SchemaError("report: calibration presentation inputs are incomplete")
    verdict, limits = data.verdict, data.lock.contract.limits
    headline = _headline(data)
    html_parts = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>Actseal report</title><style>{_CSS}</style></head><body><main>",
        '<p class="eyebrow">Actseal · replayed evidence</p>',
        f"<h1>{html.escape(verdict.status)}</h1>",
        f"<p>{html.escape(headline)}</p>",
        f'<p class="scope">{html.escape(_SCOPE_SENTENCE)}</p>',
    ]
    markdown = [f"# Actseal: {verdict.status}", headline, _SCOPE_SENTENCE]

    def table(title: str, headers: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
        html_parts.extend((f"<h2>{html.escape(title)}</h2>", _html_table(headers, rows)))
        markdown.extend((f"## {title}", _markdown_table(headers, rows)))

    table(
        "Verification limits",
        ("Measure", "Value"),
        (
            ("Risk limit", _exact(limits.max_risk)),
            ("Confidence (1 - alpha)", f"{_percent(1 - limits.alpha)}%"),
            ("Alpha", _exact(limits.alpha)),
            ("Minimum coverage", _exact(limits.min_coverage)),
        ),
    )
    table(
        "Verification result",
        ("Measure", "Stored value"),
        (
            ("Accepted", str(verdict.accepted)),
            ("Errors", str(verdict.errors)),
            ("Total cases", str(verdict.total)),
            ("Risk interval", f"[{_number(verdict.risk.lower)}, {_number(verdict.risk.upper)}]"),
            (
                "Coverage interval",
                f"[{_number(verdict.coverage.lower)}, {_number(verdict.coverage.upper)}]",
            ),
            ("Reasons", ", ".join(verdict.reasons)),
        ),
    )
    if data.selection is not None:
        plan = cast(Mapping[str, object], data.selection_plan)
        grid = cast(Sequence[float], plan["grid"])
        selected = data.selection.threshold
        table(
            "Threshold selection",
            ("Measure", "Stored value"),
            (
                ("Selected threshold", _exact(selected) if selected is not None else "none"),
                ("Selection reason", data.selection.reason),
                ("Prespecified grid", ", ".join(_exact(value) for value in grid)),
                ("Target pass probability", _exact(cast(float, plan["target_pass_probability"]))),
                ("Selection tail", _exact(cast(float, plan["selection_tail"]))),
                ("Calibration cases", str(data.calibration_total)),
                ("Planned verification cases", str(plan["n_verify"])),
                (
                    "Rule",
                    (
                        "Maximum calibration accepted count among candidates reaching the target "
                        "predicted pass probability; ties choose the higher threshold."
                    ),
                ),
            ),
        )
        table(
            "Calibration grid",
            (
                "Threshold",
                "Accepted",
                "Errors",
                "Predicted PASS probability",
                "Empirical coverage",
                "Empirical risk",
            ),
            _selection_rows(data),
        )
        html_parts.extend((f"<h2>{_CHART_LABEL}</h2>", _svg_chart(data)))
        markdown.extend((f"## {_CHART_LABEL}", f"```text\n{_text_chart(data)}\n```"))
        note = "Zero-accepted points have no estimated risk and are omitted from the plot."
        html_parts.append(f'<p class="note">{note}</p>')
        markdown.append(note)
    else:
        table(
            "Threshold",
            ("Measure", "Stored value"),
            (("Prespecified threshold", _exact(data.lock.contract.policy.threshold)),),
        )
    table("Model identity", ("Field", "Value"), _identity_rows(data))
    html_parts.append("<h2>Provider scope</h2>")
    markdown.append("## Provider scope")
    for note in _provider_notes(data):
        html_parts.append(f"<p>{html.escape(note)}</p>")
        markdown.append(_markdown_text(note))
    hashes = [("Lock seal", data.lock.sha256), ("Evidence manifest file", data.manifest_sha256)]
    if data.calibration_manifest_sha256 is not None:
        hashes.append(("Calibration manifest file", data.calibration_manifest_sha256))
    table("SHA-256", ("Artifact", "Digest"), hashes)
    commands = "\n".join(_replay_commands(data))
    instruction = "Run from the original input directory, using a compatible Actseal installation:"
    html_parts.extend(
        ("<h2>Replay commands</h2>", f"<p>{instruction}</p>", f"<pre>{html.escape(commands)}</pre>")
    )
    markdown.extend(("## Replay commands", instruction, f"```sh\n{commands}\n```"))
    attestation = (
        f"attested — caller-supplied reference: {attestation_ref}"
        if attestation_ref is not None
        else "checksummed, not attested"
    )
    html_parts.extend(
        (
            f"<footer><p>{html.escape(attestation)}</p>",
            f'<p class="note">{_SIGNATURE_NOTE}</p></footer>',
            "</main></body></html>",
        )
    )
    markdown.extend(("## Attestation", _markdown_text(attestation), _SIGNATURE_NOTE))
    badge = {
        "schemaVersion": 1,
        "label": "Actseal",
        "message": (
            f"PASS · ≥{verdict.coverage.lower * 100:.1f}% alone "
            f"@ ≤{_percent(limits.max_risk)}% risk"
            if verdict.status == "PASS"
            else verdict.status
        ),
        "color": _BADGE_COLORS[verdict.status],
    }
    return {
        "report.html": ("\n".join(html_parts) + "\n").encode("utf-8"),
        "report.md": ("\n\n".join(markdown) + "\n").encode("utf-8"),
        "badge.json": (json.dumps(badge, sort_keys=True, separators=(",", ":")) + "\n").encode(
            "utf-8"
        ),
    }


def render_report(data: ReportData, out: Path, *, attestation_ref: str | None = None) -> None:
    """Publish three presentation files atomically in a new output directory."""
    _check_path_text("out", out)
    if os.path.lexists(out):
        raise FileExistsError(errno.EEXIST, "destination: already exists")
    documents = _documents(data, attestation_ref)
    temporary = Path(tempfile.mkdtemp(prefix=".actseal-report-", dir=out.parent))
    try:
        for name, content in documents.items():
            _write_file(temporary / name, content)
        _exclusive_rename(temporary, out)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
