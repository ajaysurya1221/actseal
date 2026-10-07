"""Strict parsing of the Actseal contract TOML and JSONL case datasets.

The TOML shape is exact (plan/CONTRACTS.md section 3): top-level
``schema_version``, ``name``, ``evidence_scope``, ``population`` and the
``[question]``, ``[policy]`` and ``[risk]`` tables. Unknown keys, missing
keys, wrong types (including booleans where numbers are required), nonfinite
numbers and unsupported versions are :class:`SchemaError`. ``known_labels``
is derived from the ordered question options and can never be configured.
The ``[risk]`` table populates ``Contract.limits``; diagnostics therefore
name ``Contract.limits``.

JSONL datasets hold exactly ``case_id``, ``state`` and ``expected_label`` per
line, all strings. Readers decode raw bytes as strict UTF-8 without newline
translation and never repair case, whitespace or line endings, so re-encoding
the returned text recovers the exact bytes hashed by the lock. Rows are
limited to 1 MiB each, documents to the generic 128 MiB ceiling and splits to
10,000 cases. Duplicate IDs and exact duplicate state texts are rejected
within one split; cross-split checks live in :mod:`actseal.locking`.
"""

from __future__ import annotations

import tomllib
from collections.abc import Iterator
from pathlib import Path
from typing import Final

from actseal.errors import SchemaError
from actseal.records import MAX_CASES_PER_SPLIT, Case, ChoiceQuestion, Contract
from actseal.serialization import MAX_JSON_BYTES, from_data, strict_json_loads

__all__ = ["MAX_ROW_BYTES", "parse_cases", "parse_contract", "read_input_text"]

MAX_ROW_BYTES: Final = 1024 * 1024

_TOP_FIELDS: Final = (
    "schema_version",
    "name",
    "evidence_scope",
    "population",
    "question",
    "policy",
    "risk",
)
_POLICY_FIELDS: Final = ("allowed_labels", "threshold")


# --------------------------------------------------------------------------- #
# Raw input
# --------------------------------------------------------------------------- #


def _exceeds_byte_limit(text: str, limit: int) -> bool:
    """Whether the UTF-8 form of ``text`` is longer than ``limit`` bytes.

    The character count is a lower bound on the byte count, so oversized text
    is rejected before any encoding is allocated. Unpaired surrogates count as
    three bytes; strict parsing rejects them later.
    """
    if len(text) > limit:
        return True
    if text.isascii():
        return False
    return len(text.encode("utf-8", errors="surrogatepass")) > limit


def read_input_text(path: Path, *, limit: int = MAX_JSON_BYTES) -> str:
    """Read ``path`` as exact UTF-8 text, never buffering more than ``limit`` + 1 bytes.

    ``limit`` must be a plain positive integer at most ``MAX_JSON_BYTES``; the
    read is bounded *before* allocation, so an oversized file is rejected after
    at most ``limit + 1`` bytes are requested from the stream. No BOM stripping,
    no universal-newline translation, no error replacement:
    ``result.encode("utf-8")`` reproduces the file bytes. Oversized files, bad
    limits and files that are not valid UTF-8 are :class:`SchemaError`.
    Operating-system errors propagate unchanged.
    """
    if type(limit) is not int or not 1 <= limit <= MAX_JSON_BYTES:
        raise SchemaError(f"limit: must be an integer in [1, {MAX_JSON_BYTES}]")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise SchemaError(f"input: file exceeds {limit} bytes")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        raise SchemaError("input: file must be valid UTF-8") from None


# --------------------------------------------------------------------------- #
# Contract TOML
# --------------------------------------------------------------------------- #


def _exact_table(path: str, value: object, fields: tuple[str, ...]) -> dict[str, object]:
    if type(value) is not dict:
        raise SchemaError(f"{path}: expected table")
    missing = [name for name in fields if name not in value]
    if missing:
        raise SchemaError(f"{path}: missing fields {', '.join(missing)}")
    unknown = len(value) - len(fields)
    if unknown:
        raise SchemaError(f"{path}: {unknown} unknown field(s)")
    return value


def _option_labels(question: object) -> list[object]:
    """Best-effort ordered option labels for ``known_labels`` derivation.

    Any structural problem yields an empty list; the subsequent strict decode
    of the whole contract reports the question error first because fields are
    decoded in schema order.
    """
    if type(question) is not dict or type(question.get("options")) is not list:
        return []
    labels: list[object] = []
    for option in question["options"]:
        if type(option) is not dict or "label" not in option:
            return []
        labels.append(option["label"])
    return labels


def _load_toml(text: str) -> object:
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        raise SchemaError("Contract: invalid TOML") from None
    except RecursionError:
        raise SchemaError("Contract: nesting too deep") from None


def parse_contract(path: Path) -> Contract:
    """Parse the exact contract TOML at ``path`` into a validated :class:`Contract`."""
    document = _load_toml(read_input_text(path))
    top = _exact_table("Contract", document, _TOP_FIELDS)
    policy = _exact_table("Contract.policy", top["policy"], _POLICY_FIELDS)
    data: dict[str, object] = {
        "schema_version": top["schema_version"],
        "name": top["name"],
        "question": top["question"],
        "policy": {
            "known_labels": _option_labels(top["question"]),
            "allowed_labels": policy["allowed_labels"],
            "threshold": policy["threshold"],
        },
        "limits": top["risk"],
        "evidence_scope": top["evidence_scope"],
        "population": top["population"],
    }
    return from_data(Contract, data)


# --------------------------------------------------------------------------- #
# JSONL cases
# --------------------------------------------------------------------------- #


def _iter_rows(text: str) -> Iterator[str]:
    """Yield rows split on LF only; one terminating LF is a terminator, not an empty row.

    Rows are produced one at a time, so a newline-heavy document never
    materialises a list of every row before the first row is checked.
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


def _parse_row(index: int, row: str) -> Case:
    if not row.strip():
        raise SchemaError(f"cases[{index}]: blank record")
    if _exceeds_byte_limit(row, MAX_ROW_BYTES):
        raise SchemaError(f"cases[{index}]: row exceeds {MAX_ROW_BYTES} bytes")
    try:
        return from_data(Case, strict_json_loads(row))
    except SchemaError as exc:
        raise SchemaError(f"cases[{index}]: {exc}") from None


def parse_cases(text: str, question: ChoiceQuestion) -> tuple[Case, ...]:
    """Parse one JSONL split into validated cases, preserving state text exactly."""
    if not isinstance(text, str):
        raise SchemaError("cases: must be text")
    if not isinstance(question, ChoiceQuestion):
        raise SchemaError("question: must be ChoiceQuestion")
    if _exceeds_byte_limit(text, MAX_JSON_BYTES):
        raise SchemaError(f"cases: document exceeds {MAX_JSON_BYTES} bytes")
    known = frozenset(question.labels)
    cases: list[Case] = []
    ids: set[str] = set()
    states: set[str] = set()
    for index, row in enumerate(_iter_rows(text)):
        if len(cases) >= MAX_CASES_PER_SPLIT:
            raise SchemaError(f"cases: must contain at most {MAX_CASES_PER_SPLIT} records")
        case = _parse_row(index, row)
        if case.expected_label not in known:
            raise SchemaError(f"cases[{index}].expected_label: must be a known label")
        if case.case_id in ids:
            raise SchemaError(f"cases[{index}].case_id: duplicate case id")
        if case.state in states:
            raise SchemaError(f"cases[{index}].state: exact duplicate state text")
        ids.add(case.case_id)
        states.add(case.state)
        cases.append(case)
    if not cases:
        raise SchemaError("cases: must contain at least one record")
    return tuple(cases)
