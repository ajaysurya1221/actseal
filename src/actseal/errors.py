"""Public exception hierarchy for Actseal.

Messages name the failing field, path or invariant. They never include source
values, raw provider bodies, credentials or arbitrary exception text.
"""

from __future__ import annotations

__all__ = ["ActsealError", "IntegrityError", "ProviderSetupError", "SchemaError"]


class ActsealError(Exception):
    """Base class for all Actseal errors."""


class SchemaError(ActsealError):
    """A record, wire document or value violates the frozen schema."""


class IntegrityError(ActsealError):
    """A hash, seal, inventory or replay check does not match its evidence."""


class ProviderSetupError(ActsealError):
    """A decision model could not be prepared for use."""
