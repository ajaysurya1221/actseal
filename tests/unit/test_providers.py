"""Providers: protocol conformance, fixture adapter, and the Laya worker lifecycle.

Laya tests never import the native stack. The subprocess lifecycle is exercised
with a tiny fake worker script that speaks the adapter's JSON-lines protocol,
and the worker-side preflight/inference seam is exercised in-process with a
fake tokenizer/packing object and a spy in place of ``predict``.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import time
import warnings
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import pytest

from actseal.adapters.base import DecisionModel
from actseal.adapters.fixture import MAX_FIXTURE_BYTES, FixtureModel
from actseal.adapters.laya import (
    ADAPTER_VERSION,
    ARTIFACT_HASHES,
    HEAD_MAX_LEN,
    MAX_LEN,
    MODEL_ID,
    OPTION_BUDGET,
    OPTION_TOKEN_LIMIT,
    REVISION,
    STARTUP_TIMEOUT_S,
    THREADS,
    LayaModel,
    _infer,
    _native_worker_command,
    _question_payload,
)
from actseal.errors import ProviderSetupError, SchemaError
from actseal.normalization import NORMALIZER_VERSION, normalize, request_sha256
from actseal.records import (
    CapturedOutcome,
    ChoiceAnswer,
    ChoiceQuestion,
    DecisionRequest,
    ModelIdentity,
    Option,
    ProviderFailure,
)
from actseal.serialization import sha256_bytes
from conftest import make_question, make_request
from provider_support import (
    FAKE_WORKER,
    ROW_FAIL,
    ROW_OK,
    child_alive,
    pinned_identity,
    spawn,
    write_fake_worker,
    write_rows,
)

# Re-exported for tests/unit/test_runner.py and tests/unit/test_cli.py, which import the
# fake worker and the pinned identity from this module; the definitions now live in
# tests/provider_support.py so the conformance suite can share them.
__all__ = ["FAKE_WORKER", "pinned_identity"]

# --------------------------------------------------------------------------- #
# Fixture adapter
# --------------------------------------------------------------------------- #


@pytest.fixture
def responses(tmp_path: Path) -> tuple[Path, bytes]:
    path = tmp_path / "responses.jsonl"
    data = write_rows(path, [ROW_OK, ROW_FAIL])
    return path, data


def test_fixture_identity_is_derived_from_raw_bytes(responses: tuple[Path, bytes]) -> None:
    path, data = responses
    model = FixtureModel(path)
    identity = model.identity()
    expected_hash = sha256_bytes(data)
    assert identity == ModelIdentity(
        "fixture",
        "recorded-choice-v1",
        expected_hash,
        (("responses", expected_hash),),
        "1",
        NORMALIZER_VERSION,
        (),
    )
    assert model.identity() == identity
    model.close()


def test_fixture_identity_changes_with_any_byte(tmp_path: Path) -> None:
    first = tmp_path / "a.jsonl"
    second = tmp_path / "b.jsonl"
    write_rows(first, [ROW_OK])
    write_rows(second, [ROW_OK], trailing_newline=False)
    assert FixtureModel(first).identity().revision != FixtureModel(second).identity().revision


def test_fixture_rows_cannot_supply_identity(tmp_path: Path) -> None:
    path = tmp_path / "r.jsonl"
    write_rows(path, [{**ROW_OK, "identity": {"provider": "laya"}}])
    with pytest.raises(SchemaError, match=r"responses\[0\]"):
        FixtureModel(path)


def test_fixture_capture_matches_row_and_request(responses: tuple[Path, bytes]) -> None:
    path, _ = responses
    model = FixtureModel(path)
    request = make_request()
    capture = model.decide(request, timeout_s=30.0)
    assert capture == CapturedOutcome(
        request_sha256(request), model.identity(), ROW_OK["body_json"], None, (), False
    )
    failed = model.decide(DecisionRequest("v-002", "s", make_question()), timeout_s=1.5)
    assert failed.body_json is None
    assert failed.failure_code == "timeout"
    assert failed.warnings == ("w.slow",)
    assert failed.fallback_used is False
    assert failed.request_sha256 != capture.request_sha256


def test_fixture_body_text_is_preserved_verbatim(tmp_path: Path) -> None:
    path = tmp_path / "r.jsonl"
    odd = (
        '{ "type" : "choice" ,"choice":"billing",'
        '"probabilities":{"billing":1,"technical":0,"sales":0} }'
    )
    write_rows(path, [{**ROW_OK, "body_json": odd}])
    capture = FixtureModel(path).decide(make_request(), timeout_s=30.0)
    assert capture.body_json == odd
    answer = normalize(capture, make_question(), FixtureModel(path).identity())
    assert isinstance(answer, ChoiceAnswer)
    assert answer.selected_probability == 1.0


def test_fixture_captures_are_deterministic(responses: tuple[Path, bytes]) -> None:
    path, _ = responses
    first = FixtureModel(path)
    second = FixtureModel(path)
    request = make_request()
    assert first.decide(request, timeout_s=30.0) == second.decide(request, timeout_s=30.0)
    assert first.decide(request, timeout_s=30.0) == first.decide(request, timeout_s=30.0)


def test_fixture_missing_requested_case_is_setup_error(responses: tuple[Path, bytes]) -> None:
    path, _ = responses
    model = FixtureModel(path)
    request = DecisionRequest("v-999-SECRET", "s", make_question())
    with pytest.raises(ProviderSetupError) as info:
        model.decide(request, timeout_s=30.0)
    assert "SECRET" not in str(info.value)


def test_fixture_duplicate_case_id_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "r.jsonl"
    write_rows(path, [ROW_OK, {**ROW_FAIL, "case_id": "v-001"}])
    with pytest.raises(SchemaError, match=r"responses\[1\].case_id"):
        FixtureModel(path)


@pytest.mark.parametrize(
    "row",
    [
        {k: v for k, v in ROW_OK.items() if k != "warnings"},
        {k: v for k, v in ROW_OK.items() if k != "case_id"},
        {k: v for k, v in ROW_OK.items() if k != "failure_code"},
        {k: v for k, v in ROW_OK.items() if k != "body_json"},
        {**ROW_OK, "extra": 1},
        {**ROW_OK, "case_id": ""},
        {**ROW_OK, "case_id": 7},
        {**ROW_OK, "body_json": {"type": "choice"}},
        {**ROW_OK, "body_json": 1},
        {**ROW_OK, "body_json": None},
        {**ROW_OK, "failure_code": "timeout"},
        {**ROW_OK, "failure_code": "unknown"},
        {**ROW_FAIL, "failure_code": ""},
        {**ROW_FAIL, "failure_code": "TIMEOUT"},
        {**ROW_FAIL, "failure_code": 1},
        {**ROW_OK, "warnings": "w"},
        {**ROW_OK, "warnings": [1]},
        {**ROW_OK, "warnings": [""]},
        {**ROW_OK, "warnings": None},
        {**ROW_OK, "fallback_used": True},
        [],
        "null",
        '"row"',
        "1",
        "{",
        '{"case_id": "a", "case_id": "a"}',
        "",
    ],
)
def test_fixture_bad_row_schema_is_rejected(tmp_path: Path, row: object) -> None:
    path = tmp_path / "r.jsonl"
    write_rows(path, [ROW_OK, row])
    with pytest.raises(SchemaError, match=r"responses\[1\]"):
        FixtureModel(path)


def test_fixture_rejects_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "r.jsonl"
    path.write_bytes(b"")
    with pytest.raises(SchemaError, match="responses"):
        FixtureModel(path)


def test_fixture_rejects_invalid_utf8(tmp_path: Path) -> None:
    path = tmp_path / "r.jsonl"
    path.write_bytes(b'{"case_id": "\xff"}\n')
    with pytest.raises(SchemaError, match="responses"):
        FixtureModel(path)


def test_fixture_rejects_oversized_row(tmp_path: Path) -> None:
    path = tmp_path / "r.jsonl"
    big = {**ROW_OK, "body_json": "x" * (1024 * 1024)}
    write_rows(path, [big])
    with pytest.raises(SchemaError, match=r"responses\[0\]"):
        FixtureModel(path)


def test_fixture_accepts_row_at_size_limit(tmp_path: Path) -> None:
    path = tmp_path / "r.jsonl"
    prefix = json.dumps({**ROW_OK, "body_json": ""})
    filler = "x" * (1024 * 1024 - len(prefix.encode("utf-8")))
    write_rows(path, [{**ROW_OK, "body_json": filler}])
    assert len(path.read_bytes()) == 1024 * 1024 + 1
    FixtureModel(path).close()


def test_fixture_missing_file_is_setup_error(tmp_path: Path) -> None:
    with pytest.raises(ProviderSetupError):
        FixtureModel(tmp_path / "absent.jsonl")


def test_fixture_rejects_file_over_128_mib_of_legal_rows(tmp_path: Path) -> None:
    path = tmp_path / "r.jsonl"
    body = "x" * 1_040_000  # each row stays under the 1 MiB row limit
    rows: list[object] = [
        {**ROW_OK, "case_id": f"v-{i:03d}", "body_json": body} for i in range(130)
    ]
    write_rows(path, rows)
    assert path.stat().st_size > MAX_FIXTURE_BYTES
    with pytest.raises(SchemaError, match="responses: file exceeds"):
        FixtureModel(path)


def test_fixture_aggregate_limit_boundary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    limit = 4096
    monkeypatch.setattr("actseal.adapters.fixture.MAX_FIXTURE_BYTES", limit)
    path = tmp_path / "r.jsonl"
    prefix = json.dumps({**ROW_OK, "body_json": ""})
    filler = "x" * (limit - len(prefix.encode("utf-8")) - 1)
    write_rows(path, [{**ROW_OK, "body_json": filler}])
    assert path.stat().st_size == limit
    FixtureModel(path).close()
    path.write_bytes(path.read_bytes() + b"\n")
    assert path.stat().st_size == limit + 1
    with pytest.raises(SchemaError, match="responses: file exceeds"):
        FixtureModel(path)


def test_fixture_aggregate_limit_precedes_row_parsing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    limit = 4096
    monkeypatch.setattr("actseal.adapters.fixture.MAX_FIXTURE_BYTES", limit)
    path = tmp_path / "r.jsonl"
    path.write_bytes(b"{" * (10 * limit))  # invalid rows and far over the limit
    with pytest.raises(SchemaError, match="responses: file exceeds"):
        FixtureModel(path)


@pytest.mark.parametrize("timeout", [0, 0.0, -1.0, math.inf, math.nan, True, "30", None])
def test_fixture_rejects_invalid_timeouts(responses: tuple[Path, bytes], timeout: Any) -> None:
    path, _ = responses
    with pytest.raises(SchemaError, match="timeout_s"):
        FixtureModel(path).decide(make_request(), timeout_s=timeout)


def test_fixture_close_is_idempotent(responses: tuple[Path, bytes]) -> None:
    path, _ = responses
    model = FixtureModel(path)
    model.close()
    model.close()
    assert model.identity().provider == "fixture"


def test_fixture_unicode_state_and_body_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "r.jsonl"
    body = json.dumps(
        {
            "type": "choice",
            "choice": "café",
            "probabilities": {"café": 1.0, "☃": 0.0},
        },
        ensure_ascii=False,
    )
    write_rows(path, [{**ROW_OK, "body_json": body}])
    question = ChoiceQuestion("q", "pick", (Option("café", "d"), Option("☃", "d")))
    model = FixtureModel(path)
    capture = model.decide(DecisionRequest("v-001", "état 😀", question), timeout_s=30.0)
    answer = normalize(capture, question, model.identity())
    assert isinstance(answer, ChoiceAnswer)
    assert answer.choice == "café"


def test_fixture_satisfies_protocol(responses: tuple[Path, bytes]) -> None:
    path, _ = responses
    model: DecisionModel = FixtureModel(path)
    assert model.identity().provider == "fixture"
    model.close()


# --------------------------------------------------------------------------- #
# Laya constants and question payload
# --------------------------------------------------------------------------- #


def test_laya_pins_are_the_documented_values() -> None:
    assert MODEL_ID == "convaiinnovations/laya-typed-decisions"
    assert REVISION == "e929ae5cf69bc34259cd2f95c9e91145b818b1f0"
    assert dict(ARTIFACT_HASHES) == {
        "model.safetensors": "4fa56de72383a9d3efa9cfa78955733c81b9fc8067a587ca4beb82c78107a24e",
        "encoder/config.json": "5268d24ad3b77c8151de5dcb0762ba4391619aad9ab0bda33e36fb083cfeae6d",
        "rl_agent_config.json": "ebf0cd524d92342a6be5e48e9fca3d7c2babfb5a56ccd79d2171ef5d8c7f7be8",
        "tokenizer/tokenizer.json": (
            "6c8aaa9a542084f2457eab775d4eeb51f92a70c0fd9de28d5edb0ddec3c08d30"
        ),
        "tokenizer/tokenizer_config.json": (
            "08d4cf3ac4dca381759441b85b91a6d40e688471dcd33d15d6649eb0a9a854d1"
        ),
    }
    assert tuple(sorted(ARTIFACT_HASHES)) == ARTIFACT_HASHES
    assert (MAX_LEN, HEAD_MAX_LEN, OPTION_TOKEN_LIMIT, OPTION_BUDGET) == (1024, 256, 48, 240)
    assert STARTUP_TIMEOUT_S == 120.0
    assert THREADS == 4
    assert ADAPTER_VERSION == "1"


def test_question_payload_is_native_choice_shape() -> None:
    assert _question_payload(make_question()) == {
        "type": "choice",
        "instructions": "Select the department responsible for this ticket.",
        "criteria": {
            "billing": "Payments and refunds",
            "technical": "Technical support",
            "sales": "Purchasing questions",
        },
    }


# --------------------------------------------------------------------------- #
# Worker-side preflight and inference seam (in-process, no native stack)
# --------------------------------------------------------------------------- #


def fake_tokens(text: str) -> int:
    """One token per ASCII word; every non-ASCII character costs three tokens."""
    count = 0
    for word in text.split():
        if word.isascii():
            count += 1
        else:
            count += sum(1 if ch.isascii() else 3 for ch in word)
    return count


class FakePacking:
    """Mirror of the upstream head/state packing arithmetic over the fake tokenizer."""

    mask_token = "[MASK]"  # noqa: S105 - a tokenizer marker, not a credential

    def __init__(self, *, reject_question: bool = False) -> None:
        self.reject_question = reject_question
        self.built = 0

    def check_question(self, question_id: str, question: Mapping[str, object]) -> None:
        del question_id
        if self.reject_question or question.get("type") != "choice":
            msg = "question rejected: SECRET-DETAIL"
            raise ValueError(msg)

    def to_internal(self, question: Mapping[str, object]) -> dict[str, object]:
        return {"t": "choice", "ins": question["instructions"], "crit": question["criteria"]}

    def render_options(self, internal: Mapping[str, object]) -> list[str]:
        criteria = internal["crit"]
        assert isinstance(criteria, dict)
        return [f"{label}: {description}" for label, description in criteria.items()]

    def count_tokens(self, text: str) -> int:
        return fake_tokens(text)

    def build_sequence(
        self, state: str, internal: Mapping[str, object]
    ) -> tuple[int, dict[str, object], dict[str, object]]:
        self.built += 1
        options = self.render_options(internal)
        clipped = [min(fake_tokens(" " + o.replace(self.mask_token, " ")), 48) + 1 for o in options]
        budget = HEAD_MAX_LEN - sum(clipped)
        per_option: int | None = None
        if budget < 16:
            per_option = max(4, (HEAD_MAX_LEN - 16) // max(1, len(clipped)))
            clipped = [min(c, per_option) for c in clipped]
            budget = HEAD_MAX_LEN - sum(clipped)
        instruction = fake_tokens(f"choice question: {internal['ins']}")
        head = 1 + min(instruction, max(8, budget)) + 1 + sum(clipped) + 1
        room = max(0, MAX_LEN - head - 1)
        state_tokens = fake_tokens(state)
        used = min(state_tokens, room)
        distinct = len({(o[:per_option] if per_option else o) for o in options})
        return (
            len(options),
            {
                "options": len(options),
                "options_distinct": distinct,
                "tokens_per_option": per_option,
            },
            {
                "state_tokens": state_tokens,
                "state_tokens_used": used,
                "state_tokens_dropped": state_tokens - used,
                "truncated": used < state_tokens,
            },
        )


class SpyPredict:
    def __init__(self, result: object = None, *, raise_error: BaseException | None = None) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.result = result
        self.raise_error = raise_error

    def __call__(self, state: str, questions: dict[str, object]) -> object:
        self.calls.append((state, questions))
        if self.raise_error is not None:
            raise self.raise_error
        return self.result


def native_body(question_id: str = "department") -> dict[str, object]:
    return {
        "model": "laya-rl-agent",
        "answers": {
            question_id: {
                "type": "choice",
                "choice": "billing",
                "probabilities": {"billing": 0.8085, "technical": 0.0877, "sales": 0.1039},
                "confidence": 0.4352,
                "answer_confidence": 0.8085,
                "action": {"act_probability": 1.0},
            }
        },
        "usage": {
            "input_tokens": 59,
            "output_tokens": 0,
            "state_tokens": 15,
            "state_tokens_dropped": 0,
            "truncated": False,
            "truncated_questions": [],
        },
    }


def question_of(options: list[tuple[str, str]], instructions: str = "pick one") -> ChoiceQuestion:
    return ChoiceQuestion("q", instructions, tuple(Option(label, desc) for label, desc in options))


def run_infer(
    packing: FakePacking,
    predict: Callable[[str, dict[str, object]], object],
    state: str,
    question: ChoiceQuestion,
) -> dict[str, object]:
    return _infer(packing, predict, state, question.question_id, _question_payload(question))


def test_infer_calls_predict_with_pinned_budget_and_preserves_body() -> None:
    packing = FakePacking()
    body = native_body("q")
    spy = SpyPredict(body)
    question = question_of([("billing", "money"), ("technical", "bugs"), ("sales", "buy")])
    reply = run_infer(packing, spy, "I was charged twice", question)
    assert reply == {"body": body, "warnings": []}
    assert spy.calls == [("I was charged twice", {"q": _question_payload(question)})]
    assert packing.built == 1


def test_infer_captures_predict_warnings() -> None:
    def predict(state: str, questions: dict[str, object]) -> object:
        del state, questions
        warnings.warn("choice:11+ clamped", RuntimeWarning, stacklevel=1)
        return native_body("q")

    reply = run_infer(FakePacking(), predict, "s", question_of([("billing", "m"), ("sales", "b")]))
    assert reply["warnings"] == ["laya.predict_warning:RuntimeWarning:choice:11+ clamped"]


def test_infer_bounds_warning_text() -> None:
    def predict(state: str, questions: dict[str, object]) -> object:
        del state, questions
        warnings.warn("x" * 5000, RuntimeWarning, stacklevel=1)
        return native_body("q")

    reply = run_infer(FakePacking(), predict, "s", question_of([("billing", "m"), ("sales", "b")]))
    recorded = reply["warnings"]
    assert isinstance(recorded, list)
    assert len(recorded) == 1
    assert len(recorded[0]) <= 256


def test_infer_maps_exceptions_to_provider_error_without_message() -> None:
    spy = SpyPredict(raise_error=RuntimeError("token=SECRET-VALUE"))
    reply = run_infer(FakePacking(), spy, "s", question_of([("billing", "m"), ("sales", "b")]))
    assert reply == {"failure": "provider_error", "warnings": ["laya.exception:RuntimeError"]}


def test_infer_rejected_question_is_provider_error_without_detail() -> None:
    spy = SpyPredict(native_body("q"))
    reply = run_infer(
        FakePacking(reject_question=True), spy, "s", question_of([("billing", "m"), ("sales", "b")])
    )
    assert reply == {"failure": "provider_error", "warnings": ["laya.preflight.question_rejected"]}
    assert spy.calls == []


@pytest.mark.parametrize("result", [None, [], "billing", {"answers": {}, "usage": object()}])
def test_infer_unserializable_or_non_object_result_is_malformed(result: object) -> None:
    spy = SpyPredict(result)
    reply = run_infer(FakePacking(), spy, "s", question_of([("billing", "m"), ("sales", "b")]))
    assert reply == {"failure": "malformed_response", "warnings": ["laya.body_unserializable"]}


def test_infer_rejects_option_over_48_tokens_before_predict() -> None:
    spy = SpyPredict(native_body("q"))
    long_option = " ".join(["w"] * 48)  # rendered as "label: w w ... w" -> 50 tokens
    question = question_of([("billing", long_option), ("sales", "b")])
    reply = run_infer(FakePacking(), spy, "s", question)
    assert reply == {"failure": "input_too_long", "warnings": ["laya.preflight.option_tokens"]}
    assert spy.calls == []


def test_infer_accepts_option_at_exactly_48_tokens() -> None:
    spy = SpyPredict(native_body("q"))
    option = " ".join(["w"] * 46)  # "label:" + 46 words = 47 tokens, plus leading space -> 47
    question = question_of([("billing", option), ("sales", "b")])
    assert fake_tokens(" billing: " + option) == 47
    reply = run_infer(FakePacking(), spy, "s", question)
    assert "body" in reply
    exact = " ".join(["w"] * 47)
    assert fake_tokens(" billing: " + exact) == 48
    reply = run_infer(FakePacking(), spy, "s", question_of([("billing", exact), ("sales", "b")]))
    assert "body" in reply
    assert len(spy.calls) == 2


def test_infer_rejects_option_budget_over_240_before_predict() -> None:
    spy = SpyPredict(native_body("q"))
    # six options of 40 tokens each: 6 * (40 + 1 mask) = 246 > 240
    option = " ".join(["w"] * 39)  # "label:" + 39 words = 40 tokens
    question = question_of([(f"l{i}", option) for i in range(6)])
    reply = run_infer(FakePacking(), spy, "s", question)
    assert reply == {"failure": "input_too_long", "warnings": ["laya.preflight.option_budget"]}
    assert spy.calls == []


def test_infer_accepts_option_budget_at_exactly_240() -> None:
    spy = SpyPredict(native_body("q"))
    # six options of 39 tokens each: 6 * (39 + 1) = 240
    option = " ".join(["w"] * 38)  # "label:" + 38 words = 39 tokens
    question = question_of([(f"l{i}", option) for i in range(6)], instructions="short")
    reply = run_infer(FakePacking(), spy, "s", question)
    assert "body" in reply


def test_infer_rejects_instruction_clipping_before_predict() -> None:
    spy = SpyPredict(native_body("q"))
    # options take 2 * (2 + 1) = 6 tokens; instruction budget is 256 - 6 = 250
    # "choice question: " adds 2 tokens, so 249 instruction words -> 251 > 250
    instructions = " ".join(["i"] * 249)
    question = question_of([("a", "x"), ("b", "y")], instructions=instructions)
    reply = run_infer(FakePacking(), spy, "s", question)
    assert reply == {"failure": "input_too_long", "warnings": ["laya.preflight.instruction_tokens"]}
    assert spy.calls == []


def test_infer_accepts_instruction_at_exact_budget() -> None:
    spy = SpyPredict(native_body("q"))
    instructions = " ".join(["i"] * 248)  # 2 + 248 = 250 == budget
    question = question_of([("a", "x"), ("b", "y")], instructions=instructions)
    reply = run_infer(FakePacking(), spy, "s", question)
    assert "body" in reply


def test_infer_rejects_state_overflow_before_predict() -> None:
    spy = SpyPredict(native_body("q"))
    question = question_of([("a", "x"), ("b", "y")], instructions="short")
    packing = FakePacking()
    head = 1 + 3 + 1 + (3 + 3) + 1  # cls, instruction(3), sep, options, sep
    room = MAX_LEN - head - 1
    fits = " ".join(["s"] * room)
    assert "body" in run_infer(packing, spy, fits, question)
    overflow = " ".join(["s"] * (room + 1))
    reply = run_infer(packing, spy, overflow, question)
    assert reply == {"failure": "input_too_long", "warnings": ["laya.preflight.state_tokens"]}
    assert len(spy.calls) == 1


def test_infer_rejects_token_heavy_unicode_option() -> None:
    spy = SpyPredict(native_body("q"))
    emoji = "😀" * 17  # 17 characters, 51 fake tokens
    question = question_of([("a", emoji), ("b", "y")])
    reply = run_infer(FakePacking(), spy, "s", question)
    assert reply == {"failure": "input_too_long", "warnings": ["laya.preflight.option_tokens"]}
    assert spy.calls == []


def test_infer_rejects_token_heavy_unicode_state() -> None:
    spy = SpyPredict(native_body("q"))
    question = question_of([("a", "x"), ("b", "y")], instructions="short")
    state = "é" * 400  # 1200 fake tokens in 400 characters
    reply = run_infer(FakePacking(), spy, state, question)
    assert reply == {"failure": "input_too_long", "warnings": ["laya.preflight.state_tokens"]}
    assert spy.calls == []


def test_infer_rejects_collapsed_options_before_predict() -> None:
    spy = SpyPredict(native_body("q"))
    # fifteen options of 16 tokens each: 15 * 17 = 255 > 240 -> rejected by the budget first,
    # so make them share text with fewer tokens: identical rendered options collapse.
    question = question_of([("a", "same text"), ("b", "same text")])

    class Collapsing(FakePacking):
        def render_options(self, internal: Mapping[str, object]) -> list[str]:
            del internal
            return ["same", "same"]

    reply = run_infer(Collapsing(), spy, "s", question)
    assert reply == {"failure": "input_too_long", "warnings": ["laya.preflight.collapsed_options"]}
    assert spy.calls == []


def test_infer_rejects_marker_shortfall_before_predict() -> None:
    spy = SpyPredict(native_body("q"))

    class DroppingMarkers(FakePacking):
        def build_sequence(
            self, state: str, internal: Mapping[str, object]
        ) -> tuple[int, dict[str, object], dict[str, object]]:
            markers, stats, state_stats = super().build_sequence(state, internal)
            return markers - 1, stats, state_stats

    reply = run_infer(DroppingMarkers(), spy, "s", question_of([("a", "x"), ("b", "y")]))
    assert reply == {"failure": "input_too_long", "warnings": ["laya.preflight.markers"]}
    assert spy.calls == []


def test_infer_mask_token_in_text_is_neutralized_before_counting() -> None:
    packing = FakePacking()
    seen: list[str] = []
    original = packing.count_tokens

    def counting(text: str) -> int:
        seen.append(text)
        return original(text)

    packing.count_tokens = counting  # type: ignore[method-assign]
    question = question_of([("a", "x [MASK] y"), ("b", "y")], instructions="use [MASK] here")
    run_infer(packing, SpyPredict(native_body("q")), "s", question)
    assert all("[MASK]" not in text for text in seen)


# --------------------------------------------------------------------------- #
# Laya subprocess lifecycle with a fake worker
# --------------------------------------------------------------------------- #


@pytest.fixture
def fake_worker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return write_fake_worker(tmp_path, monkeypatch)


def test_fake_worker_round_trip(fake_worker: Path) -> None:
    model = spawn(fake_worker)
    try:
        model_as_protocol: DecisionModel = model
        assert model_as_protocol.identity() == pinned_identity()
        request = make_request()
        capture = model.decide(request, timeout_s=5.0)
        assert capture.request_sha256 == request_sha256(request)
        assert capture.identity == pinned_identity()
        assert capture.failure_code is None
        assert capture.warnings == ("laya.load_warning:RuntimeWarning:clamped",)
        assert capture.fallback_used is False
        answer = normalize(capture, make_question(), pinned_identity())
        assert isinstance(answer, ChoiceAnswer)
        assert answer.choice == "billing"
        assert answer.selected_probability == 1.0
        assert child_alive(model)
    finally:
        model.close()
    assert not child_alive(model)


def test_fake_worker_predict_warnings_follow_load_warnings(fake_worker: Path) -> None:
    model = spawn(fake_worker, "warn")
    try:
        capture = model.decide(make_request(), timeout_s=5.0)
        assert capture.warnings == (
            "laya.load_warning:RuntimeWarning:clamped",
            "laya.predict_warning:x",
        )
    finally:
        model.close()


def test_fake_worker_reported_failure_keeps_worker_usable(fake_worker: Path) -> None:
    model = spawn(fake_worker, "fail-decide")
    try:
        first = model.decide(make_request(), timeout_s=5.0)
        assert first.failure_code == "provider_error"
        assert first.body_json is None
        assert first.warnings == (
            "laya.load_warning:RuntimeWarning:clamped",
            "laya.exception:RuntimeError",
        )
        second = model.decide(make_request(), timeout_s=5.0)
        assert second.failure_code == "provider_error"
        assert child_alive(model)
    finally:
        model.close()


def test_fake_worker_unknown_failure_code_is_unavailable(fake_worker: Path) -> None:
    model = spawn(fake_worker, "bad-failure")
    try:
        capture = model.decide(make_request(), timeout_s=5.0)
        assert capture.failure_code == "unavailable"
        assert not child_alive(model)
    finally:
        model.close()


def test_timeout_terminates_joins_and_invalidates(fake_worker: Path) -> None:
    model = spawn(fake_worker, "hang-on-decide")
    try:
        capture = model.decide(make_request(), timeout_s=0.3)
        assert capture.failure_code == "timeout"
        assert capture.body_json is None
        assert "laya.load_warning:RuntimeWarning:clamped" in capture.warnings
        child = model._child
        assert child is not None
        assert child.poll() is not None  # terminated and joined before returning
        pid = child.pid
        later = model.decide(make_request(), timeout_s=5.0)
        assert later.failure_code == "unavailable"
        assert "laya.unavailable:timeout" in later.warnings
        assert model._child is not None
        assert model._child.pid == pid  # no silent restart
        assert model.identity() == pinned_identity()
    finally:
        model.close()
    assert model.decide(make_request(), timeout_s=5.0).failure_code == "unavailable"


def test_late_reply_never_crosses_requests(fake_worker: Path) -> None:
    model = spawn(fake_worker, "slow-reply")
    try:
        first = model.decide(make_request(), timeout_s=0.1)
        assert first.failure_code == "timeout"
        second = model.decide(make_request(), timeout_s=5.0)
        assert second.failure_code == "unavailable"
        assert second.body_json is None
    finally:
        model.close()


def test_stale_sequence_reply_is_unavailable_and_invalidates(fake_worker: Path) -> None:
    model = spawn(fake_worker, "stale-seq")
    try:
        capture = model.decide(make_request(), timeout_s=5.0)
        assert capture.failure_code == "unavailable"
        assert "laya.unavailable:ipc" in capture.warnings
        assert not child_alive(model)
        assert model.decide(make_request(), timeout_s=5.0).failure_code == "unavailable"
    finally:
        model.close()


#: A stdlib worker whose reply frame splices the ``seq`` member as raw JSON text so the
#: parent sees exactly the token under test: the echoed integer, ``true``, ``<n>.0`` or no
#: member at all. Everything else matches the round-trip reply of the shared fake worker.
SEQ_WORKER = r"""
import json
import os
import sys

