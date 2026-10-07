"""Deterministic six-scenario fault campaign: canonical captures, real normalizer and policy."""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from dataclasses import replace

import pytest

from actseal.errors import SchemaError
from actseal.faults import FAULT_STATE, fault_capture, run_fault_campaign
from actseal.locking import FAULT_INVENTORY, create_lock, validate_lock
from actseal.normalization import normalize, request_sha256
from actseal.policy import evaluate
from actseal.records import (
    CapturedOutcome,
    ChoiceAnswer,
    ChoiceQuestion,
    Contract,
    DecisionRequest,
    FaultResult,
    FaultSpec,
    GateLimits,
    LockedPolicy,
    ModelIdentity,
    Option,
    PlanLock,
    ProviderFailure,
)
from actseal.serialization import from_data, to_data
from conftest import HEX_B, make_contract, make_identity

CALIBRATION = '{"case_id": "c-001", "state": "Calibration one.", "expected_label": "billing"}\n'
VERIFICATION = '{"case_id": "v-001", "state": "Verification one.", "expected_label": "billing"}\n'

EXPECTED_ACTIONS = {
    "fault.timeout": ("ESCALATE", "provider.timeout"),
    "fault.rate_limit": ("ESCALATE", "provider.rate_limit"),
    "fault.malformed_response": ("ESCALATE", "provider.malformed_response"),
    "fault.identity_mismatch": ("ESCALATE", "provider.identity_mismatch"),
    "fault.unknown_choice": ("DENY", "policy.unknown_choice"),
    "fault.low_confidence": ("ABSTAIN", "policy.low_confidence"),
}

ZERO_USAGE = (
    '"usage":{"input_tokens":0,"output_tokens":0,"state_tokens":0,'
    '"state_tokens_dropped":0,"truncated":false,"truncated_questions":[]}'
)


def laya_identity() -> ModelIdentity:
    return ModelIdentity(
        "laya",
        "convaiinnovations/laya-typed-decisions",
        "e929ae5cf69bc34259cd2f95c9e91145b818b1f0",
        (("model.safetensors", HEX_B),),
        "1",
        "1",
        (("device", "cpu"),),
    )


def make_lock(identity: ModelIdentity | None = None, contract: Contract | None = None) -> PlanLock:
    lock = create_lock(
        contract or make_contract(), CALIBRATION, VERIFICATION, identity or make_identity()
    )
    validate_lock(lock)
    return lock


def spec_for(kind: str) -> FaultSpec:
    return next(spec for spec in FAULT_INVENTORY if spec.kind == kind)


def laya_envelope(answer_json: str) -> str:
    return f'{{"answers":{{"department":{answer_json}}},"model":"laya-rl-agent",{ZERO_USAGE}}}'


JEV_ZERO_USAGE = '"usage":{"input_tokens":0,"output_tokens":0}'


def jev_identity() -> ModelIdentity:
    return ModelIdentity(
        "jev",
        "jev-1.13.0",
        "jev-1.13.0",
        (),
        "1",
        "1",
        (("endpoint", "https://api.typesafe.ai/v1/systemone"),),
    )


def jev_envelope(answer_json: str) -> str:
    """The canonical Jev fault body: the inner answer plus diagnostic confidence 1.0."""
    inner = json.loads(answer_json)
    inner["confidence"] = 1.0
    answer = json.dumps(inner, sort_keys=True, separators=(",", ":"))
    return f'{{"answers":{{"department":{answer}}},"model":"jev-1.13.0",{JEV_ZERO_USAGE}}}'


IdentityFactory = Callable[[], ModelIdentity]
PROVIDERS = [
    pytest.param(make_identity, id="fixture"),
    pytest.param(laya_identity, id="laya"),
    pytest.param(jev_identity, id="jev"),
]


