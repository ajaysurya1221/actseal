"""Reproducible self-sealed locks, raw-input binding and tamper detection."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from actseal.contract import MAX_ROW_BYTES, parse_cases
from actseal.errors import IntegrityError, SchemaError
from actseal.locking import (
    FAULT_INVENTORY,
    MAX_LOCK_BYTES,
    case_digest,
    create_lock,
    lock_digest,
    parse_lock,
    validate_inputs,
    validate_lock,
)
from actseal.records import Case, CaseRef, FaultSpec, PlanLock
from actseal.serialization import (
    MAX_JSON_BYTES,
    canonical_json,
    implementation_fingerprint,
    to_data,
)
from conftest import HEX_A, make_contract, make_identity, make_lock

CALIBRATION = (
    '{"case_id":"c-001","state":"Refund missing.","expected_label":"billing"}\n'
    '{"case_id":"c-002","state":"App crashes.","expected_label":"technical"}\n'
)
VERIFICATION = (
    '{"case_id":"v-001","state":"Charged twice.","expected_label":"billing"}\n'
    '{"case_id":"v-002","state":"Login error.","expected_label":"technical"}\n'
    '{"case_id":"v-003","state":"Volume pricing?","expected_label":"sales"}\n'
)


def fresh_lock() -> PlanLock:
    return create_lock(make_contract(), CALIBRATION, VERIFICATION, make_identity())


def reseal(lock: PlanLock) -> PlanLock:
    """Test-only helper: a tampered lock with a fresh, self-consistent seal."""
    return replace(lock, sha256=lock_digest(lock))


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------- #
# Fault inventory
# --------------------------------------------------------------------------- #


def test_fault_inventory_is_the_literal_contracts_table_in_order() -> None:
    expected = (
        FaultSpec("fault.timeout", "timeout", "ESCALATE"),
        FaultSpec("fault.rate_limit", "rate_limit", "ESCALATE"),
        FaultSpec("fault.malformed_response", "malformed_response", "ESCALATE"),
        FaultSpec("fault.identity_mismatch", "identity_mismatch", "ESCALATE"),
        FaultSpec("fault.unknown_choice", "unknown_choice", "DENY"),
        FaultSpec("fault.low_confidence", "low_confidence", "ABSTAIN"),
    )
    assert expected == FAULT_INVENTORY
    assert len(FAULT_INVENTORY) == 6
    assert isinstance(FAULT_INVENTORY, tuple)
    assert all(spec.scenario_id == f"fault.{spec.kind}" for spec in FAULT_INVENTORY)
    with pytest.raises(AttributeError):
        FAULT_INVENTORY[0].kind = "x"  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# create_lock
# --------------------------------------------------------------------------- #


def test_identical_inputs_produce_identical_locks() -> None:
    first = fresh_lock()
    second = create_lock(make_contract(), CALIBRATION, VERIFICATION, make_identity())
    assert first == second
    assert first.sha256 == second.sha256
    assert canonical_json(to_data(first)) == canonical_json(to_data(second))


def test_lock_binds_raw_bytes_inventories_cases_faults_and_implementation() -> None:
    lock = fresh_lock()
    assert lock.schema_version == 2
    assert lock.replay_engine_version == "actseal-choice-v1"
    assert lock.contract == make_contract()
    assert lock.model_identity == make_identity()
    assert lock.calibration_sha256 == sha(CALIBRATION.encode())
    assert lock.verification_sha256 == sha(VERIFICATION.encode())
    assert lock.calibration_inventory == (
        CaseRef(
            "c-001",
            case_digest(Case("c-001", "Refund missing.", "billing")),
        ),
        CaseRef("c-002", case_digest(Case("c-002", "App crashes.", "technical"))),
    )
    assert tuple(ref.case_id for ref in lock.verification_inventory) == ("v-001", "v-002", "v-003")
    assert lock.verification_cases == parse_cases(VERIFICATION, make_contract().question)
    assert lock.fault_inventory == FAULT_INVENTORY
    assert lock.implementation_sha256 == implementation_fingerprint()
    assert lock.sha256 == lock_digest(lock)


def test_independently_specified_digests() -> None:
    """Hashes computed with hashlib/json only, not with actseal helpers."""
    lock = fresh_lock()
    # Raw input hash is over the exact UTF-8 bytes, newline included.
    assert lock.calibration_sha256 == hashlib.sha256(CALIBRATION.encode("utf-8")).hexdigest()
    # A canonical case: sorted keys, compact separators, UTF-8, no newline.
    canonical_case = b'{"case_id":"c-001","expected_label":"billing","state":"Refund missing."}'
    assert lock.calibration_inventory[0].sha256 == hashlib.sha256(canonical_case).hexdigest()
    # The seal: canonical JSON of the whole lock minus its own sha256 field.
    expected_wire: dict[str, Any] = {
        "schema_version": 2,
        "replay_engine_version": "actseal-choice-v1",
        "contract": {
            "schema_version": 1,
            "name": "support-triage",
            "question": {
                "question_id": "department",
                "instructions": "Select the department responsible for this ticket.",
                "options": [
                    {"label": "billing", "description": "Payments and refunds"},
                    {"label": "technical", "description": "Technical support"},
                    {"label": "sales", "description": "Purchasing questions"},
                ],
            },
            "policy": {
                "known_labels": ["billing", "technical", "sales"],
                "allowed_labels": ["billing", "technical"],
                "threshold": 0.9,
            },
            "limits": {"max_risk": 0.05, "min_coverage": 0.5, "alpha": 0.05},
            "evidence_scope": "demo",
            "population": "Authored support-routing demonstration; no deployment claim",
        },
        "model_identity": {
            "provider": "fixture",
            "model": "recorded-choice-v1",
            "revision": HEX_A,
            "artifact_hashes": {"responses": HEX_A},
            "adapter_version": "1",
            "normalizer_version": "1",
            "runtime": {"os": "darwin", "python": "3.12"},
        },
        "calibration_sha256": hashlib.sha256(CALIBRATION.encode()).hexdigest(),
        "verification_sha256": hashlib.sha256(VERIFICATION.encode()).hexdigest(),
        "calibration_inventory": [
            {"case_id": "c-001", "sha256": hashlib.sha256(canonical_case).hexdigest()},
            {
                "case_id": "c-002",
                "sha256": hashlib.sha256(
                    b'{"case_id":"c-002","expected_label":"technical","state":"App crashes."}'
                ).hexdigest(),
            },
        ],
        "verification_inventory": [
            {
                "case_id": "v-001",
                "sha256": hashlib.sha256(
                    b'{"case_id":"v-001","expected_label":"billing","state":"Charged twice."}'
                ).hexdigest(),
            },
            {
                "case_id": "v-002",
                "sha256": hashlib.sha256(
                    b'{"case_id":"v-002","expected_label":"technical","state":"Login error."}'
                ).hexdigest(),
            },
            {
                "case_id": "v-003",
                "sha256": hashlib.sha256(
                    b'{"case_id":"v-003","expected_label":"sales","state":"Volume pricing?"}'
                ).hexdigest(),
            },
        ],
        "verification_cases": [
            {"case_id": "v-001", "state": "Charged twice.", "expected_label": "billing"},
            {
                "case_id": "v-002",
                "state": "Login error.",
                "expected_label": "technical",
            },
            {
                "case_id": "v-003",
                "state": "Volume pricing?",
                "expected_label": "sales",
            },
        ],
        "fault_inventory": [
            {"scenario_id": "fault.timeout", "kind": "timeout", "expected_action": "ESCALATE"},
            {
                "scenario_id": "fault.rate_limit",
                "kind": "rate_limit",
                "expected_action": "ESCALATE",
            },
            {
                "scenario_id": "fault.malformed_response",
                "kind": "malformed_response",
                "expected_action": "ESCALATE",
            },
            {
                "scenario_id": "fault.identity_mismatch",
                "kind": "identity_mismatch",
                "expected_action": "ESCALATE",
            },
            {
                "scenario_id": "fault.unknown_choice",
                "kind": "unknown_choice",
                "expected_action": "DENY",
            },
            {
                "scenario_id": "fault.low_confidence",
                "kind": "low_confidence",
                "expected_action": "ABSTAIN",
            },
        ],
        "implementation_sha256": lock.implementation_sha256,
    }
    seal_bytes = json.dumps(
        expected_wire, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    assert lock.sha256 == hashlib.sha256(seal_bytes).hexdigest()
    expected_wire["sha256"] = lock.sha256
    assert to_data(lock) == expected_wire


def test_case_digest_distinguishes_every_field_and_ignores_raw_layout() -> None:
    base = Case("v-001", "Charged twice.", "billing")
    assert case_digest(base) == case_digest(Case("v-001", "Charged twice.", "billing"))
    assert case_digest(base) != case_digest(Case("v-002", "Charged twice.", "billing"))
    assert case_digest(base) != case_digest(Case("v-001", "Charged twice this month", "billing"))
    assert case_digest(base) != case_digest(Case("v-001", "Charged twice.", "sales"))
    with pytest.raises(SchemaError, match="case: must be Case"):
        case_digest({"case_id": "v-001"})  # type: ignore[arg-type]


def test_create_lock_rejects_wrong_argument_types() -> None:
    with pytest.raises(SchemaError, match="contract: must be Contract"):
        create_lock(to_data(make_contract()), CALIBRATION, VERIFICATION, make_identity())  # type: ignore[arg-type]
    with pytest.raises(SchemaError, match="model_identity: must be ModelIdentity"):
        create_lock(make_contract(), CALIBRATION, VERIFICATION, "fixture")  # type: ignore[arg-type]
    with pytest.raises(SchemaError, match="calibration_jsonl: must be text"):
        create_lock(make_contract(), CALIBRATION.encode(), VERIFICATION, make_identity())  # type: ignore[arg-type]
    with pytest.raises(SchemaError, match="verification_jsonl: must be text"):
        create_lock(make_contract(), CALIBRATION, None, make_identity())  # type: ignore[arg-type]


def test_create_lock_rejects_unencodable_text_before_parsing() -> None:
    with pytest.raises(SchemaError, match="verification_jsonl: must be valid Unicode text"):
        create_lock(make_contract(), CALIBRATION, VERIFICATION + "\ud800", make_identity())


@pytest.mark.parametrize(
    ("calibration", "verification", "fragment"),
    [
        ("", VERIFICATION, "calibration: cases: must contain at least one record"),
        (CALIBRATION, "", "verification: cases: must contain at least one record"),
        (CALIBRATION, VERIFICATION + "\n", r"verification: cases\[3\]: blank record"),
        (
            CALIBRATION,
            VERIFICATION.replace('"sales"', '"legal"'),
            r"verification: cases\[2\].expected_label: must be a known label",
        ),
        (
            CALIBRATION,
            VERIFICATION + '{"case_id":"c-001","state":"Fresh text.","expected_label":"billing"}\n',
            r"verification\[3\].case_id: also present in calibration",
        ),
        (
            CALIBRATION,
            VERIFICATION + '{"case_id":"v-004","state":"App crashes.","expected_label":"sales"}\n',
            r"verification\[3\].state: exact state text also present in calibration",
        ),
        (
            CALIBRATION
            + '{"case_id":"c-003","state":"Charged twice.","expected_label":"billing"}\n',
            VERIFICATION,
            r"verification\[0\].state: exact state text also present in calibration",
        ),
        (
            CALIBRATION + CALIBRATION.splitlines(keepends=True)[0],
            VERIFICATION,
            r"calibration: cases\[2\].case_id: duplicate case id",
        ),
    ],
    ids=[
        "empty calibration",
        "empty verification",
        "trailing blank verification row",
        "foreign label",
        "id leaked across splits",
        "state leaked into verification",
        "state leaked into calibration",
        "duplicate id within calibration",
    ],
)
def test_create_lock_rejects_malformed_or_leaking_datasets(
    calibration: str, verification: str, fragment: str
) -> None:
    with pytest.raises(SchemaError, match=fragment):
        create_lock(make_contract(), calibration, verification, make_identity())


def test_create_lock_does_not_treat_near_duplicates_as_leakage() -> None:
    verification = VERIFICATION + (
        '{"case_id":"v-004","state":"app crashes on launch.","expected_label":"technical"}\n'
        '{"case_id":"v-005","state":"App crashes. ","expected_label":"technical"}\n'
    )
    lock = create_lock(make_contract(), CALIBRATION, verification, make_identity())
    assert len(lock.verification_cases) == 5
    assert validate_inputs(lock, CALIBRATION, verification) == lock.verification_cases


def test_threshold_is_taken_from_the_contract_not_fitted() -> None:
    """Different verification labels never change the locked threshold or policy."""
    contract = make_contract()
    flipped = VERIFICATION.replace('"billing"', '"technical"', 1)
    lock_a = create_lock(contract, CALIBRATION, VERIFICATION, make_identity())
    lock_b = create_lock(contract, CALIBRATION, flipped, make_identity())
    assert lock_a.contract.policy == lock_b.contract.policy == contract.policy
    assert lock_a.contract.policy.threshold == 0.9
    assert lock_a.sha256 != lock_b.sha256


# --------------------------------------------------------------------------- #
# validate_lock
# --------------------------------------------------------------------------- #


def test_fresh_lock_validates_and_is_not_resealed() -> None:
    lock = fresh_lock()
    before = to_data(lock)
    validate_lock(lock)
    assert to_data(lock) == before


def test_validate_lock_rejects_non_locks() -> None:
    with pytest.raises(SchemaError, match="lock: must be PlanLock"):
        validate_lock(to_data(fresh_lock()))  # type: ignore[arg-type]
    with pytest.raises(SchemaError, match="lock: must be PlanLock"):
        lock_digest(None)  # type: ignore[arg-type]


def test_conftest_sample_lock_has_a_syntactically_valid_but_false_seal() -> None:
    with pytest.raises(IntegrityError, match="sha256: self-seal does not match"):
        validate_lock(make_lock())


def _swap_cases(lock: PlanLock) -> PlanLock:
    cases = lock.verification_cases
    inventory = lock.verification_inventory
    return replace(
        lock,
        verification_cases=(cases[1], cases[0], cases[2]),
        verification_inventory=(inventory[1], inventory[0], inventory[2]),
    )


def _relabel_case(lock: PlanLock) -> PlanLock:
    cases = list(lock.verification_cases)
    cases[0] = replace(cases[0], expected_label="sales")
    return replace(lock, verification_cases=tuple(cases))


def _restate_case(lock: PlanLock) -> PlanLock:
    cases = list(lock.verification_cases)
    cases[2] = replace(cases[2], state="Volume pricing? ")
    return replace(lock, verification_cases=tuple(cases))


def _relabel_case_and_inventory(lock: PlanLock) -> PlanLock:
    """Consistent case/inventory change: raw bytes can no longer agree."""
    cases = list(lock.verification_cases)
    cases[0] = replace(cases[0], expected_label="sales")
    inventory = list(lock.verification_inventory)
    inventory[0] = CaseRef("v-001", case_digest(cases[0]))
    return replace(lock, verification_cases=tuple(cases), verification_inventory=tuple(inventory))


def _duplicate_state(lock: PlanLock) -> PlanLock:
    cases = list(lock.verification_cases)
    cases[1] = replace(cases[1], state=cases[0].state)
    inventory = list(lock.verification_inventory)
    inventory[1] = CaseRef("v-002", case_digest(cases[1]))
    return replace(lock, verification_cases=tuple(cases), verification_inventory=tuple(inventory))


def _alter_inventory_hash(lock: PlanLock) -> PlanLock:
    inventory = list(lock.verification_inventory)
    inventory[1] = CaseRef("v-002", "0" * 64)
    return replace(lock, verification_inventory=tuple(inventory))


def _alter_calibration_hash(lock: PlanLock) -> PlanLock:
    inventory = list(lock.calibration_inventory)
    inventory[0] = CaseRef("c-001", "0" * 64)
    return replace(lock, calibration_inventory=tuple(inventory))


def _drop_fault(lock: PlanLock) -> PlanLock:
    return replace(lock, fault_inventory=lock.fault_inventory[:-1])


def _reorder_faults(lock: PlanLock) -> PlanLock:
    faults = lock.fault_inventory
    return replace(lock, fault_inventory=(faults[1], faults[0], *faults[2:]))


def _relax_fault(lock: PlanLock) -> PlanLock:
    faults = list(lock.fault_inventory)
    faults[5] = FaultSpec("fault.low_confidence", "low_confidence", "ACT")
    return replace(lock, fault_inventory=tuple(faults))


def _rename_fault(lock: PlanLock) -> PlanLock:
    faults = list(lock.fault_inventory)
    faults[0] = FaultSpec("fault.timeout", "provider_error", "ESCALATE")
    return replace(lock, fault_inventory=tuple(faults))


def _extra_fault(lock: PlanLock) -> PlanLock:
    extra = FaultSpec("fault.unavailable", "unavailable", "ESCALATE")
    return replace(lock, fault_inventory=(*lock.fault_inventory, extra))


def _empty_faults(lock: PlanLock) -> PlanLock:
    return replace(lock, fault_inventory=())


def _other_implementation(lock: PlanLock) -> PlanLock:
    return replace(lock, implementation_sha256="f" * 64)


RESEALED_TAMPERING = [
    (_relabel_case, "verification_inventory[0].sha256: does not match the case"),
    (_restate_case, "verification_inventory[2].sha256: does not match the case"),
    (_duplicate_state, "verification_cases[1].state: exact duplicate state text"),
    (_alter_inventory_hash, "verification_inventory[1].sha256: does not match the case"),
    (_drop_fault, "fault_inventory: must equal the frozen six-scenario inventory"),
    (_reorder_faults, "fault_inventory: must equal the frozen six-scenario inventory"),
    (_relax_fault, "fault_inventory: must equal the frozen six-scenario inventory"),
    (_rename_fault, "fault_inventory: must equal the frozen six-scenario inventory"),
    (_extra_fault, "fault_inventory: must equal the frozen six-scenario inventory"),
    (_empty_faults, "fault_inventory: must equal the frozen six-scenario inventory"),
    (_other_implementation, "implementation_sha256: does not match the current implementation"),
]


@pytest.mark.parametrize(
    ("tamper", "fragment"), RESEALED_TAMPERING, ids=[t.__name__ for t, _ in RESEALED_TAMPERING]
)
def test_resealed_tampering_cannot_validate(tamper: Any, fragment: str) -> None:
    tampered = reseal(tamper(fresh_lock()))
    assert lock_digest(tampered) == tampered.sha256  # the seal itself is consistent
    with pytest.raises(IntegrityError, match=_escape(fragment)):
        validate_lock(tampered)


def _escape(fragment: str) -> str:
    return re.escape(fragment)


UNSEALED_TAMPERING = [
    *(tamper for tamper, _ in RESEALED_TAMPERING),
    _swap_cases,
    _alter_calibration_hash,
    _relabel_case_and_inventory,
    lambda lock: replace(lock, calibration_sha256="1" * 64),
    lambda lock: replace(lock, verification_sha256="2" * 64),
    lambda lock: replace(lock, model_identity=replace(lock.model_identity, revision="other")),
    lambda lock: replace(lock, model_identity=replace(lock.model_identity, model="other")),
    lambda lock: replace(
        lock, contract=replace(lock.contract, policy=replace(lock.contract.policy, threshold=0.5))
    ),
    lambda lock: replace(
        lock,
        contract=replace(
            lock.contract, policy=replace(lock.contract.policy, allowed_labels=("billing",))
        ),
    ),
    lambda lock: replace(lock, contract=replace(lock.contract, evidence_scope="iid")),
    lambda lock: replace(lock, sha256="a" * 64),
]


@pytest.mark.parametrize("tamper", UNSEALED_TAMPERING)
def test_any_field_change_without_resealing_breaks_the_seal(tamper: Any) -> None:
    original = fresh_lock()
    tampered = tamper(original)
    assert tampered != original
    with pytest.raises(IntegrityError, match="sha256: self-seal does not match"):
        validate_lock(tampered)


def test_resealed_identity_or_policy_change_is_a_different_lock() -> None:
    """Resealing is a test-only act; the product never does it, but the result is detectable."""
    original = fresh_lock()
    changed = reseal(
        replace(original, model_identity=replace(original.model_identity, revision="r2"))
    )
    validate_lock(changed)
    assert changed.sha256 != original.sha256
    assert validate_inputs(changed, CALIBRATION, VERIFICATION) == original.verification_cases


# --------------------------------------------------------------------------- #
# validate_inputs
# --------------------------------------------------------------------------- #


def test_validate_inputs_returns_verification_cases_in_lock_order() -> None:
    lock = fresh_lock()
    cases = validate_inputs(lock, CALIBRATION, VERIFICATION)
    assert cases == lock.verification_cases
    assert isinstance(cases, tuple)
    assert tuple(case.case_id for case in cases) == ("v-001", "v-002", "v-003")


def test_validate_inputs_validates_the_lock_first() -> None:
    with pytest.raises(IntegrityError, match="sha256: self-seal"):
        validate_inputs(make_lock(), CALIBRATION, VERIFICATION)
    tampered = reseal(_drop_fault(fresh_lock()))
    with pytest.raises(IntegrityError, match="fault_inventory"):
        validate_inputs(tampered, CALIBRATION, VERIFICATION)


REFORMATTED_VERIFICATION = (
    '{"state": "Charged twice.", "expected_label": "billing", "case_id": "v-001"}\n'
    '{"case_id":"v-002","state":"Login error.","expected_label":"technical"}\n'
    '  {"case_id":"v-003","state":"Volume pricing?","expected_label":"sales"}\n'
)


@pytest.mark.parametrize(
    "variant",
    [
        REFORMATTED_VERIFICATION,
        VERIFICATION.replace("\n", "\r\n"),
        VERIFICATION.rstrip("\n"),
        VERIFICATION.replace('"v-002"', '"v-002" '),
        VERIFICATION.replace("Charged", "Charg\\u0065d"),
    ],
    ids=["reordered keys", "crlf", "no final lf", "padding", "json escape"],
)
def test_raw_bytes_are_bound_even_when_canonical_cases_agree(variant: str) -> None:
    lock = fresh_lock()
    question = lock.contract.question
    assert parse_cases(variant, question) == lock.verification_cases
    assert variant.encode() != VERIFICATION.encode()
    with pytest.raises(IntegrityError, match="verification_sha256: raw verification input"):
        validate_inputs(lock, CALIBRATION, variant)
    equivalent = create_lock(make_contract(), CALIBRATION, variant, make_identity())
    assert equivalent.verification_inventory == lock.verification_inventory
    assert equivalent.verification_cases == lock.verification_cases
    assert equivalent.verification_sha256 != lock.verification_sha256
    assert equivalent.sha256 != lock.sha256


def _lines(text: str) -> list[str]:
    return text.splitlines(keepends=True)


@pytest.mark.parametrize(
    ("calibration", "verification", "fragment"),
    [
        (CALIBRATION, VERIFICATION.replace('"billing"', '"sales"', 1), "verification_sha256"),
        (CALIBRATION, "".join(reversed(_lines(VERIFICATION))), "verification_sha256"),
        (CALIBRATION, "".join(_lines(VERIFICATION)[:2]), "verification_sha256"),
        (CALIBRATION, VERIFICATION + CALIBRATION, "verification_sha256"),
        (CALIBRATION, VERIFICATION.replace("twice", "thrice"), "verification_sha256"),
        (CALIBRATION, VERIFICATION.replace("v-001", "v-01"), "verification_sha256"),
        (CALIBRATION.replace('"billing"', '"sales"', 1), VERIFICATION, "calibration_sha256"),
        ("".join(reversed(_lines(CALIBRATION))), VERIFICATION, "calibration_sha256"),
        (CALIBRATION + VERIFICATION, VERIFICATION, "calibration_sha256"),
        (VERIFICATION, CALIBRATION, "calibration_sha256"),
        (CALIBRATION, CALIBRATION, "verification_sha256"),
        ("", VERIFICATION, "calibration_sha256"),
        (CALIBRATION, "", "verification_sha256"),
        (CALIBRATION, "﻿" + VERIFICATION, "verification_sha256"),
    ],
    ids=[
        "relabeled verification",
        "reordered verification",
        "dropped verification case",
        "appended cases",
        "edited state",
        "edited id",
        "relabeled calibration",
        "reordered calibration",
        "appended calibration",
        "swapped splits",
        "calibration used twice",
        "empty calibration",
        "empty verification",
        "bom",
    ],
)
def test_mutated_inputs_cannot_validate(calibration: str, verification: str, fragment: str) -> None:
    lock = fresh_lock()
    with pytest.raises(IntegrityError, match=fragment):
        validate_inputs(lock, calibration, verification)


def test_validate_inputs_rejects_non_text_inputs() -> None:
    lock = fresh_lock()
    with pytest.raises(SchemaError, match="calibration_jsonl: must be text"):
        validate_inputs(lock, CALIBRATION.encode(), VERIFICATION)  # type: ignore[arg-type]
    with pytest.raises(SchemaError, match="verification_jsonl: must be text"):
        validate_inputs(lock, CALIBRATION, None)  # type: ignore[arg-type]


def test_hash_matching_inputs_with_tampered_inventory_or_cases_cannot_validate() -> None:
    """Raw hashes agree but the locked inventories/cases were edited and resealed."""
    lock = reseal(_alter_calibration_hash(fresh_lock()))
    validate_lock(lock)  # calibration inventory cannot be checked without the raw input
    with pytest.raises(IntegrityError, match=r"calibration_inventory\[0\].sha256: does not match"):
        validate_inputs(lock, CALIBRATION, VERIFICATION)
    lock = reseal(_relabel_case_and_inventory(fresh_lock()))
    validate_lock(lock)  # internally coherent, but the raw bytes say "billing"
    with pytest.raises(IntegrityError, match=r"verification_inventory\[0\].sha256: does not match"):
        validate_inputs(lock, CALIBRATION, VERIFICATION)
    lock = reseal(_swap_cases(fresh_lock()))
    validate_lock(lock)  # a consistently reordered lock passes alone
    with pytest.raises(
        IntegrityError, match=r"verification_inventory\[0\].case_id: does not match"
    ):
        validate_inputs(lock, CALIBRATION, VERIFICATION)
    relabeled = VERIFICATION.replace('"billing"', '"sales"', 1)
    consistent = create_lock(make_contract(), CALIBRATION, relabeled, make_identity())
    assert consistent.verification_cases[0].expected_label == "sales"
    assert validate_inputs(consistent, CALIBRATION, relabeled) == consistent.verification_cases


def _lock_over_calibration(calibration: str) -> PlanLock:
    """A lock sealed over ``calibration`` by bypassing create_lock's leakage checks."""
    cases = parse_cases(calibration, make_contract().question)
    return reseal(
        replace(
            fresh_lock(),
            calibration_sha256=sha(calibration.encode()),
            calibration_inventory=tuple(CaseRef(c.case_id, case_digest(c)) for c in cases),
        )
    )


