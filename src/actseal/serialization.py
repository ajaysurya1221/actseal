"""Canonical JSON, strict parsing, record (de)serialization and fingerprinting.

Canonical JSON is UTF-8, ``ensure_ascii=False``, sorted keys, compact separators,
``allow_nan=False`` and no terminal newline. Strict parsing is bounded: it
rejects documents over 128 MiB (the generic ceiling; JSONL readers enforce 1 MiB
per row and the lock reader 32 MiB), nesting over 32, duplicate object keys at
any level, nonfinite numbers and invalid Unicode in keys or values. Record
conversion is table driven;
no class is imported or instantiated from wire data, and union outcomes carry an
explicit ``kind`` tag (``answer`` or ``failure``).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Final, TypeVar, cast

from actseal.errors import SchemaError
from actseal.records import (
    CapturedOutcome,
    Case,
    CaseRef,
    ChoiceAnswer,
    ChoiceQuestion,
    Contract,
    DecisionRecord,
    DecisionRequest,
    EvidenceBundle,
    FaultResult,
    FaultSpec,
    GateLimits,
    Interval,
    LockedPolicy,
    ModelIdentity,
    Option,
    PlanLock,
    PolicyDecision,
    ProviderFailure,
    Verdict,
)

__all__ = [
    "MAX_JSON_BYTES",
    "MAX_JSON_DEPTH",
    "canonical_json",
    "from_data",
    "implementation_fingerprint",
    "sha256_bytes",
    "strict_json_loads",
    "to_data",
]

MAX_JSON_BYTES: Final = 128 * 1024 * 1024
MAX_JSON_DEPTH: Final = 32

T = TypeVar(
    "T",
    bound=(
        Option
        | ChoiceQuestion
        | Case
        | CaseRef
        | ModelIdentity
        | DecisionRequest
        | CapturedOutcome
        | ChoiceAnswer
        | ProviderFailure
        | LockedPolicy
        | GateLimits
        | Contract
        | FaultSpec
        | PlanLock
        | PolicyDecision
        | DecisionRecord
        | FaultResult
        | Interval
        | Verdict
        | EvidenceBundle
    ),
)

_Pairs = tuple[tuple[str, str], ...]


# --------------------------------------------------------------------------- #
# Canonical JSON and hashing
# --------------------------------------------------------------------------- #


def _check_text(value: str, path: str) -> None:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise SchemaError(f"{path}: string must be valid Unicode") from None


def _check_json_value(value: object, path: str, depth: int) -> None:
    """Reject anything that is not a finite, well-formed JSON value.

    Paths are positional (``$[3]`` for array items, ``$.key[3]`` for the fourth
    object member) so diagnostics never echo untrusted keys or values.
    """
    if value is None or type(value) is bool or type(value) is int:
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise SchemaError(f"{path}: number must be finite")
        return
    if type(value) is str:
        _check_text(value, path)
        return
    if depth >= MAX_JSON_DEPTH:
        raise SchemaError(f"{path}: nesting exceeds {MAX_JSON_DEPTH}")
    if isinstance(value, list | tuple):
        for index, item in enumerate(value):
            _check_json_value(item, f"{path}[{index}]", depth + 1)
        return
    if type(value) is dict:
        for index, (key, item) in enumerate(value.items()):
            member = f"{path}.key[{index}]"
            if type(key) is not str:
                raise SchemaError(f"{member}: object keys must be strings")
            _check_text(key, member)
            _check_json_value(item, member, depth + 1)
        return
    raise SchemaError(f"{path}: unsupported value type")


def canonical_json(value: object) -> bytes:
    """Serialize a JSON value (not a record) to canonical UTF-8 bytes."""
    _check_json_value(value, "$", 0)
    try:
        text = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        return text.encode("utf-8")
    except (ValueError, OverflowError, TypeError, UnicodeEncodeError):
        # Integer-to-text conversion limits, surrogates or other encoder failures.
        raise SchemaError("$: value cannot be canonically encoded") from None


def sha256_bytes(data: bytes) -> str:
    """Return the lowercase hex SHA256 digest of ``data`` (``hashlib`` rejects text)."""
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------- #
# Strict parsing
# --------------------------------------------------------------------------- #


_STRUCTURAL: Final = re.compile(r'["\[\]{}]')
_STRING_CONTROL: Final = re.compile(r'["\\]')


def _scan_depth(text: str) -> None:
    """Reject nesting deeper than MAX_JSON_DEPTH before handing text to the parser.

    A two-state scan (outside/inside a string literal) advances a single cursor
    monotonically: outside strings it jumps to the next quote or bracket, inside
    strings to the next quote or backslash and skips the escaped character. Each
    character is visited at most once, so the cost is linear even for malformed
    or truncated input. Brackets inside string literals never count.
    """
    depth = 0
    position = 0
    length = len(text)
    while position < length:
        structural = _STRUCTURAL.search(text, position)
        if structural is None:
            return
        char = structural.group()
        position = structural.end()
        if char == '"':
            while True:
                control = _STRING_CONTROL.search(text, position)
                if control is None:
                    return  # unterminated string; json.loads reports the error
                position = control.end()
                if control.group() == "\\":
                    position += 1  # skip the escaped character
                else:
                    break
        elif char in "[{":
            depth += 1
            if depth > MAX_JSON_DEPTH:
                raise SchemaError(f"$: nesting exceeds {MAX_JSON_DEPTH}")
        else:
            depth -= 1


def _exceeds_byte_limit(text: str, limit: int) -> bool:
    """Whether the UTF-8 form of ``text`` is longer than ``limit`` bytes.

    The character count is a lower bound on the byte count, so oversized text is
    rejected before any encoding is allocated; ASCII text needs no encoding at
    all. Unpaired surrogates count as three bytes.
    """
    if len(text) > limit:
        return True
    if text.isascii():
        return False
    return len(text.encode("utf-8", errors="surrogatepass")) > limit


def _reject_constant(name: str) -> object:
    del name  # the constant name is one of NaN/Infinity/-Infinity; do not echo it
    raise SchemaError("$: nonfinite numbers are not allowed")


def _parse_float(text: str) -> float:
    number = float(text)
    if not math.isfinite(number):
        raise SchemaError("$: number must be finite")
    return number


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise SchemaError("$: duplicate object key")
        result[key] = value
    return result


def strict_json_loads(text: str) -> object:
    """Parse one JSON document under the bundle's size, depth and strictness limits."""
    if _exceeds_byte_limit(text, MAX_JSON_BYTES):
        raise SchemaError(f"$: document exceeds {MAX_JSON_BYTES} bytes")
    _scan_depth(text)
    try:
        value: object = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
            parse_float=_parse_float,
        )
    except SchemaError:
        raise
    except RecursionError:
        raise SchemaError(f"$: nesting exceeds {MAX_JSON_DEPTH}") from None
    except ValueError as exc:
        position = getattr(exc, "pos", None)
        where = f" at offset {position}" if isinstance(position, int) else ""
        raise SchemaError(f"$: invalid JSON{where}") from None
    _check_json_value(value, "$", 0)
    return value


