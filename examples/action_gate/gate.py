"""An application-owned action gate around the Actseal evaluator (Task 07).

This module is the *application* side of the boundary. It is example code,
not part of the ``actseal`` package, and it adds no product API. It shows
where Actseal sits in ordinary control flow:

1. The application decides whether the gate may open at all: the lock it
   holds must match the policy identity it expects (``expected_lock_sha256``
   from the application's own configuration), the lock must validate under
   the running implementation, the deployed model must report the locked
   identity, and the verification verdict for that exact lock must be PASS.
2. For each incoming ticket the application builds a label-free
   :class:`~actseal.records.DecisionRequest`, captures the model's raw
   response, requires the capture to be bound to that exact request (its
   ``request_sha256`` must equal ``request_sha256(request)``; a capture for a
   different ticket is :class:`RequestBindingError` before anything else
   happens), normalizes it against the locked question and identity with the
   same pure ``normalize`` that verification and replay use, and evaluates the
   locked policy with the same ``evaluate``.
3. Only an ``ACT`` decision performs the application's action, here one
   ``enqueue`` on a local in-memory queue. ``ABSTAIN``, ``ESCALATE`` and
   ``DENY`` take explicit non-execution paths (held for a person, escalated,
   rejected). Nothing is retried, repaired or downgraded. An exception from
   the provider or the queue propagates as is; whether a failing queue
   operation left a partial effect behind is the queue's and the
   application's concern, not something this example can promise away.

Actseal does not enforce any of this: the application calls the evaluator and
owns every effect. A gold label is never needed at run time and never enters
the request.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

from actseal.adapters.base import DecisionModel
from actseal.locking import validate_lock
from actseal.normalization import normalize, request_sha256
from actseal.policy import evaluate
from actseal.records import Action, DecisionRequest, PlanLock, PolicyDecision, Verdict
from actseal.runner import REQUEST_TIMEOUT_S

__all__ = [
    "PATH_ESCALATED",
    "PATH_HELD",
    "PATH_QUEUED",
    "PATH_REJECTED",
    "ActionGate",
    "Disposition",
    "GateClosedError",
    "LocalQueue",
    "RequestBindingError",
    "RoutePath",
    "Ticket",
    "route_all",
]

RoutePath = Literal["queued", "held_for_review", "escalated", "rejected"]

PATH_QUEUED: Final[RoutePath] = "queued"
PATH_HELD: Final[RoutePath] = "held_for_review"
PATH_ESCALATED: Final[RoutePath] = "escalated"
PATH_REJECTED: Final[RoutePath] = "rejected"


class GateClosedError(RuntimeError):
    """The application refused to open the gate; no ticket is routed."""


class RequestBindingError(RuntimeError):
    """The provider returned a capture for a different request; nothing is evaluated or executed."""


@dataclass(frozen=True, slots=True)
class Ticket:
    """An incoming ticket as the application sees it: an id and text, never a label."""

    ticket_id: str
    text: str


@dataclass(frozen=True, slots=True)
class Disposition:
    """What the application did with one ticket.

    ``executed`` is true only when the queue operation actually ran, which
    happens only for ``ACT``; ``queue`` names the queue written to in that
    case and is ``None`` otherwise.
    """

    ticket_id: str
    action: Action
    reason: str
    path: RoutePath
    queue: str | None
    executed: bool


class LocalQueue:
    """In-memory stand-in for the application's queue; the only action this example executes."""

    def __init__(self) -> None:
        self._journal: list[tuple[str, str]] = []

    def enqueue(self, queue: str, ticket_id: str) -> None:
        self._journal.append((queue, ticket_id))

    @property
    def journal(self) -> tuple[tuple[str, str], ...]:
        """Every ``(queue, ticket_id)`` operation in execution order."""
        return tuple(self._journal)

    def contents(self, queue: str) -> tuple[str, ...]:
        return tuple(ticket_id for name, ticket_id in self._journal if name == queue)