mode = sys.argv[1]
out = sys.stdout.buffer
inp = sys.stdin.buffer


def send_line(text):
    out.write(text.encode("utf-8") + b"\n")
    out.flush()


identity = json.loads(os.environ["ACTSEAL_FAKE_IDENTITY"])
send_line(json.dumps({"kind": "ready", "identity": identity, "warnings": []}))
while True:
    line = inp.readline()
    if not line:
        sys.exit(0)
    msg = json.loads(line)
    if msg["kind"] == "close":
        sys.exit(0)
    seq = msg["seq"]
    labels = list(msg["question"]["criteria"])
    probabilities = {label: 0.0 for label in labels}
    probabilities[labels[0]] = 1.0
    body = {
        "model": "laya-rl-agent",
        "answers": {msg["question_id"]: {"type": "choice", "choice": labels[0],
                                          "probabilities": probabilities}},
        "usage": {"input_tokens": len(msg["state"]), "output_tokens": 0,
                  "state_tokens": 1, "state_tokens_dropped": 0,
                  "truncated": False, "truncated_questions": []},
    }
    token = {"seq-int": str(seq), "seq-true": "true", "seq-float": str(seq) + ".0",
             "seq-missing": None}[mode]
    member = "" if token is None else '"seq": ' + token + ", "
    send_line('{"kind": "reply", ' + member + '"body": ' + json.dumps(body)
              + ', "warnings": []}')