# --------------------------------------------------------------------------- #
# Campaign
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("identity_factory", PROVIDERS)
def test_campaign_emits_all_six_results_in_lock_order(identity_factory: IdentityFactory) -> None:
    lock = make_lock(identity_factory())
    results = run_fault_campaign(lock)
    assert isinstance(results, tuple)
    assert len(results) == 6
    assert [result.scenario_id for result in results] == [
        spec.scenario_id for spec in lock.fault_inventory
    ]
    for result, spec in zip(results, lock.fault_inventory, strict=True):
        assert isinstance(result, FaultResult)
        expected_action, expected_reason = EXPECTED_ACTIONS[spec.scenario_id]
        assert result.decision.action == spec.expected_action == expected_action
        assert result.decision.reason == expected_reason
        assert result.decision.choice is None
        assert result.decision.fallback_used is False
        assert result.request.case_id == spec.scenario_id
        assert result.capture.request_sha256 == request_sha256(result.request)
        assert result.capture.warnings == ()
        assert result.capture.fallback_used is False


@pytest.mark.parametrize("identity_factory", PROVIDERS)
def test_campaign_uses_the_real_normalizer_and_evaluator(
    identity_factory: IdentityFactory,
) -> None:
    lock = make_lock(identity_factory())
    for result in run_fault_campaign(lock):
        outcome = normalize(result.capture, lock.contract.question, lock.model_identity)
        assert outcome == result.outcome
        assert evaluate(outcome, lock.contract.policy) == result.decision
        request, capture = fault_capture(lock, spec_for(result.scenario_id.removeprefix("fault.")))
        assert (request, capture) == (result.request, result.capture)


def test_campaign_outcome_kinds_match_scenarios() -> None:
    results = {result.scenario_id: result for result in run_fault_campaign(make_lock())}
    for kind in (
        "timeout",
        "rate_limit",
        "malformed_response",
        "identity_mismatch",
        "unknown_choice",
    ):
        outcome = results[f"fault.{kind}"].outcome
        assert isinstance(outcome, ProviderFailure)
        assert outcome.code == kind
    low = results["fault.low_confidence"].outcome
    assert isinstance(low, ChoiceAnswer)
    assert low.choice == "billing"
    assert low.selected_probability == 0.0
    assert low.probabilities == (("billing", 0.0), ("technical", 1.0), ("sales", 0.0))


def test_campaign_is_deterministic_and_does_not_mutate_the_lock() -> None:
    lock = make_lock()
    before = to_data(lock)
    first = run_fault_campaign(lock)
    second = run_fault_campaign(lock)
    assert first == second
    assert to_data(lock) == before
    for result in first:
        assert from_data(FaultResult, to_data(result)) == result


def test_campaign_continues_after_a_violation() -> None:
    """A lock whose policy disallows the first allowed-by-known label still yields six results."""
    lock = make_lock()
    results = run_fault_campaign(lock)
    assert len(results) == 6
    assert all(
        result.decision.action == spec.expected_action
        for result, spec in zip(results, lock.fault_inventory, strict=True)
    )


def test_campaign_rejects_non_lock() -> None:
    with pytest.raises(SchemaError, match="lock"):
        run_fault_campaign(to_data(make_lock()))  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# Canonical generator
# --------------------------------------------------------------------------- #


def test_fault_state_literal() -> None:
    assert FAULT_STATE == "Actseal deterministic fault campaign."


@pytest.mark.parametrize("identity_factory", PROVIDERS)
def test_request_is_scenario_id_literal_state_and_locked_question(
    identity_factory: IdentityFactory,
) -> None:
    lock = make_lock(identity_factory())
    for spec in lock.fault_inventory:
        request, capture = fault_capture(lock, spec)
        assert request == DecisionRequest(spec.scenario_id, FAULT_STATE, lock.contract.question)
        assert capture.request_sha256 == request_sha256(request)
        assert capture.warnings == ()
        assert capture.fallback_used is False
        assert (capture.body_json is None) != (capture.failure_code is None)


