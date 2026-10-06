"""Shared test configuration: offline guard and canonical sample records.

Unit tests never touch the network. An autouse fixture replaces socket
construction with a failure unless the test is explicitly marked
``integration`` or ``packaging``. Sample builders construct one valid instance
of every public record so tests can parameterize over the whole schema.
"""

from __future__ import annotations

import socket
from typing import Any

import pytest

from actseal.records import (
    CapturedOutcome,
    Case,
    CaseRef,
    ChoiceAnswer,
    ChoiceQuestion,
    Contract,
    DecisionRecord,
    DecisionRequest,
    EvidenceBundle,
    FaultResult,
    FaultSpec,
    GateLimits,
    Interval,
    LockedPolicy,
    ModelIdentity,
    Option,
    PlanLock,
    PolicyDecision,
    ProviderFailure,
    Verdict,
)

_NETWORK_MARKERS = ("integration", "packaging")


class _NetworkBlockedError(RuntimeError):
    """Raised when a unit test tries to open a socket."""


def _blocked_socket(*_args: object, **_kwargs: object) -> socket.socket:
    msg = "network access is disabled in unit tests"
    raise _NetworkBlockedError(msg)


@pytest.fixture(autouse=True)
def _offline(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Block socket creation for every test that is not marked integration/packaging."""
    if any(request.node.get_closest_marker(name) for name in _NETWORK_MARKERS):
        return
    monkeypatch.setattr(socket, "socket", _blocked_socket)
    monkeypatch.setattr(socket, "create_connection", _blocked_socket)
    monkeypatch.setattr(socket, "socketpair", _blocked_socket)
    monkeypatch.setattr(socket, "getaddrinfo", _blocked_socket)


# --------------------------------------------------------------------------- #
# Sample records
# --------------------------------------------------------------------------- #

HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64
HEX_D = "d" * 64
HEX_E = "e" * 64
HEX_F = "f" * 64
HEX_0 = "0" * 64
HEX_1 = "1" * 64


def make_question() -> ChoiceQuestion:
    return ChoiceQuestion(
        "department",
        "Select the department responsible for this ticket.",
        (
            Option("billing", "Payments and refunds"),
            Option("technical", "Technical support"),
            Option("sales", "Purchasing questions"),
        ),
    )


def make_identity() -> ModelIdentity:
    return ModelIdentity(
        "fixture",
        "recorded-choice-v1",
        HEX_A,
        (("responses", HEX_A),),
        "1",
        "1",
        (("python", "3.12"), ("os", "darwin")),
    )


def make_policy() -> LockedPolicy:
    return LockedPolicy(("billing", "technical", "sales"), ("billing", "technical"), 0.9)


def make_limits() -> GateLimits:
    return GateLimits(0.05, 0.5, 0.05)


def make_contract() -> Contract:
    return Contract(
        1,
        "support-triage",
        make_question(),
        make_policy(),
        make_limits(),
        "demo",
        "Authored support-routing demonstration; no deployment claim",
    )


def make_case() -> Case:
    return Case("v-001", "Refund not received after cancellation.", "billing")


def make_case_ref() -> CaseRef:
    return CaseRef("v-001", HEX_B)


def make_fault_spec() -> FaultSpec:
    return FaultSpec("fault.timeout", "timeout", "ESCALATE")


def make_lock() -> PlanLock:
    return PlanLock(
        2,
        make_contract(),
        make_identity(),
        HEX_C,
        HEX_D,
        (CaseRef("c-001", HEX_E), CaseRef("c-002", HEX_F)),
        (make_case_ref(),),
        (make_case(),),
        (make_fault_spec(), FaultSpec("fault.unknown_choice", "unknown_choice", "DENY")),
        HEX_0,
        HEX_1,
        "actseal-choice-v1",
    )


def make_request() -> DecisionRequest:
    return DecisionRequest("v-001", "Refund not received after cancellation.", make_question())


def make_capture(*, failed: bool = False) -> CapturedOutcome:
    if failed:
        return CapturedOutcome(HEX_A, make_identity(), None, "timeout", ("w.slow",), False)
    return CapturedOutcome(HEX_A, make_identity(), '{"type":"choice"}', None, (), False)


def make_answer() -> ChoiceAnswer:
    return ChoiceAnswer(
        "billing",
        (("billing", 0.95), ("technical", 0.04), ("sales", 0.01)),
        0.95,
        0.9,
        ("w.calibration",),
        False,
    )


def make_failure() -> ProviderFailure:
    return ProviderFailure("timeout", (), False)


def make_decision(*, act: bool = True) -> PolicyDecision:
    if act:
        return PolicyDecision("ACT", "billing", "policy.allowed", False)
    return PolicyDecision("ESCALATE", None, "provider.timeout", False)


def make_record() -> DecisionRecord:
    return DecisionRecord("v-001", make_capture(), make_answer(), make_decision())


def make_fault_result() -> FaultResult:
    return FaultResult(
        "fault.timeout",
        make_request(),
        make_capture(failed=True),
        make_failure(),
        make_decision(act=False),
    )


def make_interval() -> Interval:
    return Interval(0.0, 0.25)


def make_verdict() -> Verdict:
    return Verdict(
        "PASS",
        ("contract.satisfied",),
        1,
        1,
        0,
        Interval(0.0, 0.05),
        Interval(0.5, 1.0),
        "demo",
        HEX_1,
    )


def make_bundle() -> EvidenceBundle:
    second_fault = FaultResult(
        "fault.unknown_choice",
        make_request(),
        make_capture(),
        ProviderFailure("unknown_choice", (), False),
        PolicyDecision("DENY", None, "policy.unknown_choice", False),
    )
    return EvidenceBundle(
        make_lock(),
        '{"case_id":"c-001","state":"s","expected_label":"billing"}\n',
        '{"case_id":"v-001","state":"s","expected_label":"billing"}\n',
        (make_record(),),
        (make_fault_result(), second_fault),
        make_verdict(),
    )


SAMPLE_BUILDERS: dict[str, Any] = {
    "Option": lambda: Option("billing", "Payments and refunds"),
    "ChoiceQuestion": make_question,
    "Case": make_case,
    "CaseRef": make_case_ref,
    "ModelIdentity": make_identity,
    "DecisionRequest": make_request,
    "CapturedOutcome": make_capture,
    "ChoiceAnswer": make_answer,
    "ProviderFailure": make_failure,
    "LockedPolicy": make_policy,
    "GateLimits": make_limits,
    "Contract": make_contract,
    "FaultSpec": make_fault_spec,
    "PlanLock": make_lock,
    "PolicyDecision": make_decision,
    "DecisionRecord": make_record,
    "FaultResult": make_fault_result,
    "Interval": make_interval,
    "Verdict": make_verdict,
    "EvidenceBundle": make_bundle,
}


@pytest.fixture
def samples() -> dict[str, object]:
    """One freshly built valid instance of every public record type."""
    return {name: build() for name, build in SAMPLE_BUILDERS.items()}
