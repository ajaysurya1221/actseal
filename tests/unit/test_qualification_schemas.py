"""The opt-in calibration documents have strict, separately versioned schemas."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from test_evidence import make_bundle

from actseal.cli import main
from actseal.serialization import to_data

SCHEMAS = Path(__file__).resolve().parents[2] / "docs" / "schemas"
SIDECAR_SCHEMAS = (
    "selection-plan.schema.json",
    "selection.schema.json",
    "calibration-manifest.schema.json",
    "qualification.schema.json",
)
HASH = "a" * 64


def _schema(name: str) -> dict[str, Any]:
    value: dict[str, Any] = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
    return value


def _documents() -> dict[str, dict[str, Any]]:
    bundle = make_bundle()
    contract = to_data(bundle.lock.contract)
    policy = contract["policy"]
    assert isinstance(policy, dict)
    del policy["threshold"]
    return {
        "selection-plan.schema.json": {
            "schema_version": 1,
            "contract": contract,
            "grid": [0.5, 0.9],
            "target_pass_probability": 0.8,
            "selection_tail": 0.05,
            "n_verify": 128,
            "calibration_sha256": HASH,
            "verification_sha256": HASH,
            "model_identity": to_data(bundle.lock.model_identity),
            "implementation_sha256": HASH,
            "replay_engine_version": "actseal-choice-v1",
            "sha256": HASH,
        },
        "selection.schema.json": {
            "schema_version": 1,
            "threshold": 0.9,
            "reason": "selected",
            "points": [
                {
                    "threshold": 0.9,
                    "accepted": 128,
                    "errors": 0,
                    "predicted_pass_probability": 0.9,
                }
            ],
        },
        "calibration-manifest.schema.json": {
            "schema_version": 1,
            "files": {
                name: {"size": 1, "sha256": HASH}
                for name in (
                    "selection_plan.json",
                    "calibration.jsonl",
                    "records.jsonl",
                    "selection.json",
                )
            },
            "sha256": HASH,
        },
        "qualification.schema.json": {
            "schema_version": 1,
            "calibration_manifest_sha256": HASH,
            "lock_sha256": bundle.lock.sha256,
            "verdict": to_data(bundle.verdict),
        },
    }


@pytest.mark.parametrize("name", SIDECAR_SCHEMAS)
def test_sidecar_schema_validates_document_and_rejects_extra_fields(name: str) -> None:
    schema = _schema(name)
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    validator = Draft202012Validator(schema)
    document = _documents()[name]
    validator.validate(document)
    assert not validator.is_valid({**document, "extra": True})
    assert not validator.is_valid({**document, "schema_version": 2})


@pytest.mark.parametrize("grid", [[], [0.0], [1.1], [0.5] * 33, [True]])
def test_plan_schema_rejects_out_of_domain_grid(grid: list[float]) -> None:
    document = _documents()["selection-plan.schema.json"]
    document["grid"] = grid
    assert not Draft202012Validator(_schema("selection-plan.schema.json")).is_valid(document)


def test_plan_schema_excludes_threshold_and_requires_complete_identity() -> None:
    document = _documents()["selection-plan.schema.json"]
    validator = Draft202012Validator(_schema("selection-plan.schema.json"))
    changed = copy.deepcopy(document)
    changed["contract"]["policy"]["threshold"] = 0.9
    assert not validator.is_valid(changed)
    del document["model_identity"]["revision"]
    assert not validator.is_valid(document)


def test_selection_schema_distinguishes_no_threshold() -> None:
    document = _documents()["selection.schema.json"]
    validator = Draft202012Validator(_schema("selection.schema.json"))
    document.update(threshold=None, reason="calibration.no_threshold")
    validator.validate(document)
    document["reason"] = "selected"
    assert not validator.is_valid(document)


def test_manifest_schema_rejects_missing_and_unknown_inventory_names() -> None:
    document = _documents()["calibration-manifest.schema.json"]
    validator = Draft202012Validator(_schema("calibration-manifest.schema.json"))
    changed = copy.deepcopy(document)
    del changed["files"]["records.jsonl"]
    assert not validator.is_valid(changed)
    document["files"]["verification.jsonl"] = {"size": 1, "sha256": HASH}
    assert not validator.is_valid(document)


def test_qualification_artifacts_validate_against_published_schemas(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    destination = tmp_path / "qualified"
    assert main(["demo", "--qualify", "--out", str(destination), "--json"]) == 0
    stdout, stderr = capsys.readouterr()
    assert stderr == ""
    Draft202012Validator(_schema("qualification-cli-receipt.schema.json")).validate(
        json.loads(stdout)
    )
    artifacts = {
        "selection-plan.schema.json": destination / "calibration" / "selection_plan.json",
        "selection.schema.json": destination / "calibration" / "selection.json",
        "calibration-manifest.schema.json": destination / "calibration" / "manifest.json",
        "qualification.schema.json": destination / "qualification.json",
    }
    for name, path in artifacts.items():
        document = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator(_schema(name)).validate(document)