@pytest.mark.parametrize("kind", ["timeout", "rate_limit"])
def test_transport_faults_have_no_body(kind: str) -> None:
    lock = make_lock()
    _, capture = fault_capture(lock, spec_for(kind))
    assert capture == CapturedOutcome(
        capture.request_sha256, lock.model_identity, None, kind, (), fallback_used=False
    )


@pytest.mark.parametrize("identity_factory", PROVIDERS)
def test_malformed_fault_is_the_literal_open_brace(identity_factory: IdentityFactory) -> None:
    lock = make_lock(identity_factory())
    _, capture = fault_capture(lock, spec_for("malformed_response"))
    assert capture.body_json == "{"
    assert capture.failure_code is None
    assert capture.identity == lock.model_identity


def test_fixture_bodies_are_exact_canonical_inner_answers() -> None:
    lock = make_lock()
    bodies = {
        kind: fault_capture(lock, spec_for(kind))[1].body_json
        for kind in ("identity_mismatch", "unknown_choice", "low_confidence")
    }
    assert bodies == {
        "identity_mismatch": (
            '{"choice":"billing","probabilities":{"billing":1.0,"sales":0.0,"technical":0.0},'
            '"type":"choice"}'
        ),
        "unknown_choice": (
            '{"choice":"__actseal_unknown__",'
            '"probabilities":{"billing":1.0,"sales":0.0,"technical":0.0},"type":"choice"}'
        ),
        "low_confidence": (
            '{"choice":"billing","probabilities":{"billing":0.0,"sales":0.0,"technical":1.0},'
            '"type":"choice"}'
        ),
    }


def test_laya_bodies_are_exact_zero_usage_envelopes() -> None:
    lock = make_lock(laya_identity())
    fixture_lock = make_lock()
    for kind in ("identity_mismatch", "unknown_choice", "low_confidence"):
        inner = fault_capture(fixture_lock, spec_for(kind))[1].body_json
        assert inner is not None
        _, capture = fault_capture(lock, spec_for(kind))
        assert capture.body_json == laya_envelope(inner)
        body = json.loads(capture.body_json or "")
        assert set(body) == {"model", "answers", "usage"}
        assert body["usage"] == {
            "input_tokens": 0,
            "output_tokens": 0,
            "state_tokens": 0,
            "state_tokens_dropped": 0,
            "truncated": False,
            "truncated_questions": [],
        }


def test_jev_bodies_are_exact_envelopes_with_diagnostic_confidence_one() -> None:
    """V1-011: the six scenarios keep their ids, order and dispositions under a Jev identity."""
    lock = make_lock(jev_identity())
    fixture_lock = make_lock()
    assert [spec.scenario_id for spec in lock.fault_inventory] == [
        spec.scenario_id for spec in fixture_lock.fault_inventory
    ]
    for kind in ("identity_mismatch", "unknown_choice", "low_confidence"):
        inner = fault_capture(fixture_lock, spec_for(kind))[1].body_json
        assert inner is not None
        _, capture = fault_capture(lock, spec_for(kind))
        assert capture.body_json == jev_envelope(inner)
        body = json.loads(capture.body_json or "")
        assert set(body) == {"model", "answers", "usage"}
        assert body["model"] == "jev-1.13.0"
        assert body["usage"] == {"input_tokens": 0, "output_tokens": 0}
        answer = body["answers"]["department"]
        assert set(answer) == {"type", "choice", "probabilities", "confidence"}
        assert answer["confidence"] == 1.0
    for kind in ("timeout", "rate_limit"):
        assert fault_capture(lock, spec_for(kind))[1].body_json is None
    assert fault_capture(lock, spec_for("malformed_response"))[1].body_json == "{"


