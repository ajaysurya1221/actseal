"""The runner composes the accepted authorities into the fixed v1 collection protocol.

Every lock and bundle here is produced by the real ``create_lock``,
``validate_inputs``, ``normalize``, ``evaluate``, ``run_fault_campaign``,
``assess``, ``write_bundle`` and ``replay``; only the decision model is scripted
(an in-process ``DecisionModel`` with recorded calls, the real ``FixtureModel``,
or the real ``LayaModel`` around the T30 fake worker). No test authors a
verdict: expected statuses come from a direct ``assess`` or from the ADR 0013
inequalities evaluated by the pipeline itself.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import subprocess
import sys
import tomllib
from collections.abc import Callable, Mapping
from dataclasses import replace
from pathlib import Path

import pytest
from test_evidence import CALIBRATION, GOLD, answer_json, contract_with, verification_jsonl
from test_providers import FAKE_WORKER, pinned_identity

import actseal.adapters.laya as laya_module
import actseal.runner as runner_module
from actseal.adapters.fixture import FixtureModel
from actseal.adapters.laya import STARTUP_TIMEOUT_S, LayaModel
from actseal.assessment import REASON_WORKER_INVALIDATED, assess
from actseal.contract import parse_cases, parse_contract, read_input_text
from actseal.errors import IntegrityError, ProviderSetupError, SchemaError
from actseal.evidence import BUNDLE_FILES, RECORDS_FILE, decode_rows
from actseal.faults import run_fault_campaign
from actseal.locking import create_lock, lock_digest, parse_lock, validate_lock
from actseal.normalization import request_sha256
from actseal.records import (
    CapturedOutcome,
    ChoiceAnswer,
    Contract,
    DecisionRecord,
    DecisionRequest,
    Interval,
    ModelIdentity,
    PlanLock,
)
from actseal.replay import replay
from actseal.runner import (
    DEMO_EXPECTED,
    DEMO_INPUTS_DIRECTORY,
    DEMO_RUNS,
    EVIDENCE_DIRECTORY,
    LOCK_FILE_NAME,
    REQUEST_TIMEOUT_S,
    collect,
    demo_run,
    lock_run,
    open_model,
    verify_run,
    write_lock,
)
from actseal.serialization import canonical_json, implementation_fingerprint, to_data
from conftest import make_identity

ROOT = Path(__file__).resolve().parents[2]
PACKAGED = ROOT / "src" / "actseal" / "demo_data"
EXAMPLES = ROOT / "examples" / "support_triage"
GENERATOR = EXAMPLES / "generate_demo_data.py"
RESOURCE_NAMES = tuple(
    f"{run}{suffix}"
    for run in ("bad", "fixed")
    for suffix in (".toml", "_calibration.jsonl", "_verification.jsonl", "_responses.jsonl")
)
LABELS = ("billing", "technical", "sales")
FULL = Interval(0.0, 1.0)

CONTRACT_TOML = """\
schema_version = 1
name = "support-triage"
evidence_scope = "demo"
population = "Authored support-routing demonstration; no deployment claim"

[question]
question_id = "department"
instructions = "Select the department responsible for this ticket."
options = [
  {label = "billing", description = "Payments and refunds"},
  {label = "technical", description = "Technical support"},
  {label = "sales", description = "Purchasing questions"},
]

[policy]
allowed_labels = ["billing", "technical", "sales"]
threshold = 0.90

