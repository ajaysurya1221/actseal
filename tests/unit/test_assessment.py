"""Complete-evidence assessment against real locks, normalizer, policy and fault generator.

Every piece of evidence here is produced with the accepted T10/T30 authorities
(``create_lock``/``validate_lock``, ``normalize``, ``evaluate``,
``fault_capture``/``run_fault_campaign``) and strict T00 records. Forgeries are
built by replacing fields of otherwise valid records so each test isolates one
invariant. Statistical expectations are hand-derived closed forms or the
upstream SciPy golden vectors, never values read back from ``assess``.

The only test seam is the fault-violation branch: the accepted normalizer and
policy never violate a canonical scenario, so those tests wrap the evaluator
imported by ``assessment`` to simulate a defective policy for one outcome.
That wrapper never stands in for a missing dependency.
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import replace
from decimal import Decimal, localcontext

import pytest

import actseal.assessment as assessment_module
from actseal.assessment import (
    REASON_CONTRACT_SATISFIED,
    REASON_COVERAGE_BELOW_MINIMUM,
    REASON_EVIDENCE_INSUFFICIENT,
    REASON_NO_ACCEPTED_CASES,
    REASON_RISK_EXCEEDS_LIMIT,
    REASON_WORKER_INVALIDATED,
    assess,
)
from actseal.errors import SchemaError
from actseal.faults import fault_capture, run_fault_campaign
from actseal.locking import FAULT_INVENTORY, case_digest, create_lock, lock_digest, validate_lock
from actseal.normalization import normalize, request_sha256
from actseal.policy import evaluate
from actseal.records import (
    Action,
    CapturedOutcome,
    Case,
    CaseRef,
    ChoiceAnswer,
    Contract,
    DecisionRecord,
    DecisionRequest,
    EvidenceBundle,
    FaultResult,
    GateLimits,
    Interval,
    LockedPolicy,
    ModelIdentity,
    Outcome,
    PlanLock,
    PolicyDecision,
    ProviderFailure,
    Verdict,
)
from actseal.serialization import canonical_json, to_data
from conftest import HEX_B, make_contract, make_identity

# --------------------------------------------------------------------------- #
# Evidence builders (real authorities only)
# --------------------------------------------------------------------------- #

CALIBRATION = '{"case_id": "c-001", "state": "Calibration one.", "expected_label": "billing"}\n'

GOLD: tuple[tuple[str, str, str], ...] = (
    ("v-001", "Refund missing after cancellation.", "billing"),
    ("v-002", "Login page returns 500.", "technical"),
    ("v-003", "Is there bulk license pricing?", "sales"),
    ("v-004", "Charged twice this month.", "billing"),
    ("v-005", "App crashes on launch.", "technical"),
    ("v-006", "Need a quote for fifty seats.", "sales"),
)

ALL_LABELS = ("billing", "technical", "sales")
GATE_TAIL = 0.0125
ZERO_USAGE = {
    "input_tokens": 0,
    "output_tokens": 0,
    "state_tokens": 0,
    "state_tokens_dropped": 0,
    "truncated": False,
    "truncated_questions": [],
}
FULL = Interval(0.0, 1.0)


def verification_jsonl(cases: Sequence[tuple[str, str, str]] = GOLD) -> str:
    return "".join(
        json.dumps({"case_id": case_id, "state": state, "expected_label": label}) + "\n"
        for case_id, state, label in cases
    )


def many_cases(count: int) -> tuple[tuple[str, str, str], ...]:
    return tuple(
        (f"v-{index:04d}", f"Verification case number {index}.", ALL_LABELS[index % 3])
        for index in range(1, count + 1)
    )


def laya_identity() -> ModelIdentity:
    return ModelIdentity(
        "laya",
        "convaiinnovations/laya-typed-decisions",
        "e929ae5cf69bc34259cd2f95c9e91145b818b1f0",
        (("model.safetensors", HEX_B),),
        "1",
        "1",
        (("device", "cpu"),),
    )


def contract_with(
    *,
    allowed: tuple[str, ...] = ALL_LABELS,
    threshold: float = 0.9,
    max_risk: float = 0.05,
    min_coverage: float = 0.5,
    alpha: float = 0.05,
) -> Contract:
    base = make_contract()
    return Contract(
        1,
        base.name,
        base.question,
        LockedPolicy(ALL_LABELS, allowed, threshold),
        GateLimits(max_risk, min_coverage, alpha),
        base.evidence_scope,
        base.population,
    )


def make_lock(
    contract: Contract | None = None,
    identity: ModelIdentity | None = None,
    cases: Sequence[tuple[str, str, str]] = GOLD,
) -> PlanLock:
    lock = create_lock(
        contract or contract_with(),
        CALIBRATION,
        verification_jsonl(cases),
        identity or make_identity(),
    )
    validate_lock(lock)
    return lock


def with_limits(lock: PlanLock, *, max_risk: float, min_coverage: float) -> PlanLock:
    """A freshly sealed lock differing only in its gate limits (records stay valid)."""
    contract = lock.contract
    limits = GateLimits(max_risk, min_coverage, contract.limits.alpha)
    new_contract = Contract(
        1,
        contract.name,
        contract.question,
        contract.policy,
        limits,
        contract.evidence_scope,
        contract.population,
    )
    unsealed = replace(lock, contract=new_contract)
    sealed = replace(unsealed, sha256=lock_digest(unsealed))
    validate_lock(sealed)
    return sealed


def answer_json(choice: str, selected: float = 0.95) -> str:
    rest = (1.0 - selected) / (len(ALL_LABELS) - 1)
    probabilities = {label: (selected if label == choice else rest) for label in ALL_LABELS}
    return json.dumps({"type": "choice", "choice": choice, "probabilities": probabilities})


def body_for(lock: PlanLock, choice: str, selected: float = 0.95) -> str:
    inner = answer_json(choice, selected)
    if lock.model_identity.provider != "laya":
        return inner
    envelope = {
        "model": "laya-rl-agent",
        "answers": {lock.contract.question.question_id: json.loads(inner)},
        "usage": dict(ZERO_USAGE),
    }
    return json.dumps(envelope)


def request_for(lock: PlanLock, case: Case) -> DecisionRequest:
    return DecisionRequest(case.case_id, case.state, lock.contract.question)


def capture_for(
    lock: PlanLock,
    case: Case,
    *,
    body: str | None = None,
    failure_code: str | None = None,
    identity: ModelIdentity | None = None,
    warnings: tuple[str, ...] = (),
    fallback_used: bool = False,
    request: DecisionRequest | None = None,
) -> CapturedOutcome:
    if body is None and failure_code is None:
        body = body_for(lock, case.expected_label)
    return CapturedOutcome(
        request_sha256(request or request_for(lock, case)),
        identity or lock.model_identity,
        body,
        failure_code,
        warnings,
        fallback_used,
    )


def record_from_capture(lock: PlanLock, case: Case, capture: CapturedOutcome) -> DecisionRecord:
    """A faithful record: real normalization against the lock, real policy evaluation."""
    outcome = normalize(capture, lock.contract.question, lock.model_identity)
    decision = evaluate(outcome, lock.contract.policy)
    return DecisionRecord(case.case_id, capture, outcome, decision)


def record_for(lock: PlanLock, case: Case, **capture_fields: object) -> DecisionRecord:
    capture = capture_for(lock, case, **capture_fields)  # type: ignore[arg-type]
    return record_from_capture(lock, case, capture)


def records_for(
    lock: PlanLock, choices: Sequence[str | None] | None = None, selected: float = 0.95
) -> tuple[DecisionRecord, ...]:
    """One faithful ACT-shaped record per locked case; ``None`` means the gold label."""
    cases = lock.verification_cases
    picks = choices if choices is not None else [None] * len(cases)
    assert len(picks) == len(cases)
    return tuple(
        record_for(lock, case, body=body_for(lock, pick or case.expected_label, selected))
        for case, pick in zip(cases, picks, strict=True)
    )


def evidence(lock: PlanLock) -> tuple[tuple[DecisionRecord, ...], tuple[FaultResult, ...]]:
    return records_for(lock), run_fault_campaign(lock)


def fault_index(kind: str) -> int:
    return next(index for index, spec in enumerate(FAULT_INVENTORY) if spec.kind == kind)


def assert_well_formed(verdict: Verdict, lock: PlanLock) -> None:
    assert verdict.reasons == tuple(sorted(set(verdict.reasons)))
    assert verdict.lock_sha256 == lock.sha256
    assert verdict.evidence_scope == lock.contract.evidence_scope


def assert_error(verdict: Verdict, lock: PlanLock, *reasons: str) -> None:
    assert_well_formed(verdict, lock)
    assert verdict.status == "ERROR"
    assert verdict.reasons == tuple(sorted(reasons))
    assert (verdict.total, verdict.accepted, verdict.errors) == (0, 0, 0)
    assert verdict.risk == FULL
    assert verdict.coverage == FULL


def closed_form_root(tail: float, n: int) -> Decimal:
    """tail ** (1 / n) to 40 digits: the lower bound at x == n and 1 - upper bound at x == 0."""
    with localcontext() as context:
        context.prec = 40
        return Decimal(tail) ** (Decimal(1) / Decimal(n))


def approx_exact(value: float, reference: Decimal | float) -> None:
    assert value == pytest.approx(float(reference), rel=0, abs=1e-15)


# --------------------------------------------------------------------------- #
# Hand-reasoned statistical verdicts
# --------------------------------------------------------------------------- #


def test_all_six_correct_acts_are_inconclusive_at_default_limits() -> None:
    """a = n = 6, e = 0: risk upper 1 - 0.0125^(1/6) ~ 0.518 > 0.05, but risk lower is 0 and
    coverage upper is 1, so neither BLOCK condition holds."""
    lock = make_lock()
    records, faults = evidence(lock)
    verdict = assess(records, lock, faults)
    assert_well_formed(verdict, lock)
    assert verdict.status == "INCONCLUSIVE"
    assert verdict.reasons == (REASON_EVIDENCE_INSUFFICIENT,)
    assert (verdict.total, verdict.accepted, verdict.errors) == (6, 6, 0)
    root = closed_form_root(GATE_TAIL, 6)
    assert verdict.risk.lower == 0.0
    approx_exact(verdict.risk.upper, 1 - root)
    approx_exact(verdict.coverage.lower, root)
    assert verdict.coverage.upper == 1.0


def test_pass_requires_both_bounds_inside_the_limits() -> None:
    """Same evidence, limits 0.6 / 0.4: 0.518 <= 0.6 and 0.4818 >= 0.4 -> PASS."""
    lock = make_lock(contract_with(max_risk=0.6, min_coverage=0.4))
    records, faults = evidence(lock)
    verdict = assess(records, lock, faults)
    assert_well_formed(verdict, lock)
    assert verdict.status == "PASS"
    assert verdict.reasons == (REASON_CONTRACT_SATISFIED,)
    assert (verdict.total, verdict.accepted, verdict.errors) == (6, 6, 0)


def test_all_wrong_acts_block_on_risk() -> None:
    """e = a = 6: risk lower 0.0125^(1/6) ~ 0.4818 > 0.05 -> BLOCK."""
    lock = make_lock()
    wrong = ["technical", "sales", "billing", "technical", "sales", "billing"]
    records = records_for(lock, wrong)
    verdict = assess(records, lock, run_fault_campaign(lock))
    assert_well_formed(verdict, lock)
    assert verdict.status == "BLOCK"
    assert verdict.reasons == (REASON_RISK_EXCEEDS_LIMIT,)
    assert (verdict.total, verdict.accepted, verdict.errors) == (6, 6, 6)
    approx_exact(verdict.risk.lower, closed_form_root(GATE_TAIL, 6))
    assert verdict.risk.upper == 1.0


def test_no_accepted_cases_use_full_risk_and_cannot_pass() -> None:
    """Six faithful fixture timeouts: a = 0, coverage [0, 0.518]; even limits (1.0, 0.0)
    cannot PASS."""
    lock = make_lock(contract_with(max_risk=1.0, min_coverage=0.0))
    records = tuple(
        record_for(lock, case, failure_code="timeout") for case in lock.verification_cases
    )
    assert all(record.decision.action == "ESCALATE" for record in records)
    verdict = assess(records, lock, run_fault_campaign(lock))
    assert_well_formed(verdict, lock)
    assert verdict.status == "INCONCLUSIVE"
    assert verdict.reasons == (REASON_EVIDENCE_INSUFFICIENT, REASON_NO_ACCEPTED_CASES)
    assert (verdict.total, verdict.accepted, verdict.errors) == (6, 0, 0)
    assert verdict.risk == FULL
    assert verdict.coverage.lower == 0.0
    approx_exact(verdict.coverage.upper, 1 - closed_form_root(GATE_TAIL, 6))


def test_no_accepted_cases_block_when_coverage_upper_is_below_the_floor() -> None:
    lock = make_lock(contract_with(min_coverage=0.6))
    records = tuple(
        record_for(lock, case, failure_code="timeout") for case in lock.verification_cases
    )
    verdict = assess(records, lock, run_fault_campaign(lock))
    assert verdict.status == "BLOCK"
    assert verdict.reasons == (REASON_COVERAGE_BELOW_MINIMUM, REASON_NO_ACCEPTED_CASES)
    assert (verdict.total, verdict.accepted, verdict.errors) == (6, 0, 0)
    assert verdict.risk == FULL


def test_risk_upper_above_the_ceiling_alone_never_blocks() -> None:
    """One wrong ACT in six: risk [~0.002, ~0.64] straddles 0.05 -> INCONCLUSIVE, not BLOCK."""
    lock = make_lock()
    records = records_for(lock, ["technical", None, None, None, None, None])
    verdict = assess(records, lock, run_fault_campaign(lock))
    assert verdict.status == "INCONCLUSIVE"
    assert verdict.reasons == (REASON_EVIDENCE_INSUFFICIENT,)
    assert (verdict.total, verdict.accepted, verdict.errors) == (6, 6, 1)
    assert verdict.risk.lower < lock.contract.limits.max_risk < verdict.risk.upper


def test_denominator_counts_every_scheduled_case_and_only_final_acts() -> None:
    lock = make_lock(contract_with(allowed=("billing", "technical")))
    cases = lock.verification_cases
    mismatched = replace(lock.model_identity, revision="other-revision")
    records = (
        record_for(lock, cases[0]),  # ACT billing, correct
        record_for(lock, cases[1], body=body_for(lock, "billing")),  # ACT billing, wrong
        record_for(lock, cases[2]),  # sales is known but disallowed -> DENY
        record_for(lock, cases[3], body=body_for(lock, "billing", 0.5)),  # ABSTAIN
        record_for(lock, cases[4], failure_code="rate_limit"),  # ESCALATE
        record_for(lock, cases[5], identity=mismatched),  # faithful identity mismatch
    )
    actions = [record.decision.action for record in records]
    assert actions == ["ACT", "ACT", "DENY", "ABSTAIN", "ESCALATE", "ESCALATE"]
    verdict = assess(records, lock, run_fault_campaign(lock))
    assert_well_formed(verdict, lock)
    assert verdict.status == "INCONCLUSIVE"
    assert (verdict.total, verdict.accepted, verdict.errors) == (6, 2, 1)
    assert verdict.total == len(lock.verification_cases)
    assert verdict.total != len(records) + len(FAULT_INVENTORY)


def test_two_hundred_cases_match_the_upstream_golden_vectors() -> None:
    """10 wrong of 200 ACTs: risk = reflected CP(190, 200) golden; coverage lower 0.0125^(1/200)."""
    lock = make_lock(contract_with(max_risk=0.1, min_coverage=0.9), cases=many_cases(200))
    cases = lock.verification_cases
    picks: list[str | None] = [None] * 200
    for index in range(10):
        gold = cases[index].expected_label
        picks[index] = next(label for label in ALL_LABELS if label != gold)
    records = records_for(lock, picks)
    verdict = assess(records, lock, run_fault_campaign(lock))
    assert_well_formed(verdict, lock)
    assert verdict.status == "PASS"
    assert (verdict.total, verdict.accepted, verdict.errors) == (200, 200, 10)
    assert verdict.risk.lower == pytest.approx(1 - 0.978351375522, rel=0, abs=1e-9)
    assert verdict.risk.upper == pytest.approx(1 - 0.903744200551, rel=0, abs=1e-9)
    approx_exact(verdict.coverage.lower, closed_form_root(GATE_TAIL, 200))
    assert verdict.coverage.upper == 1.0

    tighter = with_limits(lock, max_risk=0.05, min_coverage=0.9)
    assert assess(records, tighter, run_fault_campaign(tighter)).status == "INCONCLUSIVE"


def test_seventy_wrong_of_two_hundred_block_on_the_golden_lower_bound() -> None:
    lock = make_lock(cases=many_cases(200))
    cases = lock.verification_cases
    picks: list[str | None] = [None] * 200
    for index in range(70):
        gold = cases[index].expected_label
        picks[index] = next(label for label in ALL_LABELS if label != gold)
    verdict = assess(records_for(lock, picks), lock, run_fault_campaign(lock))
    assert verdict.status == "BLOCK"
    assert verdict.reasons == (REASON_RISK_EXCEEDS_LIMIT,)
    assert verdict.risk.lower == pytest.approx(1 - 0.724655682038, rel=0, abs=1e-9)
    assert verdict.risk.upper == pytest.approx(1 - 0.569630393398, rel=0, abs=1e-9)


def test_pass_comparisons_are_inclusive_at_exact_equality() -> None:
    lock = make_lock()
    records, faults = evidence(lock)
    bounds = assess(records, lock, faults)
    at_limit = with_limits(lock, max_risk=bounds.risk.upper, min_coverage=bounds.coverage.lower)
    assert assess(records, at_limit, run_fault_campaign(at_limit)).status == "PASS"
    below_risk = with_limits(
        lock,
        max_risk=math.nextafter(bounds.risk.upper, 0.0),
        min_coverage=bounds.coverage.lower,
    )
    assert assess(records, below_risk, run_fault_campaign(below_risk)).status == "INCONCLUSIVE"
    above_coverage = with_limits(
        lock,
        max_risk=bounds.risk.upper,
        min_coverage=math.nextafter(bounds.coverage.lower, 1.0),
    )
    assert assess(records, above_coverage, run_fault_campaign(above_coverage)).status == (
        "INCONCLUSIVE"
    )


def test_block_comparisons_are_strict_at_exact_equality() -> None:
    lock = make_lock()
    wrong = ["technical", "sales", "billing", "technical", "sales", "billing"]
    records = records_for(lock, wrong)
    bounds = assess(records, lock, run_fault_campaign(lock))
    assert bounds.status == "BLOCK"
    at_limit = with_limits(lock, max_risk=bounds.risk.lower, min_coverage=0.5)
    equal = assess(records, at_limit, run_fault_campaign(at_limit))
    assert equal.status == "INCONCLUSIVE"
    assert equal.reasons == (REASON_EVIDENCE_INSUFFICIENT,)
    just_below = with_limits(
        lock, max_risk=math.nextafter(bounds.risk.lower, 0.0), min_coverage=0.5
    )
    assert assess(records, just_below, run_fault_campaign(just_below)).status == "BLOCK"

    escalated = tuple(
        record_for(lock, case, failure_code="timeout") for case in lock.verification_cases
    )
    bounds = assess(escalated, lock, run_fault_campaign(lock))
    at_cover = with_limits(lock, max_risk=0.05, min_coverage=bounds.coverage.upper)
    assert assess(escalated, at_cover, run_fault_campaign(at_cover)).status == "INCONCLUSIVE"
    over_cover = with_limits(
        lock, max_risk=0.05, min_coverage=math.nextafter(bounds.coverage.upper, 1.0)
    )
    assert assess(escalated, over_cover, run_fault_campaign(over_cover)).status == "BLOCK"


def test_single_case_lock_uses_the_n_equals_one_closed_forms() -> None:
    lock = make_lock(cases=GOLD[:1])
    records, faults = evidence(lock)
    verdict = assess(records, lock, faults)
    assert (verdict.total, verdict.accepted, verdict.errors) == (1, 1, 0)
    approx_exact(verdict.risk.upper, Decimal(1) - Decimal(GATE_TAIL))
    approx_exact(verdict.coverage.lower, Decimal(GATE_TAIL))
    assert verdict.status == "INCONCLUSIVE"


def test_alpha_quarter_is_the_tail_for_each_interval() -> None:
    lock = make_lock(contract_with(alpha=0.2))  # tail 0.05
    records, faults = evidence(lock)
    verdict = assess(records, lock, faults)
    approx_exact(verdict.risk.upper, 1 - closed_form_root(0.05, 6))
    approx_exact(verdict.coverage.lower, closed_form_root(0.05, 6))


def test_valid_evidence_yields_identical_verdict_bytes_and_a_coherent_bundle() -> None:
    lock = make_lock()
    records, faults = evidence(lock)
    first = assess(records, lock, faults)
    second = assess(list(records), lock, list(faults))
    assert first == second
    assert canonical_json(to_data(first)) == canonical_json(to_data(second))
    bundle = EvidenceBundle(lock, CALIBRATION, verification_jsonl(), records, faults, first)
    assert bundle.verdict is first


# --------------------------------------------------------------------------- #
# Record inventory integrity
# --------------------------------------------------------------------------- #


def _inventory_mutations() -> dict[
    str, Callable[[tuple[DecisionRecord, ...]], list[DecisionRecord]]
]:
    return {
        "missing_last": lambda r: list(r[:-1]),
        "missing_first": lambda r: list(r[1:]),
        "empty": lambda _r: [],
        "duplicate_replaces_last": lambda r: [*r[:-1], r[0]],
        "extra_duplicate": lambda r: [*r, r[-1]],
        "reordered": lambda r: [r[1], r[0], *r[2:]],
        "foreign_id": lambda r: [*r[:-1], replace(r[-1], case_id="v-999")],
    }


@pytest.mark.parametrize("mutation", sorted(_inventory_mutations()))
def test_record_inventory_must_match_the_lock_exactly(mutation: str) -> None:
    lock = make_lock()
    records, faults = evidence(lock)
    mutated = _inventory_mutations()[mutation](records)
    assert_error(assess(mutated, lock, faults), lock, "integrity.records")


# --------------------------------------------------------------------------- #
# Per-record semantic reconstruction
# --------------------------------------------------------------------------- #


def test_rehashed_altered_state_substitution_is_detected() -> None:
    """A self-consistent capture for a different state text: hash matches its own request,
    not the locked one."""
    lock = make_lock()
    records, faults = evidence(lock)
    case = lock.verification_cases[2]
    altered = DecisionRequest(case.case_id, "A different, easier ticket.", lock.contract.question)
    capture = capture_for(lock, case, request=altered)
    assert capture.request_sha256 == request_sha256(altered)
    forged = record_from_capture(lock, case, capture)
    assert forged.decision.action == "ACT"
    mutated = [*records[:2], forged, *records[3:]]
    assert_error(assess(mutated, lock, faults), lock, "integrity.request_hash")


def test_substituted_question_in_the_request_is_detected() -> None:
    lock = make_lock()
    records, faults = evidence(lock)
    case = lock.verification_cases[0]
    other_question = replace(lock.contract.question, instructions="Pick anything.")
    capture = capture_for(
        lock, case, request=DecisionRequest(case.case_id, case.state, other_question)
    )
    mutated = [record_from_capture(lock, case, capture), *records[1:]]
    assert_error(assess(mutated, lock, faults), lock, "integrity.request_hash")


def test_raw_body_versus_recorded_answer_forgery_is_detected() -> None:
    """The raw body says technical; the stored answer and ACT claim billing."""
    lock = make_lock()
    records, faults = evidence(lock)
    case = lock.verification_cases[0]  # gold billing
    capture = capture_for(lock, case, body=body_for(lock, "technical"))
    truthful = record_from_capture(lock, case, capture)
    assert truthful.decision == PolicyDecision("ACT", "technical", "policy.allowed", False)
    forged_answer = ChoiceAnswer(
        "billing",
        (("billing", 0.95), ("technical", 0.025), ("sales", 0.025)),
        0.95,
        None,
        (),
        False,
    )
    forged = DecisionRecord(
        case.case_id,
        capture,
        forged_answer,
        PolicyDecision("ACT", "billing", "policy.allowed", False),
    )
    verdict = assess([forged, *records[1:]], lock, faults)
    assert_error(verdict, lock, "integrity.decision", "integrity.outcome")


def test_invented_normalization_of_a_malformed_body_is_detected() -> None:
    lock = make_lock()
    records, faults = evidence(lock)
    case = lock.verification_cases[1]
    capture = capture_for(lock, case, body="{")
    truthful = record_from_capture(lock, case, capture)
    assert isinstance(truthful.outcome, ProviderFailure)
    assert truthful.outcome.code == "malformed_response"
    invented = DecisionRecord(
        case.case_id,
        capture,
        ChoiceAnswer(
            "technical",
            (("billing", 0.0), ("technical", 1.0), ("sales", 0.0)),
            1.0,
            None,
            (),
            False,
        ),
        PolicyDecision("ACT", "technical", "policy.allowed", False),
    )
    verdict = assess([records[0], invented, *records[2:]], lock, faults)
    assert_error(verdict, lock, "integrity.decision", "integrity.outcome")


def test_relabelled_failure_code_is_detected() -> None:
    lock = make_lock()
    records, faults = evidence(lock)
    case = lock.verification_cases[4]
    capture = capture_for(lock, case, failure_code="rate_limit")
    relabelled = DecisionRecord(
        case.case_id,
        capture,
        ProviderFailure("timeout", (), False),
        PolicyDecision("ESCALATE", None, "provider.timeout", False),
    )
    verdict = assess([*records[:4], relabelled, records[5]], lock, faults)
    assert_error(verdict, lock, "integrity.decision", "integrity.outcome")


def test_outcome_only_forgery_is_detected_even_when_the_decision_agrees() -> None:
    lock = make_lock()
    records, faults = evidence(lock)
    record = records[0]
    assert isinstance(record.outcome, ChoiceAnswer)
    inflated = replace(
        record.outcome,
        probabilities=(("billing", 0.96), ("technical", 0.02), ("sales", 0.02)),
        selected_probability=0.96,
    )
    forged = replace(record, outcome=inflated)
    assert forged.decision == record.decision
    assert_error(assess([forged, *records[1:]], lock, faults), lock, "integrity.outcome")


@pytest.mark.parametrize(
    "decision",
    [
        PolicyDecision("ABSTAIN", None, "policy.low_confidence", False),
        PolicyDecision("DENY", None, "policy.disallowed_choice", False),
        PolicyDecision("ESCALATE", None, "provider.timeout", False),
        PolicyDecision("ACT", "technical", "policy.allowed", False),
        PolicyDecision("ACT", "billing", "policy.low_confidence", False),
    ],
)
def test_decision_forgery_is_detected_for_every_other_disposition(
    decision: PolicyDecision,
) -> None:
    lock = make_lock()
    records, faults = evidence(lock)
    forged = replace(records[0], decision=decision)
    assert_error(assess([forged, *records[1:]], lock, faults), lock, "integrity.decision")


def test_records_evaluated_under_a_different_policy_are_detected() -> None:
    lock = make_lock()
    stricter = LockedPolicy(ALL_LABELS, ALL_LABELS, 0.99)
    records = []
    for case in lock.verification_cases:
        capture = capture_for(lock, case)
        outcome = normalize(capture, lock.contract.question, lock.model_identity)
        records.append(DecisionRecord(case.case_id, capture, outcome, evaluate(outcome, stricter)))
    assert all(record.decision.action == "ABSTAIN" for record in records)
    assert_error(assess(records, lock, run_fault_campaign(lock)), lock, "integrity.decision")


def test_normalization_against_a_foreign_identity_is_detected() -> None:
    """The capture's observed identity differs from the lock, yet an answer was recorded."""
    lock = make_lock()
    records, faults = evidence(lock)
    case = lock.verification_cases[5]
    foreign = replace(lock.model_identity, revision="other-revision")
    capture = capture_for(lock, case, identity=foreign)
    outcome = normalize(capture, lock.contract.question, foreign)  # wrong expected identity
    assert isinstance(outcome, ChoiceAnswer)
    inconsistent = DecisionRecord(
        case.case_id, capture, outcome, evaluate(outcome, lock.contract.policy)
    )
    verdict = assess([*records[:5], inconsistent], lock, faults)
    assert_error(verdict, lock, "integrity.decision", "integrity.outcome")


