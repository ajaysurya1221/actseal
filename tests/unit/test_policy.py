"""Exhaustive runtime policy evaluation: precedence, boundaries and invariants."""

from __future__ import annotations

import itertools

import pytest

from actseal.errors import SchemaError
from actseal.policy import (
    REASON_ALLOWED,
    REASON_DISALLOWED_CHOICE,
    REASON_FALLBACK_USED,
    REASON_LOW_CONFIDENCE,
    REASON_PROVIDER_PREFIX,
    REASON_UNKNOWN_CHOICE,
    evaluate,
)
from actseal.records import (
    FAILURE_CODES,
    ChoiceAnswer,
    LockedPolicy,
    Outcome,
    PolicyDecision,
    ProviderFailure,
)
from conftest import make_policy

# The shared sample policy knows billing/technical/sales, allows billing and
# technical only, and gates at 0.9.
POLICY = make_policy()
THRESHOLD = POLICY.threshold
KNOWN = POLICY.known_labels
ALLOWED = POLICY.allowed_labels
DISALLOWED_KNOWN = "sales"
UNKNOWN = "legal"
CONFIDENCES: tuple[float | None, ...] = (None, 0.0, 0.5, 1.0)
WARNINGS: tuple[tuple[str, ...], ...] = ((), ("w.slow", "w.calibration"))


def answer(
    choice: str,
    probability: float,
    *,
    fallback: bool = False,
    confidence: float | None = None,
    warnings: tuple[str, ...] = (),
    labels: tuple[str, ...] = KNOWN,
) -> ChoiceAnswer:
    """An answer whose selected label carries ``probability``; the rest share the remainder."""
    others = [label for label in labels if label != choice]
    share = (1.0 - probability) / len(others)
    pairs = [(label, probability if label == choice else share) for label in labels]
    if choice not in labels:
        pairs.append((choice, probability))
    return ChoiceAnswer(choice, tuple(pairs), probability, confidence, warnings, fallback)


def failure(
    code: str, *, fallback: bool = False, warnings: tuple[str, ...] = ()
) -> ProviderFailure:
    return ProviderFailure(code, warnings, fallback)


# --------------------------------------------------------------------------- #
# Reason codes and precedence table
# --------------------------------------------------------------------------- #


def test_reason_codes_are_the_frozen_strings() -> None:
    assert REASON_FALLBACK_USED == "policy.fallback_used"
    assert REASON_UNKNOWN_CHOICE == "policy.unknown_choice"
    assert REASON_PROVIDER_PREFIX == "provider."
    assert REASON_DISALLOWED_CHOICE == "policy.disallowed_choice"
    assert REASON_LOW_CONFIDENCE == "policy.low_confidence"
    assert REASON_ALLOWED == "policy.allowed"


@pytest.mark.parametrize(
    ("outcome", "expected"),
    [
        # 6. allowed label at or above threshold -> ACT with the choice
        (answer("billing", 0.95), PolicyDecision("ACT", "billing", "policy.allowed", False)),
        (answer("technical", 1.0), PolicyDecision("ACT", "technical", "policy.allowed", False)),
        (answer("billing", 0.9), PolicyDecision("ACT", "billing", "policy.allowed", False)),
        # 5. allowed label below threshold -> ABSTAIN
        (answer("billing", 0.0), PolicyDecision("ABSTAIN", None, "policy.low_confidence", False)),
        (answer("billing", 0.5), PolicyDecision("ABSTAIN", None, "policy.low_confidence", False)),
        (
            answer("technical", 0.89),
            PolicyDecision("ABSTAIN", None, "policy.low_confidence", False),
        ),
        # 4. known but not allowed, or unknown, label -> DENY regardless of probability
        (answer("sales", 1.0), PolicyDecision("DENY", None, "policy.disallowed_choice", False)),
        (answer("sales", 0.1), PolicyDecision("DENY", None, "policy.disallowed_choice", False)),
        (answer("legal", 1.0), PolicyDecision("DENY", None, "policy.disallowed_choice", False)),
        (answer("Billing", 1.0), PolicyDecision("DENY", None, "policy.disallowed_choice", False)),
        # 3. provider failures other than unknown_choice -> ESCALATE with provider.<code>
        (failure("timeout"), PolicyDecision("ESCALATE", None, "provider.timeout", False)),
        (failure("rate_limit"), PolicyDecision("ESCALATE", None, "provider.rate_limit", False)),
        (
            failure("malformed_response"),
            PolicyDecision("ESCALATE", None, "provider.malformed_response", False),
        ),
        (
            failure("identity_mismatch"),
            PolicyDecision("ESCALATE", None, "provider.identity_mismatch", False),
        ),
        (
            failure("provider_error"),
            PolicyDecision("ESCALATE", None, "provider.provider_error", False),
        ),
        (
            failure("input_too_long"),
            PolicyDecision("ESCALATE", None, "provider.input_too_long", False),
        ),
        (failure("unavailable"), PolicyDecision("ESCALATE", None, "provider.unavailable", False)),
        # 2. unknown_choice failure -> DENY
        (failure("unknown_choice"), PolicyDecision("DENY", None, "policy.unknown_choice", False)),
        # 1. fallback on anything -> ESCALATE, flag carried
        (
            answer("billing", 1.0, fallback=True),
            PolicyDecision("ESCALATE", None, "policy.fallback_used", True),
        ),
        (
            answer("sales", 1.0, fallback=True),
            PolicyDecision("ESCALATE", None, "policy.fallback_used", True),
        ),
        (
            answer("billing", 0.1, fallback=True),
            PolicyDecision("ESCALATE", None, "policy.fallback_used", True),
        ),
        (
            failure("unknown_choice", fallback=True),
            PolicyDecision("ESCALATE", None, "policy.fallback_used", True),
        ),
        (
            failure("timeout", fallback=True),
            PolicyDecision("ESCALATE", None, "policy.fallback_used", True),
        ),
    ],
    ids=lambda value: getattr(value, "reason", None) or type(value).__name__,
)
def test_precedence_table(outcome: Outcome, expected: PolicyDecision) -> None:
    assert evaluate(outcome, POLICY) == expected


