"""Real decision-API locking, collection, synthetic faults and offline replay."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_evidence import GOLD
from test_jev import FakeConnect, FakeConnection, jev_body, ok
from test_runner import write_inputs

from actseal.adapters.base import DecisionModel
from actseal.errors import IntegrityError
from actseal.experimental.providers.decision_api import _Endpoint
from actseal.records import ChoiceAnswer
from actseal.replay import replay
from actseal.runner import ModelFactory, lock_run, open_model, verify_run
from conftest import make_question


def _factory(endpoint: str, model: str, revision: str) -> ModelFactory:
    def create() -> DecisionModel:
        return open_model(
            "decision-api",
            responses=None,
            offline=False,
            endpoint=endpoint,
            model=model,
            revision=revision,
        )

    return create


def _transport(monkeypatch: pytest.MonkeyPatch, model: str) -> FakeConnect:
    connect = FakeConnect(
        *(ok(jev_body(make_question(), model=model, choice=label)) for _, _, label in GOLD)
    )

    def connection(_endpoint: _Endpoint, timeout: float) -> FakeConnection:
        return connect(timeout)

    monkeypatch.setattr(_Endpoint, "connect", connection)
    return connect


@pytest.mark.parametrize(
    ("endpoint", "model", "revision"),
    [
        ("http://localhost:8080/decide", "local-choice-v2", "weights-abc"),
        ("http://[::1]:9000/v1/systemone", "another-model", "release-2"),
        ("https://decisions.example.org/v1", "remote-choice", "pinned-build"),
    ],
)
def test_decision_api_workflow_replays_non_jev_models_and_all_synthetic_faults(
    endpoint: str,
    model: str,
    revision: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = write_inputs(tmp_path / "inputs")
    factory = _factory(endpoint, model, revision)
    connect = _transport(monkeypatch, model)
    lock_path = tmp_path / "lock.json"
    lock = lock_run(
        inputs["contract"],
        inputs["calibration"],
        inputs["verification"],
        lock_path,
        model_factory=factory,
    )
    assert connect.connections == 0
    assert lock.model_identity.provider == "decision-api"
    assert lock.model_identity.model == model
    assert lock.model_identity.revision == revision
    assert dict(lock.model_identity.runtime)["endpoint"] == endpoint

    bundle, bundle_path = verify_run(
        lock_path,
        inputs["calibration"],
        inputs["verification"],
        tmp_path / "bundle",
        provider="decision-api",
        model_factory=factory,
    )
    assert len(bundle.records) == len(GOLD)
    for record, (case_id, state, label), sent in zip(
        bundle.records, GOLD, connect.log, strict=True
    ):
        assert record.case_id == case_id
        assert isinstance(record.outcome, ChoiceAnswer)
        assert record.outcome.choice == label
        assert record.decision.action == "ACT"
        assert record.capture.identity == lock.model_identity
        payload = json.loads(sent.body)
        assert payload["model"] == model
        assert payload["state"] == state
        assert sent.closed == 1
        assert sent.timeout == 30.0
    assert len(connect.log) == len(GOLD)
    assert tuple(fault.decision.action for fault in bundle.faults) == (
        "ESCALATE",
        "ESCALATE",
        "ESCALATE",
        "ESCALATE",
        "DENY",
        "ABSTAIN",
    )
    for spec, fault in zip(lock.fault_inventory, bundle.faults, strict=True):
        assert fault.scenario_id == spec.scenario_id
        assert fault.decision.action == spec.expected_action
    assert bundle.verdict.status == "INCONCLUSIVE"
    assert bundle.verdict.total == len(GOLD)
    assert bundle.verdict.accepted == len(GOLD)
    assert bundle.verdict.errors == 0

    def no_transport(_endpoint: _Endpoint, _timeout: float) -> FakeConnection:
        pytest.fail("replay must not open a provider transport")

    monkeypatch.setattr(_Endpoint, "connect", no_transport)
    assert replay(bundle_path) == bundle.verdict


@pytest.mark.parametrize(
    ("endpoint", "model", "revision"),
    [
        ("http://localhost:8081/decide", "local-choice-v2", "weights-abc"),
        ("http://localhost:8080/decide", "other-model", "weights-abc"),
        ("http://localhost:8080/decide", "local-choice-v2", "other-revision"),
    ],
    ids=["endpoint-drift", "model-drift", "revision-drift"],
)
def test_decision_api_identity_drift_refuses_collection_before_transport(
    endpoint: str,
    model: str,
    revision: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = write_inputs(tmp_path / "inputs")
    connect = _transport(monkeypatch, "local-choice-v2")
    lock_path = tmp_path / "lock.json"
    lock_run(
        inputs["contract"],
        inputs["calibration"],
        inputs["verification"],
        lock_path,
        model_factory=_factory("http://localhost:8080/decide", "local-choice-v2", "weights-abc"),
    )
    destination = tmp_path / "rejected-bundle"
    with pytest.raises(IntegrityError, match=r"model_identity:.*does not match the lock"):
        verify_run(
            lock_path,
            inputs["calibration"],
            inputs["verification"],
            destination,
            provider="decision-api",
            model_factory=_factory(endpoint, model, revision),
        )
    assert connect.connections == 0
    assert not destination.exists()
