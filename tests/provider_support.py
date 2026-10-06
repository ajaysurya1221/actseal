"""Shared provider test support: fixture rows, the fake Laya worker and conformance checks.

Three test trees use this module:

* ``tests/unit/test_providers.py`` imports the fixture rows and the fake worker;
* ``tests/conformance`` runs the shared behavioural checks below against every
  provider profile (recorded fixture, the fake-worker Laya double and the
  experimental Jev adapter over a stdlib fake connection);
* ``tests/integration/test_laya.py`` applies the same close-lifecycle check to
  the real pinned model.

The checks are plain functions over the public ``DecisionModel`` protocol, so a
misbehaving adapter (or a deliberately wrong test double) fails with an
``AssertionError`` rather than being routed around. Nothing here imports the
native stack: the Laya double is a stdlib script speaking the worker protocol,
and the Jev double never opens a socket (its connection factory is a fake and
its only API key is a mocked string that is never read from the environment).
"""

from __future__ import annotations

import dataclasses
import hashlib
import inspect
import json
import math
import sys
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any, Final, Literal, Protocol

import pytest

from actseal.adapters.base import DecisionModel
from actseal.adapters.fixture import FixtureModel
from actseal.adapters.laya import ADAPTER_VERSION, ARTIFACT_HASHES, MODEL_ID, REVISION, LayaModel
from actseal.errors import SchemaError
from actseal.experimental.providers import jev as jev_module
from actseal.experimental.providers.jev import JevModel
from actseal.normalization import NORMALIZER_VERSION, normalize, request_sha256
from actseal.records import (
    FAILURE_CODES,
    PROVIDERS,
    CapturedOutcome,
    ChoiceAnswer,
    ChoiceQuestion,
    DecisionRequest,
    ModelIdentity,
    Option,
    ProviderFailure,
)
from actseal.serialization import canonical_json, strict_json_loads, to_data

Lifecycle = Literal["usable", "unavailable"]

# --------------------------------------------------------------------------- #
# Fixture rows
# --------------------------------------------------------------------------- #

ROW_OK: dict[str, Any] = {
    "case_id": "v-001",
    "body_json": '{"type": "choice", "choice": "billing", '
    '"probabilities": {"billing": 0.95, "technical": 0.04, "sales": 0.01}}',
    "failure_code": None,
    "warnings": [],
}
ROW_FAIL: dict[str, Any] = {
    "case_id": "v-002",
    "body_json": None,
    "failure_code": "timeout",
    "warnings": ["w.slow"],
}


def write_rows(path: Path, rows: list[object], *, trailing_newline: bool = True) -> bytes:
    text = "\n".join(json.dumps(row) if not isinstance(row, str) else row for row in rows)
    if trailing_newline:
        text += "\n"
    data = text.encode("utf-8")
    path.write_bytes(data)
    return data


# --------------------------------------------------------------------------- #
# Fake Laya worker (stdlib only; speaks the adapter's JSON-lines protocol)
# --------------------------------------------------------------------------- #

