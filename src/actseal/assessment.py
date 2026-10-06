"""Complete-evidence risk/coverage assessment (plan/CONTRACTS.md section 5, ADR 0003/0009).

``assess`` turns one sealed lock, its scheduled decision records and the six
fault results into a :class:`Verdict`. It trusts nothing stored: every
recorded request, normalization and policy decision is recomputed from the
raw capture with the accepted pure authorities and must match exactly before
anything is counted.

Order of work:

1. **Integrity.** ``validate_lock`` (seal, implementation fingerprint, frozen
   fault inventory, case inventory). Exactly one record per locked
   verification case, in lock order. For each record the request is rebuilt
   from the locked case and question, its canonical hash must equal the
   captured hash, the raw capture is re-normalized against the locked
   identity and re-evaluated against the locked policy, and both results must
   equal the recorded outcome and decision. Exactly one fault result per
   locked scenario, in lock order, whose request and capture equal the pure
   canonical generator and whose outcome/decision equal re-normalization and
   re-evaluation. Any failure is ERROR with ``integrity.<invariant>`` codes,
   zero counts and [0, 1] intervals; no partial statistics are reported.
2. **Infrastructure (ADR 0009).** With a ``laya`` locked provider, a regular
   capture whose transport failure is ``timeout`` or ``unavailable`` means the
   resident worker was lost, so later outcomes depended on an earlier case.
   The run is ERROR with ``infrastructure.worker_invalidated``. Synthetic fault
   captures are excluded; fixture failures and other failure codes stay in the
   denominator.
3. **Fault contract.** A correctly reconstructed fault whose re-evaluated
   action differs from its locked expected action is BLOCK (``fault.<kind>``).
4. **Statistics.** n is every locked verification case; a is the number of
   final ACT decisions; e is the number of ACT choices unequal to the locked
   gold label. Each Clopper-Pearson tail is ``alpha / 4``. Risk uses e/a, or
   [0, 1] when a == 0 (no PASS, no zero-risk claim). Coverage uses a/n.
   PASS iff a > 0, risk.upper <= max_risk and coverage.lower >= min_coverage.
   BLOCK iff risk.lower > max_risk or coverage.upper < min_coverage.
   Otherwise INCONCLUSIVE. Precedence ERROR > BLOCK > INCONCLUSIVE > PASS.

Reasons are sorted unique machine codes. This module imports no adapter or
model library; it depends on records, errors, serialization, the T10
lock/policy authorities, the T30 pure normalizer/fault generator and the
numerical kernel in ``stats``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final, TypeVar

from actseal.errors import ActsealError, SchemaError
from actseal.faults import fault_capture
from actseal.locking import validate_lock
from actseal.normalization import normalize, request_sha256
from actseal.policy import evaluate
from actseal.records import (
    DecisionRecord,
    DecisionRequest,
    FaultResult,
    Interval,
    PlanLock,
    Status,
    Verdict,
)
from actseal.stats import clopper_pearson_tail

__all__ = [
    "REASON_CONTRACT_SATISFIED",
    "REASON_COVERAGE_BELOW_MINIMUM",
    "REASON_EVIDENCE_INSUFFICIENT",
    "REASON_FAULT_PREFIX",
    "REASON_INTEGRITY_PREFIX",
    "REASON_NO_ACCEPTED_CASES",
    "REASON_RISK_EXCEEDS_LIMIT",
    "REASON_WORKER_INVALIDATED",
    "TAIL_DIVISOR",
    "assess",
]

REASON_RISK_EXCEEDS_LIMIT: Final = "risk.exceeds_limit"
REASON_COVERAGE_BELOW_MINIMUM: Final = "coverage.below_minimum"
REASON_EVIDENCE_INSUFFICIENT: Final = "evidence.insufficient"
REASON_NO_ACCEPTED_CASES: Final = "risk.no_accepted_cases"
REASON_CONTRACT_SATISFIED: Final = "contract.satisfied"
REASON_WORKER_INVALIDATED: Final = "infrastructure.worker_invalidated"
REASON_FAULT_PREFIX: Final = "fault."
REASON_INTEGRITY_PREFIX: Final = "integrity."

#: Four one-sided tails share the family alpha: two per interval (ADR 0003).
TAIL_DIVISOR: Final = 4

_WORKER_LOSS_CODES: Final[frozenset[str]] = frozenset({"timeout", "unavailable"})
_WORKER_LOSS_PROVIDER: Final = "laya"
_FULL: Final = (0.0, 1.0)

_T = TypeVar("_T")


def _integrity(invariant: str) -> str:
    return f"{REASON_INTEGRITY_PREFIX}{invariant}"


def _check_sequence(field: str, value: object, item_type: type[_T]) -> tuple[_T, ...]:
    if isinstance(value, str | bytes | bytearray) or not isinstance(value, Sequence):
        raise SchemaError(f"{field}: must be a sequence")
    items: list[_T] = []
    for index, item in enumerate(value):
        if not isinstance(item, item_type):
            raise SchemaError(f"{field}[{index}]: must be {item_type.__name__}")
        items.append(item)
    return tuple(items)


# --------------------------------------------------------------------------- #
# Integrity
# --------------------------------------------------------------------------- #


def _check_records(records: tuple[DecisionRecord, ...], lock: PlanLock, failures: set[str]) -> None:
    """Inventory, request reconstruction, re-normalization and re-evaluation per record."""
    expected_ids = tuple(case.case_id for case in lock.verification_cases)
    if tuple(record.case_id for record in records) != expected_ids:
        failures.add(_integrity("records"))
        return
    question = lock.contract.question
    policy = lock.contract.policy
    for record, case in zip(records, lock.verification_cases, strict=True):
        request = DecisionRequest(case.case_id, case.state, question)
        if record.capture.request_sha256 != request_sha256(request):
            failures.add(_integrity("request_hash"))
        outcome = normalize(record.capture, question, lock.model_identity)
        if outcome != record.outcome:
            failures.add(_integrity("outcome"))
        if evaluate(outcome, policy) != record.decision:
            failures.add(_integrity("decision"))


def _check_faults(faults: tuple[FaultResult, ...], lock: PlanLock, failures: set[str]) -> None:
    """Inventory, canonical request/capture equality, re-normalization and re-evaluation."""
    expected_ids = tuple(spec.scenario_id for spec in lock.fault_inventory)
    if tuple(fault.scenario_id for fault in faults) != expected_ids:
        failures.add(_integrity("faults"))
        return
    question = lock.contract.question
    policy = lock.contract.policy
    for fault, spec in zip(faults, lock.fault_inventory, strict=True):
        request, capture = fault_capture(lock, spec)
        if fault.request != request:
            failures.add(_integrity("fault_request"))
        if fault.capture != capture:
            failures.add(_integrity("fault_capture"))
        outcome = normalize(fault.capture, question, lock.model_identity)
        if outcome != fault.outcome:
            failures.add(_integrity("fault_outcome"))
        if evaluate(outcome, policy) != fault.decision:
            failures.add(_integrity("fault_decision"))


def _integrity_failures(
    records: tuple[DecisionRecord, ...], lock: PlanLock, faults: tuple[FaultResult, ...]
) -> set[str]:
    failures: set[str] = set()
    try:
        validate_lock(lock)
    except ActsealError:
        failures.add(_integrity("lock"))
        return failures
    _check_records(records, lock, failures)
    _check_faults(faults, lock, failures)
    return failures


def _worker_invalidated(records: tuple[DecisionRecord, ...], lock: PlanLock) -> bool:
    """ADR 0009: a regular Laya transport loss makes later outcomes dependent."""
    if lock.model_identity.provider != _WORKER_LOSS_PROVIDER:
        return False
    return any(record.capture.failure_code in _WORKER_LOSS_CODES for record in records)


def _fault_violations(faults: tuple[FaultResult, ...], lock: PlanLock) -> set[str]:
    return {
        f"{REASON_FAULT_PREFIX}{spec.kind}"
        for fault, spec in zip(faults, lock.fault_inventory, strict=True)
        if fault.decision.action != spec.expected_action
    }


# --------------------------------------------------------------------------- #
# Statistics
# --------------------------------------------------------------------------- #


def _counts(records: tuple[DecisionRecord, ...], lock: PlanLock) -> tuple[int, int, int]:
    """Return ``(n, a, e)`` from final decisions against locked gold labels."""
    accepted = 0
    errors = 0
    for record, case in zip(records, lock.verification_cases, strict=True):
        if record.decision.action != "ACT":
            continue
        accepted += 1
        if record.decision.choice != case.expected_label:
            errors += 1
    return len(lock.verification_cases), accepted, errors


def _statistics(
    records: tuple[DecisionRecord, ...], lock: PlanLock
) -> tuple[Status, set[str], int, int, int, Interval, Interval]:
    total, accepted, errors = _counts(records, lock)
    limits = lock.contract.limits
    tail = limits.alpha / TAIL_DIVISOR
    risk = _FULL if accepted == 0 else clopper_pearson_tail(errors, accepted, tail)
    coverage = clopper_pearson_tail(accepted, total, tail)
    reasons: set[str] = set()
    if accepted == 0:
        reasons.add(REASON_NO_ACCEPTED_CASES)
    if risk[0] > limits.max_risk:
        reasons.add(REASON_RISK_EXCEEDS_LIMIT)
    if coverage[1] < limits.min_coverage:
        reasons.add(REASON_COVERAGE_BELOW_MINIMUM)
    status: Status
    if REASON_RISK_EXCEEDS_LIMIT in reasons or REASON_COVERAGE_BELOW_MINIMUM in reasons:
        status = "BLOCK"
    elif accepted > 0 and risk[1] <= limits.max_risk and coverage[0] >= limits.min_coverage:
        status = "PASS"
        reasons.add(REASON_CONTRACT_SATISFIED)
    else:
        status = "INCONCLUSIVE"
        reasons.add(REASON_EVIDENCE_INSUFFICIENT)
    return status, reasons, total, accepted, errors, Interval(*risk), Interval(*coverage)


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #


def _error(lock: PlanLock, reasons: set[str]) -> Verdict:
    return Verdict(
        "ERROR",
        tuple(sorted(reasons)),
        0,
        0,
        0,
        Interval(*_FULL),
        Interval(*_FULL),
        lock.contract.evidence_scope,
        lock.sha256,
    )


def assess(
    records: Sequence[DecisionRecord], lock: PlanLock, faults: Sequence[FaultResult]
) -> Verdict:
    """Assess complete evidence against the lock; never count unverified or partial data."""
    if not isinstance(lock, PlanLock):
        raise SchemaError("lock: must be PlanLock")
    typed_records = _check_sequence("records", records, DecisionRecord)
    typed_faults = _check_sequence("faults", faults, FaultResult)

    failures = _integrity_failures(typed_records, lock, typed_faults)
    if failures:
        return _error(lock, failures)
    if _worker_invalidated(typed_records, lock):
        return _error(lock, {REASON_WORKER_INVALIDATED})

    status, reasons, total, accepted, errors, risk, coverage = _statistics(typed_records, lock)
    violations = _fault_violations(typed_faults, lock)
    if violations:
        status = "BLOCK"
        reasons.discard(REASON_CONTRACT_SATISFIED)
        reasons |= violations
    return Verdict(
        status,
        tuple(sorted(reasons)),
        total,
        accepted,
        errors,
        risk,
        coverage,
        lock.contract.evidence_scope,
        lock.sha256,
    )
