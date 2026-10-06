"""Experimental Jev adapter: exact request shape, frozen failure mapping, bounded capture.

No test here opens a network connection: the shared ``conftest`` socket block
is live for every test, the adapter's connection seam is a stdlib-only fake
that records the exact ``request`` call and scripts the response, and the only
``JEV_API_KEY`` values are mocked strings set through ``monkeypatch``. The
"recorded" Jev bodies below are authored mocks of the documented response
shape, not live captures; nothing here is a model-quality claim.
"""

from __future__ import annotations

import http.client
import json
import os
import ssl
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import pytest
from test_evidence import make_bundle, make_lock, record_for
from test_schema_validation import valid, validate_bundle_directory

import actseal.experimental.providers.jev as jev_module
import actseal.normalization as normalization_module
from actseal.errors import ProviderSetupError, SchemaError
from actseal.evidence import write_bundle
from actseal.experimental.providers.jev import (
    ADAPTER_VERSION,
    API_KEY_ENV,
    ENDPOINT_HOST,
    ENDPOINT_PATH,
    EXECUTION_PROFILE,
    MAX_RESPONSE_BYTES,
    MODEL,
    REVISION,
    JevModel,
    request_body,
)
from actseal.normalization import NORMALIZER_VERSION, normalize, request_sha256
from actseal.policy import evaluate
from actseal.records import (
    PROVIDERS,
    Case,
    ChoiceAnswer,
    ChoiceQuestion,
    DecisionRequest,
    ModelIdentity,
    Option,
    ProviderFailure,
)
from actseal.serialization import canonical_json, from_data, strict_json_loads, to_data
from conftest import make_question, make_request
from provider_support import INVALID_TIMEOUTS, independent_request_digest

MOCK_KEY = "mock-jev-key-SECRETMARKER-not-a-real-credential"
ROOT = Path(__file__).resolve().parents[2]


# --------------------------------------------------------------------------- #
# Stdlib fake for the connection seam
# --------------------------------------------------------------------------- #


@dataclass
class Script:
    """What one fake connection does: a status and body, or an exception at a stage."""

    status: int = 200
    body: bytes = b""
    raise_on_connect: BaseException | None = None
    raise_on_request: BaseException | None = None
    raise_on_response: BaseException | None = None
    raise_on_read: BaseException | None = None


@dataclass
class Sent:
    method: str
    url: str
    body: bytes
    headers: dict[str, str]
    timeout: float
    read_amounts: list[int] = field(default_factory=list)
    closed: int = 0


class FakeResponse:
    def __init__(self, sent: Sent, script: Script) -> None:
        self._sent = sent
        self._script = script
        self.status = script.status
        self._buffer = script.body

    def read(self, amt: int) -> bytes:
        self._sent.read_amounts.append(amt)
        if self._script.raise_on_read is not None:
            raise self._script.raise_on_read
        chunk, self._buffer = self._buffer[:amt], self._buffer[amt:]
        return chunk


class FakeConnection:
    def __init__(self, script: Script, timeout: float, log: list[Sent]) -> None:
        self._script = script
        self._timeout = timeout
        self._log = log
        self._sent: Sent | None = None

    def request(self, method: str, url: str, body: bytes, headers: Mapping[str, str]) -> None:
        self._sent = Sent(method, url, bytes(body), dict(headers), self._timeout)
        self._log.append(self._sent)
        if self._script.raise_on_request is not None:
            raise self._script.raise_on_request

    def getresponse(self) -> FakeResponse:
        assert self._sent is not None
        if self._script.raise_on_response is not None:
            raise self._script.raise_on_response
        return FakeResponse(self._sent, self._script)

    def close(self) -> None:
        if self._sent is not None:
            self._sent.closed += 1
        else:
            self._log.append(Sent("", "", b"", {}, self._timeout, closed=1))


class FakeConnect:
    """A connection factory that hands out one scripted connection per call, in order."""

    def __init__(self, *scripts: Script) -> None:
        self._scripts = list(scripts)
        self.log: list[Sent] = []
        self.connections = 0

    def __call__(self, timeout: float) -> FakeConnection:
        self.connections += 1
        script = self._scripts.pop(0) if len(self._scripts) > 1 else self._scripts[0]
        if script.raise_on_connect is not None:
            raise script.raise_on_connect
        return FakeConnection(script, timeout, self.log)


def failing(stage: str, error: BaseException) -> Script:
    """A script that raises ``error`` at ``stage`` (connect, request, response or read)."""
    if stage == "connect":
        return Script(raise_on_connect=error)
    if stage == "request":
        return Script(raise_on_request=error)
    if stage == "response":
        return Script(raise_on_response=error)
    assert stage == "read"
    return Script(raise_on_read=error)


