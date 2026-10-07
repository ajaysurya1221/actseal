"""Pure normalization: identity first, exact schema, bounded tolerance, selected-label gating."""

from __future__ import annotations

import json
import math
import subprocess
import sys
from dataclasses import replace
from typing import Any

import pytest

import actseal.normalization as normalization_module
from actseal.errors import SchemaError
from actseal.normalization import (
    _JEV_MASS_TOLERANCE,
    _JEV_MODEL,
    FIXTURE_MASS_TOLERANCE,
    LAYA_MASS_TOLERANCE_PER_OPTION,
    NORMALIZER_VERSION,
    laya_mass_tolerance,
    normalize,
    request_sha256,
)
from actseal.records import (
    CapturedOutcome,
    ChoiceAnswer,
    ChoiceQuestion,
    DecisionRequest,
    ModelIdentity,
    Option,
    ProviderFailure,
)
from actseal.serialization import canonical_json, from_data, sha256_bytes, to_data
from conftest import HEX_A, HEX_B, make_identity, make_question, make_request

# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #

GOOD_ANSWER: dict[str, Any] = {
    "type": "choice",
    "choice": "billing",
    "probabilities": {"billing": 0.95, "technical": 0.04, "sales": 0.01},
}

NATIVE_USAGE: dict[str, Any] = {
    "input_tokens": 59,
    "output_tokens": 0,
    "state_tokens": 15,
    "state_tokens_dropped": 0,
    "truncated": False,
    "truncated_questions": [],
}


def laya_identity() -> ModelIdentity:
    return ModelIdentity(
        "laya",
        "convaiinnovations/laya-typed-decisions",
        "e929ae5cf69bc34259cd2f95c9e91145b818b1f0",
        (("model.safetensors", HEX_B),),
        "1",
        "1",
        (("device", "cpu"), ("dtype", "float32")),
    )


def fixture_capture(
    body: object,
    *,
    identity: ModelIdentity | None = None,
    warnings: tuple[str, ...] = (),
    fallback_used: bool = False,
) -> CapturedOutcome:
    text = body if isinstance(body, str) else json.dumps(body)
    return CapturedOutcome(HEX_A, identity or make_identity(), text, None, warnings, fallback_used)


def failure_capture(code: str, *, warnings: tuple[str, ...] = ()) -> CapturedOutcome:
    return CapturedOutcome(HEX_A, make_identity(), None, code, warnings, False)


_DEFAULT_USAGE = object()


def envelope(
    answer: object,
    *,
    question_id: str = "department",
    usage: object = _DEFAULT_USAGE,
    model: object = "laya-rl-agent",
) -> dict[str, Any]:
    return {
        "model": model,
        "answers": {question_id: answer},
        "usage": dict(NATIVE_USAGE) if usage is _DEFAULT_USAGE else usage,
    }


def laya_capture(body: object, *, warnings: tuple[str, ...] = ()) -> CapturedOutcome:
    text = body if isinstance(body, str) else json.dumps(body)
    return CapturedOutcome(HEX_A, laya_identity(), text, None, warnings, False)


def answer_with(**changes: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "type": "choice",
        "choice": "billing",
        "probabilities": dict(GOOD_ANSWER["probabilities"]),
    }
    data.update(changes)
    return data


def expect_failure(outcome: object, code: str) -> ProviderFailure:
    assert isinstance(outcome, ProviderFailure), outcome
    assert outcome.code == code
    return outcome


def expect_answer(outcome: object) -> ChoiceAnswer:
    assert isinstance(outcome, ChoiceAnswer), outcome
    return outcome


# --------------------------------------------------------------------------- #
# Helpers and constants
# --------------------------------------------------------------------------- #


def test_normalizer_version_and_tolerances_are_frozen() -> None:
    assert NORMALIZER_VERSION == "1"
    assert FIXTURE_MASS_TOLERANCE == 1e-12
    assert LAYA_MASS_TOLERANCE_PER_OPTION == 0.00005
    assert laya_mass_tolerance(3) == 0.00005 * 3 + 1e-12
    assert laya_mass_tolerance(16) == 0.00005 * 16 + 1e-12


def test_request_sha256_is_canonical_request_hash() -> None:
    request = make_request()
    expected = sha256_bytes(canonical_json(to_data(request)))
    assert request_sha256(request) == expected
    other = DecisionRequest("v-002", request.state, request.question)
    assert request_sha256(other) != expected