def test_faithfully_recorded_identity_mismatch_escalates_inside_the_denominator() -> None:
    lock = make_lock()
    records, faults = evidence(lock)
    case = lock.verification_cases[5]
    foreign = replace(lock.model_identity, revision="other-revision")
    faithful = record_for(lock, case, identity=foreign)
    assert faithful.outcome == ProviderFailure(
        "identity_mismatch", ("normalize.identity_mismatch",), False
    )
    assert faithful.decision == PolicyDecision(
        "ESCALATE", None, "provider.identity_mismatch", False
    )
    verdict = assess([*records[:5], faithful], lock, faults)
    assert_well_formed(verdict, lock)
    assert verdict.status == "INCONCLUSIVE"
    assert (verdict.total, verdict.accepted, verdict.errors) == (6, 5, 0)


def test_fallback_and_warning_bearing_captures_are_reconstructed_exactly() -> None:
    lock = make_lock()
    cases = lock.verification_cases
    records = (
        record_for(lock, cases[0], fallback_used=True),
        record_for(lock, cases[1], warnings=("adapter.slow",)),
        *records_for(lock)[2:],
    )
    assert records[0].decision.action == "ESCALATE"
    assert records[0].decision.fallback_used is True
    assert isinstance(records[1].outcome, ChoiceAnswer)
    assert records[1].outcome.warnings == ("adapter.slow",)
    verdict = assess(records, lock, run_fault_campaign(lock))
    assert verdict.status == "INCONCLUSIVE"
    assert (verdict.total, verdict.accepted, verdict.errors) == (6, 5, 0)
    stripped = replace(records[1], outcome=replace(records[1].outcome, warnings=()))
    assert_error(
        assess([records[0], stripped, *records[2:]], lock, run_fault_campaign(lock)),
        lock,
        "integrity.outcome",
    )


