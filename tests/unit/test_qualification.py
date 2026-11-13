"""Selection sidecars bind inputs, preserve split isolation and replay captured data."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from actseal import qualification
from actseal.adapters.fixture import FixtureModel
from actseal.cli import main
from actseal.compatibility import CURRENT_ENGINE, CompatibilityRegistry
from actseal.errors import IntegrityError, SchemaError
from actseal.qualification import calibrate_run, qualify_run, replay_selection
from actseal.records import CapturedOutcome, DecisionRequest
from actseal.serialization import canonical_json, implementation_fingerprint, sha256_bytes

TEMPLATE = """schema_version = 1
name = "synthetic-qualification"
evidence_scope = "demo"
population = "Authored synthetic cases only"
[question]
question_id = "q"
instructions = "Choose a label."
options = [{label="yes",description="Yes"},{label="no",description="No"}]
[policy]
allowed_labels = ["yes"]
threshold = 0.99
[risk]
max_risk = 0.2
min_coverage = 0.5
alpha = 0.05
"""


def inputs(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    contract = tmp_path / "input.toml"
    contract.write_text(TEMPLATE)
    responses: list[dict[str, object]] = []
    paths: list[Path] = []
    for split, count in (("cal", 64), ("ver", 100)):
        path = tmp_path / f"{split}.jsonl"
        cases = []
        for index in range(count):
            case_id = f"{split}-{index}"
            cases.append({"case_id": case_id, "state": case_id, "expected_label": "yes"})
            responses.append(
                {
                    "case_id": case_id,
                    "body_json": json.dumps(
                        {
                            "type": "choice",
                            "choice": "yes",
                            "probabilities": {"yes": 0.95, "no": 0.05},
                        }
                    ),
                    "failure_code": None,
                    "warnings": [],
                }
            )
        path.write_bytes(b"".join(canonical_json(row) + b"\n" for row in cases))
        paths.append(path)
    recording = tmp_path / "responses.jsonl"
    recording.write_bytes(b"".join(canonical_json(row) + b"\n" for row in responses))
    return contract, paths[0], paths[1], recording


def reseal(directory: Path, name: str, value: Any) -> None:
    """Model an author updating the hashes; semantic checks must still run."""
    data = canonical_json(value) + b"\n"
    (directory / name).write_bytes(data)
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["files"][name] = {"size": len(data), "sha256": sha256_bytes(data)}
    del manifest["sha256"]
    manifest["sha256"] = sha256_bytes(canonical_json(manifest))
    manifest_path.write_bytes(canonical_json(manifest) + b"\n")


def test_qualification_pass_and_offline_selection(tmp_path: Path) -> None:
    contract, cal, ver, responses = inputs(tmp_path)
    result = qualify_run(
        contract,
        cal,
        ver,
        tmp_path / "out",
        provider="fixture",
        model_factory=lambda: FixtureModel(responses),
    )
    assert result.bundle is not None
    assert result.bundle.verdict.status == "PASS"
    assert result.bundle.verdict.total == 100
    assert result.calibration.selection.threshold == 0.95
    assert replay_selection(tmp_path / "out" / "calibration") == result.calibration.selection
    assert result.receipt_path is not None
    receipt = json.loads(result.receipt_path.read_bytes())
    assert receipt["calibration_manifest_sha256"] == sha256_bytes(
        (tmp_path / "out" / "calibration" / "manifest.json").read_bytes()
    )
    assert receipt["lock_sha256"] == result.bundle.lock.sha256


@pytest.mark.parametrize("missing", [None, "producer", "running"])
def test_selection_replay_requires_exact_source_or_both_registered(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    missing: str | None,
) -> None:
    contract, cal, ver, responses = inputs(tmp_path)
    result = calibrate_run(
        contract, cal, ver, tmp_path / "out", model_factory=lambda: FixtureModel(responses)
    )
    directory = tmp_path / "out" / "calibration"
    plan = json.loads((directory / "selection_plan.json").read_bytes())
    producer, running = "f" * 64, implementation_fingerprint()
    assert plan["implementation_sha256"] == running
    assert plan["replay_engine_version"] == CURRENT_ENGINE
    plan["implementation_sha256"] = producer
    del plan["sha256"]
    plan["sha256"] = sha256_bytes(canonical_json(plan))
    reseal(directory, "selection_plan.json", plan)
    registered = {"producer": producer, "running": running}
    registry = CompatibilityRegistry(
        1,
        tuple(
            sorted((value, CURRENT_ENGINE) for side, value in registered.items() if side != missing)
        ),
    )
    monkeypatch.setattr("actseal.compatibility.load_registry", lambda: registry)
    code = main(["replay-selection", str(directory), "--json"])
    stdout, stderr = capsys.readouterr()
    assert stderr == ""
    assert code == (0 if missing is None else 3)
    if missing is None:
        assert replay_selection(directory) == result.selection
    else:
        assert "approved compatible implementation" in stdout


def test_selection_exact_source_does_not_load_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contract, cal, ver, responses = inputs(tmp_path)
    result = calibrate_run(
        contract, cal, ver, tmp_path / "out", model_factory=lambda: FixtureModel(responses)
    )

    def unavailable() -> CompatibilityRegistry:
        raise AssertionError("exact-source replay must not load the registry")

    monkeypatch.setattr("actseal.compatibility.load_registry", unavailable)
    assert replay_selection(tmp_path / "out" / "calibration") == result.selection


def test_selection_collection_rejects_registered_foreign_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contract, cal, ver, responses = inputs(tmp_path)
    calibrate_run(
        contract, cal, ver, tmp_path / "out", model_factory=lambda: FixtureModel(responses)
    )
    plan = qualification._decode_plan(
        (tmp_path / "out" / "calibration" / "selection_plan.json").read_bytes()
    )
    foreign = replace(plan, implementation_sha256="f" * 64)
    registry = CompatibilityRegistry(
        1, (("f" * 64, CURRENT_ENGINE), (implementation_fingerprint(), CURRENT_ENGINE))
    )
    monkeypatch.setattr("actseal.compatibility.load_registry", lambda: registry)
    model = FixtureModel(responses)
    try:
        with pytest.raises(IntegrityError, match="new collection requires the exact"):
            qualification._collect_calibration(model, foreign, ())
    finally:
        model.close()


def test_no_threshold_never_collects_verification(tmp_path: Path) -> None:
    contract, cal, ver, responses = inputs(tmp_path)
    # No verification responses exist: collecting even one would fail setup.
    rows = responses.read_text().splitlines()[:64]
    responses.write_text("\n".join(rows) + "\n")
    result = qualify_run(
        contract,
        cal,
        ver,
        tmp_path / "out",
        provider="fixture",
        model_factory=lambda: FixtureModel(responses),
        grid=(1.0,),
    )
    assert result.bundle is None
    assert result.calibration.contract_path is None
    assert result.calibration.selection.reason == "calibration.no_threshold"
    assert replay_selection(tmp_path / "out" / "calibration").threshold is None
    assert sorted(path.name for path in (tmp_path / "out").iterdir()) == ["calibration"]


@pytest.mark.parametrize("name", ["records.jsonl", "selection_plan.json", "manifest.json"])
def test_byte_tampering_is_rejected(tmp_path: Path, name: str) -> None:
    contract, cal, ver, responses = inputs(tmp_path)
    calibrate_run(
        contract, cal, ver, tmp_path / "out", model_factory=lambda: FixtureModel(responses)
    )
    sidecar = tmp_path / "out" / "calibration"
    path = sidecar / name
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises((SchemaError, IntegrityError)):
        replay_selection(sidecar)


@pytest.mark.parametrize(("field", "value"), [("grid", [0.6, 0.95]), ("n_verify", 50)])
def test_rehashed_manifest_cannot_hide_changed_plan(tmp_path: Path, field: str, value: Any) -> None:
    contract, cal, ver, responses = inputs(tmp_path)
    calibrate_run(
        contract, cal, ver, tmp_path / "out", model_factory=lambda: FixtureModel(responses)
    )
    sidecar = tmp_path / "out" / "calibration"
    plan = json.loads((sidecar / "selection_plan.json").read_bytes())
    plan[field] = value
    reseal(sidecar, "selection_plan.json", plan)
    with pytest.raises(IntegrityError):
        replay_selection(sidecar)


def test_overlap_rejected_before_provider_construction(tmp_path: Path) -> None:
    contract, cal, _ver, _responses = inputs(tmp_path)

    def forbidden() -> FixtureModel:
        pytest.fail("provider constructed for invalid splits")

    with pytest.raises(SchemaError, match="calibration"):
        calibrate_run(contract, cal, cal, tmp_path / "out", model_factory=forbidden)
    assert not (tmp_path / "out").exists()


def test_shuffled_calibration_selection_is_identical(tmp_path: Path) -> None:
    contract, cal, ver, responses = inputs(tmp_path)
    first = calibrate_run(
        contract, cal, ver, tmp_path / "first", model_factory=lambda: FixtureModel(responses)
    )
    cal.write_text("\n".join(reversed(cal.read_text().splitlines())) + "\n")
    second = calibrate_run(
        contract, cal, ver, tmp_path / "second", model_factory=lambda: FixtureModel(responses)
    )
    assert first.selection == second.selection


def test_publication_failure_after_manifest_cleans_captures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contract, cal, ver, responses = inputs(tmp_path)

    def fail(_directory: Path) -> None:
        raise IntegrityError("injected prepublication verification failure")

    monkeypatch.setattr("actseal.qualification.replay_selection", fail)
    with pytest.raises(IntegrityError, match="injected"):
        calibrate_run(
            contract, cal, ver, tmp_path / "out", model_factory=lambda: FixtureModel(responses)
        )
    assert not list(tmp_path.glob(".actseal-selection-*"))
    assert not (tmp_path / "out").exists()


def test_grid_is_frozen_before_provider_setup(tmp_path: Path) -> None:
    contract, cal, ver, responses = inputs(tmp_path)
    grid = [0.5, 0.95]

    def factory() -> FixtureModel:
        grid[:] = [1.0]
        return FixtureModel(responses)

    result = calibrate_run(contract, cal, ver, tmp_path / "out", model_factory=factory, grid=grid)
    assert result.selection.threshold == 0.95
    assert tuple(point.threshold for point in result.selection.points) == (0.5, 0.95)


def test_derived_contract_preserves_escaped_del_and_unicode(tmp_path: Path) -> None:
    contract, cal, ver, responses = inputs(tmp_path)
    contract.write_text(TEMPLATE.replace("Authored synthetic cases only", "Unicode 😀 \\u007f"))
    result = calibrate_run(
        contract, cal, ver, tmp_path / "out", model_factory=lambda: FixtureModel(responses)
    )
    assert result.contract_path is not None


def test_late_sidecar_drift_prevents_qualification_receipt(tmp_path: Path) -> None:
    contract, cal, ver, responses = inputs(tmp_path)
    destination = tmp_path / "out"

    class Drift(FixtureModel):
        def close(self) -> None:
            super().close()
            path = destination / "calibration" / "manifest.json"
            if (destination / "evidence").exists():
                path.write_bytes(path.read_bytes() + b" ")

    with pytest.raises((SchemaError, IntegrityError)):
        qualify_run(
            contract,
            cal,
            ver,
            destination,
            provider="fixture",
            model_factory=lambda: Drift(responses),
        )
    assert not (destination / "qualification.json").exists()


def test_plan_is_written_before_capture_and_policy_controls_eligibility(tmp_path: Path) -> None:
    contract, cal, ver, responses = inputs(tmp_path)

    class SpecialCases(FixtureModel):
        def decide(self, request: DecisionRequest, *, timeout_s: float) -> CapturedOutcome:
            plans = list(tmp_path.glob(".actseal-selection-*/calibration/selection_plan.json"))
            assert len(plans) == 1
            plan = json.loads(plans[0].read_bytes())
            seal = plan.pop("sha256")
            assert seal == sha256_bytes(canonical_json(plan))
            assert "threshold" not in plan["contract"]["policy"]
            assert timeout_s == 30.0
            capture = super().decide(request, timeout_s=timeout_s)
            if request.case_id == "cal-0":
                return replace(capture, fallback_used=True)
            if request.case_id == "cal-1":
                return replace(
                    capture,
                    body_json=json.dumps(
                        {
                            "type": "choice",
                            "choice": "no",
                            "probabilities": {"yes": 0.05, "no": 0.95},
                        }
                    ),
                )
            if request.case_id == "cal-2":
                return replace(capture, body_json=None, failure_code="timeout")
            if request.case_id == "cal-3":
                return replace(
                    capture,
                    body_json=json.dumps(
                        {
                            "type": "choice",
                            "choice": "yes",
                            "probabilities": {"yes": 0.0, "no": 1.0},
                        }
                    ),
                )
            if request.case_id == "cal-4":
                return replace(
                    capture,
                    body_json=json.dumps(
                        {
                            "type": "choice",
                            "choice": "yes",
                            "probabilities": {"yes": 0.7, "no": 0.3},
                        }
                    ),
                )
            return capture

    result = calibrate_run(
        contract,
        cal,
        ver,
        tmp_path / "out",
        model_factory=lambda: SpecialCases(responses),
        grid=(0.5, 0.9),
    )
    assert [(point.accepted, point.errors) for point in result.selection.points] == [
        (60, 0),
        (59, 0),
    ]
    assert replay_selection(tmp_path / "out" / "calibration") == result.selection


@pytest.mark.parametrize("field", ["outcome", "decision", "request"])
def test_resealed_records_still_require_semantic_reproduction(tmp_path: Path, field: str) -> None:
    contract, cal, ver, responses = inputs(tmp_path)
    calibrate_run(
        contract, cal, ver, tmp_path / "out", model_factory=lambda: FixtureModel(responses)
    )
    directory = tmp_path / "out" / "calibration"
    records = [json.loads(line) for line in (directory / "records.jsonl").read_text().splitlines()]
    if field == "outcome":
        records[0]["outcome"]["selected_probability"] = 0.6
    elif field == "decision":
        records[0]["decision"]["reason"] = "policy.low_confidence"
    else:
        records[0]["capture"]["request_sha256"] = "0" * 64
    raw = b"".join(canonical_json(row) + b"\n" for row in records)
    (directory / "records.jsonl").write_bytes(raw)
    manifest = json.loads((directory / "manifest.json").read_bytes())
    manifest["files"]["records.jsonl"] = {"size": len(raw), "sha256": sha256_bytes(raw)}
    del manifest["sha256"]
    manifest["sha256"] = sha256_bytes(canonical_json(manifest))
    (directory / "manifest.json").write_bytes(canonical_json(manifest) + b"\n")
    with pytest.raises((SchemaError, IntegrityError)):
        replay_selection(directory)


def test_probability_tolerance_never_applies_to_selected_threshold(tmp_path: Path) -> None:
    contract, cal, ver, responses = inputs(tmp_path)
    result = calibrate_run(
        contract, cal, ver, tmp_path / "out", model_factory=lambda: FixtureModel(responses)
    )
    directory = tmp_path / "out" / "calibration"
    selection = json.loads((directory / "selection.json").read_bytes())
    selection["points"][0]["predicted_pass_probability"] += 1e-11
    reseal(directory, "selection.json", selection)
    assert replay_selection(directory) == result.selection
    selection["threshold"] += 1e-11
    reseal(directory, "selection.json", selection)
    with pytest.raises(IntegrityError, match="threshold"):
        replay_selection(directory)


@pytest.mark.parametrize("kind", ["extra", "symlink", "missing", "budget"])
def test_sidecar_inventory_and_budget_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    contract, cal, ver, responses = inputs(tmp_path)
    calibrate_run(
        contract, cal, ver, tmp_path / "out", model_factory=lambda: FixtureModel(responses)
    )
    directory = tmp_path / "out" / "calibration"
    if kind == "extra":
        (directory / "unexpected").touch()
    elif kind == "budget":
        monkeypatch.setattr("actseal.qualification.MAX_BUNDLE_BYTES", 10)
    else:
        target = directory / "calibration.jsonl"
        target.unlink()
        if kind == "symlink":
            target.symlink_to(cal)
    with pytest.raises(SchemaError):
        replay_selection(directory)
