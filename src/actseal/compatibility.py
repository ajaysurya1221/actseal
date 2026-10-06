"""Replay-engine compatibility and the reviewed implementation registry (v1.0, plan E).

A lock records two different facts about the code that produced it:

* ``implementation_sha256`` is **producer provenance**: the fingerprint of every
  installed ``actseal/**/*.py`` source file at collection time
  (:func:`actseal.serialization.implementation_fingerprint`).
* ``replay_engine_version`` names the **replay semantics** the evidence was
  produced under. The initial and only supported engine is
  ``actseal-choice-v1``: canonical encoding, policy precedence, normalizer
  behaviour, the six canonical faults and the Clopper-Pearson assessment.

Validation rules (applied by the shared :func:`actseal.locking.validate_lock`,
hence by ``validate_inputs``, ``assess``, ``write_bundle`` and ``replay``):

1. The lock's engine must be one of :data:`SUPPORTED_ENGINES`.
2. A lock whose producer fingerprint equals the running fingerprint is valid
   under its supported engine, with no registry lookup.
3. Otherwise **both** the producer fingerprint and the running fingerprint must
   be registered for exactly the lock's engine in the packaged
   :data:`REGISTRY_FILE`. One side alone is not enough.
4. New collection (``collect`` and ``verify_run``) additionally requires the
   exact running fingerprint: :func:`require_exact_implementation`.

The registry is a small packaged JSON document that lives beside this module
and is deliberately *outside* the implementation fingerprint (which hashes only
``*.py`` files). Its shape is ``{"schema_version": 1, "implementations":
{"<lowercase 64-hex source SHA-256>": "<engine>"}}``. The loader rejects
unknown fields, duplicate keys, malformed hashes, unsupported engines and any
wildcard or range form. Entries are added only by review with archived
evidence regression tests. The registry is trusted verifier configuration; it
is not proof that any bundle is authentic.

Schema-1 documents (actseal 0.1.0 locks and bundle manifests) are detected
before generic decoding so that callers receive :class:`LegacySchemaError` with
:data:`LEGACY_GUIDANCE` instead of a bare missing-field error. Legacy bytes are
never rewritten or resealed; historical evidence replays under an isolated,
pinned ``actseal==0.1.0``.

This module imports no adapter, transport or optional library.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from actseal.contract import read_input_text
from actseal.errors import IntegrityError, SchemaError
from actseal.records import PlanLock
from actseal.serialization import implementation_fingerprint, strict_json_loads

__all__ = [
    "CURRENT_ENGINE",
    "LEGACY_GUIDANCE",
    "MAX_REGISTRY_BYTES",
    "REGISTRY_FILE",
    "REGISTRY_SCHEMA_VERSION",
    "RELEASE_RECEIPT_SCHEMA_VERSION",
    "SUPPORTED_ENGINES",
    "CompatibilityRegistry",
    "LegacySchemaError",
    "check_replay_compatibility",
    "is_legacy_lock",
    "is_legacy_manifest",
    "load_registry",
    "parse_registry",
    "require_exact_implementation",
]

#: Engine recorded in every lock created by this release.
CURRENT_ENGINE: Final = "actseal-choice-v1"
#: Engines this release can replay. Adding one is a reviewed, documented change.
SUPPORTED_ENGINES: Final[frozenset[str]] = frozenset({CURRENT_ENGINE})
#: Schema version of the packaged compatibility registry document.
REGISTRY_SCHEMA_VERSION: Final = 1
#: Schema version of the release provenance receipt produced by release tooling.
RELEASE_RECEIPT_SCHEMA_VERSION: Final = 1
REGISTRY_FILE: Final = "compatibility_registry.json"
MAX_REGISTRY_BYTES: Final = 1024 * 1024

#: Operator guidance for schema-1 evidence; contains no input values.
LEGACY_GUIDANCE: Final = (
    "schema 1 locks and bundles were produced by actseal 0.1.0 and are not supported by "
    "this release; replay that evidence with an isolated pinned installation "
    "(for example `uvx actseal==0.1.0 replay DIRECTORY`) or start a new evaluation by "
    "creating a new lock; see docs/migration.md"
)

_LEGACY_LOCK_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "schema_version",
        "contract",
        "model_identity",
        "calibration_sha256",
        "verification_sha256",
        "calibration_inventory",
        "verification_inventory",
        "verification_cases",
        "fault_inventory",
        "implementation_sha256",
        "sha256",
    }
)
_LEGACY_MANIFEST_FIELDS: Final[frozenset[str]] = frozenset({"schema_version", "files", "sha256"})
_LEGACY_MANIFEST_FILES: Final[frozenset[str]] = frozenset(
    {
        "lock.json",
        "calibration.jsonl",
        "verification.jsonl",
        "records.jsonl",
        "faults.jsonl",
        "verdict.json",
    }
)
_LEGACY_SCHEMA_VERSION: Final = 1
_REGISTRY_KEYS: Final[frozenset[str]] = frozenset({"schema_version", "implementations"})
_SHA256_HEX: Final = re.compile(r"[0-9a-f]{64}")
_REGISTRY_PATH: Final = Path(__file__).resolve().parent / REGISTRY_FILE


class LegacySchemaError(SchemaError):
    """A document uses the retired schema 1 (actseal 0.1.0); see :data:`LEGACY_GUIDANCE`."""


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class CompatibilityRegistry:
    """Reviewed producer fingerprint -> replay engine approvals, sorted by fingerprint."""

    schema_version: int
    implementations: tuple[tuple[str, str], ...]

    def engine_for(self, implementation_sha256: str) -> str | None:
        """The approved engine for an exact producer fingerprint, or ``None``."""
        for fingerprint, engine in self.implementations:
            if fingerprint == implementation_sha256:
                return engine
        return None


def _exceeds_byte_limit(text: str, limit: int) -> bool:
    if len(text) > limit:
        return True
    if text.isascii():
        return False
    return len(text.encode("utf-8", errors="surrogatepass")) > limit


def parse_registry(text: str) -> CompatibilityRegistry:
    """Strictly decode a registry document; every defect is :class:`SchemaError`.

    Exactly the keys ``schema_version`` (the integer 1, never a boolean) and
    ``implementations`` (an object, possibly empty, whose keys are lowercase
    64-character SHA-256 hex and whose values are supported engine names).
    Duplicate keys, nonfinite numbers and nesting defects are rejected by the
    strict JSON parser. Messages never echo keys or values.
    """
    if not isinstance(text, str):
        raise SchemaError("compatibility_registry: must be text")
    if _exceeds_byte_limit(text, MAX_REGISTRY_BYTES):
        raise SchemaError(f"compatibility_registry: document exceeds {MAX_REGISTRY_BYTES} bytes")
    value = strict_json_loads(text)
    if type(value) is not dict:
        raise SchemaError("compatibility_registry: expected object")
    if set(value) != _REGISTRY_KEYS:
        raise SchemaError(
            "compatibility_registry: expected exactly schema_version, implementations"
        )
    version = value["schema_version"]
    if type(version) is not int:
        raise SchemaError("compatibility_registry.schema_version: expected integer")
    if version != REGISTRY_SCHEMA_VERSION:
        raise SchemaError("compatibility_registry.schema_version: unsupported schema version")
    implementations = value["implementations"]
    if type(implementations) is not dict:
        raise SchemaError("compatibility_registry.implementations: expected object")
    pairs: list[tuple[str, str]] = []
    for index, (fingerprint, engine) in enumerate(implementations.items()):
        if _SHA256_HEX.fullmatch(fingerprint) is None:
            raise SchemaError(
                f"compatibility_registry.implementations[{index}]: "
                "keys must be lowercase 64-character SHA256 hex"
            )
        if type(engine) is not str or engine not in SUPPORTED_ENGINES:
            raise SchemaError(
                f"compatibility_registry.implementations[{index}]: unsupported replay engine"
            )
        pairs.append((fingerprint, engine))
    return CompatibilityRegistry(version, tuple(sorted(pairs)))


def load_registry() -> CompatibilityRegistry:
    """Read and strictly decode the packaged registry beside this module.

    The file is read on every call (it is tiny and only consulted when a lock's
    producer fingerprint differs from the running one). An unreadable file is
    :class:`SchemaError` naming the registry, not the path.
    """
    try:
        text = read_input_text(_REGISTRY_PATH, limit=MAX_REGISTRY_BYTES)
    except OSError:
        raise SchemaError("compatibility_registry: unavailable") from None
    return parse_registry(text)


# --------------------------------------------------------------------------- #
# Lock validation rules
# --------------------------------------------------------------------------- #


def _check_lock(lock: object) -> PlanLock:
    if not isinstance(lock, PlanLock):
        raise SchemaError("lock: must be PlanLock")
    return lock


def check_replay_compatibility(
    lock: PlanLock, *, registry: CompatibilityRegistry | None = None
) -> None:
    """Rules 1-3 above: supported engine, then exact source or dual registration.

    ``registry`` defaults to the packaged registry, loaded only when the producer
    fingerprint differs from the running fingerprint. An unsupported engine or a
    fingerprint that is neither current nor approved for that engine on *both*
    sides is :class:`IntegrityError`.
    """
    checked = _check_lock(lock)
    if checked.replay_engine_version not in SUPPORTED_ENGINES:
        raise IntegrityError("replay_engine_version: unsupported replay engine")
    current = implementation_fingerprint()
    if checked.implementation_sha256 == current:
        return
    approved = load_registry() if registry is None else registry
    engine = checked.replay_engine_version
    if (
        approved.engine_for(checked.implementation_sha256) != engine
        or approved.engine_for(current) != engine
    ):
        raise IntegrityError(
            "implementation_sha256: does not match the current implementation or an "
            "approved compatible implementation for its replay engine"
        )


def require_exact_implementation(lock: PlanLock) -> None:
    """Rule 4: new collection needs the exact running fingerprint, registry or not."""
    checked = _check_lock(lock)
    if checked.implementation_sha256 != implementation_fingerprint():
        raise IntegrityError(
            "implementation_sha256: new collection requires the exact current implementation"
        )


# --------------------------------------------------------------------------- #
# Legacy (schema 1) detection
# --------------------------------------------------------------------------- #


def _is_legacy_version(value: object) -> bool:
    return type(value) is int and value == _LEGACY_SCHEMA_VERSION


def is_legacy_lock(value: object) -> bool:
    """Whether decoded JSON has exactly the eleven actseal 0.1.0 lock fields at version 1."""
    return (
        type(value) is dict
        and set(value) == _LEGACY_LOCK_FIELDS
        and _is_legacy_version(value["schema_version"])
    )


def is_legacy_manifest(value: object) -> bool:
    """Whether decoded JSON is an actseal 0.1.0 bundle manifest over the six data files."""
    if type(value) is not dict or set(value) != _LEGACY_MANIFEST_FIELDS:
        return False
    files = value["files"]
    return (
        _is_legacy_version(value["schema_version"])
        and type(files) is dict
        and set(files) == _LEGACY_MANIFEST_FILES
    )