# --------------------------------------------------------------------------- #
# Threshold boundaries
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("threshold", "probability", "action"),
    [
        (0.9, 0.9, "ACT"),
        (0.9, 0.8999999999999999, "ABSTAIN"),
        (0.9, 0.9000000000000001, "ACT"),
        (0.9, 0.89, "ABSTAIN"),
        (0.9, 0.91, "ACT"),
        (1.0, 1.0, "ACT"),
        (1.0, 0.9999999999999999, "ABSTAIN"),
        (1e-300, 0.0, "ABSTAIN"),
        (1e-300, 1e-300, "ACT"),
        (1e-300, 5e-324, "ABSTAIN"),
        (5e-324, 5e-324, "ACT"),
        (0.5, 0.5, "ACT"),
        (0.5, 0.49999999999999994, "ABSTAIN"),
    ],
)
def test_threshold_equality_is_act_and_anything_below_abstains(
    threshold: float, probability: float, action: str
) -> None:
    policy = LockedPolicy(KNOWN, ALLOWED, threshold)
    decision = evaluate(answer("billing", probability), policy)
    assert decision.action == action
    if action == "ACT":
        assert decision == PolicyDecision("ACT", "billing", REASON_ALLOWED, False)
    else:
        assert decision == PolicyDecision("ABSTAIN", None, REASON_LOW_CONFIDENCE, False)


def test_gate_uses_the_selected_probability_not_the_argmax() -> None:
    """The CONTRACTS low_confidence fault: selected label mass 0, another known label mass 1."""
    outcome = ChoiceAnswer(
        "billing", (("billing", 0.0), ("technical", 1.0), ("sales", 0.0)), 0.0, None, (), False
    )
    assert evaluate(outcome, POLICY) == PolicyDecision(
        "ABSTAIN", None, REASON_LOW_CONFIDENCE, False
    )
    # The argmax label is allowed and confident, yet no substitution happens.
    assert evaluate(outcome, POLICY).choice is None


def test_single_allowed_label_policy() -> None:
    policy = LockedPolicy(KNOWN, ("technical",), 0.6)
    assert evaluate(answer("technical", 0.6), policy).action == "ACT"
    assert evaluate(answer("billing", 1.0), policy) == PolicyDecision(
        "DENY", None, REASON_DISALLOWED_CHOICE, False
    )
    assert evaluate(answer("sales", 1.0), policy).action == "DENY"


# --------------------------------------------------------------------------- #
# Cross-product invariants
# --------------------------------------------------------------------------- #

PROBABILITIES = (0.0, 0.25, 0.8999999999999999, 0.9, 0.9000000000000001, 1.0)
CHOICES = (*KNOWN, UNKNOWN)