[risk]
max_risk = 0.05
min_coverage = 0.50
alpha = 0.05
"""


# --------------------------------------------------------------------------- #
# Scripted models and input writers
# --------------------------------------------------------------------------- #


class ScriptedModel:
    """An in-process DecisionModel whose captures follow a script keyed by case id."""

    def __init__(
        self,
        identity: ModelIdentity,
        script: Callable[[str], tuple[str | None, str | None, tuple[str, ...]]],
    ) -> None:
        self._identity = identity
        self._script = script
        self.calls: list[tuple[str, float]] = []
        self.closed = 0

    def identity(self) -> ModelIdentity:
        return self._identity

    def decide(self, request: DecisionRequest, *, timeout_s: float) -> CapturedOutcome:
        self.calls.append((request.case_id, timeout_s))
        body, failure, warnings = self._script(request.case_id)
        return CapturedOutcome(
            request_sha256(request), self._identity, body, failure, warnings, fallback_used=False
        )

    def close(self) -> None:
        self.closed += 1


class Closing:
    """Wrap any DecisionModel to observe close() calls."""

    def __init__(self, inner: FixtureModel | LayaModel) -> None:
        self._inner = inner
        self.closed = 0

    def identity(self) -> ModelIdentity:
        return self._inner.identity()

    def decide(self, request: DecisionRequest, *, timeout_s: float) -> CapturedOutcome:
        return self._inner.decide(request, timeout_s=timeout_s)

    def close(self) -> None:
        self.closed += 1
        self._inner.close()


def gold_script(case_id: str) -> tuple[str | None, str | None, tuple[str, ...]]:
    label = next(label for cid, _, label in GOLD if cid == case_id)
    return answer_json(label), None, ()


def write_inputs(directory: Path, *, verification: str | None = None) -> dict[str, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    paths = {
        "contract": directory / "contract.toml",
        "calibration": directory / "calibration.jsonl",
        "verification": directory / "verification.jsonl",
    }
    paths["contract"].write_text(CONTRACT_TOML, encoding="utf-8")
    paths["calibration"].write_bytes(CALIBRATION.encode("utf-8"))
    paths["verification"].write_bytes((verification or verification_jsonl()).encode("utf-8"))
    return paths


def write_responses(path: Path, rows: Mapping[str, tuple[str | None, str | None]]) -> Path:
    lines = [
        json.dumps(
            {"case_id": cid, "body_json": body, "failure_code": failure, "warnings": []},
            ensure_ascii=False,
        )
        for cid, (body, failure) in rows.items()
    ]
    path.write_text("".join(line + "\n" for line in lines), encoding="utf-8")
    return path


def gold_responses(path: Path, *, drop: str | None = None) -> Path:
    rows = {cid: (answer_json(label), None) for cid, _, label in GOLD if cid != drop}
    return write_responses(path, rows)


def small_contract() -> Contract:
    return contract_with()


def never_called() -> ScriptedModel:
    pytest.fail("model factory must not be called")


def lock_for(tmp_path: Path, identity: ModelIdentity, *, verification: str | None = None) -> Path:
    inputs = write_inputs(tmp_path / "in", verification=verification)
    lock = create_lock(
        parse_contract(inputs["contract"]),
        read_input_text(inputs["calibration"]),
        read_input_text(inputs["verification"]),
        identity,
    )
    return write_lock(lock, tmp_path / "lock.json")


def read_lock(path: Path) -> PlanLock:
    lock = parse_lock(read_input_text(path))
    validate_lock(lock)
    return lock


def tree(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


# --------------------------------------------------------------------------- #
# ADR 0008: fixed deadlines, no override surface
# --------------------------------------------------------------------------- #


def test_request_timeout_is_the_fixed_source_constant() -> None:
    assert REQUEST_TIMEOUT_S == 30.0
    assert type(REQUEST_TIMEOUT_S) is float
    assert STARTUP_TIMEOUT_S == 120.0


@pytest.mark.parametrize("function", [collect, lock_run, verify_run, demo_run, open_model])
def test_runner_entrypoints_expose_no_deadline_override(function: Callable[..., object]) -> None:
    names = {name.lower() for name in inspect.signature(function).parameters}
    assert not any("timeout" in name or "deadline" in name for name in names)


def test_laya_constructor_accepts_only_the_offline_flag() -> None:
    assert list(inspect.signature(LayaModel.__init__).parameters) == ["self", "offline"]


def test_collect_passes_30_seconds_to_every_normal_request(tmp_path: Path) -> None:
    lock = read_lock(lock_for(tmp_path, make_identity()))
    model = ScriptedModel(make_identity(), gold_script)
    records = collect(model, lock, lock.verification_cases)
    assert [case_id for case_id, _ in model.calls] == [cid for cid, _, _ in GOLD]
    assert {timeout for _, timeout in model.calls} == {30.0}
    assert all(type(timeout) is float for _, timeout in model.calls)
    assert len(records) == len(GOLD)
    assert all(record.decision.action == "ACT" for record in records)


# --------------------------------------------------------------------------- #
# verify: exact collection, retention, cleanup
# --------------------------------------------------------------------------- #


def test_verify_run_executes_each_case_once_in_lock_order_and_closes(tmp_path: Path) -> None:
    lock_path = lock_for(tmp_path, make_identity())
    inputs = tmp_path / "in"
    model = ScriptedModel(make_identity(), gold_script)
    factories: list[int] = []

    def factory() -> ScriptedModel:
        factories.append(1)
        return model

    bundle, out = verify_run(
        lock_path,
        inputs / "calibration.jsonl",
        inputs / "verification.jsonl",
        tmp_path / "run",
        provider="fixture",
        model_factory=factory,
    )
    assert factories == [1]
    assert model.closed == 1
    assert [cid for cid, _ in model.calls] == [cid for cid, _, _ in GOLD]
    assert out == tmp_path / "run"
    assert sorted(p.name for p in out.iterdir()) == sorted(BUNDLE_FILES)
    assert bundle.verdict == assess(bundle.records, bundle.lock, bundle.faults)
    assert bundle.verdict.status == "INCONCLUSIVE"
    assert (bundle.verdict.total, bundle.verdict.accepted) == (6, 6)
    assert len(bundle.faults) == 6
    assert replay(out, expected_lock_sha256=bundle.lock.sha256) == bundle.verdict


def test_verify_run_never_stops_on_an_attractive_intermediate_result(tmp_path: Path) -> None:
    """A run whose first cases already satisfy PASS still collects every scheduled case."""
    contract = contract_with(max_risk=0.6, min_coverage=0.1)
    inputs = write_inputs(tmp_path / "in")
    lock = create_lock(contract, CALIBRATION, verification_jsonl(), make_identity())
    lock_path = write_lock(lock, tmp_path / "lock.json")
    model = ScriptedModel(make_identity(), gold_script)
    bundle, _ = verify_run(
        lock_path,
        inputs["calibration"],
        inputs["verification"],
        tmp_path / "run",
        provider="fixture",
        model_factory=lambda: model,
    )
    assert len(model.calls) == len(GOLD)
    assert bundle.verdict.status == "PASS"
    assert bundle.verdict.total == len(GOLD)


def test_nonfatal_fixture_failure_remains_a_denominator_observation(tmp_path: Path) -> None:
    inputs = write_inputs(tmp_path / "in")
    rows: dict[str, tuple[str | None, str | None]] = {
        cid: (answer_json(label), None) for cid, _, label in GOLD
    }
    rows["v-003"] = (None, "provider_error")
    responses = write_responses(tmp_path / "responses.jsonl", rows)
    model = Closing(FixtureModel(responses))
    lock = create_lock(
        small_contract(), CALIBRATION, verification_jsonl(), FixtureModel(responses).identity()
    )
    lock_path = write_lock(lock, tmp_path / "lock.json")
    bundle, out = verify_run(
        lock_path,
        inputs["calibration"],
        inputs["verification"],
        tmp_path / "run",
        provider="fixture",
        model_factory=lambda: model,
    )
    assert model.closed == 1
    assert bundle.verdict.status == "INCONCLUSIVE"
    assert (bundle.verdict.total, bundle.verdict.accepted, bundle.verdict.errors) == (6, 5, 0)
    failed = bundle.records[2]
    assert failed.capture.failure_code == "provider_error"
    assert failed.decision.action == "ESCALATE"
    assert failed.decision.reason == "provider.provider_error"
    assert replay(out) == bundle.verdict


def laya_envelope(label: str) -> str:
    """The complete native Laya response envelope around a gold-label answer."""
    envelope = {
        "model": "laya-rl-agent",
        "answers": {"department": json.loads(answer_json(label))},
        "usage": {
            "input_tokens": 1,
            "output_tokens": 0,
            "state_tokens": 1,
            "state_tokens_dropped": 0,
            "truncated": False,
            "truncated_questions": [],
        },
    }
    return json.dumps(envelope)


def laya_script(case_id: str) -> tuple[str | None, str | None, tuple[str, ...]]:
    label = next(label for cid, _, label in GOLD if cid == case_id)
    return laya_envelope(label), None, ()


def worker_loss_script(case_id: str) -> tuple[str | None, str | None, tuple[str, ...]]:
    """Healthy native answer first, timeout on the second, explicit unavailable afterwards."""
    index = [cid for cid, _, _ in GOLD].index(case_id)
    if index == 0:
        return laya_script(case_id)
    if index == 1:
        return None, "timeout", ()
    return None, "unavailable", ("laya.unavailable:timeout",)


def test_regular_laya_worker_loss_yields_a_complete_diagnostic_error_bundle(
    tmp_path: Path,
) -> None:
    identity = pinned_identity()
    lock_path = lock_for(tmp_path, identity)
    inputs = tmp_path / "in"
    model = ScriptedModel(identity, worker_loss_script)
    factories: list[int] = []

    def factory() -> ScriptedModel:
        factories.append(1)
        return model

    bundle, out = verify_run(
        lock_path,
        inputs / "calibration.jsonl",
        inputs / "verification.jsonl",
        tmp_path / "run",
        provider="laya",
        model_factory=factory,
    )
    assert factories == [1]  # no restart, no replacement instance
    assert model.closed == 1
    assert [cid for cid, _ in model.calls] == [cid for cid, _, _ in GOLD]
    assert {timeout for _, timeout in model.calls} == {30.0}
    codes = [record.capture.failure_code for record in bundle.records]
    assert codes == [None, "timeout", "unavailable", "unavailable", "unavailable", "unavailable"]
    healthy = bundle.records[0]
    assert isinstance(healthy.outcome, ChoiceAnswer)
    assert healthy.decision.action == "ACT"
    assert healthy.decision.choice == GOLD[0][2]
    assert healthy.decision.reason == "policy.allowed"
    assert bundle.records[1].decision.reason == "provider.timeout"
    assert bundle.records[2].decision.reason == "provider.unavailable"
    verdict = bundle.verdict
    assert verdict.status == "ERROR"
    assert verdict.reasons == (REASON_WORKER_INVALIDATED,)
    assert (verdict.total, verdict.accepted, verdict.errors) == (0, 0, 0)
    assert verdict.risk == FULL
    assert verdict.coverage == FULL
    assert len(bundle.faults) == 6
    written = decode_rows(RECORDS_FILE, (out / RECORDS_FILE).read_bytes(), DecisionRecord)
    assert written == bundle.records
    assert replay(out, expected_lock_sha256=bundle.lock.sha256) == verdict


def test_real_laya_adapter_worker_loss_end_to_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real LayaModel around the T30 fake worker: the first decide loses the worker."""
    script = tmp_path / "fake_worker.py"
    script.write_text(FAKE_WORKER, encoding="utf-8")
    monkeypatch.setenv("ACTSEAL_FAKE_IDENTITY", json.dumps(to_data(pinned_identity())))
    lock_path = lock_for(tmp_path, pinned_identity())
    inputs = tmp_path / "in"
    spawned: list[Closing] = []

    def factory() -> Closing:
        model = Closing(
            LayaModel._spawn(
                (sys.executable, str(script), "exit-on-decide"),
                offline=True,
                startup_timeout_s=10.0,
                close_grace_s=0.3,
            )
        )
        spawned.append(model)
        return model

    bundle, out = verify_run(
        lock_path,
        inputs / "calibration.jsonl",
        inputs / "verification.jsonl",
        tmp_path / "run",
        provider="laya",
        model_factory=factory,
    )
    assert len(spawned) == 1
    assert spawned[0].closed == 1
    assert all(record.capture.failure_code == "unavailable" for record in bundle.records)
    assert len(bundle.records) == len(GOLD)
    assert "laya.unavailable:worker_exit" in bundle.records[0].capture.warnings
    assert bundle.verdict.status == "ERROR"
    assert bundle.verdict.reasons == (REASON_WORKER_INVALIDATED,)
    assert replay(out) == bundle.verdict


