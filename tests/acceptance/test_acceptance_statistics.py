"""Statistical policy and denominator invariants through the public runner/assessment API.

Evidence is produced by the real ``lock_run``/``verify_run`` protocol around a
scripted or fixture ``DecisionModel``; records are then mutated with
``dataclasses.replace`` and handed to the real ``assess``/``replay``. Expected
statuses come from the frozen table applied to an independent Clopper-Pearson
oracle (binomial-tail bisection in floating point, written here without the
product's kernel). The T30 review follow-up injects an actual fault-policy
violation on the FIRST canonical fault through a narrow wrapper around the real
evaluator and proves the campaign still emits all six ordered terminal results.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest
from acceptance_support import (
    LABELS,
    ScriptedModel,
    Workspace,
    answer_body,
    contract_toml,
    expected_bounds,
    expected_status,
    laya_envelope,
    laya_identity,
    responses_jsonl,
    write_workspace,
)

import actseal.assessment as assessment_module
import actseal.faults as faults_module
from actseal.adapters.fixture import FixtureModel
from actseal.assessment import assess
from actseal.evidence import decode_rows
from actseal.faults import run_fault_campaign
from actseal.normalization import normalize, request_sha256
from actseal.policy import evaluate
from actseal.records import (
    ChoiceAnswer,
    ChoiceQuestion,
    DecisionRecord,
    DecisionRequest,
    EvidenceBundle,
    FaultResult,
    Interval,
    LockedPolicy,
    ModelIdentity,
    Option,
    PlanLock,
    PolicyDecision,
    ProviderFailure,
    Verdict,
)
from actseal.replay import replay
from actseal.runner import lock_run, verify_run

FULL = Interval(0.0, 1.0)
WORKER_INVALIDATED = "infrastructure.worker_invalidated"
Script = Callable[[str], tuple[str | None, str | None, tuple[str, ...], bool]]


# --------------------------------------------------------------------------- #
# Evidence production through the public protocol
# --------------------------------------------------------------------------- #


def fixture_run(
    tmp_path: Path, workspace: Workspace, *, name: str = "run"
) -> tuple[EvidenceBundle, Path]:
    lock_path = tmp_path / f"{name}.lock.json"
    lock_run(
        workspace.contract,
        workspace.calibration,
        workspace.verification,
        lock_path,
        model_factory=lambda: FixtureModel(workspace.responses),
    )
    return verify_run(
        lock_path,
        workspace.calibration,
        workspace.verification,
        tmp_path / f"{name}.evidence",
        provider="fixture",
        model_factory=lambda: FixtureModel(workspace.responses),
    )


def scripted_run(
    tmp_path: Path,
    workspace: Workspace,
    identity: ModelIdentity,
    script: Script,
    *,
    name: str = "run",
) -> tuple[EvidenceBundle, Path, ScriptedModel]:
    lock_path = tmp_path / f"{name}.lock.json"
    lock_run(
        workspace.contract,
        workspace.calibration,
        workspace.verification,
        lock_path,
        model_factory=lambda: ScriptedModel(identity, script),
    )
    model = ScriptedModel(identity, script)
    bundle, out = verify_run(
        lock_path,
        workspace.calibration,
        workspace.verification,
        tmp_path / f"{name}.evidence",
        provider=identity.provider,
        model_factory=lambda: model,
    )
    return bundle, out, model


def gold_of(workspace: Workspace) -> dict[str, str]:
    return {cid: label for cid, _, label in workspace.cases}


def index_of(workspace: Workspace, case_id: str) -> int:
    return [cid for cid, _, _ in workspace.cases].index(case_id)


def assert_error(verdict: Verdict, lock: PlanLock, *required: str) -> None:
    assert verdict.status == "ERROR"
    assert (verdict.total, verdict.accepted, verdict.errors) == (0, 0, 0)
    assert verdict.risk == FULL
    assert verdict.coverage == FULL
    assert verdict.lock_sha256 == lock.sha256
    assert all(reason.startswith("integrity.") for reason in verdict.reasons), verdict.reasons
    assert set(required) <= set(verdict.reasons), verdict.reasons


def assert_statistics_match_oracle(verdict: Verdict, lock: PlanLock) -> None:
    limits = lock.contract.limits
    risk, coverage = expected_bounds(verdict.total, verdict.accepted, verdict.errors, limits.alpha)
    assert verdict.risk.lower == pytest.approx(risk[0], abs=1e-9)
    assert verdict.risk.upper == pytest.approx(risk[1], abs=1e-9)
    assert verdict.coverage.lower == pytest.approx(coverage[0], abs=1e-9)
    assert verdict.coverage.upper == pytest.approx(coverage[1], abs=1e-9)
    assert verdict.status == expected_status(
        verdict.total,
        verdict.accepted,
        verdict.errors,
        max_risk=limits.max_risk,
        min_coverage=limits.min_coverage,
        alpha=limits.alpha,
    )


# --------------------------------------------------------------------------- #
# Acceptance 2: exact inventory enforcement
# --------------------------------------------------------------------------- #

Mutation = Callable[[list[DecisionRecord], list[FaultResult], PlanLock], None]


def _other_question() -> ChoiceQuestion:
    return ChoiceQuestion(
        "department",
        "A different instruction text yields a different request hash.",
        tuple(Option(label, f"{label} desk") for label in LABELS),
    )


def _mutations() -> dict[str, tuple[Mutation, set[str]]]:
    def omitted(records: list[DecisionRecord], _f: list[FaultResult], _l: PlanLock) -> None:
        records.pop()

    def duplicated(records: list[DecisionRecord], _f: list[FaultResult], _l: PlanLock) -> None:
        records[-1] = records[-2]

    def foreign(records: list[DecisionRecord], _f: list[FaultResult], _l: PlanLock) -> None:
        records[-1] = replace(records[-1], case_id="foreign-9999")

    def reordered(records: list[DecisionRecord], _f: list[FaultResult], _l: PlanLock) -> None:
        records[0], records[1] = records[1], records[0]

    def swapped_hashes(records: list[DecisionRecord], _f: list[FaultResult], _l: PlanLock) -> None:
        first, second = records[0].capture.request_sha256, records[1].capture.request_sha256
        records[0] = replace(records[0], capture=replace(records[0].capture, request_sha256=second))
        records[1] = replace(records[1], capture=replace(records[1].capture, request_sha256=first))

    def swapped_question(
        records: list[DecisionRecord], _f: list[FaultResult], lock: PlanLock
    ) -> None:
        case = lock.verification_cases[2]
        digest = request_sha256(DecisionRequest(case.case_id, case.state, _other_question()))
        records[2] = replace(records[2], capture=replace(records[2].capture, request_sha256=digest))

    def extra(records: list[DecisionRecord], _f: list[FaultResult], _l: PlanLock) -> None:
        records.append(records[0])

    def missing_fault(_r: list[DecisionRecord], faults: list[FaultResult], _l: PlanLock) -> None:
        faults.pop()

    def duplicated_fault(_r: list[DecisionRecord], faults: list[FaultResult], _l: PlanLock) -> None:
        faults[-1] = faults[-2]

    def swapped_faults(_r: list[DecisionRecord], faults: list[FaultResult], _l: PlanLock) -> None:
        unknown, low = faults[4], faults[5]
        faults[4] = replace(low, scenario_id=unknown.scenario_id)
        faults[5] = replace(unknown, scenario_id=low.scenario_id)

    def reordered_faults(_r: list[DecisionRecord], faults: list[FaultResult], _l: PlanLock) -> None:
        faults[0], faults[1] = faults[1], faults[0]

    return {
        "omitted_record": (omitted, {"integrity.records"}),
        "duplicated_record": (duplicated, {"integrity.records"}),
        "foreign_record": (foreign, {"integrity.records"}),
        "reordered_records": (reordered, {"integrity.records"}),
        "extra_record": (extra, {"integrity.records"}),
        "swapped_request_hashes": (swapped_hashes, {"integrity.request_hash"}),
        "swapped_question_hash": (swapped_question, {"integrity.request_hash"}),
        "missing_fault": (missing_fault, {"integrity.faults"}),
        "duplicated_fault": (duplicated_fault, {"integrity.faults"}),
        "reordered_faults": (reordered_faults, {"integrity.faults"}),
        "swapped_fault_scenarios": (
            swapped_faults,
            {"integrity.fault_request", "integrity.fault_capture"},
        ),
    }


@pytest.mark.parametrize("name", sorted(_mutations()))
def test_inventory_defects_are_errors_never_counts(tmp_path: Path, name: str) -> None:
    workspace = write_workspace(tmp_path / "ws", count=9, wrong=[0], prefix="inv")
    bundle, _ = fixture_run(tmp_path, workspace)
    assert bundle.verdict.status == "INCONCLUSIVE"
    mutate, required = _mutations()[name]
    records, faults = list(bundle.records), list(bundle.faults)
    mutate(records, faults, bundle.lock)
    assert_error(assess(records, bundle.lock, faults), bundle.lock, *required)


def test_canonical_faults_from_another_lock_are_rejected(tmp_path: Path) -> None:
    workspace = write_workspace(tmp_path / "ws", count=6, prefix="cf")
    bundle, _ = fixture_run(tmp_path, workspace)
    other_contract = contract_toml(name="other")
    other_contract = other_contract.replace(
        "Select the department responsible for this ticket.", "Route this ticket."
    )
    other = write_workspace(tmp_path / "other", count=6, prefix="cf2", contract=other_contract)
    other_bundle, _ = fixture_run(tmp_path, other, name="other")
    foreign_faults = run_fault_campaign(other_bundle.lock)
    assert [f.scenario_id for f in foreign_faults] == [f.scenario_id for f in bundle.faults]
    assert_error(
        assess(bundle.records, bundle.lock, foreign_faults), bundle.lock, "integrity.fault_request"
    )


# --------------------------------------------------------------------------- #
# Acceptance 2: denominators, worker loss, fallback
# --------------------------------------------------------------------------- #


def test_nonfatal_failures_stay_in_the_denominator_without_act(tmp_path: Path) -> None:
    workspace = write_workspace(
        tmp_path / "ws",
        count=15,
        wrong=[3],
        failures={1: "provider_error", 4: "rate_limit", 7: "timeout"},
        prefix="den",
    )
    rows: dict[str, tuple[str | None, str | None]] = {
        cid: (answer_body(label), None) if idx != 9 else ("{", None)
        for idx, (cid, _, label) in enumerate(workspace.cases)
    }
    rows[workspace.cases[1][0]] = (None, "provider_error")
    rows[workspace.cases[4][0]] = (None, "rate_limit")
    rows[workspace.cases[7][0]] = (None, "timeout")
    wrong_cid, _, wrong_gold = workspace.cases[3]
    rows[wrong_cid] = (answer_body(LABELS[(LABELS.index(wrong_gold) + 1) % 3]), None)
    workspace.responses.write_bytes(responses_jsonl(rows).encode("utf-8"))
    bundle, out = fixture_run(tmp_path, workspace)
    verdict = bundle.verdict
    assert (verdict.total, verdict.accepted, verdict.errors) == (15, 11, 1)
    reasons = {
        record.decision.reason for record in bundle.records if record.decision.action != "ACT"
    }
    assert reasons == {
        "provider.provider_error",
        "provider.rate_limit",
        "provider.timeout",
        "provider.malformed_response",
    }
    assert all(
        record.decision.action == "ESCALATE" and record.decision.choice is None
        for record in bundle.records
        if isinstance(record.outcome, ProviderFailure)
    )
    assert verdict.status != "ERROR"  # a fixture timeout is a nonfatal captured failure
    assert_statistics_match_oracle(verdict, bundle.lock)
    assert replay(out, expected_lock_sha256=bundle.lock.sha256) == verdict


def worker_loss_script(workspace: Workspace, *, lost_at: int, code: str) -> Script:
    gold = gold_of(workspace)

    def script(case_id: str) -> tuple[str | None, str | None, tuple[str, ...], bool]:
        index = index_of(workspace, case_id)
        if index < lost_at:
            return laya_envelope(gold[case_id]), None, (), False
        if index == lost_at:
            return None, code, (), False
        return None, "unavailable", (f"laya.unavailable:{code}",), False

    return script


@pytest.mark.parametrize("code", ["timeout", "unavailable"])
def test_regular_laya_worker_loss_is_a_complete_diagnostic_error(tmp_path: Path, code: str) -> None:
    workspace = write_workspace(tmp_path / "ws", count=9, prefix="wl")
    bundle, out, model = scripted_run(
        tmp_path, workspace, laya_identity(), worker_loss_script(workspace, lost_at=3, code=code)
    )
    assert [cid for cid, _ in model.calls] == [cid for cid, _, _ in workspace.cases]
    assert {timeout for _, timeout in model.calls} == {30.0}
    assert model.closed == 1
    assert len(bundle.records) == 9
    for record in bundle.records[:3]:
        assert isinstance(record.outcome, ChoiceAnswer)
        assert record.decision.action == "ACT"
        assert record.decision.choice == gold_of(workspace)[record.case_id]
    assert bundle.records[3].capture.failure_code == code
    assert bundle.records[3].decision.reason == f"provider.{code}"
    assert all(r.capture.failure_code == "unavailable" for r in bundle.records[4:])
    verdict = bundle.verdict
    assert verdict.status == "ERROR"
    assert verdict.reasons == (WORKER_INVALIDATED,)
    assert (verdict.total, verdict.accepted, verdict.errors) == (0, 0, 0)
    assert verdict.risk == FULL
    assert verdict.coverage == FULL
    written = decode_rows("records.jsonl", (out / "records.jsonl").read_bytes(), DecisionRecord)
    assert written == bundle.records
    assert len(bundle.faults) == 6
    assert replay(out, expected_lock_sha256=bundle.lock.sha256) == verdict


def test_synthetic_fault_transport_failures_never_invalidate_a_healthy_laya_run(
    tmp_path: Path,
) -> None:
    workspace = write_workspace(tmp_path / "ws", count=9, prefix="hl")
    gold = gold_of(workspace)
    bundle, out, _ = scripted_run(
        tmp_path,
        workspace,
        laya_identity(),
        lambda case_id: (laya_envelope(gold[case_id]), None, (), False),
    )
    assert bundle.faults[0].capture.failure_code == "timeout"
    assert bundle.faults[1].capture.failure_code == "rate_limit"
    assert bundle.verdict.status == "INCONCLUSIVE"
    assert bundle.verdict.accepted == 9
    assert_statistics_match_oracle(bundle.verdict, bundle.lock)
    assert replay(out) == bundle.verdict


def test_fallback_flags_cannot_acquire_act(tmp_path: Path) -> None:
    policy = LockedPolicy(LABELS, LABELS, 0.9)
    probabilities = (("billing", 1.0), ("technical", 0.0), ("sales", 0.0))
    perfect = ChoiceAnswer("billing", probabilities, 1.0, 1.0, (), True)
    decision = evaluate(perfect, policy)
    assert decision == PolicyDecision("ESCALATE", None, "policy.fallback_used", True)
    workspace = write_workspace(tmp_path / "ws", count=9, prefix="fb")
    gold = gold_of(workspace)
    identity = FixtureModel(workspace.responses).identity()
    bundle, out, _ = scripted_run(
        tmp_path,
        workspace,
        identity,
        lambda case_id: (answer_body(gold[case_id]), None, (), index_of(workspace, case_id) < 2),
    )
    for record in bundle.records[:2]:
        assert record.capture.fallback_used is True
        assert record.outcome.fallback_used is True
        assert record.decision == PolicyDecision("ESCALATE", None, "policy.fallback_used", True)
    assert all(record.decision.action == "ACT" for record in bundle.records[2:])
    assert (bundle.verdict.total, bundle.verdict.accepted) == (9, 7)
    assert replay(out) == bundle.verdict


# --------------------------------------------------------------------------- #
# Acceptance 3: boundaries, zero accepted, no extra observations
# --------------------------------------------------------------------------- #


def test_threshold_boundary_gates_on_the_selected_probability(tmp_path: Path) -> None:
    workspace = write_workspace(tmp_path / "ws", count=6, prefix="th")
    rows: dict[str, tuple[str | None, str | None]] = {}
    for index, (cid, _, gold) in enumerate(workspace.cases):
        if index == 0:
            rows[cid] = (answer_body(gold, 0.9), None)  # exactly the threshold -> ACT
        elif index == 1:
            rows[cid] = (answer_body(gold, 0.8999), None)  # just below -> ABSTAIN
        elif index == 2:
            other = LABELS[(LABELS.index(gold) + 1) % 3]
            rows[cid] = (answer_body(other, 0.0), None)  # selected at 0.0; two labels hold 0.5
        else:
            rows[cid] = (answer_body(gold), None)
    workspace.responses.write_bytes(responses_jsonl(rows).encode("utf-8"))
    bundle, out = fixture_run(tmp_path, workspace)
    first, second, third = bundle.records[:3]
    assert isinstance(first.outcome, ChoiceAnswer)
    assert first.outcome.selected_probability == 0.9
    assert first.decision.action == "ACT"
    assert second.decision == PolicyDecision("ABSTAIN", None, "policy.low_confidence", False)
    assert isinstance(third.outcome, ChoiceAnswer)
    assert third.outcome.selected_probability == 0.0
    assert max(p for _, p in third.outcome.probabilities) == 0.5
    assert third.decision.action == "ABSTAIN"  # no argmax substitution
    assert (bundle.verdict.total, bundle.verdict.accepted, bundle.verdict.errors) == (6, 4, 0)
    assert replay(out) == bundle.verdict


def test_zero_accepted_cases_can_never_pass(tmp_path: Path) -> None:
    lenient = contract_toml(name="lenient", max_risk=1.0, min_coverage=0.0)
    workspace = write_workspace(
        tmp_path / "ws", count=6, selected=0.5, contract=lenient, prefix="za"
    )
    bundle, out = fixture_run(tmp_path, workspace)
    verdict = bundle.verdict
    assert all(record.decision.action == "ABSTAIN" for record in bundle.records)
    assert verdict.status == "INCONCLUSIVE"
    assert verdict.reasons == ("evidence.insufficient", "risk.no_accepted_cases")
    assert (verdict.total, verdict.accepted, verdict.errors) == (6, 0, 0)
    assert verdict.risk == FULL
    assert_statistics_match_oracle(verdict, bundle.lock)
    assert replay(out) == verdict


def test_mixed_evidence_matches_the_exact_oracle(tmp_path: Path) -> None:
    workspace = write_workspace(
        tmp_path / "ws", count=21, wrong=[0, 5], failures={2: "rate_limit"}, prefix="mx"
    )
    bundle, _ = fixture_run(tmp_path, workspace)
    assert (bundle.verdict.total, bundle.verdict.accepted, bundle.verdict.errors) == (21, 20, 2)
    assert_statistics_match_oracle(bundle.verdict, bundle.lock)


def test_repeating_or_replaying_a_run_adds_no_observations(tmp_path: Path) -> None:
    workspace = write_workspace(tmp_path / "ws", count=9, prefix="rp")
    first, out_a = fixture_run(tmp_path, workspace, name="a")
    second, out_b = fixture_run(tmp_path, workspace, name="b")
    assert first.verdict.total == second.verdict.total == 9
    assert first.records == second.records
    assert replay(out_a) == replay(out_a) == first.verdict
    assert replay(out_b).total == 9
    doubled = (*first.records, *second.records)
    assert_error(assess(doubled, first.lock, first.faults), first.lock, "integrity.records")


# --------------------------------------------------------------------------- #
# T30 review follow-up: an actual injected fault-policy violation
# --------------------------------------------------------------------------- #


def _violating_wrapper(
    delegated: list[str], injected: list[str]
) -> Callable[[ChoiceAnswer | ProviderFailure, LockedPolicy], PolicyDecision]:
    """Wrap the real evaluator: wrong ACT for the FIRST fault (timeout) only, delegate the rest.

    The timeout scenario is the first of the six canonical faults, so a campaign
    that stopped at the violation would emit one result instead of six. The
    ordinary verification records used with this wrapper carry no timeout, so the
    assessor's record re-evaluation is untouched by the injected branch.
    """
    real = evaluate

    def wrapper(outcome: ChoiceAnswer | ProviderFailure, policy: LockedPolicy) -> PolicyDecision:
        if isinstance(outcome, ProviderFailure) and outcome.code == "timeout":
            injected.append(outcome.code)
            return PolicyDecision("ACT", policy.allowed_labels[0], "policy.allowed", False)
        decision = real(outcome, policy)
        delegated.append(decision.action)
        return decision

    return wrapper


EXPECTED_FAULT_ACTIONS = ["ESCALATE", "ESCALATE", "ESCALATE", "ESCALATE", "DENY", "ABSTAIN"]
VIOLATED_FAULT_ACTIONS = ["ACT", "ESCALATE", "ESCALATE", "ESCALATE", "DENY", "ABSTAIN"]


def test_injected_first_fault_violation_keeps_all_six_ordered_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = write_workspace(tmp_path / "ws", count=6, prefix="fv")
    bundle, _ = fixture_run(tmp_path, workspace)
    lock = bundle.lock
    assert [s.expected_action for s in lock.fault_inventory] == EXPECTED_FAULT_ACTIONS
    assert all(r.capture.failure_code is None for r in bundle.records)  # no regular timeout
    delegated: list[str] = []
    injected: list[str] = []
    monkeypatch.setattr(faults_module, "evaluate", _violating_wrapper(delegated, injected))
    faults = run_fault_campaign(lock)
    assert [f.scenario_id for f in faults] == [s.scenario_id for s in lock.fault_inventory]
    assert [f.scenario_id for f in faults] == [
        "fault.timeout",
        "fault.rate_limit",
        "fault.malformed_response",
        "fault.identity_mismatch",
        "fault.unknown_choice",
        "fault.low_confidence",
    ]
    # The violation happened on the first scenario; the five later scenarios were
    # still evaluated by the real evaluator, in order, after it.
    assert injected == ["timeout"]
    assert delegated == EXPECTED_FAULT_ACTIONS[1:]
    assert [f.decision.action for f in faults] == VIOLATED_FAULT_ACTIONS
    assert faults[0].decision == PolicyDecision(
        "ACT", lock.contract.policy.allowed_labels[0], "policy.allowed", False
    )
    assert faults[0].decision.action != lock.fault_inventory[0].expected_action
    # Every other field is the real canonical fault result.
    assert faults[1:] == bundle.faults[1:]
    assert (faults[0].request, faults[0].capture, faults[0].outcome) == (
        bundle.faults[0].request,
        bundle.faults[0].capture,
        bundle.faults[0].outcome,
    )
    # The unpatched assessor re-evaluates with the real policy: a decision that does
    # not reproduce is invalid evidence (ERROR), not a certified fault BLOCK.
    verdict = assess(bundle.records, lock, faults)
    assert_error(verdict, lock, "integrity.fault_decision")
    assert verdict.reasons == ("integrity.fault_decision",)


def test_consistent_policy_regression_blocks_and_retains_all_six_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the campaign AND the assessor share the regressed evaluator, the result is BLOCK."""
    workspace = write_workspace(tmp_path / "ws", count=6, prefix="fr")
    bundle, _ = fixture_run(tmp_path, workspace)
    lock = bundle.lock
    delegated: list[str] = []
    injected: list[str] = []
    wrapper = _violating_wrapper(delegated, injected)
    monkeypatch.setattr(faults_module, "evaluate", wrapper)
    monkeypatch.setattr(assessment_module, "evaluate", wrapper)
    faults = run_fault_campaign(lock)
    verdict = assess(bundle.records, lock, faults)
    assert verdict.status == "BLOCK"
    assert verdict.reasons == ("evidence.insufficient", "fault.timeout")
    assert (verdict.total, verdict.accepted, verdict.errors) == (6, 6, 0)
    assert len(faults) == 6
    assert [f.decision.action for f in faults] == VIOLATED_FAULT_ACTIONS
    assert injected == ["timeout", "timeout"]  # once in the campaign, once in the assessor
    # Campaign: five delegated faults. Assessor: six real records plus five faults.
    assert delegated[:5] == EXPECTED_FAULT_ACTIONS[1:]
    assert sorted(delegated[5:]) == sorted([*EXPECTED_FAULT_ACTIONS[1:], *["ACT"] * 6])
    # Statistics are still those of the six real records (fault cases never inflate n).
    assert_statistics_match_oracle(
        replace(verdict, status="INCONCLUSIVE", reasons=("evidence.insufficient",)), lock
    )
    # The real evaluator still disagrees: outside the regression the same faults are ERROR.
    monkeypatch.undo()
    assert (
        normalize(faults[0].capture, lock.contract.question, lock.model_identity)
        == faults[0].outcome
    )
    assert evaluate(faults[0].outcome, lock.contract.policy).action == "ESCALATE"
    assert_error(assess(bundle.records, lock, faults), lock, "integrity.fault_decision")