def test_validate_inputs_rechecks_cross_split_state_leakage() -> None:
    """A leaked state under a fresh ID is invisible to validate_lock but caught with inputs."""
    leaked = CALIBRATION + '{"case_id":"c-003","state":"Charged twice.","expected_label":"sales"}\n'
    lock = _lock_over_calibration(leaked)
    validate_lock(lock)  # calibration states are not embedded; only inventories are
    with pytest.raises(SchemaError, match=r"verification\[0\].state: exact state text also"):
        validate_inputs(lock, leaked, VERIFICATION)


def test_validate_lock_rejects_cross_split_ids_from_the_inventories_alone() -> None:
    """REVIEW T10-01 finding 3: a correctly resealed lock with intersecting IDs."""
    base = fresh_lock()
    inventory = list(base.calibration_inventory)
    inventory[0] = CaseRef("v-001", inventory[0].sha256)
    overlapping = reseal(replace(base, calibration_inventory=tuple(inventory)))
    assert lock_digest(overlapping) == overlapping.sha256
    assert overlapping.implementation_sha256 == implementation_fingerprint()
    with pytest.raises(
        SchemaError, match=r"verification_inventory\[0\].case_id: also present in calibration"
    ):
        validate_lock(overlapping)
    with pytest.raises(SchemaError, match=r"verification_inventory\[0\].case_id"):
        validate_inputs(overlapping, CALIBRATION, VERIFICATION)
    # The same overlap built from real leaking data is rejected before inputs are seen.
    leaked = CALIBRATION + VERIFICATION.splitlines(keepends=True)[2]
    with pytest.raises(SchemaError, match=r"verification_inventory\[2\].case_id: also present"):
        validate_lock(_lock_over_calibration(leaked))
    with pytest.raises(SchemaError, match=r"verification\[2\].case_id: also present"):
        create_lock(make_contract(), leaked, VERIFICATION, make_identity())


