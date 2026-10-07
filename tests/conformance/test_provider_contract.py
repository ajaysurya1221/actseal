"""Shared provider conformance: every provider profile passes exactly the same cases.

The ``profile`` fixture is parametrized over every name in ``PROFILE_NAMES``
(the recorded fixture adapter and the Laya adapter over its fake worker). No
case skips, xfails or branches a provider out of a check. Provider-specific
facts (whether ``close`` releases a worker, whether body text is verbatim or
canonical, what follows a timeout) are declared by the profile and asserted.
The checks themselves live in ``tests/provider_support.py`` and are the same
functions the negative doubles in ``test_provider_doubles.py`` must fail.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from actseal.adapters.base import DecisionModel
from actseal.errors import SchemaError
from actseal.normalization import normalize
from actseal.records import FAILURE_CODES, ChoiceQuestion, DecisionRequest, ProviderFailure
from actseal.serialization import to_data
from conftest import make_question
from provider_support import (
    PROFILE_NAMES,
    ProviderProfile,
    build_profile,
    capture_or_fail,
    check_after_timeout,
    check_body_preserved,
    check_capture_binds,
    check_close_lifecycle,
    check_identity_immutable,
    check_identity_mismatch_precedes_body,
    check_protocol_shape,
    check_request_binding,
    check_timeout_validation,
    check_typed_failure,
    check_valid_body_normalizes,
)

MALFORMED_BODIES: tuple[str, ...] = (
    "{}",
    '{"type": "choice"}',
    '{"answers": 1}',
    '{"model": "laya-rl-agent", "answers": {}, "usage": {}}',
    (
        '{"type": "choice", "choice": "billing", '
        '"probabilities": {"billing": true, "technical": 0, "sales": 0}}'
    ),
    (
        '{"type": "choice", "choice": "billing", '
        '"probabilities": {"billing": 0.5, "technical": 0.5, "sales": 0.5}}'
    ),
    (
        '{"type": "score", "choice": "billing", '
        '"probabilities": {"billing": 1.0, "technical": 0.0, "sales": 0.0}}'
    ),
)


@pytest.fixture(params=PROFILE_NAMES)
def profile(
    request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> ProviderProfile:
    built = build_profile(str(request.param), tmp_path, monkeypatch)
    assert built.name == request.param
    return built


@pytest.fixture
def question() -> ChoiceQuestion:
    return make_question()


@contextmanager
def opened(model: DecisionModel) -> Iterator[DecisionModel]:
    try:
        yield model
    finally:
        model.close()


def test_profiles_cover_fixture_and_laya() -> None:
    assert PROFILE_NAMES == ("fixture", "laya-fake")


def test_protocol_shape_and_identity_are_stable(
    profile: ProviderProfile, question: ChoiceQuestion
) -> None:
    with opened(profile.open(body=profile.valid_raw_body(question))) as model:
        check_protocol_shape(model)
        identity = check_identity_immutable(model)
        request = DecisionRequest("v-001", "s", question)
        capture = capture_or_fail(model, request, 5.0)
        check_capture_binds(capture, request, identity)
        assert model.identity() == identity
        assert capture.identity == identity
        assert capture == capture_or_fail(model, request, 5.0)  # deterministic replay of a capture


def test_request_hash_binds_case_state_instructions_and_ordered_options(
    profile: ProviderProfile, question: ChoiceQuestion
) -> None:
    body = profile.valid_raw_body(question)
    with opened(profile.open(body=body, case_ids=("v-001", "v-002"))) as model:
        check_request_binding(model, question)


def test_invalid_timeouts_raise_before_any_transport(
    profile: ProviderProfile, question: ChoiceQuestion
) -> None:
    request = DecisionRequest("v-001", "s", question)
    with opened(profile.open(body=profile.valid_raw_body(question))) as model:
        check_timeout_validation(model, request)
        assert profile.requests_sent(model) == 0
        assert profile.worker_alive(model) is not False
        healthy = capture_or_fail(model, request, 5.0)
        assert healthy.body_json is not None


def test_non_request_is_a_schema_error(profile: ProviderProfile, question: ChoiceQuestion) -> None:
    request = DecisionRequest("v-001", "s", question)
    with opened(profile.open(body=profile.valid_raw_body(question))) as model:
        for bad in (None, "v-001", to_data(request), question, (request,)):
            with pytest.raises(SchemaError, match="request"):
                model.decide(bad, timeout_s=5.0)  # type: ignore[arg-type]
        assert profile.requests_sent(model) == 0
        assert profile.worker_alive(model) is not False


@pytest.mark.parametrize("code", sorted(FAILURE_CODES))
def test_every_failure_code_is_a_typed_capture(
    profile: ProviderProfile, question: ChoiceQuestion, code: str
) -> None:
    request = DecisionRequest("v-001", "s", question)
    with opened(profile.open(failure=code, warnings=("w.detail",))) as model:
        identity = model.identity()
        capture = check_typed_failure(model, request, code, (*profile.load_warnings, "w.detail"))
        check_identity_mismatch_precedes_body(capture, question, identity)


def test_timeout_capture_and_documented_aftermath(
    profile: ProviderProfile, question: ChoiceQuestion
) -> None:
    model, timeout_s = profile.open_timing_out(question)
    with opened(model):
        pid_before = profile.worker_pid(model)
        timed_out = check_typed_failure(
            model,
            DecisionRequest("v-timeout", "s", question),
            "timeout",
            profile.load_warnings,
            timeout_s=timeout_s,
        )
        assert timed_out.body_json is None
        check_after_timeout(
            model,
            DecisionRequest("v-healthy", "s", question),
            after_timeout=profile.after_timeout,
            pid_before=pid_before,
            alive=lambda: profile.worker_alive(model),
            pid_now=lambda: profile.worker_pid(model),
        )


@pytest.mark.parametrize("raw", MALFORMED_BODIES)
def test_malformed_body_is_captured_then_rejected_by_normalization(
    profile: ProviderProfile, question: ChoiceQuestion, raw: str
) -> None:
    request = DecisionRequest("v-001", "s", question)
    with opened(profile.open(body=raw)) as model:
        identity = model.identity()
        capture = check_body_preserved(
            model, request, raw, profile.preserved(raw), profile.load_warnings
        )
        outcome = normalize(capture, question, identity)
        assert isinstance(outcome, ProviderFailure), outcome
        assert outcome.code == "malformed_response"
        assert outcome.warnings[: len(capture.warnings)] == capture.warnings
        assert outcome.warnings[-1].startswith("normalize.")
        check_identity_mismatch_precedes_body(capture, question, identity)


def test_raw_body_is_preserved_without_repair_and_normalizes(
    profile: ProviderProfile, question: ChoiceQuestion
) -> None:
    raw = profile.valid_raw_body(question)
    request = DecisionRequest("v-001", "s", question)
    with opened(profile.open(body=raw, warnings=("w.a", "w.b", "w.a"))) as model:
        identity = model.identity()
        expected_warnings = (*profile.load_warnings, "w.a", "w.b", "w.a")
        capture = check_body_preserved(
            model, request, raw, profile.preserved(raw), expected_warnings
        )
        assert capture.body_json is not None
        assert '"action"' in capture.body_json  # fields the normalizer ignores are still evidence
        assert '"answer_confidence"' in capture.body_json
        answer = check_valid_body_normalizes(capture, question, identity)
        assert answer.warnings == expected_warnings
        check_identity_mismatch_precedes_body(capture, question, identity)
        assert capture == capture_or_fail(model, request, 5.0)


def test_close_is_idempotent_and_identity_outlives_it(
    profile: ProviderProfile, question: ChoiceQuestion
) -> None:
    request = DecisionRequest("v-001", "s", question)
    with opened(profile.open(body=profile.valid_raw_body(question))) as model:
        before = capture_or_fail(model, request, 5.0)
        assert before.body_json is not None
        after = check_close_lifecycle(
            model,
            request,
            after_close=profile.after_close,
            alive=lambda: profile.worker_alive(model),
        )
        assert after.identity == before.identity
        assert after.request_sha256 == before.request_sha256
        if profile.after_close == "usable":
            assert after == before
        else:
            assert profile.worker_alive(model) is False