def model_over(*scripts: Script, key: str = MOCK_KEY) -> tuple[JevModel, FakeConnect]:
    connect = FakeConnect(*scripts)
    exchange = jev_module._HttpsExchange(key, connect)
    return JevModel._with_exchange(exchange), connect


# --------------------------------------------------------------------------- #
# Mocked response bodies
# --------------------------------------------------------------------------- #


def jev_answer(
    question: ChoiceQuestion, *, choice: str | None = None, **changes: Any
) -> dict[str, Any]:
    labels = question.labels
    selected = choice or labels[0]
    rest = 0.05 / (len(labels) - 1)
    probabilities = {label: 0.95 if label == selected else rest for label in labels}
    answer: dict[str, Any] = {
        "type": "choice",
        "choice": selected,
        "probabilities": probabilities,
        "confidence": 0.925,
    }
    answer.update(changes)
    return answer


def jev_body(
    question: ChoiceQuestion,
    *,
    model: object = MODEL,
    usage: object | None = None,
    **changes: Any,
) -> str:
    body = {
        "model": model,
        "answers": {question.question_id: jev_answer(question, **changes)},
        "usage": {"input_tokens": 41, "output_tokens": 0} if usage is None else usage,
    }
    return json.dumps(body)


RAW_NONCANONICAL = (
    '{ "usage" : {"input_tokens": 41, "output_tokens": 0},\n'
    '  "answers": { "department": { "type": "choice", "confidence": 0.925,\n'
    '    "choice": "billing", "probabilities": {"technical": 0.025, "billing": 0.95, '
    '"sales": 0.025} } },\n'
    '  "model": "jev-1.13.0" }'
)


def ok(body: str | bytes) -> Script:
    return Script(200, body if isinstance(body, bytes) else body.encode("utf-8"))


# --------------------------------------------------------------------------- #
# Profile constants and identity
# --------------------------------------------------------------------------- #


def test_profile_constants_are_frozen_and_shared_with_the_pure_normalizer() -> None:
    assert MODEL == REVISION == "jev-1.13.0" == normalization_module._JEV_MODEL
    assert ENDPOINT_HOST == "api.typesafe.ai"
    assert ENDPOINT_PATH == "/v1/systemone"
    assert API_KEY_ENV == "JEV_API_KEY"
    assert ADAPTER_VERSION == "1"
    assert MAX_RESPONSE_BYTES == 1024 * 1024
    assert EXECUTION_PROFILE == "jev-cloud-single-attempt-v1"
    assert normalization_module._JEV_MASS_TOLERANCE == 1e-12
    assert "jev" in PROVIDERS
    assert jev_module._STATUS_FAILURES == {
        401: "provider_error",
        422: "provider_error",
        429: "rate_limit",
        529: "unavailable",
    }


def test_identity_is_fixed_cloud_target_with_empty_artifact_hashes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(API_KEY_ENV, raising=False)
    model = JevModel(offline=True)
    identity = model.identity()
    assert identity == ModelIdentity(
        "jev",
        "jev-1.13.0",
        "jev-1.13.0",
        (),
        ADAPTER_VERSION,
        NORMALIZER_VERSION,
        (
            ("endpoint", "https://api.typesafe.ai/v1/systemone"),
            ("execution_profile", EXECUTION_PROFILE),
            ("python", sys.version.split()[0]),
            ("transport", "stdlib-http.client-tls"),
            ("weights_attested", "false"),
        ),
    )
    assert identity.artifact_hashes == ()
    assert model.identity() is identity
    assert from_data(ModelIdentity, to_data(identity)) == identity
    model.close()
    assert model.identity() == identity


def test_identity_never_mutates_from_a_response_claiming_another_model() -> None:
    question = make_question()
    model, _ = model_over(ok(jev_body(question, model="jev-1.12.0")))
    before = model.identity()
    capture = model.decide(make_request(), timeout_s=5.0)
    assert capture.identity == before
    assert model.identity() == before
    outcome = normalize(capture, question, before)
    assert isinstance(outcome, ProviderFailure)
    assert outcome.code == "identity_mismatch"
    assert outcome.warnings == ("normalize.answering_model",)


# --------------------------------------------------------------------------- #
# Setup: key handling and offline mode
# --------------------------------------------------------------------------- #


