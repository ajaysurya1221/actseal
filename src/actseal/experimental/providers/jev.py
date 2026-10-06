"""Experimental Jev cloud adapter (PROVISIONAL; plan/v1/PLAN.md section E, V1-011).

``JevModel`` implements :class:`actseal.adapters.base.DecisionModel` over the
vendor's HTTP API with the standard library only. Nothing here is part of the
1.x stability promise; the module may change in any release and is never
imported by the core, by replay or by the runner unless explicitly registered
(Task 19). Importing it performs no network, process or environment access.

Fixed execution profile (frozen before any live collection):

* ``POST https://api.typesafe.ai/v1/systemone`` with the pinned ``jev-1.13.0``
  target; neither endpoint nor model can be overridden by environment or
  argument. The outbound object is exactly ``{state, model, questions}`` where
  ``questions`` holds the locked question id mapped to ``{type: "choice",
  instructions, criteria}`` and ``criteria`` preserves the locked option order.
  It is serialized with ``json.dumps`` in insertion order: ``canonical_json``
  sorts keys and must never serialize this request. The canonical request hash
  recorded in captures (``request_sha256``) is unchanged. No case id, gold
  label or evaluation metadata is sent: byte-identical states produce
  byte-identical bodies while ``request_sha256`` still differs by case id.
* Credentials: the constructor reads only ``JEV_API_KEY`` from the process
  environment, validates that it is a nonempty printable ASCII token and keeps
  it solely inside the transport's ``Authorization`` header. The key never
  enters identity, captures, warnings, exceptions or diagnostics. ``offline=True``
  reads nothing, performs no request, and every ``decide`` returns
  ``unavailable``. A missing or malformed key raises
  :class:`ProviderSetupError` before any request.
* One attempt per ``decide``: no retry, no redirect following, no fallback.
  ``http.client.HTTPSConnection`` with the default TLS context and the caller's
  ``timeout_s`` as the per-operation socket timeout. That bounds connect and
  each read; it is not a hard wall-clock bound on the whole exchange.
* Frozen status mapping: ``429`` -> ``rate_limit``; ``529`` -> ``unavailable``;
  ``401``, ``422`` and every redirect -> ``provider_error``; other ``5xx`` ->
  ``unavailable``; any other non-200 status -> ``provider_error``. A socket
  timeout is ``timeout``; connection, TLS and protocol errors are
  ``unavailable``; any other exception is ``provider_error`` with a bounded
  class-name warning. Error response bodies are never retained.
* Successful bodies: at most ``MAX_RESPONSE_BYTES`` are read (actual bytes, not
  the declared ``Content-Length``); more is ``malformed_response``
  (``jev.body_oversized``), as is a body that is not valid UTF-8
  (``jev.body_not_utf8``). Otherwise the decoded text is captured verbatim,
  byte for byte, including invalid JSON, duplicate keys, a wrong answering
  model or out-of-profile fields; the pure normalizer classifies those
  (``actseal.normalization``, Jev profile) and replay repeats that
  classification without importing this module.
* Every connection is closed on every path. ``close`` is idempotent; after it
  every ``decide`` is ``unavailable`` and no request is made.

Identity: ``provider="jev"``, ``model`` and ``revision`` both ``jev-1.13.0``
(the configured vendor target that every response must report), an empty
``artifact_hashes`` tuple because no model-weight hash exists for a cloud
target, and a runtime describing the endpoint, execution profile, Python
version and transport. The returned version is a vendor claim, not a weight
attestation; identity is fixed at construction and never mutated by a
response.
"""

from __future__ import annotations

import contextlib
import http.client
import json
import os
import platform
import ssl
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Final, Protocol

from actseal.adapters.fixture import validate_timeout
from actseal.errors import ProviderSetupError, SchemaError
from actseal.normalization import _JEV_MODEL, NORMALIZER_VERSION, request_sha256
from actseal.records import CapturedOutcome, DecisionRequest, ModelIdentity

__all__ = [
    "ADAPTER_VERSION",
    "API_KEY_ENV",
    "ENDPOINT_HOST",
    "ENDPOINT_PATH",
    "EXECUTION_PROFILE",
    "MAX_RESPONSE_BYTES",
    "MODEL",
    "REVISION",
    "JevModel",
    "request_body",
]

