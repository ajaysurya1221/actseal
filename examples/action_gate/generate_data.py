"""Deterministic generator for the authored action-gate example data (Task 07).

This script documents how the committed example inputs were produced; the
installed package never runs it. It uses no randomness, so a rerun reproduces
the committed files byte for byte. Usage:

    python examples/action_gate/generate_data.py DIRECTORY

The directory is created when missing; none of the five output files may
already exist. Everything produced here is **authored synthetic data** with
``evidence_scope = "demo"``: no model produced any label, probability or
failure, and nothing below is a population, calibration or deployment claim.

Two kinds of files are produced and must be kept apart:

* **Evaluation data** (``contract.toml``, ``calibration.jsonl``,
  ``verification.jsonl``): the labelled ``Case`` fixtures that the offline
  verification run locks and scores. ``expected_label`` exists only here.
* **Application inputs** (``tickets.jsonl``): label-free tickets that the
  example application routes at run time. A ticket row has exactly
  ``ticket_id`` and ``text``; the application never sees or needs a label.

``responses.jsonl`` is the recorded-response fixture that stands in for a
model for BOTH uses. It is keyed by case id / ticket id and is the only
"model" in this example.

Rules (frozen before the files were created, before any run was recorded):

* question options in order: ``billing``, ``technical``, ``sales``, ``other``;
  routed (allowed) labels ``billing``, ``technical``, ``sales``; threshold
  0.90; ``max_risk`` 0.05; ``min_coverage`` 0.50; ``alpha`` 0.05;
* 160 verification cases (indices 0..159) and 12 calibration cases
  (indices 0..11); the gold label of index ``i`` is routed label ``i mod 3``;
* authored verification outcome of index ``i``:
  ``i mod 20 == 7`` selects the gold label at 0.85 (below threshold);
  ``i mod 20 == 13`` is a recorded ``timeout`` failure;
  ``i mod 20 == 19`` selects ``other`` at 0.95 (known but not routed);
  ``i == 42`` selects the next routed label after the gold label at 0.95
  (one authored wrong accepted answer); every other index selects the gold
  label at 0.95;
* probability shapes: a selected label at 0.95 gives the following labels in
  cyclic order 0.03, 0.01, 0.01; at 0.85 gives 0.10, 0.03, 0.02; at exactly
  0.90 gives 0.06, 0.03, 0.01; at 0.8999 gives 0.0601, 0.03, 0.01. Every
  shape sums to exactly 1.0 in binary floating point, so the normalizer never
  renormalizes. No provider confidence is recorded;
* eight run-time tickets cover every decision and both sides of the
  threshold: see ``TICKETS`` below. Their ids share the ``T-`` prefix and
  never appear in a labelled split;
* every case id, ticket id and state text is unique across all files.

Prespecified expectation for the verification run (computed from the frozen
statistical contract before recording; not tuned afterwards): n = 160,
24 non-ACT cases (8 ABSTAIN, 8 ESCALATE, 8 DENY), a = 136 accepted, e = 1
wrong accepted answer; each Clopper-Pearson tail is 0.05 / 4; risk upper
bound about 0.0460 <= 0.05 and coverage lower bound about 0.775 >= 0.50, so
the predicted verdict is PASS. The recorded run reports whatever the pipeline
actually produced.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Final

OPTIONS: Final[tuple[tuple[str, str], ...]] = (
    ("billing", "Payments, invoices and refunds"),
    ("technical", "Errors, outages and technical support"),
    ("sales", "Purchasing, quotes and plan questions"),
    ("other", "Anything else; a person chooses the queue"),
)
LABELS: Final[tuple[str, ...]] = tuple(label for label, _ in OPTIONS)
ROUTED_LABELS: Final[tuple[str, ...]] = ("billing", "technical", "sales")
THRESHOLD: Final = "0.90"

VERIFICATION_CASES: Final = 160
CALIBRATION_CASES: Final = 12
CYCLE: Final = 20
ABSTAIN_SLOT: Final = 7
TIMEOUT_SLOT: Final = 13
OTHER_SLOT: Final = 19
WRONG_INDEX: Final = 42

#: Probability shapes: selected probability -> following three labels in cyclic order.
SHAPES: Final[dict[str, tuple[float, tuple[float, float, float]]]] = {
    "confident": (0.95, (0.03, 0.01, 0.01)),
    "low": (0.85, (0.10, 0.03, 0.02)),
    "at_threshold": (0.90, (0.06, 0.03, 0.01)),
    "below_threshold": (0.8999, (0.0601, 0.03, 0.01)),
}

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

#: Run-time tickets: (ticket id, text, authored response kind, authored choice).
#: ``kind`` is a shape name, ``timeout`` (recorded failure), ``unknown`` (a
#: choice outside the question) or ``malformed`` (a body that is not JSON).
TICKETS: Final[tuple[tuple[str, str, str, str], ...]] = (
    (
        "T-1001",
        "Ticket T-1001: Invoice 2201 was charged twice; please refund the duplicate.",
        "confident",
        "billing",
    ),
    (
        "T-1002",
        "Ticket T-1002: The dashboard returns error 502 after today's deploy.",
        "confident",
        "technical",
    ),
    (
        "T-1003",
        "Ticket T-1003: Can we get a quote for 40 seats on the annual plan?",
        "at_threshold",
        "sales",
    ),
    (
        "T-1004",
        "Ticket T-1004: Our card expires next week; update it before invoice 2204.",
        "below_threshold",
        "billing",
    ),
    (
        "T-1005",
        "Ticket T-1005: Export job 2205 hangs at zero percent.",
        "timeout",
        "",
    ),
    (
        "T-1006",
        "Ticket T-1006: Is your office open on public holidays?",
        "confident",
        "other",
    ),
    (
        "T-1007",
        "Ticket T-1007: Please forward this to legal about contract 2207.",
        "unknown",
        "legal",
    ),
    (
        "T-1008",
        "Ticket T-1008: Notifications stopped on device 2208.",
        "malformed",
        "",
    ),
)

CONTRACT_NAME: Final = "action-gate-triage"
POPULATION: Final = (
    "Authored support-routing example for the application action gate; "
    "demo evidence only, no deployment, population or calibration claim"
)


def gold_label(index: int) -> str:
    return ROUTED_LABELS[index % len(ROUTED_LABELS)]


def next_routed_label(label: str) -> str:
    return ROUTED_LABELS[(ROUTED_LABELS.index(label) + 1) % len(ROUTED_LABELS)]


def state_text(split: str, index: int) -> str:
    label = gold_label(index)
    templates = TEMPLATES[label]
    template = templates[(index // len(ROUTED_LABELS)) % len(templates)]
    ticket = f"GATE-{split.upper()}-{index:03d}"
    return template.format(ticket=ticket, number=3000 + index)


def case_rows(split: str, count: int) -> str:
    rows = []
    for index in range(count):
        row = {
            "case_id": f"gate-{split}-{index:03d}",
            "state": state_text(split, index),
            "expected_label": gold_label(index),
        }
        rows.append(json.dumps(row, ensure_ascii=False))
    return "".join(row + "\n" for row in rows)


def ticket_rows() -> str:
    rows = [
        json.dumps({"ticket_id": ticket_id, "text": text}, ensure_ascii=False)
        for ticket_id, text, _, _ in TICKETS
    ]
    return "".join(row + "\n" for row in rows)


def answer_body(selected: str, shape: str) -> str:
    """A fixture inner answer selecting ``selected`` with the named probability shape."""
    selected_probability, following = SHAPES[shape]
    start = LABELS.index(selected)
    ordered = [LABELS[(start + offset) % len(LABELS)] for offset in range(len(LABELS))]
    values = (selected_probability, *following)
    probabilities = {label: values[ordered.index(label)] for label in LABELS}
    return json.dumps({"type": "choice", "choice": selected, "probabilities": probabilities})


def unknown_body(choice: str) -> str:
    """An answer whose choice is not one of the question's options."""
    probabilities = dict.fromkeys(LABELS, 0.0)
    probabilities[LABELS[0]] = 1.0
    return json.dumps({"type": "choice", "choice": choice, "probabilities": probabilities})