def test_offline_setup_reads_no_environment_and_makes_no_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def tripwire() -> str:
        raise AssertionError("JEV_API_KEY was read in offline mode")

    monkeypatch.setattr(jev_module, "_api_key_from_environment", tripwire)
    model = JevModel(offline=True)
    capture = model.decide(make_request(), timeout_s=5.0)
    assert capture.failure_code == "unavailable"
    assert capture.warnings == ("jev.unavailable:offline",)
    assert capture.body_json is None
    assert capture.request_sha256 == independent_request_digest(make_request())
    assert model._attempts == 0
    assert normalize(capture, make_question(), model.identity()) == ProviderFailure(
        "unavailable", ("jev.unavailable:offline",), False
    )
    model.close()
    assert model.decide(make_request(), timeout_s=5.0).failure_code == "unavailable"


@pytest.mark.parametrize(
    "value",
    [None, "", "has space", "tab\there", "line\nbreak", "clé", "x" * 4097, "\x1b[0m"],
    ids=["unset", "empty", "space", "tab", "newline", "non-ascii", "too-long", "control"],
)
def test_missing_or_malformed_key_is_a_setup_error_without_echo(
    monkeypatch: pytest.MonkeyPatch, value: str | None
) -> None:
    if value is None:
        monkeypatch.delenv(API_KEY_ENV, raising=False)
    else:
        monkeypatch.setenv(API_KEY_ENV, value)
    with pytest.raises(ProviderSetupError) as excinfo:
        JevModel()
    message = str(excinfo.value)
    assert message.startswith("JEV_API_KEY:")
    if value:
        assert value not in message


