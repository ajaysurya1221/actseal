"""Exact TOML contract parsing and strict JSONL case parsing."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from actseal.contract import MAX_ROW_BYTES, parse_cases, parse_contract, read_input_text
from actseal.errors import SchemaError
from actseal.records import (
    MAX_CASES_PER_SPLIT,
    Case,
    ChoiceQuestion,
    Contract,
    GateLimits,
    LockedPolicy,
    Option,
)
from actseal.serialization import MAX_JSON_BYTES
from conftest import make_question

# --------------------------------------------------------------------------- #
# Minimal TOML renderer for the exact contract shape
# --------------------------------------------------------------------------- #


class Raw:
    """A TOML fragment inserted verbatim (``inf``, ``true``, dates, ...)."""

    def __init__(self, text: str) -> None:
        self.text = text


def _value(value: Any) -> str:
    if isinstance(value, Raw):
        return value.text
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ", ".join(_value(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{key} = {_value(item)}" for key, item in value.items()) + "}"
    raise TypeError(type(value))


def render(document: dict[str, Any]) -> str:
    """Render scalars first, then one ``[table]`` per dict value."""
    lines = [f"{key} = {_value(v)}" for key, v in document.items() if not isinstance(v, dict)]
    for key, table in document.items():
        if isinstance(table, dict):
            lines.append(f"\n[{key}]")
            lines.extend(f"{name} = {_value(item)}" for name, item in table.items())
    return "\n".join(lines) + "\n"


def base_document() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "name": "support-triage",
        "evidence_scope": "demo",
        "population": "Authored support-routing demonstration; no deployment claim",
        "question": {
            "question_id": "department",
            "instructions": "Select the department responsible for this ticket.",
            "options": [
                {"label": "billing", "description": "Payments and refunds"},
                {"label": "technical", "description": "Technical support"},
                {"label": "sales", "description": "Purchasing questions"},
            ],
        },
        "policy": {"allowed_labels": ["billing", "technical", "sales"], "threshold": 0.90},
        "risk": {"max_risk": 0.05, "min_coverage": 0.50, "alpha": 0.05},
    }


def write_toml(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "contract.toml"
    path.write_bytes(text.encode("utf-8"))
    return path


def parse_text(tmp_path: Path, text: str) -> Contract:
    return parse_contract(write_toml(tmp_path, text))


def parse_document(tmp_path: Path, document: dict[str, Any]) -> Contract:
    return parse_text(tmp_path, render(document))


# --------------------------------------------------------------------------- #
# parse_contract: accepted documents
# --------------------------------------------------------------------------- #


def test_contract_example_parses_to_the_exact_record(tmp_path: Path) -> None:
    contract = parse_document(tmp_path, base_document())
    assert contract == Contract(
        1,
        "support-triage",
        ChoiceQuestion(
            "department",
            "Select the department responsible for this ticket.",
            (
                Option("billing", "Payments and refunds"),
                Option("technical", "Technical support"),
                Option("sales", "Purchasing questions"),
            ),
        ),
        LockedPolicy(("billing", "technical", "sales"), ("billing", "technical", "sales"), 0.9),
        GateLimits(0.05, 0.5, 0.05),
        "demo",
        "Authored support-routing demonstration; no deployment claim",
    )


def test_contract_verbatim_contracts_example(tmp_path: Path) -> None:
    text = """
schema_version = 1
name = "support-triage"
evidence_scope = "demo"
population = "Authored support-routing demonstration; no deployment claim"

[question]
question_id = "department"
instructions = "Select the department responsible for this ticket."
options = [
  {label = "billing", description = "Payments and refunds"},
  {label = "technical", description = "Technical support"},
  {label = "sales", description = "Purchasing questions"},
]

[policy]
allowed_labels = ["billing", "technical", "sales"]
threshold = 0.90

