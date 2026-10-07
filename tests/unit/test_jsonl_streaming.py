"""JSONL readers stream LF-delimited rows instead of materialising every row first.

Three readers split JSONL on LF: :func:`actseal.contract.parse_cases` (case
splits), :func:`actseal.evidence.decode_rows` (bundle records and faults) and
the recorded fixture adapter. Each formerly built a list of every row before
the first row was checked, so a newline-heavy input allocated one list slot per
LF (about 8 MiB for one MiB of LFs). These regressions pin three properties:

* row boundaries are exactly those of the former ``split`` readers, checked
  exhaustively over short texts and differentially over whole decodes against
  reference copies of the former readers kept below as oracles;
* the first malformed row, the case limit and the row byte limit are reported
  with the same messages and in the same order as before;
* one MiB of LFs is rejected without allocating a row list: the traced peak
  stays far below the cost of one list slot per LF.
"""

from __future__ import annotations

import itertools
import json
import tracemalloc
from collections.abc import Callable, Iterable, Iterator, Sequence
from functools import partial
from pathlib import Path
from typing import Any

import pytest

import actseal.adapters.fixture as fixture_module
import actseal.contract as contract_module
import actseal.evidence as evidence_module
from actseal.adapters.fixture import FixtureModel
from actseal.contract import MAX_ROW_BYTES, parse_cases
from actseal.errors import SchemaError
from actseal.evidence import decode_rows
from actseal.records import MAX_CASES_PER_SPLIT, Case, ChoiceQuestion, DecisionRecord
from actseal.serialization import canonical_json, to_data
from conftest import make_question, make_record, make_request

ONE_MIB = 1024 * 1024
#: A row list for one MiB of LFs costs about 8 MiB; streaming readers stay far below this.
ROW_LIST_FREE_PEAK = 256 * 1024
QUESTION = make_question()

Outcome = tuple[str, object]


def _outcome(call: Callable[[], object]) -> Outcome:
    """``("ok", value)`` or ``("SchemaError", message)``; any other exception propagates."""
    try:
        return ("ok", call())
    except SchemaError as exc:
        return ("SchemaError", str(exc))


def _rejection_with_peak(call: Callable[[], object]) -> tuple[str, int]:
    """The :class:`SchemaError` message of ``call`` and the traced peak it allocated."""
    was_tracing = tracemalloc.is_tracing()
    if not was_tracing:
        tracemalloc.start()
    try:
        tracemalloc.reset_peak()
        baseline, _ = tracemalloc.get_traced_memory()
        with pytest.raises(SchemaError) as info:
            call()
        _, peak = tracemalloc.get_traced_memory()
    finally:
        if not was_tracing:
            tracemalloc.stop()
    return str(info.value), peak - baseline


def _texts(alphabet: Sequence[str], max_length: int) -> Iterator[str]:
    for length in range(max_length + 1):
        for chars in itertools.product(alphabet, repeat=length):
            yield "".join(chars)


def _documents(tokens: Sequence[str], separators: Sequence[str], max_rows: int) -> Iterator[str]:
    """Every join of up to ``max_rows`` tokens, with every separator choice and terminator."""
    yield ""
    for count in range(1, max_rows + 1):
        for chosen in itertools.product(tokens, repeat=count):
            for seps in itertools.product(separators, repeat=count - 1):
                pairs = zip(seps, chosen[1:], strict=True)
                body = chosen[0] + "".join(sep + token for sep, token in pairs)
                yield body
                for terminator in separators:
                    yield body + terminator


# --------------------------------------------------------------------------- #
# Reference copies of the former (list-building) readers, used only as oracles
# --------------------------------------------------------------------------- #


def _former_split_rows(text: str) -> list[str]:
    """Former ``contract._split_rows`` and fixture splitting: LF only, one terminator."""
    rows = text.split("\n")
    if rows and rows[-1] == "":
        rows.pop()
    return rows


def _former_parse_cases(text: str, question: ChoiceQuestion) -> tuple[Case, ...]:
    """Former ``parse_cases`` body after its type and document-size checks."""
    known = frozenset(question.labels)
    cases: list[Case] = []
    ids: set[str] = set()
    states: set[str] = set()
    for index, row in enumerate(_former_split_rows(text)):
        if len(cases) >= MAX_CASES_PER_SPLIT:
            raise SchemaError(f"cases: must contain at most {MAX_CASES_PER_SPLIT} records")
        case = contract_module._parse_row(index, row)
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