def test_normalization_imports_no_provider_or_native_module() -> None:
    script = (
        "import sys\n"
        "import actseal.normalization\n"
        "loaded = sorted(name for name in sys.modules if name.split('.')[0] in "
        "('laya', 'torch', 'transformers', 'huggingface_hub', 'safetensors', 'numpy') "
        "or name.startswith('actseal.adapters'))\n"
        "print(loaded)\n"
    )
    result = subprocess.run(  # noqa: S603 - fixed interpreter and literal script, no user input
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    assert result.stdout.strip() == "[]"


# --------------------------------------------------------------------------- #
# Identity and transport failures
# --------------------------------------------------------------------------- #


def test_identity_mismatch_precedes_body_inspection() -> None:
    capture = fixture_capture("not json at all", identity=replace(make_identity(), revision=HEX_B))
    outcome = expect_failure(
        normalize(capture, make_question(), make_identity()), "identity_mismatch"
    )
    assert "normalize.identity_mismatch" in outcome.warnings


@pytest.mark.parametrize(
    "field",
    [
        "provider",
        "model",
        "revision",
        "artifact_hashes",
        "adapter_version",
        "normalizer_version",
        "runtime",
    ],
)
def test_any_identity_field_difference_is_a_mismatch(field: str) -> None:
    changes: dict[str, object] = {
        "provider": "laya",
        "model": "other",
        "revision": "other",
        "artifact_hashes": {"responses": HEX_B},
        "adapter_version": "2",
        "normalizer_version": "2",
        "runtime": {"python": "3.13"},
    }
    data = to_data(make_identity())
    data[field] = changes[field]
    observed = from_data(ModelIdentity, data)
    capture = fixture_capture(GOOD_ANSWER, identity=observed)
    expect_failure(normalize(capture, make_question(), make_identity()), "identity_mismatch")


def test_identity_mismatch_keeps_capture_warnings_and_fallback() -> None:
    capture = fixture_capture(
        GOOD_ANSWER,
        identity=replace(make_identity(), revision=HEX_B),
        warnings=("w.one",),
        fallback_used=True,
    )
    outcome = expect_failure(
        normalize(capture, make_question(), make_identity()), "identity_mismatch"
    )
    assert outcome.warnings[0] == "w.one"
    assert outcome.fallback_used is True


@pytest.mark.parametrize(
    "code",
    [
        "timeout",
        "rate_limit",
        "provider_error",
        "malformed_response",
        "identity_mismatch",
        "unknown_choice",
        "input_too_long",
        "unavailable",
    ],
)
def test_transport_failure_codes_pass_through(code: str) -> None:
    capture = failure_capture(code, warnings=("laya.load_warning:x",))
    outcome = expect_failure(normalize(capture, make_question(), make_identity()), code)
    assert outcome.warnings == ("laya.load_warning:x",)
    assert outcome.fallback_used is False


def test_fallback_flag_survives_a_successful_answer() -> None:
    capture = fixture_capture(GOOD_ANSWER, fallback_used=True)
    outcome = expect_answer(normalize(capture, make_question(), make_identity()))
    assert outcome.fallback_used is True


def test_fallback_flag_survives_a_failure() -> None:
    capture = CapturedOutcome(HEX_A, make_identity(), None, "timeout", (), True)
    outcome = expect_failure(normalize(capture, make_question(), make_identity()), "timeout")
    assert outcome.fallback_used is True


# --------------------------------------------------------------------------- #
# Fixture bodies: success paths
# --------------------------------------------------------------------------- #


def test_fixture_answer_is_ordered_by_question_and_gates_on_choice() -> None:
    body = {
        "type": "choice",
        "choice": "sales",
        "probabilities": {"technical": 0.3, "sales": 0.2, "billing": 0.5},
        "confidence": 0.42,
        "answer_confidence": 0.5,
        "action": {"act_probability": 1.0},
    }
    outcome = expect_answer(normalize(fixture_capture(body), make_question(), make_identity()))
    assert outcome.choice == "sales"
    assert outcome.probabilities == (("billing", 0.5), ("technical", 0.3), ("sales", 0.2))
    assert outcome.selected_probability == 0.2
    assert outcome.provider_confidence == 0.42
    assert outcome.warnings == ()
    assert outcome.fallback_used is False


def test_selected_label_is_not_replaced_by_argmax() -> None:
    body = answer_with(
        choice="sales", probabilities={"billing": 0.9, "technical": 0.1, "sales": 0.0}
    )
    outcome = expect_answer(normalize(fixture_capture(body), make_question(), make_identity()))
    assert outcome.choice == "sales"
    assert outcome.selected_probability == 0.0


def test_provider_confidence_disagreement_does_not_change_selected_probability() -> None:
    body = answer_with(confidence=0.99, answer_confidence=0.99)
    body["probabilities"] = {"billing": 0.2, "technical": 0.8, "sales": 0.0}
    outcome = expect_answer(normalize(fixture_capture(body), make_question(), make_identity()))
    assert outcome.selected_probability == 0.2
    assert outcome.provider_confidence == 0.99


def test_native_action_metadata_is_ignored() -> None:
    body = answer_with(action={"act_probability": 1.0, "act": True})
    outcome = expect_answer(normalize(fixture_capture(body), make_question(), make_identity()))
    assert outcome.choice == "billing"
    assert outcome.selected_probability == 0.95


def test_missing_confidence_yields_none() -> None:
    outcome = expect_answer(
        normalize(fixture_capture(GOOD_ANSWER), make_question(), make_identity())
    )
    assert outcome.provider_confidence is None


def test_integer_probabilities_are_accepted_as_numbers() -> None:
    body = answer_with(probabilities={"billing": 1, "technical": 0, "sales": 0})
    outcome = expect_answer(normalize(fixture_capture(body), make_question(), make_identity()))
    assert outcome.probabilities == (("billing", 1.0), ("technical", 0.0), ("sales", 0.0))
    assert outcome.selected_probability == 1.0


def test_capture_warnings_are_preserved_before_normalization_warnings() -> None:
    capture = fixture_capture(GOOD_ANSWER, warnings=("w.first", "w.second"))
    outcome = expect_answer(normalize(capture, make_question(), make_identity()))
    assert outcome.warnings == ("w.first", "w.second")


# --------------------------------------------------------------------------- #
# Fixture bodies: tolerance
# --------------------------------------------------------------------------- #


def test_fixture_sum_just_inside_tolerance_is_renormalized_with_warning() -> None:
    body = answer_with(probabilities={"billing": 0.5, "technical": 0.3, "sales": 0.2 + 0.9e-12})
    outcome = expect_answer(normalize(fixture_capture(body), make_question(), make_identity()))
    total = math.fsum(p for _, p in outcome.probabilities)
    assert abs(total - 1.0) <= 1e-12
    assert "normalize.renormalized" in outcome.warnings
    assert outcome.selected_probability == pytest.approx(0.5, abs=1e-12)


def test_fixture_sum_just_outside_tolerance_is_malformed() -> None:
    body = answer_with(probabilities={"billing": 0.5, "technical": 0.3, "sales": 0.2 + 1.1e-12})
    outcome = expect_failure(
        normalize(fixture_capture(body), make_question(), make_identity()), "malformed_response"
    )
    assert "normalize.probability_sum" in outcome.warnings


def test_fixture_does_not_get_the_laya_rounding_tolerance() -> None:
    body = answer_with(probabilities={"billing": 0.8085, "technical": 0.0877, "sales": 0.1039})
    expect_failure(
        normalize(fixture_capture(body), make_question(), make_identity()), "malformed_response"
    )


def test_exact_sum_does_not_warn() -> None:
    outcome = expect_answer(
        normalize(fixture_capture(GOOD_ANSWER), make_question(), make_identity())
    )
    assert "normalize.renormalized" not in outcome.warnings


# --------------------------------------------------------------------------- #
# Fixture bodies: rejections
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "text",
    ['{"type": "choice"', "", "null", "[]", '"choice"', "1", '{"a": 1, "a": 2}', "NaN"],
)
def test_non_object_or_invalid_json_body_is_malformed(text: str) -> None:
    outcome = expect_failure(
        normalize(fixture_capture(text), make_question(), make_identity()), "malformed_response"
    )
    assert outcome.warnings
    assert all(warning.startswith("normalize.") for warning in outcome.warnings)


