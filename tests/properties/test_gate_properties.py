"""Gate semantics of ``actseal.assessment.assess`` against independent oracles.

Every piece of evidence is produced with the accepted authorities
(``create_lock``/``validate_lock``, ``normalize``, ``evaluate``,
``run_fault_campaign``) so the lock carries the identity of the running source
and validation is never disabled. Expected verdicts are restated from
docs/statistical-contract.md in plain code; expected endpoints come from
``decimal`` closed forms or from the exact ``fractions.Fraction`` binomial tail
driving the gate's 60-step bisection schedule (the same oracle form as
tests/unit/test_stats.py, adapted from agent-reliability-ci, Apache-2.0,
commit ``d13dd94124cb71d378a4e76224fc115b750e8133``). No expected value is
read back from ``assess``.

The only seam is the documented defective-evaluator wrapper: the accepted
policy never violates a canonical fault, so a *reproducible* violation is
simulated by wrapping the evaluator ``assessment`` imports for one outcome.

Each test names the semantic mutation of tools/check_mutations.py it is
designated to kill where that applies.
"""

from __future__ import annotations

import json
import math
import random
from collections.abc import Sequence
from dataclasses import replace
from decimal import Decimal, localcontext
from fractions import Fraction
from itertools import accumulate

import pytest

import actseal.assessment as assessment_module
from actseal.assessment import (
    REASON_CONTRACT_SATISFIED,
    REASON_COVERAGE_BELOW_MINIMUM,
    REASON_EVIDENCE_INSUFFICIENT,
    REASON_NO_ACCEPTED_CASES,
    REASON_RISK_EXCEEDS_LIMIT,
    assess,
)
from actseal.faults import run_fault_campaign
from actseal.locking import FAULT_INVENTORY, create_lock, validate_lock
from actseal.normalization import normalize, request_sha256
from actseal.policy import evaluate
from actseal.records import (
    CapturedOutcome,
    Case,
    ChoiceAnswer,
    Contract,
    DecisionRecord,
    DecisionRequest,
    FaultResult,
    GateLimits,
    Interval,
    LockedPolicy,
    Outcome,
    PlanLock,
    PolicyDecision,
    Status,
    Verdict,
)
from conftest import make_contract, make_identity

ALL_LABELS = ("billing", "technical", "sales")
CALIBRATION = '{"case_id": "c-001", "state": "Calibration one.", "expected_label": "billing"}\n'
GOLD: tuple[tuple[str, str, str], ...] = (
    ("v-001", "Refund missing after cancellation.", "billing"),
    ("v-002", "Login page returns 500.", "technical"),
    ("v-003", "Is there bulk license pricing?", "sales"),
    ("v-004", "Charged twice this month.", "billing"),
    ("v-005", "App crashes on launch.", "technical"),
    ("v-006", "Need a quote for fifty seats.", "sales"),
)
FULL = Interval(0.0, 1.0)
TAIL_DIVISOR = 4
BISECTION_STEPS = 60
ACT_PROBABILITY = 0.95
ABSTAIN_PROBABILITY = 0.5

SEED_THRESHOLD = 20261012
SEED_ALPHA = 20261013
SEED_PROFILES = 20261014


# --------------------------------------------------------------------------- #
# Evidence builders (accepted authorities only)
# --------------------------------------------------------------------------- #


def verification_jsonl(cases: Sequence[tuple[str, str, str]]) -> str:
    return "".join(
        json.dumps({"case_id": case_id, "state": state, "expected_label": label}) + "\n"
        for case_id, state, label in cases
    )


def many_cases(count: int) -> tuple[tuple[str, str, str], ...]:
    return tuple(
        (f"v-{index:04d}", f"Verification case number {index}.", ALL_LABELS[index % 3])
        for index in range(1, count + 1)
    )


def contract_with(
    *,
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
        LockedPolicy(ALL_LABELS, ALL_LABELS, threshold),
        GateLimits(max_risk, min_coverage, alpha),
        base.evidence_scope,
        base.population,
    )


def make_lock(
    contract: Contract | None = None, cases: Sequence[tuple[str, str, str]] = GOLD
) -> PlanLock:
    """A lock sealed over the running source; validation stays enabled."""
    lock = create_lock(
        contract or contract_with(), CALIBRATION, verification_jsonl(cases), make_identity()
    )
    validate_lock(lock)
    return lock