"""


@pytest.fixture
def seq_worker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    write_fake_worker(tmp_path, monkeypatch)  # exports the pinned identity
    script = tmp_path / "seq_worker.py"
    script.write_text(SEQ_WORKER, encoding="utf-8")
    return script


def test_integer_sequence_reply_is_captured(seq_worker: Path) -> None:
    """Control: the echoed JSON integer is the pending request's sequence on every call."""
    model = spawn(seq_worker, "seq-int")
    try:
        for _ in range(2):
            capture = model.decide(make_request(), timeout_s=5.0)
            assert capture.failure_code is None
            assert capture.body_json is not None
            assert capture.warnings == ()
            answer = normalize(capture, make_question(), pinned_identity())
            assert isinstance(answer, ChoiceAnswer)
            assert answer.choice == "billing"
        assert child_alive(model)
    finally:
        model.close()
    assert not child_alive(model)


@pytest.mark.parametrize("mode", ["seq-true", "seq-float", "seq-missing"])
def test_non_integer_sequence_reply_is_unavailable_and_invalidates(
    seq_worker: Path, mode: str
) -> None:
    """``true`` and ``1.0`` compare equal to the first sequence ``1`` in Python but are not
    the JSON integer that was sent; like a missing sequence they are unusable IPC."""
    model = spawn(seq_worker, mode)
    try:
        capture = model.decide(make_request(), timeout_s=5.0)
        assert capture.failure_code == "unavailable"
        assert capture.body_json is None
        assert capture.warnings == ("laya.unavailable:ipc",)
        assert not child_alive(model)
        later = model.decide(make_request(), timeout_s=5.0)
        assert later.failure_code == "unavailable"
        assert later.warnings == ("laya.unavailable:ipc",)
        assert not child_alive(model)
    finally:
        model.close()