def test_default_transport_targets_the_fixed_host_and_is_blocked_offline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The real seam: ``HTTPSConnection`` to the fixed host; the conftest socket block fires."""
    connection = jev_module._default_connect(7.5)
    assert isinstance(connection, http.client.HTTPSConnection)
    assert connection.host == ENDPOINT_HOST
    assert connection.port == 443
    assert connection.timeout == 7.5
    connection.close()
    monkeypatch.setenv(API_KEY_ENV, MOCK_KEY)
    model = JevModel()
    capture = model.decide(make_request(), timeout_s=5.0)
    # The blocked ``socket.create_connection`` raises a RuntimeError subclass: an
    # unexpected transport exception is bounded provider_error data, never an exception.
    assert capture.failure_code == "provider_error"
    assert capture.warnings == ("jev.exception:_NetworkBlockedError",)
    assert capture.body_json is None
    assert model._attempts == 1
    assert MOCK_KEY not in repr(model) + repr(model._exchange) + json.dumps(to_data(capture))
    model.close()


def test_default_tls_context_verifies_certificates() -> None:
    context = ssl.create_default_context()
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


# --------------------------------------------------------------------------- #
# Exact request shape and gold-label isolation
# --------------------------------------------------------------------------- #


def test_request_body_is_state_model_questions_in_locked_order() -> None:
    question = ChoiceQuestion(
        "route",
        "Pick the queue.",
        (
            Option("technical", "Bugs"),
            Option("billing", "Money"),
            Option("sales", "Quotes"),
        ),
    )
    request = DecisionRequest("v-009", 'état 😀 "quoted" \\ back', question)
    body = request_body(request)
    expected = {
        "state": 'état 😀 "quoted" \\ back',
        "model": "jev-1.13.0",
        "questions": {
            "route": {
                "type": "choice",
                "instructions": "Pick the queue.",
                "criteria": {"technical": "Bugs", "billing": "Money", "sales": "Quotes"},
            }
        },
    }
    assert body == json.dumps(expected, ensure_ascii=False, separators=(",", ":")).encode()
    decoded = json.loads(body)
    assert list(decoded) == ["state", "model", "questions"]
    assert list(decoded["questions"]["route"]) == ["type", "instructions", "criteria"]
    assert list(decoded["questions"]["route"]["criteria"]) == ["technical", "billing", "sales"]
    assert body != canonical_json(decoded)  # canonical sorting would reorder the criteria
    assert b"v-009" not in body
    assert b"case_id" not in body
    assert b"expected_label" not in body
    with pytest.raises(SchemaError, match="request"):
        request_body(to_data(request))  # type: ignore[arg-type]


def test_decide_sends_exactly_one_post_with_the_fixed_headers_and_closes() -> None:
    question = make_question()
    model, connect = model_over(ok(jev_body(question)))
    request = make_request()
    capture = model.decide(request, timeout_s=12.5)
    assert connect.connections == 1
    assert len(connect.log) == 1
    sent = connect.log[0]
    assert sent.method == "POST"
    assert sent.url == "/v1/systemone"
    assert sent.body == request_body(request)
    assert sent.headers == {
        "Authorization": f"Bearer {MOCK_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    assert sent.timeout == 12.5
    assert sent.read_amounts == [MAX_RESPONSE_BYTES + 1]
    assert sent.closed == 1
    assert capture.body_json == jev_body(question)
    assert capture.failure_code is None
    assert capture.warnings == ()
    assert model._attempts == 1


def test_case_id_changes_the_capture_hash_but_not_the_http_body() -> None:
    question = make_question()
    first = DecisionRequest("v-001", "same state", question)
    second = DecisionRequest("v-002", "same state", question)
    assert request_body(first) == request_body(second)
    assert request_sha256(first) != request_sha256(second)
    model, connect = model_over(ok(jev_body(question)))
    captures = [model.decide(r, timeout_s=5.0) for r in (first, second)]
    assert connect.log[0].body == connect.log[1].body
    assert captures[0].request_sha256 != captures[1].request_sha256
    assert captures[0].body_json == captures[1].body_json


def test_gold_label_never_reaches_the_request_or_the_wire() -> None:
    question = make_question()
    billing = Case("v-001", "Refund missing.", "billing")
    sales = Case("v-001", "Refund missing.", "sales")
    requests = [DecisionRequest(c.case_id, c.state, question) for c in (billing, sales)]
    assert requests[0] == requests[1]
    assert request_body(requests[0]) == request_body(requests[1])
    assert request_sha256(requests[0]) == request_sha256(requests[1])
    # Every legitimate option, including the gold label's text, stays in the criteria.
    criteria = json.loads(request_body(requests[0]))["questions"]["department"]["criteria"]
    assert criteria == {o.label: o.description for o in question.options}


# --------------------------------------------------------------------------- #
# Successful bodies: byte-exact preservation, then pure normalization
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "raw",
    [
        RAW_NONCANONICAL.encode("utf-8"),
        b'{\n\t"model": "jev-1.13.0" , "answers": {}, "usage": {} }\n',
        b"{",
        b"",
        b'{"model":"jev-1.13.0","model":"jev-1.13.0"}',
        "café \U0001f600 \u0000".encode(),
        b"\xe2\x82\xac" * 3,
        b" " * MAX_RESPONSE_BYTES,
    ],
    ids=[
        "noncanonical",
        "whitespace",
        "truncated-json",
        "empty",
        "duplicate-keys",
        "unicode-and-nul",
        "multibyte",
        "exactly-max",
    ],
)
def test_successful_body_is_captured_byte_for_byte_without_repair(raw: bytes) -> None:
    model, connect = model_over(ok(raw))
    capture = model.decide(make_request(), timeout_s=5.0)
    assert capture.failure_code is None
    assert capture.body_json is not None
    assert capture.body_json.encode("utf-8") == raw
    assert capture.warnings == ()
    assert connect.log[0].closed == 1
    # A round trip through the wire codec keeps the same bytes.
    assert from_data(type(capture), to_data(capture)) == capture


def test_noncanonical_valid_body_normalizes_to_the_selected_label() -> None:
    model, _ = model_over(ok(RAW_NONCANONICAL))
    capture = model.decide(make_request(), timeout_s=5.0)
    assert capture.body_json == RAW_NONCANONICAL
    outcome = normalize(capture, make_question(), model.identity())
    assert isinstance(outcome, ChoiceAnswer)
    assert outcome.choice == "billing"
    assert outcome.probabilities == (("billing", 0.95), ("technical", 0.025), ("sales", 0.025))
    assert outcome.selected_probability == 0.95
    assert outcome.provider_confidence == 0.925
    assert outcome.warnings == ()
    assert evaluate(outcome, make_lock().contract.policy).action == "ACT"


@pytest.mark.parametrize(
    ("body", "code", "warning", "action"),
    [
        ("{", "malformed_response", "normalize.invalid_json", "ESCALATE"),
        (
            '{"model":"jev-1.13.0","model":"jev-1.13.0"}',
            "malformed_response",
            "normalize.invalid_json",
            "ESCALATE",
        ),
        (
            json.dumps(
                {"model": MODEL, "answers": {}, "usage": {"input_tokens": 1, "output_tokens": 0}}
            ),
            "malformed_response",
            "normalize.answers",
            "ESCALATE",
        ),
        (
            jev_body(make_question(), model="jev-1.12.0"),
            "identity_mismatch",
            "normalize.answering_model",
            "ESCALATE",
        ),
        (
            jev_body(make_question(), choice="refunds"),
            "unknown_choice",
            "normalize.unknown_choice",
            "DENY",
        ),
        (
            jev_body(make_question(), probabilities={"billing": 0.95, "technical": 0.05}),
            "malformed_response",
            "normalize.probabilities_keys",
            "ESCALATE",
        ),
        (
            jev_body(
                make_question(),
                probabilities={"billing": 0.8085, "technical": 0.0877, "sales": 0.1039},
            ),
            "malformed_response",
            "normalize.probability_sum",
            "ESCALATE",
        ),
        (
            jev_body(make_question(), usage={"input_tokens": 1}),
            "malformed_response",
            "normalize.usage.keys",
            "ESCALATE",
        ),
        (
            jev_body(make_question(), action={"act": True}),
            "malformed_response",
            "normalize.answer_keys",
            "ESCALATE",
        ),
    ],
    ids=[
        "invalid-json",
        "duplicate-keys",
        "wrong-question",
        "wrong-model",
        "unknown-choice",
        "option-mismatch",
        "laya-rounding",
        "usage-shape",
        "extra-answer-field",
    ],
)
def test_captured_bodies_are_classified_by_pure_normalization(
    body: str, code: str, warning: str, action: str
) -> None:
    model, _ = model_over(ok(body))
    capture = model.decide(make_request(), timeout_s=5.0)
    assert capture.body_json == body  # retained even when rejected
    outcome = normalize(capture, make_question(), model.identity())
    assert isinstance(outcome, ProviderFailure)
    assert outcome.code == code
    assert outcome.warnings == (warning,)
    decision = evaluate(outcome, make_lock().contract.policy)
    assert decision.action == action


def test_selected_probability_gates_act_not_vendor_confidence() -> None:
    question = make_question()
    low = jev_body(
        question,
        choice="sales",
        probabilities={"billing": 0.9, "technical": 0.1, "sales": 0.0},
        confidence=0.99,
    )
    model, _ = model_over(ok(low))
    outcome = normalize(model.decide(make_request(), timeout_s=5.0), question, model.identity())
    assert isinstance(outcome, ChoiceAnswer)
    assert outcome.choice == "sales"
    assert outcome.selected_probability == 0.0
    assert outcome.provider_confidence == 0.99
    policy = make_lock().contract.policy
    decision = evaluate(outcome, policy)
    assert decision.action == "ABSTAIN"
    assert decision.reason == "policy.low_confidence"


# --------------------------------------------------------------------------- #
# Frozen failure mapping
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (401, "provider_error"),
        (422, "provider_error"),
        (429, "rate_limit"),
        (529, "unavailable"),
        (301, "provider_error"),
        (302, "provider_error"),
        (307, "provider_error"),
        (308, "provider_error"),
        (400, "provider_error"),
        (403, "provider_error"),
        (404, "provider_error"),
        (500, "unavailable"),
        (502, "unavailable"),
        (503, "unavailable"),
        (201, "provider_error"),
        (204, "provider_error"),
    ],
)
def test_http_status_mapping_is_frozen_and_error_bodies_are_not_retained(
    status: int, code: str
) -> None:
    leaking = b'{"error":"Authorization: Bearer ' + MOCK_KEY.encode() + b'"}'
    model, connect = model_over(Script(status, leaking))
    capture = model.decide(make_request(), timeout_s=5.0)
    assert capture.failure_code == code
    assert capture.body_json is None
    assert capture.warnings == (f"jev.http:{status}",)
    assert connect.log[0].read_amounts == []  # the error body is never read
    assert connect.log[0].closed == 1
    assert MOCK_KEY not in json.dumps(to_data(capture))
    outcome = normalize(capture, make_question(), model.identity())
    assert outcome == ProviderFailure(code, (f"jev.http:{status}",), False)
    assert evaluate(outcome, make_lock().contract.policy).action == "ESCALATE"
    # One attempt only: no redirect was followed and no retry was made.
    assert connect.connections == 1


@pytest.mark.parametrize("stage", ["connect", "request", "response", "read"])
def test_socket_timeout_at_any_stage_is_a_timeout_and_the_model_stays_usable(
    stage: str,
) -> None:
    question = make_question()
    timing_out = failing(stage, TimeoutError("timed out"))
    model, connect = model_over(timing_out, ok(jev_body(question)))
    first = model.decide(DecisionRequest("v-timeout", "s", question), timeout_s=0.25)
    assert first.failure_code == "timeout"
    assert first.warnings == ()
    assert first.body_json is None
    if stage != "connect":
        assert connect.log[0].closed == 1
    second = model.decide(DecisionRequest("v-healthy", "s", question), timeout_s=5.0)
    assert second.failure_code is None
    assert second.body_json == jev_body(question)
    assert connect.connections == 2  # a later case is a new attempt, never a retry
    assert model._attempts == 2


@pytest.mark.parametrize(
    "error",
    [
        ConnectionRefusedError(),
        ConnectionResetError(),
        ssl.SSLError(),
        ssl.SSLCertVerificationError(),
        OSError("network unreachable"),
        http.client.RemoteDisconnected(""),
        http.client.BadStatusLine("x"),
        http.client.IncompleteRead(b""),
        http.client.LineTooLong("status"),
    ],
    ids=lambda e: type(e).__name__,
)
def test_connection_tls_and_protocol_errors_are_unavailable(error: BaseException) -> None:
    for stage in ("connect", "request", "response", "read"):
        model, connect = model_over(failing(stage, error))
        capture = model.decide(make_request(), timeout_s=5.0)
        assert capture.failure_code == "unavailable", stage
        assert capture.warnings == (f"jev.transport:{type(error).__name__}",)
        assert capture.body_json is None
        if stage != "connect":
            assert connect.log[0].closed == 1


def test_unexpected_exception_is_bounded_provider_error_and_base_exceptions_propagate() -> None:
    model, _ = model_over(Script(raise_on_response=ValueError("boom " + MOCK_KEY)))
    capture = model.decide(make_request(), timeout_s=5.0)
    assert capture.failure_code == "provider_error"
    assert capture.warnings == ("jev.exception:ValueError",)
    model, _ = model_over(Script(raise_on_response=KeyboardInterrupt()))
    with pytest.raises(KeyboardInterrupt):
        model.decide(make_request(), timeout_s=5.0)


def test_oversized_body_is_malformed_after_a_bounded_read() -> None:
    model, connect = model_over(ok(b"x" * (MAX_RESPONSE_BYTES + 1)))
    capture = model.decide(make_request(), timeout_s=5.0)
    assert capture.failure_code == "malformed_response"
    assert capture.warnings == ("jev.body_oversized",)
    assert capture.body_json is None
    assert connect.log[0].read_amounts == [MAX_RESPONSE_BYTES + 1]
    huge, connect = model_over(ok(b"y" * (4 * MAX_RESPONSE_BYTES)))
    huge.decide(make_request(), timeout_s=5.0)
    assert connect.log[0].read_amounts == [MAX_RESPONSE_BYTES + 1]  # never more than the bound


@pytest.mark.parametrize("raw", [b"\xff\xfe", b'{"model": "\xc3"}', b"\xed\xa0\x80"])
def test_invalid_utf8_body_is_malformed(raw: bytes) -> None:
    model, _ = model_over(ok(raw))
    capture = model.decide(make_request(), timeout_s=5.0)
    assert capture.failure_code == "malformed_response"
    assert capture.warnings == ("jev.body_not_utf8",)
    assert capture.body_json is None


def test_scripted_reply_with_an_unknown_failure_code_is_rejected_by_the_record() -> None:
    def exchange(payload: bytes, timeout: float) -> jev_module._Reply:
        del payload, timeout
        return jev_module._Reply(None, "weird", ())

    model = JevModel._with_exchange(exchange)
    with pytest.raises(SchemaError, match="failure_code"):
        model.decide(make_request(), timeout_s=5.0)


# --------------------------------------------------------------------------- #
# Deadline validation, request validation, close
# --------------------------------------------------------------------------- #


def test_invalid_timeouts_and_non_requests_raise_before_any_transport() -> None:
    model, connect = model_over(ok(jev_body(make_question())))
    for timeout in INVALID_TIMEOUTS:
        with pytest.raises(SchemaError, match="timeout_s"):
            model.decide(make_request(), timeout_s=timeout)  # type: ignore[arg-type]
    for bad in (None, "v-001", to_data(make_request()), make_question()):
        with pytest.raises(SchemaError, match="request"):
            model.decide(bad, timeout_s=5.0)  # type: ignore[arg-type]
    assert connect.connections == 0
    assert model._attempts == 0


def test_close_is_idempotent_and_stops_all_requests() -> None:
    question = make_question()
    model, connect = model_over(ok(jev_body(question)))
    before = model.decide(make_request(), timeout_s=5.0)
    assert before.body_json is not None
    identity = model.identity()
    model.close()
    model.close()
    after = model.decide(make_request(), timeout_s=5.0)
    assert after.failure_code == "unavailable"
    assert after.warnings == ("jev.unavailable:closed",)
    assert after.identity == identity
    assert after.request_sha256 == before.request_sha256
    assert connect.connections == 1
    assert model._attempts == 1
    assert model._closed is True


# --------------------------------------------------------------------------- #
# Credential hygiene across every output
# --------------------------------------------------------------------------- #


def test_key_never_enters_identity_captures_warnings_or_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    question = make_question()
    scripts = [
        ok(jev_body(question)),
        Script(401, MOCK_KEY.encode()),
        Script(raise_on_response=OSError(MOCK_KEY)),
        Script(raise_on_response=ValueError(MOCK_KEY)),
        ok(b"\xff"),
    ]
    texts: list[str] = []
    for script in scripts:
        model, connect = model_over(script)
        capture = model.decide(make_request(), timeout_s=5.0)
        texts.append(json.dumps(to_data(capture)))
        texts.append(json.dumps(to_data(model.identity())))
        texts.append(repr(model) + repr(model._exchange) + repr(capture))
        assert connect.connections == 1
        model.close()
    monkeypatch.setenv(API_KEY_ENV, "bad key")
    with pytest.raises(ProviderSetupError) as excinfo:
        JevModel()
    texts.append(str(excinfo.value) + repr(excinfo.value))
    assert all("SECRETMARKER" not in text and "bad key" not in text for text in texts)
    # The header mapping is the only place the key exists, and it is built once.
    model, connect = model_over(ok(jev_body(question)))
    model.decide(make_request(), timeout_s=5.0)
    assert connect.log[0].headers["Authorization"] == f"Bearer {MOCK_KEY}"
    assert MOCK_KEY not in json.dumps(to_data(model.identity()))


# --------------------------------------------------------------------------- #
# Recorded (mocked) captures: lock, bundle, schema, offline replay without transport
# --------------------------------------------------------------------------- #


def jev_identity() -> ModelIdentity:
    return JevModel(offline=True).identity()


def recorded_bundle() -> tuple[Any, list[str]]:
    """A bundle whose records are mocked Jev captures taken through the real adapter seam."""
    lock = make_lock(identity=jev_identity())
    question = lock.contract.question
    bodies: list[str] = []
    records = []
    for index, case in enumerate(lock.verification_cases):
        if index == 1:
            body = RAW_NONCANONICAL.replace('"choice": "billing"', '"choice": "technical"')
            body = body.replace('"billing": 0.95', '"billing": 0.025').replace(
                '"technical": 0.025', '"technical": 0.95'
            )
        else:
            body = jev_body(question, choice=case.expected_label)
        model, _ = model_over(ok(body))
        capture = model.decide(DecisionRequest(case.case_id, case.state, question), timeout_s=5.0)
        assert capture.body_json == body
        bodies.append(body)
        records.append(record_for(lock, case, body=capture.body_json))
    return make_bundle(lock, tuple(records)), bodies


def test_recorded_jev_bundle_validates_against_the_published_schemas(tmp_path: Path) -> None:
    bundle, bodies = recorded_bundle()
    assert bundle.lock.model_identity.provider == "jev"
    assert bundle.verdict.status in {"PASS", "BLOCK", "INCONCLUSIVE"}
    assert not any(reason.startswith("fault.") for reason in bundle.verdict.reasons)
    assert [fault.decision.action for fault in bundle.faults] == [
        spec.expected_action for spec in bundle.lock.fault_inventory
    ]
    out = write_bundle(bundle, tmp_path / "run")
    validate_bundle_directory(out)
    valid("lock.schema.json", json.loads((out / "lock.json").read_text(encoding="utf-8")))
    rows = [json.loads(line) for line in (out / "records.jsonl").read_text().split("\n")[:-1]]
    assert [row["capture"]["body_json"] for row in rows] == bodies  # byte-exact in the bundle
    assert all(row["capture"]["identity"]["provider"] == "jev" for row in rows)


REPLAY_CHILD = r"""
import importlib.abc, json, socket, sys


