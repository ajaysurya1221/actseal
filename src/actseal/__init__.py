"""Actseal: verify frozen categorical decision policies with sealed, replayable evidence.

The runtime core depends only on the Python standard library. Importing this
package never imports an optional model stack.
"""

from __future__ import annotations

from actseal.errors import ActsealError, IntegrityError, ProviderSetupError, SchemaError
from actseal.records import (
    Action,
    CapturedOutcome,
    Case,
    CaseRef,
    ChoiceAnswer,
    ChoiceQuestion,
    Contract,
    DecisionRecord,
    DecisionRequest,
    EvidenceBundle,
    EvidenceScope,
    FaultResult,
    FaultSpec,
    GateLimits,
    Interval,
    LockedPolicy,
    ModelIdentity,
    Option,
    Outcome,
    PlanLock,
    PolicyDecision,
    ProviderFailure,
    Status,
    Verdict,
)
from actseal.serialization import (
    canonical_json,
    from_data,
    implementation_fingerprint,
    sha256_bytes,
    strict_json_loads,
    to_data,
)

__version__ = "1.0.1"

__all__ = [
    "Action",
    "ActsealError",
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
    "IntegrityError",
    "Interval",
    "LockedPolicy",
    "ModelIdentity",
    "Option",
    "Outcome",
    "PlanLock",
    "PolicyDecision",
    "ProviderFailure",
    "ProviderSetupError",
    "SchemaError",
    "Status",
    "Verdict",
    "__version__",
    "canonical_json",
    "from_data",
    "implementation_fingerprint",
    "sha256_bytes",
    "strict_json_loads",
    "to_data",
]