@pytest.mark.parametrize("choice", ["refunds", "", "Billing", "billing "])
def test_unknown_choice_is_a_distinct_failure(choice: str) -> None:
    body = answer_with(choice=choice)
    outcome = expect_failure(
        normalize(fixture_capture(body), make_question(), make_identity()), "unknown_choice"
    )
    assert "normalize.unknown_choice" in outcome.warnings


def test_unknown_choice_is_reported_even_with_invented_probability_keys() -> None:
    body = answer_with(choice="refunds", probabilities={"refunds": 1.0, "billing": 0.0})
    expect_failure(
        normalize(fixture_capture(body), make_question(), make_identity()), "unknown_choice"
    )


@pytest.mark.parametrize(
    ("changes", "warning"),
    [
        ({"type": "score"}, "normalize.type"),
        ({"type": 1}, "normalize.type"),
        ({"choice": 1}, "normalize.choice_type"),
        ({"choice": None}, "normalize.choice_type"),
        ({"extra": 1}, "normalize.answer_keys"),
        ({"probabilities": [0.95, 0.04, 0.01]}, "normalize.probabilities_type"),
        ({"probabilities": {"billing": 0.95, "technical": 0.05}}, "normalize.probabilities_keys"),
        (
            {"probabilities": {"billing": 0.95, "technical": 0.04, "sales": 0.01, "other": 0.0}},
            "normalize.probabilities_keys",
        ),
        (
            {"probabilities": {"billing": True, "technical": 0.0, "sales": 0.0}},
            "normalize.probability_value",
        ),
        (
            {"probabilities": {"billing": "0.95", "technical": 0.04, "sales": 0.01}},
            "normalize.probability_value",
        ),
        (
            {"probabilities": {"billing": None, "technical": 0.04, "sales": 0.01}},
            "normalize.probability_value",
        ),
        (
            {"probabilities": {"billing": -0.01, "technical": 0.5, "sales": 0.51}},
            "normalize.probability_value",
        ),
        (
            {"probabilities": {"billing": 1.01, "technical": 0.0, "sales": 0.0}},
            "normalize.probability_value",
        ),
        (
            {"probabilities": {"billing": 0.0, "technical": 0.0, "sales": 0.0}},
            "normalize.probability_sum",
        ),
        (
            {"probabilities": {"billing": 0.5, "technical": 0.5, "sales": 0.5}},
            "normalize.probability_sum",
        ),
        ({"confidence": True}, "normalize.confidence"),
        ({"confidence": "high"}, "normalize.confidence"),
        ({"confidence": 1.5}, "normalize.confidence"),
        ({"confidence": -0.1}, "normalize.confidence"),
        ({"answer_confidence": False}, "normalize.answer_confidence"),
        ({"answer_confidence": 2}, "normalize.answer_confidence"),
        ({"action": "act"}, "normalize.action"),
        ({"action": None}, "normalize.action"),
    ],
)
def test_answer_schema_violations_are_malformed(changes: dict[str, Any], warning: str) -> None:
    body = answer_with(**changes)
    outcome = expect_failure(
        normalize(fixture_capture(body), make_question(), make_identity()), "malformed_response"
    )
    assert warning in outcome.warnings


