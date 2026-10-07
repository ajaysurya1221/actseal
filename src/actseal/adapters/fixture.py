"""Recorded-response fixture adapter.

The fixture file is JSONL with rows ``{case_id, body_json, failure_code,
warnings}``; ``body_json`` is a string (the recorded inner answer object, see
docs/providers.md), exactly one of ``body_json``/``failure_code`` is present,
and ``warnings`` is a list of nonempty strings. Rows are at most 1 MiB each and
the whole file at most 128 MiB (ADR 0011), enforced with a bounded read of at
most limit+1 bytes before decoding, splitting or hashing.
The file supplies no identity: the identity is derived from the raw file bytes
so that any change to the recording changes the revision.

A requested case that is not in the file is a :class:`ProviderSetupError`,
never a skip. Captures are deterministic and carry ``fallback_used=False``.
"""

from __future__ import annotations

import math
from collections.abc import Iterator
from pathlib import Path
from typing import Final

from actseal.errors import ProviderSetupError, SchemaError
from actseal.normalization import NORMALIZER_VERSION, request_sha256
from actseal.records import (
    FAILURE_CODES,
    CapturedOutcome,
    DecisionRequest,
    ModelIdentity,
)
from actseal.serialization import sha256_bytes, strict_json_loads

__all__ = [
    "ADAPTER_VERSION",
    "MAX_FIXTURE_BYTES",
    "MAX_ROW_BYTES",
    "MODEL_NAME",
    "FixtureModel",
    "validate_timeout",
]

ADAPTER_VERSION: Final = "1"
MODEL_NAME: Final = "recorded-choice-v1"
MAX_ROW_BYTES: Final = 1024 * 1024
MAX_FIXTURE_BYTES: Final = 128 * 1024 * 1024
_ROW_KEYS: Final[frozenset[str]] = frozenset({"case_id", "body_json", "failure_code", "warnings"})


def validate_timeout(timeout_s: object) -> float:
    """Return ``timeout_s`` as a finite positive float or raise :class:`SchemaError`."""
    if type(timeout_s) is bool or not isinstance(timeout_s, int | float):
        raise SchemaError("timeout_s: must be a number")
    try:
        value = float(timeout_s)
    except OverflowError:
        raise SchemaError("timeout_s: must be finite") from None
    if not math.isfinite(value) or value <= 0.0:
        raise SchemaError("timeout_s: must be a finite positive number")
    return value


class _Row:
    __slots__ = ("body_json", "failure_code", "warnings")

    def __init__(
        self, body_json: str | None, failure_code: str | None, warnings: tuple[str, ...]
    ) -> None:
        self.body_json = body_json
        self.failure_code = failure_code
        self.warnings = warnings


def _parse_row(index: int, text: str) -> tuple[str, _Row]:
    path = f"responses[{index}]"
    if len(text.encode("utf-8")) > MAX_ROW_BYTES:
        raise SchemaError(f"{path}: row exceeds {MAX_ROW_BYTES} bytes")
    try:
        value = strict_json_loads(text)
    except SchemaError as exc:
        raise SchemaError(f"{path}: {exc}") from None
    if type(value) is not dict:
        raise SchemaError(f"{path}: expected object")
    if set(value) != _ROW_KEYS:
        raise SchemaError(f"{path}: expected exactly case_id, body_json, failure_code, warnings")
    case_id = value["case_id"]
    if type(case_id) is not str or not case_id:
        raise SchemaError(f"{path}.case_id: must be a nonempty string")
    body = value["body_json"]
    failure = value["failure_code"]
    if body is not None and type(body) is not str:
        raise SchemaError(f"{path}.body_json: must be a string or null")
    if failure is not None and (type(failure) is not str or failure not in FAILURE_CODES):
        raise SchemaError(f"{path}.failure_code: unsupported value")
    if (body is None) == (failure is None):
        raise SchemaError(f"{path}: exactly one of body_json/failure_code must be present")
    warnings = value["warnings"]
    if type(warnings) is not list or any(type(w) is not str or not w for w in warnings):
        raise SchemaError(f"{path}.warnings: must be a list of nonempty strings")
    return case_id, _Row(body, failure, tuple(warnings))


def _iter_lines(text: str) -> Iterator[str]:
    """Yield lines split on LF only; one terminating LF is a terminator, not an empty row.

    Lines are produced one at a time so a newline-heavy file never materialises
    a list of every line before the first one is checked.
    """
    start = 0
    end = len(text)
    while start < end:
        stop = text.find("\n", start)
        if stop < 0:
            yield text[start:]
            return
        yield text[start:stop]
        start = stop + 1


def _parse_rows(data: bytes) -> dict[str, _Row]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise SchemaError("responses: must be valid UTF-8") from None
    rows: dict[str, _Row] = {}
    for index, line in enumerate(_iter_lines(text)):
        case_id, row = _parse_row(index, line)
        if case_id in rows:
            raise SchemaError(f"responses[{index}].case_id: duplicate case id")
        rows[case_id] = row
    if not rows:
        raise SchemaError("responses: must contain at least one row")
    return rows


class FixtureModel:
    """Replay recorded provider responses keyed by case id."""

    def __init__(self, responses: Path) -> None:
        if not isinstance(responses, Path):
            raise SchemaError("responses: must be a Path")
        try:
            with responses.open("rb") as handle:
                data = handle.read(MAX_FIXTURE_BYTES + 1)
        except OSError:
            raise ProviderSetupError("responses: fixture file could not be read") from None
        if len(data) > MAX_FIXTURE_BYTES:
            raise SchemaError(f"responses: file exceeds {MAX_FIXTURE_BYTES} bytes")
        self._rows = _parse_rows(data)
        file_hash = sha256_bytes(data)
        self._identity = ModelIdentity(
            "fixture",
            MODEL_NAME,
            file_hash,
            (("responses", file_hash),),
            ADAPTER_VERSION,
            NORMALIZER_VERSION,
            (),
        )

    def identity(self) -> ModelIdentity:
        return self._identity

    def decide(self, request: DecisionRequest, *, timeout_s: float) -> CapturedOutcome:
        validate_timeout(timeout_s)
        if not isinstance(request, DecisionRequest):
            raise SchemaError("request: must be DecisionRequest")
        row = self._rows.get(request.case_id)
        if row is None:
            raise ProviderSetupError("responses: requested case id is not recorded")
        return CapturedOutcome(
            request_sha256(request),
            self._identity,
            row.body_json,
            row.failure_code,
            row.warnings,
            fallback_used=False,
        )

    def close(self) -> None:
        """Nothing to release; recorded responses stay available until the object is dropped."""
        return
