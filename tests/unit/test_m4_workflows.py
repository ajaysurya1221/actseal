"""M4 provider selection, synthetic fault scope and offline evidence round trips."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from actseal.cli import main
from actseal.errors import SchemaError
from actseal.evidence import decode_rows, read_bundle_files
from actseal.records import FaultResult
from actseal.runner import open_model

PACKAGED = Path(__file__).resolve().parents[2] / "src" / "actseal" / "demo_data"
NOTE = "recorded: provider faults not tested"


def test_recorded_cli_round_trip_keeps_six_synthetic_checks_and_replay_note(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    responses = tmp_path / "predictions.jsonl"
    cases = [
        json.loads(line)
        for line in (PACKAGED / "fixed_verification.jsonl").read_text().splitlines()
    ]
    responses.write_text(
        "".join(
            json.dumps({"case_id": row["case_id"], "choice": row["expected_label"], "score": 1.0})
            + "\n"
            for row in cases
        ),
        encoding="utf-8",
    )
    common = [
        "--calibration",
        str(PACKAGED / "fixed_calibration.jsonl"),
        "--verification",
        str(PACKAGED / "fixed_verification.jsonl"),
        "--provider",
        "recorded",
        "--responses",
        str(responses),
        "--model",
        "user-model",
        "--revision",
        "user-revision",
        "--json",
    ]
    lock = tmp_path / "lock.json"
    assert (
        main(["lock", "--contract", str(PACKAGED / "fixed.toml"), *common, "--out", str(lock)]) == 0
    )
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["model_identity"]["model"] == "user-model"
    assert receipt["model_identity"]["revision"] == "user-revision"
    bundle = tmp_path / "bundle"
    assert main(["verify", "--lock", str(lock), *common, "--out", str(bundle)]) == 0
    verified = json.loads(capsys.readouterr().out)
    assert verified["status"] == "PASS"
    assert verified["total"] == verified["accepted"] == len(cases)
    assert verified["errors"] == 0
    assert verified["warnings"][NOTE] == len(cases)
    assert len(verified["faults"]) == 6
    assert all(value["action"] == value["expected_action"] for value in verified["faults"].values())
    faults = decode_rows("faults.jsonl", read_bundle_files(bundle)["faults.jsonl"], FaultResult)
    assert all(fault.capture.warnings == (NOTE,) for fault in faults)
    low = next(fault for fault in faults if fault.scenario_id == "fault.low_confidence")
    assert json.loads(low.capture.body_json or "null")["score"] == 0.0
    assert main(["replay", str(bundle), "--json"]) == 0
    replayed = json.loads(capsys.readouterr().out)
    assert replayed["notes"] == [NOTE]
    for name in ("status", "reasons", "total", "accepted", "errors", "risk", "coverage"):
        assert replayed[name] == verified[name]


@pytest.mark.parametrize("missing", ["--responses", "--model", "--revision"])
def test_recorded_requires_identity_and_predictions_before_reading_inputs(
    missing: str, capsys: pytest.CaptureFixture[str]
) -> None:
    args = [
        "lock",
        "--contract",
        "absent",
        "--calibration",
        "absent",
        "--verification",
        "absent",
        "--out",
        "absent",
        "--provider",
        "recorded",
        "--responses",
        "absent",
        "--model",
        "name",
        "--revision",
        "revision",
        "--json",
    ]
    index = args.index(missing)
    del args[index : index + 2]
    assert main(args) == 3
    assert f"{missing} is required" in json.loads(capsys.readouterr().out)["error"]


@pytest.mark.parametrize(
    "missing", ["--experimental-provider", "--endpoint", "--model", "--revision"]
)
def test_decision_api_requires_explicit_inputs_before_reading_files(
    missing: str, capsys: pytest.CaptureFixture[str]
) -> None:
    args = [
        "lock",
        "--contract",
        "absent",
        "--calibration",
        "absent",
        "--verification",
        "absent",
        "--out",
        "absent",
        "--provider",
        "decision-api",
        "--experimental-provider",
        "--endpoint",
        "http://localhost:8123/v1/systemone",
        "--model",
        "name",
        "--revision",
        "revision",
        "--json",
    ]
    index = args.index(missing)
    del args[index : index + (1 if missing == "--experimental-provider" else 2)]
    assert main(args) == 3
    assert f"{missing} is required" in json.loads(capsys.readouterr().out)["error"]


def test_open_model_decision_api_locks_endpoint_model_and_revision() -> None:
    model = open_model(
        "decision-api",
        responses=None,
        offline=False,
        endpoint="http://localhost:8123/v1/systemone",
        model="local-model",
        revision="weights-v1",
    )
    try:
        identity = model.identity()
        assert identity.provider == "decision-api"
        assert identity.model == "local-model"
        assert identity.revision == "weights-v1"
        assert dict(identity.runtime)["endpoint"] == "http://localhost:8123/v1/systemone"
    finally:
        model.close()


def test_existing_provider_rejects_new_options_before_adapter_import() -> None:
    with pytest.raises(SchemaError, match="model"):
        open_model("fixture", responses=Path("absent"), offline=True, model="ignored")