def test_interleaved_invalid_evidence_never_yields_partial_statistics() -> None:
    """Five records that alone would PASS plus one forgery: ERROR with neutral counts."""
    lock = make_lock(contract_with(max_risk=0.6, min_coverage=0.4))
    records, faults = evidence(lock)
    assert assess(records, lock, faults).status == "PASS"
    case = lock.verification_cases[3]
    forged = replace(records[3], decision=PolicyDecision("ACT", "sales", "policy.allowed", False))
    assert forged.case_id == case.case_id
    verdict = assess([*records[:3], forged, *records[4:]], lock, faults)
    assert_error(verdict, lock, "integrity.decision")


def test_multiple_defects_report_all_sorted_unique_codes() -> None:
    lock = make_lock()
    records, faults = evidence(lock)
    case = lock.verification_cases[0]
    altered = capture_for(
        lock, case, request=DecisionRequest(case.case_id, "Other.", lock.contract.question)
    )
    bad_hash = record_from_capture(lock, case, altered)
    bad_decision = replace(
        records[1], decision=PolicyDecision("ABSTAIN", None, "policy.low_confidence", False)
    )
    bad_faults = list(faults[:-1])
    verdict = assess([bad_hash, bad_decision, *records[2:]], lock, bad_faults)
    assert_error(verdict, lock, "integrity.decision", "integrity.faults", "integrity.request_hash")