def test_jev_low_confidence_abstains_despite_vendor_confidence_one() -> None:
    """The one-hot vendor confidence is 1.0 while the selected probability is 0.0."""
    results = {r.scenario_id: r for r in run_fault_campaign(make_lock(jev_identity()))}
    low = results["fault.low_confidence"]
    assert isinstance(low.outcome, ChoiceAnswer)
    assert low.outcome.provider_confidence == 1.0
    assert low.outcome.selected_probability == 0.0
    assert low.outcome.choice == "billing"
    assert low.decision.action == "ABSTAIN"
    assert low.decision.reason == "policy.low_confidence"
    unknown = results["fault.unknown_choice"]
    assert isinstance(unknown.outcome, ProviderFailure)
    assert unknown.outcome.code == "unknown_choice"
    assert unknown.decision.action == "DENY"
    mismatch = results["fault.identity_mismatch"]
    assert isinstance(mismatch.outcome, ProviderFailure)
    assert mismatch.outcome.code == "identity_mismatch"
    assert mismatch.capture.identity.revision == "jev-1.13.0:fault"
    assert json.loads(mismatch.capture.body_json or "")["model"] == "jev-1.13.0"


def test_jev_campaign_rederives_on_offline_round_trip() -> None:
    """Serialized Jev fault results decode and re-normalize to themselves without any adapter."""
    lock = make_lock(jev_identity())
    for result in run_fault_campaign(lock):
        decoded = from_data(FaultResult, to_data(result))
        assert decoded == result
        assert normalize(decoded.capture, lock.contract.question, lock.model_identity) == (
            decoded.outcome
        )
        assert evaluate(decoded.outcome, lock.contract.policy) == decoded.decision


def test_identity_mismatch_changes_only_the_revision() -> None:
    lock = make_lock()
    _, capture = fault_capture(lock, spec_for("identity_mismatch"))
    assert capture.identity == replace(
        lock.model_identity, revision=lock.model_identity.revision + ":fault"
    )
    assert capture.identity != lock.model_identity
    for kind in ("timeout", "rate_limit", "malformed_response", "unknown_choice", "low_confidence"):
        assert fault_capture(lock, spec_for(kind))[1].identity == lock.model_identity


def test_unknown_choice_appends_underscores_until_outside_known_labels() -> None:
    question = ChoiceQuestion(
        "department",
        "Pick one.",
        (
            Option("__actseal_unknown__", "a"),
            Option("__actseal_unknown___", "b"),
            Option("billing", "c"),
        ),
    )
    contract = Contract(
        1,
        "weird-labels",
        question,
        LockedPolicy(question.labels, ("billing",), 0.9),
        GateLimits(0.05, 0.5, 0.05),
        "demo",
        "Authored demonstration",
    )
    lock = make_lock(contract=contract)
    _, capture = fault_capture(lock, spec_for("unknown_choice"))
    body = json.loads(capture.body_json or "")
    assert body["choice"] == "__actseal_unknown____"
    assert body["probabilities"] == {
        "__actseal_unknown__": 0.0,
        "__actseal_unknown___": 0.0,
        "billing": 1.0,
    }
    result = next(r for r in run_fault_campaign(lock) if r.scenario_id == "fault.unknown_choice")
    assert result.decision.action == "DENY"


def test_low_confidence_keeps_first_allowed_label_not_first_known() -> None:
    question = make_contract().question
    contract = Contract(
        1,
        "technical-first",
        question,
        LockedPolicy(question.labels, ("technical", "sales"), 0.5),
        GateLimits(0.05, 0.5, 0.05),
        "demo",
        "Authored demonstration",
    )
    lock = make_lock(contract=contract)
    _, capture = fault_capture(lock, spec_for("low_confidence"))
    assert capture.body_json == (
        '{"choice":"technical","probabilities":{"billing":1.0,"sales":0.0,"technical":0.0},'
        '"type":"choice"}'
    )
    results = {r.scenario_id: r for r in run_fault_campaign(lock)}
    low = results["fault.low_confidence"]
    assert isinstance(low.outcome, ChoiceAnswer)
    assert low.outcome.choice == "technical"
    assert low.outcome.selected_probability == 0.0
    assert low.decision.action == "ABSTAIN"
    mismatch = results["fault.identity_mismatch"]
    assert json.loads(mismatch.capture.body_json or "")["choice"] == "technical"


