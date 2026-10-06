"""The decision-model protocol (plan/CONTRACTS.md section 4).

A provider captures raw evidence; it never normalizes, retries, falls back or
authorizes an action. ``decide`` returns a :class:`CapturedOutcome` whose
``request_sha256`` is the canonical hash of the request, whose ``identity`` is
the provider's actual identity, and whose body/failure are exclusive. Setup
problems raise :class:`actseal.errors.ProviderSetupError`; captured failures
use the frozen failure codes.

This module imports nothing beyond the standard library and ``records``.
"""

from __future__ import annotations

from typing import Protocol

from actseal.records import CapturedOutcome, DecisionRequest, ModelIdentity

__all__ = ["DecisionModel"]


class DecisionModel(Protocol):
    """Sequential capture of locked decision requests against one resident model."""

    def identity(self) -> ModelIdentity:
        """The actual identity of the loaded model, fixed for the object's lifetime."""
        ...

    def decide(self, request: DecisionRequest, *, timeout_s: float) -> CapturedOutcome:
        """Capture one request within a finite positive deadline; never raise for a failure."""
        ...

    def close(self) -> None:
        """Release resources; idempotent and leaves no worker alive."""
        ...