@pytest.mark.parametrize("missing", ["type", "choice", "probabilities"])
def test_missing_required_answer_field_is_malformed(missing: str) -> None:
    body = answer_with()
    del body[missing]
    outcome = expect_failure(
        normalize(fixture_capture(body), make_question(), make_identity()), "malformed_response"
    )
    assert "normalize.answer_keys" in outcome.warnings


def test_nonfinite_probability_text_is_malformed() -> None:
    text = (
        '{"type":"choice","choice":"billing",'
        '"probabilities":{"billing":Infinity,"technical":0,"sales":0}}'
    )
    expect_failure(
        normalize(fixture_capture(text), make_question(), make_identity()), "malformed_response"
    )


def test_huge_probability_literal_is_malformed() -> None:
    text = (
        '{"type":"choice","choice":"billing",'
        '"probabilities":{"billing":1e400,"technical":0,"sales":0}}'
    )
    expect_failure(
        normalize(fixture_capture(text), make_question(), make_identity()), "malformed_response"
    )


def test_fixture_rejects_native_envelope_shape() -> None:
    capture = fixture_capture(envelope(GOOD_ANSWER))
    outcome = expect_failure(
        normalize(capture, make_question(), make_identity()), "malformed_response"
    )
    assert "normalize.answer_keys" in outcome.warnings


def test_failure_outcomes_do_not_echo_body_text() -> None:
    body = answer_with(choice="SECRET-TOKEN-VALUE")
    outcome = expect_failure(
        normalize(fixture_capture(body), make_question(), make_identity()), "unknown_choice"
    )
    assert all("SECRET" not in warning for warning in outcome.warnings)


# --------------------------------------------------------------------------- #
# Laya envelopes
# --------------------------------------------------------------------------- #


def test_laya_smoke_envelope_normalizes_with_rounding_tolerance() -> None:
    answer = {
        "type": "choice",
        "choice": "billing",
        "probabilities": {"billing": 0.8085, "technical": 0.0877, "sales": 0.1039},
        "confidence": 0.4352,
        "answer_confidence": 0.8085,
        "action": {"act_probability": 1.0},
    }
    outcome = expect_answer(
        normalize(laya_capture(envelope(answer)), make_question(), laya_identity())
    )
    assert outcome.choice == "billing"
    assert outcome.selected_probability == pytest.approx(0.8085 / 1.0001)
    assert math.fsum(p for _, p in outcome.probabilities) == pytest.approx(1.0, abs=1e-12)
    assert outcome.provider_confidence == 0.4352
    assert "normalize.renormalized" in outcome.warnings


def test_laya_tolerance_boundary_inside_and_outside() -> None:
    tolerance = laya_mass_tolerance(3)
    inside = answer_with(
        probabilities={"billing": 0.5, "technical": 0.3, "sales": 0.2 + tolerance * 0.99}
    )
    outside = answer_with(
        probabilities={"billing": 0.5, "technical": 0.3, "sales": 0.2 + tolerance * 1.01}
    )
    expect_answer(normalize(laya_capture(envelope(inside)), make_question(), laya_identity()))
    outcome = expect_failure(
        normalize(laya_capture(envelope(outside)), make_question(), laya_identity()),
        "malformed_response",
    )
    assert "normalize.probability_sum" in outcome.warnings


def test_laya_tolerance_scales_with_option_count() -> None:
    labels = [f"l{i}" for i in range(16)]
    question = ChoiceQuestion("q", "pick", tuple(Option(label, "d") for label in labels))
    base = dict.fromkeys(labels, 0.0625)
    base["l0"] = 0.0625 + 0.0007  # within 0.00005 * 16 = 0.0008, outside the 3-option bound
    answer = {"type": "choice", "choice": "l0", "probabilities": base}
    capture = laya_capture(envelope(answer, question_id="q"))
    expect_answer(normalize(capture, question, laya_identity()))