def test_fault_capture_is_pure_and_deterministic() -> None:
    lock = make_lock(laya_identity())
    before = to_data(lock)
    spec = spec_for("low_confidence")
    assert fault_capture(lock, spec) == fault_capture(lock, spec)
    assert to_data(lock) == before
    assert to_data(spec) == {
        "scenario_id": "fault.low_confidence",
        "kind": "low_confidence",
        "expected_action": "ABSTAIN",
    }


def test_fault_capture_rejects_unknown_kind_and_bad_types() -> None:
    lock = make_lock()
    with pytest.raises(SchemaError, match="kind"):
        fault_capture(lock, FaultSpec("fault.other", "other", "ESCALATE"))
    with pytest.raises(SchemaError, match="lock"):
        fault_capture(to_data(lock), spec_for("timeout"))  # type: ignore[arg-type]
    with pytest.raises(SchemaError, match="spec"):
        fault_capture(lock, to_data(spec_for("timeout")))  # type: ignore[arg-type]


def test_faults_module_imports_no_adapter_or_native_module() -> None:
    script = (
        "import sys\n"
        "import actseal.faults\n"
        "loaded = sorted(name for name in sys.modules if name.split('.')[0] in "
        "('laya', 'torch', 'transformers', 'huggingface_hub', 'safetensors', 'numpy') "
        "or name.startswith('actseal.adapters') or name in "
        "('actseal.assessment', 'actseal.replay'))\n"
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
# Envelope defects through the provider-specific campaigns
# --------------------------------------------------------------------------- #


def _laya_low_confidence() -> tuple[PlanLock, CapturedOutcome, dict[str, object]]:
    lock = make_lock(laya_identity())
    _, capture = fault_capture(lock, spec_for("low_confidence"))
    body = json.loads(capture.body_json or "")
    assert isinstance(body, dict)
    return lock, capture, body


def _with_body(capture: CapturedOutcome, body: object) -> CapturedOutcome:
    return replace(capture, body_json=json.dumps(body))


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (
            lambda b: b["answers"].update({"other": b["answers"].pop("department")}),
            "malformed_response",
        ),
        (lambda b: b["answers"].clear(), "malformed_response"),
        (
            lambda b: b["answers"].update({"extra": dict(b["answers"]["department"])}),
            "malformed_response",
        ),
        (lambda b: b["usage"].update({"input_tokens": True}), "malformed_response"),
        (lambda b: b["usage"].pop("truncated"), "malformed_response"),
        (lambda b: b["usage"].update({"truncated": True}), "input_too_long"),
        (lambda b: b["usage"].update({"state_tokens_dropped": 1}), "input_too_long"),
        (lambda b: b["usage"].update({"truncated_questions": ["department"]}), "input_too_long"),
        (
            lambda b: b["usage"].update(
                {"options": {"department": {"total": 3, "distinct": 2, "tokens_per_option": None}}}
            ),
            "input_too_long",
        ),
        (lambda b: b.update({"model": "laya-typed-decisions"}), "malformed_response"),
        (lambda b: b.pop("usage"), "malformed_response"),
    ],
)
def test_laya_campaign_envelope_defects_escalate(mutate: object, code: str) -> None:
    lock, capture, body = _laya_low_confidence()
    mutate(body)  # type: ignore[operator]
    outcome = normalize(_with_body(capture, body), lock.contract.question, lock.model_identity)
    assert isinstance(outcome, ProviderFailure)
    assert outcome.code == code
    decision = evaluate(outcome, lock.contract.policy)
    assert decision.action == "ESCALATE"
    assert decision.reason == f"provider.{code}"


