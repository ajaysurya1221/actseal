"""Negative evidence: the shared checks catch misbehaving adapters.

Every double wraps an honest fixture model and violates exactly one rule of the
provider contract. The relevant shared check must fail with ``AssertionError``
on the double and pass on the honest model, so the checks are neither vacuous
nor satisfiable by an adapter-specific escape hatch.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import cast

import pytest

from actseal.adapters.base import DecisionModel
from actseal.adapters.fixture import validate_timeout
from actseal.errors import SchemaError
from actseal.normalization import request_sha256
from actseal.records import CapturedOutcome, ChoiceQuestion, DecisionRequest, ModelIdentity
from actseal.serialization import strict_json_loads
from conftest import make_question
from provider_support import (
    FixtureProfile,
    capture_or_fail,
    check_after_timeout,
    check_body_preserved,
    check_capture_binds,
    check_close_lifecycle,
    check_identity_immutable,
    check_protocol_shape,
    check_request_binding,
    check_timeout_validation,
    check_typed_failure,
)


class Delegating:
    """An honest pass-through; subclasses break one rule each."""

    def __init__(self, inner: DecisionModel) -> None:
        self._inner = inner

    def identity(self) -> ModelIdentity:
        return self._inner.identity()

    def decide(self, request: DecisionRequest, *, timeout_s: float) -> CapturedOutcome:
        return self._inner.decide(request, timeout_s=timeout_s)

    def close(self) -> None:
        self._inner.close()


class WrongHash(Delegating):
    def decide(self, request: DecisionRequest, *, timeout_s: float) -> CapturedOutcome:
        capture = super().decide(request, timeout_s=timeout_s)
        other = DecisionRequest(request.case_id + "-x", request.state, request.question)
        return dataclasses.replace(capture, request_sha256=request_sha256(other))


class ForeignCaptureIdentity(Delegating):
    def decide(self, request: DecisionRequest, *, timeout_s: float) -> CapturedOutcome:
        capture = super().decide(request, timeout_s=timeout_s)
        foreign = dataclasses.replace(capture.identity, revision="0" * 40)
        return dataclasses.replace(capture, identity=foreign)


class DriftingIdentity(Delegating):
    def __init__(self, inner: DecisionModel) -> None:
        super().__init__(inner)
        self._calls = 0

    def identity(self) -> ModelIdentity:
        self._calls += 1
        return dataclasses.replace(super().identity(), revision=f"{self._calls:064x}")


class RaisingOnDecide(Delegating):
    def decide(self, request: DecisionRequest, *, timeout_s: float) -> CapturedOutcome:
        del request, timeout_s
        raise RuntimeError("provider exploded")


class RepairingBody(Delegating):
    """Re-serializes the body and drops the optional fields the normalizer ignores."""

    def decide(self, request: DecisionRequest, *, timeout_s: float) -> CapturedOutcome:
        capture = super().decide(request, timeout_s=timeout_s)
        assert capture.body_json is not None
        body = strict_json_loads(capture.body_json)
        assert isinstance(body, dict)
        kept = {k: body[k] for k in ("type", "choice", "probabilities") if k in body}
        return dataclasses.replace(capture, body_json=json.dumps(kept))


class CanonicalizingBody(Delegating):
    """Same JSON value, different text: breaks a verbatim-text profile."""

    def decide(self, request: DecisionRequest, *, timeout_s: float) -> CapturedOutcome:
        capture = super().decide(request, timeout_s=timeout_s)
        assert capture.body_json is not None
        value = strict_json_loads(capture.body_json)
        return dataclasses.replace(
            capture, body_json=json.dumps(value, sort_keys=True, separators=(",", ":"))
        )


class LenientTimeout(Delegating):
    def decide(self, request: DecisionRequest, *, timeout_s: float) -> CapturedOutcome:
        try:
            validate_timeout(timeout_s)
        except SchemaError:
            timeout_s = 30.0
        return super().decide(request, timeout_s=timeout_s)


class FallbackCapture(Delegating):
    def decide(self, request: DecisionRequest, *, timeout_s: float) -> CapturedOutcome:
        return dataclasses.replace(super().decide(request, timeout_s=timeout_s), fallback_used=True)


class WrongFailureCode(Delegating):
    def decide(self, request: DecisionRequest, *, timeout_s: float) -> CapturedOutcome:
        capture = super().decide(request, timeout_s=timeout_s)
        return dataclasses.replace(capture, failure_code="unavailable")


class DroppedWarnings(Delegating):
    def decide(self, request: DecisionRequest, *, timeout_s: float) -> CapturedOutcome:
        return dataclasses.replace(super().decide(request, timeout_s=timeout_s), warnings=())


class CloseMutatesIdentity(Delegating):
    def __init__(self, inner: DecisionModel) -> None:
        super().__init__(inner)
        self._closed = False

    def identity(self) -> ModelIdentity:
        identity = super().identity()
        if self._closed:
            return dataclasses.replace(identity, adapter_version="2")
        return identity

    def close(self) -> None:
        self._closed = True
        super().close()


class DeadAfterClose(Delegating):
    """Returns ``unavailable`` after close: wrong for a profile that stays usable."""

    def __init__(self, inner: DecisionModel) -> None:
        super().__init__(inner)
        self._closed = False

    def decide(self, request: DecisionRequest, *, timeout_s: float) -> CapturedOutcome:
        capture = super().decide(request, timeout_s=timeout_s)
        if self._closed:
            return dataclasses.replace(capture, body_json=None, failure_code="unavailable")
        return capture

    def close(self) -> None:
        self._closed = True
        super().close()


class SecondCloseRaises(Delegating):
    def __init__(self, inner: DecisionModel) -> None:
        super().__init__(inner)
        self._closed = False

    def close(self) -> None:
        if self._closed:
            raise RuntimeError("already closed")
        self._closed = True
        super().close()


class PositionalTimeout:
    """Protocol-shaped by duck typing, but ``timeout_s`` is not keyword-only."""

    def __init__(self, inner: DecisionModel) -> None:
        self._inner = inner

    def identity(self) -> ModelIdentity:
        return self._inner.identity()

    def decide(self, request: DecisionRequest, timeout_s: float) -> CapturedOutcome:
        return self._inner.decide(request, timeout_s=timeout_s)

    def close(self) -> None:
        self._inner.close()


class NoClose:
    def __init__(self, inner: DecisionModel) -> None:
        self._inner = inner

    def identity(self) -> ModelIdentity:
        return self._inner.identity()

    def decide(self, request: DecisionRequest, *, timeout_s: float) -> CapturedOutcome:
        return self._inner.decide(request, timeout_s=timeout_s)


@pytest.fixture
def question() -> ChoiceQuestion:
    return make_question()


@pytest.fixture
def honest(tmp_path: Path, question: ChoiceQuestion) -> DecisionModel:
    profile = FixtureProfile(tmp_path)
    return profile.open(body=profile.valid_raw_body(question), case_ids=("v-001", "v-002"))


@pytest.fixture
def honest_failure(tmp_path: Path) -> DecisionModel:
    return FixtureProfile(tmp_path).open(failure="timeout", warnings=("w.slow",))


@pytest.fixture
def request_(question: ChoiceQuestion) -> DecisionRequest:
    return DecisionRequest("v-001", "s", question)


def test_shared_checks_pass_on_the_honest_fixture(
    honest: DecisionModel, honest_failure: DecisionModel, request_: DecisionRequest
) -> None:
    check_protocol_shape(honest)
    identity = check_identity_immutable(honest)
    check_request_binding(honest, request_.question)
    check_timeout_validation(honest, request_)
    check_capture_binds(capture_or_fail(honest, request_, 5.0), request_, identity)
    check_typed_failure(honest_failure, request_, "timeout", ("w.slow",))
    check_close_lifecycle(honest, request_, after_close="usable")


def test_wrong_request_hash_is_caught(honest: DecisionModel, request_: DecisionRequest) -> None:
    double = WrongHash(honest)
    with pytest.raises(AssertionError):
        check_capture_binds(capture_or_fail(double, request_, 5.0), request_, double.identity())
    with pytest.raises(AssertionError):
        check_request_binding(double, request_.question)


def test_foreign_capture_identity_is_caught(
    honest: DecisionModel, request_: DecisionRequest
) -> None:
    double = ForeignCaptureIdentity(honest)
    with pytest.raises(AssertionError):
        check_capture_binds(capture_or_fail(double, request_, 5.0), request_, double.identity())


def test_drifting_identity_is_caught(honest: DecisionModel) -> None:
    with pytest.raises(AssertionError):
        check_identity_immutable(DriftingIdentity(honest))


def test_raising_decide_is_caught(honest: DecisionModel, request_: DecisionRequest) -> None:
    with pytest.raises(AssertionError, match="raised RuntimeError"):
        capture_or_fail(RaisingOnDecide(honest), request_, 5.0)


def test_repaired_body_is_caught(
    tmp_path: Path, honest: DecisionModel, request_: DecisionRequest
) -> None:
    raw = FixtureProfile(tmp_path).valid_raw_body(request_.question)
    double = RepairingBody(honest)
    with pytest.raises(AssertionError):
        check_body_preserved(double, request_, raw, raw, ())


def test_canonicalized_text_is_caught_for_a_verbatim_profile(
    tmp_path: Path, honest: DecisionModel, request_: DecisionRequest
) -> None:
    raw = FixtureProfile(tmp_path).valid_raw_body(request_.question)
    double = CanonicalizingBody(honest)
    capture = capture_or_fail(double, request_, 5.0)
    assert capture.body_json is not None
    assert strict_json_loads(capture.body_json) == strict_json_loads(raw)  # value survives...
    with pytest.raises(AssertionError):
        check_body_preserved(double, request_, raw, raw, ())  # ...but the documented text does not


def test_lenient_timeout_is_caught(honest: DecisionModel, request_: DecisionRequest) -> None:
    with pytest.raises(AssertionError):
        check_timeout_validation(LenientTimeout(honest), request_)


def test_fallback_flag_is_caught(honest: DecisionModel, request_: DecisionRequest) -> None:
    double = FallbackCapture(honest)
    with pytest.raises(AssertionError):
        check_capture_binds(capture_or_fail(double, request_, 5.0), request_, double.identity())


def test_wrong_failure_code_is_caught(
    honest_failure: DecisionModel, request_: DecisionRequest
) -> None:
    with pytest.raises(AssertionError):
        check_typed_failure(WrongFailureCode(honest_failure), request_, "timeout", ("w.slow",))


def test_dropped_warnings_are_caught(
    honest_failure: DecisionModel, request_: DecisionRequest
) -> None:
    with pytest.raises(AssertionError):
        check_typed_failure(DroppedWarnings(honest_failure), request_, "timeout", ("w.slow",))


def test_identity_change_on_close_is_caught(
    honest: DecisionModel, request_: DecisionRequest
) -> None:
    with pytest.raises(AssertionError):
        check_close_lifecycle(CloseMutatesIdentity(honest), request_, after_close="usable")


def test_post_close_behaviour_must_match_the_declared_profile(
    honest: DecisionModel, request_: DecisionRequest
) -> None:
    with pytest.raises(AssertionError):
        check_close_lifecycle(DeadAfterClose(honest), request_, after_close="usable")
    with pytest.raises(AssertionError):
        check_close_lifecycle(honest, request_, after_close="unavailable")


def test_live_worker_after_close_is_caught(
    honest: DecisionModel, request_: DecisionRequest
) -> None:
    with pytest.raises(AssertionError, match="no worker alive"):
        check_close_lifecycle(honest, request_, after_close="usable", alive=lambda: True)


def test_non_idempotent_close_is_caught(honest: DecisionModel, request_: DecisionRequest) -> None:
    with pytest.raises(RuntimeError, match="already closed"):
        check_close_lifecycle(SecondCloseRaises(honest), request_, after_close="usable")


def test_restart_after_timeout_is_caught(honest: DecisionModel, request_: DecisionRequest) -> None:
    # An honest fixture keeps answering: wrong for a profile whose worker must die.
    with pytest.raises(AssertionError):
        check_after_timeout(
            honest,
            request_,
            after_timeout="unavailable",
            pid_before=1,
            alive=lambda: False,
            pid_now=lambda: 1,
        )
    dead = DeadAfterClose(honest)
    dead.close()
    # Reports unavailable, but the worker is still alive: caught.
    with pytest.raises(AssertionError, match="terminated"):
        check_after_timeout(
            dead,
            request_,
            after_timeout="unavailable",
            pid_before=1,
            alive=lambda: True,
            pid_now=lambda: 1,
        )
    # Reports unavailable with a dead worker, but under a new pid: a silent restart, caught.
    with pytest.raises(AssertionError, match="restart"):
        check_after_timeout(
            dead,
            request_,
            after_timeout="unavailable",
            pid_before=1,
            alive=lambda: False,
            pid_now=lambda: 2,
        )


def test_protocol_shape_rejects_positional_timeout_and_missing_close(
    honest: DecisionModel,
) -> None:
    with pytest.raises(AssertionError):
        check_protocol_shape(PositionalTimeout(honest))
    with pytest.raises(AssertionError):
        check_protocol_shape(cast(DecisionModel, NoClose(honest)))