def _former_decode_rows(name: str, data: bytes) -> tuple[DecisionRecord, ...]:
    """Former ``evidence.decode_rows`` for decision records."""
    if not data.endswith(b"\n"):
        raise SchemaError(f"{name}: must end with one LF")
    rows = data.split(b"\n")
    rows.pop()
    if not rows:
        raise SchemaError(f"{name}: must contain at least one row")
    if len(rows) > MAX_CASES_PER_SPLIT:
        raise SchemaError(f"{name}: must contain at most {MAX_CASES_PER_SPLIT} rows")
    decoded: list[DecisionRecord] = []
    for index, row in enumerate(rows):
        if len(row) > MAX_ROW_BYTES:
            raise SchemaError(f"{name}[{index}]: row exceeds {MAX_ROW_BYTES} bytes")
        decoded.append(evidence_module._decode_canonical(f"{name}[{index}]", row, DecisionRecord))
    return tuple(decoded)


def _former_fixture_rows(data: bytes) -> dict[str, tuple[Any, ...]]:
    """Former fixture ``_parse_rows``, with rows flattened for comparison."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise SchemaError("responses: must be valid UTF-8") from None
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines:
        raise SchemaError("responses: must contain at least one row")
    rows: dict[str, tuple[Any, ...]] = {}
    for index, line in enumerate(lines):
        case_id, row = fixture_module._parse_row(index, line)
        if case_id in rows:
            raise SchemaError(f"responses[{index}].case_id: duplicate case id")
        rows[case_id] = (row.body_json, row.failure_code, row.warnings)
    return rows


def _fixture_rows(data: bytes) -> dict[str, tuple[Any, ...]]:
    return {
        case_id: (row.body_json, row.failure_code, row.warnings)
        for case_id, row in fixture_module._parse_rows(data).items()
    }


# --------------------------------------------------------------------------- #
# Row boundaries
# --------------------------------------------------------------------------- #

SPLITTERS: dict[str, Callable[[str], Iterable[str]]] = {
    "contract": contract_module._iter_rows,
    "fixture": fixture_module._iter_lines,
}


@pytest.mark.parametrize("name", sorted(SPLITTERS))
def test_row_boundaries_match_the_former_split_exhaustively(name: str) -> None:
    """Every text of up to seven characters over LF, CR, space and a letter."""
    split = SPLITTERS[name]
    checked = 0
    for text in _texts(("\n", "\r", " ", "a"), 7):
        assert list(split(text)) == _former_split_rows(text), repr(text)
        checked += 1
    assert checked == sum(4**length for length in range(8))


@pytest.mark.parametrize("name", sorted(SPLITTERS))
def test_rows_are_produced_lazily(name: str) -> None:
    rows = SPLITTERS[name]("a\n" + "\n" * ONE_MIB)
    assert not isinstance(rows, list | tuple)
    iterator = iter(rows)
    assert iterator is rows
    assert next(iterator) == "a"
    assert next(iterator) == ""


# --------------------------------------------------------------------------- #
# parse_cases
# --------------------------------------------------------------------------- #


def _case_row(case_id: str, state: str, label: str = "billing") -> str:
    return json.dumps({"case_id": case_id, "state": state, "expected_label": label})


CASE_TOKENS = (
    _case_row("a", "s1"),
    _case_row("b", "s2", "technical"),
    _case_row("a", "s3"),  # duplicate id after the first token
    _case_row("c", "s1"),  # duplicate state after the first token
    _case_row("d", "s4", "legal"),  # unknown label
    "",
    " ",
    "{",
)


def test_parse_cases_matches_the_former_reader_on_every_small_document() -> None:
    checked = 0
    for text in _documents(CASE_TOKENS, ("\n", "\r\n", "\r"), 3):
        expected = _outcome(partial(_former_parse_cases, text, QUESTION))
        assert _outcome(partial(parse_cases, text, QUESTION)) == expected, repr(text)
        checked += 1
    assert checked > 4000


def test_parse_cases_rejects_a_mebibyte_of_lfs_without_a_row_list() -> None:
    lfs = "\n" * ONE_MIB
    message, peak = _rejection_with_peak(lambda: parse_cases(lfs, QUESTION))
    assert message == "cases[0]: blank record"
    assert peak < ROW_LIST_FREE_PEAK
    text = _case_row("a", "s1") + lfs
    message, peak = _rejection_with_peak(lambda: parse_cases(text, QUESTION))
    assert message == "cases[1]: blank record"
    assert peak < ROW_LIST_FREE_PEAK


def test_parse_cases_first_malformed_row_precedes_the_case_limit() -> None:
    valid = "\n".join(_case_row(f"c{i}", f"s{i}") for i in range(MAX_CASES_PER_SPLIT + 1))
    for text, message in (
        ("{\n" + valid + "\n", "cases[0]: $: invalid JSON at offset 1"),
        (valid + "\n", f"cases: must contain at most {MAX_CASES_PER_SPLIT} records"),
        (valid + "\n{\n", f"cases: must contain at most {MAX_CASES_PER_SPLIT} records"),
    ):
        assert _outcome(partial(_former_parse_cases, text, QUESTION)) == ("SchemaError", message)
        with pytest.raises(SchemaError) as info:
            parse_cases(text, QUESTION)
        assert str(info.value) == message


def test_parse_cases_overlong_row_message_is_unchanged() -> None:
    overlong = _case_row("z", "s" * MAX_ROW_BYTES)
    text = _case_row("a", "s1") + "\n" + overlong + "\n" + "\n" * ONE_MIB
    expected = f"cases[1]: row exceeds {MAX_ROW_BYTES} bytes"
    assert _outcome(lambda: _former_parse_cases(text, QUESTION)) == ("SchemaError", expected)
    with pytest.raises(SchemaError) as info:
        parse_cases(text, QUESTION)
    assert str(info.value) == expected


# --------------------------------------------------------------------------- #
# evidence.decode_rows
# --------------------------------------------------------------------------- #

RECORDS = "records.jsonl"
RECORD_ROW = canonical_json(to_data(make_record()))


def test_record_row_fixture_is_a_canonical_decodable_row() -> None:
    assert decode_rows(RECORDS, RECORD_ROW + b"\n", DecisionRecord) == (make_record(),)


def test_decode_rows_matches_the_former_reader_on_every_small_file() -> None:
    tokens = (RECORD_ROW, b"", b" ", b"{", b"[]", RECORD_ROW + b"\r", b" " + RECORD_ROW)
    checked = 0
    for count in range(4):
        for chosen in itertools.product(tokens, repeat=count):
            for data in (b"\n".join(chosen), b"\n".join(chosen) + b"\n"):
                expected = _outcome(partial(_former_decode_rows, RECORDS, data))
                actual = _outcome(partial(decode_rows, RECORDS, data, DecisionRecord))
                assert actual == expected, repr(data[:80])
                checked += 1
    assert checked == 2 * sum(len(tokens) ** count for count in range(4))


def test_decode_rows_rejects_a_mebibyte_of_lfs_without_a_row_list() -> None:
    data = b"\n" * ONE_MIB
    message, peak = _rejection_with_peak(lambda: decode_rows(RECORDS, data, DecisionRecord))
    assert message == f"{RECORDS}: must contain at most {MAX_CASES_PER_SPLIT} rows"
    assert _outcome(lambda: _former_decode_rows(RECORDS, data)) == ("SchemaError", message)
    assert peak < ROW_LIST_FREE_PEAK


def test_decode_rows_row_count_still_precedes_row_decoding() -> None:
    at_limit = b"{" + b"\n" * MAX_CASES_PER_SPLIT
    over_limit = b"{" + b"\n" * (MAX_CASES_PER_SPLIT + 1)
    for data in (at_limit, over_limit):
        expected = _outcome(partial(_former_decode_rows, RECORDS, data))
        message, peak = _rejection_with_peak(partial(decode_rows, RECORDS, data, DecisionRecord))
        assert ("SchemaError", message) == expected
        assert peak < ROW_LIST_FREE_PEAK
    assert _outcome(lambda: decode_rows(RECORDS, at_limit, DecisionRecord))[1] == (
        f"{RECORDS}[0]: $: invalid JSON at offset 1"
    )
    assert _outcome(lambda: decode_rows(RECORDS, over_limit, DecisionRecord))[1] == (
        f"{RECORDS}: must contain at most {MAX_CASES_PER_SPLIT} rows"
    )


def test_decode_rows_overlong_row_is_rejected_before_it_is_copied() -> None:
    data = RECORD_ROW + b"\n" + b"x" * (MAX_ROW_BYTES + 1) + b"\n" + RECORD_ROW + b"\n"
    expected = f"{RECORDS}[1]: row exceeds {MAX_ROW_BYTES} bytes"
    assert _outcome(lambda: _former_decode_rows(RECORDS, data)) == ("SchemaError", expected)
    message, peak = _rejection_with_peak(lambda: decode_rows(RECORDS, data, DecisionRecord))
    assert message == expected
    assert peak < ROW_LIST_FREE_PEAK


# --------------------------------------------------------------------------- #
# Recorded fixture adapter
# --------------------------------------------------------------------------- #


def _fixture_row(case_id: str, **changes: object) -> str:
    row: dict[str, object] = {
        "case_id": case_id,
        "body_json": '{"type": "choice", "choice": "billing"}',
        "failure_code": None,
        "warnings": [],
    }
    row.update(changes)
    return json.dumps(row)


FIXTURE_TOKENS = (
    _fixture_row("v-001"),
    _fixture_row("v-002", body_json=None, failure_code="timeout", warnings=["w.slow"]),
    _fixture_row("v-001", warnings=["w.dup"]),  # duplicate id after the first token
    _fixture_row("v-003", extra=1),
    "",
    " ",
    "{",
)


def test_fixture_rows_match_the_former_reader_on_every_small_file() -> None:
    checked = 0
    for text in _documents(FIXTURE_TOKENS, ("\n", "\r\n", "\r"), 3):
        data = text.encode("utf-8")
        expected = _outcome(partial(_former_fixture_rows, data))
        assert _outcome(partial(_fixture_rows, data)) == expected, repr(text)
        checked += 1
    assert checked > 3000
    for data in (b"\xff\n", b"\n\xff", "\n".join(FIXTURE_TOKENS[:2]).encode() + b"\n\xc3"):
        assert _outcome(partial(_fixture_rows, data)) == _outcome(
            partial(_former_fixture_rows, data)
        )


def test_fixture_rejects_a_mebibyte_of_lfs_without_a_row_list() -> None:
    data = b"\n" * ONE_MIB
    message, peak = _rejection_with_peak(lambda: fixture_module._parse_rows(data))
    assert ("SchemaError", message) == _outcome(lambda: _former_fixture_rows(data))
    assert message.startswith("responses[0]: ")
    # The decoded text itself (one MiB) is allocated by both readers; the row list is not.
    assert peak < len(data) + ROW_LIST_FREE_PEAK


def test_fixture_overlong_row_message_is_unchanged(tmp_path: Path) -> None:
    overlong = _fixture_row("v-009", body_json="x" * MAX_ROW_BYTES)
    data = (_fixture_row("v-001") + "\n" + overlong + "\n" + "\n" * 1024).encode("utf-8")
    expected = f"responses[1]: row exceeds {fixture_module.MAX_ROW_BYTES} bytes"
    assert _outcome(lambda: _former_fixture_rows(data)) == ("SchemaError", expected)
    path = tmp_path / "responses.jsonl"
    path.write_bytes(data)
    with pytest.raises(SchemaError) as info:
        FixtureModel(path)
    assert str(info.value) == expected


def test_fixture_has_no_row_count_limit(tmp_path: Path) -> None:
    """The fixture never had a row limit; streaming must not invent one."""
    count = MAX_CASES_PER_SPLIT + 1
    path = tmp_path / "responses.jsonl"
    path.write_text("".join(_fixture_row(f"v-{i:05d}") + "\n" for i in range(count)))
    model = FixtureModel(path)
    try:
        request = make_request()
        last = type(request)(f"v-{count - 1:05d}", request.state, request.question)
        capture = model.decide(last, timeout_s=30.0)
        assert capture.body_json == '{"type": "choice", "choice": "billing"}'
        assert capture.failure_code is None
    finally:
        model.close()
