"""Semantic replay forgeries through the public bundle format, ``replay`` and the CLI.

A real good bundle is produced by the public protocol, copied, edited on the
wire and then *rehashed*: every per-file hash and the manifest self-hash are
recomputed with ``hashlib``/``json`` here, so ordinary integrity checks pass
and only semantic replay can notice. Each forgery must ERROR both through
``replay()`` and through the ``actseal replay`` subprocess anchored with the
ORIGINAL trusted lock digest. The T40 review follow-up (a rehashed
``fallback_used`` forgery that keeps the stored ACT/PASS) is included. A wholly
coherent rewrite that reseals a changed lock is documented as the ADR 0005
boundary: the external lock digest catches it, nothing else can.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest
from acceptance_support import (
    LABELS,
    MODULE_ENTRY,
    ScriptedModel,
    Workspace,
    answer_body,
    canonical,
    contract_toml,
    document_bytes,
    expected_bounds,
    nested,
    read_document,
    read_rows,
    rehash_bundle,
    reseal_lock,
    rows_bytes,
    run_cli,
    sha256_hex,
    write_workspace,
)

from actseal.adapters.fixture import FixtureModel
from actseal.assessment import assess
from actseal.errors import IntegrityError
from actseal.evidence import write_bundle
from actseal.records import (
    DecisionRecord,
    EvidenceBundle,
    FaultResult,
    Interval,
    PlanLock,
    Verdict,
)
from actseal.replay import replay
from actseal.runner import lock_run, verify_run
from actseal.serialization import from_data

RECORDS = "records.jsonl"
FAULTS = "faults.jsonl"
VERDICT = "verdict.json"
LOCK = "lock.json"
VERIFICATION = "verification.jsonl"
HASH_LEVEL = {"integrity.bundle_hash", "integrity.bundle_schema", "integrity.bundle_io"}


@pytest.fixture(scope="module")
def good(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, EvidenceBundle]:
    """A real PASS bundle with one genuine accepted error (30 cases, max_risk 0.2)."""
    base = tmp_path_factory.mktemp("good")
    workspace = write_workspace(
        base / "ws", count=30, wrong=[0], contract=contract_toml(max_risk=0.2), prefix="fg"
    )
    lock_path = base / "lock.json"
    lock_run(
        workspace.contract,
        workspace.calibration,
        workspace.verification,
        lock_path,
        model_factory=lambda: FixtureModel(workspace.responses),
    )
    bundle, out = verify_run(
        lock_path,
        workspace.calibration,
        workspace.verification,
        base / "evidence",
        provider="fixture",
        model_factory=lambda: FixtureModel(workspace.responses),
    )
    assert bundle.verdict.status == "PASS"
    assert (bundle.verdict.total, bundle.verdict.accepted, bundle.verdict.errors) == (30, 30, 1)
    assert replay(out, expected_lock_sha256=bundle.lock.sha256) == bundle.verdict
    return out, bundle


def copy_bundle(source: Path, tmp_path: Path) -> Path:
    target = tmp_path / "forged"
    shutil.copytree(source, target)
    return target


def observed_lock_sha256(bundle_dir: Path) -> str:
    """The seal recorded in the (possibly resealed) lock document on disk."""
    return str(read_document(bundle_dir / LOCK)["sha256"])


def assert_semantic_error(verdict: Verdict, observed: str, *required: str) -> None:
    assert verdict.status == "ERROR"
    assert (verdict.total, verdict.accepted, verdict.errors) == (0, 0, 0)
    assert verdict.lock_sha256 == observed  # the decoded seal, never the expectation
    reasons = set(verdict.reasons)
    assert not reasons & HASH_LEVEL, verdict.reasons  # ordinary hashes were consistent
    assert all(reason.startswith("integrity.") for reason in reasons), verdict.reasons
    assert set(required) <= reasons, verdict.reasons


def assert_cli_error_with_anchor(bundle_dir: Path, anchor: str, observed: str, cwd: Path) -> None:
    result = run_cli(
        MODULE_ENTRY,
        ["replay", str(bundle_dir), "--expected-lock-sha256", anchor, "--json"],
        cwd=cwd,
    )
    assert result.code == 3, result.stderr
    document = result.json()
    assert document["status"] == "ERROR"
    assert document["lock_sha256"] == observed
    assert document["expected_lock_sha256"] == anchor
    reasons = document["reasons"]
    assert isinstance(reasons, list)
    assert reasons
    assert all(isinstance(reason, str) and reason.startswith("integrity.") for reason in reasons)
    assert not set(reasons) & HASH_LEVEL


# --------------------------------------------------------------------------- #
# Record, fault and verdict forgeries with recomputed ordinary hashes
# --------------------------------------------------------------------------- #

Forgery = Callable[[Path], None]


def _record_forgeries() -> dict[str, tuple[Forgery, set[str]]]:
    def fallback_capture_only(bundle: Path) -> None:
        # T40 follow-up: the capture now claims a designed fallback produced the body
        # while the stored outcome and decision still say ACT; the verdict still says PASS.
        rows = read_rows(bundle / RECORDS)
        nested(rows[3], "capture")["fallback_used"] = True
        assert nested(rows[3], "decision")["action"] == "ACT"
        rehash_bundle(bundle, {RECORDS: rows_bytes(rows)})

    def fallback_flags_everywhere_but_act_kept(bundle: Path) -> None:
        rows = read_rows(bundle / RECORDS)
        nested(rows[3], "capture")["fallback_used"] = True
        nested(rows[3], "outcome")["fallback_used"] = True
        nested(rows[3], "decision")["fallback_used"] = True
        assert nested(rows[3], "decision")["action"] == "ACT"
        rehash_bundle(bundle, {RECORDS: rows_bytes(rows)})

    def inflated_probabilities(bundle: Path) -> None:
        rows = read_rows(bundle / RECORDS)
        outcome = nested(rows[4], "outcome")
        choice = str(outcome["choice"])
        rest = (1.0 - 0.99) / 2
        outcome["probabilities"] = [[label, 0.99 if label == choice else rest] for label in LABELS]
        outcome["selected_probability"] = 0.99
        rehash_bundle(bundle, {RECORDS: rows_bytes(rows)})

    def relabelled_wrong_decision(bundle: Path) -> None:
        # The one genuine error is rewritten to the gold label and the verdict's error
        # count is lowered to match: stored ACT choice, outcome and counts all forged.
        rows = read_rows(bundle / RECORDS)
        verdict = read_document(bundle / VERDICT)
        lock = read_document(bundle / LOCK)
        cases = lock["verification_cases"]
        assert isinstance(cases, list)
        gold = str(cases[0]["expected_label"])
        outcome = nested(rows[0], "outcome")
        assert outcome["choice"] != gold
        outcome["choice"] = gold
        outcome["probabilities"] = [[label, 0.95 if label == gold else 0.025] for label in LABELS]
        nested(rows[0], "decision")["choice"] = gold
        verdict["errors"] = 0
        rehash_bundle(bundle, {RECORDS: rows_bytes(rows), VERDICT: document_bytes(verdict)})

    def stored_verdict_counts(bundle: Path) -> None:
        verdict = read_document(bundle / VERDICT)
        verdict["errors"] = 0
        nested(verdict, "risk")["upper"] = 0.01
        rehash_bundle(bundle, {VERDICT: document_bytes(verdict)})

    def stored_verdict_status(bundle: Path) -> None:
        verdict = read_document(bundle / VERDICT)
        verdict["status"] = "BLOCK"
        verdict["reasons"] = ["risk.exceeds_limit"]
        rehash_bundle(bundle, {VERDICT: document_bytes(verdict)})

    return {
        "fallback_capture_only": (
            fallback_capture_only,
            {"integrity.outcome", "integrity.decision", "integrity.verdict"},
        ),
        "fallback_flags_everywhere_but_act_kept": (
            fallback_flags_everywhere_but_act_kept,
            {"integrity.decision", "integrity.verdict"},
        ),
        "inflated_probabilities": (
            inflated_probabilities,
            {"integrity.outcome", "integrity.verdict"},
        ),
        "relabelled_wrong_decision": (
            relabelled_wrong_decision,
            {"integrity.outcome", "integrity.decision", "integrity.verdict"},
        ),
        "stored_verdict_counts": (stored_verdict_counts, {"integrity.verdict"}),
        "stored_verdict_status": (stored_verdict_status, {"integrity.verdict"}),
    }


def _fault_and_lock_forgeries() -> dict[str, tuple[Forgery, set[str]]]:
    def swapped_scenario_captures(bundle: Path) -> None:
        rows = read_rows(bundle / FAULTS)
        unknown, low = rows[4], rows[5]
        rows[4] = {**low, "scenario_id": unknown["scenario_id"]}
        rows[5] = {**unknown, "scenario_id": low["scenario_id"]}
        rehash_bundle(bundle, {FAULTS: rows_bytes(rows)})

    def edited_scenario_capture(bundle: Path) -> None:
        # low_confidence rewritten into an ordinary confident answer with a coherent ACT.
        rows = read_rows(bundle / FAULTS)
        capture = nested(rows[5], "capture")
        body = json.loads(str(capture["body_json"]))
        selected = str(body["choice"])
        body["probabilities"] = {label: 1.0 if label == selected else 0.0 for label in LABELS}
        capture["body_json"] = canonical(body).decode("utf-8")
        rows[5]["outcome"] = {
            "kind": "answer",
            "choice": selected,
            "probabilities": [[label, 1.0 if label == selected else 0.0] for label in LABELS],
            "selected_probability": 1.0,
            "provider_confidence": None,
            "warnings": [],
            "fallback_used": False,
        }
        rows[5]["decision"] = {
            "action": "ACT",
            "choice": selected,
            "reason": "policy.allowed",
            "fallback_used": False,
        }
        rehash_bundle(bundle, {FAULTS: rows_bytes(rows)})

    def missing_scenario(bundle: Path) -> None:
        rows = read_rows(bundle / FAULTS)
        rows.pop(2)
        rehash_bundle(bundle, {FAULTS: rows_bytes(rows)})

    def duplicated_scenario(bundle: Path) -> None:
        rows = read_rows(bundle / FAULTS)
        rows[1] = dict(rows[0])
        rehash_bundle(bundle, {FAULTS: rows_bytes(rows)})

    def gold_reference_in_raw_dataset(bundle: Path) -> None:
        text = (bundle / VERIFICATION).read_text(encoding="utf-8")
        assert '"expected_label": "technical"' in text
        edited = text.replace('"expected_label": "technical"', '"expected_label": "sales"', 1)
        rehash_bundle(bundle, {VERIFICATION: edited.encode("utf-8")})

    def gold_reference_in_lock_only(bundle: Path) -> None:
        lock = read_document(bundle / LOCK)
        cases = lock["verification_cases"]
        assert isinstance(cases, list)
        cases[1]["expected_label"] = "sales"
        rehash_bundle(bundle, {LOCK: document_bytes(reseal_lock(lock))})

    def threshold_in_lock(bundle: Path) -> None:
        lock = read_document(bundle / LOCK)
        nested(lock, "contract", "policy")["threshold"] = 0.96
        rehash_bundle(bundle, {LOCK: document_bytes(reseal_lock(lock))})

    def model_revision_in_lock(bundle: Path) -> None:
        lock = read_document(bundle / LOCK)
        nested(lock, "model_identity")["revision"] = "f" * 64
        rehash_bundle(bundle, {LOCK: document_bytes(reseal_lock(lock))})

    return {
        "swapped_scenario_captures": (
            swapped_scenario_captures,
            {"integrity.fault_request", "integrity.fault_capture", "integrity.verdict"},
        ),
        "edited_scenario_capture": (
            edited_scenario_capture,
            {"integrity.fault_capture", "integrity.verdict"},
        ),
        "missing_scenario": (missing_scenario, {"integrity.faults", "integrity.verdict"}),
        "duplicated_scenario": (duplicated_scenario, {"integrity.faults", "integrity.verdict"}),
        "gold_reference_in_raw_dataset": (gold_reference_in_raw_dataset, {"integrity.inputs"}),
        "gold_reference_in_lock_only": (gold_reference_in_lock_only, {"integrity.expected_lock"}),
        "threshold_in_lock": (threshold_in_lock, {"integrity.expected_lock"}),
        "model_revision_in_lock": (model_revision_in_lock, {"integrity.expected_lock"}),
    }


def _forgeries() -> dict[str, tuple[Forgery, set[str]]]:
    return {**_record_forgeries(), **_fault_and_lock_forgeries()}


@pytest.mark.parametrize("name", sorted(_forgeries()))
def test_rehashed_forgeries_error_under_the_original_lock_digest(
    good: tuple[Path, EvidenceBundle], tmp_path: Path, name: str
) -> None:
    source, bundle = good
    forged = copy_bundle(source, tmp_path)
    mutate, required = _forgeries()[name]
    mutate(forged)
    anchor = bundle.lock.sha256
    observed = observed_lock_sha256(forged)
    verdict = replay(forged, expected_lock_sha256=anchor)
    assert_semantic_error(verdict, observed, *required)
    assert_cli_error_with_anchor(forged, anchor, observed, tmp_path)
    assert replay(source, expected_lock_sha256=anchor) == bundle.verdict  # untouched original


@pytest.mark.parametrize(
    "name",
    [
        "fallback_capture_only",
        "fallback_flags_everywhere_but_act_kept",
        "inflated_probabilities",
        "relabelled_wrong_decision",
        "stored_verdict_counts",
        "swapped_scenario_captures",
        "edited_scenario_capture",
        "gold_reference_in_raw_dataset",
    ],
)
def test_same_lock_forgeries_error_even_without_an_external_anchor(
    good: tuple[Path, EvidenceBundle], tmp_path: Path, name: str
) -> None:
    """These forgeries keep the lock intact, so semantic replay alone must catch them."""
    source, bundle = good
    forged = copy_bundle(source, tmp_path)
    mutate, required = _forgeries()[name]
    mutate(forged)
    verdict = replay(forged)
    assert_semantic_error(verdict, bundle.lock.sha256, *required)
    assert observed_lock_sha256(forged) == bundle.lock.sha256
    result = run_cli(MODULE_ENTRY, ["replay", str(forged), "--json"], cwd=tmp_path)
    assert result.code == 3
    assert result.json()["status"] == "ERROR"


def test_coherent_resealed_lock_rewrite_is_caught_only_by_the_external_digest(
    good: tuple[Path, EvidenceBundle], tmp_path: Path
) -> None:
    """A gold-label change that updates lock, inventory, raw bytes AND verdict coherently.

    This rewrite RESEALS A CHANGED LOCK (it is not a same-lock forgery), so the
    trusted external digest catches it. Without an anchor the rewritten bundle
    replays as its own (different) experiment: ADR 0005 states that hash anchors
    cannot authenticate a wholly coherent rewrite, and this test records that
    limit instead of inventing a stronger guarantee.
    """
    source, bundle = good
    forged = copy_bundle(source, tmp_path)
    lock = read_document(forged / LOCK)
    cases = lock["verification_cases"]
    inventory = lock["verification_inventory"]
    assert isinstance(cases, list)
    assert isinstance(inventory, list)
    case = cases[1]
    assert case["expected_label"] == "technical"
    case["expected_label"] = "sales"
    inventory[1]["sha256"] = sha256_hex(canonical(case))
    text = (forged / VERIFICATION).read_text(encoding="utf-8")
    raw = text.replace('"expected_label": "technical"', '"expected_label": "sales"', 1).encode()
    lock["verification_sha256"] = sha256_hex(raw)
    resealed = reseal_lock(lock)
    new_lock = from_data(PlanLock, resealed)
    records = tuple(from_data(DecisionRecord, row) for row in read_rows(forged / RECORDS))
    faults = tuple(from_data(FaultResult, row) for row in read_rows(forged / FAULTS))
    coherent = assess(records, new_lock, faults)
    assert coherent.status != "ERROR"
    assert coherent.errors == 2  # the relabelled case is now counted as a second error
    rehash_bundle(
        forged,
        {
            LOCK: document_bytes(resealed),
            VERIFICATION: raw,
            VERDICT: document_bytes(json.loads(canonical(_verdict_data(coherent)))),
        },
    )
    anchored = replay(forged, expected_lock_sha256=bundle.lock.sha256)
    assert anchored.status == "ERROR"
    assert anchored.reasons == ("integrity.expected_lock",)
    assert anchored.lock_sha256 == new_lock.sha256  # observed digest, not the expectation
    assert_cli_error_with_anchor(forged, bundle.lock.sha256, new_lock.sha256, tmp_path)
    unanchored = replay(forged)
    assert unanchored == coherent  # documented limit: a coherent resealed rewrite replays as itself
    assert unanchored.lock_sha256 != bundle.lock.sha256


def _verdict_data(verdict: Verdict) -> dict[str, object]:
    return {
        "status": verdict.status,
        "reasons": list(verdict.reasons),
        "total": verdict.total,
        "accepted": verdict.accepted,
        "errors": verdict.errors,
        "risk": {"lower": verdict.risk.lower, "upper": verdict.risk.upper},
        "coverage": {"lower": verdict.coverage.lower, "upper": verdict.coverage.upper},
        "evidence_scope": verdict.evidence_scope,
        "lock_sha256": verdict.lock_sha256,
    }


# --------------------------------------------------------------------------- #
# Faithful fallback and the writer's own refusal
# --------------------------------------------------------------------------- #


def test_faithful_fallback_is_escalate_and_replays(tmp_path: Path) -> None:
    workspace: Workspace = write_workspace(tmp_path / "ws", count=9, prefix="ff")
    gold = {cid: label for cid, _, label in workspace.cases}
    identity = FixtureModel(workspace.responses).identity()

    def script(case_id: str) -> tuple[str | None, str | None, tuple[str, ...], bool]:
        return answer_body(gold[case_id]), None, ("adapter.fallback_recommendation",), True

    lock_path = tmp_path / "lock.json"
    lock_run(
        workspace.contract,
        workspace.calibration,
        workspace.verification,
        lock_path,
        model_factory=lambda: ScriptedModel(identity, script),
    )
    bundle, out = verify_run(
        lock_path,
        workspace.calibration,
        workspace.verification,
        tmp_path / "evidence",
        provider="fixture",
        model_factory=lambda: ScriptedModel(identity, script),
    )
    assert all(record.capture.fallback_used for record in bundle.records)
    assert {record.decision.action for record in bundle.records} == {"ESCALATE"}
    assert {record.decision.reason for record in bundle.records} == {"policy.fallback_used"}
    verdict = bundle.verdict
    assert (verdict.total, verdict.accepted, verdict.errors) == (9, 0, 0)
    # Independently: zero accepted out of nine puts the coverage upper bound below 0.5.
    limits = bundle.lock.contract.limits
    assert expected_bounds(9, 0, 0, limits.alpha)[1][1] < limits.min_coverage
    assert verdict.status == "BLOCK"
    assert verdict.reasons == ("coverage.below_minimum", "risk.no_accepted_cases")
    assert verdict.risk == Interval(0.0, 1.0)
    assert replay(out, expected_lock_sha256=bundle.lock.sha256) == verdict
    result = run_cli(MODULE_ENTRY, ["replay", str(out), "--json"], cwd=tmp_path)
    assert result.code == 1
    assert result.json()["reasons"] == ["coverage.below_minimum", "risk.no_accepted_cases"]


def test_writer_refuses_a_bundle_whose_verdict_was_authored(
    good: tuple[Path, EvidenceBundle], tmp_path: Path
) -> None:
    _, bundle = good
    authored = Verdict(
        "PASS",
        ("contract.satisfied",),
        bundle.verdict.total,
        bundle.verdict.accepted,
        0,
        bundle.verdict.risk,
        bundle.verdict.coverage,
        bundle.verdict.evidence_scope,
        bundle.lock.sha256,
    )
    forged = EvidenceBundle(
        bundle.lock,
        bundle.calibration_jsonl,
        bundle.verification_jsonl,
        bundle.records,
        bundle.faults,
        authored,
    )
    with pytest.raises(IntegrityError, match="verdict"):
        write_bundle(forged, tmp_path / "authored")
    assert not (tmp_path / "authored").exists()
    assert [p.name for p in tmp_path.iterdir() if p.name.startswith(".actseal")] == []
