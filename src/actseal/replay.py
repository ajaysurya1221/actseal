"""Semantic offline replay of an evidence bundle (plan/CONTRACTS.md section 6, ADR 0005/0012).

``replay`` re-derives a verdict from bundle *data* with the accepted pure
authorities and never returns the archived verdict on trust. It imports only
records, serialization, contracts, locking, normalization, policy, fault
generation, assessment and the evidence reader: no adapter, optional
dependency, bundle-supplied module, environment or provider is ever loaded,
and no bundle content is executed.

Stages, each ending the replay with an ERROR verdict when it fails:

1. **Structure.** Directory shape, symlink/regular-file checks, per-file and
   aggregate size ceilings before any content is read, strict manifest
   decoding, manifest self-hash and per-file hashes
   (``integrity.bundle_io``/``bundle_schema``/``bundle_hash``).
2. **Lock decoding.** Strict structural decoding of ``lock.json`` in its exact
   canonical form (``integrity.lock_schema``). Until this succeeds the ERROR
   carries ``evidence_scope='demo'`` and a 64-zero ``lock_sha256`` sentinel:
   an explicitly unknown identity (ADR 0012). From here on every verdict
   carries the *decoded* scope and seal, never the expected external digest.
3. **Identity.** The optional externally trusted lock digest must equal the
   decoded seal (``integrity.expected_lock``); ``validate_lock`` checks the
   seal, current implementation fingerprint, frozen fault inventory and case
   coherence (``integrity.lock``); ``validate_inputs`` checks both raw dataset
   byte hashes, inventories and literal leakage (``integrity.inputs``).
4. **Records.** Strict canonical decoding of records, faults and the stored
   verdict with the frozen row limits (``integrity.records_schema``,
   ``integrity.faults_schema``, ``integrity.verdict_schema``).
5. **Semantics.** ``assess`` rebuilds every request from the locked cases,
   checks capture hashes, re-normalizes every raw body against the locked
   identity, re-evaluates the policy, compares every outcome and decision,
   checks the six canonical fault captures, applies ADR 0009 and recomputes
   the statistics. Its verdict must equal the stored one exactly
   (``integrity.verdict``); otherwise the fresh verdict is returned.

A wholly rewritten, internally consistent bundle cannot be detected here: an
author who recomputes every hash, outcome and verdict produces a bundle that
replays cleanly. Only a separately trusted expected lock digest anchors the
locked identity, and it authenticates neither responses nor execution
(ADR 0005). Python argument-type misuse raises :class:`SchemaError`.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Final

from actseal.assessment import REASON_INTEGRITY_PREFIX, assess
from actseal.errors import ActsealError, IntegrityError, SchemaError
from actseal.evidence import (
    CALIBRATION_FILE,
    FAULTS_FILE,
    LOCK_FILE,
    RECORDS_FILE,
    VERDICT_FILE,
    VERIFICATION_FILE,
    decode_document,
    decode_rows,
    read_bundle_files,
)
from actseal.locking import parse_lock, validate_inputs, validate_lock
from actseal.records import (
    DecisionRecord,
    EvidenceScope,
    FaultResult,
    Interval,
    PlanLock,
    Verdict,
)
from actseal.serialization import canonical_json, to_data

__all__ = [
    "REASON_BUNDLE_HASH",
    "REASON_BUNDLE_IO",
    "REASON_BUNDLE_SCHEMA",
    "REASON_EXPECTED_LOCK",
    "REASON_FAULTS_SCHEMA",
    "REASON_INPUTS",
    "REASON_LOCK",
    "REASON_LOCK_SCHEMA",
    "REASON_RECORDS_SCHEMA",
    "REASON_VERDICT",
    "REASON_VERDICT_SCHEMA",
    "UNKNOWN_LOCK_SHA256",
    "UNKNOWN_SCOPE",
    "replay",
]

REASON_BUNDLE_IO: Final = f"{REASON_INTEGRITY_PREFIX}bundle_io"
REASON_BUNDLE_SCHEMA: Final = f"{REASON_INTEGRITY_PREFIX}bundle_schema"
REASON_BUNDLE_HASH: Final = f"{REASON_INTEGRITY_PREFIX}bundle_hash"
REASON_LOCK_SCHEMA: Final = f"{REASON_INTEGRITY_PREFIX}lock_schema"
REASON_EXPECTED_LOCK: Final = f"{REASON_INTEGRITY_PREFIX}expected_lock"
REASON_LOCK: Final = f"{REASON_INTEGRITY_PREFIX}lock"
REASON_INPUTS: Final = f"{REASON_INTEGRITY_PREFIX}inputs"
REASON_RECORDS_SCHEMA: Final = f"{REASON_INTEGRITY_PREFIX}records_schema"
REASON_FAULTS_SCHEMA: Final = f"{REASON_INTEGRITY_PREFIX}faults_schema"
REASON_VERDICT_SCHEMA: Final = f"{REASON_INTEGRITY_PREFIX}verdict_schema"
REASON_VERDICT: Final = f"{REASON_INTEGRITY_PREFIX}verdict"

#: ADR 0012 sentinel for an ERROR raised before the lock could be decoded.
UNKNOWN_LOCK_SHA256: Final = "0" * 64
UNKNOWN_SCOPE: Final[EvidenceScope] = "demo"

_SHA256_HEX: Final = re.compile(r"[0-9a-f]{64}")
_FULL: Final = (0.0, 1.0)


class _InvalidEvidenceError(Exception):
    """Internal control flow: a stage failed; carries the ERROR verdict (never escapes)."""

    def __init__(self, verdict: Verdict) -> None:
        super().__init__(verdict.status)
        self.verdict = verdict


def _error(reasons: set[str], scope: EvidenceScope, lock_sha256: str) -> _InvalidEvidenceError:
    return _InvalidEvidenceError(
        Verdict(
            "ERROR",
            tuple(sorted(reasons)),
            0,
            0,
            0,
            Interval(*_FULL),
            Interval(*_FULL),
            scope,
            lock_sha256,
        )
    )


def _unknown_error(reason: str) -> _InvalidEvidenceError:
    return _error({reason}, UNKNOWN_SCOPE, UNKNOWN_LOCK_SHA256)


def _lock_error(lock: PlanLock, reasons: set[str]) -> _InvalidEvidenceError:
    return _error(reasons, lock.contract.evidence_scope, lock.sha256)


def _check_arguments(bundle: object, expected_lock_sha256: object) -> None:
    if not isinstance(bundle, Path):
        raise SchemaError("bundle: must be a Path")
    if "\x00" in os.fspath(bundle):
        # A NUL cannot reach the operating system intact; this is Python argument
        # misuse (SchemaError), not evidence about any bundle.
        raise SchemaError("bundle: must not contain NUL")
    if expected_lock_sha256 is not None and (
        type(expected_lock_sha256) is not str or _SHA256_HEX.fullmatch(expected_lock_sha256) is None
    ):
        raise SchemaError("expected_lock_sha256: must be lowercase 64-character SHA256 hex")


def _load_files(bundle: Path) -> dict[str, bytes]:
    """Stage 1: bounded inspection, manifest decoding and hash verification."""
    try:
        return read_bundle_files(bundle)
    except OSError:
        raise _unknown_error(REASON_BUNDLE_IO) from None
    except IntegrityError:
        raise _unknown_error(REASON_BUNDLE_HASH) from None
    except SchemaError:
        raise _unknown_error(REASON_BUNDLE_SCHEMA) from None


def _parse_canonical_lock(data: bytes) -> PlanLock:
    lock = parse_lock(data.decode("utf-8"))
    if canonical_json(to_data(lock)) + b"\n" != data:
        raise SchemaError(f"{LOCK_FILE}: must be canonical JSON with one terminal LF")
    return lock


def _decode_lock(data: bytes) -> PlanLock:
    """Stage 2: strict structural decoding (seal untouched) of the exact canonical document."""
    try:
        return _parse_canonical_lock(data)
    except SchemaError:
        raise _unknown_error(REASON_LOCK_SCHEMA) from None


def _check_identity(
    lock: PlanLock, files: dict[str, bytes], expected_lock_sha256: str | None
) -> None:
    """Stage 3: external digest, self-seal/implementation/inventories, raw inputs."""
    failures: set[str] = set()
    if expected_lock_sha256 is not None and expected_lock_sha256 != lock.sha256:
        failures.add(REASON_EXPECTED_LOCK)
    try:
        validate_lock(lock)
    except ActsealError:
        failures.add(REASON_LOCK)
    if failures:
        raise _lock_error(lock, failures)
    try:
        validate_inputs(
            lock,
            files[CALIBRATION_FILE].decode("utf-8"),
            files[VERIFICATION_FILE].decode("utf-8"),
        )
    except ActsealError:
        raise _lock_error(lock, {REASON_INPUTS}) from None


def _decode_evidence(
    lock: PlanLock, files: dict[str, bytes]
) -> tuple[tuple[DecisionRecord, ...], tuple[FaultResult, ...], Verdict]:
    """Stage 4: strict canonical decoding of records, faults and the stored verdict."""
    failures: set[str] = set()
    records: tuple[DecisionRecord, ...] = ()
    faults: tuple[FaultResult, ...] = ()
    stored: Verdict | None = None
    try:
        records = decode_rows(RECORDS_FILE, files[RECORDS_FILE], DecisionRecord)
    except SchemaError:
        failures.add(REASON_RECORDS_SCHEMA)
    try:
        faults = decode_rows(FAULTS_FILE, files[FAULTS_FILE], FaultResult)
    except SchemaError:
        failures.add(REASON_FAULTS_SCHEMA)
    try:
        stored = decode_document(VERDICT_FILE, files[VERDICT_FILE], Verdict)
    except SchemaError:
        failures.add(REASON_VERDICT_SCHEMA)
    if failures or stored is None:
        raise _lock_error(lock, failures)
    return records, faults, stored


def _reassess(
    lock: PlanLock,
    records: tuple[DecisionRecord, ...],
    faults: tuple[FaultResult, ...],
    stored: Verdict,
) -> Verdict:
    """Stage 5: fresh reconstruction and assessment, compared exactly with the stored verdict."""
    recomputed = assess(records, lock, faults)
    if recomputed != stored:
        reasons = set(recomputed.reasons) if recomputed.status == "ERROR" else set()
        reasons.add(REASON_VERDICT)
        raise _lock_error(lock, reasons)
    return recomputed


def replay(bundle: Path, *, expected_lock_sha256: str | None = None) -> Verdict:
    """Recompute the verdict of the bundle directory ``bundle`` from its data alone.

    Returns the freshly assessed verdict when every structural, identity and
    semantic check passes and the stored verdict equals it; otherwise an ERROR
    verdict whose reasons name the failed invariants. ``expected_lock_sha256``,
    when supplied, must equal the decoded lock seal; it is never reported as
    the observed identity.
    """
    _check_arguments(bundle, expected_lock_sha256)
    try:
        files = _load_files(bundle)
        lock = _decode_lock(files[LOCK_FILE])
        _check_identity(lock, files, expected_lock_sha256)
        records, faults, stored = _decode_evidence(lock, files)
        return _reassess(lock, records, faults, stored)
    except _InvalidEvidenceError as invalid:
        return invalid.verdict