def test_validate_lock_accepts_disjoint_inventories_with_shared_hashes() -> None:
    """Equal canonical hashes under different IDs are not an ID intersection."""
    base = fresh_lock()
    inventory = list(base.calibration_inventory)
    inventory[0] = CaseRef("c-001", base.verification_inventory[0].sha256)
    validate_lock(reseal(replace(base, calibration_inventory=tuple(inventory))))


# --------------------------------------------------------------------------- #
# parse_lock
# --------------------------------------------------------------------------- #


def test_parse_lock_round_trips_canonical_json_with_or_without_terminal_lf() -> None:
    lock = fresh_lock()
    wire = canonical_json(to_data(lock)).decode("utf-8")
    assert parse_lock(wire) == lock
    assert parse_lock(wire + "\n") == lock
    validate_lock(parse_lock(wire + "\n"))


def test_parse_lock_keeps_the_recorded_seal_and_never_reseals() -> None:
    lock = fresh_lock()
    data = to_data(lock)
    data["sha256"] = "0" * 64
    parsed = parse_lock(canonical_json(data).decode("utf-8"))
    assert parsed.sha256 == "0" * 64
    with pytest.raises(IntegrityError, match="sha256: self-seal does not match"):
        validate_lock(parsed)
    data = to_data(lock)
    data["implementation_sha256"] = "e" * 64
    parsed = parse_lock(canonical_json(data).decode("utf-8"))
    assert parsed.implementation_sha256 == "e" * 64
    with pytest.raises(IntegrityError, match="sha256: self-seal does not match"):
        validate_lock(parsed)