class Blocked(RuntimeError):
    pass


def block(*args, **kwargs):
    raise Blocked("blocked")


for name in ("socket", "create_connection", "socketpair", "getaddrinfo"):
    setattr(socket, name, block)


class Deny(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name.startswith(("actseal.experimental", "actseal.adapters", "http", "ssl", "urllib")):
            raise ImportError("forbidden import during replay: " + name)
        return None


sys.meta_path.insert(0, Deny())
from pathlib import Path
from actseal.replay import replay
from actseal.serialization import to_data

verdict = replay(Path(sys.argv[1]), expected_lock_sha256=sys.argv[2])
forbidden = ("actseal.experimental", "actseal.adapters", "http", "ssl")
loaded = sorted(m for m in sys.modules if m.startswith(forbidden))
print(json.dumps({"verdict": to_data(verdict), "loaded": loaded}))
"""


def test_recorded_jev_bundle_replays_offline_without_importing_the_transport(
    tmp_path: Path,
) -> None:
    bundle, _ = recorded_bundle()
    out = write_bundle(bundle, tmp_path / "run")
    result = subprocess.run(  # noqa: S603 - fixed interpreter and literal script, no user input
        [sys.executable, "-I", "-W", "error", "-c", REPLAY_CHILD, str(out), bundle.lock.sha256],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    report = json.loads(result.stdout.splitlines()[-1])
    assert report["loaded"] == []
    assert report["verdict"] == to_data(bundle.verdict)
    # Tampering with one recorded Jev body is caught by the same offline replay.
    data = (out / "records.jsonl").read_bytes()
    recorded = b'\\"choice\\": \\"technical\\"'  # the body text is a JSON string in the row
    assert recorded in data
    (out / "records.jsonl").write_bytes(data.replace(recorded, b'\\"choice\\": \\"billing\\"', 1))
    tampered = subprocess.run(  # noqa: S603 - fixed interpreter and literal script, no user input
        [sys.executable, "-I", "-c", REPLAY_CHILD, str(out), bundle.lock.sha256],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert tampered.returncode == 0, tampered.stderr[-2000:]
    assert json.loads(tampered.stdout.splitlines()[-1])["verdict"]["status"] == "ERROR"


def test_recorded_captures_round_trip_through_the_wire_codec() -> None:
    bundle, _ = recorded_bundle()
    for record in bundle.records:
        decoded = from_data(type(record), to_data(record))
        assert decoded == record
        assert strict_json_loads(decoded.capture.body_json or "") == strict_json_loads(
            record.capture.body_json or ""
        )
        fresh = normalize(
            decoded.capture, bundle.lock.contract.question, bundle.lock.model_identity
        )
        assert fresh == decoded.outcome
        assert evaluate(fresh, bundle.lock.contract.policy) == decoded.decision


# --------------------------------------------------------------------------- #
# Import isolation of the adapter module itself
# --------------------------------------------------------------------------- #


def test_adapter_import_performs_no_network_process_or_environment_access() -> None:
    script = (
        "import os, socket, subprocess, sys\n"
        "class Blocked(RuntimeError):\n"
        "    pass\n"
        "def block(*a, **k):\n"
        "    raise Blocked('blocked')\n"
        "class BlockedSocket(socket.socket):\n"
        "    def __init__(self, *a, **k):\n"
        "        raise Blocked('socket')\n"
        "socket.socket = BlockedSocket\n"
        "for n in ('create_connection', 'getaddrinfo'):\n"
        "    setattr(socket, n, block)\n"
        "subprocess.Popen = block\n"
        "class Env(dict):\n"
        "    def get(self, key, default=None):\n"
        "        if key == 'JEV_API_KEY':\n"
        "            raise Blocked('environment read at import')\n"
        "        return super().get(key, default)\n"
        "os.environ = Env(os.environ)\n"
        "import actseal.experimental.providers.jev as jev\n"
        "model = jev.JevModel(offline=True)\n"
        "loaded = sorted(m.split('.')[0] for m in sys.modules if m.split('.')[0] in "
        "('laya', 'torch', 'transformers', 'huggingface_hub', 'safetensors', 'numpy'))\n"
        "print(loaded, model.identity().provider)\n"
    )
    result = subprocess.run(  # noqa: S603 - fixed interpreter and literal script, no user input
        [sys.executable, "-I", "-W", "error", "-c", script],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
        env={**os.environ, "JEV_API_KEY": "must-not-be-read-at-import"},
    )
    assert result.returncode == 0, result.stderr[-2000:]
    assert result.stdout.strip() == "[] jev"


def test_wrong_model_response_is_detected_by_replace_not_argmax() -> None:
    """Sanity: dataclasses.replace of the identity is how a foreign identity is expressed."""
    identity = jev_identity()
    foreign = replace(identity, revision=identity.revision + ":fault")
    capture = model_over(ok(jev_body(make_question())))[0].decide(make_request(), timeout_s=5.0)
    outcome = normalize(replace(capture, identity=foreign), make_question(), identity)
    assert isinstance(outcome, ProviderFailure)
    assert outcome.code == "identity_mismatch"
