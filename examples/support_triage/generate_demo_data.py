"""Deterministic generator for the authored support-triage demonstration (ADR 0013).

This script is documentation of how the committed demo inputs were produced; it
is not a product feature and the installed package never runs it. It uses no
randomness, so a rerun reproduces the committed files byte for byte. Usage:

    python examples/support_triage/generate_demo_data.py DIRECTORY

The directory is created when missing; none of the eight output files may
already exist. The eight generated files are the two prespecified
contracts, the four labelled JSONL datasets and the two recorded fixture
response files. Every case, label, probability and wrong answer below is
authored synthetic data with ``evidence_scope = "demo"``; nothing here was
produced by a model, and the demo makes no population or calibration claim.

Rules (frozen before the fixtures were created):

* ordered labels ``billing``, ``technical``, ``sales``; all allowed; threshold
  0.90; max_risk 0.05; min_coverage 0.50; alpha 0.05;
* each run has 128 verification cases (indices 0..127) and 12 calibration
  cases (indices 0..11); the gold label of index ``i`` is label ``i mod 3``;
* the fixed fixture selects the gold label for every verification case; the
  deliberately bad fixture selects the next cyclic label for indices 0..31 and
  the gold label for indices 32..127 (32 authored wrong accepted decisions);
* every selected label has probability 0.95, the label after it in cyclic
  order 0.03 and the remaining label 0.02; no provider confidence is recorded;
* case IDs and state texts are unique across all four datasets: each state
  embeds its own ticket identifier, and templates cycle per label.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Final

LABELS: Final[tuple[str, ...]] = ("billing", "technical", "sales")
VERIFICATION_CASES: Final = 128
CALIBRATION_CASES: Final = 12
BAD_WRONG_CASES: Final = 32
SELECTED_PROBABILITY: Final = 0.95
NEXT_PROBABILITY: Final = 0.03
REMAINING_PROBABILITY: Final = 0.02

OPTIONS: Final[tuple[tuple[str, str], ...]] = (
    ("billing", "Payments, invoices and refunds"),
    ("technical", "Errors, outages and technical support"),
    ("sales", "Purchasing, quotes and plan questions"),
)

TEMPLATES: Final[dict[str, tuple[str, ...]]] = {
    "billing": (
        "Ticket {ticket}: I was charged twice for invoice {number}; please refund the duplicate.",
        "Ticket {ticket}: My refund for order {number} has not arrived after cancellation.",
        "Ticket {ticket}: The receipt for payment {number} shows the wrong amount.",
        "Ticket {ticket}: Please update the card on file before invoice {number} is due.",
    ),
    "technical": (
        "Ticket {ticket}: The app crashes on launch since update {number}.",
        "Ticket {ticket}: Login returns error {number} after a password reset.",
        "Ticket {ticket}: Export job {number} never finishes and shows no progress.",
        "Ticket {ticket}: Notifications stopped arriving on device {number}.",
    ),
    "sales": (
        "Ticket {ticket}: We need a quote for {number} seats on the annual plan.",
        "Ticket {ticket}: Does plan {number} include single sign-on for our team?",
        "Ticket {ticket}: Can we trial the enterprise tier before contract {number} renews?",
        "Ticket {ticket}: What discount applies when ordering {number} licences?",
    ),
}

CONTRACTS: Final[dict[str, tuple[str, str]]] = {
    "bad": (
        "support-triage-bad",
        (
            "Authored support-routing demonstration with 32 deliberately wrong accepted "
            "answers; demo evidence only, no deployment or population claim"
        ),
    ),
    "fixed": (
        "support-triage-fixed",
        (
            "Authored support-routing demonstration whose recorded answers all equal the "
            "authored labels; demo evidence only, no deployment or population claim"
        ),
    ),
}


def gold_label(index: int) -> str:
    return LABELS[index % len(LABELS)]


def next_label(label: str) -> str:
    return LABELS[(LABELS.index(label) + 1) % len(LABELS)]


def state_text(run: str, split: str, index: int) -> str:
    label = gold_label(index)
    templates = TEMPLATES[label]
    template = templates[(index // len(LABELS)) % len(templates)]
    ticket = f"{run.upper()}-{split.upper()}-{index:03d}"
    return template.format(ticket=ticket, number=1000 + index)


def case_rows(run: str, split: str, count: int) -> str:
    rows = []
    for index in range(count):
        row = {
            "case_id": f"{run}-{split}-{index:03d}",
            "state": state_text(run, split, index),
            "expected_label": gold_label(index),
        }
        rows.append(json.dumps(row, ensure_ascii=False))
    return "".join(row + "\n" for row in rows)


def selected_label(run: str, index: int) -> str:
    gold = gold_label(index)
    if run == "bad" and index < BAD_WRONG_CASES:
        return next_label(gold)
    return gold


def answer_body(selected: str) -> str:
    following = next_label(selected)
    probabilities = {
        label: (
            SELECTED_PROBABILITY
            if label == selected
            else NEXT_PROBABILITY
            if label == following
            else REMAINING_PROBABILITY
        )
        for label in LABELS
    }
    return json.dumps({"type": "choice", "choice": selected, "probabilities": probabilities})


def response_rows(run: str) -> str:
    rows = []
    for index in range(VERIFICATION_CASES):
        row = {
            "case_id": f"{run}-v-{index:03d}",
            "body_json": answer_body(selected_label(run, index)),
            "failure_code": None,
            "warnings": [],
        }
        rows.append(json.dumps(row, ensure_ascii=False))
    return "".join(row + "\n" for row in rows)


def contract_toml(run: str) -> str:
    name, population = CONTRACTS[run]
    options = "".join(
        f'  {{label = "{label}", description = "{description}"}},\n'
        for label, description in OPTIONS
    )
    allowed = ", ".join(f'"{label}"' for label in LABELS)
    return (
        "schema_version = 1\n"
        f'name = "{name}"\n'
        'evidence_scope = "demo"\n'
        f'population = "{population}"\n'
        "\n"
        "[question]\n"
        'question_id = "department"\n'
        'instructions = "Select the department responsible for this ticket."\n'
        "options = [\n"
        f"{options}"
        "]\n"
        "\n"
        "[policy]\n"
        f"allowed_labels = [{allowed}]\n"
        "threshold = 0.90\n"
        "\n"
        "[risk]\n"
        "max_risk = 0.05\n"
        "min_coverage = 0.50\n"
        "alpha = 0.05\n"
    )


def generate() -> dict[str, str]:
    """Return the eight demo files as ``{filename: text}``."""
    files: dict[str, str] = {}
    for run in ("bad", "fixed"):
        files[f"{run}.toml"] = contract_toml(run)
        files[f"{run}_calibration.jsonl"] = case_rows(run, "c", CALIBRATION_CASES)
        files[f"{run}_verification.jsonl"] = case_rows(run, "v", VERIFICATION_CASES)
        files[f"{run}_responses.jsonl"] = response_rows(run)
    return files


def write(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, text in generate().items():
        with (directory / name).open("x", encoding="utf-8", newline="") as handle:
            handle.write(text)


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        sys.stderr.write("usage: generate_demo_data.py DIRECTORY\n")
        return 2
    write(Path(argv[0]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