def test_synthetic_fault_campaign_does_not_invalidate_a_healthy_laya_run(tmp_path: Path) -> None:
    identity = pinned_identity()
    lock_path = lock_for(tmp_path, identity)
    inputs = tmp_path / "in"
    model = ScriptedModel(identity, laya_script)
    bundle, _ = verify_run(
        lock_path,
        inputs / "calibration.jsonl",
        inputs / "verification.jsonl",
        tmp_path / "run",
        provider="laya",
        model_factory=lambda: model,
    )
    assert bundle.faults[0].capture.failure_code == "timeout"  # synthetic, excluded
    assert bundle.verdict.status == "INCONCLUSIVE"
    assert bundle.verdict.accepted == len(GOLD)
    assert all(record.decision.action == "ACT" for record in bundle.records)


def test_missing_fixture_case_is_a_setup_error_with_no_bundle(tmp_path: Path) -> None:
    inputs = write_inputs(tmp_path / "in")
    responses = gold_responses(tmp_path / "responses.jsonl", drop="v-004")
    model = Closing(FixtureModel(responses))
    lock = create_lock(small_contract(), CALIBRATION, verification_jsonl(), model.identity())
    lock_path = write_lock(lock, tmp_path / "lock.json")
    with pytest.raises(ProviderSetupError):
        verify_run(
            lock_path,
            inputs["calibration"],
            inputs["verification"],
            tmp_path / "run",
            provider="fixture",
            model_factory=lambda: model,
        )
    assert model.closed == 1
    assert not (tmp_path / "run").exists()
    assert [p.name for p in tmp_path.iterdir() if p.name.startswith(".actseal")] == []


