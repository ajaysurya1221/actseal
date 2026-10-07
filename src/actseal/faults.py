"""Deterministic six-scenario fault campaign (plan/CONTRACTS.md section 4).

``fault_capture`` is a pure canonical generator: given a sealed lock and one
of its frozen :class:`FaultSpec` records it returns the exact synthetic request
and capture that assessment and replay independently recompute and compare.
``run_fault_campaign`` feeds each canonical capture through the SAME pure
normalizer and the accepted policy evaluator and returns one
:class:`FaultResult` per inventory entry, in lock order, never stopping early.

Canonical shape:

* request ``case_id`` is the scenario id, ``state`` is the literal
  ``Actseal deterministic fault campaign.`` and ``question`` is the locked
  question; the capture hash is the canonical request hash;
* every capture has ``warnings=()`` and ``fallback_used=False`` and starts
  from ``lock.model_identity``;
* ``timeout``/``rate_limit`` carry no body and ``failure_code=kind``;
  ``malformed_response`` carries the literal body ``{``;
* the other three carry a canonical JSON answer with only ``type``,
  ``choice`` and ``probabilities`` (all known labels at 0.0 except the first
  allowed label at 1.0). ``identity_mismatch`` changes only the observed
  revision to ``<revision>:fault``; ``unknown_choice`` selects
  ``__actseal_unknown__`` with ``_`` appended until it is outside the known
  labels; ``low_confidence`` keeps the first allowed label selected at 0.0 and
  gives the first different known label 1.0 (selected-probability gating, not
  argmax substitution). For a ``laya`` identity the answer is wrapped in the
  synthetic zero-usage native envelope before serialization. For a ``jev``
  identity (experimental, plan/v1/CHANGE_LOG.md V1-011) the answer additionally
  carries the diagnostic vendor ``confidence`` 1.0 that a one-hot distribution
  implies, including the ``low_confidence`` case whose *selected* probability
  is 0.0, and is wrapped in ``{model: jev-1.13.0, answers, usage:
  {input_tokens: 0, output_tokens: 0}}``. That confidence proves the vendor
  score is not the ACT gate. Zero usage is synthetic fault data, not inference.

This module imports no adapter, transport, assessment or replay code.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Final

from actseal.errors import SchemaError
from actseal.normalization import _JEV_MODEL, LAYA_MODEL_MARKER, normalize, request_sha256
from actseal.policy import evaluate
from actseal.records import (
    CapturedOutcome,
    DecisionRequest,
    FaultResult,
    FaultSpec,
    ModelIdentity,
    PlanLock,
)
from actseal.serialization import canonical_json

__all__ = ["FAULT_STATE", "fault_capture", "run_fault_campaign"]

FAULT_STATE: Final = "Actseal deterministic fault campaign."
_UNKNOWN_CHOICE: Final = "__actseal_unknown__"
_MALFORMED_BODY: Final = "{"
_TRANSPORT_KINDS: Final[frozenset[str]] = frozenset({"timeout", "rate_limit"})
_ANSWER_KINDS: Final[frozenset[str]] = frozenset(
    {"identity_mismatch", "unknown_choice", "low_confidence"}
)
_ZERO_USAGE: Final[dict[str, object]] = {
    "input_tokens": 0,
    "output_tokens": 0,
    "state_tokens": 0,
    "state_tokens_dropped": 0,
    "truncated": False,
    "truncated_questions": [],
}
_JEV_ZERO_USAGE: Final[dict[str, object]] = {"input_tokens": 0, "output_tokens": 0}
#: Vendor Choice confidence ``(p_max - 1/n) / (1 - 1/n)`` of a one-hot distribution.
_JEV_ONE_HOT_CONFIDENCE: Final = 1.0


def _canonical_body(lock: PlanLock, kind: str) -> tuple[str, ModelIdentity]:
    """The serialized answer body and observed identity for an answer-shaped fault."""
    policy = lock.contract.policy
    known = policy.known_labels
    selected = policy.allowed_labels[0]
    probabilities: dict[str, float] = dict.fromkeys(known, 0.0)
    probabilities[selected] = 1.0
    choice = selected
    identity = lock.model_identity
    if kind == "identity_mismatch":
        identity = replace(identity, revision=identity.revision + ":fault")
    elif kind == "unknown_choice":
        choice = _UNKNOWN_CHOICE
        while choice in known:
            choice += "_"
    else:  # low_confidence
        probabilities[selected] = 0.0
        probabilities[next(label for label in known if label != selected)] = 1.0
    answer: dict[str, object] = {
        "type": "choice",
        "choice": choice,
        "probabilities": probabilities,
    }
    body: dict[str, object] = answer
    if lock.model_identity.provider == "laya":
        body = {
            "model": LAYA_MODEL_MARKER,
            "answers": {lock.contract.question.question_id: answer},
            "usage": dict(_ZERO_USAGE),
        }
    elif lock.model_identity.provider == "jev":
        answer["confidence"] = _JEV_ONE_HOT_CONFIDENCE
        body = {
            "model": _JEV_MODEL,
            "answers": {lock.contract.question.question_id: answer},
            "usage": dict(_JEV_ZERO_USAGE),
        }
    return canonical_json(body).decode("utf-8"), identity


def fault_capture(lock: PlanLock, spec: FaultSpec) -> tuple[DecisionRequest, CapturedOutcome]:
    """Return the canonical synthetic request and capture for one fault specification."""
    if not isinstance(lock, PlanLock):
        raise SchemaError("lock: must be PlanLock")
    if not isinstance(spec, FaultSpec):
        raise SchemaError("spec: must be FaultSpec")
    kind = spec.kind
    request = DecisionRequest(spec.scenario_id, FAULT_STATE, lock.contract.question)
    digest = request_sha256(request)
    if kind in _TRANSPORT_KINDS:
        capture = CapturedOutcome(digest, lock.model_identity, None, kind, (), fallback_used=False)
    elif kind == "malformed_response":
        capture = CapturedOutcome(
            digest, lock.model_identity, _MALFORMED_BODY, None, (), fallback_used=False
        )
    elif kind in _ANSWER_KINDS:
        body, identity = _canonical_body(lock, kind)
        capture = CapturedOutcome(digest, identity, body, None, (), fallback_used=False)
    else:
        raise SchemaError("spec.kind: unsupported fault kind")
    return request, capture


def run_fault_campaign(lock: PlanLock) -> tuple[FaultResult, ...]:
    """Normalize and evaluate every locked fault scenario in order; never stop early."""
    if not isinstance(lock, PlanLock):
        raise SchemaError("lock: must be PlanLock")
    question = lock.contract.question
    results: list[FaultResult] = []
    for spec in lock.fault_inventory:
        request, capture = fault_capture(lock, spec)
        outcome = normalize(capture, question, lock.model_identity)
        decision = evaluate(outcome, lock.contract.policy)
        results.append(FaultResult(spec.scenario_id, request, capture, outcome, decision))
    return tuple(results)
