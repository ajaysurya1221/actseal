"""Frozen public record types for Actseal.

Every record is a frozen dataclass whose children are tuples or other frozen
records. Direct constructors validate the same domains that strict
deserialization enforces, convert caller-owned sequences into tuples so that no
mutable alias survives construction, and raise :class:`SchemaError` naming the
offending field or invariant without echoing the offending value.

Field order below is constructor order and matches plan/CONTRACTS.md section 1.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Final, Literal, TypeVar, get_args

from actseal.errors import SchemaError

__all__ = [
    "FAILURE_CODES",
    "MASS_TOLERANCE",
    "MAX_CASES_PER_SPLIT",
    "MAX_OPTIONS",
    "MIN_OPTIONS",
    "PROVIDERS",
    "SCHEMA_VERSION",
    "Action",
    "CapturedOutcome",
    "Case",
    "CaseRef",
    "ChoiceAnswer",
    "ChoiceQuestion",
    "Contract",
    "DecisionRecord",
    "DecisionRequest",
    "EvidenceBundle",
    "EvidenceScope",
    "FaultResult",
    "FaultSpec",
    "GateLimits",
    "Interval",
    "LockedPolicy",
    "ModelIdentity",
    "Option",
    "Outcome",
    "PlanLock",
    "PolicyDecision",
    "ProviderFailure",
    "Status",
    "Verdict",
]

Action = Literal["ACT", "ABSTAIN", "ESCALATE", "DENY"]
Status = Literal["PASS", "BLOCK", "INCONCLUSIVE", "ERROR"]
EvidenceScope = Literal["demo", "iid"]

SCHEMA_VERSION: Final = 1
MIN_OPTIONS: Final = 2
MAX_OPTIONS: Final = 16
MAX_CASES_PER_SPLIT: Final = 10_000
FAILURE_CODES: Final[frozenset[str]] = frozenset(
    {
        "timeout",
        "rate_limit",
        "provider_error",
        "malformed_response",
        "identity_mismatch",
        "unknown_choice",
        "input_too_long",
        "unavailable",
    }
)

_ACTIONS: Final[frozenset[str]] = frozenset(get_args(Action))
_STATUSES: Final[frozenset[str]] = frozenset(get_args(Status))
_EVIDENCE_SCOPES: Final[frozenset[str]] = frozenset(get_args(EvidenceScope))
_SHA256_HEX: Final = re.compile(r"[0-9a-f]{64}")
_MIN_ALPHA: Final = 1e-6
_PAIR_LENGTH: Final = 2
MASS_TOLERANCE: Final = 1e-12
PROVIDERS: Final[frozenset[str]] = frozenset({"fixture", "laya"})

_R = TypeVar("_R")


# --------------------------------------------------------------------------- #
# Validation helpers. Every message starts with the field name so that
# deserialization can prefix a path without re-parsing the text.
# --------------------------------------------------------------------------- #


def _fail(field: str, reason: str) -> SchemaError:
    return SchemaError(f"{field}: {reason}")


def _str(field: str, value: object, *, nonempty: bool = True) -> str:
    if not isinstance(value, str):
        raise _fail(field, "must be a string")
    if nonempty and not value:
        raise _fail(field, "must be nonempty")
    return value


def _optional_str(field: str, value: object, *, nonempty: bool) -> str | None:
    if value is None:
        return None
    return _str(field, value, nonempty=nonempty)


def _bool(field: str, value: object) -> bool:
    if type(value) is not bool:
        raise _fail(field, "must be a boolean")
    return value


def _int(
    field: str, value: object, *, minimum: int | None = None, maximum: int | None = None
) -> int:
    if type(value) is not int:
        raise _fail(field, "must be an integer")
    if minimum is not None and value < minimum:
        raise _fail(field, f"must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise _fail(field, f"must be <= {maximum}")
    return value


def _float(
    field: str,
    value: object,
    *,
    minimum: float,
    maximum: float,
    exclusive_minimum: bool = False,
    exclusive_maximum: bool = False,
) -> float:
    if type(value) is bool or not isinstance(value, int | float):
        raise _fail(field, "must be a number")
    try:
        number = float(value)
    except OverflowError:
        raise _fail(field, "must be finite") from None
    if not math.isfinite(number):
        raise _fail(field, "must be finite")
    low_ok = number > minimum if exclusive_minimum else number >= minimum
    high_ok = number < maximum if exclusive_maximum else number <= maximum
    if not (low_ok and high_ok):
        low = "(" if exclusive_minimum else "["
        high = ")" if exclusive_maximum else "]"
        raise _fail(field, f"must be in {low}{minimum}, {maximum}{high}")
    return number


def _optional_float(field: str, value: object, *, minimum: float, maximum: float) -> float | None:
    if value is None:
        return None
    return _float(field, value, minimum=minimum, maximum=maximum)


def _sha256(field: str, value: object) -> str:
    text = _str(field, value)
    if _SHA256_HEX.fullmatch(text) is None:
        raise _fail(field, "must be lowercase 64-character SHA256 hex")
    return text


def _literal(field: str, value: object, allowed: frozenset[str]) -> str:
    text = _str(field, value)
    if text not in allowed:
        raise _fail(field, "unsupported value")
    return text


def _sequence(field: str, value: object) -> tuple[object, ...]:
    """Copy a caller-owned list or tuple; strings and other iterables are rejected."""
    if isinstance(value, tuple):
        return value
    if isinstance(value, list):
        return tuple(value)
    raise _fail(field, "must be a list or tuple")


def _records(field: str, value: object, item_type: type[_R]) -> tuple[_R, ...]:
    checked: list[_R] = []
    for index, item in enumerate(_sequence(field, value)):
        if not isinstance(item, item_type):
            raise _fail(f"{field}[{index}]", f"must be {item_type.__name__}")
        checked.append(item)
    return tuple(checked)


def _str_tuple(field: str, value: object, *, nonempty_items: bool = True) -> tuple[str, ...]:
    items = _sequence(field, value)
    return tuple(
        _str(f"{field}[{i}]", item, nonempty=nonempty_items) for i, item in enumerate(items)
    )


def _unique_str_tuple(field: str, value: object) -> tuple[str, ...]:
    items = _str_tuple(field, value)
    if len(set(items)) != len(items):
        raise _fail(field, "must not contain duplicates")
    return items


def _pair(field: str, value: object) -> tuple[object, object]:
    items = _sequence(field, value)
    if len(items) != _PAIR_LENGTH:
        raise _fail(field, "must be a key/value pair")
    return items[0], items[1]


def _str_map(
    field: str, value: object, *, hashed_values: bool = False
) -> tuple[tuple[str, str], ...]:
    """Validate ``((key, value), ...)``; stored sorted by key with unique keys."""
    pairs: list[tuple[str, str]] = []
    for index, item in enumerate(_sequence(field, value)):
        key, item_value = _pair(f"{field}[{index}]", item)
        value_field = f"{field}[{index}].value"
        pairs.append(
            (
                _str(f"{field}[{index}].key", key),
                _sha256(value_field, item_value)
                if hashed_values
                else _str(value_field, item_value),
            )
        )
    keys = [key for key, _ in pairs]
    if len(set(keys)) != len(keys):
        raise _fail(field, "keys must be unique")
    return tuple(sorted(pairs))


def _hash_map(field: str, value: object) -> tuple[tuple[str, str], ...]:
    return _str_map(field, value, hashed_values=True)


def _probabilities(field: str, value: object) -> tuple[tuple[str, float], ...]:
    """Validate ordered ``((label, probability), ...)`` pairs with unique labels."""
    pairs: list[tuple[str, float]] = []
    for index, item in enumerate(_sequence(field, value)):
        label, probability = _pair(f"{field}[{index}]", item)
        pairs.append(
            (
                _str(f"{field}[{index}].label", label),
                _float(f"{field}[{index}].probability", probability, minimum=0.0, maximum=1.0),
            )
        )
    if not MIN_OPTIONS <= len(pairs) <= MAX_OPTIONS:
        raise _fail(field, f"must contain {MIN_OPTIONS}..{MAX_OPTIONS} entries")
    labels = [label for label, _ in pairs]
    if len(set(labels)) != len(labels):
        raise _fail(field, "labels must be unique")
    if abs(math.fsum(probability for _, probability in pairs) - 1.0) > MASS_TOLERANCE:
        raise _fail(field, f"total mass must be within {MASS_TOLERANCE} of 1")
    return tuple(pairs)


def _schema_version(field: str, value: object) -> int:
    version = _int(field, value)
    if version != SCHEMA_VERSION:
        raise _fail(field, "unsupported schema version")
    return version


def _set(record: object, field: str, value: object) -> None:
    object.__setattr__(record, field, value)


# --------------------------------------------------------------------------- #
# Records
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class Option:
    label: str
    description: str

    def __post_init__(self) -> None:
        _set(self, "label", _str("label", self.label))
        _set(self, "description", _str("description", self.description))


@dataclass(frozen=True, slots=True)
class ChoiceQuestion:
    question_id: str
    instructions: str
    options: tuple[Option, ...]

    def __post_init__(self) -> None:
        _set(self, "question_id", _str("question_id", self.question_id))
        _set(self, "instructions", _str("instructions", self.instructions))
        options = _records("options", self.options, Option)
        if not MIN_OPTIONS <= len(options) <= MAX_OPTIONS:
            raise _fail("options", f"must contain {MIN_OPTIONS}..{MAX_OPTIONS} options")
        labels = [option.label for option in options]
        if len(set(labels)) != len(labels):
            raise _fail("options", "labels must be unique")
        _set(self, "options", options)

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(option.label for option in self.options)


@dataclass(frozen=True, slots=True)
class Case:
    case_id: str
    state: str
    expected_label: str

    def __post_init__(self) -> None:
        _set(self, "case_id", _str("case_id", self.case_id))
        _set(self, "state", _str("state", self.state))
        _set(self, "expected_label", _str("expected_label", self.expected_label))


@dataclass(frozen=True, slots=True)
class CaseRef:
    case_id: str
    sha256: str

    def __post_init__(self) -> None:
        _set(self, "case_id", _str("case_id", self.case_id))
        _set(self, "sha256", _sha256("sha256", self.sha256))


@dataclass(frozen=True, slots=True)
class ModelIdentity:
    provider: str
    model: str
    revision: str
    artifact_hashes: tuple[tuple[str, str], ...]
    adapter_version: str
    normalizer_version: str
    runtime: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        _set(self, "provider", _literal("provider", self.provider, PROVIDERS))
        _set(self, "model", _str("model", self.model))
        _set(self, "revision", _str("revision", self.revision))
        _set(self, "artifact_hashes", _hash_map("artifact_hashes", self.artifact_hashes))
        _set(self, "adapter_version", _str("adapter_version", self.adapter_version))
        _set(self, "normalizer_version", _str("normalizer_version", self.normalizer_version))
        _set(self, "runtime", _str_map("runtime", self.runtime))


@dataclass(frozen=True, slots=True)
class DecisionRequest:
    case_id: str
    state: str
    question: ChoiceQuestion

    def __post_init__(self) -> None:
        _set(self, "case_id", _str("case_id", self.case_id))
        _set(self, "state", _str("state", self.state))
        if not isinstance(self.question, ChoiceQuestion):
            raise _fail("question", "must be ChoiceQuestion")


@dataclass(frozen=True, slots=True)
class CapturedOutcome:
    request_sha256: str
    identity: ModelIdentity
    body_json: str | None
    failure_code: str | None
    warnings: tuple[str, ...]
    fallback_used: bool

    def __post_init__(self) -> None:
        _set(self, "request_sha256", _sha256("request_sha256", self.request_sha256))
        if not isinstance(self.identity, ModelIdentity):
            raise _fail("identity", "must be ModelIdentity")
        body = _optional_str("body_json", self.body_json, nonempty=False)
        failure = _optional_str("failure_code", self.failure_code, nonempty=True)
        if (body is None) == (failure is None):
            raise _fail("body_json/failure_code", "exactly one must be present")
        if failure is not None:
            _literal("failure_code", failure, FAILURE_CODES)
        _set(self, "body_json", body)
        _set(self, "failure_code", failure)
        _set(self, "warnings", _str_tuple("warnings", self.warnings))
        _set(self, "fallback_used", _bool("fallback_used", self.fallback_used))


@dataclass(frozen=True, slots=True)
class ChoiceAnswer:
    choice: str
    probabilities: tuple[tuple[str, float], ...]
    selected_probability: float
    provider_confidence: float | None
    warnings: tuple[str, ...]
    fallback_used: bool

    def __post_init__(self) -> None:
        choice = _str("choice", self.choice)
        probabilities = _probabilities("probabilities", self.probabilities)
        selected = _float(
            "selected_probability", self.selected_probability, minimum=0.0, maximum=1.0
        )
        by_label = dict(probabilities)
        if choice not in by_label:
            raise _fail("choice", "must be one of the probability labels")
        if by_label[choice] != selected:
            raise _fail("selected_probability", "must equal the probability of choice")
        _set(self, "choice", choice)
        _set(self, "probabilities", probabilities)
        _set(self, "selected_probability", selected)
        _set(
            self,
            "provider_confidence",
            _optional_float(
                "provider_confidence", self.provider_confidence, minimum=0.0, maximum=1.0
            ),
        )
        _set(self, "warnings", _str_tuple("warnings", self.warnings))
        _set(self, "fallback_used", _bool("fallback_used", self.fallback_used))


@dataclass(frozen=True, slots=True)
class ProviderFailure:
    code: str
    warnings: tuple[str, ...]
    fallback_used: bool

    def __post_init__(self) -> None:
        _set(self, "code", _literal("code", self.code, FAILURE_CODES))
        _set(self, "warnings", _str_tuple("warnings", self.warnings))
        _set(self, "fallback_used", _bool("fallback_used", self.fallback_used))


type Outcome = ChoiceAnswer | ProviderFailure


def _outcome(field: str, value: object) -> Outcome:
    if not isinstance(value, ChoiceAnswer | ProviderFailure):
        raise _fail(field, "must be ChoiceAnswer or ProviderFailure")
    return value


@dataclass(frozen=True, slots=True)
class LockedPolicy:
    known_labels: tuple[str, ...]
    allowed_labels: tuple[str, ...]
    threshold: float

    def __post_init__(self) -> None:
        known = _unique_str_tuple("known_labels", self.known_labels)
        if not MIN_OPTIONS <= len(known) <= MAX_OPTIONS:
            raise _fail("known_labels", f"must contain {MIN_OPTIONS}..{MAX_OPTIONS} labels")
        allowed = _unique_str_tuple("allowed_labels", self.allowed_labels)
        if not allowed:
            raise _fail("allowed_labels", "must contain at least one label")
        if not set(allowed) <= set(known):
            raise _fail("allowed_labels", "must be a subset of known_labels")
        _set(self, "known_labels", known)
        _set(self, "allowed_labels", allowed)
        _set(
            self,
            "threshold",
            _float("threshold", self.threshold, minimum=0.0, maximum=1.0, exclusive_minimum=True),
        )


@dataclass(frozen=True, slots=True)
class GateLimits:
    max_risk: float
    min_coverage: float
    alpha: float

    def __post_init__(self) -> None:
        _set(self, "max_risk", _float("max_risk", self.max_risk, minimum=0.0, maximum=1.0))
        _set(
            self,
            "min_coverage",
            _float("min_coverage", self.min_coverage, minimum=0.0, maximum=1.0),
        )
        _set(
            self,
            "alpha",
            _float("alpha", self.alpha, minimum=_MIN_ALPHA, maximum=1.0, exclusive_maximum=True),
        )


@dataclass(frozen=True, slots=True)
class Contract:
    schema_version: int
    name: str
    question: ChoiceQuestion
    policy: LockedPolicy
    limits: GateLimits
    evidence_scope: EvidenceScope
    population: str

    def __post_init__(self) -> None:
        _set(self, "schema_version", _schema_version("schema_version", self.schema_version))
        _set(self, "name", _str("name", self.name))
        if not isinstance(self.question, ChoiceQuestion):
            raise _fail("question", "must be ChoiceQuestion")
        if not isinstance(self.policy, LockedPolicy):
            raise _fail("policy", "must be LockedPolicy")
        if not isinstance(self.limits, GateLimits):
            raise _fail("limits", "must be GateLimits")
        if self.policy.known_labels != self.question.labels:
            raise _fail("policy.known_labels", "must equal the question option labels in order")
        _set(
            self,
            "evidence_scope",
            _literal("evidence_scope", self.evidence_scope, _EVIDENCE_SCOPES),
        )
        _set(self, "population", _str("population", self.population))


@dataclass(frozen=True, slots=True)
class FaultSpec:
    scenario_id: str
    kind: str
    expected_action: Action

    def __post_init__(self) -> None:
        _set(self, "scenario_id", _str("scenario_id", self.scenario_id))
        _set(self, "kind", _str("kind", self.kind))
        _set(self, "expected_action", _literal("expected_action", self.expected_action, _ACTIONS))


def _unique_ids(field: str, ids: tuple[str, ...]) -> None:
    if len(set(ids)) != len(ids):
        raise _fail(field, "ids must be unique")


@dataclass(frozen=True, slots=True)
class PlanLock:
    schema_version: int
    contract: Contract
    model_identity: ModelIdentity
    calibration_sha256: str
    verification_sha256: str
    calibration_inventory: tuple[CaseRef, ...]
    verification_inventory: tuple[CaseRef, ...]
    verification_cases: tuple[Case, ...]
    fault_inventory: tuple[FaultSpec, ...]
    implementation_sha256: str
    sha256: str

    def __post_init__(self) -> None:
        _set(self, "schema_version", _schema_version("schema_version", self.schema_version))
        if not isinstance(self.contract, Contract):
            raise _fail("contract", "must be Contract")
        if not isinstance(self.model_identity, ModelIdentity):
            raise _fail("model_identity", "must be ModelIdentity")
        _set(self, "calibration_sha256", _sha256("calibration_sha256", self.calibration_sha256))
        _set(self, "verification_sha256", _sha256("verification_sha256", self.verification_sha256))
        calibration = _records("calibration_inventory", self.calibration_inventory, CaseRef)
        verification = _records("verification_inventory", self.verification_inventory, CaseRef)
        cases = _records("verification_cases", self.verification_cases, Case)
        faults = _records("fault_inventory", self.fault_inventory, FaultSpec)
        for field, inventory in (
            ("calibration_inventory", calibration),
            ("verification_inventory", verification),
        ):
            if not 1 <= len(inventory) <= MAX_CASES_PER_SPLIT:
                raise _fail(field, f"must contain 1..{MAX_CASES_PER_SPLIT} cases")
            _unique_ids(field, tuple(ref.case_id for ref in inventory))
        if tuple(case.case_id for case in cases) != tuple(ref.case_id for ref in verification):
            raise _fail("verification_cases", "ids must match verification_inventory in order")
        known = set(self.contract.question.labels)
        for index, case in enumerate(cases):
            if case.expected_label not in known:
                raise _fail(f"verification_cases[{index}].expected_label", "must be a known label")
        _unique_ids("fault_inventory", tuple(spec.scenario_id for spec in faults))
        _set(self, "calibration_inventory", calibration)
        _set(self, "verification_inventory", verification)
        _set(self, "verification_cases", cases)
        _set(self, "fault_inventory", faults)
        _set(
            self,
            "implementation_sha256",
            _sha256("implementation_sha256", self.implementation_sha256),
        )
        _set(self, "sha256", _sha256("sha256", self.sha256))


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    action: Action
    choice: str | None
    reason: str
    fallback_used: bool

    def __post_init__(self) -> None:
        action = _literal("action", self.action, _ACTIONS)
        choice = _optional_str("choice", self.choice, nonempty=True)
        if (action == "ACT") != (choice is not None):
            raise _fail("choice", "must be present exactly when action is ACT")
        _set(self, "action", action)
        _set(self, "choice", choice)
        _set(self, "reason", _str("reason", self.reason))
        _set(self, "fallback_used", _bool("fallback_used", self.fallback_used))


def _check_capture_outcome_decision(
    capture: object, outcome: object, decision: object
) -> tuple[CapturedOutcome, Outcome, PolicyDecision]:
    if not isinstance(capture, CapturedOutcome):
        raise _fail("capture", "must be CapturedOutcome")
    checked_outcome = _outcome("outcome", outcome)
    if not isinstance(decision, PolicyDecision):
        raise _fail("decision", "must be PolicyDecision")
    if isinstance(checked_outcome, ChoiceAnswer) and capture.body_json is None:
        raise _fail("outcome", "answer outcomes require a captured body_json")
    if decision.fallback_used != checked_outcome.fallback_used:
        raise _fail("decision.fallback_used", "must equal outcome.fallback_used")
    return capture, checked_outcome, decision


@dataclass(frozen=True, slots=True)
class DecisionRecord:
    case_id: str
    capture: CapturedOutcome
    outcome: Outcome
    decision: PolicyDecision

    def __post_init__(self) -> None:
        _set(self, "case_id", _str("case_id", self.case_id))
        _check_capture_outcome_decision(self.capture, self.outcome, self.decision)


@dataclass(frozen=True, slots=True)
class FaultResult:
    scenario_id: str
    request: DecisionRequest
    capture: CapturedOutcome
    outcome: Outcome
    decision: PolicyDecision

    def __post_init__(self) -> None:
        _set(self, "scenario_id", _str("scenario_id", self.scenario_id))
        if not isinstance(self.request, DecisionRequest):
            raise _fail("request", "must be DecisionRequest")
        _check_capture_outcome_decision(self.capture, self.outcome, self.decision)


@dataclass(frozen=True, slots=True)
class Interval:
    lower: float
    upper: float

    def __post_init__(self) -> None:
        lower = _float("lower", self.lower, minimum=0.0, maximum=1.0)
        upper = _float("upper", self.upper, minimum=0.0, maximum=1.0)
        if lower > upper:
            raise _fail("lower", "must not exceed upper")
        _set(self, "lower", lower)
        _set(self, "upper", upper)


@dataclass(frozen=True, slots=True)
class Verdict:
    status: Status
    reasons: tuple[str, ...]
    total: int
    accepted: int
    errors: int
    risk: Interval
    coverage: Interval
    evidence_scope: EvidenceScope
    lock_sha256: str

    def __post_init__(self) -> None:
        status = _literal("status", self.status, _STATUSES)
        reasons = _unique_str_tuple("reasons", self.reasons)
        if tuple(sorted(reasons)) != reasons:
            raise _fail("reasons", "must be sorted")
        total = _int("total", self.total, minimum=0, maximum=MAX_CASES_PER_SPLIT)
        accepted = _int("accepted", self.accepted, minimum=0, maximum=total)
        errors = _int("errors", self.errors, minimum=0, maximum=accepted)
        if not isinstance(self.risk, Interval):
            raise _fail("risk", "must be Interval")
        if not isinstance(self.coverage, Interval):
            raise _fail("coverage", "must be Interval")
        if status == "ERROR":
            full = Interval(0.0, 1.0)
            if total != 0 or self.risk != full or self.coverage != full:
                raise _fail("status", "ERROR requires zero counts and [0, 1] intervals")
        elif total == 0:
            raise _fail("total", "must be > 0 unless status is ERROR")
        elif status == "PASS" and accepted == 0:
            raise _fail("accepted", "must be > 0 when status is PASS")
        _set(self, "status", status)
        _set(self, "reasons", reasons)
        _set(self, "total", total)
        _set(self, "accepted", accepted)
        _set(self, "errors", errors)
        _set(
            self,
            "evidence_scope",
            _literal("evidence_scope", self.evidence_scope, _EVIDENCE_SCOPES),
        )
        _set(self, "lock_sha256", _sha256("lock_sha256", self.lock_sha256))


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    lock: PlanLock
    calibration_jsonl: str
    verification_jsonl: str
    records: tuple[DecisionRecord, ...]
    faults: tuple[FaultResult, ...]
    verdict: Verdict

    def __post_init__(self) -> None:
        if not isinstance(self.lock, PlanLock):
            raise _fail("lock", "must be PlanLock")
        _set(self, "calibration_jsonl", _str("calibration_jsonl", self.calibration_jsonl))
        _set(self, "verification_jsonl", _str("verification_jsonl", self.verification_jsonl))
        records = _records("records", self.records, DecisionRecord)
        faults = _records("faults", self.faults, FaultResult)
        if not isinstance(self.verdict, Verdict):
            raise _fail("verdict", "must be Verdict")
        expected_ids = tuple(ref.case_id for ref in self.lock.verification_inventory)
        if tuple(record.case_id for record in records) != expected_ids:
            raise _fail("records", "case ids must match lock.verification_inventory in order")
        expected_faults = tuple(spec.scenario_id for spec in self.lock.fault_inventory)
        if tuple(fault.scenario_id for fault in faults) != expected_faults:
            raise _fail("faults", "scenario ids must match lock.fault_inventory in order")
        if self.verdict.lock_sha256 != self.lock.sha256:
            raise _fail("verdict.lock_sha256", "must equal lock.sha256")
        if self.verdict.evidence_scope != self.lock.contract.evidence_scope:
            raise _fail("verdict.evidence_scope", "must equal lock.contract.evidence_scope")
        _set(self, "records", records)
        _set(self, "faults", faults)
