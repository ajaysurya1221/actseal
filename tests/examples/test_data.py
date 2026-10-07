"""The authored data: deterministic generator, labelled versus label-free files, frozen rules."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from actseal.contract import parse_cases, parse_contract, read_input_text
from actseal.errors import SchemaError
from examples.examples_support import DATA_FILES, EXAMPLE_DIR, GENERATOR

VERIFICATION_CASES = 160
CALIBRATION_CASES = 12
EXPECTED_COUNTS = {"ACT": 136, "ABSTAIN": 8, "ESCALATE": 8, "DENY": 8}


def test_generator_reproduces_every_committed_file_byte_for_byte(generator: ModuleType) -> None:
    files = generator.generate()
    assert set(files) == set(DATA_FILES)
    for name, text in files.items():
        assert (EXAMPLE_DIR / name).read_bytes() == text.encode("utf-8"), name


def test_generator_script_writes_once_and_refuses_to_overwrite(tmp_path: Path) -> None:
    out = tmp_path / "generated"
    first = subprocess.run(  # noqa: S603 - fixed interpreter and repository script
        [sys.executable, str(GENERATOR), str(out)],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert first.returncode == 0, first.stderr
    for name in DATA_FILES:
        assert (out / name).read_bytes() == (EXAMPLE_DIR / name).read_bytes(), name
    again = subprocess.run(  # noqa: S603 - fixed interpreter and repository script
        [sys.executable, str(GENERATOR), str(out)],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert again.returncode != 0
    usage = subprocess.run(  # noqa: S603 - fixed interpreter and repository script
        [sys.executable, str(GENERATOR)], capture_output=True, text=True, check=False, timeout=120
    )
    assert usage.returncode == 2
    assert "usage:" in usage.stderr


def test_tickets_are_label_free_and_splits_are_labelled() -> None:
    ticket_rows = [
        json.loads(line)
        for line in (EXAMPLE_DIR / "tickets.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(ticket_rows) == 8
    assert all(set(row) == {"ticket_id", "text"} for row in ticket_rows)
    assert b"expected_label" not in (EXAMPLE_DIR / "tickets.jsonl").read_bytes()
    assert b"expected_label" not in (EXAMPLE_DIR / "responses.jsonl").read_bytes()
    contract = parse_contract(EXAMPLE_DIR / "contract.toml")
    verification = parse_cases(
        read_input_text(EXAMPLE_DIR / "verification.jsonl"), contract.question
    )
    calibration = parse_cases(read_input_text(EXAMPLE_DIR / "calibration.jsonl"), contract.question)
    assert len(verification) == VERIFICATION_CASES
    assert len(calibration) == CALIBRATION_CASES
    split_ids = {case.case_id for case in verification} | {case.case_id for case in calibration}
    assert split_ids.isdisjoint(row["ticket_id"] for row in ticket_rows)
    assert all(case.expected_label in contract.policy.allowed_labels for case in verification)


def test_contract_follows_the_frozen_rules() -> None:
    contract = parse_contract(EXAMPLE_DIR / "contract.toml")
    assert contract.evidence_scope == "demo"
    assert contract.question.labels == ("billing", "technical", "sales", "other")
    assert contract.policy.allowed_labels == ("billing", "technical", "sales")
    assert contract.policy.threshold == 0.9
    assert (contract.limits.max_risk, contract.limits.min_coverage, contract.limits.alpha) == (
        0.05,
        0.5,
        0.05,
    )
    assert "demo evidence only" in contract.population


def test_fresh_verification_matches_the_prespecified_counts(fresh: Any) -> None:
    """The authored rules fix n, a and e; the verdict is whatever the pipeline computes."""
    actions = [record.decision.action for record in fresh.bundle.records]
    assert {action: actions.count(action) for action in EXPECTED_COUNTS} == EXPECTED_COUNTS
    verdict = fresh.bundle.verdict
    assert (verdict.total, verdict.accepted, verdict.errors) == (VERIFICATION_CASES, 136, 1)
    wrong = [
        record.case_id
        for record, case in zip(fresh.bundle.records, fresh.lock.verification_cases, strict=True)
        if record.decision.action == "ACT" and record.decision.choice != case.expected_label
    ]
    assert wrong == ["gate-v-042"]
    assert verdict.status == "PASS"
    assert verdict.risk.upper <= fresh.lock.contract.limits.max_risk
    assert verdict.coverage.lower >= fresh.lock.contract.limits.min_coverage
    assert all(
        fault.decision.action == spec.expected_action
        for fault, spec in zip(fresh.bundle.faults, fresh.lock.fault_inventory, strict=True)
    )


@pytest.mark.parametrize(
    "rows",
    [
        '{"ticket_id": "T-1", "text": "x", "expected_label": "billing"}\n',
        '{"ticket_id": "T-1", "text": "x"}\n{"ticket_id": "T-1", "text": "y"}\n',
        '{"ticket_id": "", "text": "x"}\n',
        '{"ticket_id": "T-1"}\n',
        "",
    ],
    ids=["label-smuggled", "duplicate-id", "empty-id", "missing-text", "empty-file"],
)
def test_ticket_loader_rejects_labels_duplicates_and_malformed_rows(
    run: ModuleType, tmp_path: Path, rows: str
) -> None:
    path = tmp_path / "tickets.jsonl"
    path.write_text(rows, encoding="utf-8")
    with pytest.raises(SchemaError):
        run.load_tickets(path)