def test_laya_requires_generic_model_marker() -> None:
    capture = laya_capture(envelope(GOOD_ANSWER, model="laya-typed-decisions"))
    outcome = expect_failure(
        normalize(capture, make_question(), laya_identity()), "malformed_response"
    )
    assert "normalize.model_marker" in outcome.warnings


@pytest.mark.parametrize(
    ("body", "warning"),
    [
        (
            {"model": "laya-rl-agent", "answers": {"department": GOOD_ANSWER}},
            "normalize.envelope_keys",
        ),
        ({**envelope(GOOD_ANSWER), "extra": 1}, "normalize.envelope_keys"),
        ({**envelope(GOOD_ANSWER), "answers": []}, "normalize.answers"),
        ({**envelope(GOOD_ANSWER), "answers": {}}, "normalize.answers"),
        ({**envelope(GOOD_ANSWER), "answers": {"other": GOOD_ANSWER}}, "normalize.answers"),
        (
            {**envelope(GOOD_ANSWER), "answers": {"department": GOOD_ANSWER, "other": GOOD_ANSWER}},
            "normalize.answers",
        ),
        (GOOD_ANSWER, "normalize.envelope_keys"),
        ([], "normalize.body_type"),
    ],
)
def test_laya_envelope_violations_are_malformed(body: object, warning: str) -> None:
    outcome = expect_failure(
        normalize(laya_capture(body), make_question(), laya_identity()), "malformed_response"
    )
    assert warning in outcome.warnings


def test_laya_wrong_answer_id_rejected_before_inner_answer() -> None:
    capture = laya_capture(envelope(answer_with(choice="refunds"), question_id="dept"))
    expect_failure(normalize(capture, make_question(), laya_identity()), "malformed_response")


def _usage(**changes: Any) -> dict[str, Any]:
    usage = dict(NATIVE_USAGE)
    usage.update(changes)
    return usage


@pytest.mark.parametrize(
    "usage",
    [
        _usage(input_tokens=True),
        _usage(input_tokens=-1),
        _usage(input_tokens=1.0),
        _usage(input_tokens="59"),
        _usage(output_tokens=None),
        _usage(state_tokens=False),
        _usage(state_tokens_dropped=1.5),
        _usage(truncated="false"),
        _usage(truncated=0),
        _usage(truncated_questions="department"),
        _usage(truncated_questions=[1]),
        _usage(truncated_questions=None),
        _usage(extra=1),
        {k: v for k, v in NATIVE_USAGE.items() if k != "truncated"},
        {k: v for k, v in NATIVE_USAGE.items() if k != "truncated_questions"},
        {},
        [],
        None,
        _usage(options=[]),
        _usage(options={"department": {"total": 3, "distinct": 2}}),
        _usage(
            options={"department": {"total": 3, "distinct": 2, "tokens_per_option": None, "x": 1}}
        ),
        _usage(options={"department": {"total": True, "distinct": 2, "tokens_per_option": None}}),
        _usage(options={"department": {"total": -1, "distinct": 2, "tokens_per_option": None}}),
        _usage(options={"department": {"total": 3, "distinct": 2, "tokens_per_option": 1.5}}),
        _usage(options={"department": {"total": 3, "distinct": 2, "tokens_per_option": False}}),
        _usage(options={"department": "collapsed"}),
    ],
)
def test_malformed_usage_is_malformed_response(usage: object) -> None:
    capture = laya_capture(envelope(GOOD_ANSWER, usage=usage))
    outcome = expect_failure(
        normalize(capture, make_question(), laya_identity()), "malformed_response"
    )
    assert any(w.startswith("normalize.usage") for w in outcome.warnings)


@pytest.mark.parametrize(
    "usage",
    [
        _usage(state_tokens_dropped=1),
        _usage(truncated=True),
        _usage(truncated_questions=["department"]),
        _usage(options={"department": {"total": 3, "distinct": 2, "tokens_per_option": None}}),
        _usage(options={"department": {"total": 3, "distinct": 3, "tokens_per_option": 4}}),
        _usage(options={"other": {"total": 3, "distinct": 2, "tokens_per_option": 4}}),
    ],
)
def test_truncation_or_collapsed_options_is_input_too_long(usage: object) -> None:
    capture = laya_capture(envelope(GOOD_ANSWER, usage=usage))
    outcome = expect_failure(normalize(capture, make_question(), laya_identity()), "input_too_long")
    assert "normalize.usage.truncation" in outcome.warnings


def test_empty_options_mapping_is_accepted() -> None:
    capture = laya_capture(envelope(GOOD_ANSWER, usage=_usage(options={})))
    expect_answer(normalize(capture, make_question(), laya_identity()))