ADAPTER_VERSION: Final = "1"
#: Pinned vendor target; the single source is the pure normalizer's Jev profile.
MODEL: Final = _JEV_MODEL
#: The version string every response must report (a vendor claim, not an artifact hash).
REVISION: Final = _JEV_MODEL
ENDPOINT_HOST: Final = "api.typesafe.ai"
ENDPOINT_PATH: Final = "/v1/systemone"
API_KEY_ENV: Final = "JEV_API_KEY"
EXECUTION_PROFILE: Final = "jev-cloud-single-attempt-v1"
#: Upper bound on the bytes read from a successful response body.
MAX_RESPONSE_BYTES: Final = 1024 * 1024

_MAX_KEY_CHARS: Final = 4096
_SUCCESS_STATUS: Final = 200
_SERVER_ERROR_RANGE: Final = range(500, 600)
#: Frozen explicit status mapping; see the module docstring for class fallbacks.
_STATUS_FAILURES: Final[Mapping[int, str]] = {
    401: "provider_error",
    422: "provider_error",
    429: "rate_limit",
    529: "unavailable",
}


# --------------------------------------------------------------------------- #
# Outbound request
# --------------------------------------------------------------------------- #


def request_body(request: DecisionRequest) -> bytes:
    """The exact HTTP body for ``request``: ``{state, model, questions}`` in that order.

    ``criteria`` keeps the locked option order; keys are never sorted. Only the
    state, the fixed model and the question definition are sent.
    """
    if not isinstance(request, DecisionRequest):
        raise SchemaError("request: must be DecisionRequest")
    question = request.question
    payload: dict[str, object] = {
        "state": request.state,
        "model": MODEL,
        "questions": {
            question.question_id: {
                "type": "choice",
                "instructions": question.instructions,
                "criteria": {option.label: option.description for option in question.options},
            }
        },
    }
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return text.encode("utf-8")


# --------------------------------------------------------------------------- #
# Transport seam
# --------------------------------------------------------------------------- #


class _Response(Protocol):
    """The part of ``http.client.HTTPResponse`` the exchange uses."""

    @property
    def status(self) -> int: ...

    def read(self, amt: int) -> bytes: ...


class _Connection(Protocol):
    """The part of ``http.client.HTTPSConnection`` the exchange uses."""

    def request(self, method: str, url: str, body: bytes, headers: Mapping[str, str]) -> None: ...

    def getresponse(self) -> _Response: ...

    def close(self) -> None: ...


_Connect = Callable[[float], _Connection]


@dataclass(frozen=True, slots=True)
class _Reply:
    """One attempt's data-only result: a verbatim body text or a frozen failure code."""

    body: str | None
    failure: str | None
    warnings: tuple[str, ...]


_Exchange = Callable[[bytes, float], _Reply]


def _default_connect(timeout: float) -> _Connection:
    """A fresh TLS connection to the fixed host with the default verifying context."""
    return http.client.HTTPSConnection(
        ENDPOINT_HOST, timeout=timeout, context=ssl.create_default_context()
    )


def _status_failure(status: int) -> tuple[str, tuple[str, ...]]:
    code = _STATUS_FAILURES.get(status)
    if code is None:
        code = "unavailable" if status in _SERVER_ERROR_RANGE else "provider_error"
    return code, (f"jev.http:{status}",)


class _HttpsExchange:
    """One POST per call over a fresh connection; maps every outcome to a ``_Reply``.

    The API key lives only in this object's header mapping.
    """

    def __init__(self, api_key: str, connect: _Connect) -> None:
        self._headers: Mapping[str, str] = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self._connect = connect

    def __call__(self, payload: bytes, timeout: float) -> _Reply:
        try:
            data = self._post(payload, timeout)
        except _StatusError as exc:
            code, warnings = _status_failure(exc.status)
            return _Reply(None, code, warnings)
        except TimeoutError:
            return _Reply(None, "timeout", ())
        except (OSError, http.client.HTTPException) as exc:
            return _Reply(None, "unavailable", (f"jev.transport:{type(exc).__name__}",))
        except Exception as exc:  # a failure is data, never an exception (CONTRACTS section 4)
            return _Reply(None, "provider_error", (f"jev.exception:{type(exc).__name__}",))
        return _decode_success(data)

    def _post(self, payload: bytes, timeout: float) -> bytes:
        """One request on a fresh connection; the connection is closed on every path."""
        connection = self._connect(timeout)
        try:
            connection.request("POST", ENDPOINT_PATH, payload, self._headers)
            response = connection.getresponse()
            if response.status != _SUCCESS_STATUS:
                raise _StatusError(response.status)
            return response.read(MAX_RESPONSE_BYTES + 1)
        finally:
            with contextlib.suppress(OSError):
                connection.close()