def answer_body(choice: str, selected: float) -> str:
    rest = (1.0 - selected) / (len(ALL_LABELS) - 1)
    probabilities = {label: (selected if label == choice else rest) for label in ALL_LABELS}
    return json.dumps({"type": "choice", "choice": choice, "probabilities": probabilities})


def capture_for(
    lock: PlanLock, case: Case, body: str, request: DecisionRequest | None = None
) -> CapturedOutcome:
    request = request or DecisionRequest(case.case_id, case.state, lock.contract.question)
    return CapturedOutcome(request_sha256(request), lock.model_identity, body, None, (), False)


def record_from_capture(lock: PlanLock, case: Case, capture: CapturedOutcome) -> DecisionRecord:
    outcome = normalize(capture, lock.contract.question, lock.model_identity)
    decision = evaluate(outcome, lock.contract.policy)
    return DecisionRecord(case.case_id, capture, outcome, decision)


def record_for(lock: PlanLock, case: Case, choice: str, selected: float) -> DecisionRecord:
    return record_from_capture(lock, case, capture_for(lock, case, answer_body(choice, selected)))


def correct_act_records(lock: PlanLock) -> tuple[DecisionRecord, ...]:
    records = tuple(
        record_for(lock, case, case.expected_label, ACT_PROBABILITY)
        for case in lock.verification_cases
    )
    assert all(record.decision.action == "ACT" for record in records)
    return records


def wrong_label(gold: str) -> str:
    return next(label for label in ALL_LABELS if label != gold)


def profile_records(lock: PlanLock, accepted: int, errors: int) -> tuple[DecisionRecord, ...]:
    """``accepted`` ACT records (the first ``errors`` of them wrong), the rest ABSTAIN."""
    records: list[DecisionRecord] = []
    for index, case in enumerate(lock.verification_cases):
        if index < errors:
            record = record_for(lock, case, wrong_label(case.expected_label), ACT_PROBABILITY)
        elif index < accepted:
            record = record_for(lock, case, case.expected_label, ACT_PROBABILITY)
        else:
            record = record_for(lock, case, case.expected_label, ABSTAIN_PROBABILITY)
        records.append(record)
    actions = [record.decision.action for record in records]
    assert actions == ["ACT"] * accepted + ["ABSTAIN"] * (len(records) - accepted)
    return tuple(records)


def fault_index(kind: str) -> int:
    return next(index for index, spec in enumerate(FAULT_INVENTORY) if spec.kind == kind)


def reproducible_violation(
    lock: PlanLock, kind: str, decision: PolicyDecision, monkeypatch: pytest.MonkeyPatch
) -> list[FaultResult]:
    """Fault results whose one violation the (wrapped) evaluator faithfully reproduces."""
    faults = list(run_fault_campaign(lock))
    index = fault_index(kind)
    original = faults[index]
    assert original.decision.action == FAULT_INVENTORY[index].expected_action
    assert decision.action != original.decision.action
    faults[index] = replace(original, decision=decision)

    def defective(outcome: Outcome, policy: LockedPolicy) -> PolicyDecision:
        if outcome == original.outcome:
            return decision
        return evaluate(outcome, policy)  # the accepted evaluator for every other outcome

    monkeypatch.setattr(assessment_module, "evaluate", defective)
    return faults


# --------------------------------------------------------------------------- #
# Independent oracles
# --------------------------------------------------------------------------- #


def closed_form_root(tail: float, n: int) -> Decimal:
    """``tail ** (1/n)`` to 40 digits: low(n, n) and ``1 - high(0, n)``."""
    with localcontext() as context:
        context.prec = 40
        return Decimal(tail) ** (Decimal(1) / Decimal(n))


def assert_decimal_endpoint(value: float, reference: Decimal) -> None:
    assert value == pytest.approx(float(reference), rel=0, abs=1e-15)


def _pmf(n: int, p: float) -> list[Fraction]:
    prob = Fraction.from_float(p)
    return [math.comb(n, k) * prob**k * (1 - prob) ** (n - k) for k in range(n + 1)]


def _oracle_tail(x: int, n: int, p: float, *, upper: bool) -> Fraction:
    terms = _pmf(n, p)
    if upper:
        return list(accumulate(reversed(terms)))[::-1][x]
    return list(accumulate(terms))[x]


def _oracle_root(x: int, n: int, tail: float, *, upper: bool) -> float:
    low, high = 0.0, 1.0
    target = Fraction.from_float(tail)
    for _ in range(BISECTION_STEPS):
        midpoint = (low + high) / 2.0
        greater = _oracle_tail(x, n, midpoint, upper=upper) > target
        if upper == greater:
            high = midpoint
        else:
            low = midpoint
    return (low + high) / 2.0