def test_worker_death_is_unavailable_and_stays_unavailable(fake_worker: Path) -> None:
    model = spawn(fake_worker, "exit-on-decide")
    try:
        capture = model.decide(make_request(), timeout_s=5.0)
        assert capture.failure_code == "unavailable"
        assert "laya.unavailable:worker_exit" in capture.warnings
        assert not child_alive(model)
        again = model.decide(make_request(), timeout_s=5.0)
        assert again.failure_code == "unavailable"
    finally:
        model.close()


@pytest.mark.parametrize(
    "mode",
    ["garbage-on-decide", "huge-on-decide", "deep-on-decide", "duplicate-keys-on-decide"],
)
def test_unusable_ipc_is_unavailable(fake_worker: Path, mode: str) -> None:
    model = spawn(fake_worker, mode)
    try:
        capture = model.decide(make_request(), timeout_s=5.0)
        assert capture.failure_code == "unavailable"
        assert "laya.unavailable:ipc" in capture.warnings
        assert not child_alive(model)
        later = model.decide(make_request(), timeout_s=5.0)
        assert later.failure_code == "unavailable"
        assert "laya.unavailable:ipc" in later.warnings
        assert not child_alive(model)
    finally:
        model.close()


def test_nonreading_worker_times_out_on_pipe_filling_request(fake_worker: Path) -> None:
    model = spawn(fake_worker, "stop-reading", grace=0.2)
    try:
        request = DecisionRequest("v-big", "x" * 1_000_000, make_question())
        started = time.monotonic()
        capture = model.decide(request, timeout_s=0.3)
        elapsed = time.monotonic() - started
        assert capture.failure_code == "timeout"
        assert capture.request_sha256 == request_sha256(request)
        assert elapsed < 2.0, elapsed  # deadline covers the write; cleanup is bounded
        child = model._child
        assert child is not None
        assert child.poll() is not None  # joined before returning
        later = model.decide(make_request(), timeout_s=5.0)
        assert later.failure_code == "unavailable"
        assert "laya.unavailable:timeout" in later.warnings
    finally:
        model.close()