def test_truncation_is_checked_before_inner_answer_errors() -> None:
    capture = laya_capture(envelope(answer_with(choice="refunds"), usage=_usage(truncated=True)))
    expect_failure(normalize(capture, make_question(), laya_identity()), "input_too_long")


def test_laya_inner_answer_unknown_choice() -> None:
    capture = laya_capture(envelope(answer_with(choice="refunds")))
    expect_failure(normalize(capture, make_question(), laya_identity()), "unknown_choice")


def test_laya_inner_answer_schema_violation() -> None:
    capture = laya_capture(envelope(answer_with(probabilities={"billing": 1.0})))
    outcome = expect_failure(
        normalize(capture, make_question(), laya_identity()), "malformed_response"
    )
    assert "normalize.probabilities_keys" in outcome.warnings


def test_laya_identity_is_checked_before_envelope() -> None:
    capture = CapturedOutcome(HEX_A, make_identity(), "{", None, (), False)
    expect_failure(normalize(capture, make_question(), laya_identity()), "identity_mismatch")


def test_unsupported_expected_provider_is_a_schema_error() -> None:
    with pytest.raises(SchemaError):
        ModelIdentity("unsupported", "m", "r", (), "1", "1", ())


# --------------------------------------------------------------------------- #
# Jev envelopes (experimental profile, V1-011): frozen shape, model, tolerance
# --------------------------------------------------------------------------- #

JEV_MODEL = "jev-1.13.0"
JEV_USAGE: dict[str, Any] = {"input_tokens": 12, "output_tokens": 0}


def jev_identity() -> ModelIdentity:
    return ModelIdentity(
        "jev",
        JEV_MODEL,
        JEV_MODEL,
        (),
        "1",
        "1",
        (("endpoint", "https://api.typesafe.ai/v1/systemone"),),
    )


def jev_answer(**changes: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "type": "choice",
        "choice": "billing",
        "probabilities": dict(GOOD_ANSWER["probabilities"]),
        "confidence": 0.925,
    }
    data.update(changes)
    return data


def jev_envelope(
    answer: object,
    *,
    question_id: str = "department",
    usage: object = _DEFAULT_USAGE,
    model: object = JEV_MODEL,
) -> dict[str, Any]:
    return {
        "model": model,
        "answers": {question_id: answer},
        "usage": dict(JEV_USAGE) if usage is _DEFAULT_USAGE else usage,
    }


def jev_capture(body: object, *, warnings: tuple[str, ...] = ()) -> CapturedOutcome:
    text = body if isinstance(body, str) else json.dumps(body)
    return CapturedOutcome(HEX_A, jev_identity(), text, None, warnings, False)


def test_jev_profile_constants_are_frozen_and_private() -> None:
    assert _JEV_MODEL == JEV_MODEL
    assert _JEV_MASS_TOLERANCE == 1e-12 == FIXTURE_MASS_TOLERANCE
    # PROVISIONAL profile: not part of the stable manifest (docs/stability.md).
    assert "_JEV_MODEL" not in normalization_module.__all__
    assert not any(name.startswith("JEV") for name in normalization_module.__all__)


def test_jev_envelope_normalizes_and_keeps_vendor_confidence_diagnostic() -> None:
    answer = jev_answer(
        choice="sales",
        probabilities={"technical": 0.3, "sales": 0.2, "billing": 0.5},
        confidence=0.25,
    )
    outcome = expect_answer(
        normalize(jev_capture(jev_envelope(answer)), make_question(), jev_identity())
    )
    assert outcome.choice == "sales"
    assert outcome.probabilities == (("billing", 0.5), ("technical", 0.3), ("sales", 0.2))
    assert outcome.selected_probability == 0.2  # the selected label, not the argmax 0.5
    assert outcome.provider_confidence == 0.25
    assert outcome.warnings == ()
    assert outcome.fallback_used is False


def test_jev_selected_probability_gates_not_argmax_or_vendor_confidence() -> None:
    answer = jev_answer(
        choice="sales",
        probabilities={"billing": 0.9, "technical": 0.1, "sales": 0.0},
        confidence=0.99,
    )
    outcome = expect_answer(
        normalize(jev_capture(jev_envelope(answer)), make_question(), jev_identity())
    )
    assert outcome.choice == "sales"
    assert outcome.selected_probability == 0.0
    assert outcome.provider_confidence == 0.99


@pytest.mark.parametrize("model", ["jev-1.12.0", "jev-1.13.1", "jev", "laya-rl-agent", ""])
def test_jev_wrong_answering_model_is_identity_mismatch(model: str) -> None:
    capture = jev_capture(jev_envelope(jev_answer(), model=model))
    outcome = expect_failure(
        normalize(capture, make_question(), jev_identity()), "identity_mismatch"
    )
    assert outcome.warnings == ("normalize.answering_model",)