@pytest.mark.parametrize(
    ("mutate", "fragment"),
    [
        (lambda d: d.update(extra=1), "unknown field"),
        (lambda d: d.pop("fault_inventory"), "missing fields fault_inventory"),
        (lambda d: d.update(schema_version=3), "unsupported schema version"),
        # Version 1 with the v1.0 field still present is not a real 0.1.0 document.
        (lambda d: d.update(schema_version=1), "unsupported schema version"),
        (lambda d: d.update(schema_version=True), "expected integer"),
        (lambda d: d.update(replay_engine_version=""), "replay_engine_version: must be nonempty"),
        (lambda d: d.pop("replay_engine_version"), "missing fields replay_engine_version"),
        (lambda d: d.update(sha256="xyz"), "lowercase 64-character SHA256 hex"),
        (lambda d: d.update(verification_cases=[]), "ids must match verification_inventory"),
        (lambda d: d.update(calibration_inventory=[]), "must contain 1..10000 cases"),
        (lambda d: d["contract"]["policy"].update(threshold=True), "expected number"),
        (lambda d: d["contract"]["policy"].update(known_labels=["x", "y"]), "known_labels"),
        (lambda d: d["verification_cases"][0].update(expected_label="legal"), "known label"),
        (lambda d: d["fault_inventory"][0].update(expected_action="SKIP"), "unsupported value"),
        (lambda d: d["model_identity"].update(provider="unsupported"), "unsupported value"),
    ],
)
def test_parse_lock_rejects_malformed_documents(mutate: Any, fragment: str) -> None:
    data = to_data(fresh_lock())
    mutate(data)
    with pytest.raises(SchemaError, match=fragment):
        parse_lock(json.dumps(data, ensure_ascii=False))