def test_small_request_to_nonreading_worker_also_times_out(fake_worker: Path) -> None:
    model = spawn(fake_worker, "stop-reading", grace=0.2)
    try:
        capture = model.decide(make_request(), timeout_s=0.3)
        assert capture.failure_code == "timeout"
        assert not child_alive(model)
    finally:
        model.close()


def test_close_is_idempotent_and_leaves_no_child(fake_worker: Path) -> None:
    model = spawn(fake_worker)
    assert child_alive(model)
    model.close()
    assert not child_alive(model)
    model.close()
    capture = model.decide(make_request(), timeout_s=5.0)
    assert capture.failure_code == "unavailable"
    assert "laya.unavailable:closed" in capture.warnings


def test_close_kills_a_worker_that_ignores_close(fake_worker: Path) -> None:
    model = spawn(fake_worker, "ignore-close", grace=0.2)
    model.close()
    assert not child_alive(model)
    model.close()


@pytest.mark.parametrize(
    "mode",
    ["hang-on-start", "exit-on-start", "setup-error", "garbage-on-start", "deep-on-start"],
)
def test_startup_failures_raise_and_leave_no_child(fake_worker: Path, mode: str) -> None:
    with pytest.raises(ProviderSetupError) as info:
        spawn(fake_worker, mode, startup=0.5)
    assert "SECRET" not in str(info.value)
    assert _child_command_lines(fake_worker) == []