def oracle_interval(x: int, n: int, tail: float) -> Interval:
    low = 0.0 if x == 0 else _oracle_root(x, n, tail, upper=True)
    high = 1.0 if x == n else _oracle_root(x, n, tail, upper=False)
    return Interval(low, high)


def oracle_verdict(
    total: int, accepted: int, errors: int, limits: GateLimits
) -> tuple[Status, tuple[str, ...], Interval, Interval]:
    """docs/statistical-contract.md verdict rules restated independently of ``assess``."""
    tail = limits.alpha / TAIL_DIVISOR
    risk = FULL if accepted == 0 else oracle_interval(errors, accepted, tail)
    coverage = oracle_interval(accepted, total, tail)
    reasons: set[str] = set()
    if accepted == 0:
        reasons.add(REASON_NO_ACCEPTED_CASES)
    if risk.lower > limits.max_risk:
        reasons.add(REASON_RISK_EXCEEDS_LIMIT)
    if coverage.upper < limits.min_coverage:
        reasons.add(REASON_COVERAGE_BELOW_MINIMUM)
    status: Status
    if reasons & {REASON_RISK_EXCEEDS_LIMIT, REASON_COVERAGE_BELOW_MINIMUM}:
        status = "BLOCK"
    elif accepted > 0 and risk.upper <= limits.max_risk and coverage.lower >= limits.min_coverage:
        status = "PASS"
        reasons.add(REASON_CONTRACT_SATISFIED)
    else:
        status = "INCONCLUSIVE"
        reasons.add(REASON_EVIDENCE_INSUFFICIENT)
    return status, tuple(sorted(reasons)), risk, coverage


def assert_matches(
    verdict: Verdict, lock: PlanLock, total: int, accepted: int, errors: int
) -> None:
    status, reasons, risk, coverage = oracle_verdict(total, accepted, errors, lock.contract.limits)
    assert verdict.status == status, (total, accepted, errors, lock.contract.limits)
    assert verdict.reasons == reasons, (total, accepted, errors, lock.contract.limits)
    assert (verdict.total, verdict.accepted, verdict.errors) == (total, accepted, errors)
    assert verdict.risk == risk, (total, accepted, errors)
    assert verdict.coverage == coverage, (total, accepted, errors)
    assert verdict.lock_sha256 == lock.sha256


# --------------------------------------------------------------------------- #
# M01: each interval uses the alpha / 4 tail
# --------------------------------------------------------------------------- #


def test_alpha_quarter_endpoints_match_the_decimal_oracle_at_alpha_point_two() -> None:
    """alpha = 0.2 -> tail 0.05; six correct ACTs: risk.upper = 1 - 0.05^(1/6) and
    coverage.lower = 0.05^(1/6) (both one-term tails); any other divisor moves them."""
    lock = make_lock(contract_with(alpha=0.2))
    verdict = assess(correct_act_records(lock), lock, run_fault_campaign(lock))
    assert (verdict.total, verdict.accepted, verdict.errors) == (6, 6, 0)
    root = closed_form_root(0.2 / TAIL_DIVISOR, 6)
    assert_decimal_endpoint(verdict.risk.upper, 1 - root)
    assert_decimal_endpoint(verdict.coverage.lower, root)
    assert verdict.risk.lower == 0.0
    assert verdict.coverage.upper == 1.0
    # The half-alpha and whole-alpha tails are measurably different roots.
    for other_divisor in (1, 2, 8):
        other = closed_form_root(0.2 / other_divisor, 6)
        assert abs(float(root) - float(other)) > 1e-3


def test_generated_alphas_place_each_tail_at_alpha_over_four() -> None:
    rng = random.Random(SEED_ALPHA)  # noqa: S311
    alphas = {0.05, 0.2, 0.01, 1e-6, math.nextafter(1.0, 0.0)}
    alphas |= {rng.uniform(1e-6, 1.0) for _ in range(6)}
    for alpha in sorted(alphas):
        lock = make_lock(contract_with(alpha=alpha, max_risk=1.0, min_coverage=0.0))
        verdict = assess(correct_act_records(lock), lock, run_fault_campaign(lock))
        root = closed_form_root(alpha / TAIL_DIVISOR, 6)
        assert_decimal_endpoint(verdict.risk.upper, 1 - root)
        assert_decimal_endpoint(verdict.coverage.lower, root)