class ActionGate:
    """A gate the application opens once, then consults for every ticket."""

    def __init__(
        self,
        lock: PlanLock,
        verdict: Verdict,
        model: DecisionModel,
        *,
        expected_lock_sha256: str,
    ) -> None:
        if lock.sha256 != expected_lock_sha256:
            raise GateClosedError("lock: does not match the expected policy identity")
        # Seal, replay-engine compatibility with the running implementation,
        # frozen fault inventory and case coherence: the product's own check.
        validate_lock(lock)
        if verdict.lock_sha256 != lock.sha256:
            raise GateClosedError("verdict: belongs to a different lock")
        if verdict.status != "PASS":
            raise GateClosedError(f"verdict: status is {verdict.status}, not PASS")
        if model.identity() != lock.model_identity:
            raise GateClosedError("model: deployed identity differs from the locked identity")
        self._lock = lock
        self._model = model

    @property
    def lock(self) -> PlanLock:
        return self._lock

    def decide(self, ticket: Ticket) -> PolicyDecision:
        """Capture, bind, normalize and evaluate one ticket. Executes nothing.

        The capture must carry the canonical hash of exactly this request. A
        same-identity capture for another ticket (a provider bug, a stale
        cache, a swapped reply) is :class:`RequestBindingError` before
        normalization, so it can never authorize a queue write.
        """
        question = self._lock.contract.question
        request = DecisionRequest(ticket.ticket_id, ticket.text, question)
        capture = self._model.decide(request, timeout_s=REQUEST_TIMEOUT_S)
        if capture.request_sha256 != request_sha256(request):
            raise RequestBindingError(
                f"capture: request_sha256 is not bound to ticket {ticket.ticket_id}"
            )
        outcome = normalize(capture, question, self._lock.model_identity)
        return evaluate(outcome, self._lock.contract.policy)

    def route(self, ticket: Ticket, queue: LocalQueue) -> Disposition:
        """Decide one ticket and take exactly one of the four application paths."""
        decision = self.decide(ticket)
        if decision.action == "ACT":
            return self._enqueue(ticket, decision, queue)
        if decision.action == "ABSTAIN":
            return self._hold_for_review(ticket, decision)
        if decision.action == "ESCALATE":
            return self._escalate(ticket, decision)
        return self._reject(ticket, decision)

    # The four application-owned paths. Only the first one has an effect.

    @staticmethod
    def _enqueue(ticket: Ticket, decision: PolicyDecision, queue: LocalQueue) -> Disposition:
        if decision.choice is None:  # the policy guarantees a choice for ACT
            raise GateClosedError("decision: ACT without a choice")
        queue.enqueue(decision.choice, ticket.ticket_id)
        return Disposition(
            ticket.ticket_id,
            decision.action,
            decision.reason,
            PATH_QUEUED,
            decision.choice,
            executed=True,
        )

    @staticmethod
    def _hold_for_review(ticket: Ticket, decision: PolicyDecision) -> Disposition:
        """ABSTAIN: the model's selected probability was below the frozen threshold."""
        return Disposition(
            ticket.ticket_id, decision.action, decision.reason, PATH_HELD, None, executed=False
        )

    @staticmethod
    def _escalate(ticket: Ticket, decision: PolicyDecision) -> Disposition:
        """ESCALATE: a provider failure, identity mismatch or fallback flag."""
        return Disposition(
            ticket.ticket_id, decision.action, decision.reason, PATH_ESCALATED, None, executed=False
        )

    @staticmethod
    def _reject(ticket: Ticket, decision: PolicyDecision) -> Disposition:
        """DENY: an unknown choice or a known label the policy does not route."""
        return Disposition(
            ticket.ticket_id, decision.action, decision.reason, PATH_REJECTED, None, executed=False
        )


def route_all(
    gate: ActionGate, tickets: tuple[Ticket, ...], queue: LocalQueue
) -> tuple[Disposition, ...]:
    """Route tickets in order.

    An exception from the provider, the binding check or the queue propagates
    and stops routing at that ticket: nothing is retried, skipped or
    downgraded to a different path, and no :class:`Disposition` is produced
    for it. A provider or binding failure happens before any effect. A queue
    operation that fails may or may not have performed its effect first; the
    exception carries that question to the application, which owns the queue.
    This example adds no transaction or compensation machinery.
    """
    return tuple(gate.route(ticket, queue) for ticket in tickets)