def _child_command_lines(script: Path) -> list[str]:
    result = subprocess.run(
        ["/bin/ps", "-axo", "command"], capture_output=True, text=True, check=False
    )
    return [line for line in result.stdout.splitlines() if str(script) in line]


def test_startup_error_message_names_the_bounded_code(fake_worker: Path) -> None:
    with pytest.raises(ProviderSetupError, match=r"laya\.setup:ValueError"):
        spawn(fake_worker, "setup-error")


@pytest.mark.parametrize("mode", ["wrong-identity", "bad-identity"])
def test_substituted_identity_is_a_setup_error(fake_worker: Path, mode: str) -> None:
    with pytest.raises(ProviderSetupError):
        spawn(fake_worker, mode)
    assert _child_command_lines(fake_worker) == []


def test_offline_flag_sets_library_offline_variables(
    fake_worker: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
    monkeypatch.delenv("TRANSFORMERS_OFFLINE", raising=False)
    offline = LayaModel._spawn(
        (sys.executable, str(fake_worker), "echo-env"),
        offline=True,
        startup_timeout_s=10.0,
        close_grace_s=0.3,
    )
    try:
        assert offline.decide(make_request(), timeout_s=5.0).warnings == ("env:1:1",)
    finally:
        offline.close()
    online = LayaModel._spawn(
        (sys.executable, str(fake_worker), "echo-env"),
        offline=False,
        startup_timeout_s=10.0,
        close_grace_s=0.3,
    )
    try:
        assert online.decide(make_request(), timeout_s=5.0).warnings == ("env:unset:unset",)
    finally:
        online.close()


@pytest.mark.parametrize("timeout", [0, 0.0, -1.0, math.inf, math.nan, True, "30", None])
def test_laya_rejects_invalid_timeouts(fake_worker: Path, timeout: Any) -> None:
    model = spawn(fake_worker)
    try:
        with pytest.raises(SchemaError, match="timeout_s"):
            model.decide(make_request(), timeout_s=timeout)
        assert child_alive(model)
    finally:
        model.close()


def test_laya_request_hash_binds_state_and_question(fake_worker: Path) -> None:
    model = spawn(fake_worker)
    try:
        first = model.decide(make_request(), timeout_s=5.0)
        other = DecisionRequest("v-001", "different state", make_question())
        second = model.decide(other, timeout_s=5.0)
        assert first.request_sha256 != second.request_sha256
        assert second.request_sha256 == request_sha256(other)
    finally:
        model.close()


def test_native_worker_command_uses_current_interpreter() -> None:
    command = _native_worker_command()
    assert command[0] == sys.executable
    assert "actseal.adapters.laya" in " ".join(command)


def test_adapter_modules_do_not_import_native_stack() -> None:
    script = (
        "import sys\n"
        "import actseal.adapters.base, actseal.adapters.fixture, actseal.adapters.laya\n"
        "loaded = sorted(name for name in sys.modules if name.split('.')[0] in "
        "('laya', 'torch', 'transformers', 'huggingface_hub', 'safetensors', 'numpy'))\n"
        "print(loaded)\n"
    )
    result = subprocess.run(  # noqa: S603 - fixed interpreter and literal script, no user input
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
        env={**os.environ, "PYTHONWARNINGS": "error"},
    )
    assert result.stdout.strip() == "[]"


def test_provider_failure_from_capture_is_normalizable(fake_worker: Path) -> None:
    model = spawn(fake_worker, "hang-on-decide")
    try:
        capture = model.decide(make_request(), timeout_s=0.2)
    finally:
        model.close()
    outcome = normalize(capture, make_question(), pinned_identity())
    assert isinstance(outcome, ProviderFailure)
    assert outcome.code == "timeout"
