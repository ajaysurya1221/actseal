"""The application boundary: four decisions, the threshold edge, no execution on failure."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from actseal.adapters.fixture import FixtureModel
from actseal.errors import IntegrityError, ProviderSetupError
from actseal.locking import lock_digest
from actseal.normalization import normalize
from actseal.records import (
    CapturedOutcome,
    ChoiceAnswer,
    DecisionRequest,
    Interval,
    ModelIdentity,
    Verdict,
)
from actseal.serialization import canonical_json, to_data
from examples.examples_support import EXAMPLE_DIR

HEX_F = "f" * 64


def open_gate(gate: ModuleType, fresh: Any, model: Any | None = None) -> Any:
    responses = EXAMPLE_DIR / "responses.jsonl"
    return gate.ActionGate(
        fresh.lock,
        fresh.replayed,
        FixtureModel(responses) if model is None else model,
        expected_lock_sha256=fresh.lock.sha256,
    )


class RecordingModel:
    """Wraps the fixture and records every request the application sends."""

    def __init__(self, responses: Path) -> None:
        self._inner = FixtureModel(responses)
        self.requests: list[DecisionRequest] = []

    def identity(self) -> ModelIdentity:
        return self._inner.identity()

    def decide(self, request: DecisionRequest, *, timeout_s: float) -> CapturedOutcome:
        self.requests.append(request)
        return self._inner.decide(request, timeout_s=timeout_s)

    def close(self) -> None:
        self._inner.close()


class FallbackModel(RecordingModel):
    """A provider that answers confidently but flags that a fallback was used."""

    def decide(self, request: DecisionRequest, *, timeout_s: float) -> CapturedOutcome:
        capture = super().decide(request, timeout_s=timeout_s)
        return replace(capture, fallback_used=True)


class SwappingModel(RecordingModel):
    """Answers one ticket with the (same-identity) capture recorded for another ticket."""

    def __init__(self, responses: Path, swap: dict[str, str]) -> None:
        super().__init__(responses)
        self._swap = swap

    def decide(self, request: DecisionRequest, *, timeout_s: float) -> CapturedOutcome:
        self.requests.append(request)
        other = self._swap.get(request.case_id)
        if other is None:
            return self._inner.decide(request, timeout_s=timeout_s)
        swapped = DecisionRequest(other, f"Ticket {other}: swapped", request.question)
        return self._inner.decide(swapped, timeout_s=timeout_s)


class FailingModel(RecordingModel):
    """Raises on the named ticket, after answering the earlier ones."""

    def __init__(self, responses: Path, failing_ticket: str) -> None:
        super().__init__(responses)
        self._failing = failing_ticket

    def decide(self, request: DecisionRequest, *, timeout_s: float) -> CapturedOutcome:
        if request.case_id == self._failing:
            self.requests.append(request)
            raise RuntimeError("provider crashed")
        return super().decide(request, timeout_s=timeout_s)


# --------------------------------------------------------------------------- #
# All four decisions
# --------------------------------------------------------------------------- #


def test_every_decision_takes_its_own_path_and_only_act_executes(
    gate: ModuleType, run: ModuleType, fresh: Any
) -> None:
    tickets = run.load_tickets(EXAMPLE_DIR / "tickets.jsonl")
    queue = gate.LocalQueue()
    dispositions = gate.route_all(open_gate(gate, fresh), tickets, queue)
    by_action = {d.action for d in dispositions}
    assert by_action == {"ACT", "ABSTAIN", "ESCALATE", "DENY"}
    paths = {
        "ACT": gate.PATH_QUEUED,
        "ABSTAIN": gate.PATH_HELD,
        "ESCALATE": gate.PATH_ESCALATED,
        "DENY": gate.PATH_REJECTED,
    }
    for disposition in dispositions:
        expected_action, expected_reason, expected_queue = run.EXPECTED_DISPOSITIONS[
            disposition.ticket_id
        ]
        assert disposition.action == expected_action
        assert disposition.reason == expected_reason
        assert disposition.path == paths[expected_action]
        assert disposition.queue == expected_queue
        assert disposition.executed is (expected_action == "ACT")
    assert queue.journal == (("billing", "T-1001"), ("technical", "T-1002"), ("sales", "T-1003"))
    assert queue.contents("billing") == ("T-1001",)
    assert queue.contents("other") == ()


def test_both_deny_reasons_and_both_escalate_reasons_are_covered(
    gate: ModuleType, run: ModuleType, fresh: Any
) -> None:
    tickets = run.load_tickets(EXAMPLE_DIR / "tickets.jsonl")
    reasons = {
        d.ticket_id: d.reason
        for d in gate.route_all(open_gate(gate, fresh), tickets, gate.LocalQueue())
    }
    assert reasons["T-1006"] == "policy.disallowed_choice"  # known label, not routed
    assert reasons["T-1007"] == "policy.unknown_choice"  # label outside the question
    assert reasons["T-1005"] == "provider.timeout"
    assert reasons["T-1008"] == "provider.malformed_response"


# --------------------------------------------------------------------------- #
# Threshold boundary
# --------------------------------------------------------------------------- #


def test_selected_probability_at_threshold_acts_and_just_below_abstains(
    gate: ModuleType, run: ModuleType, fresh: Any
) -> None:
    threshold = fresh.lock.contract.policy.threshold
    model = RecordingModel(EXAMPLE_DIR / "responses.jsonl")
    opened = open_gate(gate, fresh, model)
    tickets = {t.ticket_id: t for t in run.load_tickets(EXAMPLE_DIR / "tickets.jsonl")}
    at = opened.decide(tickets["T-1003"])
    below = opened.decide(tickets["T-1004"])
    assert (at.action, at.choice) == ("ACT", "sales")
    assert (below.action, below.choice, below.reason) == ("ABSTAIN", None, "policy.low_confidence")
    # The recorded selected probabilities sit exactly on either side of the frozen threshold.
    question = fresh.lock.contract.question
    outcomes = [
        normalize(
            model.decide(DecisionRequest(t.ticket_id, t.text, question), timeout_s=1.0),
            question,
            fresh.lock.model_identity,
        )
        for t in (tickets["T-1003"], tickets["T-1004"])
    ]
    assert all(isinstance(o, ChoiceAnswer) for o in outcomes)
    assert isinstance(outcomes[0], ChoiceAnswer)
    assert isinstance(outcomes[1], ChoiceAnswer)
    assert outcomes[0].selected_probability == threshold == 0.9
    assert outcomes[1].selected_probability < threshold
    assert outcomes[0].warnings == ()  # no renormalization on either side
    assert outcomes[1].warnings == ()


# --------------------------------------------------------------------------- #
# Run time needs no gold label
# --------------------------------------------------------------------------- #


def test_requests_carry_no_label_and_tickets_have_no_label_field(
    gate: ModuleType, run: ModuleType, fresh: Any
) -> None:
    model = RecordingModel(EXAMPLE_DIR / "responses.jsonl")
    tickets = run.load_tickets(EXAMPLE_DIR / "tickets.jsonl")
    gate.route_all(open_gate(gate, fresh, model), tickets, gate.LocalQueue())
    assert len(model.requests) == len(tickets)
    for request, ticket in zip(model.requests, tickets, strict=True):
        assert isinstance(request, DecisionRequest)
        assert set(to_data(request)) == {"case_id", "state", "question"}
        assert request.case_id == ticket.ticket_id
        assert request.state == ticket.text
        assert request.question == fresh.lock.contract.question
        assert b"expected_label" not in canonical_json(to_data(request))
    assert gate.Ticket.__dataclass_fields__.keys() == {"ticket_id", "text"}


# --------------------------------------------------------------------------- #
# No execution on failure
# --------------------------------------------------------------------------- #


def test_fallback_flag_never_inherits_act(gate: ModuleType, run: ModuleType, fresh: Any) -> None:
    tickets = run.load_tickets(EXAMPLE_DIR / "tickets.jsonl")
    queue = gate.LocalQueue()
    model = FallbackModel(EXAMPLE_DIR / "responses.jsonl")
    dispositions = gate.route_all(open_gate(gate, fresh, model), tickets, queue)
    assert {d.action for d in dispositions} == {"ESCALATE"}
    assert {d.reason for d in dispositions} == {"policy.fallback_used"}
    assert all(not d.executed and d.queue is None for d in dispositions)
    assert queue.journal == ()


def test_provider_exception_stops_routing_without_enqueueing_that_ticket(
    gate: ModuleType, run: ModuleType, fresh: Any
) -> None:
    tickets = run.load_tickets(EXAMPLE_DIR / "tickets.jsonl")
    queue = gate.LocalQueue()
    model = FailingModel(EXAMPLE_DIR / "responses.jsonl", "T-1002")
    with pytest.raises(RuntimeError, match="provider crashed"):
        gate.route_all(open_gate(gate, fresh, model), tickets, queue)
    assert queue.journal == (("billing", "T-1001"),)  # routed before the failure, nothing after
    assert [r.case_id for r in model.requests] == ["T-1001", "T-1002"]


def test_unrecorded_ticket_is_a_setup_error_not_a_decision(gate: ModuleType, fresh: Any) -> None:
    queue = gate.LocalQueue()
    with pytest.raises(ProviderSetupError):
        open_gate(gate, fresh).route(gate.Ticket("T-9999", "Ticket T-9999: unseen"), queue)
    assert queue.journal == ()


def test_swapped_capture_is_refused_before_any_effect(
    gate: ModuleType, run: ModuleType, fresh: Any
) -> None:
    """A same-identity capture for another ticket must not authorize a queue write.

    T-1002's recorded answer is a confident ``technical`` ACT. Served as the
    reply to T-1001 it still carries T-1002's request hash, so the gate must
    refuse it before normalization; nothing is enqueued and no disposition is
    produced.
    """
    tickets = run.load_tickets(EXAMPLE_DIR / "tickets.jsonl")
    queue = gate.LocalQueue()
    model = SwappingModel(EXAMPLE_DIR / "responses.jsonl", {"T-1001": "T-1002"})
    opened = open_gate(gate, fresh, model)
    with pytest.raises(gate.RequestBindingError, match="T-1001"):
        opened.route(tickets[0], queue)
    assert queue.journal == ()
    assert [r.case_id for r in model.requests] == ["T-1001"]
    with pytest.raises(gate.RequestBindingError):
        gate.route_all(opened, tickets, queue)
    assert queue.journal == ()
    # The same model answers every other ticket exactly as before.
    honest = gate.route_all(
        open_gate(gate, fresh, SwappingModel(EXAMPLE_DIR / "responses.jsonl", {})),
        tickets,
        queue,
    )
    assert [d.action for d in honest] == [
        run.EXPECTED_DISPOSITIONS[t.ticket_id][0] for t in tickets
    ]


def test_queue_failure_before_its_effect_propagates_and_records_nothing(
    gate: ModuleType, run: ModuleType, fresh: Any
) -> None:
    class BrokenQueue:
        journal: tuple[tuple[str, str], ...] = ()

        def enqueue(self, queue: str, ticket_id: str) -> None:
            del queue, ticket_id
            raise OSError("queue unavailable")

    tickets = run.load_tickets(EXAMPLE_DIR / "tickets.jsonl")
    queue = BrokenQueue()
    with pytest.raises(OSError, match="queue unavailable"):
        gate.route_all(open_gate(gate, fresh), tickets, queue)
    assert queue.journal == ()


def test_queue_failure_after_its_effect_propagates_with_the_effect_retained(
    gate: ModuleType, run: ModuleType, fresh: Any
) -> None:
    """The example promises propagation without retry, not that a failed enqueue had no effect."""

    class EffectThenRaiseQueue:
        def __init__(self) -> None:
            self.journal: tuple[tuple[str, str], ...] = ()

        def enqueue(self, queue: str, ticket_id: str) -> None:
            self.journal = (*self.journal, (queue, ticket_id))
            if ticket_id == "T-1002":
                raise OSError("acknowledgement lost after write")

    def route_each(opened: Any, queue: EffectThenRaiseQueue, sink: list[Any]) -> None:
        for ticket in run.load_tickets(EXAMPLE_DIR / "tickets.jsonl"):
            disposition = opened.route(ticket, queue)
            sink.append(disposition)

    queue = EffectThenRaiseQueue()
    dispositions: list[Any] = []
    with pytest.raises(OSError, match="acknowledgement lost"):
        route_each(open_gate(gate, fresh), queue, dispositions)
    # The write happened, the exception reached the application, no disposition claims it,
    # and nothing after it was routed or retried.
    assert queue.journal == (("billing", "T-1001"), ("technical", "T-1002"))
    assert [d.ticket_id for d in dispositions] == ["T-1001"]


# --------------------------------------------------------------------------- #
# The gate does not open on bad preconditions
# --------------------------------------------------------------------------- #


def _blocked(verdict: Verdict) -> Verdict:
    return replace(
        verdict,
        status="BLOCK",
        reasons=("risk.exceeds_limit",),
        risk=Interval(0.2, 0.4),
    )


def test_gate_refuses_non_pass_verdict(gate: ModuleType, fresh: Any, responses: Path) -> None:
    with pytest.raises(gate.GateClosedError, match="not PASS"):
        gate.ActionGate(
            fresh.lock,
            _blocked(fresh.replayed),
            FixtureModel(responses),
            expected_lock_sha256=fresh.lock.sha256,
        )


def test_gate_refuses_unexpected_lock_identity(
    gate: ModuleType, fresh: Any, responses: Path
) -> None:
    with pytest.raises(gate.GateClosedError, match="expected policy identity"):
        gate.ActionGate(
            fresh.lock, fresh.replayed, FixtureModel(responses), expected_lock_sha256=HEX_F
        )


def test_gate_refuses_verdict_for_a_different_lock(
    gate: ModuleType, fresh: Any, responses: Path
) -> None:
    foreign = replace(fresh.replayed, lock_sha256=HEX_F)
    with pytest.raises(gate.GateClosedError, match="different lock"):
        gate.ActionGate(
            fresh.lock, foreign, FixtureModel(responses), expected_lock_sha256=fresh.lock.sha256
        )


def test_gate_refuses_a_model_whose_identity_differs(
    gate: ModuleType, fresh: Any, responses: Path, tmp_path: Path
) -> None:
    altered = tmp_path / "responses.jsonl"
    # A valid but different recording: the fixture identity is the file hash.
    altered.write_bytes(responses.read_bytes().replace(b'"warnings": []', b'"warnings": ["x"]', 1))
    with pytest.raises(gate.GateClosedError, match="locked identity"):
        gate.ActionGate(
            fresh.lock,
            fresh.replayed,
            FixtureModel(altered),
            expected_lock_sha256=fresh.lock.sha256,
        )


def test_gate_refuses_a_lock_from_a_foreign_implementation(
    gate: ModuleType, fresh: Any, responses: Path
) -> None:
    foreign = replace(fresh.lock, implementation_sha256=HEX_F)
    foreign = replace(foreign, sha256=lock_digest(foreign))
    verdict = replace(fresh.replayed, lock_sha256=foreign.sha256)
    with pytest.raises(IntegrityError, match="implementation_sha256"):
        gate.ActionGate(
            foreign, verdict, FixtureModel(responses), expected_lock_sha256=foreign.sha256
        )


def test_gate_refuses_a_tampered_seal(gate: ModuleType, fresh: Any, responses: Path) -> None:
    tampered = replace(fresh.lock, sha256=HEX_F)
    verdict = replace(fresh.replayed, lock_sha256=HEX_F)
    with pytest.raises(IntegrityError, match="self-seal"):
        gate.ActionGate(tampered, verdict, FixtureModel(responses), expected_lock_sha256=HEX_F)
