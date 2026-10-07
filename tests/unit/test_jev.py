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
import inspect
import io
import json
import os
import ssl
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, cast

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
from provider_support import INVALID_TIMEOUTS

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
    #: Declared unread fixed-length bytes reported after the body is drained
    #: (``None`` = close-delimited/chunked framing, as ``HTTPResponse.length``).
    length: int | None = None
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
    delivered: int = 0  # body bytes the adapter actually consumed
    closed: int = 0


class FakeResponse:
    def __init__(self, sent: Sent, script: Script) -> None:
        self._sent = sent
        self._script = script
        self.status = script.status
        self.length = script.length
        self._buffer = script.body

    def read(self, amt: int) -> bytes:
        self._sent.read_amounts.append(amt)
        if self._script.raise_on_read is not None:
            raise self._script.raise_on_read
        chunk, self._buffer = self._buffer[:amt], self._buffer[amt:]
        self._sent.delivered += len(chunk)
        return chunk


# --------------------------------------------------------------------------- #
# Real ``http.client.HTTPResponse`` fed from memory (no socket): genuine framing
# --------------------------------------------------------------------------- #


class _MemorySocket:
    """The one method ``HTTPResponse`` needs from a socket: ``makefile``."""

    def __init__(self, raw: bytes) -> None:
        self._file = io.BytesIO(raw)

    def makefile(self, mode: str, *args: object, **kwargs: object) -> io.BytesIO:
        del mode, args, kwargs
        return self._file


def real_response(raw_http: bytes) -> http.client.HTTPResponse:
    response = http.client.HTTPResponse(cast(Any, _MemorySocket(raw_http)), method="POST")
    response.begin()
    return response


class CountingResponse:
    """Pass-through over a genuine ``HTTPResponse`` that records what the adapter consumed."""

    def __init__(self, inner: http.client.HTTPResponse, connection: RealResponseConnection) -> None:
        self._inner = inner
        self._connection = connection

    @property
    def status(self) -> int:
        return self._inner.status

    @property
    def length(self) -> int | None:
        return self._inner.length

    def read(self, amt: int) -> bytes:
        self._connection.read_amounts.append(amt)
        piece = self._inner.read(amt)
        self._connection.delivered += len(piece)
        return piece


class RealResponseConnection:
    """A connection whose ``getresponse`` is a genuine ``HTTPResponse`` over bytes."""

    def __init__(self, raw_http: bytes, log: list[Sent], timeout: float) -> None:
        self._raw = raw_http
        self._log = log
        self._timeout = timeout
        self.response: http.client.HTTPResponse | None = None
        self.read_amounts: list[int] = []
        self.delivered = 0
        self.closed = 0

    def request(self, method: str, url: str, body: bytes, headers: Mapping[str, str]) -> None:
        self._log.append(Sent(method, url, bytes(body), dict(headers), self._timeout))

    def getresponse(self) -> CountingResponse:
        self.response = real_response(self._raw)
        return CountingResponse(self.response, self)

    def close(self) -> None:
        self.closed += 1


class RealResponseConnect:
    def __init__(self, raw_http: bytes) -> None:
        self._raw = raw_http
        self.log: list[Sent] = []
        self.connections: list[RealResponseConnection] = []

    def __call__(self, timeout: float) -> RealResponseConnection:
        connection = RealResponseConnection(self._raw, self.log, timeout)
        self.connections.append(connection)
        return connection


def fixed_length_http(body: bytes, *, declared: int | None = None, status: str = "200 OK") -> bytes:
    length = len(body) if declared is None else declared
    head = (
        f"HTTP/1.1 {status}\r\nContent-Type: application/json\r\nContent-Length: {length}\r\n\r\n"
    )
    return head.encode("ascii") + body


def chunked_http(pieces: list[bytes], *, terminated: bool = True) -> bytes:
    head = b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
    head += b"Transfer-Encoding: chunked\r\n\r\n"
    frame = b"".join(f"{len(piece):x}\r\n".encode("ascii") + piece + b"\r\n" for piece in pieces)
    return head + frame + (b"0\r\n\r\n" if terminated else b"")


def close_delimited_http(body: bytes) -> bytes:
    return b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n" + body


def model_over_http(raw_http: bytes, key: str = MOCK_KEY) -> tuple[JevModel, RealResponseConnect]:
    connect = RealResponseConnect(raw_http)
    return JevModel._with_exchange(jev_module._HttpsExchange(key, connect)), connect


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
    model, _ = model_over(ok(jev_body(make_question())))
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