@pytest.mark.parametrize(
    ("choice", "probability", "fallback", "confidence", "warnings"),
    list(itertools.product(CHOICES, PROBABILITIES, (False, True), CONFIDENCES, WARNINGS)),
)
def test_answer_cross_product(
    choice: str,
    probability: float,
    fallback: bool,
    confidence: float | None,
    warnings: tuple[str, ...],
) -> None:
    outcome = answer(
        choice, probability, fallback=fallback, confidence=confidence, warnings=warnings
    )
    decision = evaluate(outcome, POLICY)
    # Independently stated expectation for every cell.
    if fallback:
        expected = PolicyDecision("ESCALATE", None, REASON_FALLBACK_USED, True)
    elif choice not in ALLOWED:
        expected = PolicyDecision("DENY", None, REASON_DISALLOWED_CHOICE, False)
    elif probability < THRESHOLD:
        expected = PolicyDecision("ABSTAIN", None, REASON_LOW_CONFIDENCE, False)
    else:
        expected = PolicyDecision("ACT", choice, REASON_ALLOWED, False)
    assert decision == expected
    # Structural invariants.
    assert decision.fallback_used is outcome.fallback_used
    assert (decision.action == "ACT") == (decision.choice is not None)
    assert fallback is False or decision.action == "ESCALATE"
    # Provider confidence and warnings never change anything.
    neutral = answer(choice, probability, fallback=fallback)
    assert evaluate(neutral, POLICY) == decision


@pytest.mark.parametrize(
    ("code", "fallback", "warnings"),
    list(itertools.product(sorted(FAILURE_CODES), (False, True), WARNINGS)),
)
def test_failure_cross_product(code: str, fallback: bool, warnings: tuple[str, ...]) -> None:
    decision = evaluate(failure(code, fallback=fallback, warnings=warnings), POLICY)
    if fallback:
        expected = PolicyDecision("ESCALATE", None, REASON_FALLBACK_USED, True)
    elif code == "unknown_choice":
        expected = PolicyDecision("DENY", None, REASON_UNKNOWN_CHOICE, False)
    else:
        expected = PolicyDecision("ESCALATE", None, f"provider.{code}", False)
    assert decision == expected
    assert decision.choice is None
    assert decision.fallback_used is fallback


def test_every_failure_code_is_covered_by_the_cross_product() -> None:
    expected = {
        "timeout",
        "rate_limit",
        "provider_error",
        "malformed_response",
        "identity_mismatch",
        "unknown_choice",
        "input_too_long",
        "unavailable",
    }
    assert set(FAILURE_CODES) == expected


def test_vendor_confidence_cannot_rescue_or_demote_a_decision() -> None:
    low = answer("billing", 0.5, confidence=1.0)
    high = answer("billing", 0.95, confidence=0.0)
    disallowed = answer("sales", 1.0, confidence=1.0)
    assert evaluate(low, POLICY).action == "ABSTAIN"
    assert evaluate(high, POLICY) == PolicyDecision("ACT", "billing", REASON_ALLOWED, False)
    assert evaluate(disallowed, POLICY).action == "DENY"


def test_fallback_removes_act_authority_on_any_label_at_any_probability() -> None:
    for choice, probability in itertools.product(CHOICES, PROBABILITIES):
        decision = evaluate(answer(choice, probability, fallback=True), POLICY)
        assert decision == PolicyDecision("ESCALATE", None, REASON_FALLBACK_USED, True)
    for code in FAILURE_CODES:
        decision = evaluate(failure(code, fallback=True), POLICY)
        assert decision == PolicyDecision("ESCALATE", None, REASON_FALLBACK_USED, True)


def test_evaluate_is_pure_and_deterministic() -> None:
    outcome = answer("billing", 0.95, confidence=0.3, warnings=("w.a",))
    before = (outcome.choice, outcome.probabilities, outcome.selected_probability)
    decisions = {evaluate(outcome, POLICY) for _ in range(10)}
    assert len(decisions) == 1
    assert (outcome.choice, outcome.probabilities, outcome.selected_probability) == before
    assert make_policy() == POLICY


# --------------------------------------------------------------------------- #
# Argument validation
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "outcome",
    [
        None,
        "billing",
        {"choice": "billing"},
        PolicyDecision("ACT", "billing", "policy.allowed", False),
        ("billing", 0.95),
    ],
)
def test_evaluate_rejects_non_outcomes(outcome: object) -> None:
    with pytest.raises(SchemaError, match="outcome: must be ChoiceAnswer or ProviderFailure"):
        evaluate(outcome, POLICY)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "policy",
    [None, ("billing", "technical", "sales"), {"threshold": 0.9}, 0.9, make_policy().known_labels],
)
def test_evaluate_rejects_non_policies(policy: object) -> None:
    with pytest.raises(SchemaError, match="policy: must be LockedPolicy"):
        evaluate(answer("billing", 0.95), policy)  # type: ignore[arg-type]


def test_decisions_are_frozen_records() -> None:
    decision = evaluate(answer("billing", 0.95), POLICY)
    assert isinstance(decision, PolicyDecision)
    with pytest.raises(AttributeError):
        decision.action = "DENY"  # type: ignore[misc]
