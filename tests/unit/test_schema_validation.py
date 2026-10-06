"""Genuine Draft 2020-12 validation of real product output against docs/schemas.

The structural key-set checks in ``test_schemas`` cannot catch a schema that
*requires* a field the product never writes (REVIEW 02, P1). This module runs
the maintained ``jsonschema`` validator (dev-only dependency, amendment V1-008)
over documents the product actually produces: every bundle file written by
``write_bundle`` for fixture, Laya and infrastructure-ERROR evidence, both demo
runs, and every CLI receipt variant including nested demo runs and error paths.
All ``$ref`` resolution goes through a local ``referencing.Registry`` built from
the committed schema files; an unknown reference fails instead of fetching.
Negative cases prove the validator is strict (a demo run carrying ``exit_code``
is rejected, as are unversioned or over-specified receipts).
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any, cast

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource
from referencing.exceptions import NoSuchResource, Unresolvable
from test_compatibility import legacy_bundle_dir, legacy_lock_bytes
from test_evidence import (
    contract_with,
    laya_identity,
    make_bundle,
    make_lock,
    record_for,
    records_for,
)

import actseal.runner as runner_module
from actseal.cli import main
from actseal.compatibility import REGISTRY_FILE
from actseal.evidence import write_bundle
from actseal.records import EvidenceBundle
from actseal.runner import demo_run

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "docs" / "schemas"
PACKAGE = ROOT / "src" / "actseal"
PACKAGED_INPUTS = PACKAGE / "demo_data"
SCHEMA_FILES = (
    "lock.schema.json",
    "manifest.schema.json",
    "captured-outcome.schema.json",
    "decision-record.schema.json",
    "fault-result.schema.json",
    "verdict.schema.json",
    "cli-receipt.schema.json",
    "compatibility-registry.schema.json",
)


# --------------------------------------------------------------------------- #
# Validator construction: local registry, no retrieval
# --------------------------------------------------------------------------- #


#: The document type jsonschema's validators accept for schemas and registry resources.
SchemaDocument = bool | Mapping[str, Any]


def _load(name: str) -> dict[str, Any]:
    document = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def _registry() -> Registry[SchemaDocument]:
    """Local registry of the committed schemas; the default retriever refuses unknown URIs.

    ``referencing.Registry`` performs no network or filesystem retrieval unless a
    ``retrieve`` callable is supplied; none is, so an unknown ``$ref`` raises
    ``Unresolvable`` instead of fetching (asserted below).
    """
    registry: Registry[SchemaDocument] = Registry()
    resources = [
        (str(schema["$id"]), Resource.from_contents(cast(SchemaDocument, schema)))
        for schema in (_load(name) for name in SCHEMA_FILES)
    ]
    return registry.with_resources(resources)


def _validator(name: str) -> Draft202012Validator:
    schema = _load(name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, registry=_registry())


VALIDATORS = {name: _validator(name) for name in SCHEMA_FILES}


def valid(name: str, instance: object) -> None:
    VALIDATORS[name].validate(instance)


def invalid(name: str, instance: object) -> None:
    with pytest.raises(ValidationError):
        VALIDATORS[name].validate(instance)


def _document(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _rows(path: Path) -> Iterator[object]:
    for line in path.read_text(encoding="utf-8").split("\n")[:-1]:
        yield json.loads(line)


def receipt(capsys: pytest.CaptureFixture[str], argv: list[str]) -> tuple[int, dict[str, object]]:
    code = main([*argv, "--json"])
    out, err = capsys.readouterr()
    assert err == ""
    document = json.loads(out)
    assert isinstance(document, dict)
    return code, document


def demo_argv(run: str, lock: Path, out: Path | None) -> list[str]:
    argv = (
        ["lock", "--contract", str(PACKAGED_INPUTS / f"{run}.toml")]
        if out is None
        else ["verify", "--lock", str(lock)]
    )
    return [
        *argv,
        "--calibration",
        str(PACKAGED_INPUTS / f"{run}_calibration.jsonl"),
        "--verification",
        str(PACKAGED_INPUTS / f"{run}_verification.jsonl"),
        "--provider",
        "fixture",
        "--responses",
        str(PACKAGED_INPUTS / f"{run}_responses.jsonl"),
        "--out",
        str(lock if out is None else out),
    ]


def validate_bundle_directory(out: Path) -> None:
    """Every file of a written bundle validates against its published schema."""
    valid("manifest.schema.json", _document(out / "manifest.json"))
    valid("lock.schema.json", _document(out / "lock.json"))
    valid("verdict.schema.json", _document(out / "verdict.json"))
    records = list(_rows(out / "records.jsonl"))
    faults = list(_rows(out / "faults.jsonl"))
    assert records
    assert len(faults) == 6
    for row in records:
        valid("decision-record.schema.json", row)
        assert isinstance(row, dict)
        valid("captured-outcome.schema.json", row["capture"])
    for row in faults:
        valid("fault-result.schema.json", row)
        assert isinstance(row, dict)
        valid("captured-outcome.schema.json", row["capture"])


# --------------------------------------------------------------------------- #
# Schema files and registry behaviour
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name", SCHEMA_FILES)
def test_schema_files_are_valid_draft_2020_12_schemas(name: str) -> None:
    schema = _load(name)
    Draft202012Validator.check_schema(schema)
    assert str(schema["$id"]) in _registry()


def test_unknown_references_fail_instead_of_fetching() -> None:
    probe = Draft202012Validator(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$ref": "urn:actseal:schema:missing:1",
        },
        registry=_registry(),
    )
    with pytest.raises(Unresolvable):
        probe.validate({})
    # Committed ids do resolve through the local registry.
    resolved = _registry().get_or_retrieve("urn:actseal:schema:lock:2")
    contents = resolved.value.contents
    assert isinstance(contents, Mapping)
    assert contents["title"] == "Actseal PlanLock document (schema 2)"
    with pytest.raises(NoSuchResource):
        _registry().get_or_retrieve("urn:actseal:schema:missing:1")


# --------------------------------------------------------------------------- #
# Bundles written by the product
# --------------------------------------------------------------------------- #


def _error_bundle() -> EvidenceBundle:
    """A complete ADR 0009 infrastructure-ERROR bundle (regular Laya timeout)."""
    lock = make_lock(identity=laya_identity())
    records = records_for(lock)
    records = (record_for(lock, lock.verification_cases[0], failure_code="timeout"), *records[1:])
    bundle = make_bundle(lock, records)
    assert bundle.verdict.status == "ERROR"
    assert "infrastructure.worker_invalidated" in bundle.verdict.reasons
    return bundle


@pytest.mark.parametrize(
    "build",
    [
        make_bundle,
        lambda: make_bundle(make_lock(identity=laya_identity())),
        lambda: make_bundle(make_lock(contract_with(max_risk=0.6, min_coverage=0.4))),
        lambda: make_bundle(
            make_lock(),
            records_for(
                make_lock(), ["technical", "sales", "billing", "technical", "sales", "billing"]
            ),
        ),
        _error_bundle,
    ],
    ids=[
        "fixture-inconclusive",
        "laya-inconclusive",
        "fixture-pass",
        "fixture-block",
        "laya-error",
    ],
)
def test_written_bundles_validate_against_the_published_schemas(
    tmp_path: Path, build: object
) -> None:
    assert callable(build)
    bundle = build()
    assert isinstance(bundle, EvidenceBundle)
    out = write_bundle(bundle, tmp_path / "run")
    validate_bundle_directory(out)


def test_demo_bundles_and_locks_validate(tmp_path: Path) -> None:
    result = demo_run(tmp_path / "demo")
    assert result.succeeded
    for run in result.runs:
        valid("lock.schema.json", _document(run.lock_path))
        validate_bundle_directory(run.bundle_path)


def test_packaged_registry_validates_and_malformed_registries_do_not() -> None:
    valid("compatibility-registry.schema.json", _document(PACKAGE / REGISTRY_FILE))
    valid(
        "compatibility-registry.schema.json",
        {"schema_version": 1, "implementations": {"a" * 64: "actseal-choice-v1"}},
    )
    for bad in (
        {"schema_version": 2, "implementations": {}},
        {"schema_version": 1},
        {"schema_version": 1, "implementations": {}, "extra": 1},
        {"schema_version": 1, "implementations": {"A" * 64: "actseal-choice-v1"}},
        {"schema_version": 1, "implementations": {"*": "actseal-choice-v1"}},
        {"schema_version": 1, "implementations": {"a" * 64: "actseal-choice-v2"}},
        {"schema_version": 1, "implementations": []},
    ):
        invalid("compatibility-registry.schema.json", bad)


def test_legacy_lock_does_not_validate_as_schema_2() -> None:
    invalid("lock.schema.json", json.loads(legacy_lock_bytes(make_lock())))


# --------------------------------------------------------------------------- #
# Every CLI receipt variant, including nested demo runs and error paths
# --------------------------------------------------------------------------- #


def test_lock_verify_and_replay_receipts_validate(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    lock = tmp_path / "lock.json"
    code, locked = receipt(capsys, demo_argv("fixed", lock, None))
    assert code == 0
    valid("cli-receipt.schema.json", locked)

    code, exists = receipt(capsys, demo_argv("fixed", lock, None))
    assert code == 3
    valid("cli-receipt.schema.json", exists)

    for run, expected in (("fixed", 0), ("bad", 1)):
        run_lock = tmp_path / f"{run}.lock.json"
        assert receipt(capsys, demo_argv(run, run_lock, None))[0] == 0
        out = tmp_path / f"{run}.evidence"
        code, verified = receipt(capsys, demo_argv(run, run_lock, out))
        assert code == expected
        valid("cli-receipt.schema.json", verified)
        code, replayed = receipt(capsys, ["replay", str(out)])
        assert code == expected
        valid("cli-receipt.schema.json", replayed)
        code, anchored = receipt(
            capsys, ["replay", str(out), "--expected-lock-sha256", str(verified["lock_sha256"])]
        )
        assert code == expected
        valid("cli-receipt.schema.json", anchored)
        code, mismatched = receipt(capsys, ["replay", str(out), "--expected-lock-sha256", "1" * 64])
        assert code == 3
        assert mismatched["reasons"] == ["integrity.expected_lock"]
        valid("cli-receipt.schema.json", mismatched)


def test_error_and_usage_receipts_validate(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bundle = make_bundle()
    legacy_lock = tmp_path / "legacy-lock.json"
    legacy_lock.write_bytes(legacy_lock_bytes(bundle.lock))
    (tmp_path / "c.jsonl").write_text(bundle.calibration_jsonl, encoding="utf-8")
    (tmp_path / "v.jsonl").write_text(bundle.verification_jsonl, encoding="utf-8")
    (tmp_path / "r.jsonl").write_text("", encoding="utf-8")
    verify_legacy = [
        "verify",
        "--lock",
        str(legacy_lock),
        "--calibration",
        str(tmp_path / "c.jsonl"),
        "--verification",
        str(tmp_path / "v.jsonl"),
        "--provider",
        "fixture",
        "--responses",
        str(tmp_path / "r.jsonl"),
        "--out",
        str(tmp_path / "run"),
    ]
    variants: list[list[str]] = [
        ["replay", str(tmp_path / "missing")],  # replay ERROR verdict (bundle_io)
        ["replay", str(legacy_bundle_dir(tmp_path))],  # legacy ERROR with notes
        verify_legacy,  # verify error path (LegacySchemaError)
        ["replay"],  # usage error, command known
        ["replay", "dir", "--expected"],  # abbreviation rejected
        ["bogus"],  # unparsable command -> command "actseal"
        ["lock", "--provider", "jev"],  # invalid choice
        ["demo"],  # missing required option
    ]
    for argv in variants:
        code, document = receipt(capsys, argv)
        assert code == 3, argv
        valid("cli-receipt.schema.json", document)


def test_demo_receipts_validate_including_nested_runs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    code, success = receipt(capsys, ["demo", "--out", str(tmp_path / "demo")])
    assert code == 0
    valid("cli-receipt.schema.json", success)
    runs = success["runs"]
    assert isinstance(runs, dict)
    for name in ("bad", "fixed"):
        run = runs[name]
        assert isinstance(run, dict)
        assert "exit_code" not in run
        assert "ok" not in run
        assert "out" not in run
    # The prespecified-expectation failure path is also a demo receipt (exit 3, status ERROR).
    monkeypatch.setitem(runner_module.DEMO_EXPECTED, "fixed", "BLOCK")
    code, failure = receipt(capsys, ["demo", "--out", str(tmp_path / "demo-failure")])
    assert code == 3
    assert failure["status"] == "ERROR"
    valid("cli-receipt.schema.json", failure)
    # Setup failure (existing destination) is the generic error receipt.
    code, exists = receipt(capsys, ["demo", "--out", str(tmp_path / "demo")])
    assert code == 3
    valid("cli-receipt.schema.json", exists)


# --------------------------------------------------------------------------- #
# Negative receipt cases: the validator is strict
# --------------------------------------------------------------------------- #


def test_receipt_schema_rejects_the_review_02_shape_and_other_defects(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, success = receipt(capsys, ["demo", "--out", str(tmp_path / "demo")])
    assert code == 0
    runs = success["runs"]
    assert isinstance(runs, dict)
    with_exit_code = json.loads(json.dumps(success))
    with_exit_code["runs"]["bad"]["exit_code"] = 1
    invalid("cli-receipt.schema.json", with_exit_code)  # the REVIEW 02 P1 shape
    with_ok = json.loads(json.dumps(success))
    with_ok["runs"]["fixed"]["ok"] = True
    invalid("cli-receipt.schema.json", with_ok)
    unversioned = {key: value for key, value in success.items() if key != "schema_version"}
    invalid("cli-receipt.schema.json", unversioned)
    wrong_version = {**success, "schema_version": 2}
    invalid("cli-receipt.schema.json", wrong_version)
    extra = {**success, "elapsed": 1.0}
    invalid("cli-receipt.schema.json", extra)

    lock = tmp_path / "lock.json"
    code, locked = receipt(capsys, demo_argv("fixed", lock, None))
    assert code == 0
    invalid("cli-receipt.schema.json", {**locked, "exit_code": 1})
    invalid("cli-receipt.schema.json", {**locked, "replay_engine_version": ""})
    invalid("cli-receipt.schema.json", {key: v for key, v in locked.items() if key != "command"})
    out = tmp_path / "evidence"
    code, verified = receipt(capsys, demo_argv("fixed", lock, out))
    assert code == 0
    invalid("cli-receipt.schema.json", {**verified, "extra": 1})
    invalid("cli-receipt.schema.json", {**verified, "exit_code": 7})
    code, replayed = receipt(capsys, ["replay", str(out)])
    assert code == 0
    invalid("cli-receipt.schema.json", {**replayed, "notes": "none"})
    invalid("cli-receipt.schema.json", {**replayed, "expected_lock_sha256": "abc"})
    missing_notes = {key: v for key, v in replayed.items() if key != "notes"}
    invalid("cli-receipt.schema.json", missing_notes)