FAKE_WORKER: Final = r"""
import json
import os
import sys
import time

mode = sys.argv[1] if len(sys.argv) > 1 else "ok"
out = sys.stdout.buffer
inp = sys.stdin.buffer


def send(obj):
    out.write(json.dumps(obj).encode("utf-8") + b"\n")
    out.flush()


identity = json.loads(os.environ["ACTSEAL_FAKE_IDENTITY"])
if mode == "hang-on-start":
    time.sleep(60)
if mode == "exit-on-start":
    sys.exit(3)
if mode == "setup-error":
    send({"kind": "setup_error", "warnings": ["laya.setup:ValueError"]})
    sys.exit(1)
if mode == "garbage-on-start":
    out.write(b"not json\n")
    out.flush()
    time.sleep(60)
if mode == "deep-on-start":
    out.write(b"[" * 10001 + b"]" * 10001 + b"\n")
    out.flush()
    time.sleep(60)
if mode == "wrong-identity":
    identity["revision"] = "0000000000000000000000000000000000000000"
if mode == "bad-identity":
    identity = {"provider": "laya"}
if mode == "echo-env":
    send({"kind": "ready", "identity": identity,
          "warnings": ["env:" + os.environ.get("HF_HUB_OFFLINE", "unset")
                       + ":" + os.environ.get("TRANSFORMERS_OFFLINE", "unset")]})
else:
    send({"kind": "ready", "identity": identity,
          "warnings": ["laya.load_warning:RuntimeWarning:clamped"]})
if mode == "stop-reading":
    time.sleep(60)  # ready, but never reads stdin: a large request cannot be written

while True:
    line = inp.readline()
    if not line:
        sys.exit(0)
    msg = json.loads(line)
    if msg["kind"] == "close":
        if mode == "ignore-close":
            time.sleep(60)
        sys.exit(0)
    seq = msg["seq"]
    if mode == "hang-on-decide":
        time.sleep(60)
    if mode == "exit-on-decide":
        sys.exit(4)
    if mode == "garbage-on-decide":
        out.write(b"{\n")
        out.flush()
        continue
    if mode == "huge-on-decide":
        out.write(b"[" + b"1," * 700000 + b"1]\n")
        out.flush()
        continue
    if mode == "deep-on-decide":
        out.write(b"[" * 10001 + b"]" * 10001 + b"\n")
        out.flush()
        continue
    if mode == "duplicate-keys-on-decide":
        out.write(b'{"kind": "reply", "kind": "reply", "seq": ' + str(seq).encode() + b"}\n")
        out.flush()
        continue
    if mode == "slow-reply":
        time.sleep(0.6)
    if mode == "fail-decide":
        send({"kind": "reply", "seq": seq, "failure": "provider_error",
              "warnings": ["laya.exception:RuntimeError"]})
        continue
    if mode == "bad-failure":
        send({"kind": "reply", "seq": seq, "failure": "weird", "warnings": []})
        continue
    if mode == "failure-from-env":
        send({"kind": "reply", "seq": seq, "failure": os.environ["ACTSEAL_FAKE_FAILURE"],
              "warnings": json.loads(os.environ["ACTSEAL_FAKE_WARNINGS"])})
        continue
    if mode == "raw-body-from-env":
        # The recorded body text is spliced into the frame byte-for-byte so the
        # parent sees exactly the provider's own (non-canonical) serialization.
        raw = os.environ["ACTSEAL_FAKE_BODY"].encode("utf-8")
        warnings = json.dumps(json.loads(os.environ["ACTSEAL_FAKE_WARNINGS"])).encode("utf-8")
        out.write(b'{"kind": "reply", "seq": ' + str(seq).encode() + b', "body": ' + raw
                  + b', "warnings": ' + warnings + b"}\n")
        out.flush()
        continue
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
    reply_seq = seq - 1 if mode == "stale-seq" else seq
    send({"kind": "reply", "seq": reply_seq, "body": body,
          "warnings": ["laya.predict_warning:x"] if mode == "warn" else []})
"""

FAKE_LOAD_WARNINGS: Final[tuple[str, ...]] = ("laya.load_warning:RuntimeWarning:clamped",)


def pinned_identity() -> ModelIdentity:
    return ModelIdentity(
        "laya",
        MODEL_ID,
        REVISION,
        ARTIFACT_HASHES,
        ADAPTER_VERSION,
        NORMALIZER_VERSION,
        (("device", "cpu"), ("dtype", "torch.float32"), ("threads", "4")),
    )


