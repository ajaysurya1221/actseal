"""Offline recorded-provider contract and configurable envelope normalization."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

import actseal.adapters.recorded as recorded_module
from actseal.adapters.recorded import RecordedModel
from actseal.errors import ProviderSetupError, SchemaError
from actseal.normalization import RECORDING_WARNING, normalize, request_sha256
from actseal.records import CapturedOutcome, ChoiceAnswer, ModelIdentity, ProviderFailure
from actseal.serialization import from_data, sha256_bytes, to_data
from conftest import HEX_A, make_identity, make_question, make_request


def recorded_identity() -> ModelIdentity:
    return replace(make_identity(), provider="recorded", model="my-model", revision="r1")


def recorded_outcome(body: object) -> ChoiceAnswer | ProviderFailure:
    identity = recorded_identity()
    capture = CapturedOutcome(HEX_A, identity, json.dumps(body), None, (), False)
    return normalize(capture, make_question(), identity)


def test_score_only_answer_round_trips_without_fabricated_probabilities() -> None:
    answer = recorded_outcome({"type": "choice", "choice": "billing", "score": 0.8})
    assert isinstance(answer, ChoiceAnswer)
    assert answer.probabilities == ()
    assert answer.selected_probability == 0.8
    assert from_data(ChoiceAnswer, to_data(answer)) == answer


def test_recorded_mass_tolerance_never_changes_score_or_probabilities() -> None:
    probabilities = {"billing": 0.8, "technical": 0.1, "sales": 0.1000000000001}
    answer = recorded_outcome(
        {"type": "choice", "choice": "billing", "score": 0.8, "probabilities": probabilities}
    )
    assert isinstance(answer, ChoiceAnswer)
    assert answer.selected_probability.hex() == (0.8).hex()
    assert dict(answer.probabilities) == probabilities
    assert "normalize.renormalized" not in answer.warnings


@pytest.mark.parametrize(
    "score", [None, True, "0.8", [], {}, -0.1, 1.1, float("nan"), float("inf")]
)
def test_invalid_score_fails(score: object) -> None:
    result = recorded_outcome({"type": "choice", "choice": "billing", "score": score})
    assert isinstance(result, ProviderFailure)
    assert result.code == "malformed_response"


@pytest.mark.parametrize(
    "body",
    [
        {"type": "choice", "choice": "billing"},
        {"type": "choice", "choice": "billing", "score": 0.8, "confidence": 0.9},
        {"type": "other", "choice": "billing", "score": 0.8},
        {"type": "choice", "choice": True, "score": 0.8},
    ],
)
def test_invalid_answer_shape_fails(body: object) -> None:
    assert isinstance(recorded_outcome(body), ProviderFailure)


@pytest.mark.parametrize(
    "probabilities",
    [
        {},
        {"billing": 1},
        {"billing": 0.8, "technical": 0.2},
        {"billing": 0.8, "technical": 0.1, "sales": 0.1, "extra": 0},
        {"billing": 0.8, "technical": True, "sales": 0.1},
        {"billing": 0.8, "technical": 0.1, "sales": -0.1},
        {"billing": 0.8, "technical": 0.1, "sales": 0.2},
        {"billing": 0.9, "technical": 0.05, "sales": 0.05},
        None,
        [],
    ],
)
def test_bad_probability_map_fails(probabilities: object) -> None:
    result = recorded_outcome(
        {"type": "choice", "choice": "billing", "score": 0.8, "probabilities": probabilities}
    )
    assert isinstance(result, ProviderFailure)
    assert result.code == "malformed_response"


def test_unknown_choice_keeps_existing_denial_path() -> None:
    result = recorded_outcome({"type": "choice", "choice": "unknown", "score": 0.8})
    assert isinstance(result, ProviderFailure)
    assert result.code == "unknown_choice"


def test_one_probability_still_rejected() -> None:
    with pytest.raises(SchemaError, match="probabilities"):
        ChoiceAnswer("billing", (("billing", 1.0),), 1.0, None, (), False)


def test_adapter_preserves_answer_values_and_binds_file_bytes(tmp_path: Path) -> None:
    path = tmp_path / "predictions.jsonl"
    raw = b'{"case_id":"v-001","choice":"billing","score":-0.0}\n'
    path.write_bytes(raw)
    model = RecordedModel(path, model="supplied-model", revision="supplied-revision")
    identity = model.identity()
    assert identity.provider == "recorded"
    assert identity.model == "supplied-model"
    assert identity.revision == "supplied-revision"
    assert identity.artifact_hashes == (("responses", sha256_bytes(raw)),)
    capture = model.decide(make_request(), timeout_s=1.0)
    assert capture.request_sha256 == request_sha256(make_request())
    assert capture.warnings == (RECORDING_WARNING,)
    assert not capture.fallback_used
    assert capture.body_json is not None
    assert json.loads(capture.body_json)["score"].hex() == (-0.0).hex()
    assert json.loads(capture.body_json) == {"type": "choice", "choice": "billing", "score": -0.0}
    assert model.decide(make_request(), timeout_s=1.0) == capture
    model.close()


def test_failure_capture_also_carries_warning(tmp_path: Path) -> None:
    path = tmp_path / "predictions.jsonl"
    path.write_text('{"case_id":"v-001","failure_code":"timeout"}\n')
    model = RecordedModel(path, model="m", revision="r")
    capture = model.decide(make_request(), timeout_s=1.0)
    assert capture.failure_code == "timeout"
    assert capture.body_json is None
    assert capture.warnings == (RECORDING_WARNING,)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "\n",
        "[]\n",
        '{"case_id":"v-001","choice":"billing","score":0.8,"unknown":1}\n',
        '{"case_id":"v-001","choice":"billing"}\n',
        '{"case_id":"v-001","failure_code":"invalid"}\n',
        '{"case_id":"v-001","failure_code":"timeout","score":0.8}\n',
        '{"case_id":"","choice":"billing","score":0.8}\n',
        '{"case_id":"v-001","choice":"billing","score":0.8,"score":0.9}\n',
        '{"case_id":"v-001","failure_code":"timeout"}\n' * 2,
    ],
)
def test_invalid_recorded_rows_fail_explicitly(tmp_path: Path, text: str) -> None:
    path = tmp_path / "predictions.jsonl"
    path.write_text(text)
    with pytest.raises(SchemaError):
        RecordedModel(path, model="m", revision="r")


def test_missing_case_is_not_skipped(tmp_path: Path) -> None:
    path = tmp_path / "predictions.jsonl"
    path.write_text('{"case_id":"other","choice":"billing","score":0.8}\n')
    model = RecordedModel(path, model="m", revision="r")
    with pytest.raises(ProviderSetupError, match="case id"):
        model.decide(make_request(), timeout_s=1.0)


def test_invalid_answer_values_are_captured_and_fail_normalization(tmp_path: Path) -> None:
    path = tmp_path / "predictions.jsonl"
    path.write_text('{"case_id":"v-001","choice":"billing","score":true}\n')
    model = RecordedModel(path, model="m", revision="r")
    capture = model.decide(make_request(), timeout_s=1.0)
    result = normalize(capture, make_question(), model.identity())
    assert isinstance(result, ProviderFailure)
    assert result.code == "malformed_response"
    assert result.warnings[0] == RECORDING_WARNING


def test_recorded_bounds_and_utf8_fail_before_collection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "predictions.jsonl"
    path.write_bytes(b"\xff")
    with pytest.raises(SchemaError, match="UTF-8"):
        RecordedModel(path, model="m", revision="r")
    path.write_text('{"case_id":"v-001","choice":"billing","score":0.8}\n')
    monkeypatch.setattr(recorded_module, "MAX_RECORDED_BYTES", 8)
    with pytest.raises(SchemaError, match="file exceeds"):
        RecordedModel(path, model="m", revision="r")
    monkeypatch.setattr(recorded_module, "MAX_RECORDED_BYTES", 1024)
    monkeypatch.setattr(recorded_module, "MAX_ROW_BYTES", 8)
    with pytest.raises(SchemaError, match="row exceeds"):
        RecordedModel(path, model="m", revision="r")


def test_recorded_missing_file_is_explicit(tmp_path: Path) -> None:
    with pytest.raises(ProviderSetupError, match="could not be read"):
        RecordedModel(tmp_path / "missing.jsonl", model="m", revision="r")


@pytest.mark.parametrize("field", ["model", "revision"])
def test_recorded_requires_supplied_nonempty_identity(tmp_path: Path, field: str) -> None:
    path = tmp_path / "predictions.jsonl"
    path.write_text('{"case_id":"v-001","choice":"billing","score":0.8}\n')
    with pytest.raises(SchemaError, match=field):
        RecordedModel(
            path, model="" if field == "model" else "m", revision="" if field == "revision" else "r"
        )


@pytest.mark.parametrize("timeout", [0.0, -1.0, float("nan"), float("inf")])
def test_recorded_rejects_invalid_timeout(tmp_path: Path, timeout: float) -> None:
    path = tmp_path / "predictions.jsonl"
    path.write_text('{"case_id":"v-001","choice":"billing","score":0.8}\n')
    model = RecordedModel(path, model="m", revision="r")
    with pytest.raises(SchemaError, match="timeout_s"):
        model.decide(make_request(), timeout_s=timeout)


@pytest.mark.parametrize("provider", ["jev", "decision-api"])
@pytest.mark.parametrize("response_model", ["my-model", "jev-1.13.0", "other"])
def test_decision_api_uses_locked_model_while_jev_retains_pin(
    provider: str, response_model: str
) -> None:
    identity = replace(make_identity(), provider=provider, model="my-model")
    body = {
        "model": response_model,
        "answers": {
            "department": {
                "type": "choice",
                "choice": "billing",
                "probabilities": {"billing": 0.8, "technical": 0.1, "sales": 0.1},
                "confidence": 0.7,
            }
        },
        "usage": {"input_tokens": 1, "output_tokens": 1},
    }
    capture = CapturedOutcome(HEX_A, identity, json.dumps(body), None, (), False)
    result = normalize(capture, make_question(), identity)
    expected_model = "my-model" if provider == "decision-api" else "jev-1.13.0"
    if response_model == expected_model:
        assert isinstance(result, ChoiceAnswer)
    else:
        assert isinstance(result, ProviderFailure)
        assert result.code == "identity_mismatch"