class _StatusError(Exception):
    """Internal control flow: a non-200 status; the error body is never read or kept."""

    def __init__(self, status: int) -> None:
        super().__init__(str(status))
        self.status = status


def _decode_success(data: bytes) -> _Reply:
    """Bound and decode a 200 body; the text is otherwise kept verbatim."""
    if len(data) > MAX_RESPONSE_BYTES:
        return _Reply(None, "malformed_response", ("jev.body_oversized",))
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return _Reply(None, "malformed_response", ("jev.body_not_utf8",))
    return _Reply(text, None, ())


# --------------------------------------------------------------------------- #
# Setup
# --------------------------------------------------------------------------- #


def _api_key_from_environment() -> str:
    """Read ``JEV_API_KEY`` and validate its shape; the value is never echoed."""
    value = os.environ.get(API_KEY_ENV)
    if value is None or not value:
        raise ProviderSetupError(f"{API_KEY_ENV}: environment variable is not set")
    if (
        len(value) > _MAX_KEY_CHARS
        or not value.isascii()
        or not value.isprintable()
        or any(character.isspace() for character in value)
    ):
        raise ProviderSetupError(f"{API_KEY_ENV}: must be a printable ASCII token without spaces")
    return value


def _runtime() -> tuple[tuple[str, str], ...]:
    return (
        ("endpoint", f"https://{ENDPOINT_HOST}{ENDPOINT_PATH}"),
        ("execution_profile", EXECUTION_PROFILE),
        ("python", platform.python_version()),
        ("transport", "stdlib-http.client-tls"),
        ("weights_attested", "false"),
    )


# --------------------------------------------------------------------------- #
# Adapter
# --------------------------------------------------------------------------- #


class JevModel:
    """Pinned ``jev-1.13.0`` over the fixed vendor endpoint; one attempt per request."""

    def __init__(self, *, offline: bool = False) -> None:
        exchange: _Exchange | None = None
        if not offline:
            exchange = _HttpsExchange(_api_key_from_environment(), _default_connect)
        self._configure(exchange, offline=offline)

    @classmethod
    def _with_exchange(cls, exchange: _Exchange | None, *, offline: bool = False) -> JevModel:
        """Test seam: a model over an injected exchange; reads no environment variable."""
        model = cls.__new__(cls)
        model._configure(exchange, offline=offline)
        return model

    def _configure(self, exchange: _Exchange | None, *, offline: bool) -> None:
        self._exchange: _Exchange | None = None if offline else exchange
        self._unavailable: str | None = "offline" if self._exchange is None else None
        self._closed = False
        self._attempts = 0
        self._identity = ModelIdentity(
            "jev",
            MODEL,
            REVISION,
            (),
            ADAPTER_VERSION,
            NORMALIZER_VERSION,
            _runtime(),
        )

    def identity(self) -> ModelIdentity:
        return self._identity

    def decide(self, request: DecisionRequest, *, timeout_s: float) -> CapturedOutcome:
        timeout = validate_timeout(timeout_s)
        if not isinstance(request, DecisionRequest):
            raise SchemaError("request: must be DecisionRequest")
        digest = request_sha256(request)
        exchange = self._exchange
        if self._unavailable is not None or exchange is None:
            reason = self._unavailable or "closed"
            return self._failure(digest, "unavailable", (f"jev.unavailable:{reason}",))
        payload = request_body(request)
        self._attempts += 1
        reply = exchange(payload, timeout)
        if reply.failure is not None:
            return self._failure(digest, reply.failure, reply.warnings)
        return CapturedOutcome(
            digest, self._identity, reply.body, None, reply.warnings, fallback_used=False
        )

    def _failure(self, digest: str, code: str, warnings: tuple[str, ...]) -> CapturedOutcome:
        return CapturedOutcome(digest, self._identity, None, code, warnings, fallback_used=False)

    def close(self) -> None:
        """Drop the transport; later calls are ``unavailable``. Safe to repeat."""
        self._exchange = None
        self._closed = True
        if self._unavailable is None:
            self._unavailable = "closed"