def write_fake_worker(directory: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Write the fake worker script and export the pinned identity it reports."""
    script = directory / "fake_worker.py"
    script.write_text(FAKE_WORKER, encoding="utf-8")
    monkeypatch.setenv("ACTSEAL_FAKE_IDENTITY", json.dumps(to_data(pinned_identity())))
    return script


def spawn(
    script: Path, mode: str = "ok", *, startup: float = 10.0, grace: float = 0.3
) -> LayaModel:
    return LayaModel._spawn(
        (sys.executable, str(script), mode),
        offline=True,
        startup_timeout_s=startup,
        close_grace_s=grace,
    )


def child_alive(model: LayaModel) -> bool:
    child = model._child
    return child is not None and child.poll() is None


def child_pid(model: LayaModel) -> int | None:
    child = model._child
    return None if child is None else child.pid


# --------------------------------------------------------------------------- #
# Independent request digest (no actseal serialization involved)
# --------------------------------------------------------------------------- #


def independent_request_digest(request: DecisionRequest) -> str:
    """Recompute the canonical request digest with ``json`` and ``hashlib`` only.

    Mirrors the documented canonical encoding (UTF-8, ``ensure_ascii=False``,
    sorted keys, compact separators) over a hand-built mapping, so a capture's
    ``request_sha256`` is checked against something other than the function
    adapters themselves call.
    """
    payload = {
        "case_id": request.case_id,
        "state": request.state,
        "question": {
            "question_id": request.question.question_id,
            "instructions": request.question.instructions,
            "options": [
                {"label": option.label, "description": option.description}
                for option in request.question.options
            ],
        },
    }
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# Provider profiles: how to obtain a model that emits a given body or failure
# --------------------------------------------------------------------------- #

DEFAULT_CASE_IDS: Final[tuple[str, ...]] = ("v-001",)


class ProviderProfile(Protocol):
    """Everything the shared checks need to know about one provider double."""

    @property
    def name(self) -> str: ...

    @property
    def after_close(self) -> Lifecycle:
        """What ``decide`` returns after ``close``: a body, or ``unavailable``."""
        ...

    @property
    def after_timeout(self) -> Lifecycle:
        """What a later ``decide`` returns after a ``timeout`` capture."""
        ...

    @property
    def load_warnings(self) -> tuple[str, ...]:
        """Warnings the provider prepends to every capture (setup-time warnings)."""
        ...

    @property
    def evidence_only_fields(self) -> tuple[str, ...]:
        """Field names in ``valid_raw_body`` that normalization never uses but must survive."""
        ...

    def open(
        self,
        *,
        body: str | None = None,
        failure: str | None = None,
        warnings: tuple[str, ...] = (),
        case_ids: tuple[str, ...] = DEFAULT_CASE_IDS,
    ) -> DecisionModel:
        """A model whose every listed case yields ``body`` (raw text) or ``failure``."""
        ...

    def open_timing_out(self, question: ChoiceQuestion) -> tuple[DecisionModel, float]:
        """A model and deadline such that case ``v-timeout`` captures ``timeout``.

        Case ``v-healthy`` has a valid answer if the provider is still usable
        afterwards (recorded timeouts are not real inference; a real worker
        timeout terminates the worker).
        """
        ...

    def preserved(self, raw: str) -> str:
        """The exact ``body_json`` text this provider records for raw text ``raw``."""
        ...

    def valid_raw_body(self, question: ChoiceQuestion) -> str:
        """A valid answer for ``question`` in deliberately non-canonical serialization."""
        ...

    def requests_sent(self, model: DecisionModel) -> int:
        """How many requests reached the transport (0 for a provider without one)."""
        ...

    def worker_alive(self, model: DecisionModel) -> bool | None:
        """Whether a resident worker is alive; ``None`` when the provider has none."""
        ...

    def worker_pid(self, model: DecisionModel) -> int | None: ...


def _probabilities(question: ChoiceQuestion, *, selected: str) -> dict[str, float]:
    labels = question.labels
    rest = 0.5 / (len(labels) - 1)
    return {label: 0.5 if label == selected else rest for label in labels}


def _inner_answer_text(question: ChoiceQuestion, *, newline: str) -> str:
    """Unsorted keys, odd spacing and every optional field; valid for both normalizers."""
    probabilities = _probabilities(question, selected=question.labels[0])
    pairs = " ,  ".join(f'"{label}" : {value!r}' for label, value in probabilities.items())
    parts = [
        '{ "type" : "choice" ,',
        newline,
        f'  "choice":"{question.labels[0]}",  "answer_confidence": 0.5, "confidence": 0.25,',
        newline,
        f'  "probabilities" : {{ {pairs} }},  "action": {{"act_probability": 1.0}}  }}',
    ]
    return "".join(parts)


#: Optional inner-answer fields the fixture and Laya normalizers ignore but keep as evidence.
IGNORED_ANSWER_FIELDS: Final[tuple[str, ...]] = ("action", "answer_confidence")


class FixtureProfile:
    """Recorded-response adapter: no transport, close is a no-op, bodies are verbatim."""

    name = "fixture"
    after_close: Lifecycle = "usable"
    after_timeout: Lifecycle = "usable"
    load_warnings: tuple[str, ...] = ()
    evidence_only_fields = IGNORED_ANSWER_FIELDS

    def __init__(self, directory: Path) -> None:
        self._directory = directory
        self._count = 0

    def _write(self, rows: list[object]) -> DecisionModel:
        self._count += 1
        path = self._directory / f"responses-{self._count}.jsonl"
        write_rows(path, rows)
        return FixtureModel(path)

    def open(
        self,
        *,
        body: str | None = None,
        failure: str | None = None,
        warnings: tuple[str, ...] = (),
        case_ids: tuple[str, ...] = DEFAULT_CASE_IDS,
    ) -> DecisionModel:
        if (body is None) == (failure is None):
            raise ValueError("exactly one of body/failure is required")
        rows: list[object] = [
            {"case_id": c, "body_json": body, "failure_code": failure, "warnings": list(warnings)}
            for c in case_ids
        ]
        return self._write(rows)

    def open_timing_out(self, question: ChoiceQuestion) -> tuple[DecisionModel, float]:
        rows: list[object] = [
            {"case_id": "v-timeout", "body_json": None, "failure_code": "timeout", "warnings": []},
            {
                "case_id": "v-healthy",
                "body_json": self.valid_raw_body(question),
                "failure_code": None,
                "warnings": [],
            },
        ]
        return self._write(rows), 30.0

    def preserved(self, raw: str) -> str:
        return raw

    def valid_raw_body(self, question: ChoiceQuestion) -> str:
        return _inner_answer_text(question, newline="\n")

    def requests_sent(self, model: DecisionModel) -> int:
        assert isinstance(model, FixtureModel)
        return 0

    def worker_alive(self, model: DecisionModel) -> bool | None:
        assert isinstance(model, FixtureModel)
        return None

    def worker_pid(self, model: DecisionModel) -> int | None:
        assert isinstance(model, FixtureModel)
        return None


class FakeLayaProfile:
    """Laya adapter over the fake worker: one resident child, close releases it."""

    name = "laya-fake"
    after_close: Lifecycle = "unavailable"
    after_timeout: Lifecycle = "unavailable"
    load_warnings = FAKE_LOAD_WARNINGS
    evidence_only_fields = IGNORED_ANSWER_FIELDS

    def __init__(self, script: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._script = script
        self._monkeypatch = monkeypatch

    def open(
        self,
        *,
        body: str | None = None,
        failure: str | None = None,
        warnings: tuple[str, ...] = (),
        case_ids: tuple[str, ...] = DEFAULT_CASE_IDS,
    ) -> DecisionModel:
        del case_ids  # the fake worker answers every case id alike
        if (body is None) == (failure is None):
            raise ValueError("exactly one of body/failure is required")
        self._monkeypatch.setenv("ACTSEAL_FAKE_WARNINGS", json.dumps(list(warnings)))
        if body is not None:
            self._monkeypatch.setenv("ACTSEAL_FAKE_BODY", body)
            return spawn(self._script, "raw-body-from-env")
        assert failure is not None
        self._monkeypatch.setenv("ACTSEAL_FAKE_FAILURE", failure)
        return spawn(self._script, "failure-from-env")

    def open_timing_out(self, question: ChoiceQuestion) -> tuple[DecisionModel, float]:
        del question
        return spawn(self._script, "hang-on-decide"), 0.3

    def preserved(self, raw: str) -> str:
        return canonical_json(strict_json_loads(raw)).decode("utf-8")

    def valid_raw_body(self, question: ChoiceQuestion) -> str:
        inner = _inner_answer_text(question, newline=" ")
        usage = (
            '{"input_tokens": 59, "output_tokens": 0, "state_tokens": 15, '
            '"state_tokens_dropped": 0, "truncated": false, "truncated_questions": []}'
        )
        answers = f'{{ "{question.question_id}" : {inner} }}'
        return f'{{ "usage": {usage},  "answers" : {answers}, "model":"laya-rl-agent" }}'

    def requests_sent(self, model: DecisionModel) -> int:
        assert isinstance(model, LayaModel)
        return model._sequence

    def worker_alive(self, model: DecisionModel) -> bool | None:
        assert isinstance(model, LayaModel)
        return child_alive(model)

    def worker_pid(self, model: DecisionModel) -> int | None:
        assert isinstance(model, LayaModel)
        return child_pid(model)


# --------------------------------------------------------------------------- #
# Fake Jev connection (stdlib only; the adapter's http.client seam)
# --------------------------------------------------------------------------- #

JEV_MOCK_KEY: Final = "mock-jev-key-for-conformance-only"
JEV_TIMEOUT: Final = "timeout"


class _JevFakeResponse:
    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self._body = body

    def read(self, amt: int) -> bytes:
        chunk, self._body = self._body[:amt], self._body[amt:]
        return chunk


class _JevFakeConnection:
    """One scripted exchange: a status and body, or a socket timeout on ``request``."""

    def __init__(self, script: tuple[str | int, bytes], log: list[dict[str, object]]) -> None:
        self._script = script
        self._log = log

    def request(self, method: str, url: str, body: bytes, headers: Mapping[str, str]) -> None:
        self._log.append({"method": method, "url": url, "body": bytes(body), **dict(headers)})
        if self._script[0] == JEV_TIMEOUT:
            raise TimeoutError("fake socket timeout")

    def getresponse(self) -> _JevFakeResponse:
        status, body = self._script
        assert isinstance(status, int)
        return _JevFakeResponse(status, body)

    def close(self) -> None:
        return


class _JevFakeConnect:
    """Hands out scripted connections in order, repeating the last one indefinitely."""

    def __init__(self, scripts: list[tuple[str | int, bytes]]) -> None:
        self._scripts = scripts
        self.log: list[dict[str, object]] = []

    def __call__(self, timeout: float) -> _JevFakeConnection:
        del timeout
        script = self._scripts.pop(0) if len(self._scripts) > 1 else self._scripts[0]
        return _JevFakeConnection(script, self.log)


class JevProfile:
    """Experimental Jev adapter over a fake connection: no socket, no worker, no key read.

    Successful bodies travel through the adapter's real HTTPS exchange and
    bounded reader (so verbatim capture is tested for real); scripted failure
    codes are injected at the exchange seam, exactly as the Laya double injects
    them at the worker reply, because an honest transport cannot produce every
    frozen code. Jev has no worker: ``worker_alive`` reports whether the
    transport is still open so the shared close checks can assert it is shut.
    """

    name = "jev-fake"
    after_close: Lifecycle = "unavailable"
    after_timeout: Lifecycle = "usable"
    load_warnings: tuple[str, ...] = ()
    #: Validated for shape only; their values never reach the outcome.
    evidence_only_fields = ("usage", "input_tokens", "output_tokens")

    def open(
        self,
        *,
        body: str | None = None,
        failure: str | None = None,
        warnings: tuple[str, ...] = (),
        case_ids: tuple[str, ...] = DEFAULT_CASE_IDS,
    ) -> DecisionModel:
        del case_ids  # the fake connection answers every case alike
        if (body is None) == (failure is None):
            raise ValueError("exactly one of body/failure is required")
        if body is not None:
            inner = jev_module._HttpsExchange(
                JEV_MOCK_KEY, _JevFakeConnect([(200, body.encode("utf-8"))])
            )

            def exchange(payload: bytes, timeout: float) -> jev_module._Reply:
                reply = inner(payload, timeout)
                return jev_module._Reply(reply.body, reply.failure, (*reply.warnings, *warnings))

            return JevModel._with_exchange(exchange)
        assert failure is not None

        def scripted(payload: bytes, timeout: float) -> jev_module._Reply:
            del payload, timeout
            return jev_module._Reply(None, failure, warnings)

        return JevModel._with_exchange(scripted)

    def open_timing_out(self, question: ChoiceQuestion) -> tuple[DecisionModel, float]:
        connect = _JevFakeConnect(
            [(JEV_TIMEOUT, b""), (200, self.valid_raw_body(question).encode("utf-8"))]
        )
        return JevModel._with_exchange(jev_module._HttpsExchange(JEV_MOCK_KEY, connect)), 5.0

    def preserved(self, raw: str) -> str:
        return raw

    def valid_raw_body(self, question: ChoiceQuestion) -> str:
        probabilities = _probabilities(question, selected=question.labels[0])
        pairs = " ,  ".join(f'"{label}" : {value!r}' for label, value in probabilities.items())
        inner = (
            '{ "type" : "choice" ,  "confidence": 0.25, '
            f'"choice":"{question.labels[0]}",  "probabilities" : {{ {pairs} }} }}'
        )
        return (
            '{ "usage" : {"input_tokens": 59, "output_tokens": 0},  '
            f'"answers" : {{ "{question.question_id}" : {inner} }}, "model":"jev-1.13.0" }}'
        )

    def requests_sent(self, model: DecisionModel) -> int:
        assert isinstance(model, JevModel)
        return model._attempts

    def worker_alive(self, model: DecisionModel) -> bool | None:
        assert isinstance(model, JevModel)
        return not model._closed

    def worker_pid(self, model: DecisionModel) -> int | None:
        assert isinstance(model, JevModel)
        return None


PROFILE_NAMES: Final[tuple[str, ...]] = ("fixture", "laya-fake", "jev-fake")


def build_profile(name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProviderProfile:
    if name == "fixture":
        return FixtureProfile(tmp_path)
    if name == "laya-fake":
        return FakeLayaProfile(write_fake_worker(tmp_path, monkeypatch), monkeypatch)
    if name == "jev-fake":
        return JevProfile()
    raise ValueError(f"unknown provider profile: {name}")


# --------------------------------------------------------------------------- #
# Shared behavioural checks (plain assertions over the public protocol)
# --------------------------------------------------------------------------- #

INVALID_TIMEOUTS: Final[tuple[object, ...]] = (
    0,
    0.0,
    -1.0,
    -0.0,
    math.inf,
    -math.inf,
    math.nan,
    True,
    False,
    10**400,  # float() overflows
    "30",
    None,
    [30.0],
)


def question_with(
    question: ChoiceQuestion,
    *,
    question_id: str | None = None,
    instructions: str | None = None,
    options: Iterable[Option] | None = None,
) -> ChoiceQuestion:
    return ChoiceQuestion(
        question.question_id if question_id is None else question_id,
        question.instructions if instructions is None else instructions,
        question.options if options is None else tuple(options),
    )


def request_variants(question: ChoiceQuestion) -> tuple[DecisionRequest, ...]:
    """Requests that differ in exactly one binding-relevant field each."""
    first = question.options[0]
    return (
        DecisionRequest("v-001", "state one", question),
        DecisionRequest("v-002", "state one", question),
        DecisionRequest("v-001", "state two", question),
        DecisionRequest("v-001", "state one ", question),
        DecisionRequest("v-001", "état 😀", question),
        DecisionRequest("v-001", "state one", question_with(question, question_id="other")),
        DecisionRequest(
            "v-001",
            "state one",
            question_with(question, instructions=question.instructions + " Now."),
        ),
        DecisionRequest(
            "v-001", "state one", question_with(question, options=reversed(question.options))
        ),
        DecisionRequest(
            "v-001",
            "state one",
            question_with(
                question,
                options=(Option(first.label, first.description + "!"), *question.options[1:]),
            ),
        ),
    )


def capture_or_fail(
    model: DecisionModel, request: DecisionRequest, timeout_s: float
) -> CapturedOutcome:
    """``decide`` must return a capture; a provider failure is data, never an exception."""
    try:
        capture = model.decide(request, timeout_s=timeout_s)
    except Exception as exc:
        raise AssertionError(f"decide raised {type(exc).__name__} instead of capturing") from exc
    assert isinstance(capture, CapturedOutcome), type(capture).__name__
    return capture


def check_capture_binds(
    capture: CapturedOutcome, request: DecisionRequest, identity: ModelIdentity
) -> None:
    """The capture names exactly this request and this model, with no fallback."""
    assert isinstance(capture, CapturedOutcome)
    assert capture.request_sha256 == independent_request_digest(request)
    assert capture.request_sha256 == request_sha256(request)
    assert capture.identity == identity
    assert capture.fallback_used is False
    assert (capture.body_json is None) != (capture.failure_code is None)
    assert isinstance(capture.warnings, tuple)
    assert all(type(w) is str and w for w in capture.warnings)


def check_identity_immutable(model: DecisionModel) -> ModelIdentity:
    """``identity()`` is a frozen record and the same value on every call."""
    identity = model.identity()
    assert isinstance(identity, ModelIdentity)
    assert identity.provider in PROVIDERS
    assert model.identity() == identity
    with pytest.raises(dataclasses.FrozenInstanceError):
        identity.revision = "tampered"  # type: ignore[misc]
    assert model.identity() == identity
    assert model.identity().revision != "tampered"
    return identity


def check_protocol_shape(model: DecisionModel) -> None:
    """Structural conformance: the three methods with the frozen signatures."""
    model_type = type(model)
    assert callable(getattr(model_type, "identity", None))
    assert callable(getattr(model_type, "decide", None))
    assert callable(getattr(model_type, "close", None))
    decide = inspect.signature(model_type.decide)
    names = list(decide.parameters)
    assert names == ["self", "request", "timeout_s"], names
    assert decide.parameters["timeout_s"].kind is inspect.Parameter.KEYWORD_ONLY
    assert decide.parameters["request"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert list(inspect.signature(model_type.identity).parameters) == ["self"]
    assert list(inspect.signature(model_type.close).parameters) == ["self"]


def check_request_binding(model: DecisionModel, question: ChoiceQuestion) -> None:
    """Every variant of the request is bound to its own independently computed digest."""
    identity = model.identity()
    digests: list[str] = []
    for request in request_variants(question):
        capture = capture_or_fail(model, request, 5.0)
        check_capture_binds(capture, request, identity)
        digests.append(capture.request_sha256)
    assert len(set(digests)) == len(digests), "distinct requests produced equal digests"
    assert model.identity() == identity


def check_timeout_validation(model: DecisionModel, request: DecisionRequest) -> None:
    """Every invalid deadline raises ``SchemaError`` naming ``timeout_s`` (never a capture)."""
    for timeout in INVALID_TIMEOUTS:
        message: str | None = None
        try:
            model.decide(request, timeout_s=timeout)  # type: ignore[arg-type]
        except SchemaError as exc:
            message = str(exc)
        if message is None:
            raise AssertionError(f"timeout_s={timeout!r} was accepted instead of rejected")
        assert "timeout_s" in message, message


def check_typed_failure(
    model: DecisionModel,
    request: DecisionRequest,
    code: str,
    expected_warnings: tuple[str, ...],
    *,
    timeout_s: float = 5.0,
) -> CapturedOutcome:
    """A provider failure is a capture with the frozen code and no body, normalizable as such."""
    assert code in FAILURE_CODES
    identity = model.identity()
    capture = capture_or_fail(model, request, timeout_s)
    check_capture_binds(capture, request, identity)
    assert capture.failure_code == code
    assert capture.body_json is None
    assert capture.warnings == expected_warnings
    outcome = normalize(capture, request.question, identity)
    assert outcome == ProviderFailure(code, expected_warnings, False)
    return capture


def check_body_preserved(
    model: DecisionModel,
    request: DecisionRequest,
    raw: str,
    expected_text: str,
    expected_warnings: tuple[str, ...],
) -> CapturedOutcome:
    """The raw body is captured whole: same JSON value, documented text form, no repair."""
    identity = model.identity()
    capture = capture_or_fail(model, request, 5.0)
    check_capture_binds(capture, request, identity)
    assert capture.failure_code is None
    assert capture.body_json is not None
    assert capture.body_json == expected_text
    assert strict_json_loads(capture.body_json) == strict_json_loads(raw)
    assert capture.warnings == expected_warnings
    return capture


def check_valid_body_normalizes(
    capture: CapturedOutcome, question: ChoiceQuestion, identity: ModelIdentity
) -> ChoiceAnswer:
    outcome = normalize(capture, question, identity)
    assert isinstance(outcome, ChoiceAnswer), outcome
    assert outcome.choice == question.labels[0]
    assert outcome.selected_probability == 0.5
    assert outcome.provider_confidence == 0.25  # optional native field survived capture
    assert outcome.fallback_used is False
    return outcome


def foreign_identities(identity: ModelIdentity) -> tuple[ModelIdentity, ...]:
    """Identities that differ from ``identity`` in exactly one field each."""
    other_provider = min(PROVIDERS - {identity.provider})
    return (
        dataclasses.replace(identity, provider=other_provider),
        dataclasses.replace(identity, model=identity.model + "-x"),
        dataclasses.replace(identity, revision="0" * 40),
        dataclasses.replace(identity, artifact_hashes=(("other", "f" * 64),)),
        dataclasses.replace(identity, adapter_version=identity.adapter_version + ".x"),
        dataclasses.replace(identity, normalizer_version=identity.normalizer_version + ".x"),
        dataclasses.replace(identity, runtime=(*identity.runtime, ("zz", "tampered"))),
    )


def check_identity_mismatch_precedes_body(
    capture: CapturedOutcome, question: ChoiceQuestion, identity: ModelIdentity
) -> None:
    """Against any foreign identity the outcome is ``identity_mismatch``, whatever the body."""
    for foreign in foreign_identities(identity):
        outcome = normalize(capture, question, foreign)
        assert isinstance(outcome, ProviderFailure), outcome
        assert outcome.code == "identity_mismatch"
        assert outcome.warnings == (*capture.warnings, "normalize.identity_mismatch")
        assert outcome.fallback_used is False


def check_close_lifecycle(
    model: DecisionModel,
    request: DecisionRequest,
    *,
    after_close: Lifecycle,
    timeout_s: float = 5.0,
    alive: Callable[[], bool | None] = lambda: None,
) -> CapturedOutcome:
    """``close`` is idempotent, keeps identity and leaves the documented post-close behaviour."""
    identity = model.identity()
    assert alive() is not False, "worker must be alive before close"
    model.close()
    assert alive() is not True, "close must leave no worker alive"
    model.close()
    assert model.identity() == identity
    capture = capture_or_fail(model, request, timeout_s)
    check_capture_binds(capture, request, identity)
    if after_close == "usable":
        assert capture.failure_code is None
        assert capture.body_json is not None
    else:
        assert capture.failure_code == "unavailable"
        assert capture.body_json is None
    assert alive() is not True
    model.close()
    assert model.identity() == identity
    return capture


def check_after_timeout(
    model: DecisionModel,
    request: DecisionRequest,
    *,
    after_timeout: Lifecycle,
    pid_before: int | None,
    alive: Callable[[], bool | None],
    pid_now: Callable[[], int | None],
) -> CapturedOutcome:
    """After a ``timeout`` capture the provider is still usable or permanently unavailable."""
    identity = model.identity()
    capture = capture_or_fail(model, request, 5.0)
    check_capture_binds(capture, request, identity)
    if after_timeout == "usable":
        assert capture.failure_code is None
        assert capture.body_json is not None
    else:
        assert capture.failure_code == "unavailable"
        assert capture.body_json is None
        assert alive() is False, "a timed-out worker must be terminated and joined"
        assert pid_now() == pid_before, "no silent restart after a timeout"
    assert model.identity() == identity
    return capture