def _jev_low_confidence() -> tuple[PlanLock, CapturedOutcome, dict[str, object]]:
    lock = make_lock(jev_identity())
    _, capture = fault_capture(lock, spec_for("low_confidence"))
    body = json.loads(capture.body_json or "")
    assert isinstance(body, dict)
    return lock, capture, body


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda b: b.update({"model": "jev-1.12.0"}), "identity_mismatch"),
        (lambda b: b.update({"model": "laya-rl-agent"}), "identity_mismatch"),
        (lambda b: b.update({"model": 1}), "malformed_response"),
        (
            lambda b: b["answers"].update({"other": b["answers"].pop("department")}),
            "malformed_response",
        ),
        (lambda b: b["answers"].clear(), "malformed_response"),
        (lambda b: b["usage"].update({"input_tokens": True}), "malformed_response"),
        (lambda b: b["usage"].update({"state_tokens": 0}), "malformed_response"),
        (lambda b: b["usage"].pop("output_tokens"), "malformed_response"),
        (lambda b: b.pop("usage"), "malformed_response"),
        (lambda b: b["answers"]["department"].pop("confidence"), "malformed_response"),
        (lambda b: b["answers"]["department"].update({"action": {}}), "malformed_response"),
        (lambda b: b["answers"]["department"].update({"confidence": 2.0}), "malformed_response"),
    ],
)
def test_jev_campaign_envelope_defects_escalate(mutate: object, code: str) -> None:
    lock, capture, body = _jev_low_confidence()
    mutate(body)  # type: ignore[operator]
    outcome = normalize(_with_body(capture, body), lock.contract.question, lock.model_identity)
    assert isinstance(outcome, ProviderFailure)
    assert outcome.code == code
    decision = evaluate(outcome, lock.contract.policy)
    assert decision.action == "ESCALATE"
    assert decision.reason == f"provider.{code}"


def test_jev_and_laya_campaigns_reject_each_other_s_envelopes() -> None:
    jev_lock, jev_capture, _ = _jev_low_confidence()
    laya_lock, laya_capture, _ = _laya_low_confidence()
    assert jev_capture.body_json is not None
    assert laya_capture.body_json is not None
    swapped = replace(jev_capture, body_json=laya_capture.body_json)
    outcome = normalize(swapped, jev_lock.contract.question, jev_lock.model_identity)
    assert isinstance(outcome, ProviderFailure)
    assert outcome.code == "malformed_response"
    swapped = replace(laya_capture, body_json=jev_capture.body_json)
    outcome = normalize(swapped, laya_lock.contract.question, laya_lock.model_identity)
    assert isinstance(outcome, ProviderFailure)
    assert outcome.code == "malformed_response"


def test_fixture_campaign_rejects_a_native_envelope_body() -> None:
    lock = make_lock()
    _, capture = fault_capture(lock, spec_for("low_confidence"))
    laya_lock, laya_capture, _ = _laya_low_confidence()
    assert laya_capture.body_json is not None
    swapped = replace(capture, body_json=laya_capture.body_json)
    outcome = normalize(swapped, lock.contract.question, lock.model_identity)
    assert isinstance(outcome, ProviderFailure)
    assert outcome.code == "malformed_response"
    assert evaluate(outcome, lock.contract.policy).action == "ESCALATE"
    inner = capture.body_json
    assert inner is not None
    unwrapped = replace(laya_capture, body_json=inner)
    outcome = normalize(unwrapped, laya_lock.contract.question, laya_lock.model_identity)
    assert isinstance(outcome, ProviderFailure)
    assert outcome.code == "malformed_response"


def test_swapped_scenario_capture_is_detectable_by_exact_comparison() -> None:
    lock = make_lock()
    _, timeout = fault_capture(lock, spec_for("timeout"))
    _, rate_limit = fault_capture(lock, spec_for("rate_limit"))
    assert timeout != rate_limit
    assert timeout.request_sha256 != rate_limit.request_sha256
    digests = {fault_capture(lock, spec)[1].request_sha256 for spec in lock.fault_inventory}
    assert len(digests) == 6