@pytest.mark.parametrize("text", ["", "[]", "null", "{", '{"schema_version": 1}', "{} {}"])
def test_parse_lock_rejects_non_lock_documents(text: str) -> None:
    with pytest.raises(SchemaError):
        parse_lock(text)


def test_parse_lock_rejects_duplicate_keys_and_nonfinite_numbers() -> None:
    wire = canonical_json(to_data(fresh_lock())).decode("utf-8")
    with pytest.raises(SchemaError, match="duplicate object key"):
        parse_lock(wire[:-1] + ',"schema_version":2}')
    with pytest.raises(SchemaError, match="nonfinite"):
        parse_lock(wire.replace('"threshold":0.9', '"threshold":NaN'))


def wire_size(lock: PlanLock) -> int:
    """Canonical lock bytes plus the one terminal LF that wire files add."""
    return (
        len(
            json.dumps(
                to_data(lock), sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode()
        )
        + 1
    )


FULL_ROWS = 31


def _full_row(index: int) -> str:
    """A verification row of exactly MAX_ROW_BYTES bytes with a unique ASCII state."""
    skeleton = f'{{"case_id":"big-{index:02d}","state":"","expected_label":"billing"}}'
    fill = MAX_ROW_BYTES - len(skeleton.encode()) - 2
    state = f"{index:02d}" + "s" * fill
    return f'{{"case_id":"big-{index:02d}","state":"{state}","expected_label":"billing"}}'


def _big_verification(final_state: str) -> str:
    rows = [_full_row(index) for index in range(FULL_ROWS)]
    rows.append(
        json.dumps(
            {"case_id": "big-last", "state": final_state, "expected_label": "sales"},
            ensure_ascii=False,
        )
    )
    return "\n".join(rows) + "\n"


def _lock_with(final_state: str) -> PlanLock:
    return create_lock(
        make_contract(), CALIBRATION, _big_verification(final_state), make_identity()
    )


@pytest.mark.parametrize("multibyte", [False, True], ids=["ascii", "multibyte"])
def test_lock_wire_ceiling_is_32_mib_including_the_terminal_lf(multibyte: bool) -> None:
    """REVIEW T10-01 finding 2: creation, validation and parsing agree on the ceiling."""
    assert len(_full_row(0).encode()) == MAX_ROW_BYTES
    probe = _lock_with("p")
    slack = MAX_LOCK_BYTES - wire_size(probe)
    assert slack > 0
    assert slack + 100 < MAX_ROW_BYTES  # the adjustable final row stays under the row ceiling
    filler = ("é" * (slack // 2) + "a" * (slack % 2)) if multibyte else "a" * slack
    assert len(("p" + filler).encode()) == 1 + slack
    exact = _lock_with("p" + filler)
    assert wire_size(exact) == MAX_LOCK_BYTES
    assert len(exact.verification_cases) == FULL_ROWS + 1
    if multibyte:
        assert len("p" + filler) < 1 + slack  # fewer characters than bytes
    validate_lock(exact)
    wire = canonical_json(to_data(exact)).decode("utf-8") + "\n"
    assert len(wire.encode()) == MAX_LOCK_BYTES
    assert parse_lock(wire) == exact
    with pytest.raises(SchemaError, match=f"lock: canonical document exceeds {MAX_LOCK_BYTES}"):
        _lock_with("p" + filler + "a")
    # A lock that bypassed create_lock and sits one byte over is rejected on validation,
    # before any seal or fingerprint comparison.
    cases = list(exact.verification_cases)
    cases[-1] = replace(cases[-1], state=cases[-1].state + "a")
    inventory = list(exact.verification_inventory)
    inventory[-1] = CaseRef("big-last", case_digest(cases[-1]))
    oversized = reseal(
        replace(exact, verification_cases=tuple(cases), verification_inventory=tuple(inventory))
    )
    assert wire_size(oversized) == MAX_LOCK_BYTES + 1
    with pytest.raises(SchemaError, match="lock: canonical document exceeds"):
        validate_lock(oversized)
    with pytest.raises(SchemaError, match="lock: canonical document exceeds"):
        validate_inputs(oversized, CALIBRATION, _big_verification("p" + filler + "a"))
    with pytest.raises(SchemaError, match="lock: document exceeds"):
        parse_lock(canonical_json(to_data(oversized)).decode("utf-8") + "\n")


def test_raw_hash_rejects_oversized_text_before_encoding() -> None:
    """Character count is a cheap lower bound on the byte count."""
    with pytest.raises(SchemaError, match="calibration_jsonl: document exceeds"):
        create_lock(make_contract(), " " * (MAX_JSON_BYTES + 1), VERIFICATION, make_identity())
    with pytest.raises(SchemaError, match="verification_jsonl: document exceeds"):
        validate_inputs(fresh_lock(), CALIBRATION, "é" * (MAX_JSON_BYTES // 2 + 1))


def test_parse_lock_limit_is_32_mib() -> None:
    assert MAX_LOCK_BYTES == 32 * 1024 * 1024
    wire = canonical_json(to_data(fresh_lock())).decode("utf-8")
    padded = wire + " " * (MAX_LOCK_BYTES - len(wire.encode()))
    assert len(padded.encode()) == MAX_LOCK_BYTES
    assert parse_lock(padded) == fresh_lock()
    with pytest.raises(SchemaError, match=f"lock: document exceeds {MAX_LOCK_BYTES} bytes"):
        parse_lock(padded + " ")
    with pytest.raises(SchemaError, match="lock: document exceeds"):
        parse_lock("é" * (MAX_LOCK_BYTES // 2 + 1))
    with pytest.raises(SchemaError, match="lock: must be text"):
        parse_lock(wire.encode())  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# Import hygiene
# --------------------------------------------------------------------------- #

FORBIDDEN_MODULES = (
    "actseal.faults",
    "actseal.providers",
    "actseal.normalization",
    "actseal.assessment",
    "actseal.replay",
    "laya",
    "torch",
    "transformers",
    "huggingface_hub",
    "safetensors",
    "numpy",
    "tomllib_extra",
)


def test_t10_modules_import_only_stdlib_and_t00() -> None:
    package = Path(__file__).resolve().parents[2] / "src" / "actseal"
    allowed = {
        "actseal.compatibility",  # v1.0 pure replay-compatibility rules used by validate_lock
        "actseal.contract",
        "actseal.errors",
        "actseal.records",
        "actseal.serialization",
    }
    for name in ("compatibility", "contract", "locking", "policy"):
        source = (package / f"{name}.py").read_text(encoding="utf-8")
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("from actseal"):
                module = stripped.split()[1]
                assert module in allowed, (name, module)
            assert not stripped.startswith("import actseal"), (name, line)
    script = (
        "import sys\n"
        "import actseal.compatibility, actseal.contract, actseal.locking, actseal.policy\n"
        f"loaded = [m for m in {FORBIDDEN_MODULES!r} if m in sys.modules]\n"
        "assert not loaded, loaded\n"
        "print('ok')\n"
    )
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", script], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"