[risk]
max_risk = 0.05
min_coverage = 0.50
alpha = 0.05
"""
    assert parse_text(tmp_path, text) == parse_document(tmp_path, base_document())


def test_known_labels_follow_option_order_and_allowed_may_be_a_subset(tmp_path: Path) -> None:
    document = base_document()
    document["question"]["options"].reverse()
    document["policy"]["allowed_labels"] = ["billing"]
    contract = parse_document(tmp_path, document)
    assert contract.policy.known_labels == ("sales", "technical", "billing")
    assert contract.policy.allowed_labels == ("billing",)
    assert contract.question.labels == contract.policy.known_labels


def test_integer_threshold_and_limits_are_accepted_as_numbers(tmp_path: Path) -> None:
    document = base_document()
    document["policy"]["threshold"] = 1
    document["risk"] = {"max_risk": 0, "min_coverage": 1, "alpha": 0.5}
    contract = parse_document(tmp_path, document)
    assert contract.policy.threshold == 1.0
    assert isinstance(contract.policy.threshold, float)
    assert contract.limits == GateLimits(0.0, 1.0, 0.5)


def test_non_ascii_text_is_preserved_exactly(tmp_path: Path) -> None:
    document = base_document()
    document["name"] = "triage café ☃ \U0001f600"
    document["question"]["options"][0]["description"] = "Zahlungen  und\tRückerstattungen"
    contract = parse_document(tmp_path, document)
    assert contract.name == "triage café ☃ \U0001f600"
    assert contract.question.options[0].description == "Zahlungen  und\tRückerstattungen"


def test_contract_tables_may_appear_in_any_order(tmp_path: Path) -> None:
    document = base_document()
    reordered = {key: document[key] for key in ("risk", "policy", "question")}
    reordered.update({k: v for k, v in document.items() if k not in reordered})
    assert parse_document(tmp_path, reordered) == parse_document(tmp_path, document)


def test_contract_iid_scope_accepted(tmp_path: Path) -> None:
    document = base_document()
    document["evidence_scope"] = "iid"
    assert parse_document(tmp_path, document).evidence_scope == "iid"


# --------------------------------------------------------------------------- #
# parse_contract: rejected documents
# --------------------------------------------------------------------------- #


def _set(document: dict[str, Any], path: tuple[Any, ...], value: Any) -> dict[str, Any]:
    target: Any = document
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return document


def _delete(document: dict[str, Any], path: tuple[Any, ...]) -> dict[str, Any]:
    target: Any = document
    for key in path[:-1]:
        target = target[key]
    del target[path[-1]]
    return document


SIXTEEN_OPTIONS = [{"label": f"l{i}", "description": f"d{i}"} for i in range(16)]
SEVENTEEN_OPTIONS = [*SIXTEEN_OPTIONS, {"label": "l16", "description": "d16"}]

BAD_DOCUMENTS: list[tuple[str, tuple[Any, ...], Any, str]] = [
    # (label, path, value-or-DELETE, expected message fragment)
    ("unknown top-level field", ("extra",), 1, "Contract: 1 unknown field(s)"),
    ("unknown top-level table", ("extra",), {"a": 1}, "Contract: 1 unknown field(s)"),
    ("known_labels not configurable", ("policy", "known_labels"), ["billing"], "Contract.policy"),
    ("unknown question field", ("question", "extra"), "x", "Contract.question: 1 unknown"),
    ("unknown option field", ("question", "options", 0, "extra"), "x", "options[0]: 1 unknown"),
    ("unknown risk field", ("risk", "extra"), 0.1, "Contract.limits: 1 unknown"),
    ("schema_version 2", ("schema_version",), 2, "schema_version: unsupported schema version"),
    ("schema_version 0", ("schema_version",), 0, "schema_version: unsupported schema version"),
    ("schema_version string", ("schema_version",), "1", "schema_version: expected integer"),
    ("schema_version bool", ("schema_version",), True, "schema_version: expected integer"),
    ("schema_version float", ("schema_version",), 1.0, "schema_version: expected integer"),
    ("name empty", ("name",), "", "name: must be nonempty"),
    ("name int", ("name",), 3, "name: expected string"),
    ("name date", ("name",), Raw("1979-05-27"), "name: expected string"),
    ("name array", ("name",), ["a"], "name: expected string"),
    ("evidence_scope unknown", ("evidence_scope",), "prod", "evidence_scope: unsupported value"),
    ("evidence_scope case", ("evidence_scope",), "Demo", "evidence_scope: unsupported value"),
    ("population empty", ("population",), "", "population: must be nonempty"),
    ("question not table", ("question",), "x", "Contract.question: expected object"),
    ("question_id empty", ("question", "question_id"), "", "question_id: must be nonempty"),
    ("instructions int", ("question", "instructions"), 1, "instructions: expected string"),
    ("options not array", ("question", "options"), "billing", "options: expected array"),
    ("options table", ("question", "options"), {"label": "a"}, "options: expected array"),
    ("option not table", ("question", "options", 0), "billing", "options[0]: expected object"),
    ("option missing description", ("question", "options", 0), {"label": "a"}, "missing fields"),
    ("option label int", ("question", "options", 0, "label"), 1, "label: expected string"),
    ("option label bool", ("question", "options", 0, "label"), True, "label: expected string"),
    ("option label empty", ("question", "options", 0, "label"), "", "label: must be nonempty"),
    ("option description empty", ("question", "options", 0, "description"), "", "nonempty"),
    ("duplicate option labels", ("question", "options", 1, "label"), "billing", "labels"),
    ("one option", ("question", "options"), [{"label": "a", "description": "b"}], "options"),
    ("seventeen options", ("question", "options"), SEVENTEEN_OPTIONS, "options"),
    ("policy not table", ("policy",), 1, "Contract.policy: expected table"),
    ("allowed not array", ("policy", "allowed_labels"), "billing", "allowed_labels: expected"),
    ("allowed empty", ("policy", "allowed_labels"), [], "allowed_labels: must contain"),
    ("allowed foreign", ("policy", "allowed_labels"), ["billing", "legal"], "subset"),
    ("allowed duplicate", ("policy", "allowed_labels"), ["billing", "billing"], "duplicates"),
    ("allowed int item", ("policy", "allowed_labels"), ["billing", 1], "expected string"),
    ("threshold zero", ("policy", "threshold"), 0.0, "threshold: must be in (0.0, 1.0]"),
    ("threshold int zero", ("policy", "threshold"), 0, "threshold: must be in (0.0, 1.0]"),
    ("threshold above one", ("policy", "threshold"), 1.5, "threshold: must be in (0.0, 1.0]"),
    ("threshold negative", ("policy", "threshold"), -0.5, "threshold: must be in"),
    ("threshold bool", ("policy", "threshold"), True, "threshold: expected number"),
    ("threshold string", ("policy", "threshold"), "0.9", "threshold: expected number"),
    ("threshold inf", ("policy", "threshold"), Raw("inf"), "threshold: must be finite"),
    ("threshold nan", ("policy", "threshold"), Raw("nan"), "threshold: must be finite"),
    ("threshold -inf", ("policy", "threshold"), Raw("-inf"), "threshold: must be finite"),
    ("threshold array", ("policy", "threshold"), [0.9], "threshold: expected number"),
    ("risk not table", ("risk",), [0.05], "Contract.limits: expected object"),
    ("max_risk negative", ("risk", "max_risk"), -0.1, "max_risk: must be in [0.0, 1.0]"),
    ("max_risk above one", ("risk", "max_risk"), 1.1, "max_risk: must be in [0.0, 1.0]"),
    ("max_risk bool", ("risk", "max_risk"), False, "max_risk: expected number"),
    ("max_risk nan", ("risk", "max_risk"), Raw("nan"), "max_risk: must be finite"),
    ("min_coverage string", ("risk", "min_coverage"), "0.5", "min_coverage: expected number"),
    ("min_coverage above one", ("risk", "min_coverage"), 2, "min_coverage: must be in"),
    ("alpha one", ("risk", "alpha"), 1.0, "alpha: must be in [1e-06, 1.0)"),
    ("alpha too small", ("risk", "alpha"), 1e-7, "alpha: must be in [1e-06, 1.0)"),
    ("alpha zero", ("risk", "alpha"), 0, "alpha: must be in [1e-06, 1.0)"),
    ("alpha bool", ("risk", "alpha"), True, "alpha: expected number"),
    ("alpha inf", ("risk", "alpha"), Raw("inf"), "alpha: must be finite"),
]

MISSING_DOCUMENTS: list[tuple[str, tuple[Any, ...], str]] = [
    ("missing schema_version", ("schema_version",), "Contract: missing fields schema_version"),
    ("missing name", ("name",), "Contract: missing fields name"),
    ("missing evidence_scope", ("evidence_scope",), "missing fields evidence_scope"),
    ("missing population", ("population",), "missing fields population"),
    ("missing question", ("question",), "Contract: missing fields question"),
    ("missing policy", ("policy",), "Contract: missing fields policy"),
    ("missing risk", ("risk",), "Contract: missing fields risk"),
    ("missing question_id", ("question", "question_id"), "missing fields question_id"),
    ("missing instructions", ("question", "instructions"), "missing fields instructions"),
    ("missing options", ("question", "options"), "missing fields options"),
    ("missing allowed_labels", ("policy", "allowed_labels"), "missing fields allowed_labels"),
    ("missing threshold", ("policy", "threshold"), "missing fields threshold"),
    ("missing max_risk", ("risk", "max_risk"), "missing fields max_risk"),
    ("missing min_coverage", ("risk", "min_coverage"), "missing fields min_coverage"),
    ("missing alpha", ("risk", "alpha"), "missing fields alpha"),
]


@pytest.mark.parametrize(
    ("path", "value", "fragment"),
    [(path, value, fragment) for _, path, value, fragment in BAD_DOCUMENTS],
    ids=[label for label, *_ in BAD_DOCUMENTS],
)
def test_contract_rejects_bad_values(
    tmp_path: Path, path: tuple[Any, ...], value: Any, fragment: str
) -> None:
    document = _set(base_document(), path, value)
    with pytest.raises(SchemaError, match=_escape(fragment)):
        parse_document(tmp_path, document)


@pytest.mark.parametrize(
    ("path", "fragment"),
    [(path, fragment) for _, path, fragment in MISSING_DOCUMENTS],
    ids=[label for label, *_ in MISSING_DOCUMENTS],
)
def test_contract_rejects_missing_fields(
    tmp_path: Path, path: tuple[Any, ...], fragment: str
) -> None:
    document = _delete(base_document(), path)
    with pytest.raises(SchemaError, match=_escape(fragment)):
        parse_document(tmp_path, document)


def _escape(fragment: str) -> str:
    return re.escape(fragment)


def test_sixteen_options_are_the_upper_bound(tmp_path: Path) -> None:
    document = base_document()
    document["question"]["options"] = SIXTEEN_OPTIONS
    document["policy"]["allowed_labels"] = ["l0"]
    assert len(parse_document(tmp_path, document).question.options) == 16


@pytest.mark.parametrize(
    "text",
    [
        "",
        "schema_version = 1",
        "not toml at all",
        'schema_version = 1\nschema_version = 1\nname = "x"',
        "[question]\n[question]\n",
        '{"schema_version": 1}',
        "﻿schema_version = 1\n",
    ],
    ids=["empty", "scalar only", "garbage", "duplicate key", "duplicate table", "json", "bom"],
)
def test_contract_rejects_invalid_or_incomplete_toml(tmp_path: Path, text: str) -> None:
    with pytest.raises(SchemaError, match="Contract"):
        parse_text(tmp_path, text)


def test_contract_rejects_invalid_utf8(tmp_path: Path) -> None:
    path = tmp_path / "contract.toml"
    path.write_bytes(b'name = "\xff\xfe"\n')
    with pytest.raises(SchemaError, match="input: file must be valid UTF-8"):
        parse_contract(path)


def test_contract_missing_file_propagates_os_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        parse_contract(tmp_path / "absent.toml")


def test_contract_errors_do_not_echo_values(tmp_path: Path) -> None:
    document = _set(base_document(), ("evidence_scope",), "SECRET-SCOPE-VALUE")
    with pytest.raises(SchemaError) as info:
        parse_document(tmp_path, document)
    assert "SECRET" not in str(info.value)
    document = _set(base_document(), ("policy", "SECRET_KEY"), 1)
    with pytest.raises(SchemaError) as info:
        parse_document(tmp_path, document)
    assert "SECRET" not in str(info.value)


# --------------------------------------------------------------------------- #
# read_input_text
# --------------------------------------------------------------------------- #


def test_read_input_text_preserves_bytes_exactly(tmp_path: Path) -> None:
    raw = "﻿a\r\nb\rc\n\n café \U0001f600".encode()
    path = tmp_path / "data.jsonl"
    path.write_bytes(raw)
    text = read_input_text(path)
    assert text.encode("utf-8") == raw
    assert text.startswith("﻿")
    assert "\r\n" in text


def test_read_input_text_enforces_the_byte_limit_exactly(tmp_path: Path) -> None:
    path = tmp_path / "data.jsonl"
    path.write_bytes(b"x" * 10)
    assert read_input_text(path, limit=10) == "x" * 10
    with pytest.raises(SchemaError, match="input: file exceeds 9 bytes"):
        read_input_text(path, limit=9)
    path.write_bytes(("é" * 5).encode())  # 5 characters, 10 bytes
    assert read_input_text(path, limit=10) == "é" * 5
    with pytest.raises(SchemaError, match="input: file exceeds 9 bytes"):
        read_input_text(path, limit=9)


class RecordingStream:
    """Binary stream wrapper that records every read size requested."""

    def __init__(self, inner: Any, requests: list[int | None]) -> None:
        self._inner = inner
        self.requests = requests

    def read(self, size: int | None = -1) -> bytes:
        self.requests.append(size)
        return bytes(self._inner.read(size))

    def __enter__(self) -> RecordingStream:
        return self

    def __exit__(self, *exc: object) -> None:
        self._inner.close()


@pytest.fixture
def read_requests(monkeypatch: pytest.MonkeyPatch) -> list[int | None]:
    requests: list[int | None] = []
    original = Path.open

    def recording_open(self: Path, *args: Any, **kwargs: Any) -> Any:
        stream = original(self, *args, **kwargs)
        mode = args[0] if args else kwargs.get("mode", "r")
        return RecordingStream(stream, requests) if mode == "rb" else stream

    monkeypatch.setattr(Path, "open", recording_open)
    return requests


def test_read_input_text_requests_at_most_limit_plus_one_bytes(
    tmp_path: Path, read_requests: list[int | None]
) -> None:
    """REVIEW T10-01 finding 1: the read is bounded before allocation."""
    path = tmp_path / "big.jsonl"
    path.write_bytes(b"x" * 1000)
    with pytest.raises(SchemaError, match="input: file exceeds 8 bytes"):
        read_input_text(path, limit=8)
    assert read_requests, "the file was never read through the stream"
    assert all(isinstance(size, int) and 0 < size <= 9 for size in read_requests)
    assert sum(size for size in read_requests if isinstance(size, int)) <= 9
    read_requests.clear()
    assert read_input_text(path, limit=1000) == "x" * 1000
    assert all(isinstance(size, int) and size <= 1001 for size in read_requests)
    read_requests.clear()
    small = tmp_path / "small.jsonl"
    small.write_bytes(b"ok")
    assert read_input_text(small, limit=2) == "ok"
    assert read_requests == [3]


@pytest.mark.parametrize(
    "limit",
    [0, -1, True, False, 1.0, 8.5, "8", None, MAX_JSON_BYTES + 1, 10**30],
    ids=[
        "zero",
        "negative",
        "true",
        "false",
        "float",
        "fraction",
        "string",
        "none",
        "over",
        "huge",
    ],
)
def test_read_input_text_rejects_invalid_limits(tmp_path: Path, limit: Any) -> None:
    path = tmp_path / "data.jsonl"
    path.write_bytes(b"x")
    with pytest.raises(
        SchemaError, match=f"limit: must be an integer in \\[1, {MAX_JSON_BYTES}\\]"
    ):
        read_input_text(path, limit=limit)


def test_read_input_text_accepts_the_maximum_limit(tmp_path: Path) -> None:
    path = tmp_path / "data.jsonl"
    path.write_bytes(b"xyz")
    assert read_input_text(path, limit=MAX_JSON_BYTES) == "xyz"
    assert read_input_text(path) == "xyz"


def test_read_input_text_default_limit_is_the_generic_ceiling() -> None:
    assert MAX_JSON_BYTES == 128 * 1024 * 1024
    assert MAX_ROW_BYTES == 1024 * 1024


# --------------------------------------------------------------------------- #
# parse_cases: accepted datasets
# --------------------------------------------------------------------------- #

QUESTION = make_question()


def row(case_id: str, state: str, label: str = "billing") -> str:
    return json.dumps(
        {"case_id": case_id, "state": state, "expected_label": label}, ensure_ascii=False
    )


def jsonl(*rows: str, terminator: str = "\n") -> str:
    return terminator.join(rows) + terminator


def test_parse_cases_returns_cases_in_file_order() -> None:
    text = jsonl(row("a", "first"), row("b", "second", "technical"), row("c", "third", "sales"))
    assert parse_cases(text, QUESTION) == (
        Case("a", "first", "billing"),
        Case("b", "second", "technical"),
        Case("c", "third", "sales"),
    )


def test_parse_cases_preserves_state_text_exactly() -> None:
    state = "  Mixed CASE café ☃\t\\n literal backslash \U0001f600 trailing  "
    (case,) = parse_cases(row("a", state), QUESTION)
    assert case.state == state
    escaped = '{"case_id":"a","state":"line\\nbreak\\r\\ttab\\u0000nul","expected_label":"billing"}'
    (case,) = parse_cases(escaped, QUESTION)
    assert case.state == "line\nbreak\r\ttab\x00nul"


@pytest.mark.parametrize(
    "text",
    [
        row("a", "s1") + "\n" + row("b", "s2"),
        row("a", "s1") + "\n" + row("b", "s2") + "\n",
        row("a", "s1") + "\r\n" + row("b", "s2") + "\r\n",
        row("a", "s1") + "\r\n" + row("b", "s2"),
        "  " + row("a", "s1") + " \t\n\t" + row("b", "s2") + "\n",
        (
            '{"state": "s1", "expected_label": "billing", "case_id": "a"}\n'
            '{ "case_id" : "b" , "state" : "s2" , "expected_label" : "billing" }\n'
        ),
    ],
    ids=["no final lf", "final lf", "crlf", "crlf no final", "padding", "key order"],
)
def test_parse_cases_accepts_equivalent_layouts(text: str) -> None:
    assert parse_cases(text, QUESTION) == (Case("a", "s1", "billing"), Case("b", "s2", "billing"))


def test_parse_cases_does_not_deduplicate_different_literal_texts() -> None:
    text = jsonl(
        row("a", "Refund not received"),
        row("b", "refund not received"),
        row("c", "Refund not received "),
        row("d", " Refund not received"),
        row("e", "Refund  not received"),
        row("f", "Refund not received\n"),
        row("g", "Refund not rece" + chr(0x131) + "ved"),  # dotless i, not deduplicated
    )
    cases = parse_cases(text, QUESTION)
    assert len(cases) == 7
    assert len({case.state for case in cases}) == 7


def test_parse_cases_accepts_exactly_the_maximum_split_size() -> None:
    text = jsonl(*(row(f"c{i}", f"state {i}") for i in range(MAX_CASES_PER_SPLIT)))
    cases = parse_cases(text, QUESTION)
    assert len(cases) == MAX_CASES_PER_SPLIT
    assert cases[-1].case_id == f"c{MAX_CASES_PER_SPLIT - 1}"


def test_parse_cases_rejects_one_case_over_the_maximum() -> None:
    text = jsonl(*(row(f"c{i}", f"state {i}") for i in range(MAX_CASES_PER_SPLIT + 1)))
    with pytest.raises(SchemaError, match=f"cases: must contain at most {MAX_CASES_PER_SPLIT}"):
        parse_cases(text, QUESTION)


def _row_of_bytes(size: int, case_id: str = "a") -> str:
    skeleton = row(case_id, "")
    assert len(skeleton.encode()) < size
    return row(case_id, "s" * (size - len(skeleton.encode())))


def test_parse_cases_row_limit_is_one_mib_inclusive() -> None:
    exact = _row_of_bytes(MAX_ROW_BYTES)
    assert len(exact.encode()) == MAX_ROW_BYTES
    (case,) = parse_cases(exact + "\n", QUESTION)
    assert len(case.state) == MAX_ROW_BYTES - len(row("a", "").encode())
    with pytest.raises(SchemaError, match=f"cases\\[1\\]: row exceeds {MAX_ROW_BYTES} bytes"):
        parse_cases(row("z", "small") + "\n" + _row_of_bytes(MAX_ROW_BYTES + 1), QUESTION)


def test_parse_cases_row_limit_counts_bytes_not_characters() -> None:
    skeleton_bytes = len(row("a", "").encode())
    # Each U+00E9 is two UTF-8 bytes: exactly at the limit in bytes, half in characters.
    fill = (MAX_ROW_BYTES - skeleton_bytes) // 2
    text = row("a", "é" * fill)
    assert len(text.encode()) == MAX_ROW_BYTES
    parse_cases(text, QUESTION)
    with pytest.raises(SchemaError, match="row exceeds"):
        parse_cases(row("a", "é" * fill + "x"), QUESTION)


def test_parse_cases_document_limit_is_the_generic_ceiling() -> None:
    with pytest.raises(SchemaError, match=f"cases: document exceeds {MAX_JSON_BYTES} bytes"):
        parse_cases(" " * (MAX_JSON_BYTES + 1), QUESTION)


# --------------------------------------------------------------------------- #
# parse_cases: rejected datasets
# --------------------------------------------------------------------------- #

BAD_CASES: list[tuple[str, str, str]] = [
    ("empty", "", "cases: must contain at least one record"),
    ("only newline", "\n", r"cases\[0\]: blank record"),
    ("only whitespace", "   \t ", r"cases\[0\]: blank record"),
    ("only crlf", "\r\n", r"cases\[0\]: blank record"),
    ("leading blank", "\n" + row("a", "s"), r"cases\[0\]: blank record"),
    ("interior blank", row("a", "s1") + "\n\n" + row("b", "s2"), r"cases\[1\]: blank record"),
    ("interior spaces", row("a", "s1") + "\n \n" + row("b", "s2"), r"cases\[1\]: blank record"),
    ("trailing blank line", row("a", "s1") + "\n\n", r"cases\[1\]: blank record"),
    ("two rows one line", row("a", "s1") + " " + row("b", "s2"), r"cases\[0\]: .*invalid JSON"),
    ("cr separated", row("a", "s1") + "\r" + row("b", "s2"), r"cases\[0\]: .*invalid JSON"),
    ("array row", "[1]", r"cases\[0\]: Case: expected object"),
    ("string row", '"x"', r"cases\[0\]: Case: expected object"),
    ("number row", "1", r"cases\[0\]: Case: expected object"),
    ("null row", "null", r"cases\[0\]: Case: expected object"),
    ("truncated json", '{"case_id": "a", "state": "s"', r"cases\[0\]: .*invalid JSON"),
    ("bom", "﻿" + row("a", "s"), r"cases\[0\]: .*invalid JSON"),
    ("unknown field", '{"case_id":"a","state":"s","expected_label":"billing","x":1}', "unknown"),
    ("missing state", '{"case_id":"a","expected_label":"billing"}', "missing fields state"),
    ("missing label", '{"case_id":"a","state":"s"}', "missing fields expected_label"),
    ("missing id", '{"state":"s","expected_label":"billing"}', "missing fields case_id"),
    ("state int", '{"case_id":"a","state":1,"expected_label":"billing"}', "state: expected"),
    ("state bool", '{"case_id":"a","state":true,"expected_label":"billing"}', "state: expected"),
    ("state null", '{"case_id":"a","state":null,"expected_label":"billing"}', "state: expected"),
    ("state nested", '{"case_id":"a","state":{"t":"s"},"expected_label":"billing"}', "state"),
    ("state array", '{"case_id":"a","state":["s"],"expected_label":"billing"}', "state"),
    ("state float", '{"case_id":"a","state":1.5,"expected_label":"billing"}', "state: expected"),
    ("id int", '{"case_id":1,"state":"s","expected_label":"billing"}', "case_id: expected"),
    ("label int", '{"case_id":"a","state":"s","expected_label":1}', "expected_label: expected"),
    ("label bool", '{"case_id":"a","state":"s","expected_label":true}', "expected_label"),
    ("empty id", '{"case_id":"","state":"s","expected_label":"billing"}', "case_id: must be non"),
    ("empty state", '{"case_id":"a","state":"","expected_label":"billing"}', "state: must be non"),
    ("empty label", '{"case_id":"a","state":"s","expected_label":""}', "expected_label: must be"),
    ("foreign label", row("a", "s", "legal"), r"cases\[0\].expected_label: must be a known label"),
    ("label case", row("a", "s", "Billing"), r"cases\[0\].expected_label: must be a known label"),
    ("label padded", row("a", "s", "billing "), r"expected_label: must be a known label"),
    ("duplicate key", '{"case_id":"a","case_id":"b","state":"s","expected_label":"x"}', "dup"),
    ("nan", '{"case_id":"a","state":NaN,"expected_label":"billing"}', "nonfinite"),
    ("infinity", '{"case_id":"a","state":"s","expected_label":Infinity}', "nonfinite"),
    ("overflow", '{"case_id":"a","state":1e999,"expected_label":"billing"}', "finite"),
    ("deep nesting", '{"case_id":"a","state":' + "[" * 33 + "]" * 33 + "}", "nesting"),
    ("lone surrogate", '{"case_id":"a","state":"\\ud800","expected_label":"billing"}', "Unicode"),
    ("duplicate id", row("a", "s1") + "\n" + row("a", "s2"), r"cases\[1\].case_id: duplicate"),
    ("duplicate state", row("a", "s") + "\n" + row("b", "s"), r"cases\[1\].state: exact duplicate"),
    (
        "duplicate state later",
        jsonl(row("a", "s1"), row("b", "s2"), row("c", "s3"), row("d", "s1", "sales")),
        r"cases\[3\].state: exact duplicate state text",
    ),
    (
        "duplicate id later",
        jsonl(row("a", "s1"), row("b", "s2"), row("c", "s3"), row("b", "s4")),
        r"cases\[3\].case_id: duplicate case id",
    ),
]


@pytest.mark.parametrize(
    ("text", "fragment"),
    [(text, fragment) for _, text, fragment in BAD_CASES],
    ids=[label for label, *_ in BAD_CASES],
)
def test_parse_cases_rejects_malformed_datasets(text: str, fragment: str) -> None:
    with pytest.raises(SchemaError, match=fragment):
        parse_cases(text, QUESTION)


def test_parse_cases_bad_row_after_valid_rows_reports_its_index() -> None:
    text = jsonl(row("a", "s1"), row("b", "s2"), "{", row("d", "s4"))
    with pytest.raises(SchemaError, match=r"^cases\[2\]: "):
        parse_cases(text, QUESTION)


def test_parse_cases_errors_do_not_echo_row_content() -> None:
    text = row("a", "s", "SECRET-LABEL") + "\n"
    with pytest.raises(SchemaError) as info:
        parse_cases(text, QUESTION)
    assert "SECRET" not in str(info.value)
    with pytest.raises(SchemaError) as info:
        parse_cases('{"SECRET-KEY":1}', QUESTION)
    assert "SECRET" not in str(info.value)


@pytest.mark.parametrize("text", [None, b'{"case_id":"a"}', 1, ["{}"], ("{}",)])
def test_parse_cases_rejects_non_text(text: object) -> None:
    with pytest.raises(SchemaError, match="cases: must be text"):
        parse_cases(text, QUESTION)  # type: ignore[arg-type]


@pytest.mark.parametrize("question", [None, ("billing", "technical"), {"options": []}, "q"])
def test_parse_cases_rejects_non_question(question: object) -> None:
    with pytest.raises(SchemaError, match="question: must be ChoiceQuestion"):
        parse_cases(row("a", "s"), question)  # type: ignore[arg-type]


def test_parse_cases_result_is_immutable_tuple_of_cases() -> None:
    cases = parse_cases(jsonl(row("a", "s1"), row("b", "s2")), QUESTION)
    assert isinstance(cases, tuple)
    assert all(isinstance(case, Case) for case in cases)
    with pytest.raises(AttributeError):
        cases[0].state = "changed"  # type: ignore[misc]
