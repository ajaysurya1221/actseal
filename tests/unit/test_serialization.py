"""Canonical JSON, strict parsing, record round trips and the implementation fingerprint."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

import actseal
from actseal.errors import SchemaError
from actseal.records import (
    ChoiceAnswer,
    ChoiceQuestion,
    DecisionRecord,
    FaultResult,
    Interval,
    ModelIdentity,
    Option,
    PlanLock,
    ProviderFailure,
    Verdict,
)
from actseal.serialization import (
    MAX_JSON_BYTES,
    MAX_JSON_DEPTH,
    _exceeds_byte_limit,
    _fingerprint_tree,
    canonical_json,
    from_data,
    implementation_fingerprint,
    sha256_bytes,
    strict_json_loads,
    to_data,
)
from conftest import HEX_A, HEX_B, SAMPLE_BUILDERS, make_answer, make_identity, make_record

RECORD_NAMES = sorted(SAMPLE_BUILDERS)
RECORD_TYPES: dict[str, Any] = {name: type(build()) for name, build in SAMPLE_BUILDERS.items()}


# --------------------------------------------------------------------------- #
# canonical_json and sha256_bytes
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, b"null"),
        (True, b"true"),
        (False, b"false"),
        (0, b"0"),
        (-17, b"-17"),
        (1.5, b"1.5"),
        (0.1, b"0.1"),
        (1e16, b"1e+16"),
        (10**30, b"1000000000000000000000000000000"),
        ("", b'""'),
        ("plain", b'"plain"'),
        ("café ☃ \U0001f600", '"café ☃ 😀"'.encode()),
        ('quote" slash\\ nl\n tab\t nul\x00', b'"quote\\" slash\\\\ nl\\n tab\\t nul\\u0000"'),
        ([], b"[]"),
        ({}, b"{}"),
        ((1, "a", None), b'[1,"a",null]'),
        ({"b": 1, "a": [1.5, "é", None, True]}, '{"a":[1.5,"é",null,true],"b":1}'.encode()),
        ({"z": {"y": {"x": ()}}}, b'{"z":{"y":{"x":[]}}}'),
        ({"é": 1, "e": 2, "E": 3}, '{"E":3,"e":2,"é":1}'.encode()),
    ],
)
def test_canonical_json_known_vectors(value: object, expected: bytes) -> None:
    data = canonical_json(value)
    assert data == expected
    assert not data.endswith(b"\n")
    assert json.loads(data.decode("utf-8")) == json.loads(expected.decode("utf-8"))


def test_canonical_json_is_utf8_not_ascii_escaped() -> None:
    data = canonical_json("é")
    assert data == b'"\xc3\xa9"'
    assert b"\\u00e9" not in data


@pytest.mark.parametrize(
    "value",
    [
        float("nan"),
        float("inf"),
        -float("inf"),
        [1, float("nan")],
        {"k": float("inf")},
        b"bytes",
        {1: "int key"},
        {("t",): "tuple key"},
        {"a", "set"},
        Option("a", "b"),
        make_answer(),
        object(),
        "\ud800",
        {"k": "\udfff"},
        {"\ud800": 1},
        {"ok": {"\udfff": [1]}},
        10**5000,
        [10**5000],
        {"k": -(10**5000)},
        Path("p"),
    ],
    ids=lambda v: type(v).__name__,
)
def test_canonical_json_rejects_non_json_values(value: object) -> None:
    with pytest.raises(SchemaError):
        canonical_json(value)


def test_canonical_json_translates_encoder_failures_to_schema_errors() -> None:
    with pytest.raises(SchemaError, match="encoded"):
        canonical_json(10**5000)
    with pytest.raises(SchemaError, match="Unicode"):
        canonical_json({"\ud800": 1})


def test_canonical_json_diagnostics_use_positional_paths_not_keys() -> None:
    sentinel_key = "sk-sensitive-key"
    with pytest.raises(SchemaError) as excinfo:
        canonical_json({"a": 1, sentinel_key: float("nan")})
    message = str(excinfo.value)
    assert sentinel_key not in message
    assert message.startswith("$.key[1]")
    with pytest.raises(SchemaError) as excinfo:
        canonical_json({sentinel_key: {"inner": ["\ud800"]}})
    message = str(excinfo.value)
    assert sentinel_key not in message
    assert message.startswith("$.key[0].key[0][0]")
    with pytest.raises(SchemaError) as excinfo:
        canonical_json({sentinel_key + "\ud800": 1})
    assert sentinel_key not in str(excinfo.value)


def test_canonical_json_depth_limit() -> None:
    nested: Any = []
    for _ in range(MAX_JSON_DEPTH - 1):
        nested = [nested]
    canonical_json(nested)
    with pytest.raises(SchemaError, match="nesting"):
        canonical_json([nested])


@pytest.mark.parametrize(
    ("data", "digest"),
    [
        (b"", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
        (b"abc", "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"),
        (
            b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq",
            "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1",
        ),
        ("é".encode(), hashlib.sha256(b"\xc3\xa9").hexdigest()),
    ],
)
def test_sha256_known_vectors(data: bytes, digest: str) -> None:
    assert sha256_bytes(data) == digest
    assert len(digest) == 64
    assert digest == digest.lower()


def test_sha256_rejects_text() -> None:
    with pytest.raises(TypeError):
        sha256_bytes("text")  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# strict_json_loads
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("null", None),
        ("true", True),
        ("-0", 0),
        ("-12", -12),
        ("1.25e2", 125.0),
        ('"\\u00e9"', "é"),
        ('"é"', "é"),
        ("[1, 2, [3]]", [1, 2, [3]]),
        (' {"b": 1, "a": {"c": [true, null]}} ', {"b": 1, "a": {"c": [True, None]}}),
        ('"[{"', "[{"),
    ],
)
def test_strict_json_loads_accepts_valid_documents(text: str, expected: object) -> None:
    assert strict_json_loads(text) == expected


def _deep(depth: int) -> str:
    return "[" * depth + "]" * depth


def _deep_objects(depth: int) -> str:
    return '{"k":' * depth + "1" + "}" * depth


@pytest.mark.parametrize(
    "text",
    [
        "",
        " ",
        "nul",
        "+1",
        "01",
        "1.",
        ".5",
        "0x10",
        "NaN",
        "-NaN",
        "Infinity",
        "-Infinity",
        "[NaN]",
        '{"a": Infinity}',
        "1e400",
        "-1e400",
        "[1e999]",
        "'single'",
        '{"a": 1,}',
        "[1,]",
        '{"a" 1}',
        "{a: 1}",
        '{"a": 1} {"b": 2}',
        '{"a": 1} trailing',
        "[1] 2",
        '{"a": 1, "a": 2}',
        '{"a": 1, "b": {"c": 1, "c": 2}}',
        '{"a": [{"x": 1, "x": 1}]}',
        '[[[{"k": 1, "k": 1}]]]',
        '{"a": 1, "b": 2, "a": 3}',
        _deep(MAX_JSON_DEPTH + 1),
        _deep_objects(MAX_JSON_DEPTH + 1),
        _deep(5000),
        '{"k": ' + _deep(MAX_JSON_DEPTH) + "}",
        "﻿1",
        '"\\ud800"',
        '["ok", "\\udfff"]',
        '{"\\ud800": 1}',
        '{"a": {"b": {"\\udc00": 1}}}',
        "\x00",
    ],
)
def test_strict_json_loads_rejects_malformed_documents(text: str) -> None:
    with pytest.raises(SchemaError):
        strict_json_loads(text)


def test_strict_json_loads_accepts_depth_limit_exactly() -> None:
    assert strict_json_loads(_deep(MAX_JSON_DEPTH)) is not None
    assert strict_json_loads(_deep_objects(MAX_JSON_DEPTH)) is not None


def test_strict_json_loads_brackets_inside_strings_do_not_count_as_nesting() -> None:
    text = '"' + "[" * 100 + '\\"' + "{" * 100 + '"'
    assert strict_json_loads(text) == "[" * 100 + '"' + "{" * 100


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('"\\\\"', "\\"),
        ('"\\\\\\""', '\\"'),
        ('["\\"[[[", "\\\\", "}}}\\\\"]', ['"[[[', "\\", "}}}\\"]),
        ('{"\\"{": "[\\\\"}', {'"{': "[\\"}),
        ('"' + '\\"' * 500 + '"', '"' * 500),
        ('"' + "\\\\" * 500 + '"', "\\" * 500),
        ('["\\u005b\\u007b", [[]]]', ["[{", [[]]]),
        ('"\\\\' + "[" * 40 + '"', "\\" + "[" * 40),
    ],
)
def test_scan_handles_escaped_quotes_backslashes_and_brackets(text: str, expected: object) -> None:
    assert strict_json_loads(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        '"',
        '"\\',
        '"\\"',
        '"' + '\\"' * 1000,
        '"' + "\\\\" * 1001,
        '["\\"',
        '{"a": "\\\\\\"',
        '"\\u00',
        '["abc",',
        '"' + "[" * 100,
    ],
)
def test_scan_rejects_truncated_strings_without_hanging(text: str) -> None:
    with pytest.raises(SchemaError):
        strict_json_loads(text)


def test_scan_nested_depth_after_escaped_strings_is_still_enforced() -> None:
    prefix = '["\\"\\\\\\"", '
    assert strict_json_loads(prefix + _deep(MAX_JSON_DEPTH - 1) + "]") is not None
    with pytest.raises(SchemaError, match="nesting"):
        strict_json_loads(prefix + _deep(MAX_JSON_DEPTH) + "]")


def test_adversarial_escaped_quote_string_is_rejected_within_deadline() -> None:
    """A 2 MiB unterminated run of escaped quotes must not cost more than linear time.

    The child process has a coarse deadline; the prior regex scanner took over two
    seconds for 64 KiB of this shape and would never finish 2 MiB in time.
    """
    script = (
        "from actseal.errors import SchemaError\n"
        "from actseal.serialization import strict_json_loads\n"
        "for size in (65_536, 1_048_576):\n"
        "    text = '\"' + '\\\\\"' * size\n"
        "    try:\n"
        "        strict_json_loads(text)\n"
        "    except SchemaError:\n"
        "        continue\n"
        "    raise SystemExit('accepted malformed input')\n"
        "print('ok')\n"
    )
    result = subprocess.run(  # noqa: S603 - fixed interpreter and literal script, no user input
        [sys.executable, "-I", "-c", script],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    assert result.stdout.strip() == "ok"


def test_generic_parser_ceiling_is_128_mib() -> None:
    assert MAX_JSON_BYTES == 128 * 1024 * 1024


def test_strict_json_loads_accepts_aggregate_objects_above_one_mib() -> None:
    """The generic parser is not limited to 1 MiB; JSONL row limits live in readers."""
    rows = 4000
    row = '{"case_id":"c-%06d","state":"' + "s" * 500 + '","expected_label":"billing"}'
    text = "[" + ",".join(row % index for index in range(rows)) + "]"
    assert 2 * 1024 * 1024 < len(text.encode()) < 16 * 1024 * 1024
    parsed = strict_json_loads(text)
    assert isinstance(parsed, list)
    assert len(parsed) == rows
    assert parsed[-1] == {"case_id": "c-003999", "state": "s" * 500, "expected_label": "billing"}


def test_strict_json_loads_rejects_documents_above_the_ceiling() -> None:
    """One byte over the ceiling is refused before any scanning or parsing."""
    over = '"' + "x" * (MAX_JSON_BYTES - 1) + '"'
    assert len(over) == MAX_JSON_BYTES + 1
    with pytest.raises(SchemaError, match="bytes"):
        strict_json_loads(over)
    del over


def test_oversized_character_count_is_rejected_before_encoding() -> None:
    """Text longer than the limit in characters never reaches ``str.encode``."""
    calls: list[str] = []

    class Probe(str):
        __slots__ = ()

        def encode(self, encoding: str = "utf-8", errors: str = "strict") -> bytes:
            calls.append(encoding)
            return str.encode(str(self), encoding, errors)

    assert _exceeds_byte_limit(Probe("é" * 10), 5) is True
    assert calls == []
    assert _exceeds_byte_limit(Probe("abcdefghij"), 5) is True
    assert calls == []
    assert _exceeds_byte_limit(Probe("abcd"), 5) is False
    assert calls == []
    assert _exceeds_byte_limit(Probe("ééé"), 5) is True
    assert calls == ["utf-8"]
    assert _exceeds_byte_limit(Probe("éé"), 5) is False
    assert _exceeds_byte_limit("\ud800", 2) is True
    assert _exceeds_byte_limit("\ud800", 3) is False
    with pytest.raises(SchemaError, match="bytes"):
        strict_json_loads("é" * (MAX_JSON_BYTES // 2 + 1))


def test_strict_json_loads_size_limit_counts_bytes_not_characters() -> None:
    """A document that fits in characters but not in UTF-8 bytes is refused."""
    multibyte = '"' + "é" * (MAX_JSON_BYTES // 2) + '"'
    assert len(multibyte) < MAX_JSON_BYTES < len(multibyte.encode())
    with pytest.raises(SchemaError, match="bytes"):
        strict_json_loads(multibyte)
    del multibyte


def test_strict_json_loads_rejects_unpaired_surrogate_keys() -> None:
    with pytest.raises(SchemaError, match="Unicode"):
        strict_json_loads('{"\\ud800": 1}')
    with pytest.raises(SchemaError, match="Unicode"):
        strict_json_loads('{"ok": {"\\udfff": 1}}')


def test_strict_json_loads_accepts_paired_surrogate_escapes() -> None:
    assert strict_json_loads('{"\\ud83d\\ude00": "\\ud83d\\ude00"}') == {"\U0001f600": "\U0001f600"}


def test_strict_json_loads_errors_do_not_echo_input() -> None:
    sentinel = "sk-very-sensitive-value"
    with pytest.raises(SchemaError) as excinfo:
        strict_json_loads('{"' + sentinel + '": 1, "' + sentinel + '": 2}')
    assert sentinel not in str(excinfo.value)
    with pytest.raises(SchemaError) as excinfo:
        strict_json_loads(sentinel)
    assert sentinel not in str(excinfo.value)


# --------------------------------------------------------------------------- #
# to_data / from_data round trips
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name", RECORD_NAMES)
def test_every_record_round_trips_canonical_json(name: str) -> None:
    record = SAMPLE_BUILDERS[name]()
    record_type = RECORD_TYPES[name]
    data = to_data(record)
    assert type(data) is dict
    wire = canonical_json(data)
    parsed = strict_json_loads(wire.decode("utf-8"))
    rebuilt = from_data(record_type, parsed)
    assert rebuilt == record
    assert type(rebuilt) is record_type
    assert canonical_json(to_data(rebuilt)) == wire
    assert wire == wire.rstrip(b"\n")


@pytest.mark.parametrize("name", RECORD_NAMES)
def test_to_data_returns_fresh_json_data(name: str) -> None:
    record = SAMPLE_BUILDERS[name]()
    first = to_data(record)
    second = to_data(record)
    assert first == second
    assert first is not second
    canonical_json(first)

    def only_json(value: object) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                assert type(key) is str
                only_json(item)
        elif isinstance(value, list):
            for item in value:
                only_json(item)
        else:
            assert value is None or type(value) in {str, int, float, bool}

    only_json(first)


def test_independently_specified_wire_forms() -> None:
    identity = make_identity()
    assert to_data(identity) == {
        "provider": "fixture",
        "model": "recorded-choice-v1",
        "revision": HEX_A,
        "artifact_hashes": {"responses": HEX_A},
        "adapter_version": "1",
        "normalizer_version": "1",
        "runtime": {"os": "darwin", "python": "3.12"},
    }
    assert (
        canonical_json(to_data(identity))
        == (
            '{"adapter_version":"1","artifact_hashes":{"responses":"' + HEX_A + '"},'
            '"model":"recorded-choice-v1","normalizer_version":"1","provider":"fixture",'
            '"revision":"' + HEX_A + '","runtime":{"os":"darwin","python":"3.12"}}'
        ).encode()
    )

    answer = make_answer()
    assert to_data(answer) == {
        "choice": "billing",
        "probabilities": [["billing", 0.95], ["technical", 0.04], ["sales", 0.01]],
        "selected_probability": 0.95,
        "provider_confidence": 0.9,
        "warnings": ["w.calibration"],
        "fallback_used": False,
    }
    assert to_data(ProviderFailure("timeout", (), True)) == {
        "code": "timeout",
        "warnings": [],
        "fallback_used": True,
    }
    assert canonical_json(to_data(Interval(0, 1))) == b'{"lower":0.0,"upper":1.0}'
    assert canonical_json(to_data(Option("café", "☃"))) == (
        '{"description":"☃","label":"café"}'.encode()
    )

    record = make_record()
    record_data = to_data(record)
    assert record_data["outcome"] == {"kind": "answer", **to_data(answer)}
    assert record_data["capture"] == {
        "request_sha256": HEX_A,
        "identity": to_data(identity),
        "body_json": '{"type":"choice"}',
        "failure_code": None,
        "warnings": [],
        "fallback_used": False,
    }
    assert record_data["decision"] == {
        "action": "ACT",
        "choice": "billing",
        "reason": "policy.allowed",
        "fallback_used": False,
    }


def test_outcome_discriminator_round_trips_both_kinds() -> None:
    record = make_record()
    answer_data = to_data(record)
    assert answer_data["outcome"]["kind"] == "answer"  # type: ignore[index]
    assert isinstance(from_data(DecisionRecord, answer_data).outcome, ChoiceAnswer)

    failure_record = DecisionRecord(
        "v-001",
        record.capture,
        ProviderFailure("malformed_response", ("w",), False),
        actseal.PolicyDecision("ESCALATE", None, "provider.malformed_response", False),
    )
    failure_data = to_data(failure_record)
    assert failure_data["outcome"] == {
        "kind": "failure",
        "code": "malformed_response",
        "warnings": ["w"],
        "fallback_used": False,
    }
    rebuilt = from_data(DecisionRecord, failure_data)
    assert isinstance(rebuilt.outcome, ProviderFailure)
    assert rebuilt == failure_record


def test_top_level_outcome_records_have_no_kind_tag() -> None:
    assert "kind" not in to_data(make_answer())
    with pytest.raises(SchemaError, match="unknown"):
        from_data(ChoiceAnswer, {"kind": "answer", **to_data(make_answer())})


@pytest.mark.parametrize(
    "kind",
    ["", "Answer", "ANSWER", "success", "choice", "ChoiceAnswer", "actseal.records.ChoiceAnswer"],
)
def test_unsupported_discriminator_is_rejected(kind: str) -> None:
    data = to_data(make_record())
    _set_path(data, ("outcome", "kind"), kind)
    with pytest.raises(SchemaError, match=r"outcome\.kind"):
        from_data(DecisionRecord, data)


@pytest.mark.parametrize("bad_kind", [None, 1, True, ["answer"], {"kind": "answer"}])
def test_non_string_discriminator_is_rejected(bad_kind: object) -> None:
    data = to_data(make_record())
    _set_path(data, ("outcome", "kind"), bad_kind)
    with pytest.raises(SchemaError, match=r"outcome\.kind"):
        from_data(DecisionRecord, data)


def test_missing_discriminator_is_rejected() -> None:
    data = to_data(make_record())
    _del_path(data, ("outcome", "kind"))
    with pytest.raises(SchemaError, match=r"outcome\.kind"):
        from_data(DecisionRecord, data)


def _set_path(data: Any, path: tuple[Any, ...], value: object) -> None:
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value


def _del_path(data: Any, path: tuple[Any, ...]) -> None:
    target = data
    for key in path[:-1]:
        target = target[key]
    del target[path[-1]]


BAD_WIRE: list[tuple[str, str, tuple[Any, ...], object]] = [
    ("Option bool label", "Option", ("label",), True),
    ("Option int label", "Option", ("label",), 1),
    ("Option null label", "Option", ("label",), None),
    ("Question options object", "ChoiceQuestion", ("options",), {}),
    ("Question options string", "ChoiceQuestion", ("options",), "ab"),
    ("Question option scalar", "ChoiceQuestion", ("options", 0), "billing"),
    ("Question option unknown field", "ChoiceQuestion", ("options", 0, "extra"), 1),
    ("Question option bad label", "ChoiceQuestion", ("options", 1, "label"), ""),
    ("Question duplicate labels", "ChoiceQuestion", ("options", 1, "label"), "billing"),
    ("CaseRef uppercase", "CaseRef", ("sha256",), HEX_A.upper()),
    ("Identity artifact list", "ModelIdentity", ("artifact_hashes",), [["a", HEX_A]]),
    ("Identity artifact int value", "ModelIdentity", ("artifact_hashes",), {"a": 1}),
    ("Identity artifact bad hash", "ModelIdentity", ("artifact_hashes",), {"a": "nope"}),
    ("Identity runtime list", "ModelIdentity", ("runtime",), []),
    ("Identity runtime nested", "ModelIdentity", ("runtime",), {"a": {"b": "c"}}),
    ("Identity runtime empty key", "ModelIdentity", ("runtime",), {"": "x"}),
    ("Capture both present", "CapturedOutcome", ("failure_code",), "timeout"),
    ("Capture unknown code", "CapturedOutcome", ("body_json",), None),
    ("Capture int fallback", "CapturedOutcome", ("fallback_used",), 0),
    ("Capture str fallback", "CapturedOutcome", ("fallback_used",), "false"),
    ("Capture identity scalar", "CapturedOutcome", ("identity",), "fixture"),
    ("Capture identity unknown field", "CapturedOutcome", ("identity", "device"), "cpu"),
    ("Capture warnings object", "CapturedOutcome", ("warnings",), {}),
    ("Capture warning int", "CapturedOutcome", ("warnings",), [1]),
    ("Answer probabilities object", "ChoiceAnswer", ("probabilities",), {"billing": 1.0}),
    ("Answer probability triple", "ChoiceAnswer", ("probabilities", 0), ["billing", 0.95, 1]),
    ("Answer probability single", "ChoiceAnswer", ("probabilities", 0), ["billing"]),
    ("Answer probability object", "ChoiceAnswer", ("probabilities", 0), {"billing": 0.95}),
    ("Answer probability bool", "ChoiceAnswer", ("probabilities", 0), ["billing", True]),
    ("Answer probability string", "ChoiceAnswer", ("probabilities", 0), ["billing", "0.95"]),
    ("Answer probability negative", "ChoiceAnswer", ("probabilities", 0), ["billing", -0.95]),
    ("Answer selected bool", "ChoiceAnswer", ("selected_probability",), True),
    ("Answer selected string", "ChoiceAnswer", ("selected_probability",), "0.95"),
    ("Answer selected mismatch", "ChoiceAnswer", ("selected_probability",), 0.5),
    ("Answer confidence bool", "ChoiceAnswer", ("provider_confidence",), False),
    ("Answer confidence > 1", "ChoiceAnswer", ("provider_confidence",), 2),
    ("Answer choice unknown", "ChoiceAnswer", ("choice",), "legal"),
    ("Failure unknown code", "ProviderFailure", ("code",), "crash"),
    ("Failure code int", "ProviderFailure", ("code",), 7),
    ("Policy threshold bool", "LockedPolicy", ("threshold",), True),
    ("Policy threshold zero", "LockedPolicy", ("threshold",), 0),
    ("Policy threshold above one", "LockedPolicy", ("threshold",), 1.0000001),
    ("Policy allowed outside known", "LockedPolicy", ("allowed_labels",), ["legal"]),
    ("Policy allowed string", "LockedPolicy", ("allowed_labels",), "billing"),
    ("Limits alpha one", "GateLimits", ("alpha",), 1),
    ("Limits alpha bool", "GateLimits", ("alpha",), True),
    ("Limits risk string", "GateLimits", ("max_risk",), "0.05"),
    ("Limits coverage negative", "GateLimits", ("min_coverage",), -1),
    ("Contract version 2", "Contract", ("schema_version",), 2),
    ("Contract version float", "Contract", ("schema_version",), 1.0),
    ("Contract version bool", "Contract", ("schema_version",), True),
    ("Contract version string", "Contract", ("schema_version",), "1"),
    ("Contract scope upper", "Contract", ("evidence_scope",), "DEMO"),
    ("Contract scope unknown", "Contract", ("evidence_scope",), "production"),
    ("Contract policy mismatch", "Contract", ("policy", "known_labels"), ["billing", "sales"]),
    ("Contract nested unknown field", "Contract", ("limits", "beta"), 0.1),
    ("FaultSpec action unknown", "FaultSpec", ("expected_action",), "ALLOW"),
    ("FaultSpec action lowercase", "FaultSpec", ("expected_action",), "escalate"),
    ("Lock version 0", "PlanLock", ("schema_version",), 0),
    ("Lock version negative", "PlanLock", ("schema_version",), -1),
    ("Lock bad seal", "PlanLock", ("sha256",), "0" * 63),
    ("Lock bad implementation hash", "PlanLock", ("implementation_sha256",), HEX_A + "0"),
    ("Lock cases mismatch", "PlanLock", ("verification_cases", 0, "case_id"), "v-002"),
    ("Lock case unknown label", "PlanLock", ("verification_cases", 0, "expected_label"), "legal"),
    ("Lock inventory empty", "PlanLock", ("calibration_inventory",), []),
    ("Lock inventory duplicate", "PlanLock", ("calibration_inventory", 1, "case_id"), "c-001"),
    ("Lock fault duplicate", "PlanLock", ("fault_inventory", 1, "scenario_id"), "fault.timeout"),
    ("Lock deep unknown field", "PlanLock", ("contract", "question", "options", 0, "x"), 1),
    ("Lock deep bad enum", "PlanLock", ("contract", "evidence_scope"), "x"),
    ("Decision action unknown", "PolicyDecision", ("action",), "ALLOW"),
    ("Decision ACT without choice", "PolicyDecision", ("choice",), None),
    ("Decision choice int", "PolicyDecision", ("choice",), 1),
    ("Decision fallback int", "PolicyDecision", ("fallback_used",), 1),
    ("Record outcome scalar", "DecisionRecord", ("outcome",), "answer"),
    ("Record outcome list", "DecisionRecord", ("outcome",), ["answer"]),
    ("Record outcome missing field", "DecisionRecord", ("outcome",), {"kind": "answer"}),
    ("Record outcome extra field", "DecisionRecord", ("outcome", "extra"), 1),
    ("Record fallback mismatch", "DecisionRecord", ("decision", "fallback_used"), True),
    ("Record decision scalar", "DecisionRecord", ("decision",), "ACT"),
    ("FaultResult request scalar", "FaultResult", ("request",), "r"),
    ("FaultResult nested bad hash", "FaultResult", ("capture", "request_sha256"), "x"),
    ("FaultResult outcome bad code", "FaultResult", ("outcome", "code"), "nope"),
    ("Interval lower > upper", "Interval", ("lower",), 0.5),
    ("Interval above one", "Interval", ("upper",), 1.5),
    ("Interval bool", "Interval", ("lower",), False),
    ("Interval string", "Interval", ("lower",), "0"),
    ("Verdict status unknown", "Verdict", ("status",), "OK"),
    ("Verdict reasons unsorted", "Verdict", ("reasons",), ["b", "a"]),
    ("Verdict reasons duplicate", "Verdict", ("reasons",), ["a", "a"]),
    ("Verdict total bool", "Verdict", ("total",), True),
    ("Verdict total float", "Verdict", ("total",), 1.0),
    ("Verdict total negative", "Verdict", ("total",), -1),
    ("Verdict accepted > total", "Verdict", ("accepted",), 5),
    ("Verdict errors > accepted", "Verdict", ("errors",), 5),
    ("Verdict risk scalar", "Verdict", ("risk",), 0.5),
    ("Verdict risk unknown field", "Verdict", ("risk", "mid"), 0.5),
    ("Verdict scope unknown", "Verdict", ("evidence_scope",), "prod"),
    ("Verdict ERROR with counts", "Verdict", ("status",), "ERROR"),
    ("Bundle records mismatch", "EvidenceBundle", ("records", 0, "case_id"), "v-002"),
    ("Bundle faults mismatch", "EvidenceBundle", ("faults", 0, "scenario_id"), "fault.other"),
    ("Bundle verdict hash mismatch", "EvidenceBundle", ("verdict", "lock_sha256"), HEX_B),
    ("Bundle scope mismatch", "EvidenceBundle", ("verdict", "evidence_scope"), "iid"),
    ("Bundle empty jsonl", "EvidenceBundle", ("calibration_jsonl",), ""),
    ("Bundle records object", "EvidenceBundle", ("records",), {}),
    ("Bundle lock scalar", "EvidenceBundle", ("lock",), HEX_A),
    ("Bundle deep nonfinite", "EvidenceBundle", ("lock", "contract", "limits", "alpha"), 1e400),
    ("Identity provider unknown", "ModelIdentity", ("provider",), "jev"),
    ("Identity provider case", "ModelIdentity", ("provider",), "Fixture"),
    ("Identity provider empty", "ModelIdentity", ("provider",), ""),
    (
        "Answer mass zero",
        "ChoiceAnswer",
        ("probabilities",),
        [["billing", 0.0], ["technical", 0.0], ["sales", 0.0]],
    ),
    (
        "Answer mass two",
        "ChoiceAnswer",
        ("probabilities",),
        [["billing", 0.95], ["technical", 0.95], ["sales", 0.1]],
    ),
    (
        "Answer mass slightly high",
        "ChoiceAnswer",
        ("probabilities",),
        [["billing", 0.95], ["technical", 0.04], ["sales", 0.01 + 1e-11]],
    ),
    ("Verdict PASS without accepted", "Verdict", ("accepted",), 0),
    ("Limits overflow integer", "GateLimits", ("max_risk",), 10**400),
    ("Interval overflow integer", "Interval", ("upper",), 10**400),
    ("Policy overflow integer", "LockedPolicy", ("threshold",), 10**400),
    ("Answer overflow integer", "ChoiceAnswer", ("selected_probability",), 10**400),
]


@pytest.mark.parametrize(("label", "name", "path", "value"), BAD_WIRE, ids=lambda v: str(v)[:40])
def test_from_data_rejects_malformed_wire(label: str, name: str, path: Any, value: object) -> None:
    data = to_data(SAMPLE_BUILDERS[name]())
    _set_path(data, path, value)
    with pytest.raises(SchemaError) as excinfo:
        from_data(RECORD_TYPES[name], data)
    message = str(excinfo.value)
    assert message.startswith(name), label
    assert str(path[0]) in message, label


@pytest.mark.parametrize("name", RECORD_NAMES)
def test_from_data_rejects_unknown_and_missing_fields(name: str) -> None:
    record_type = RECORD_TYPES[name]
    data = to_data(SAMPLE_BUILDERS[name]())
    first_field = next(iter(data))

    extra = {**data, "unexpected": 1}
    with pytest.raises(SchemaError, match="unknown") as excinfo:
        from_data(record_type, extra)
    assert "unexpected" not in str(excinfo.value)

    missing = {key: value for key, value in data.items() if key != first_field}
    with pytest.raises(SchemaError, match=f"missing fields {first_field}"):
        from_data(record_type, missing)

    renamed = {**missing, first_field.upper() + "_x": data[first_field]}
    with pytest.raises(SchemaError, match="missing"):
        from_data(record_type, renamed)


@pytest.mark.parametrize("value", [None, 1, "x", [], [{}], True, ()])
def test_from_data_rejects_non_objects(value: object) -> None:
    with pytest.raises(SchemaError, match="expected object"):
        from_data(Option, value)


def test_from_data_rejects_unsupported_record_types() -> None:
    with pytest.raises(SchemaError, match="unsupported record type"):
        from_data(dict, {})  # type: ignore[type-var]
    with pytest.raises(SchemaError, match="unsupported record type"):
        from_data(str, "x")  # type: ignore[type-var]


def test_to_data_rejects_non_records() -> None:
    for value in ({}, "x", None, 1, [Option("a", "b")], object()):
        with pytest.raises(SchemaError, match="unsupported record type"):
            to_data(value)


def test_from_data_does_not_alias_input_containers() -> None:
    data = to_data(make_record())
    snapshot = copy.deepcopy(data)
    record = from_data(DecisionRecord, data)
    assert data == snapshot
    _set_path(data, ("outcome", "probabilities", 0, 1), 0.0)
    capture: Any = data["capture"]
    capture["warnings"].append("mutated")
    assert record.outcome == make_record().outcome
    assert record.capture.warnings == ()


def test_from_data_error_paths_disclose_location_not_value() -> None:
    sentinel = "sk-sensitive-value"
    data = to_data(SAMPLE_BUILDERS["PlanLock"]())
    _set_path(data, ("contract", "question", "options", 1, "label"), sentinel)
    _set_path(data, ("contract", "policy", "known_labels", 1), sentinel)
    _set_path(data, ("model_identity", "artifact_hashes"), {"weights": sentinel})
    with pytest.raises(SchemaError) as excinfo:
        from_data(PlanLock, data)
    message = str(excinfo.value)
    assert message.startswith("PlanLock.contract.policy")
    assert sentinel not in message


@pytest.mark.parametrize(
    ("name", "path"),
    [
        ("Option", ("label",)),
        ("Option", ("description",)),
        ("Case", ("state",)),
        ("ModelIdentity", ("revision",)),
        ("ModelIdentity", ("runtime", "python")),
        ("CapturedOutcome", ("body_json",)),
        ("CapturedOutcome", ("identity", "runtime", "os")),
        ("ChoiceAnswer", ("probabilities", 0, 0)),
        ("ChoiceAnswer", ("warnings", 0)),
        ("LockedPolicy", ("known_labels", 0)),
        ("PolicyDecision", ("choice",)),
        ("PlanLock", ("contract", "question", "options", 1, "description")),
        ("EvidenceBundle", ("verification_jsonl",)),
        ("Verdict", ("reasons", 0)),
    ],
)
@pytest.mark.parametrize("bad", ["\ud800", "x\udfffy"])
def test_from_data_rejects_unpaired_surrogate_strings(name: str, path: Any, bad: str) -> None:
    """Python data can carry lone surrogates even though strict JSON text cannot."""
    data = to_data(SAMPLE_BUILDERS[name]())
    _set_path(data, path, bad)
    with pytest.raises(SchemaError, match="Unicode") as excinfo:
        from_data(RECORD_TYPES[name], data)
    message = str(excinfo.value)
    assert message.startswith(name)
    assert bad not in message
    assert message.isascii()


def test_from_data_rejects_unpaired_surrogate_map_keys() -> None:
    data = to_data(SAMPLE_BUILDERS["ModelIdentity"]())
    _set_path(data, ("runtime",), {"\ud800": "v"})
    with pytest.raises(SchemaError, match="Unicode") as excinfo:
        from_data(ModelIdentity, data)
    assert str(excinfo.value).isascii()
    _set_path(data, ("runtime",), {"k": "v"})
    _set_path(data, ("artifact_hashes",), {"w\udc00": HEX_A})
    with pytest.raises(SchemaError, match="Unicode") as excinfo:
        from_data(ModelIdentity, data)
    assert str(excinfo.value).isascii()


def test_every_accepted_record_with_valid_non_ascii_round_trips() -> None:
    text = "café ☃ \U0001f600 Ж"
    question = ChoiceQuestion(text, text, (Option(text, text), Option("b", text)))
    data = to_data(question)
    wire = canonical_json(data)
    assert text.encode("utf-8") in wire
    assert from_data(ChoiceQuestion, strict_json_loads(wire.decode("utf-8"))) == question


def test_from_data_accepts_integers_for_float_fields() -> None:
    interval = from_data(Interval, {"lower": 0, "upper": 1})
    assert interval == Interval(0.0, 1.0)
    assert type(interval.lower) is float


def test_from_data_accepts_json_key_order_independence() -> None:
    question = ChoiceQuestion("q", "i", (Option("b", "B"), Option("a", "A")))
    data = to_data(question)
    assert data["options"] == [
        {"label": "b", "description": "B"},
        {"label": "a", "description": "A"},
    ]
    assert from_data(ChoiceQuestion, data) == question
    assert from_data(ChoiceQuestion, dict(reversed(list(data.items())))) == question


def test_identity_map_round_trip_sorts_keys() -> None:
    identity = ModelIdentity(
        "laya", "m", "r", (("z", HEX_A), ("a", HEX_B)), "1", "1", (("k2", "v"), ("k1", "v"))
    )
    data = to_data(identity)
    assert list(data["runtime"]) == ["k1", "k2"]  # type: ignore[call-overload]
    assert from_data(ModelIdentity, data) == identity
    wire = canonical_json(data)
    assert (
        b'"artifact_hashes":{"a":"' + HEX_B.encode() + b'","z":"' + HEX_A.encode() + b'"}' in wire
    )


def test_wire_duplicate_keys_inside_record_are_rejected_at_every_level() -> None:
    wire = canonical_json(to_data(make_record())).decode()
    injected = wire.replace('"case_id":"v-001"', '"case_id":"v-001","case_id":"v-001"', 1)
    assert injected != wire
    with pytest.raises(SchemaError, match="duplicate"):
        strict_json_loads(injected)
    nested = wire.replace('"warnings":[]', '"warnings":[],"warnings":[]', 1)
    with pytest.raises(SchemaError, match="duplicate"):
        strict_json_loads(nested)


def test_fault_result_round_trip_with_failure_outcome() -> None:
    fault = SAMPLE_BUILDERS["FaultResult"]()
    data = to_data(fault)
    assert data["outcome"] == {
        "kind": "failure",
        "code": "timeout",
        "warnings": [],
        "fallback_used": False,
    }
    rebuilt = from_data(FaultResult, strict_json_loads(canonical_json(data).decode()))
    assert rebuilt == fault
    assert isinstance(rebuilt.outcome, ProviderFailure)


def test_verdict_error_round_trip() -> None:
    verdict = Verdict(
        "ERROR", ("integrity.lock",), 0, 0, 0, Interval(0, 1), Interval(0, 1), "demo", HEX_A
    )
    assert from_data(Verdict, to_data(verdict)) == verdict


# --------------------------------------------------------------------------- #
# implementation_fingerprint
# --------------------------------------------------------------------------- #


def test_implementation_fingerprint_is_a_stable_sha256() -> None:
    first = implementation_fingerprint()
    assert len(first) == 64
    assert first == first.lower()
    assert int(first, 16) >= 0
    assert implementation_fingerprint() == first


def test_implementation_fingerprint_matches_independent_computation() -> None:
    package_dir = Path(actseal.__file__).resolve().parent
    entries: dict[str, str] = {}
    for file in package_dir.rglob("*.py"):
        if "__pycache__" in file.parts:
            continue
        key = "actseal/" + file.relative_to(package_dir).as_posix()
        entries[key] = hashlib.sha256(file.read_bytes()).hexdigest()
    assert set(entries) >= {
        "actseal/__init__.py",
        "actseal/errors.py",
        "actseal/records.py",
        "actseal/serialization.py",
    }
    text = json.dumps(entries, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert implementation_fingerprint() == hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_implementation_fingerprint_is_stable_across_roots_and_ignores_noise(
    tmp_path: Path,
) -> None:
    package_dir = Path(actseal.__file__).resolve().parent
    expected = implementation_fingerprint()

    def copy_sources(root: Path) -> Path:
        destination = root / "actseal"
        shutil.copytree(
            package_dir, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
        )
        return destination

    copy_a = copy_sources(tmp_path / "site-packages-a")
    copy_b = copy_sources(tmp_path / "another" / "deeper" / "root")
    assert _fingerprint_tree(copy_a, "actseal") == expected
    assert _fingerprint_tree(copy_b, "actseal") == expected

    (copy_b / "__pycache__").mkdir()
    (copy_b / "__pycache__" / "records.cpython-312.pyc").write_bytes(b"\x00compiled")
    (copy_b / "__pycache__" / "sneaky.py").write_text("print('ignored')\n")
    (copy_b / "notes.txt").write_text("not source\n")
    (copy_b / "data.json").write_text("{}\n")
    (copy_b / "py.typed").write_text("marker changed\n")
    assert _fingerprint_tree(copy_b, "actseal") == expected

    (copy_b / "records.py").write_bytes((copy_b / "records.py").read_bytes() + b"\n# changed\n")
    assert _fingerprint_tree(copy_b, "actseal") != expected

    (copy_a / "extra.py").write_text("")
    assert _fingerprint_tree(copy_a, "actseal") != expected


def test_implementation_fingerprint_does_not_execute_sources(tmp_path: Path) -> None:
    root = tmp_path / "actseal"
    root.mkdir()
    marker = tmp_path / "executed"
    (root / "__init__.py").write_text(f"open({str(marker)!r}, 'w').close()\n")
    (root / "sub").mkdir()
    (root / "sub" / "mod.py").write_text("raise SystemExit(99)\n")
    digest = _fingerprint_tree(root, "actseal")
    assert len(digest) == 64
    assert not marker.exists()


# --------------------------------------------------------------------------- #
# Packaging and environment guarantees
# --------------------------------------------------------------------------- #

OPTIONAL_MODULES = ("laya", "torch", "transformers", "huggingface_hub", "safetensors", "numpy")
ACTSEAL_SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "actseal"


def test_package_import_and_serialization_do_not_import_optional_stack() -> None:
    script = (
        "import sys\n"
        "import actseal\n"
        "from actseal import from_data, to_data, canonical_json, strict_json_loads\n"
        "o = actseal.Option('a', 'b')\n"
        "wire = canonical_json(to_data(o)).decode()\n"
        "assert from_data(actseal.Option, strict_json_loads(wire)) == o\n"
        "actseal.implementation_fingerprint()\n"
        f"loaded = sorted(m for m in sys.modules if m.split('.')[0] in {OPTIONAL_MODULES!r})\n"
        "assert loaded == [], loaded\n"
        "assert actseal.__version__ == '0.1.0'\n"
        "print('ok')\n"
    )
    result = subprocess.run(  # noqa: S603 - fixed interpreter and literal script, no user input
        [sys.executable, "-I", "-c", script],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    assert result.stdout.strip() == "ok"


def test_optional_stack_is_absent_from_default_environment() -> None:
    """Importing the core modules this file exercises must not load any optional root.

    The check runs in a fresh isolated interpreter. The shared pytest process may
    already hold Laya or NumPy after genuine native integration tests, which says
    nothing about what the core import graph pulls in.
    """
    script = (
        "import json\n"
        "import sys\n"
        "import actseal\n"
        "import actseal.errors\n"
        "import actseal.records\n"
        "import actseal.serialization\n"
        f"roots = {OPTIONAL_MODULES!r}\n"
        "loaded = sorted({m.split('.')[0] for m in sys.modules if m.split('.')[0] in roots})\n"
        "print(json.dumps({'actseal_file': actseal.__file__, 'loaded': loaded}))\n"
        "print('optional-stack-absent')\n"
    )
    result = subprocess.run(  # noqa: S603 - fixed interpreter and literal script, no user input
        [sys.executable, "-I", "-c", script],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    lines = result.stdout.splitlines()
    assert lines[-1:] == ["optional-stack-absent"], result.stdout[-2000:]
    report = json.loads(lines[-2])
    assert Path(report["actseal_file"]).resolve() == ACTSEAL_SOURCE_ROOT / "__init__.py"
    for module in OPTIONAL_MODULES:
        assert module not in report["loaded"], report["loaded"]


def test_public_api_surface() -> None:
    expected = {
        "ActsealError",
        "SchemaError",
        "IntegrityError",
        "ProviderSetupError",
        "canonical_json",
        "sha256_bytes",
        "strict_json_loads",
        "to_data",
        "from_data",
        "implementation_fingerprint",
        "Action",
        "Status",
        "EvidenceScope",
        "Outcome",
        *RECORD_NAMES,
    }
    assert expected <= set(actseal.__all__)
    assert not hasattr(actseal, "main")


def test_unit_tests_cannot_open_sockets() -> None:
    with pytest.raises(RuntimeError, match="disabled"):
        socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with pytest.raises(RuntimeError, match="disabled"):
        socket.create_connection(("127.0.0.1", 9))


@pytest.mark.integration
def test_integration_marker_is_exempt_from_offline_guard() -> None:
    assert isinstance(socket.socket, type)
    assert socket.create_connection.__name__ == "create_connection"
    assert socket.getaddrinfo.__name__ == "getaddrinfo"