# --------------------------------------------------------------------------- #
# M05 / M06: PASS selects the risk UPPER and the coverage LOWER bound
# --------------------------------------------------------------------------- #


def test_pass_requires_the_risk_upper_bound_not_the_lower_bound() -> None:
    """Six correct ACTs, alpha 0.05, max_risk 0.05, min_coverage 0.4: coverage.lower
    (~0.4818) clears 0.4 and risk.lower is 0, but risk.upper (~0.518) exceeds 0.05, so
    the verdict is INCONCLUSIVE. Selecting risk.lower would wrongly PASS."""
    lock = make_lock(contract_with(alpha=0.05, max_risk=0.05, min_coverage=0.4))
    verdict = assess(correct_act_records(lock), lock, run_fault_campaign(lock))
    root = closed_form_root(0.05 / TAIL_DIVISOR, 6)
    assert (verdict.total, verdict.accepted, verdict.errors) == (6, 6, 0)
    assert verdict.risk.lower == 0.0
    assert_decimal_endpoint(verdict.risk.upper, 1 - root)
    assert_decimal_endpoint(verdict.coverage.lower, root)
    assert verdict.coverage.upper == 1.0
    assert verdict.risk.lower <= 0.05 < verdict.risk.upper
    assert verdict.coverage.lower >= 0.4
    assert verdict.status == "INCONCLUSIVE"
    assert verdict.reasons == (REASON_EVIDENCE_INSUFFICIENT,)


def test_pass_requires_the_coverage_lower_bound_not_the_upper_bound() -> None:
    """Six correct ACTs, alpha 0.05, max_risk 0.6, min_coverage 0.5: risk.upper (~0.518)
    is within 0.6 and coverage.upper is 1.0, but coverage.lower (~0.4818) is below 0.5,
    so the verdict is INCONCLUSIVE. Selecting coverage.upper would wrongly PASS."""
    lock = make_lock(contract_with(alpha=0.05, max_risk=0.6, min_coverage=0.5))
    verdict = assess(correct_act_records(lock), lock, run_fault_campaign(lock))
    root = closed_form_root(0.05 / TAIL_DIVISOR, 6)
    assert (verdict.total, verdict.accepted, verdict.errors) == (6, 6, 0)
    assert_decimal_endpoint(verdict.risk.upper, 1 - root)
    assert verdict.risk.upper <= 0.6
    assert_decimal_endpoint(verdict.coverage.lower, root)
    assert verdict.coverage.lower < 0.5 <= verdict.coverage.upper == 1.0
    assert verdict.status == "INCONCLUSIVE"
    assert verdict.reasons == (REASON_EVIDENCE_INSUFFICIENT,)


# --------------------------------------------------------------------------- #
# M08: an integrity failure outranks a reproducible fault violation
# --------------------------------------------------------------------------- #