def test_offline_setup_is_rejected_before_any_environment_read_or_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PLAN E line 352: offline/missing-key setup is rejected without a request."""
    reads: list[str] = []

    def key_tripwire() -> str:
        reads.append("environment")
        raise AssertionError("JEV_API_KEY was read in offline mode")

    def connect_tripwire(timeout: float) -> jev_module._Connection:
        reads.append(f"connect:{timeout}")
        raise AssertionError("a transport was constructed in offline mode")

    monkeypatch.setattr(jev_module, "_api_key_from_environment", key_tripwire)
    monkeypatch.setattr(jev_module, "_default_connect", connect_tripwire)
    monkeypatch.setenv(API_KEY_ENV, MOCK_KEY)  # even a valid key does not make offline usable
    with pytest.raises(ProviderSetupError) as excinfo:
        JevModel(offline=True)
    assert str(excinfo.value).startswith("offline:")
    assert MOCK_KEY not in str(excinfo.value)
    assert reads == []
    # The keyword keeps its frozen signature and default; offline=False is the only usable mode.
    signature = str(inspect.signature(JevModel.__init__))
    assert signature == "(self, *, offline: 'bool' = False) -> 'None'"


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
    # Bounded pieces until end of stream: one piece with the body, one empty piece.
    assert sent.read_amounts == [jev_module._READ_CHUNK, jev_module._READ_CHUNK]
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


#: The exact read budgets for a body that reaches the cap: full pieces, then one detection byte.
CAP_READ_AMOUNTS = [jev_module._READ_CHUNK] * (MAX_RESPONSE_BYTES // jev_module._READ_CHUNK) + [1]


def test_oversized_body_is_malformed_after_a_bounded_read() -> None:
    assert MAX_RESPONSE_BYTES % jev_module._READ_CHUNK == 0
    model, connect = model_over(ok(b"x" * (MAX_RESPONSE_BYTES + 1)))
    capture = model.decide(make_request(), timeout_s=5.0)
    assert capture.failure_code == "malformed_response"
    assert capture.warnings == ("jev.body_oversized",)
    assert capture.body_json is None
    # Exactly cap + 1 bytes are requested and consumed: the last read asks for one byte.
    assert connect.log[0].read_amounts == CAP_READ_AMOUNTS
    assert connect.log[0].delivered == MAX_RESPONSE_BYTES + 1
    huge, connect = model_over(ok(b"y" * (4 * MAX_RESPONSE_BYTES)))
    huge.decide(make_request(), timeout_s=5.0)
    assert connect.log[0].read_amounts == CAP_READ_AMOUNTS
    assert connect.log[0].delivered == MAX_RESPONSE_BYTES + 1
    # A declared fixed length far above the cap changes nothing: actual bytes decide.
    declared, connect = model_over(Script(200, b"z" * (MAX_RESPONSE_BYTES + 1), length=10**9))
    assert declared.decide(make_request(), timeout_s=5.0).warnings == ("jev.body_oversized",)
    assert connect.log[0].delivered == MAX_RESPONSE_BYTES + 1
    # At the cap the detection byte finds end of stream: complete, nothing beyond consumed.
    at_cap, connect = model_over(ok(b"w" * MAX_RESPONSE_BYTES))
    assert at_cap.decide(make_request(), timeout_s=5.0).failure_code is None
    assert connect.log[0].read_amounts == CAP_READ_AMOUNTS
    assert connect.log[0].delivered == MAX_RESPONSE_BYTES


def test_fixed_length_body_ending_early_is_unavailable_not_a_capture() -> None:
    """The scripted double: a short body with declared bytes still unread (``length`` > 0)."""
    body = jev_body(make_question()).encode("utf-8")
    model, connect = model_over(Script(200, body, length=10))
    capture = model.decide(make_request(), timeout_s=5.0)
    assert capture.failure_code == "unavailable"
    assert capture.warnings == ("jev.transport:incomplete_body",)
    assert capture.body_json is None
    assert connect.log[0].closed == 1
    outcome = normalize(capture, make_question(), model.identity())
    assert evaluate(outcome, make_lock().contract.policy).action == "ESCALATE"


# --------------------------------------------------------------------------- #
# Genuine HTTP framing through http.client.HTTPResponse (REVIEW 05 finding 2)
# --------------------------------------------------------------------------- #


def test_real_response_complete_fixed_length_body_is_captured_exactly() -> None:
    body = jev_body(make_question()).encode("utf-8")
    model, connect = model_over_http(fixed_length_http(body))
    capture = model.decide(make_request(), timeout_s=5.0)
    assert capture.failure_code is None
    assert capture.body_json == body.decode("utf-8")
    response = connect.connections[0].response
    assert response is not None
    assert response.length == 0
    assert response.isclosed()
    assert connect.connections[0].closed == 1
    outcome = normalize(capture, make_question(), model.identity())
    assert isinstance(outcome, ChoiceAnswer)


@pytest.mark.parametrize("missing", [1, 10, 1000])
def test_real_response_premature_eof_on_fixed_length_body_is_unavailable(missing: int) -> None:
    """The reviewer's reproduction: declared length exceeds the delivered complete JSON."""
    body = jev_body(make_question()).encode("utf-8")
    model, connect = model_over_http(fixed_length_http(body, declared=len(body) + missing))
    capture = model.decide(make_request(), timeout_s=5.0)
    assert capture.failure_code == "unavailable"
    assert capture.warnings == ("jev.transport:incomplete_body",)
    assert capture.body_json is None
    response = connect.connections[0].response
    assert response is not None
    assert response.length == missing  # declared bytes that never arrived
    assert connect.connections[0].closed == 1
    assert len(connect.connections) == 1  # no retry
    decision = evaluate(
        normalize(capture, make_question(), model.identity()), make_lock().contract.policy
    )
    assert decision.action == "ESCALATE"
    assert decision.reason == "provider.unavailable"