# --------------------------------------------------------------------------- #
# Field codecs
# --------------------------------------------------------------------------- #


class _Codec:
    """Encode a validated record field to JSON data or decode JSON data for a constructor."""

    def encode(self, value: object) -> object:
        raise NotImplementedError

    def decode(self, value: object, path: str) -> object:
        raise NotImplementedError


class _Scalar(_Codec):
    def __init__(self, name: str, check: Callable[[object], bool]) -> None:
        self._name = name
        self._check = check

    def encode(self, value: object) -> object:
        return value

    def decode(self, value: object, path: str) -> object:
        if not self._check(value):
            raise SchemaError(f"{path}: expected {self._name}")
        return value


class _Float(_Codec):
    def encode(self, value: object) -> object:
        return float(cast(float, value))

    def decode(self, value: object, path: str) -> object:
        if type(value) is bool or not isinstance(value, int | float):
            raise SchemaError(f"{path}: expected number")
        return value


class _Optional(_Codec):
    def __init__(self, inner: _Codec) -> None:
        self._inner = inner

    def encode(self, value: object) -> object:
        return None if value is None else self._inner.encode(value)

    def decode(self, value: object, path: str) -> object:
        return None if value is None else self._inner.decode(value, path)


class _Array(_Codec):
    def __init__(self, inner: _Codec) -> None:
        self._inner = inner

    def encode(self, value: object) -> object:
        return [self._inner.encode(item) for item in cast(tuple[object, ...], value)]

    def decode(self, value: object, path: str) -> object:
        if type(value) is not list:
            raise SchemaError(f"{path}: expected array")
        return [self._inner.decode(item, f"{path}[{index}]") for index, item in enumerate(value)]


class _StringMap(_Codec):
    """``tuple[tuple[str, str], ...]`` as a JSON object; canonical form is key-sorted."""

    def encode(self, value: object) -> object:
        return dict(cast(_Pairs, value))

    def decode(self, value: object, path: str) -> object:
        if type(value) is not dict:
            raise SchemaError(f"{path}: expected object")
        pairs: list[tuple[str, object]] = []
        for index, (key, item) in enumerate(value.items()):
            if type(item) is not str:
                raise SchemaError(f"{path}[{index}]: expected string value")
            pairs.append((key, item))
        return pairs