def test_observed_identity_mismatch_is_rejected_before_any_decide(tmp_path: Path) -> None:
    lock_path = lock_for(tmp_path, make_identity())
    inputs = tmp_path / "in"
    observed = replace(make_identity(), revision="b" * 64)
    model = ScriptedModel(observed, gold_script)
    with pytest.raises(IntegrityError, match="model_identity"):
        verify_run(
            lock_path,
            inputs / "calibration.jsonl",
            inputs / "verification.jsonl",
            tmp_path / "run",
            provider="fixture",
            model_factory=lambda: model,
        )
    assert model.calls == []
    assert model.closed == 1
    assert not (tmp_path / "run").exists()


def test_different_fixture_file_is_an_identity_mismatch(tmp_path: Path) -> None:
    """Only a revision-equal AND artifact-equal AND runtime-equal identity passes."""
    inputs = write_inputs(tmp_path / "in")
    locked = FixtureModel(gold_responses(tmp_path / "a.jsonl"))
    rows = {cid: (answer_json(label, 0.96), None) for cid, _, label in GOLD}
    other = Closing(FixtureModel(write_responses(tmp_path / "b.jsonl", rows)))
    lock = create_lock(small_contract(), CALIBRATION, verification_jsonl(), locked.identity())
    lock_path = write_lock(lock, tmp_path / "lock.json")
    with pytest.raises(IntegrityError, match="model_identity"):
        verify_run(
            lock_path,
            inputs["calibration"],
            inputs["verification"],
            tmp_path / "run",
            provider="fixture",
            model_factory=lambda: other,
        )
    assert other.closed == 1


def test_runtime_only_identity_difference_is_rejected(tmp_path: Path) -> None:
    identity = pinned_identity()
    lock_path = lock_for(tmp_path, identity)
    inputs = tmp_path / "in"
    observed = replace(identity, runtime=(*identity.runtime, ("extra", "1")))
    model = ScriptedModel(observed, gold_script)
    with pytest.raises(IntegrityError):
        verify_run(
            lock_path,
            inputs / "calibration.jsonl",
            inputs / "verification.jsonl",
            tmp_path / "run",
            provider="laya",
            model_factory=lambda: model,
        )
    assert model.calls == []
    assert model.closed == 1


def test_provider_mismatch_is_rejected_before_the_factory(tmp_path: Path) -> None:
    lock_path = lock_for(tmp_path, make_identity())
    inputs = tmp_path / "in"
    with pytest.raises(IntegrityError, match="provider"):
        verify_run(
            lock_path,
            inputs / "calibration.jsonl",
            inputs / "verification.jsonl",
            tmp_path / "run",
            provider="laya",
            model_factory=never_called,
        )
    with pytest.raises(SchemaError, match="provider"):
        verify_run(
            lock_path,
            inputs / "calibration.jsonl",
            inputs / "verification.jsonl",
            tmp_path / "run",
            provider="unsupported",
            model_factory=never_called,
        )


def test_admitted_jev_provider_against_a_fixture_lock_is_rejected_before_the_factory(
    tmp_path: Path,
) -> None:
    """``jev`` is an admitted identity provider (V1-011) but this lock is a fixture lock."""
    lock_path = lock_for(tmp_path, make_identity())
    inputs = tmp_path / "in"
    with pytest.raises(IntegrityError, match="provider"):
        verify_run(
            lock_path,
            inputs / "calibration.jsonl",
            inputs / "verification.jsonl",
            tmp_path / "run",
            provider="jev",
            model_factory=never_called,
        )


def test_implementation_fingerprint_mismatch_is_rejected_before_the_factory(
    tmp_path: Path,
) -> None:
    lock = read_lock(lock_for(tmp_path, make_identity()))
    foreign = replace(lock, implementation_sha256="e" * 64)
    foreign = replace(foreign, sha256=lock_digest(foreign))
    (tmp_path / "foreign.json").write_bytes(canonical_json(to_data(foreign)) + b"\n")
    inputs = tmp_path / "in"
    with pytest.raises(IntegrityError, match="implementation_sha256"):
        verify_run(
            tmp_path / "foreign.json",
            inputs / "calibration.jsonl",
            inputs / "verification.jsonl",
            tmp_path / "run",
            provider="fixture",
            model_factory=never_called,
        )