# --------------------------------------------------------------------------- #
# Lock integrity
# --------------------------------------------------------------------------- #


def _reseal(lock: PlanLock) -> PlanLock:
    return replace(lock, sha256=lock_digest(lock))


def test_changed_gold_label_without_reseal_is_a_lock_error() -> None:
    lock = make_lock()
    records, faults = evidence(lock)
    cases = list(lock.verification_cases)
    cases[0] = replace(cases[0], expected_label="technical")
    tampered = replace(lock, verification_cases=tuple(cases))
    assert_error(assess(records, tampered, faults), tampered, "integrity.lock")


def test_changed_gold_label_with_reseal_but_stale_inventory_is_a_lock_error() -> None:
    lock = make_lock()
    records, faults = evidence(lock)
    cases = list(lock.verification_cases)
    cases[0] = replace(cases[0], expected_label="technical")
    tampered = _reseal(replace(lock, verification_cases=tuple(cases)))
    assert lock_digest(tampered) == tampered.sha256
    assert_error(assess(records, tampered, faults), tampered, "integrity.lock")


def test_fully_reauthored_labels_change_the_lock_identity_not_the_verdict_shape() -> None:
    """Rewriting labels, inventory and seal is self-consistent; replay trust rests on the
    externally known lock digest, which no longer matches."""
    lock = make_lock()
    records, _ = evidence(lock)
    cases = list(lock.verification_cases)
    cases[0] = replace(cases[0], expected_label="technical")
    inventory = tuple(CaseRef(case.case_id, case_digest(case)) for case in cases)
    reauthored = _reseal(
        replace(lock, verification_cases=tuple(cases), verification_inventory=inventory)
    )
    validate_lock(reauthored)
    verdict = assess(records, reauthored, run_fault_campaign(reauthored))
    assert verdict.lock_sha256 == reauthored.sha256 != lock.sha256
    assert (verdict.total, verdict.accepted, verdict.errors) == (6, 6, 1)


