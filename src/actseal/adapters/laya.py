"""Pinned native Laya adapter: one resident CPU model in a spawned worker process.

Importing this module never imports Laya, Torch or Transformers. The parent
process spawns ``python -c "...laya._worker_main()"``; only that child loads
the native stack, verifies the pinned checkpoint and answers requests over a
data-only JSON-lines channel on its stdin/stdout. The parent enforces the
120 s startup bound and a finite positive per-request deadline.

Lifecycle (ADR 0008/0009, docs/providers.md):

* Setup failure raises :class:`ProviderSetupError`; the child is terminated and
  joined first.
* A request timeout terminates (then kills) and joins the worker, returns
  ``timeout`` and makes every later call ``unavailable``. There is no restart.
* Unexpected worker exit, EOF, an oversized or unparseable message, or a reply
  whose sequence number does not match the pending request returns
  ``unavailable`` and invalidates the instance the same way. No late reply can
  satisfy another request.
* Only a healthy, synchronized worker may report ``provider_error`` (a caught
  inference exception, named by class only) or ``input_too_long`` (preflight).
* ``close`` is idempotent and leaves no child alive.

Preflight in the worker rejects state, instruction and option clipping before
any model forward using the upstream tokenizer and packing helpers at the
pinned ``max_len=1024`` / ``head_max_len=256``. Upstream calibration/runtime
warnings are captured and surfaced in every capture's warnings.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib
import json
import os
import platform
import select
import subprocess
import sys
import time
import warnings as warnings_module
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Final, Protocol, cast

from actseal.adapters.fixture import validate_timeout
from actseal.errors import ProviderSetupError, SchemaError
from actseal.normalization import NORMALIZER_VERSION, request_sha256
from actseal.records import (
    FAILURE_CODES,
    CapturedOutcome,
    ChoiceQuestion,
    DecisionRequest,
    ModelIdentity,
)
from actseal.serialization import canonical_json, from_data, strict_json_loads, to_data

__all__ = [
    "ADAPTER_VERSION",
    "ARTIFACT_HASHES",
    "HEAD_MAX_LEN",
    "MAX_LEN",
    "MODEL_ID",
    "OPTION_BUDGET",
    "OPTION_TOKEN_LIMIT",
    "REVISION",
    "STARTUP_TIMEOUT_S",
    "THREADS",
    "LayaModel",
]

ADAPTER_VERSION: Final = "1"
MODEL_ID: Final = "convaiinnovations/laya-typed-decisions"
REVISION: Final = "e929ae5cf69bc34259cd2f95c9e91145b818b1f0"
ARTIFACT_HASHES: Final[tuple[tuple[str, str], ...]] = (
    ("encoder/config.json", "5268d24ad3b77c8151de5dcb0762ba4391619aad9ab0bda33e36fb083cfeae6d"),
    ("model.safetensors", "4fa56de72383a9d3efa9cfa78955733c81b9fc8067a587ca4beb82c78107a24e"),
    ("rl_agent_config.json", "ebf0cd524d92342a6be5e48e9fca3d7c2babfb5a56ccd79d2171ef5d8c7f7be8"),
    (
        "tokenizer/tokenizer.json",
        "6c8aaa9a542084f2457eab775d4eeb51f92a70c0fd9de28d5edb0ddec3c08d30",
    ),
    (
        "tokenizer/tokenizer_config.json",
        "08d4cf3ac4dca381759441b85b91a6d40e688471dcd33d15d6649eb0a9a854d1",
    ),
)
MAX_LEN: Final = 1024
HEAD_MAX_LEN: Final = 256
OPTION_TOKEN_LIMIT: Final = 48
OPTION_BUDGET: Final = 240
STARTUP_TIMEOUT_S: Final = 120.0
THREADS: Final = 4

_CLOSE_GRACE_S: Final = 5.0
_MAX_MESSAGE_BYTES: Final = 1024 * 1024
_MAX_WARNING_CHARS: Final = 256
_READ_CHUNK: Final = 65536
_OFFLINE_ENV: Final = "ACTSEAL_LAYA_OFFLINE"
_WORKER_ENTRY: Final = "from actseal.adapters.laya import _worker_main; _worker_main()"
_NATIVE_PACKAGES: Final = (
    "laya",
    "torch",
    "transformers",
    "huggingface_hub",
    "safetensors",
    "numpy",
)


# --------------------------------------------------------------------------- #
# Shared helpers
# --------------------------------------------------------------------------- #


def _question_payload(question: ChoiceQuestion) -> dict[str, object]:
    """The native choice-question definition for ``question``."""
    return {
        "type": "choice",
        "instructions": question.instructions,
        "criteria": {option.label: option.description for option in question.options},
    }


def _bounded(text: str) -> str:
    return text[:_MAX_WARNING_CHARS]


def _warning_code(prefix: str, warning: warnings_module.WarningMessage) -> str:
    category = getattr(warning.category, "__name__", "Warning")
    return _bounded(f"{prefix}:{category}:{warning.message}")


def _native_worker_command() -> tuple[str, ...]:
    return (sys.executable, "-c", _WORKER_ENTRY)


# --------------------------------------------------------------------------- #
# Worker side: preflight and inference (pure over an injected packing seam)
# --------------------------------------------------------------------------- #


class _Packing(Protocol):
    """Tokenizer/packing operations the preflight needs; implemented over upstream helpers."""

    @property
    def mask_token(self) -> str: ...

    def check_question(self, question_id: str, question: Mapping[str, object]) -> None: ...

    def to_internal(self, question: Mapping[str, object]) -> dict[str, object]: ...

    def render_options(self, internal: Mapping[str, object]) -> list[str]: ...

    def count_tokens(self, text: str) -> int: ...

    def build_sequence(
        self, state: str, internal: Mapping[str, object]
    ) -> tuple[int, Mapping[str, object], Mapping[str, object]]: ...


_Predict = Callable[[str, dict[str, object]], object]


class _PreflightError(Exception):
    def __init__(self, failure: str, warning: str) -> None:
        super().__init__(warning)
        self.failure = failure
        self.warning = warning


def _too_long(check: str) -> _PreflightError:
    return _PreflightError("input_too_long", f"laya.preflight.{check}")


def _stat_int(stats: Mapping[str, object], key: str) -> int:
    value = stats.get(key)
    if type(value) is not int:
        raise _PreflightError("provider_error", "laya.preflight.stats")
    return value


def _preflight(
    packing: _Packing, state: str, question_id: str, question: Mapping[str, object]
) -> dict[str, object]:
    """Validate the exact token layout before inference; return the internal question."""
    try:
        packing.check_question(question_id, question)
        internal = packing.to_internal(question)
        options = packing.render_options(internal)
    except Exception:
        raise _PreflightError("provider_error", "laya.preflight.question_rejected") from None
    mask = packing.mask_token
    counts = [packing.count_tokens(" " + option.replace(mask, " ")) for option in options]
    if any(count > OPTION_TOKEN_LIMIT for count in counts):
        raise _too_long("option_tokens")
    option_total = sum(count + 1 for count in counts)
    if option_total > OPTION_BUDGET:
        raise _too_long("option_budget")
    instruction = f"{internal['t']} question: {str(internal['ins']).replace(mask, ' ')}"
    if packing.count_tokens(instruction) > HEAD_MAX_LEN - option_total:
        raise _too_long("instruction_tokens")
    markers, stats, state_stats = packing.build_sequence(state, internal)
    if markers != len(options):
        raise _too_long("markers")
    if (
        _stat_int(stats, "options_distinct") < _stat_int(stats, "options")
        or stats.get("tokens_per_option") is not None
    ):
        raise _too_long("collapsed_options")
    if (
        _stat_int(state_stats, "state_tokens_dropped") > 0
        or state_stats.get("truncated") is not False
    ):
        raise _too_long("state_tokens")
    return internal


def _infer(
    packing: _Packing,
    predict: _Predict,
    state: str,
    question_id: str,
    question: Mapping[str, object],
) -> dict[str, object]:
    """Preflight then infer; return a reply payload with either ``body`` or ``failure``."""
    recorded: list[str] = []
    try:
        _preflight(packing, state, question_id, question)
    except _PreflightError as rejected:
        return {"failure": rejected.failure, "warnings": [rejected.warning]}
    questions: dict[str, object] = {question_id: dict(question)}
    try:
        with warnings_module.catch_warnings(record=True) as caught:
            warnings_module.simplefilter("always")
            result = predict(state, questions)
        recorded.extend(_warning_code("laya.predict_warning", w) for w in caught)
    except Exception as exc:
        return {
            "failure": "provider_error",
            "warnings": [*recorded, _bounded(f"laya.exception:{type(exc).__name__}")],
        }
    if type(result) is not dict:
        return {"failure": "malformed_response", "warnings": ["laya.body_unserializable"]}
    try:
        canonical_json(result)
    except SchemaError:
        return {"failure": "malformed_response", "warnings": ["laya.body_unserializable"]}
    return {"body": result, "warnings": recorded}


# --------------------------------------------------------------------------- #
# Worker side: native loading (runs only inside the child process)
# --------------------------------------------------------------------------- #


class _NativePacking:
    """Upstream ``laya`` 0.3.28 helpers behind the preflight seam.

    ``agent`` is the loaded ``laya.Agent`` and ``common`` the ``laya.common``
    module; both are dynamic native objects, so they are held untyped.
    """

    def __init__(self, agent: object, common: object) -> None:
        self._agent: Any = cast(Any, agent)
        self._common: Any = cast(Any, common)
        self._tok: Any = self._agent.tok
        self.mask_token = str(self._tok.mask_token)

    def check_question(self, question_id: str, question: Mapping[str, object]) -> None:
        self._agent._check_question(question_id, dict(question))

    def to_internal(self, question: Mapping[str, object]) -> dict[str, object]:
        internal = self._agent._to_internal(dict(question))
        if type(internal) is not dict:
            raise TypeError("internal question must be a dict")
        return internal

    def render_options(self, internal: Mapping[str, object]) -> list[str]:
        rendered = self._common.render_options(dict(internal))
        return [str(option) for option in rendered]

    def count_tokens(self, text: str) -> int:
        encoded = self._common.encode_text(
            self._tok, text, add_special_tokens=False, truncation=False
        )
        return len(encoded["input_ids"])

    def build_sequence(
        self, state: str, internal: Mapping[str, object]
    ) -> tuple[int, Mapping[str, object], Mapping[str, object]]:
        _ids, markers, stats, state_stats = self._common.build_sequence(
            self._tok,
            state,
            dict(internal),
            max_len=MAX_LEN,
            head_max_len=HEAD_MAX_LEN,
            return_stats=True,
            return_truncation_stats=True,
        )
        return len(markers), dict(stats), dict(state_stats)


def _cached_artifact_hashes(hub: object) -> dict[str, str]:
    """Hash the pinned artifacts from the local Hugging Face cache, independently of Laya."""
    lookup: Any = getattr(hub, "try_to_load_from_cache", None)
    if lookup is None:
        raise ProviderSetupError("huggingface_hub cache lookup is unavailable")
    hashes: dict[str, str] = {}
    for name, _expected in ARTIFACT_HASHES:
        path = lookup(MODEL_ID, name, revision=REVISION)
        if not isinstance(path, str) or not Path(path).is_file():
            raise ProviderSetupError(f"laya artifact is not cached: {name}")
        digest = hashlib.sha256()
        with Path(path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        hashes[name] = digest.hexdigest()
    return hashes


def _load_native(
    *, offline: bool
) -> tuple[object, _NativePacking, _Predict, ModelIdentity, list[str]]:
    """Load the pinned checkpoint under the frozen runtime configuration."""
    if offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
    torch = importlib.import_module("torch")
    laya = importlib.import_module("laya")
    common = importlib.import_module("laya.common")
    hub = importlib.import_module("huggingface_hub")
    torch.set_num_threads(THREADS)
    with warnings_module.catch_warnings(record=True) as caught:
        warnings_module.simplefilter("always")
        agent = laya.load(
            MODEL_ID,
            revision=REVISION,
            expected_sha256=dict(ARTIFACT_HASHES),
            device="cpu",
            backend="eager",
            compile=False,
            fast=False,
        )
    load_warnings = [_warning_code("laya.load_warning", w) for w in caught]
    observed_revision = getattr(agent, "revision", None)
    if observed_revision != REVISION:
        raise ProviderSetupError("laya checkpoint revision does not match the pin")
    device = getattr(agent, "device", None)
    if getattr(device, "type", None) != "cpu":
        raise ProviderSetupError("laya device is not cpu")
    dtype = getattr(agent, "dtype", None)
    if dtype != torch.float32:
        raise ProviderSetupError("laya dtype is not float32")
    if torch.get_num_threads() != THREADS:
        raise ProviderSetupError("torch thread count is not the pinned value")
    if getattr(agent, "backend", None) != "eager":
        raise ProviderSetupError("laya backend is not eager")
    if getattr(agent, "_compiled", False) or getattr(agent, "_fast", None) is not None:
        raise ProviderSetupError("laya compile/fast path is active")
    hashes = _cached_artifact_hashes(hub)
    if hashes != dict(ARTIFACT_HASHES):
        raise ProviderSetupError("laya cached artifacts do not match the pinned hashes")
    versions = {name: str(importlib.import_module(name).__version__) for name in _NATIVE_PACKAGES}
    runtime = (
        *sorted(versions.items()),
        ("backend", "eager"),
        ("compile", "False"),
        ("device", str(device)),
        ("dtype", str(dtype)),
        ("fast", "False"),
        ("head_max_len", str(HEAD_MAX_LEN)),
        ("machine", platform.machine()),
        ("max_len", str(MAX_LEN)),
        ("python", platform.python_version()),
        ("system", platform.system()),
        ("threads", str(THREADS)),
    )
    identity = ModelIdentity(
        "laya",
        MODEL_ID,
        REVISION,
        ARTIFACT_HASHES,
        ADAPTER_VERSION,
        NORMALIZER_VERSION,
        runtime,
    )
    packing = _NativePacking(agent, common)

    def predict(state: str, questions: dict[str, object]) -> object:
        return agent.predict(state, questions, max_len=MAX_LEN, head_max_len=HEAD_MAX_LEN)

    return agent, packing, predict, identity, load_warnings


def _worker_main() -> None:
    """Entry point of the spawned worker: load once, then serve JSON-lines requests."""
    out = sys.stdout.buffer
    inp = sys.stdin.buffer
    sys.stdout = sys.stderr  # library prints must never corrupt the protocol channel

    def send(message: dict[str, object]) -> None:
        out.write(json.dumps(message, ensure_ascii=False).encode("utf-8") + b"\n")
        out.flush()

    try:
        _agent, packing, predict, identity, load_warnings = _load_native(
            offline=os.environ.get(_OFFLINE_ENV) == "1"
        )
    except BaseException as exc:
        send({"kind": "setup_error", "warnings": [_bounded(f"laya.setup:{type(exc).__name__}")]})
        return
    send({"kind": "ready", "identity": to_data(identity), "warnings": load_warnings})
    while True:
        line = inp.readline()
        if not line:
            return
        try:
            message = strict_json_loads(line.decode("utf-8"))
        except (UnicodeDecodeError, SchemaError):
            return
        if type(message) is not dict or message.get("kind") != "decide":
            return
        reply = _infer(
            packing,
            predict,
            str(message["state"]),
            str(message["question_id"]),
            dict(message["question"]),
        )
        send({"kind": "reply", "seq": message["seq"], **reply})


# --------------------------------------------------------------------------- #
# Parent side: worker process management
# --------------------------------------------------------------------------- #


class _ChannelError(Exception):
    """The worker channel is unusable: ``reason`` is ``timeout``, ``worker_exit`` or ``ipc``."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class _Worker:
    """A spawned worker with a deadline-bounded JSON-lines channel."""

    def __init__(
        self, command: Sequence[str], env: Mapping[str, str], close_grace_s: float
    ) -> None:
        self._grace = close_grace_s
        self._buffer = bytearray()
        self.process = subprocess.Popen(  # noqa: S603 - fixed interpreter and literal entry
            list(command),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=dict(env),
        )
        if self.process.stdout is None or self.process.stdin is None:
            self.stop(graceful=False)
            raise ProviderSetupError("laya worker pipes could not be created")
        self._in_fd = self.process.stdin.fileno()
        self._out_fd = self.process.stdout.fileno()
        os.set_blocking(self._in_fd, False)
        os.set_blocking(self._out_fd, False)

    @property
    def alive(self) -> bool:
        return self.process.poll() is None

    def exchange(self, message: Mapping[str, object], timeout_s: float) -> dict[str, object]:
        """Send one request and read its reply under a single deadline covering both."""
        deadline = time.monotonic() + timeout_s
        self.send_until(message, deadline)
        return self.receive_until(deadline)

    def send_until(self, message: Mapping[str, object], deadline: float) -> None:
        """Write one message with bounded partial writes; a nonreading worker times out."""
        if not self.alive:
            raise _ChannelError("worker_exit")
        payload = json.dumps(message, ensure_ascii=False).encode("utf-8") + b"\n"
        view = memoryview(payload)
        while view:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise _ChannelError("timeout")
            _, writable, _ = select.select([], [self._in_fd], [], remaining)
            if not writable:
                raise _ChannelError("timeout")
            try:
                written = os.write(self._in_fd, view)
            except BlockingIOError:
                continue
            except OSError:
                raise _ChannelError("worker_exit") from None
            view = view[written:]

    def receive_until(self, deadline: float) -> dict[str, object]:
        """Read one message before the deadline; raise ``_ChannelError`` otherwise."""
        while True:
            newline = self._buffer.find(b"\n")
            if newline >= 0:
                line = bytes(self._buffer[:newline])
                del self._buffer[: newline + 1]
                return self._decode(line)
            if len(self._buffer) > _MAX_MESSAGE_BYTES:
                raise _ChannelError("ipc")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise _ChannelError("timeout")
            ready, _, _ = select.select([self._out_fd], [], [], remaining)
            if not ready:
                raise _ChannelError("timeout")
            try:
                chunk = os.read(self._out_fd, _READ_CHUNK)
            except BlockingIOError:
                continue
            except OSError:
                raise _ChannelError("ipc") from None
            if not chunk:
                raise _ChannelError("worker_exit")
            self._buffer.extend(chunk)

    @staticmethod
    def _decode(line: bytes) -> dict[str, object]:
        """Bounded strict parse (size, depth, duplicate keys, nonfinite); anything else is ipc."""
        if len(line) > _MAX_MESSAGE_BYTES:
            raise _ChannelError("ipc")
        try:
            message = strict_json_loads(line.decode("utf-8"))
        except (UnicodeDecodeError, SchemaError, RecursionError, ValueError):
            raise _ChannelError("ipc") from None
        if type(message) is not dict:
            raise _ChannelError("ipc")
        return message

    def stop(self, *, graceful: bool) -> None:
        """Terminate (then kill) and join the child; close the pipes. Safe to repeat."""
        process = self.process
        if graceful and process.poll() is None:
            with contextlib.suppress(_ChannelError):
                self.send_until({"kind": "close"}, time.monotonic() + self._grace)
            with contextlib.suppress(subprocess.TimeoutExpired):
                process.wait(timeout=self._grace)
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=self._grace)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        for stream in (process.stdin, process.stdout):
            if stream is not None:
                with contextlib.suppress(OSError):
                    stream.close()