def test_broken_seal_and_changed_inputs_are_rejected_before_the_factory(tmp_path: Path) -> None:
    lock = read_lock(lock_for(tmp_path, make_identity()))
    inputs = tmp_path / "in"
    tampered = replace(lock, sha256="f" * 64)
    (tmp_path / "tampered.json").write_bytes(canonical_json(to_data(tampered)) + b"\n")
    with pytest.raises(IntegrityError, match="sha256"):
        verify_run(
            tmp_path / "tampered.json",
            inputs / "calibration.jsonl",
            inputs / "verification.jsonl",
            tmp_path / "run",
            provider="fixture",
            model_factory=never_called,
        )
    changed = verification_jsonl(newline="\r\n")
    (tmp_path / "crlf.jsonl").write_bytes(changed.encode("utf-8"))
    with pytest.raises(IntegrityError, match="verification_sha256"):
        verify_run(
            tmp_path / "lock.json",
            inputs / "calibration.jsonl",
            tmp_path / "crlf.jsonl",
            tmp_path / "run",
            provider="fixture",
            model_factory=never_called,
        )
    assert not (tmp_path / "run").exists()


def test_crlf_inputs_round_trip_through_verify_and_replay(tmp_path: Path) -> None:
    verification = verification_jsonl(newline="\r\n")
    lock_path = lock_for(tmp_path, make_identity(), verification=verification)
    inputs = tmp_path / "in"
    model = ScriptedModel(make_identity(), gold_script)
    bundle, out = verify_run(
        lock_path,
        inputs / "calibration.jsonl",
        inputs / "verification.jsonl",
        tmp_path / "run",
        provider="fixture",
        model_factory=lambda: model,
    )
    assert (out / "verification.jsonl").read_bytes() == verification.encode("utf-8")
    assert b"\r\n" in (out / "verification.jsonl").read_bytes()
    assert replay(out) == bundle.verdict


@pytest.mark.parametrize("kind", ["file", "directory", "dangling-symlink"])
def test_existing_destination_is_refused_before_the_factory(tmp_path: Path, kind: str) -> None:
    lock_path = lock_for(tmp_path, make_identity())
    inputs = tmp_path / "in"
    destination = tmp_path / "run"
    if kind == "file":
        destination.write_text("x", encoding="utf-8")
    elif kind == "directory":
        destination.mkdir()
    else:
        destination.symlink_to(tmp_path / "missing")
    before = os.lstat(destination)
    with pytest.raises(FileExistsError):
        verify_run(
            lock_path,
            inputs / "calibration.jsonl",
            inputs / "verification.jsonl",
            destination,
            provider="fixture",
            model_factory=never_called,
        )
    assert os.lstat(destination) == before


def test_destination_argument_misuse_is_schema_error(tmp_path: Path) -> None:
    lock_path = lock_for(tmp_path, make_identity())
    inputs = tmp_path / "in"
    for destination in (tmp_path / "nul\x00run", tmp_path / "missing-parent" / "run"):
        with pytest.raises(SchemaError, match="destination"):
            verify_run(
                lock_path,
                inputs / "calibration.jsonl",
                inputs / "verification.jsonl",
                destination,
                provider="fixture",
                model_factory=never_called,
            )
    with pytest.raises(SchemaError, match="destination"):
        verify_run(
            lock_path,
            inputs / "calibration.jsonl",
            inputs / "verification.jsonl",
            "run",  # type: ignore[arg-type]
            provider="fixture",
            model_factory=never_called,
        )


def test_publication_failure_closes_the_provider_and_leaves_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock_path = lock_for(tmp_path, make_identity())
    inputs = tmp_path / "in"
    model = ScriptedModel(make_identity(), gold_script)

    def failing_publish(*_args: object, **_kwargs: object) -> Path:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(runner_module, "write_bundle", failing_publish)
    with pytest.raises(OSError, match="No space"):
        verify_run(
            lock_path,
            inputs / "calibration.jsonl",
            inputs / "verification.jsonl",
            tmp_path / "run",
            provider="fixture",
            model_factory=lambda: model,
        )
    assert model.closed == 1
    assert len(model.calls) == len(GOLD)
    assert not (tmp_path / "run").exists()


def test_identity_failure_closes_the_provider(tmp_path: Path) -> None:
    lock_path = lock_for(tmp_path, make_identity())
    inputs = tmp_path / "in"

    class Broken(ScriptedModel):
        def identity(self) -> ModelIdentity:
            raise RuntimeError("identity exploded")

    model = Broken(make_identity(), gold_script)
    with pytest.raises(RuntimeError):
        verify_run(
            lock_path,
            inputs / "calibration.jsonl",
            inputs / "verification.jsonl",
            tmp_path / "run",
            provider="fixture",
            model_factory=lambda: model,
        )
    assert model.closed == 1
    assert model.calls == []


def test_collect_rejects_misuse() -> None:
    model = ScriptedModel(make_identity(), gold_script)
    with pytest.raises(SchemaError, match="lock"):
        collect(model, "lock", ())  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# lock
# --------------------------------------------------------------------------- #


def test_lock_run_observes_identity_closes_and_writes_exclusively(tmp_path: Path) -> None:
    inputs = write_inputs(tmp_path / "in")
    model = ScriptedModel(make_identity(), gold_script)
    out = tmp_path / "lock.json"
    lock = lock_run(
        inputs["contract"],
        inputs["calibration"],
        inputs["verification"],
        out,
        model_factory=lambda: model,
    )
    assert model.closed == 1
    assert model.calls == []  # lock creation performs no model call
    assert lock.model_identity == make_identity()
    assert lock.implementation_sha256 == implementation_fingerprint()
    data = out.read_bytes()
    assert data == canonical_json(to_data(lock)) + b"\n"
    assert read_lock(out) == lock
    assert parse_cases(read_input_text(inputs["verification"]), lock.contract.question) == (
        lock.verification_cases
    )
    other = ScriptedModel(make_identity(), gold_script)
    with pytest.raises(FileExistsError):
        lock_run(
            inputs["contract"],
            inputs["calibration"],
            inputs["verification"],
            out,
            model_factory=lambda: other,
        )
    assert out.read_bytes() == data
    assert other.closed == 0  # refused before any provider was built


