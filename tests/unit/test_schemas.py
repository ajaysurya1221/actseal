"""Published wire schemas (docs/schemas) agree with the frozen records and version constants.

No JSON Schema validator is a runtime or development dependency, so these
tests check the parts that matter for freezing: every schema file is strict
JSON with draft 2020-12 metadata, every `required`/`properties` set equals the
corresponding record's field set, every version `const` equals the exported
constant, and real documents written by the product have exactly the key sets
the schemas declare.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest
from test_evidence import make_bundle

from actseal.cli import RECEIPT_SCHEMA_VERSION, main
from actseal.compatibility import REGISTRY_FILE, REGISTRY_SCHEMA_VERSION, SUPPORTED_ENGINES
from actseal.evidence import BUNDLE_SCHEMA_VERSION, DATA_FILES, write_bundle
from actseal.records import (
    CONTRACT_SCHEMA_VERSION,
    FAILURE_CODES,
    LOCK_SCHEMA_VERSION,
    PROVIDERS,
    CapturedOutcome,
    Case,
    CaseRef,
    ChoiceAnswer,
    ChoiceQuestion,
    Contract,
    DecisionRecord,
    DecisionRequest,
    FaultResult,
    FaultSpec,
    GateLimits,
    Interval,
    LockedPolicy,
    ModelIdentity,
    Option,
    PlanLock,
    PolicyDecision,
    ProviderFailure,
    Verdict,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "docs" / "schemas"
PACKAGE = ROOT / "src" / "actseal"
FILES = (
    "lock.schema.json",
    "manifest.schema.json",
    "captured-outcome.schema.json",
    "decision-record.schema.json",
    "fault-result.schema.json",
    "verdict.schema.json",
    "cli-receipt.schema.json",
    "compatibility-registry.schema.json",
)


def load(name: str) -> dict[str, object]:
    return obj(json.loads((SCHEMAS / name).read_text(encoding="utf-8")))


def fields(record_type: type[object]) -> set[str]:
    assert dataclasses.is_dataclass(record_type)
    return {field.name for field in dataclasses.fields(record_type)}


def obj(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return value


def strings(value: object) -> set[str]:
    assert isinstance(value, list)
    assert all(isinstance(item, str) for item in value)
    return set(value)


def items(value: object) -> list[dict[str, object]]:
    assert isinstance(value, list)
    return [obj(item) for item in value]


def defs(schema: dict[str, object], name: str) -> dict[str, object]:
    return obj(obj(schema["$defs"])[name])


def prop(schema: dict[str, object], name: str) -> dict[str, object]:
    return obj(obj(schema["properties"])[name])


def check_object(schema: dict[str, object], expected: set[str]) -> None:
    assert schema.get("type") == "object"
    assert schema.get("additionalProperties") is False
    assert set(obj(schema["properties"])) == expected
    assert strings(schema["required"]) == expected


@pytest.mark.parametrize("name", FILES)
def test_schema_files_are_strict_draft_2020_12_documents(name: str) -> None:
    schema = load(name)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert str(schema["$id"]).startswith("urn:actseal:schema:")
    assert isinstance(schema["title"], str)
    assert isinstance(schema["description"], str)


def test_schema_readme_lists_every_file() -> None:
    readme = (SCHEMAS / "README.md").read_text(encoding="utf-8")
    for name in FILES:
        assert f"[{name}]({name})" in readme, name
    assert sorted(path.name for path in SCHEMAS.iterdir()) == sorted([*FILES, "README.md"])


def test_lock_schema_matches_the_record_fields_and_versions() -> None:
    schema = load("lock.schema.json")
    check_object(schema, fields(PlanLock))
    assert prop(schema, "schema_version")["const"] == LOCK_SCHEMA_VERSION
    required = schema["required"]
    assert isinstance(required, list)
    assert required[-1] == "replay_engine_version"
    contract = defs(schema, "Contract")
    check_object(contract, fields(Contract))
    assert prop(contract, "schema_version")["const"] == CONTRACT_SCHEMA_VERSION
    identity = defs(schema, "ModelIdentity")
    check_object(identity, fields(ModelIdentity))
    assert strings(prop(identity, "provider")["enum"]) == set(PROVIDERS)
    check_object(defs(schema, "ChoiceQuestion"), fields(ChoiceQuestion))
    check_object(defs(schema, "Option"), fields(Option))
    check_object(defs(schema, "LockedPolicy"), fields(LockedPolicy))
    check_object(defs(schema, "GateLimits"), fields(GateLimits))
    check_object(defs(schema, "Case"), fields(Case))
    check_object(defs(schema, "CaseRef"), fields(CaseRef))
    check_object(defs(schema, "FaultSpec"), fields(FaultSpec))


def test_manifest_schema_matches_the_bundle_layout() -> None:
    schema = load("manifest.schema.json")
    check_object(schema, {"schema_version", "files", "sha256"})
    assert prop(schema, "schema_version")["const"] == BUNDLE_SCHEMA_VERSION
    check_object(prop(schema, "files"), set(DATA_FILES))
    check_object(defs(schema, "Entry"), {"size", "sha256"})


def test_record_schemas_match_the_record_fields() -> None:
    captured = load("captured-outcome.schema.json")
    check_object(captured, fields(CapturedOutcome))
    assert strings(defs(captured, "FailureCode")["enum"]) == set(FAILURE_CODES)
    record = load("decision-record.schema.json")
    check_object(record, fields(DecisionRecord))
    check_object(defs(record, "CapturedOutcome"), fields(CapturedOutcome))
    check_object(defs(record, "ChoiceAnswer"), fields(ChoiceAnswer) | {"kind"})
    check_object(defs(record, "ProviderFailure"), fields(ProviderFailure) | {"kind"})
    check_object(defs(record, "PolicyDecision"), fields(PolicyDecision))
    fault = load("fault-result.schema.json")
    check_object(fault, fields(FaultResult))
    check_object(defs(fault, "DecisionRequest"), fields(DecisionRequest))
    check_object(defs(fault, "ChoiceQuestion"), fields(ChoiceQuestion))
    verdict = load("verdict.schema.json")
    check_object(verdict, fields(Verdict))
    check_object(defs(verdict, "Interval"), fields(Interval))


def test_registry_schema_matches_the_loader_rules() -> None:
    schema = load("compatibility-registry.schema.json")
    check_object(schema, {"schema_version", "implementations"})
    assert prop(schema, "schema_version")["const"] == REGISTRY_SCHEMA_VERSION
    implementations = prop(schema, "implementations")
    assert obj(implementations["propertyNames"])["pattern"] == "^[0-9a-f]{64}$"
    assert strings(obj(implementations["additionalProperties"])["enum"]) == set(SUPPORTED_ENGINES)
    packaged = obj(json.loads((PACKAGE / REGISTRY_FILE).read_text(encoding="utf-8")))
    assert set(packaged) == {"schema_version", "implementations"}
    assert packaged["schema_version"] == REGISTRY_SCHEMA_VERSION


def test_cli_receipt_schema_covers_every_variant() -> None:
    schema = load("cli-receipt.schema.json")
    variants = [item["$ref"] for item in items(schema["oneOf"])]
    assert variants == [
        "#/$defs/ErrorReceipt",
        "#/$defs/LockReceipt",
        "#/$defs/VerifyReceipt",
        "#/$defs/ReplayReceipt",
        "#/$defs/DemoReceipt",
    ]
    for name in ("ErrorReceipt", "LockReceipt", "DemoReceipt"):
        assert prop(defs(schema, name), "schema_version")["const"] == RECEIPT_SCHEMA_VERSION
    check_object(
        defs(schema, "ErrorReceipt"),
        {"schema_version", "command", "exit_code", "ok", "status", "error"},
    )
    check_object(
        defs(schema, "LockReceipt"),
        {
            "schema_version",
            "command",
            "exit_code",
            "ok",
            "lock_sha256",
            "implementation_sha256",
            "replay_engine_version",
            "evidence_scope",
            "contract",
            "model_identity",
            "verification_cases",
            "calibration_cases",
            "out",
        },
    )
    assert strings(prop(defs(schema, "ErrorReceipt"), "command")["enum"]) == {
        "lock",
        "verify",
        "replay",
        "demo",
        "actseal",
    }


def _all_of_required(schema: dict[str, object], variant: str) -> set[str]:
    """Union of `required` across an allOf variant, resolving local VerdictFields refs."""
    declared: set[str] = set()
    for part in items(defs(schema, variant)["allOf"]):
        if "$ref" in part:
            declared |= strings(defs(schema, str(part["$ref"]).rsplit("/", 1)[1])["required"])
        else:
            declared |= strings(part["required"])
    return declared


def test_written_documents_have_exactly_the_schema_key_sets(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = write_bundle(make_bundle(), tmp_path / "run")
    manifest = obj(json.loads((out / "manifest.json").read_text(encoding="utf-8")))
    assert set(manifest) == strings(load("manifest.schema.json")["required"])
    assert set(obj(manifest["files"])) == set(DATA_FILES)
    lock = obj(json.loads((out / "lock.json").read_text(encoding="utf-8")))
    assert set(lock) == strings(load("lock.schema.json")["required"])
    verdict = obj(json.loads((out / "verdict.json").read_text(encoding="utf-8")))
    assert set(verdict) == strings(load("verdict.schema.json")["required"])
    rows = (out / "records.jsonl").read_text(encoding="utf-8").splitlines()
    record = obj(json.loads(rows[0]))
    assert set(record) == strings(load("decision-record.schema.json")["required"])
    assert set(obj(record["capture"])) == strings(load("captured-outcome.schema.json")["required"])
    fault = obj(json.loads((out / "faults.jsonl").read_text(encoding="utf-8").splitlines()[0]))
    assert set(fault) == strings(load("fault-result.schema.json")["required"])
    assert main(["replay", str(out), "--json"]) == 2
    receipt = obj(json.loads(capsys.readouterr().out))
    assert set(receipt) == _all_of_required(load("cli-receipt.schema.json"), "ReplayReceipt")