def test_integrity_failure_outranks_a_reproducible_fault_violation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Complete records, one of them hashed for a different state text, plus a fault
    violation the wrapped evaluator reproduces: ERROR with the integrity code only."""
    lock = make_lock(contract_with(max_risk=0.6, min_coverage=0.4))
    records = list(correct_act_records(lock))
    case = lock.verification_cases[2]
    altered = DecisionRequest(case.case_id, "A different, easier ticket.", lock.contract.question)
    corrupted = capture_for(lock, case, answer_body(case.expected_label, ACT_PROBABILITY), altered)
    assert corrupted.request_sha256 == request_sha256(altered)
    assert corrupted.request_sha256 != records[2].capture.request_sha256
    records[2] = record_from_capture(lock, case, corrupted)
    assert records[2].decision.action == "ACT"
    assert [record.case_id for record in records] == [c.case_id for c in lock.verification_cases]

    violation = PolicyDecision("ACT", "billing", "test.defective_policy", False)
    faults = reproducible_violation(lock, "low_confidence", violation, monkeypatch)

    verdict = assess(records, lock, faults)
    assert verdict.status == "ERROR"
    assert verdict.reasons == ("integrity.request_hash",)
    assert (verdict.total, verdict.accepted, verdict.errors) == (0, 0, 0)
    assert verdict.risk == FULL
    assert verdict.coverage == FULL
    assert verdict.lock_sha256 == lock.sha256

    # Control: the same faults with intact records are a genuine, reproduced BLOCK,
    # which shows the violation above was faithfully reproduced rather than forged.
    control = assess(correct_act_records(lock), lock, faults)
    assert control.status == "BLOCK"
    assert control.reasons == ("fault.low_confidence",)
    assert (control.total, control.accepted, control.errors) == (6, 6, 0)


# --------------------------------------------------------------------------- #
# M04: the policy threshold is inclusive (ACT at equality, ABSTAIN one ulp below)
# --------------------------------------------------------------------------- #


def answer_at(probability: float) -> ChoiceAnswer:
    rest = (1.0 - probability) / (len(ALL_LABELS) - 1)
    pairs = tuple((label, probability if label == "billing" else rest) for label in ALL_LABELS)
    return ChoiceAnswer("billing", pairs, probability, None, (), False)


def test_generated_thresholds_act_at_equality_and_abstain_one_ulp_below() -> None:
    rng = random.Random(SEED_THRESHOLD)  # noqa: S311
    thresholds = {1.0, 0.9, 0.5, 5e-324, 1e-300, math.nextafter(1.0, 0.0)}
    thresholds |= {rng.random() for _ in range(20)} - {0.0}
    thresholds |= {math.ldexp(rng.random(), -rng.randrange(1, 200)) for _ in range(10)} - {0.0}
    for threshold in sorted(thresholds):
        policy = LockedPolicy(ALL_LABELS, ALL_LABELS, threshold)
        at_equality = evaluate(answer_at(threshold), policy)
        assert at_equality == PolicyDecision("ACT", "billing", "policy.allowed", False), threshold
        below = math.nextafter(threshold, 0.0)
        assert evaluate(answer_at(below), policy) == PolicyDecision(
            "ABSTAIN", None, "policy.low_confidence", False
        ), threshold
        above = math.nextafter(threshold, 1.0)
        assert evaluate(answer_at(above), policy).action == "ACT", threshold


# --------------------------------------------------------------------------- #
# Generated count profiles against the full verdict oracle
# --------------------------------------------------------------------------- #


def _random_limits(rng: random.Random) -> GateLimits:
    max_risk = rng.choice((0.05, 0.1, 0.3, 0.6, 1.0, rng.random()))
    min_coverage = rng.choice((0.0, 0.2, 0.4, 0.5, 0.9, rng.random()))
    alpha = rng.choice((0.05, 0.2, 0.01, rng.uniform(1e-6, 1.0)))
    return GateLimits(max_risk, min_coverage, alpha)


def test_generated_count_profiles_match_the_independent_verdict_oracle() -> None:
    rng = random.Random(SEED_PROFILES)  # noqa: S311
    profiles: list[tuple[int, int, int]] = [(1, 0, 0), (1, 1, 0), (1, 1, 1), (6, 0, 0), (6, 6, 6)]
    while len(profiles) < 24:
        total = rng.randint(1, 24)
        accepted = rng.randint(0, total)
        errors = rng.randint(0, accepted)
        profiles.append((total, accepted, errors))
    statuses: set[str] = set()
    for total, accepted, errors in profiles:
        limits = _random_limits(rng)
        contract = contract_with(
            max_risk=limits.max_risk, min_coverage=limits.min_coverage, alpha=limits.alpha
        )
        lock = make_lock(contract, many_cases(total))
        records = profile_records(lock, accepted, errors)
        verdict = assess(records, lock, run_fault_campaign(lock))
        assert_matches(verdict, lock, total, accepted, errors)
        statuses.add(verdict.status)
    assert statuses == {"PASS", "BLOCK", "INCONCLUSIVE"}


def test_zero_accepted_profiles_report_the_full_risk_interval_and_never_pass() -> None:
    rng = random.Random(SEED_PROFILES + 1)  # noqa: S311
    for total in (1, 2, 5, 9, 17):
        limits = GateLimits(1.0, 0.0, rng.choice((0.05, 0.2, 0.5)))
        contract = contract_with(max_risk=1.0, min_coverage=0.0, alpha=limits.alpha)
        lock = make_lock(contract, many_cases(total))
        verdict = assess(profile_records(lock, 0, 0), lock, run_fault_campaign(lock))
        assert verdict.status == "INCONCLUSIVE"
        assert verdict.reasons == (REASON_EVIDENCE_INSUFFICIENT, REASON_NO_ACCEPTED_CASES)
        assert (verdict.total, verdict.accepted, verdict.errors) == (total, 0, 0)
        assert verdict.risk == FULL
        assert verdict.coverage.lower == 0.0
        assert_decimal_endpoint(
            verdict.coverage.upper, 1 - closed_form_root(limits.alpha / TAIL_DIVISOR, total)
        )