def test_lock_run_closes_the_provider_when_identity_fails(tmp_path: Path) -> None:
    inputs = write_inputs(tmp_path / "in")

    class Broken(ScriptedModel):
        def identity(self) -> ModelIdentity:
            raise ProviderSetupError("identity unavailable")

    model = Broken(make_identity(), gold_script)
    with pytest.raises(ProviderSetupError):
        lock_run(
            inputs["contract"],
            inputs["calibration"],
            inputs["verification"],
            tmp_path / "lock.json",
            model_factory=lambda: model,
        )
    assert model.closed == 1
    assert not (tmp_path / "lock.json").exists()


def test_lock_run_rejects_invalid_inputs_before_the_factory(tmp_path: Path) -> None:
    inputs = write_inputs(tmp_path / "in")
    inputs["contract"].write_text("not = [toml", encoding="utf-8")
    with pytest.raises(SchemaError):
        lock_run(
            inputs["contract"],
            inputs["calibration"],
            inputs["verification"],
            tmp_path / "lock.json",
            model_factory=never_called,
        )
    inputs = write_inputs(tmp_path / "malformed", verification='{"case_id": "v-1"}\n')
    with pytest.raises(SchemaError, match="cases"):
        lock_run(
            inputs["contract"],
            inputs["calibration"],
            inputs["verification"],
            tmp_path / "lock2.json",
            model_factory=never_called,
        )
    inputs = write_inputs(tmp_path / "leak", verification=CALIBRATION)
    model = ScriptedModel(make_identity(), gold_script)
    with pytest.raises(SchemaError, match="verification"):
        lock_run(
            inputs["contract"],
            inputs["calibration"],
            inputs["verification"],
            tmp_path / "lock3.json",
            model_factory=lambda: model,
        )
    assert model.closed == 1
    assert not (tmp_path / "lock3.json").exists()
    with pytest.raises(FileNotFoundError):
        lock_run(
            tmp_path / "absent.toml",
            inputs["calibration"],
            inputs["verification"],
            tmp_path / "lock4.json",
            model_factory=never_called,
        )


def test_write_lock_refuses_symlinks_and_misuse(tmp_path: Path) -> None:
    lock = read_lock(lock_for(tmp_path, make_identity()))
    link = tmp_path / "link.json"
    link.symlink_to(tmp_path / "absent.json")
    with pytest.raises(FileExistsError):
        write_lock(lock, link)
    assert not (tmp_path / "absent.json").exists()
    with pytest.raises(SchemaError, match="lock"):
        write_lock("lock", tmp_path / "x.json")  # type: ignore[arg-type]
    with pytest.raises(SchemaError, match="destination"):
        write_lock(lock, tmp_path / "nul\x00.json")


# --------------------------------------------------------------------------- #
# open_model
# --------------------------------------------------------------------------- #


def test_open_model_fixture_rules(tmp_path: Path) -> None:
    responses = gold_responses(tmp_path / "responses.jsonl")
    model = open_model("fixture", responses=responses, offline=False)
    assert isinstance(model, FixtureModel)
    assert model.identity() == FixtureModel(responses).identity()
    model.close()
    with pytest.raises(SchemaError, match="responses"):
        open_model("fixture", responses=None, offline=False)
    with pytest.raises(SchemaError, match="responses"):
        open_model("fixture", responses=None, offline=True)
    # --offline states the fixture adapter's existing behavior; it changes nothing.
    offline = open_model("fixture", responses=responses, offline=True)
    assert isinstance(offline, FixtureModel)
    assert offline.identity() == model.identity()
    offline.close()
    with pytest.raises(SchemaError, match="provider"):
        open_model("unsupported", responses=None, offline=False)
    with pytest.raises(SchemaError, match="provider"):
        open_model("jev", responses=None, offline=False)