def test_jev_answering_model_is_checked_after_shape_and_before_the_answer() -> None:
    # Wrong model plus an unknown choice: the vendor version claim wins (no argmax, no repair).
    capture = jev_capture(jev_envelope(jev_answer(choice="refunds"), model="jev-1.12.0"))
    expect_failure(normalize(capture, make_question(), jev_identity()), "identity_mismatch")
    # Wrong model inside a malformed envelope: the shape is rejected first.
    capture = jev_capture({"model": "laya-rl-agent", "answers": {}, "usage": {}})
    outcome = expect_failure(
        normalize(capture, make_question(), jev_identity()), "malformed_response"
    )
    assert "normalize.answers" in outcome.warnings
    capture = jev_capture(jev_envelope(jev_answer(), model=1))
    outcome = expect_failure(
        normalize(capture, make_question(), jev_identity()), "malformed_response"
    )
    assert "normalize.model_type" in outcome.warnings


def _jev_usage(**changes: Any) -> dict[str, Any]:
    usage = dict(JEV_USAGE)
    usage.update(changes)
    return usage


@pytest.mark.parametrize(
    ("body", "warning"),
    [
        ([], "normalize.body_type"),
        (GOOD_ANSWER, "normalize.envelope_keys"),
        (jev_answer(), "normalize.envelope_keys"),
        ({"model": JEV_MODEL, "answers": {"department": jev_answer()}}, "normalize.envelope_keys"),
        ({**jev_envelope(jev_answer()), "metadata": {"api": "0.2.0"}}, "normalize.envelope_keys"),
        ({**jev_envelope(jev_answer()), "answers": []}, "normalize.answers"),
        ({**jev_envelope(jev_answer()), "answers": {}}, "normalize.answers"),
        (jev_envelope(jev_answer(), question_id="other"), "normalize.answers"),
        (
            {
                **jev_envelope(jev_answer()),
                "answers": {"department": jev_answer(), "other": jev_answer()},
            },
            "normalize.answers",
        ),
        (jev_envelope(jev_answer(), usage=None), "normalize.usage"),
        (jev_envelope(jev_answer(), usage=[]), "normalize.usage"),
        (jev_envelope(jev_answer(), usage={}), "normalize.usage.keys"),
        (jev_envelope(jev_answer(), usage={"input_tokens": 12}), "normalize.usage.keys"),
        (jev_envelope(jev_answer(), usage=_jev_usage(state_tokens=0)), "normalize.usage.keys"),
        (jev_envelope(jev_answer(), usage=_jev_usage(truncated=False)), "normalize.usage.keys"),
        (
            jev_envelope(jev_answer(), usage=_jev_usage(input_tokens=True)),
            "normalize.usage.input_tokens",
        ),
        (
            jev_envelope(jev_answer(), usage=_jev_usage(input_tokens=-1)),
            "normalize.usage.input_tokens",
        ),
        (
            jev_envelope(jev_answer(), usage=_jev_usage(input_tokens=1.0)),
            "normalize.usage.input_tokens",
        ),
        (
            jev_envelope(jev_answer(), usage=_jev_usage(output_tokens="0")),
            "normalize.usage.output_tokens",
        ),
        (
            jev_envelope(jev_answer(), usage=_jev_usage(output_tokens=None)),
            "normalize.usage.output_tokens",
        ),
        (jev_envelope(jev_answer(), usage=NATIVE_USAGE), "normalize.usage.keys"),
    ],
)
def test_jev_envelope_violations_are_malformed(body: object, warning: str) -> None:
    outcome = expect_failure(
        normalize(jev_capture(body), make_question(), jev_identity()), "malformed_response"
    )
    assert warning in outcome.warnings


@pytest.mark.parametrize(
    ("changes", "warning"),
    [
        ({"answer_confidence": 0.95}, "normalize.answer_keys"),
        ({"action": {"act_probability": 1.0}}, "normalize.answer_keys"),
        ({"extra": 1}, "normalize.answer_keys"),
        ({"type": "score"}, "normalize.type"),
        ({"choice": 1}, "normalize.choice_type"),
        ({"probabilities": {"billing": 0.95, "technical": 0.05}}, "normalize.probabilities_keys"),
        (
            {"probabilities": {"billing": True, "technical": 0.0, "sales": 0.0}},
            "normalize.probability_value",
        ),
        ({"confidence": True}, "normalize.confidence"),
        ({"confidence": 1.5}, "normalize.confidence"),
        ({"confidence": "high"}, "normalize.confidence"),
        ({"confidence": None}, "normalize.confidence"),
        (
            {"probabilities": {"billing": 0.8085, "technical": 0.0877, "sales": 0.1039}},
            "normalize.probability_sum",  # Laya's four-decimal tolerance is never applied to Jev
        ),
        (
            {"probabilities": {"billing": 0.5, "technical": 0.3, "sales": 0.2 + 1.1e-12}},
            "normalize.probability_sum",
        ),
    ],
)
def test_jev_answer_violations_are_malformed(changes: dict[str, Any], warning: str) -> None:
    capture = jev_capture(jev_envelope(jev_answer(**changes)))
    outcome = expect_failure(
        normalize(capture, make_question(), jev_identity()), "malformed_response"
    )
    assert warning in outcome.warnings