class LayaModel:
    """Pinned ``convaiinnovations/laya-typed-decisions`` on CPU in a spawned worker."""

    def __init__(self, *, offline: bool = False) -> None:
        self._configure(
            _native_worker_command(),
            offline=offline,
            startup_timeout_s=STARTUP_TIMEOUT_S,
            close_grace_s=_CLOSE_GRACE_S,
        )

    @classmethod
    def _spawn(
        cls,
        command: Sequence[str],
        *,
        offline: bool,
        startup_timeout_s: float,
        close_grace_s: float,
    ) -> LayaModel:
        """Construct around an arbitrary worker command (tests use a fake worker)."""
        model = cls.__new__(cls)
        model._configure(
            command,
            offline=offline,
            startup_timeout_s=startup_timeout_s,
            close_grace_s=close_grace_s,
        )
        return model

    def _configure(
        self,
        command: Sequence[str],
        *,
        offline: bool,
        startup_timeout_s: float,
        close_grace_s: float,
    ) -> None:
        self._child: subprocess.Popen[bytes] | None = None
        self._worker: _Worker | None = None
        self._unavailable: str | None = None
        self._sequence = 0
        env = dict(os.environ)
        if offline:
            env[_OFFLINE_ENV] = "1"
            env["HF_HUB_OFFLINE"] = "1"
            env["TRANSFORMERS_OFFLINE"] = "1"
        else:
            env.pop(_OFFLINE_ENV, None)
        try:
            worker = _Worker(command, env, close_grace_s)
        except OSError:
            raise ProviderSetupError("laya worker could not be spawned") from None
        self._worker = worker
        self._child = worker.process
        try:
            self._identity, self._load_warnings = self._await_ready(worker, startup_timeout_s)
        except BaseException:
            self.close()
            raise

    @staticmethod
    def _await_ready(
        worker: _Worker, startup_timeout_s: float
    ) -> tuple[ModelIdentity, tuple[str, ...]]:
        try:
            message = worker.receive_until(time.monotonic() + startup_timeout_s)
            warnings = _warning_list(message.get("warnings"))
        except _ChannelError as exc:
            raise ProviderSetupError(f"laya worker did not become ready: {exc.reason}") from None
        kind = message.get("kind")
        if kind == "setup_error":
            raise ProviderSetupError("laya worker setup failed: " + ", ".join(warnings))
        if kind != "ready":
            raise ProviderSetupError("laya worker sent an unexpected startup message")
        try:
            identity = from_data(ModelIdentity, message.get("identity"))
        except SchemaError:
            raise ProviderSetupError("laya worker reported an invalid identity") from None
        expected = (identity.provider, identity.model, identity.revision, identity.artifact_hashes)
        if expected != ("laya", MODEL_ID, REVISION, ARTIFACT_HASHES) or (
            identity.adapter_version,
            identity.normalizer_version,
        ) != (ADAPTER_VERSION, NORMALIZER_VERSION):
            raise ProviderSetupError("laya worker reported an identity outside the pinned model")
        return identity, warnings

    def identity(self) -> ModelIdentity:
        return self._identity

    def decide(self, request: DecisionRequest, *, timeout_s: float) -> CapturedOutcome:
        timeout = validate_timeout(timeout_s)
        if not isinstance(request, DecisionRequest):
            raise SchemaError("request: must be DecisionRequest")
        digest = request_sha256(request)
        if self._unavailable is not None or self._worker is None:
            reason = self._unavailable or "closed"
            return self._failure(digest, "unavailable", (f"laya.unavailable:{reason}",))
        self._sequence += 1
        sequence = self._sequence
        try:
            reply = self._worker.exchange(
                {
                    "kind": "decide",
                    "seq": sequence,
                    "state": request.state,
                    "question_id": request.question.question_id,
                    "question": _question_payload(request.question),
                },
                timeout,
            )
            return self._capture(digest, sequence, reply)
        except _ChannelError as exc:
            self._invalidate(exc.reason)
            if exc.reason == "timeout":
                return self._failure(digest, "timeout", ())
            return self._failure(digest, "unavailable", (f"laya.unavailable:{exc.reason}",))

    def _capture(self, digest: str, sequence: int, reply: Mapping[str, object]) -> CapturedOutcome:
        """Validate the reply for exactly the pending request; anything else is unusable IPC.

        The sequence must be a JSON integer: ``true`` or ``1.0`` compare equal
        to ``1`` in Python but are not the sequence that was sent.
        """
        seq = reply.get("seq")
        if reply.get("kind") != "reply" or type(seq) is not int or seq != sequence:
            raise _ChannelError("ipc")
        warnings = _warning_list(reply.get("warnings"))
        if "failure" in reply:
            failure = reply["failure"]
            if type(failure) is not str or failure not in FAILURE_CODES or "body" in reply:
                raise _ChannelError("ipc")
            return self._failure(digest, failure, warnings)
        body = reply.get("body")
        if type(body) is not dict:
            raise _ChannelError("ipc")
        try:
            body_json = canonical_json(body).decode("utf-8")
        except SchemaError:
            raise _ChannelError("ipc") from None
        return CapturedOutcome(
            digest,
            self._identity,
            body_json,
            None,
            (*self._load_warnings, *warnings),
            fallback_used=False,
        )

    def _failure(self, digest: str, code: str, warnings: tuple[str, ...]) -> CapturedOutcome:
        return CapturedOutcome(
            digest,
            self._identity,
            None,
            code,
            (*self._load_warnings, *warnings),
            fallback_used=False,
        )

    def _invalidate(self, reason: str) -> None:
        self._unavailable = reason
        if self._worker is not None:
            self._worker.stop(graceful=False)

    def close(self) -> None:
        worker = self._worker
        if worker is None:
            return
        worker.stop(graceful=self._unavailable is None)
        self._worker = None
        if self._unavailable is None:
            self._unavailable = "closed"


def _warning_list(value: object) -> tuple[str, ...]:
    if type(value) is not list:
        raise _ChannelError("ipc")
    items: list[str] = []
    for item in value:
        if type(item) is not str or not item:
            raise _ChannelError("ipc")
        items.append(_bounded(item))
    return tuple(items)