@pytest.mark.parametrize(
    "tamper",
    [
        pytest.param(lambda lock: replace(lock, sha256="1" * 64), id="broken_seal"),
        pytest.param(
            lambda lock: _reseal(replace(lock, implementation_sha256="2" * 64)),
            id="foreign_implementation",
        ),
        pytest.param(
            lambda lock: _reseal(
                replace(
                    lock,
                    verification_inventory=(
                        replace(lock.verification_inventory[0], sha256="3" * 64),
                        *lock.verification_inventory[1:],
                    ),
                )
            ),
            id="changed_inventory_digest",
        ),
        pytest.param(
            lambda lock: _reseal(
                replace(
                    lock,
                    fault_inventory=(
                        lock.fault_inventory[1],
                        lock.fault_inventory[0],
                        *lock.fault_inventory[2:],
                    ),
                )
            ),
            id="reordered_fault_inventory",
        ),
        pytest.param(
            lambda lock: _reseal(replace(lock, fault_inventory=lock.fault_inventory[:5])),
            id="five_fault_inventory",
        ),
        pytest.param(
            lambda lock: _reseal(
                replace(
                    lock,
                    calibration_inventory=(
                        replace(lock.calibration_inventory[0], case_id="v-001"),
                    ),
                )
            ),
            id="cross_split_id",
        ),
    ],
)
def test_lock_tampering_is_an_error_before_any_counting(
    tamper: Callable[[PlanLock], PlanLock],
) -> None:
    lock = make_lock()
    records, faults = evidence(lock)
    tampered = tamper(lock)
    assert_error(assess(records, tampered, faults), tampered, "integrity.lock")