def response_row(case_id: str, body: str | None, failure: str | None) -> str:
    row: dict[str, object] = {
        "case_id": case_id,
        "body_json": body,
        "failure_code": failure,
        "warnings": [],
    }
    return json.dumps(row, ensure_ascii=False)


def verification_response(index: int) -> str:
    case_id = f"gate-v-{index:03d}"
    gold = gold_label(index)
    slot = index % CYCLE
    if slot == ABSTAIN_SLOT:
        return response_row(case_id, answer_body(gold, "low"), None)
    if slot == TIMEOUT_SLOT:
        return response_row(case_id, None, "timeout")
    if slot == OTHER_SLOT:
        return response_row(case_id, answer_body("other", "confident"), None)
    if index == WRONG_INDEX:
        return response_row(case_id, answer_body(next_routed_label(gold), "confident"), None)
    return response_row(case_id, answer_body(gold, "confident"), None)


def ticket_response(ticket_id: str, kind: str, choice: str) -> str:
    if kind == "timeout":
        return response_row(ticket_id, None, "timeout")
    if kind == "unknown":
        return response_row(ticket_id, unknown_body(choice), None)
    if kind == "malformed":
        return response_row(ticket_id, "{", None)
    return response_row(ticket_id, answer_body(choice, kind), None)


def response_rows() -> str:
    rows = [verification_response(index) for index in range(VERIFICATION_CASES)]
    rows.extend(ticket_response(ticket_id, kind, choice) for ticket_id, _, kind, choice in TICKETS)
    return "".join(row + "\n" for row in rows)


def contract_toml() -> str:
    options = "".join(
        f'  {{label = "{label}", description = "{description}"}},\n'
        for label, description in OPTIONS
    )
    allowed = ", ".join(f'"{label}"' for label in ROUTED_LABELS)
    return (
        "schema_version = 1\n"
        f'name = "{CONTRACT_NAME}"\n'
        'evidence_scope = "demo"\n'
        f'population = "{POPULATION}"\n'
        "\n"
        "[question]\n"
        'question_id = "queue"\n'
        'instructions = "Select the queue that should handle this ticket."\n'
        "options = [\n"
        f"{options}"
        "]\n"
        "\n"
        "[policy]\n"
        f"allowed_labels = [{allowed}]\n"
        f"threshold = {THRESHOLD}\n"
        "\n"
        "[risk]\n"
        "max_risk = 0.05\n"
        "min_coverage = 0.50\n"
        "alpha = 0.05\n"
    )


def generate() -> dict[str, str]:
    """Return the five example files as ``{filename: text}``."""
    return {
        "contract.toml": contract_toml(),
        "calibration.jsonl": case_rows("c", CALIBRATION_CASES),
        "verification.jsonl": case_rows("v", VERIFICATION_CASES),
        "responses.jsonl": response_rows(),
        "tickets.jsonl": ticket_rows(),
    }


def write(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, text in generate().items():
        with (directory / name).open("x", encoding="utf-8", newline="") as handle:
            handle.write(text)


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        sys.stderr.write("usage: generate_data.py DIRECTORY\n")
        return 2
    write(Path(argv[0]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
