"""Pure, deterministic runtime policy evaluation.

``evaluate`` maps one normalized provider outcome and one locked policy to a
:class:`PolicyDecision` using the exact precedence frozen in plan/CONTRACTS.md
section 3:

1. any ``fallback_used`` outcome -> ESCALATE, ``policy.fallback_used``;
2. ``ProviderFailure`` ``unknown_choice`` -> DENY, ``policy.unknown_choice``;
3. any other ``ProviderFailure`` -> ESCALATE, ``provider.<failure_code>``;
4. a choice outside the allowed labels -> DENY, ``policy.disallowed_choice``;
5. ``selected_probability < threshold`` -> ABSTAIN, ``policy.low_confidence``;
6. otherwise ACT, ``policy.allowed``.

Only ACT carries a choice. The outcome's fallback flag is always carried into
the decision. Provider confidence, warnings and any provider-suggested action
never influence the result; the gate uses the normalized probability of the
provider's selected label only.
"""

from __future__ import annotations

from typing import Final

from actseal.errors import SchemaError
from actseal.records import (
    Action,
    ChoiceAnswer,
    LockedPolicy,
    Outcome,
    PolicyDecision,
    ProviderFailure,
)

__all__ = [
    "REASON_ALLOWED",
    "REASON_DISALLOWED_CHOICE",
    "REASON_FALLBACK_USED",
    "REASON_LOW_CONFIDENCE",
    "REASON_PROVIDER_PREFIX",
    "REASON_UNKNOWN_CHOICE",
    "evaluate",
]

REASON_FALLBACK_USED: Final = "policy.fallback_used"
REASON_UNKNOWN_CHOICE: Final = "policy.unknown_choice"
REASON_PROVIDER_PREFIX: Final = "provider."
REASON_DISALLOWED_CHOICE: Final = "policy.disallowed_choice"
REASON_LOW_CONFIDENCE: Final = "policy.low_confidence"
REASON_ALLOWED: Final = "policy.allowed"

_UNKNOWN_CHOICE_CODE: Final = "unknown_choice"


def _disposition(outcome: Outcome, policy: LockedPolicy) -> tuple[Action, str | None, str]:
    """Return ``(action, choice, reason)`` following the frozen precedence table."""
    if outcome.fallback_used:
        return "ESCALATE", None, REASON_FALLBACK_USED
    if isinstance(outcome, ProviderFailure):
        if outcome.code == _UNKNOWN_CHOICE_CODE:
            return "DENY", None, REASON_UNKNOWN_CHOICE
        return "ESCALATE", None, f"{REASON_PROVIDER_PREFIX}{outcome.code}"
    # allowed_labels is a validated subset of known_labels, so this single test
    # covers both unknown and known-but-disallowed choices.
    if outcome.choice not in policy.allowed_labels:
        return "DENY", None, REASON_DISALLOWED_CHOICE
    if outcome.selected_probability < policy.threshold:
        return "ABSTAIN", None, REASON_LOW_CONFIDENCE
    return "ACT", outcome.choice, REASON_ALLOWED


def evaluate(outcome: Outcome, policy: LockedPolicy) -> PolicyDecision:
    """Evaluate one normalized outcome against a locked policy."""
    if not isinstance(outcome, ChoiceAnswer | ProviderFailure):
        raise SchemaError("outcome: must be ChoiceAnswer or ProviderFailure")
    if not isinstance(policy, LockedPolicy):
        raise SchemaError("policy: must be LockedPolicy")
    action, choice, reason = _disposition(outcome, policy)
    return PolicyDecision(
        action=action,
        choice=choice,
        reason=reason,
        fallback_used=outcome.fallback_used,
    )