def test_open_model_rejects_admitted_but_unregistered_jev_without_constructing_laya(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """V1-011 guard: ``jev`` is admitted by ``records.PROVIDERS`` but not registered here.

    Before the guard the non-fixture branch would have constructed Laya for any
    admitted provider. Every argument combination must fail loudly with a
    ``SchemaError`` naming ``provider`` and construct nothing.
    """
    constructed: list[dict[str, object]] = []

    class FakeLaya:
        def __init__(self, *, offline: bool = False) -> None:
            constructed.append({"offline": offline})

    monkeypatch.setattr(laya_module, "LayaModel", FakeLaya)
    for responses in (None, tmp_path / "r.jsonl"):
        for offline in (True, False):
            with pytest.raises(SchemaError, match="provider") as excinfo:
                open_model("jev", responses=responses, offline=offline)
            assert "not registered" in str(excinfo.value)
    assert constructed == []
    # The registered providers are exactly the stable CLI choices until Task 19.
    assert sorted(runner_module._REGISTERED_PROVIDERS) == ["fixture", "laya"]


def test_open_model_jev_rejection_imports_no_adapter_in_a_fresh_interpreter() -> None:
    """The guard fires before any adapter import: a blocked import never happens."""
    script = (
        "import importlib.abc, sys\n"
        "class Deny(importlib.abc.MetaPathFinder):\n"
        "    def find_spec(self, name, path=None, target=None):\n"
        "        if name.startswith(('actseal.adapters.', 'actseal.experimental')):\n"
        "            raise ImportError('adapter import attempted: ' + name)\n"
        "        return None\n"
        "sys.meta_path.insert(0, Deny())\n"
        "from actseal.errors import SchemaError\n"
        "from actseal.runner import open_model\n"
        "for offline in (True, False):\n"
        "    try:\n"
        "        open_model('jev', responses=None, offline=offline)\n"
        "    except SchemaError as exc:\n"
        "        assert 'provider' in str(exc), str(exc)\n"
        "    else:\n"
        "        raise SystemExit('jev was constructed')\n"
        "loaded = sorted(m for m in sys.modules if m.startswith("
        "('actseal.adapters.', 'actseal.experimental', 'laya', 'torch')))\n"
        "print(loaded)\n"
    )
    result = subprocess.run(  # noqa: S603 - fixed interpreter and literal script, no user input
        [sys.executable, "-I", "-c", script],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    assert result.stdout.strip() == "[]"


def test_open_model_laya_rules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    constructed: list[dict[str, object]] = []

    class FakeLaya:
        def __init__(self, *, offline: bool = False) -> None:
            constructed.append({"offline": offline})

    monkeypatch.setattr(laya_module, "LayaModel", FakeLaya)
    with pytest.raises(SchemaError, match="responses"):
        open_model("laya", responses=tmp_path / "r.jsonl", offline=False)
    assert constructed == []
    open_model("laya", responses=None, offline=True)
    open_model("laya", responses=None, offline=False)
    assert constructed == [{"offline": True}, {"offline": False}]


# --------------------------------------------------------------------------- #
# demo: genuine ADR 0013 results from the real pipeline
# --------------------------------------------------------------------------- #


def test_demo_run_produces_the_prespecified_block_and_pass(tmp_path: Path) -> None:
    result = demo_run(tmp_path / "demo")
    assert tuple(run.name for run in result.runs) == DEMO_RUNS == ("bad", "fixed")
    assert result.succeeded
    assert result.duration_s >= 0.0
    bad, fixed = result.runs
    assert bad.expected_status == DEMO_EXPECTED["bad"] == "BLOCK"
    assert fixed.expected_status == DEMO_EXPECTED["fixed"] == "PASS"
    for run in result.runs:
        assert run.verdict == assess(run.bundle.records, run.lock, run.bundle.faults)
        assert run.replayed == run.verdict
        assert run.replayed == replay(run.bundle_path, expected_lock_sha256=run.lock.sha256)
        assert run.verdict.evidence_scope == "demo"
        assert run.lock.contract.evidence_scope == "demo"
        assert run.lock.model_identity.provider == "fixture"
        assert run.lock.implementation_sha256 == implementation_fingerprint()
        assert (run.verdict.total, run.verdict.accepted) == (128, 128)
        assert len(run.lock.calibration_inventory) == 12
        assert len(run.bundle.faults) == 6
        assert all(
            f.decision.action == s.expected_action
            for f, s in zip(run.bundle.faults, run.lock.fault_inventory, strict=True)
        )
        assert all(record.decision.action == "ACT" for record in run.bundle.records)
        assert read_lock(run.lock_path) == run.lock
    assert bad.verdict.status == "BLOCK"
    assert bad.verdict.reasons == ("risk.exceeds_limit",)
    assert bad.verdict.errors == 32
    assert bad.verdict.risk.lower > bad.lock.contract.limits.max_risk
    assert fixed.verdict.status == "PASS"
    assert fixed.verdict.reasons == ("contract.satisfied",)
    assert fixed.verdict.errors == 0
    assert fixed.verdict.risk.upper <= fixed.lock.contract.limits.max_risk
    assert fixed.verdict.coverage.lower >= fixed.lock.contract.limits.min_coverage
    assert bad.lock.contract.policy == fixed.lock.contract.policy
    assert bad.lock.contract.limits == fixed.lock.contract.limits
    assert bad.lock.sha256 != fixed.lock.sha256


def test_demo_layout_is_self_contained_and_reproducible(tmp_path: Path) -> None:
    first = demo_run(tmp_path / "one")
    second = demo_run(tmp_path / "two")
    assert tree(tmp_path / "one") == tree(tmp_path / "two")
    root = tmp_path / "one"
    assert sorted(p.name for p in root.iterdir()) == ["bad", "fixed", DEMO_INPUTS_DIRECTORY]
    inputs = root / DEMO_INPUTS_DIRECTORY
    assert sorted(p.name for p in inputs.iterdir()) == sorted(RESOURCE_NAMES)
    for name in RESOURCE_NAMES:
        assert (inputs / name).read_bytes() == (PACKAGED / name).read_bytes()
    for run in first.runs:
        assert run.lock_path == root / run.name / LOCK_FILE_NAME
        assert run.bundle_path == root / run.name / EVIDENCE_DIRECTORY
        assert sorted(p.name for p in (root / run.name).iterdir()) == [
            EVIDENCE_DIRECTORY,
            LOCK_FILE_NAME,
        ]
        assert sorted(p.name for p in run.bundle_path.iterdir()) == sorted(BUNDLE_FILES)
    assert [run.lock.sha256 for run in first.runs] == [run.lock.sha256 for run in second.runs]


def test_demo_refuses_existing_destinations_and_writes_nothing(tmp_path: Path) -> None:
    existing = tmp_path / "exists"
    existing.mkdir()
    with pytest.raises(FileExistsError):
        demo_run(existing)
    assert list(existing.iterdir()) == []
    dangling = tmp_path / "dangling"
    dangling.symlink_to(tmp_path / "nowhere")
    with pytest.raises(FileExistsError):
        demo_run(dangling)
    assert not (tmp_path / "nowhere").exists()
    with pytest.raises(SchemaError, match="parent"):
        demo_run(tmp_path / "missing" / "demo")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["dangling", "exists"]


def test_demo_run_failure_is_reported_not_hidden(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If an expected status were not met, success must be false (no hard-coded outcome)."""
    monkeypatch.setitem(runner_module.DEMO_EXPECTED, "bad", "PASS")
    result = demo_run(tmp_path / "demo")
    assert not result.succeeded
    assert result.runs[0].verdict.status == "BLOCK"
    assert not result.runs[0].as_expected
    assert result.runs[1].as_expected


# --------------------------------------------------------------------------- #
# ADR 0013 resources: structure, parity and reproducibility
# --------------------------------------------------------------------------- #


def load_cases(name: str) -> tuple[tuple[str, str, str], ...]:
    text = (PACKAGED / name).read_text(encoding="utf-8")
    rows = [json.loads(line) for line in text.split("\n") if line]
    return tuple((row["case_id"], row["state"], row["expected_label"]) for row in rows)


def load_responses(name: str) -> dict[str, dict[str, object]]:
    text = (PACKAGED / name).read_text(encoding="utf-8")
    rows = [json.loads(line) for line in text.split("\n") if line]
    return {row["case_id"]: row for row in rows}


def test_demo_resources_follow_the_prespecified_rules() -> None:
    all_ids: list[str] = []
    all_states: list[str] = []
    contracts = {run: parse_contract(PACKAGED / f"{run}.toml") for run in DEMO_RUNS}
    assert contracts["bad"].policy == contracts["fixed"].policy
    assert contracts["bad"].limits == contracts["fixed"].limits
    assert contracts["bad"].question == contracts["fixed"].question
    assert contracts["bad"].name != contracts["fixed"].name
    policy = contracts["bad"].policy
    assert policy.known_labels == policy.allowed_labels == LABELS
    assert policy.threshold == 0.9
    assert (contracts["bad"].limits.max_risk, contracts["bad"].limits.min_coverage) == (0.05, 0.5)
    assert contracts["bad"].limits.alpha == 0.05
    assert {c.evidence_scope for c in contracts.values()} == {"demo"}
    for run in DEMO_RUNS:
        calibration = load_cases(f"{run}_calibration.jsonl")
        verification = load_cases(f"{run}_verification.jsonl")
        assert len(calibration) == 12
        assert len(verification) == 128
        for cases in (calibration, verification):
            for index, (_, _, label) in enumerate(cases):
                assert label == LABELS[index % 3]
            all_ids.extend(cid for cid, _, _ in cases)
            all_states.extend(state for _, state, _ in cases)
        responses = load_responses(f"{run}_responses.jsonl")
        assert list(responses) == [cid for cid, _, _ in verification]
        wrong = 0
        for index, (cid, _, gold) in enumerate(verification):
            row = responses[cid]
            assert row["failure_code"] is None
            assert row["warnings"] == []
            body = json.loads(str(row["body_json"]))
            assert set(body) == {"type", "choice", "probabilities"}
            selected = body["choice"]
            expected = LABELS[(index + 1) % 3] if run == "bad" and index < 32 else gold
            assert selected == expected
            wrong += selected != gold
            following = LABELS[(LABELS.index(selected) + 1) % 3]
            assert body["probabilities"] == {
                label: 0.95 if label == selected else 0.03 if label == following else 0.02
                for label in LABELS
            }
            assert list(body["probabilities"]) == list(LABELS)
        assert wrong == (32 if run == "bad" else 0)
    assert len(set(all_ids)) == len(all_ids) == 2 * (128 + 12)
    assert len(set(all_states)) == len(all_states)


def test_packaged_and_example_resources_are_byte_identical() -> None:
    shipped = [p.name for p in PACKAGED.iterdir() if p.is_file() and p.name != "__init__.py"]
    assert sorted(shipped) == sorted(RESOURCE_NAMES)
    for name in RESOURCE_NAMES:
        assert (PACKAGED / name).read_bytes() == (EXAMPLES / name).read_bytes(), name


def test_generator_reproduces_the_committed_resources(tmp_path: Path) -> None:
    out = tmp_path / "generated"
    result = subprocess.run(  # noqa: S603 - fixed interpreter and repository script
        [sys.executable, str(GENERATOR), str(out)],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert sorted(p.name for p in out.iterdir()) == sorted(RESOURCE_NAMES)
    for name in RESOURCE_NAMES:
        assert (out / name).read_bytes() == (PACKAGED / name).read_bytes(), name
    again = subprocess.run(  # noqa: S603 - fixed interpreter and repository script
        [sys.executable, str(GENERATOR), str(out)],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert again.returncode != 0  # never overwrites committed-style files


def test_demo_contract_toml_matches_the_frozen_shape() -> None:
    document = tomllib.loads((PACKAGED / "fixed.toml").read_text(encoding="utf-8"))
    assert set(document) == {
        "schema_version",
        "name",
        "evidence_scope",
        "population",
        "question",
        "policy",
        "risk",
    }
    assert document["risk"] == {"max_risk": 0.05, "min_coverage": 0.5, "alpha": 0.05}
    assert document["policy"] == {"allowed_labels": list(LABELS), "threshold": 0.9}


def test_demo_fault_campaign_is_the_frozen_inventory(tmp_path: Path) -> None:
    result = demo_run(tmp_path / "demo")
    for run in result.runs:
        assert run.bundle.faults == run_fault_campaign(run.lock)
        assert [f.scenario_id for f in run.bundle.faults] == [
            "fault.timeout",
            "fault.rate_limit",
            "fault.malformed_response",
            "fault.identity_mismatch",
            "fault.unknown_choice",
            "fault.low_confidence",
        ]