def test_lock_error_takes_precedence_over_record_and_fault_defects() -> None:
    lock = make_lock()
    records, faults = evidence(lock)
    tampered = replace(lock, sha256="1" * 64)
    verdict = assess(records[:3], tampered, faults[:2])
    assert_error(verdict, tampered, "integrity.lock")


def test_records_from_another_lock_are_rejected_by_hash_not_by_id() -> None:
    lock = make_lock()
    other = make_lock(cases=tuple((cid, state + " Revised.", label) for cid, state, label in GOLD))
    records, _ = evidence(other)
    assert [record.case_id for record in records] == [
        case.case_id for case in lock.verification_cases
    ]
    assert_error(assess(records, lock, run_fault_campaign(lock)), lock, "integrity.request_hash")


# --------------------------------------------------------------------------- #
# Fault completeness and canonical captures
# --------------------------------------------------------------------------- #


def _fault_inventory_mutations() -> dict[
    str, Callable[[tuple[FaultResult, ...]], list[FaultResult]]
]:
    return {
        "missing_one": lambda f: list(f[:-1]),
        "empty": lambda _f: [],
        "duplicated": lambda f: [*f, f[0]],
        "replaced_duplicate": lambda f: [f[1], *f[1:]],
        "reordered": lambda f: [f[1], f[0], *f[2:]],
        "foreign_scenario": lambda f: [*f[:-1], replace(f[-1], scenario_id="fault.other")],
    }


@pytest.mark.parametrize("mutation", sorted(_fault_inventory_mutations()))
def test_fault_inventory_must_match_the_lock_exactly(mutation: str) -> None:
    lock = make_lock()
    records, faults = evidence(lock)
    mutated = _fault_inventory_mutations()[mutation](faults)
    assert_error(assess(records, lock, mutated), lock, "integrity.faults")


def test_all_six_canonical_faults_are_accepted_for_both_providers() -> None:
    for identity in (make_identity(), laya_identity()):
        lock = make_lock(identity=identity)
        records, faults = evidence(lock)
        assert len(faults) == 6
        for fault, spec in zip(faults, lock.fault_inventory, strict=True):
            assert (fault.request, fault.capture) == fault_capture(lock, spec)
        verdict = assess(records, lock, faults)
        assert verdict.status == "INCONCLUSIVE"
        assert (verdict.total, verdict.accepted, verdict.errors) == (6, 6, 0)


def test_swapped_canonical_capture_between_scenarios_is_detected() -> None:
    lock = make_lock()
    records, faults = evidence(lock)
    timeout = faults[fault_index("timeout")]
    rate_limit = faults[fault_index("rate_limit")]
    # Faithfully re-normalized rate_limit capture filed under the timeout scenario.
    swapped_faithful = FaultResult(
        timeout.scenario_id,
        timeout.request,
        rate_limit.capture,
        rate_limit.outcome,
        rate_limit.decision,
    )
    mutated = [swapped_faithful, *faults[1:]]
    assert_error(assess(records, lock, mutated), lock, "integrity.fault_capture")
    # Capture swapped but the original timeout outcome/decision kept.
    swapped_stale = replace(timeout, capture=rate_limit.capture)
    mutated = [swapped_stale, *faults[1:]]
    assert_error(
        assess(records, lock, mutated),
        lock,
        "integrity.fault_capture",
        "integrity.fault_decision",
        "integrity.fault_outcome",
    )


def test_swapped_request_between_scenarios_is_detected() -> None:
    lock = make_lock()
    records, faults = evidence(lock)
    timeout = faults[fault_index("timeout")]
    rate_limit = faults[fault_index("rate_limit")]
    mutated = [replace(timeout, request=rate_limit.request), *faults[1:]]
    assert_error(assess(records, lock, mutated), lock, "integrity.fault_request")


def test_fault_from_a_different_lock_is_detected() -> None:
    lock = make_lock()
    records, faults = evidence(lock)
    other = make_lock(identity=laya_identity())
    other_faults = run_fault_campaign(other)
    index = fault_index("low_confidence")
    mutated = [*faults[:index], other_faults[index], *faults[index + 1 :]]
    verdict = assess(records, lock, mutated)
    assert_error(
        verdict,
        lock,
        "integrity.fault_capture",
        "integrity.fault_decision",
        "integrity.fault_outcome",
    )