class _Probabilities(_Codec):
    """Ordered ``[[label, probability], ...]`` pairs; order follows the question."""

    def encode(self, value: object) -> object:
        return [[label, float(probability)] for label, probability in cast(_PROBS, value)]

    def decode(self, value: object, path: str) -> object:
        if type(value) is not list:
            raise SchemaError(f"{path}: expected array")
        pairs: list[tuple[object, object]] = []
        for index, item in enumerate(value):
            if type(item) is not list or len(item) != _PAIR_LENGTH:
                raise SchemaError(f"{path}[{index}]: expected [label, probability] pair")
            pairs.append((item[0], item[1]))
        return pairs


class _Record(_Codec):
    def __init__(self, record_type: type[object]) -> None:
        self._record_type = record_type

    def encode(self, value: object) -> object:
        return _encode_record(value)

    def decode(self, value: object, path: str) -> object:
        return _decode_record(self._record_type, value, path)


class _OutcomeCodec(_Codec):
    """``ChoiceAnswer | ProviderFailure`` with an explicit ``kind`` discriminator."""

    def encode(self, value: object) -> object:
        data = _encode_record(value)
        data["kind"] = "answer" if isinstance(value, ChoiceAnswer) else "failure"
        return data

    def decode(self, value: object, path: str) -> object:
        if type(value) is not dict:
            raise SchemaError(f"{path}: expected object")
        kind = value.get("kind")
        record_type = _OUTCOME_KINDS.get(kind) if isinstance(kind, str) else None
        if record_type is None:
            raise SchemaError(f"{path}.kind: unsupported discriminator")
        body = {key: item for key, item in value.items() if key != "kind"}
        return _decode_record(record_type, body, path)


_PAIR_LENGTH: Final = 2
_PROBS = tuple[tuple[str, float], ...]

_STR = _Scalar("string", lambda value: type(value) is str)
_INT = _Scalar("integer", lambda value: type(value) is int)
_BOOL = _Scalar("boolean", lambda value: type(value) is bool)
_FLOAT = _Float()
_OPT_STR = _Optional(_STR)
_OPT_FLOAT = _Optional(_FLOAT)
_STR_ARRAY = _Array(_STR)
_STR_MAP = _StringMap()
_PROBABILITIES = _Probabilities()
_OUTCOME = _OutcomeCodec()

_OUTCOME_KINDS: Final[Mapping[str, type[object]]] = {
    "answer": ChoiceAnswer,
    "failure": ProviderFailure,
}