@pytest.mark.parametrize("missing", ["type", "choice", "probabilities", "confidence"])
def test_jev_answer_requires_every_profile_field(missing: str) -> None:
    answer = jev_answer()
    del answer[missing]
    outcome = expect_failure(
        normalize(jev_capture(jev_envelope(answer)), make_question(), jev_identity()),
        "malformed_response",
    )
    assert "normalize.answer_keys" in outcome.warnings


def test_jev_mass_tolerance_boundary_is_the_explicit_restriction() -> None:
    inside = jev_answer(probabilities={"billing": 0.5, "technical": 0.3, "sales": 0.2 + 0.9e-12})
    outcome = expect_answer(
        normalize(jev_capture(jev_envelope(inside)), make_question(), jev_identity())
    )
    assert "normalize.renormalized" in outcome.warnings
    assert math.fsum(p for _, p in outcome.probabilities) == pytest.approx(1.0, abs=1e-12)
    outside = jev_answer(probabilities={"billing": 0.5, "technical": 0.3, "sales": 0.2 + 1.1e-12})
    expect_failure(
        normalize(jev_capture(jev_envelope(outside)), make_question(), jev_identity()),
        "malformed_response",
    )


def test_jev_unknown_choice_is_a_distinct_failure() -> None:
    capture = jev_capture(jev_envelope(jev_answer(choice="refunds")))
    outcome = expect_failure(normalize(capture, make_question(), jev_identity()), "unknown_choice")
    assert "normalize.unknown_choice" in outcome.warnings


def test_jev_identity_is_checked_before_envelope() -> None:
    capture = CapturedOutcome(HEX_A, make_identity(), "{", None, (), False)
    expect_failure(normalize(capture, make_question(), jev_identity()), "identity_mismatch")
    foreign = replace(jev_identity(), runtime=(*jev_identity().runtime, ("zz", "x")))
    capture = CapturedOutcome(
        HEX_A, foreign, json.dumps(jev_envelope(jev_answer())), None, (), False
    )
    expect_failure(normalize(capture, make_question(), jev_identity()), "identity_mismatch")


def test_profiles_do_not_accept_each_other_s_envelopes() -> None:
    body = jev_envelope(jev_answer())
    outcome = expect_failure(
        normalize(fixture_capture(body), make_question(), make_identity()), "malformed_response"
    )
    assert "normalize.answer_keys" in outcome.warnings
    outcome = expect_failure(
        normalize(laya_capture(body), make_question(), laya_identity()), "malformed_response"
    )
    assert "normalize.model_marker" in outcome.warnings
    outcome = expect_failure(
        normalize(jev_capture(envelope(GOOD_ANSWER)), make_question(), jev_identity()),
        "malformed_response",
    )
    assert "normalize.usage.keys" in outcome.warnings


def test_jev_capture_warnings_precede_normalization_warnings() -> None:
    capture = jev_capture(jev_envelope(jev_answer(choice="refunds")), warnings=("w.first",))
    outcome = expect_failure(normalize(capture, make_question(), jev_identity()), "unknown_choice")
    assert outcome.warnings == ("w.first", "normalize.unknown_choice")


def test_normalization_imports_no_experimental_or_transport_module() -> None:
    script = (
        "import sys\n"
        "import actseal.normalization, actseal.faults\n"
        "loaded = sorted(name for name in sys.modules if name.startswith("
        "('actseal.experimental', 'actseal.adapters', 'http.client', 'ssl')))\n"
        "print(loaded)\n"
    )
    result = subprocess.run(  # noqa: S603 - fixed interpreter and literal script, no user input
        [sys.executable, "-I", "-c", script],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    assert result.stdout.strip() == "[]"


# --------------------------------------------------------------------------- #
# Purity and mutation protection
# --------------------------------------------------------------------------- #


def test_normalize_does_not_mutate_inputs_and_is_deterministic() -> None:
    capture = fixture_capture(GOOD_ANSWER, warnings=("w.one",))
    question = make_question()
    identity = make_identity()
    before = (to_data(capture), to_data(question), to_data(identity))
    first = normalize(capture, question, identity)
    second = normalize(capture, question, identity)
    assert first == second
    assert (to_data(capture), to_data(question), to_data(identity)) == before
    assert isinstance(first, ChoiceAnswer)
    assert isinstance(first.probabilities, tuple)
    assert isinstance(first.warnings, tuple)


def test_outcome_is_frozen() -> None:
    outcome = expect_answer(
        normalize(fixture_capture(GOOD_ANSWER), make_question(), make_identity())
    )
    with pytest.raises(AttributeError):
        outcome.choice = "sales"  # type: ignore[misc]