def test_non_canonical_identity_on_a_regular_fault_is_detected_even_if_faithful() -> None:
    """Only the identity_mismatch scenario may carry a changed observed identity."""
    lock = make_lock()
    records, faults = evidence(lock)
    index = fault_index("timeout")
    original = faults[index]
    foreign = replace(lock.model_identity, revision=lock.model_identity.revision + ":fault")
    capture = replace(original.capture, identity=foreign)
    outcome = normalize(capture, lock.contract.question, lock.model_identity)
    faithful = FaultResult(
        original.scenario_id,
        original.request,
        capture,
        outcome,
        evaluate(outcome, lock.contract.policy),
    )
    assert faithful.decision.action == "ESCALATE"
    mutated = [*faults[:index], faithful, *faults[index + 1 :]]
    assert_error(assess(records, lock, mutated), lock, "integrity.fault_capture")


def test_fault_capture_with_extra_warning_or_fallback_is_detected() -> None:
    lock = make_lock()
    records, faults = evidence(lock)
    index = fault_index("malformed_response")
    original = faults[index]
    variants = (
        replace(original.capture, warnings=("adapter.slow",)),
        replace(original.capture, fallback_used=True),
    )
    for capture in variants:
        outcome = normalize(capture, lock.contract.question, lock.model_identity)
        faithful = FaultResult(
            original.scenario_id,
            original.request,
            capture,
            outcome,
            evaluate(outcome, lock.contract.policy),
        )
        mutated = [*faults[:index], faithful, *faults[index + 1 :]]
        assert_error(assess(records, lock, mutated), lock, "integrity.fault_capture")


def test_forged_fault_outcome_or_decision_is_detected() -> None:
    lock = make_lock()
    records, faults = evidence(lock)
    index = fault_index("unknown_choice")
    original = faults[index]
    forged_outcome = replace(original, outcome=ProviderFailure("timeout", (), False))
    forged_outcome = replace(
        forged_outcome, decision=PolicyDecision("ESCALATE", None, "provider.timeout", False)
    )
    mutated = [*faults[:index], forged_outcome, *faults[index + 1 :]]
    assert_error(
        assess(records, lock, mutated), lock, "integrity.fault_decision", "integrity.fault_outcome"
    )
    forged_decision = replace(
        original, decision=PolicyDecision("ESCALATE", None, "policy.unknown_choice", False)
    )
    mutated = [*faults[:index], forged_decision, *faults[index + 1 :]]
    assert_error(assess(records, lock, mutated), lock, "integrity.fault_decision")


def test_claimed_violation_the_real_evaluator_does_not_reproduce_is_an_error() -> None:
    """A fault result asserting an unexpected action without the authorities agreeing is
    forged evidence, not a BLOCK."""
    lock = make_lock()
    records, faults = evidence(lock)
    index = fault_index("timeout")
    claimed = replace(
        faults[index], decision=PolicyDecision("ACT", "billing", "policy.allowed", False)
    )
    mutated = [*faults[:index], claimed, *faults[index + 1 :]]
    assert_error(assess(records, lock, mutated), lock, "integrity.fault_decision")


# --------------------------------------------------------------------------- #
# Fault action violations (defective-policy seam)
# --------------------------------------------------------------------------- #


def _other_actions(expected: str) -> list[Action]:
    return [action for action in ("ACT", "ABSTAIN", "ESCALATE", "DENY") if action != expected]


def _defective_evaluator(
    monkeypatch: pytest.MonkeyPatch, target_outcome: Outcome, decision: PolicyDecision
) -> None:
    def defective(outcome: Outcome, policy: LockedPolicy) -> PolicyDecision:
        if outcome == target_outcome:
            return decision
        return evaluate(outcome, policy)  # the accepted evaluator for every other outcome

    monkeypatch.setattr(assessment_module, "evaluate", defective)


def _violating_faults(
    lock: PlanLock, kind: str, action: Action, monkeypatch: pytest.MonkeyPatch
) -> list[FaultResult]:
    faults = list(run_fault_campaign(lock))
    index = fault_index(kind)
    original = faults[index]
    decision = PolicyDecision(
        action,
        "billing" if action == "ACT" else None,
        "test.defective_policy",
        original.outcome.fallback_used,
    )
    faults[index] = replace(original, decision=decision)
    _defective_evaluator(monkeypatch, original.outcome, decision)
    return faults


