"""Reproducible plan locks and locked-input validation.

A :class:`PlanLock` binds the contract, the provider's actual model identity,
the raw bytes of both JSONL splits, their ordered canonical case inventories,
the full verification cases, the six frozen fault specifications and the
current implementation fingerprint, then seals itself with the canonical hash
of everything except its own ``sha256``.

Lock creation performs no model call, no threshold fitting and no dataset
repair. The six :data:`FAULT_INVENTORY` records are literal copies of the
plan/CONTRACTS.md section 4 table; this module never imports the fault
generator, providers, normalization, assessment or replay.

Incoming locks are never resealed: :func:`validate_lock` recomputes the seal
and compares it with the recorded value, and :func:`parse_lock` returns the
record exactly as decoded. Creation, validation and parsing agree on one wire
ceiling: the canonical lock document plus its single terminal LF must fit
``MAX_LOCK_BYTES`` (32 MiB), and :func:`parse_lock` counts every supplied byte.

Dataset-shape and limit violations (malformed rows, duplicate or leaked cases,
oversized documents) are :class:`SchemaError`; mismatches between a lock and
the evidence it claims to describe are :class:`IntegrityError`.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Final

from actseal.contract import parse_cases
from actseal.errors import IntegrityError, SchemaError
from actseal.records import (
    SCHEMA_VERSION,
    Case,
    CaseRef,
    Contract,
    FaultSpec,
    ModelIdentity,
    PlanLock,
)
from actseal.serialization import (
    MAX_JSON_BYTES,
    canonical_json,
    from_data,
    implementation_fingerprint,
    sha256_bytes,
    strict_json_loads,
    to_data,
)

__all__ = [
    "FAULT_INVENTORY",
    "MAX_LOCK_BYTES",
    "case_digest",
    "create_lock",
    "lock_digest",
    "parse_lock",
    "validate_inputs",
    "validate_lock",
]

MAX_LOCK_BYTES: Final = 32 * 1024 * 1024

FAULT_INVENTORY: Final[tuple[FaultSpec, ...]] = (
    FaultSpec(scenario_id="fault.timeout", kind="timeout", expected_action="ESCALATE"),
    FaultSpec(scenario_id="fault.rate_limit", kind="rate_limit", expected_action="ESCALATE"),
    FaultSpec(
        scenario_id="fault.malformed_response",
        kind="malformed_response",
        expected_action="ESCALATE",
    ),
    FaultSpec(
        scenario_id="fault.identity_mismatch",
        kind="identity_mismatch",
        expected_action="ESCALATE",
    ),
    FaultSpec(scenario_id="fault.unknown_choice", kind="unknown_choice", expected_action="DENY"),
    FaultSpec(scenario_id="fault.low_confidence", kind="low_confidence", expected_action="ABSTAIN"),
)

_UNSEALED: Final = "0" * 64


# --------------------------------------------------------------------------- #
# Digests
# --------------------------------------------------------------------------- #


def _raw_sha256(field: str, text: object) -> str:
    """Hash the exact UTF-8 bytes of a supplied JSONL text.

    The character count is a lower bound on the byte count, so clearly
    oversized text is rejected before any UTF-8 copy is allocated; the byte
    count is checked again after encoding.
    """
    if not isinstance(text, str):
        raise SchemaError(f"{field}: must be text")
    if len(text) > MAX_JSON_BYTES:
        raise SchemaError(f"{field}: document exceeds {MAX_JSON_BYTES} bytes")
    try:
        data = text.encode("utf-8")
    except UnicodeEncodeError:
        raise SchemaError(f"{field}: must be valid Unicode text") from None
    if len(data) > MAX_JSON_BYTES:
        raise SchemaError(f"{field}: document exceeds {MAX_JSON_BYTES} bytes")
    return sha256_bytes(data)


def case_digest(case: Case) -> str:
    """Canonical hash of one case; the inventory value for that case."""
    if not isinstance(case, Case):
        raise SchemaError("case: must be Case")
    return sha256_bytes(canonical_json(to_data(case)))


def lock_digest(lock: PlanLock) -> str:
    """Canonical hash of ``lock`` with only its own ``sha256`` field omitted."""
    if not isinstance(lock, PlanLock):
        raise SchemaError("lock: must be PlanLock")
    data = to_data(lock)
    del data["sha256"]
    return sha256_bytes(canonical_json(data))


def _inventory(cases: tuple[Case, ...]) -> tuple[CaseRef, ...]:
    return tuple(CaseRef(case_id=case.case_id, sha256=case_digest(case)) for case in cases)


def _check_wire_size(lock: PlanLock) -> None:
    """The canonical lock document plus its one terminal LF must fit the lock ceiling."""
    if len(canonical_json(to_data(lock))) + 1 > MAX_LOCK_BYTES:
        raise SchemaError(f"lock: canonical document exceeds {MAX_LOCK_BYTES} bytes")


def _check_disjoint_ids(
    calibration: tuple[CaseRef, ...], verification: tuple[CaseRef, ...]
) -> None:
    """Reject case IDs shared by the two locked inventories."""
    ids = {ref.case_id for ref in calibration}
    for index, ref in enumerate(verification):
        if ref.case_id in ids:
            raise SchemaError(
                f"verification_inventory[{index}].case_id: also present in calibration_inventory"
            )


# --------------------------------------------------------------------------- #
# Dataset checks shared by creation and validation
# --------------------------------------------------------------------------- #


def _parse_split(split: str, text: str, contract: Contract) -> tuple[Case, ...]:
    try:
        return parse_cases(text, contract.question)
    except SchemaError as exc:
        raise SchemaError(f"{split}: {exc}") from None


def _check_cross_split(calibration: tuple[Case, ...], verification: tuple[Case, ...]) -> None:
    """Reject literal leakage: shared IDs or byte-identical state texts across splits."""
    ids = {case.case_id for case in calibration}
    states = {case.state for case in calibration}
    for index, case in enumerate(verification):
        if case.case_id in ids:
            raise SchemaError(f"verification[{index}].case_id: also present in calibration")
        if case.state in states:
            raise SchemaError(
                f"verification[{index}].state: exact state text also present in calibration"
            )


def _check_unique_states(field: str, cases: tuple[Case, ...]) -> None:
    states: set[str] = set()
    for index, case in enumerate(cases):
        if case.state in states:
            raise IntegrityError(f"{field}[{index}].state: exact duplicate state text")
        states.add(case.state)


def _check_inventory(field: str, inventory: tuple[CaseRef, ...], cases: tuple[Case, ...]) -> None:
    if len(inventory) != len(cases):
        raise IntegrityError(f"{field}: case count does not match")
    for index, (ref, case) in enumerate(zip(inventory, cases, strict=True)):
        if ref.case_id != case.case_id:
            raise IntegrityError(f"{field}[{index}].case_id: does not match")
        if ref.sha256 != case_digest(case):
            raise IntegrityError(f"{field}[{index}].sha256: does not match the case")


# --------------------------------------------------------------------------- #
# Public interface
# --------------------------------------------------------------------------- #


def create_lock(
    contract: Contract,
    calibration_jsonl: str,
    verification_jsonl: str,
    model_identity: ModelIdentity,
) -> PlanLock:
    """Build and self-seal a lock over the supplied contract, identity and raw inputs."""
    if not isinstance(contract, Contract):
        raise SchemaError("contract: must be Contract")
    if not isinstance(model_identity, ModelIdentity):
        raise SchemaError("model_identity: must be ModelIdentity")
    calibration_sha256 = _raw_sha256("calibration_jsonl", calibration_jsonl)
    verification_sha256 = _raw_sha256("verification_jsonl", verification_jsonl)
    calibration = _parse_split("calibration", calibration_jsonl, contract)
    verification = _parse_split("verification", verification_jsonl, contract)
    _check_cross_split(calibration, verification)
    unsealed = PlanLock(
        schema_version=SCHEMA_VERSION,
        contract=contract,
        model_identity=model_identity,
        calibration_sha256=calibration_sha256,
        verification_sha256=verification_sha256,
        calibration_inventory=_inventory(calibration),
        verification_inventory=_inventory(verification),
        verification_cases=verification,
        fault_inventory=FAULT_INVENTORY,
        implementation_sha256=implementation_fingerprint(),
        sha256=_UNSEALED,
    )
    sealed = replace(unsealed, sha256=lock_digest(unsealed))
    _check_wire_size(sealed)
    return sealed


def validate_lock(lock: PlanLock) -> None:
    """Check wire size, self-seal, implementation identity, fault inventory and case coherence.

    Calibration state texts are not embedded, so cross-split *state* overlap can
    only be checked by :func:`validate_inputs`; cross-split *ID* overlap is
    checked here from the two inventories.
    """
    if not isinstance(lock, PlanLock):
        raise SchemaError("lock: must be PlanLock")
    _check_wire_size(lock)
    if lock_digest(lock) != lock.sha256:
        raise IntegrityError("sha256: self-seal does not match the lock contents")
    if lock.implementation_sha256 != implementation_fingerprint():
        raise IntegrityError("implementation_sha256: does not match the current implementation")
    if lock.fault_inventory != FAULT_INVENTORY:
        raise IntegrityError("fault_inventory: must equal the frozen six-scenario inventory")
    _check_disjoint_ids(lock.calibration_inventory, lock.verification_inventory)
    _check_inventory("verification_inventory", lock.verification_inventory, lock.verification_cases)
    _check_unique_states("verification_cases", lock.verification_cases)


def validate_inputs(
    lock: PlanLock,
    calibration_jsonl: str,
    verification_jsonl: str,
) -> tuple[Case, ...]:
    """Validate the lock and both raw inputs against it; return verification cases in lock order."""
    validate_lock(lock)
    if _raw_sha256("calibration_jsonl", calibration_jsonl) != lock.calibration_sha256:
        raise IntegrityError("calibration_sha256: raw calibration input does not match the lock")
    if _raw_sha256("verification_jsonl", verification_jsonl) != lock.verification_sha256:
        raise IntegrityError("verification_sha256: raw verification input does not match the lock")
    calibration = _parse_split("calibration", calibration_jsonl, lock.contract)
    verification = _parse_split("verification", verification_jsonl, lock.contract)
    _check_inventory("calibration_inventory", lock.calibration_inventory, calibration)
    _check_inventory("verification_inventory", lock.verification_inventory, verification)
    if verification != lock.verification_cases:
        raise IntegrityError("verification_cases: do not match the supplied verification input")
    _check_cross_split(calibration, verification)
    return lock.verification_cases


def parse_lock(text: str) -> PlanLock:
    """Strictly decode one lock document (at most 32 MiB) without validating its seal.

    The returned record carries the recorded ``sha256`` untouched; callers must
    run :func:`validate_lock` before trusting it.
    """
    if not isinstance(text, str):
        raise SchemaError("lock: must be text")
    if len(text) > MAX_LOCK_BYTES or (
        not text.isascii() and len(text.encode("utf-8", errors="surrogatepass")) > MAX_LOCK_BYTES
    ):
        raise SchemaError(f"lock: document exceeds {MAX_LOCK_BYTES} bytes")
    return from_data(PlanLock, strict_json_loads(text))