def test_real_response_complete_chunked_body_is_captured_exactly() -> None:
    body = jev_body(make_question()).encode("utf-8")
    pieces = [body[:7], body[7:50], body[50:]]
    model, connect = model_over_http(chunked_http(pieces))
    capture = model.decide(make_request(), timeout_s=5.0)
    assert capture.failure_code is None
    assert capture.body_json == body.decode("utf-8")
    response = connect.connections[0].response
    assert response is not None
    assert response.chunked is True
    assert response.isclosed()


@pytest.mark.parametrize(
    "frame",
    [
        chunked_http([b'{"model": "jev-1.13.0", "answers": {}, "usage": {}}'], terminated=False),
        chunked_http([b'{"model": "jev-1.13.0"', b', "answers": {}}'], terminated=False),
        b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n40\r\n{"model": "jev',
    ],
    ids=["missing-terminator", "two-chunks-no-terminator", "truncated-inside-chunk"],
)
def test_real_response_truncated_chunked_body_is_unavailable(frame: bytes) -> None:
    model, connect = model_over_http(frame)
    capture = model.decide(make_request(), timeout_s=5.0)
    assert capture.failure_code == "unavailable"
    assert capture.warnings == ("jev.transport:IncompleteRead",)
    assert capture.body_json is None
    assert connect.connections[0].closed == 1


def test_real_response_close_delimited_body_is_complete_at_end_of_stream() -> None:
    body = jev_body(make_question()).encode("utf-8")
    model, connect = model_over_http(close_delimited_http(body))
    capture = model.decide(make_request(), timeout_s=5.0)
    assert capture.failure_code is None
    assert capture.body_json == body.decode("utf-8")
    response = connect.connections[0].response
    assert response is not None
    assert response.length is None
    assert response.will_close is True


@pytest.mark.parametrize(
    "frame",
    [
        fixed_length_http(b"x" * (MAX_RESPONSE_BYTES + 1)),
        fixed_length_http(b"x" * (MAX_RESPONSE_BYTES + 5), declared=4 * MAX_RESPONSE_BYTES),
        chunked_http([b"y" * 300_000, b"y" * 300_000, b"y" * 300_000, b"y" * 300_000]),
        close_delimited_http(b"z" * (2 * MAX_RESPONSE_BYTES)),
    ],
    ids=["fixed-over-cap", "declared-far-over-delivered-over", "chunked-over-cap", "close-over"],
)
def test_real_response_over_cap_is_oversized_whatever_the_declared_length(frame: bytes) -> None:
    model, connect = model_over_http(frame)
    capture = model.decide(make_request(), timeout_s=5.0)
    assert capture.failure_code == "malformed_response"
    assert capture.warnings == ("jev.body_oversized",)
    assert capture.body_json is None
    assert connect.connections[0].closed == 1
    assert connect.connections[0].delivered == MAX_RESPONSE_BYTES + 1
    assert connect.connections[0].read_amounts == CAP_READ_AMOUNTS


def _chunks(body: bytes, size: int = 300_000) -> list[bytes]:
    return [body[start : start + size] for start in range(0, len(body), size)]


@pytest.mark.parametrize(
    "framing",
    [
        fixed_length_http,
        lambda body: chunked_http(_chunks(body)),
        close_delimited_http,
    ],
    ids=["fixed-length", "chunked", "close-delimited"],
)
@pytest.mark.parametrize("extra", [0, 1, MAX_RESPONSE_BYTES], ids=["at-cap", "cap+1", "2x-cap"])
def test_real_response_consumes_at_most_one_detection_byte_beyond_the_cap(
    framing: Any, extra: int
) -> None:
    """Genuine ``HTTPResponse`` framing: the adapter never consumes more than cap + 1 body bytes."""
    body = b" " * (MAX_RESPONSE_BYTES + extra)
    model, connect = model_over_http(framing(body))
    capture = model.decide(make_request(), timeout_s=5.0)
    connection = connect.connections[0]
    assert connection.read_amounts == CAP_READ_AMOUNTS
    assert connection.closed == 1
    if extra == 0:
        assert capture.failure_code is None
        assert capture.body_json == body.decode("utf-8")
        assert connection.delivered == MAX_RESPONSE_BYTES
        response = connection.response
        assert response is not None
        assert response.isclosed()  # the one-byte detection read reached end of stream
    else:
        assert capture.failure_code == "malformed_response"
        assert capture.warnings == ("jev.body_oversized",)
        assert capture.body_json is None
        assert connection.delivered == MAX_RESPONSE_BYTES + 1


def test_real_response_non_200_status_is_mapped_without_reading_the_body() -> None:
    body = b'{"error": "rate limited"}'
    model, connect = model_over_http(fixed_length_http(body, status="429 Too Many Requests"))
    capture = model.decide(make_request(), timeout_s=5.0)
    assert capture.failure_code == "rate_limit"
    assert capture.warnings == ("jev.http:429",)
    response = connect.connections[0].response
    assert response is not None
    assert response.length == len(body)  # nothing of the error body was consumed


@pytest.mark.parametrize("raw", [b"\xff\xfe", b'{"model": "\xc3"}', b"\xed\xa0\x80"])
def test_invalid_utf8_body_is_malformed(raw: bytes) -> None:
    model, _ = model_over(ok(raw))
    capture = model.decide(make_request(), timeout_s=5.0)
    assert capture.failure_code == "malformed_response"
    assert capture.warnings == ("jev.body_not_utf8",)
    model, _ = model_over_http(fixed_length_http(raw))
    assert model.decide(make_request(), timeout_s=5.0).warnings == ("jev.body_not_utf8",)


# --------------------------------------------------------------------------- #
# Credential echo in a successful body (REVIEW 05 finding 1)
# --------------------------------------------------------------------------- #


def _json_u_escape(text: str) -> str:
    return "".join(f"\\u{ord(character):04x}" for character in text)


ECHO_KEY = 'mock/echo"key\\SECRETMARKER'  # printable ASCII with the JSON-special characters


@pytest.mark.parametrize(
    "body",
    [
        ECHO_KEY,
        '{"error": "Bearer ' + ECHO_KEY + '"}',
        json.dumps({"model": MODEL, "answers": {"department": ECHO_KEY}, "usage": {}}),
        json.dumps({"echo": ECHO_KEY}),  # json.dumps escapes the quote and backslash
        '{"echo": "' + _json_u_escape(ECHO_KEY) + '"}',
        '{"echo": "' + _json_u_escape(ECHO_KEY).upper().replace("\\U", "\\u") + '"}',
        '{"echo": "' + ECHO_KEY[:9] + _json_u_escape(ECHO_KEY[9:]) + '"}',
        '{"echo": "' + json.dumps(_json_u_escape(ECHO_KEY))[1:-1] + '"}',  # escaped twice
        "prefix " + _json_u_escape(ECHO_KEY) + " suffix",  # not even JSON
        _json_u_escape(json.dumps(ECHO_KEY)[1:-1]),
    ],
    ids=[
        "literal",
        "in-error-string",
        "in-valid-envelope",
        "json-dumps-escaped",
        "all-u-escaped",
        "upper-hex-u-escaped",
        "partly-u-escaped",
        "double-escaped",
        "non-json-text",
        "u-escaped-short-escapes",
    ],
)
def test_successful_body_echoing_the_credential_fails_closed(body: str) -> None:
    for build in (
        lambda raw: model_over(ok(raw), key=ECHO_KEY),
        lambda raw: model_over_http(fixed_length_http(raw.encode("utf-8")), key=ECHO_KEY),
    ):
        model, _ = build(body)
        capture = model.decide(make_request(), timeout_s=5.0)
        assert capture.failure_code == "malformed_response"
        assert capture.warnings == ("jev.credential_echo",)
        assert capture.body_json is None
        serialized = json.dumps(to_data(capture)) + repr(capture) + repr(model._exchange)
        assert "SECRETMARKER" not in serialized
        assert ECHO_KEY not in serialized
        outcome = normalize(capture, make_question(), model.identity())
        assert outcome == ProviderFailure("malformed_response", ("jev.credential_echo",), False)
        assert evaluate(outcome, make_lock().contract.policy).action == "ESCALATE"


@pytest.mark.parametrize(
    "body",
    [
        jev_body(make_question()),
        RAW_NONCANONICAL,
        "{",
        '{"echo": "' + ECHO_KEY[:-1] + '"}',  # one character short of the key
        '{"echo": "' + ECHO_KEY[1:] + '"}',
        '{"echo": "' + ECHO_KEY.lower() + '"}',
        '{"echo": "Bearer mock-other-key-SECRETMARKER"}',  # another secret-looking string
        '{"echo": "' + _json_u_escape(ECHO_KEY[:-1]) + '"}',
    ],
    ids=["valid", "noncanonical", "invalid-json", "prefix", "suffix", "case", "other", "u-prefix"],
)
def test_bodies_without_the_credential_are_still_captured_verbatim(body: str) -> None:
    """Control: detection is exact-key only; ordinary bodies, even invalid JSON, are untouched."""
    model, _ = model_over(ok(body), key=ECHO_KEY)
    capture = model.decide(make_request(), timeout_s=5.0)
    assert capture.failure_code is None
    assert capture.body_json == body


def test_credential_detection_helpers_are_exact_and_bounded() -> None:
    assert jev_module._echoes_credential(ECHO_KEY, ECHO_KEY)
    assert jev_module._echoes_credential(_json_u_escape(ECHO_KEY), ECHO_KEY)
    assert not jev_module._echoes_credential(ECHO_KEY[:-1], ECHO_KEY)
    assert jev_module._unescape_json(r"A\"\\\/\n") == 'A"\\/\n'
    assert jev_module._unescape_json(r"\x41 \u00zz") == r"\x41 \u00zz"  # not JSON escapes
    # Up to three nested levels of JSON escaping are resolved; a fourth is not claimed.
    assert jev_module._UNESCAPE_PASSES == 3
    nested = ECHO_KEY
    for level in range(1, 5):
        nested = _json_u_escape(nested)  # each pass adds one level (backslash -> \)
        detected = jev_module._echoes_credential(nested, ECHO_KEY)
        assert detected is (level <= 3), level
    # No claim about other encodings: a base64 form of the key is not detected.
    import base64  # noqa: PLC0415 - documenting the stated limit, not a product path

    encoded = base64.b64encode(ECHO_KEY.encode("ascii")).decode("ascii")
    assert not jev_module._echoes_credential('{"echo": "' + encoded + '"}', ECHO_KEY)


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


def _never(payload: bytes, timeout: float) -> jev_module._Reply:
    del payload, timeout
    raise AssertionError("no exchange expected")


def jev_identity() -> ModelIdentity:
    """The adapter's fixed identity, obtained without environment or transport."""
    return JevModel._with_exchange(_never).identity()


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
        "from actseal.errors import ProviderSetupError\n"
        "try:\n"
        "    jev.JevModel(offline=True)\n"
        "    outcome = 'constructed'\n"
        "except ProviderSetupError as exc:\n"
        "    outcome = 'rejected' if str(exc).startswith('offline:') else 'other'\n"
        "loaded = sorted(m.split('.')[0] for m in sys.modules if m.split('.')[0] in "
        "('laya', 'torch', 'transformers', 'huggingface_hub', 'safetensors', 'numpy'))\n"
        "print(loaded, outcome)\n"
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
    assert result.stdout.strip() == "[] rejected"


def test_wrong_model_response_is_detected_by_replace_not_argmax() -> None:
    """Sanity: dataclasses.replace of the identity is how a foreign identity is expressed."""
    identity = jev_identity()
    foreign = replace(identity, revision=identity.revision + ":fault")
    capture = model_over(ok(jev_body(make_question())))[0].decide(make_request(), timeout_s=5.0)
    outcome = normalize(replace(capture, identity=foreign), make_question(), identity)
    assert isinstance(outcome, ProviderFailure)
    assert outcome.code == "identity_mismatch"