@pytest.mark.parametrize(
    ("kind", "action"),
    [
        (spec.kind, action)
        for spec in FAULT_INVENTORY
        for action in _other_actions(spec.expected_action)
    ],
)
def test_every_fault_action_mismatch_blocks(
    kind: str, action: Action, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock = make_lock(contract_with(max_risk=0.6, min_coverage=0.4))
    records = records_for(lock)
    faults = _violating_faults(lock, kind, action, monkeypatch)
    verdict = assess(records, lock, faults)
    assert_well_formed(verdict, lock)
    assert verdict.status == "BLOCK"
    assert verdict.reasons == (f"fault.{kind}",)
    # Statistics are still those of the valid regular evidence; faults never enter n.
    assert (verdict.total, verdict.accepted, verdict.errors) == (6, 6, 0)
    assert REASON_CONTRACT_SATISFIED not in verdict.reasons


def test_fault_violation_keeps_statistical_reasons_and_block_precedence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lock = make_lock()  # default limits -> statistics INCONCLUSIVE
    records = records_for(lock)
    faults = _violating_faults(lock, "low_confidence", "ACT", monkeypatch)
    verdict = assess(records, lock, faults)
    assert verdict.status == "BLOCK"
    assert verdict.reasons == (REASON_EVIDENCE_INSUFFICIENT, "fault.low_confidence")


def test_fault_violation_with_statistical_block_lists_both(monkeypatch: pytest.MonkeyPatch) -> None:
    lock = make_lock()
    wrong = ["technical", "sales", "billing", "technical", "sales", "billing"]
    records = records_for(lock, wrong)
    faults = _violating_faults(lock, "rate_limit", "DENY", monkeypatch)
    verdict = assess(records, lock, faults)
    assert verdict.status == "BLOCK"
    assert verdict.reasons == ("fault.rate_limit", REASON_RISK_EXCEEDS_LIMIT)


def test_integrity_error_outranks_a_fault_violation(monkeypatch: pytest.MonkeyPatch) -> None:
    lock = make_lock()
    records = records_for(lock)
    faults = _violating_faults(lock, "timeout", "ACT", monkeypatch)
    verdict = assess(records[:-1], lock, faults)
    assert_error(verdict, lock, "integrity.records")


# --------------------------------------------------------------------------- #
# ADR 0009: permanent worker loss
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("code", ["timeout", "unavailable"])
def test_regular_laya_worker_loss_is_an_infrastructure_error(code: str) -> None:
    lock = make_lock(identity=laya_identity())
    records = list(records_for(lock))
    faithful = record_for(lock, lock.verification_cases[3], failure_code=code)
    assert faithful.decision == PolicyDecision("ESCALATE", None, f"provider.{code}", False)
    records[3] = faithful
    verdict = assess(records, lock, run_fault_campaign(lock))
    assert_error(verdict, lock, REASON_WORKER_INVALIDATED)


def test_worker_loss_error_requires_complete_terminal_records_first() -> None:
    lock = make_lock(identity=laya_identity())
    records = list(records_for(lock))
    records[0] = record_for(lock, lock.verification_cases[0], failure_code="timeout")
    verdict = assess(records[:-1], lock, run_fault_campaign(lock))
    assert_error(verdict, lock, "integrity.records")
    forged = replace(
        records[1], decision=PolicyDecision("ABSTAIN", None, "policy.low_confidence", False)
    )
    verdict = assess([records[0], forged, *records[2:]], lock, run_fault_campaign(lock))
    assert_error(verdict, lock, "integrity.decision")


def test_worker_loss_outranks_a_fault_violation(monkeypatch: pytest.MonkeyPatch) -> None:
    lock = make_lock(identity=laya_identity())
    records = list(records_for(lock))
    records[5] = record_for(lock, lock.verification_cases[5], failure_code="unavailable")
    faults = _violating_faults(lock, "unknown_choice", "ACT", monkeypatch)
    assert_error(assess(records, lock, faults), lock, REASON_WORKER_INVALIDATED)


@pytest.mark.parametrize("code", ["timeout", "unavailable"])
def test_fixture_provider_failures_with_the_same_codes_stay_in_the_denominator(code: str) -> None:
    lock = make_lock()
    assert lock.model_identity.provider == "fixture"
    records = list(records_for(lock))
    records[2] = record_for(lock, lock.verification_cases[2], failure_code=code)
    verdict = assess(records, lock, run_fault_campaign(lock))
    assert verdict.status == "INCONCLUSIVE"
    assert (verdict.total, verdict.accepted, verdict.errors) == (6, 5, 0)


@pytest.mark.parametrize(
    "code", ["rate_limit", "provider_error", "malformed_response", "input_too_long"]
)
def test_nonfatal_laya_failures_remain_valid_evidence(code: str) -> None:
    lock = make_lock(identity=laya_identity())
    records = list(records_for(lock))
    records[1] = record_for(lock, lock.verification_cases[1], failure_code=code)
    verdict = assess(records, lock, run_fault_campaign(lock))
    assert verdict.status == "INCONCLUSIVE"
    assert (verdict.total, verdict.accepted, verdict.errors) == (6, 5, 0)


def test_laya_identity_mismatch_and_malformed_body_are_not_worker_loss() -> None:
    lock = make_lock(identity=laya_identity())
    records = list(records_for(lock))
    foreign = replace(lock.model_identity, revision="other")
    records[0] = record_for(lock, lock.verification_cases[0], identity=foreign)
    records[1] = record_for(lock, lock.verification_cases[1], body="{")
    verdict = assess(records, lock, run_fault_campaign(lock))
    assert verdict.status == "INCONCLUSIVE"
    assert (verdict.total, verdict.accepted, verdict.errors) == (6, 4, 0)


def test_canonical_laya_timeout_fault_does_not_trigger_worker_loss() -> None:
    lock = make_lock(identity=laya_identity())
    records, faults = evidence(lock)
    timeout_fault = faults[fault_index("timeout")]
    assert timeout_fault.capture.failure_code == "timeout"
    verdict = assess(records, lock, faults)
    assert verdict.status == "INCONCLUSIVE"
    assert REASON_WORKER_INVALIDATED not in verdict.reasons
    assert (verdict.total, verdict.accepted, verdict.errors) == (6, 6, 0)


# --------------------------------------------------------------------------- #
# API boundary and isolation
# --------------------------------------------------------------------------- #


def test_type_misuse_raises_schema_error_rather_than_a_verdict() -> None:
    lock = make_lock()
    records, faults = evidence(lock)
    with pytest.raises(SchemaError, match="lock"):
        assess(records, to_data(lock), faults)  # type: ignore[arg-type]
    with pytest.raises(SchemaError, match="records"):
        assess("records", lock, faults)  # type: ignore[arg-type]
    with pytest.raises(SchemaError, match=r"records\[0\]"):
        assess(faults, lock, faults)  # type: ignore[arg-type]
    with pytest.raises(SchemaError, match=r"faults\[1\]"):
        assess(records, lock, [faults[0], records[0]])  # type: ignore[list-item]
    with pytest.raises(SchemaError, match="faults"):
        assess(records, lock, {fault.scenario_id: fault for fault in faults})  # type: ignore[arg-type]


def test_assess_does_not_mutate_its_inputs() -> None:
    lock = make_lock()
    records, faults = evidence(lock)
    before = (to_data(lock), [to_data(r) for r in records], [to_data(f) for f in faults])
    assess(records, lock, faults)
    assert before == (to_data(lock), [to_data(r) for r in records], [to_data(f) for f in faults])


def test_assessment_module_imports_no_adapter_or_native_module() -> None:
    script = (
        "import sys\n"
        "import actseal.assessment\n"
        "loaded = sorted(name for name in sys.modules if name.split('.')[0] in "
        "('laya', 'torch', 'transformers', 'huggingface_hub', 'safetensors', 'numpy', 'scipy') "
        "or name.startswith('actseal.adapters') or name == 'actseal.replay')\n"
        "print(loaded)\n"
    )
    result = subprocess.run(  # noqa: S603 - fixed interpreter and literal script, no user input
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    assert result.stdout.strip() == "[]"


def test_stats_module_does_not_import_assessment_or_its_dependencies() -> None:
    script = (
        "import sys\n"
        "import actseal.stats\n"
        "loaded = sorted(name for name in sys.modules if name in ("
        "'actseal.assessment', 'actseal.locking', 'actseal.policy', "
        "'actseal.normalization', 'actseal.faults', 'actseal.contract'))\n"
        "print(loaded)\n"
    )
    result = subprocess.run(  # noqa: S603 - fixed interpreter and literal script, no user input
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    assert result.stdout.strip() == "[]"