_SCHEMAS: Final[Mapping[type[object], tuple[tuple[str, _Codec], ...]]] = {
    Option: (("label", _STR), ("description", _STR)),
    ChoiceQuestion: (
        ("question_id", _STR),
        ("instructions", _STR),
        ("options", _Array(_Record(Option))),
    ),
    Case: (("case_id", _STR), ("state", _STR), ("expected_label", _STR)),
    CaseRef: (("case_id", _STR), ("sha256", _STR)),
    ModelIdentity: (
        ("provider", _STR),
        ("model", _STR),
        ("revision", _STR),
        ("artifact_hashes", _STR_MAP),
        ("adapter_version", _STR),
        ("normalizer_version", _STR),
        ("runtime", _STR_MAP),
    ),
    DecisionRequest: (
        ("case_id", _STR),
        ("state", _STR),
        ("question", _Record(ChoiceQuestion)),
    ),
    CapturedOutcome: (
        ("request_sha256", _STR),
        ("identity", _Record(ModelIdentity)),
        ("body_json", _OPT_STR),
        ("failure_code", _OPT_STR),
        ("warnings", _STR_ARRAY),
        ("fallback_used", _BOOL),
    ),
    ChoiceAnswer: (
        ("choice", _STR),
        ("probabilities", _PROBABILITIES),
        ("selected_probability", _FLOAT),
        ("provider_confidence", _OPT_FLOAT),
        ("warnings", _STR_ARRAY),
        ("fallback_used", _BOOL),
    ),
    ProviderFailure: (("code", _STR), ("warnings", _STR_ARRAY), ("fallback_used", _BOOL)),
    LockedPolicy: (
        ("known_labels", _STR_ARRAY),
        ("allowed_labels", _STR_ARRAY),
        ("threshold", _FLOAT),
    ),
    GateLimits: (("max_risk", _FLOAT), ("min_coverage", _FLOAT), ("alpha", _FLOAT)),
    Contract: (
        ("schema_version", _INT),
        ("name", _STR),
        ("question", _Record(ChoiceQuestion)),
        ("policy", _Record(LockedPolicy)),
        ("limits", _Record(GateLimits)),
        ("evidence_scope", _STR),
        ("population", _STR),
    ),
    FaultSpec: (("scenario_id", _STR), ("kind", _STR), ("expected_action", _STR)),
    PlanLock: (
        ("schema_version", _INT),
        ("contract", _Record(Contract)),
        ("model_identity", _Record(ModelIdentity)),
        ("calibration_sha256", _STR),
        ("verification_sha256", _STR),
        ("calibration_inventory", _Array(_Record(CaseRef))),
        ("verification_inventory", _Array(_Record(CaseRef))),
        ("verification_cases", _Array(_Record(Case))),
        ("fault_inventory", _Array(_Record(FaultSpec))),
        ("implementation_sha256", _STR),
        ("sha256", _STR),
    ),
    PolicyDecision: (
        ("action", _STR),
        ("choice", _OPT_STR),
        ("reason", _STR),
        ("fallback_used", _BOOL),
    ),
    DecisionRecord: (
        ("case_id", _STR),
        ("capture", _Record(CapturedOutcome)),
        ("outcome", _OUTCOME),
        ("decision", _Record(PolicyDecision)),
    ),
    FaultResult: (
        ("scenario_id", _STR),
        ("request", _Record(DecisionRequest)),
        ("capture", _Record(CapturedOutcome)),
        ("outcome", _OUTCOME),
        ("decision", _Record(PolicyDecision)),
    ),
    Interval: (("lower", _FLOAT), ("upper", _FLOAT)),
    Verdict: (
        ("status", _STR),
        ("reasons", _STR_ARRAY),
        ("total", _INT),
        ("accepted", _INT),
        ("errors", _INT),
        ("risk", _Record(Interval)),
        ("coverage", _Record(Interval)),
        ("evidence_scope", _STR),
        ("lock_sha256", _STR),
    ),
    EvidenceBundle: (
        ("lock", _Record(PlanLock)),
        ("calibration_jsonl", _STR),
        ("verification_jsonl", _STR),
        ("records", _Array(_Record(DecisionRecord))),
        ("faults", _Array(_Record(FaultResult))),
        ("verdict", _Record(Verdict)),
    ),
}


def _schema_for(record_type: type[object]) -> tuple[tuple[str, _Codec], ...]:
    schema = _SCHEMAS.get(record_type)
    if schema is None:
        raise SchemaError(f"{record_type.__name__}: unsupported record type")
    return schema


def _encode_record(record: object) -> dict[str, object]:
    schema = _schema_for(type(record))
    return {name: codec.encode(getattr(record, name)) for name, codec in schema}


def _decode_record(record_type: type[object], value: object, path: str) -> object:
    schema = _schema_for(record_type)
    if type(value) is not dict:
        raise SchemaError(f"{path}: expected object")
    expected = [name for name, _ in schema]
    missing = [name for name in expected if name not in value]
    if missing:
        raise SchemaError(f"{path}: missing fields {', '.join(missing)}")
    unknown = len(value) - len(expected)
    if unknown:
        raise SchemaError(f"{path}: {unknown} unknown field(s)")
    kwargs = {name: codec.decode(value[name], f"{path}.{name}") for name, codec in schema}
    try:
        return record_type(**kwargs)
    except SchemaError as exc:
        raise SchemaError(f"{path}.{exc}") from None


def to_data(record: object) -> dict[str, object]:
    """Convert a supported record into fresh JSON-compatible data."""
    if type(record) not in _SCHEMAS:
        raise SchemaError(f"{type(record).__name__}: unsupported record type")
    return _encode_record(record)


def from_data(record_type: type[T], value: object) -> T:
    """Validate JSON data against ``record_type``'s schema and construct it."""
    return cast(T, _decode_record(record_type, value, record_type.__name__))


# --------------------------------------------------------------------------- #
# Implementation fingerprint
# --------------------------------------------------------------------------- #


def _fingerprint_tree(package_dir: Path, package_name: str) -> str:
    """Hash every ``*.py`` under ``package_dir`` by relative path, without importing."""
    entries: dict[str, object] = {}
    for file in sorted(package_dir.rglob("*.py")):
        relative = file.relative_to(package_dir)
        if "__pycache__" in relative.parts or not file.is_file():
            continue
        entries[f"{package_name}/{relative.as_posix()}"] = sha256_bytes(file.read_bytes())
    return sha256_bytes(canonical_json(entries))


def implementation_fingerprint() -> str:
    """Identity of the installed actseal sources: a hash over sorted path -> source hash."""
    package_dir = Path(__file__).resolve().parent
    return _fingerprint_tree(package_dir, "actseal")
