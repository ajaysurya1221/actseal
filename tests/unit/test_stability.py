"""Public-surface snapshot for the 1.x stability manifest (docs/stability.md).

These tests pin the frozen inventory: every module's ``__all__``, every public
function signature, every record's constructor field order, the documented
properties, aliases, errors and constants, the CLI inventory (commands,
options, exit codes, abbreviation rejection) and the versioned shape of every
``--json`` receipt variant. They also check that docs/stability.md names every
exported public symbol, so no existing convenience export can be quietly
dropped from the manifest. Identity/version *values* are asserted only where
the manifest states them.
"""

from __future__ import annotations

import collections.abc
import dataclasses
import inspect
import json
import re
from pathlib import Path
from types import ModuleType
from typing import Literal, get_args, get_origin

import pytest
from test_evidence import make_bundle

import actseal
import actseal.adapters.base as base_module
import actseal.adapters.fixture as fixture_module
import actseal.adapters.laya as laya_module
import actseal.assessment as assessment_module
import actseal.cli as cli_module
import actseal.compatibility as compatibility_module
import actseal.contract as contract_module
import actseal.demo_data as demo_data_module
import actseal.errors as errors_module
import actseal.evidence as evidence_module
import actseal.faults as faults_module
import actseal.locking as locking_module
import actseal.normalization as normalization_module
import actseal.policy as policy_module
import actseal.records as records_module
import actseal.replay as replay_module
import actseal.runner as runner_module
import actseal.serialization as serialization_module
import actseal.stats as stats_module
from actseal.cli import EXIT_CODES, EXIT_ERROR, RECEIPT_SCHEMA_VERSION, main
from actseal.evidence import write_bundle
from actseal.records import Action, EvidenceScope, Status
from conftest import SAMPLE_BUILDERS

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "src" / "actseal"
PACKAGED_INPUTS = PACKAGE / "demo_data"
STABILITY_DOC = ROOT / "docs" / "stability.md"

RECORD_FIELDS: dict[str, tuple[str, ...]] = {
    "Option": ("label", "description"),
    "ChoiceQuestion": ("question_id", "instructions", "options"),
    "Case": ("case_id", "state", "expected_label"),
    "CaseRef": ("case_id", "sha256"),
    "ModelIdentity": (
        "provider",
        "model",
        "revision",
        "artifact_hashes",
        "adapter_version",
        "normalizer_version",
        "runtime",
    ),
    "DecisionRequest": ("case_id", "state", "question"),
    "CapturedOutcome": (
        "request_sha256",
        "identity",
        "body_json",
        "failure_code",
        "warnings",
        "fallback_used",
    ),
    "ChoiceAnswer": (
        "choice",
        "probabilities",
        "selected_probability",
        "provider_confidence",
        "warnings",
        "fallback_used",
    ),
    "ProviderFailure": ("code", "warnings", "fallback_used"),
    "LockedPolicy": ("known_labels", "allowed_labels", "threshold"),
    "GateLimits": ("max_risk", "min_coverage", "alpha"),
    "Contract": (
        "schema_version",
        "name",
        "question",
        "policy",
        "limits",
        "evidence_scope",
        "population",
    ),
    "FaultSpec": ("scenario_id", "kind", "expected_action"),
    "PlanLock": (
        "schema_version",
        "contract",
        "model_identity",
        "calibration_sha256",
        "verification_sha256",
        "calibration_inventory",
        "verification_inventory",
        "verification_cases",
        "fault_inventory",
        "implementation_sha256",
        "sha256",
        "replay_engine_version",
    ),
    "PolicyDecision": ("action", "choice", "reason", "fallback_used"),
    "DecisionRecord": ("case_id", "capture", "outcome", "decision"),
    "FaultResult": ("scenario_id", "request", "capture", "outcome", "decision"),
    "Interval": ("lower", "upper"),
    "Verdict": (
        "status",
        "reasons",
        "total",
        "accepted",
        "errors",
        "risk",
        "coverage",
        "evidence_scope",
        "lock_sha256",
    ),
    "EvidenceBundle": (
        "lock",
        "calibration_jsonl",
        "verification_jsonl",
        "records",
        "faults",
        "verdict",
    ),
}

EXPORTS: dict[str, tuple[ModuleType, set[str]]] = {
    "actseal": (
        actseal,
        {
            *RECORD_FIELDS,
            "Action",
            "Status",
            "EvidenceScope",
            "Outcome",
            "ActsealError",
            "SchemaError",
            "IntegrityError",
            "ProviderSetupError",
            "canonical_json",
            "sha256_bytes",
            "strict_json_loads",
            "to_data",
            "from_data",
            "implementation_fingerprint",
            "__version__",
        },
    ),
    "actseal.records": (
        records_module,
        {
            *RECORD_FIELDS,
            "Action",
            "Status",
            "EvidenceScope",
            "Outcome",
            "SCHEMA_VERSION",
            "CONTRACT_SCHEMA_VERSION",
            "LOCK_SCHEMA_VERSION",
            "MIN_OPTIONS",
            "MAX_OPTIONS",
            "MAX_CASES_PER_SPLIT",
            "MASS_TOLERANCE",
            "FAILURE_CODES",
            "PROVIDERS",
        },
    ),
    "actseal.errors": (
        errors_module,
        {"ActsealError", "SchemaError", "IntegrityError", "ProviderSetupError"},
    ),
    "actseal.serialization": (
        serialization_module,
        {
            "MAX_JSON_BYTES",
            "MAX_JSON_DEPTH",
            "canonical_json",
            "sha256_bytes",
            "strict_json_loads",
            "to_data",
            "from_data",
            "implementation_fingerprint",
        },
    ),
    "actseal.contract": (
        contract_module,
        {"MAX_ROW_BYTES", "read_input_text", "parse_contract", "parse_cases"},
    ),
    "actseal.locking": (
        locking_module,
        {
            "FAULT_INVENTORY",
            "MAX_LOCK_BYTES",
            "case_digest",
            "lock_digest",
            "create_lock",
            "validate_lock",
            "validate_inputs",
            "parse_lock",
        },
    ),
    "actseal.policy": (
        policy_module,
        {
            "REASON_ALLOWED",
            "REASON_DISALLOWED_CHOICE",
            "REASON_FALLBACK_USED",
            "REASON_LOW_CONFIDENCE",
            "REASON_PROVIDER_PREFIX",
            "REASON_UNKNOWN_CHOICE",
            "evaluate",
        },
    ),
    "actseal.normalization": (
        normalization_module,
        {
            "FIXTURE_MASS_TOLERANCE",
            "LAYA_MASS_TOLERANCE_PER_OPTION",
            "LAYA_MODEL_MARKER",
            "NORMALIZER_VERSION",
            "laya_mass_tolerance",
            "normalize",
            "request_sha256",
        },
    ),
    "actseal.faults": (faults_module, {"FAULT_STATE", "fault_capture", "run_fault_campaign"}),
    "actseal.assessment": (
        assessment_module,
        {
            "REASON_CONTRACT_SATISFIED",
            "REASON_COVERAGE_BELOW_MINIMUM",
            "REASON_EVIDENCE_INSUFFICIENT",
            "REASON_FAULT_PREFIX",
            "REASON_INTEGRITY_PREFIX",
            "REASON_NO_ACCEPTED_CASES",
            "REASON_RISK_EXCEEDS_LIMIT",
            "REASON_WORKER_INVALIDATED",
            "TAIL_DIVISOR",
            "assess",
        },
    ),
    "actseal.evidence": (
        evidence_module,
        {
            "BUNDLE_FILES",
            "BUNDLE_SCHEMA_VERSION",
            "CALIBRATION_FILE",
            "DATA_FILES",
            "FAULTS_FILE",
            "LOCK_FILE",
            "MANIFEST_FILE",
            "MAX_BUNDLE_BYTES",
            "RECORDS_FILE",
            "VERDICT_FILE",
            "VERIFICATION_FILE",
            "decode_document",
            "decode_rows",
            "read_bundle_files",
            "write_bundle",
        },
    ),
    "actseal.replay": (
        replay_module,
        {
            "REASON_BUNDLE_HASH",
            "REASON_BUNDLE_IO",
            "REASON_BUNDLE_SCHEMA",
            "REASON_EXPECTED_LOCK",
            "REASON_FAULTS_SCHEMA",
            "REASON_INPUTS",
            "REASON_LEGACY_SCHEMA",
            "REASON_LOCK",
            "REASON_LOCK_SCHEMA",
            "REASON_RECORDS_SCHEMA",
            "REASON_VERDICT",
            "REASON_VERDICT_SCHEMA",
            "UNKNOWN_LOCK_SHA256",
            "UNKNOWN_SCOPE",
            "replay",
        },
    ),
    "actseal.runner": (
        runner_module,
        {
            "DEMO_EXPECTED",
            "DEMO_INPUTS_DIRECTORY",
            "DEMO_RUNS",
            "EVIDENCE_DIRECTORY",
            "LOCK_FILE_NAME",
            "REQUEST_TIMEOUT_S",
            "DemoResult",
            "DemoRun",
            "ModelFactory",
            "collect",
            "demo_run",
            "lock_run",
            "open_model",
            "verify_run",
            "write_lock",
        },
    ),
    "actseal.cli": (cli_module, {"EXIT_CODES", "EXIT_ERROR", "RECEIPT_SCHEMA_VERSION", "main"}),
    "actseal.compatibility": (
        compatibility_module,
        {
            "CURRENT_ENGINE",
            "LEGACY_GUIDANCE",
            "MAX_REGISTRY_BYTES",
            "REGISTRY_FILE",
            "REGISTRY_SCHEMA_VERSION",
            "RELEASE_RECEIPT_SCHEMA_VERSION",
            "SUPPORTED_ENGINES",
            "CompatibilityRegistry",
            "LegacySchemaError",
            "check_replay_compatibility",
            "is_legacy_lock",
            "is_legacy_manifest",
            "load_registry",
            "parse_registry",
            "require_exact_implementation",
        },
    ),
    "actseal.adapters.base": (base_module, {"DecisionModel"}),
    "actseal.adapters.fixture": (
        fixture_module,
        {
            "ADAPTER_VERSION",
            "MAX_FIXTURE_BYTES",
            "MAX_ROW_BYTES",
            "MODEL_NAME",
            "FixtureModel",
            "validate_timeout",
        },
    ),
    "actseal.adapters.laya": (
        laya_module,
        {
            "ADAPTER_VERSION",
            "ARTIFACT_HASHES",
            "HEAD_MAX_LEN",
            "MAX_LEN",
            "MODEL_ID",
            "OPTION_BUDGET",
            "OPTION_TOKEN_LIMIT",
            "REVISION",
            "STARTUP_TIMEOUT_S",
            "THREADS",
            "LayaModel",
        },
    ),
    "actseal.demo_data": (demo_data_module, {"RESOURCE_FILES", "RUNS"}),
}

SIGNATURES: dict[str, str] = {
    "contract.read_input_text": "(path: 'Path', *, limit: 'int' = 134217728) -> 'str'",
    "contract.parse_contract": "(path: 'Path') -> 'Contract'",
    "contract.parse_cases": "(text: 'str', question: 'ChoiceQuestion') -> 'tuple[Case, ...]'",
    "locking.case_digest": "(case: 'Case') -> 'str'",
    "locking.lock_digest": "(lock: 'PlanLock') -> 'str'",
    "locking.create_lock": (
        "(contract: 'Contract', calibration_jsonl: 'str', verification_jsonl: 'str', "
        "model_identity: 'ModelIdentity') -> 'PlanLock'"
    ),
    "locking.validate_lock": "(lock: 'PlanLock') -> 'None'",
    "locking.validate_inputs": (
        "(lock: 'PlanLock', calibration_jsonl: 'str', verification_jsonl: 'str') "
        "-> 'tuple[Case, ...]'"
    ),
    "locking.parse_lock": "(text: 'str') -> 'PlanLock'",
    "policy.evaluate": "(outcome: 'Outcome', policy: 'LockedPolicy') -> 'PolicyDecision'",
    "normalization.normalize": (
        "(capture: 'CapturedOutcome', question: 'ChoiceQuestion', "
        "expected_identity: 'ModelIdentity') -> 'Outcome'"
    ),
    "normalization.request_sha256": "(request: 'DecisionRequest') -> 'str'",
    "normalization.laya_mass_tolerance": "(option_count: 'int') -> 'float'",
    "faults.fault_capture": (
        "(lock: 'PlanLock', spec: 'FaultSpec') -> 'tuple[DecisionRequest, CapturedOutcome]'"
    ),
    "faults.run_fault_campaign": "(lock: 'PlanLock') -> 'tuple[FaultResult, ...]'",
    "stats.clopper_pearson_tail": (
        "(successes: 'int', n: 'int', tail: 'float') -> 'tuple[float, float]'"
    ),
    "assessment.assess": (
        "(records: 'Sequence[DecisionRecord]', lock: 'PlanLock', "
        "faults: 'Sequence[FaultResult]') -> 'Verdict'"
    ),
    "evidence.write_bundle": "(bundle: 'EvidenceBundle', destination: 'Path') -> 'Path'",
    "evidence.read_bundle_files": "(bundle: 'Path') -> 'dict[str, bytes]'",
    "evidence.decode_document": "(name: 'str', data: 'bytes', record_type: 'type[_D]') -> '_D'",
    "evidence.decode_rows": (
        "(name: 'str', data: 'bytes', record_type: 'type[_D]') -> 'tuple[_D, ...]'"
    ),
    "replay.replay": "(bundle: 'Path', *, expected_lock_sha256: 'str | None' = None) -> 'Verdict'",
    "runner.open_model": (
        "(provider: 'str', *, responses: 'Path | None', offline: 'bool') -> 'DecisionModel'"
    ),
    "runner.write_lock": "(lock: 'PlanLock', destination: 'Path') -> 'Path'",
    "runner.collect": (
        "(model: 'DecisionModel', lock: 'PlanLock', cases: 'tuple[Case, ...]') "
        "-> 'tuple[DecisionRecord, ...]'"
    ),
    "runner.lock_run": (
        "(contract_path: 'Path', calibration_path: 'Path', verification_path: 'Path', "
        "destination: 'Path', *, model_factory: 'ModelFactory') -> 'PlanLock'"
    ),
    "runner.verify_run": (
        "(lock_path: 'Path', calibration_path: 'Path', verification_path: 'Path', "
        "destination: 'Path', *, provider: 'str', model_factory: 'ModelFactory') "
        "-> 'tuple[EvidenceBundle, Path]'"
    ),
    "runner.demo_run": "(destination: 'Path') -> 'DemoResult'",
    "cli.main": "(argv: 'Sequence[str] | None' = None) -> 'int'",
    "compatibility.parse_registry": "(text: 'str') -> 'CompatibilityRegistry'",
    "compatibility.load_registry": "() -> 'CompatibilityRegistry'",
    "compatibility.check_replay_compatibility": (
        "(lock: 'PlanLock', *, registry: 'CompatibilityRegistry | None' = None) -> 'None'"
    ),
    "compatibility.require_exact_implementation": "(lock: 'PlanLock') -> 'None'",
    "compatibility.is_legacy_lock": "(value: 'object') -> 'bool'",
    "compatibility.is_legacy_manifest": "(value: 'object') -> 'bool'",
    "compatibility.CompatibilityRegistry.engine_for": (
        "(self, implementation_sha256: 'str') -> 'str | None'"
    ),
    "serialization.canonical_json": "(value: 'object') -> 'bytes'",
    "serialization.sha256_bytes": "(data: 'bytes') -> 'str'",
    "serialization.strict_json_loads": "(text: 'str') -> 'object'",
    "serialization.to_data": "(record: 'object') -> 'dict[str, object]'",
    "serialization.from_data": "(record_type: 'type[T]', value: 'object') -> 'T'",
    "serialization.implementation_fingerprint": "() -> 'str'",
    "adapters.fixture.validate_timeout": "(timeout_s: 'object') -> 'float'",
    "adapters.fixture.FixtureModel.__init__": "(self, responses: 'Path') -> 'None'",
    "adapters.fixture.FixtureModel.identity": "(self) -> 'ModelIdentity'",
    "adapters.fixture.FixtureModel.decide": (
        "(self, request: 'DecisionRequest', *, timeout_s: 'float') -> 'CapturedOutcome'"
    ),
    "adapters.fixture.FixtureModel.close": "(self) -> 'None'",
    "adapters.laya.LayaModel.__init__": "(self, *, offline: 'bool' = False) -> 'None'",
    "adapters.laya.LayaModel.identity": "(self) -> 'ModelIdentity'",
    "adapters.laya.LayaModel.decide": (
        "(self, request: 'DecisionRequest', *, timeout_s: 'float') -> 'CapturedOutcome'"
    ),
    "adapters.laya.LayaModel.close": "(self) -> 'None'",
    "adapters.base.DecisionModel.identity": "(self) -> 'ModelIdentity'",
    "adapters.base.DecisionModel.decide": (
        "(self, request: 'DecisionRequest', *, timeout_s: 'float') -> 'CapturedOutcome'"
    ),
    "adapters.base.DecisionModel.close": "(self) -> 'None'",
}

CLI_OPTIONS: dict[str, set[str]] = {
    "lock": {
        "--contract",
        "--calibration",
        "--verification",
        "--provider",
        "--responses",
        "--offline",
        "--out",
        "--json",
    },
    "verify": {
        "--lock",
        "--calibration",
        "--verification",
        "--provider",
        "--responses",
        "--offline",
        "--out",
        "--json",
    },
    "replay": {"--expected-lock-sha256", "--json"},
    "demo": {"--out", "--json"},
}


def _resolve(dotted: str) -> object:
    target: object = actseal
    for part in dotted.split("."):
        target = getattr(target, part)
    return target


# --------------------------------------------------------------------------- #
# Exports, signatures, records, aliases, errors
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("module_name", sorted(EXPORTS))
def test_module_exports_are_exactly_the_manifest(module_name: str) -> None:
    module, expected = EXPORTS[module_name]
    exported = module.__all__
    assert set(exported) == expected, module_name
    assert len(exported) == len(expected), module_name
    for name in expected:
        assert hasattr(module, name), (module_name, name)


def test_stats_public_surface_is_the_single_kernel_function() -> None:
    public = {name for name in vars(stats_module) if not name.startswith("_")}
    assert public == {"annotations", "clopper_pearson_tail", "math"}
    assert not hasattr(stats_module, "__all__")


@pytest.mark.parametrize("dotted", sorted(SIGNATURES))
def test_public_signatures_are_frozen(dotted: str) -> None:
    target = _resolve(dotted)
    assert str(inspect.signature(target)) == SIGNATURES[dotted]  # type: ignore[arg-type]


@pytest.mark.parametrize("name", sorted(RECORD_FIELDS))
def test_record_constructor_field_order_is_frozen(name: str) -> None:
    record_type = getattr(records_module, name)
    assert dataclasses.is_dataclass(record_type)
    fields = dataclasses.fields(record_type)
    assert tuple(field.name for field in fields) == RECORD_FIELDS[name]
    assert all(field.default is dataclasses.MISSING for field in fields), name
    assert "__slots__" in vars(record_type), name
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(SAMPLE_BUILDERS[name](), fields[0].name, None)
    assert getattr(actseal, name) is record_type


def test_plan_lock_appended_engine_keeps_every_zero_point_one_position() -> None:
    fields = RECORD_FIELDS["PlanLock"]
    assert fields[:11] == (
        "schema_version",
        "contract",
        "model_identity",
        "calibration_sha256",
        "verification_sha256",
        "calibration_inventory",
        "verification_inventory",
        "verification_cases",
        "fault_inventory",
        "implementation_sha256",
        "sha256",
    )
    assert fields[11] == "replay_engine_version"


def test_documented_properties_exist() -> None:
    for owner, name in (
        (records_module.ChoiceQuestion, "labels"),
        (runner_module.DemoRun, "verdict"),
        (runner_module.DemoRun, "as_expected"),
        (runner_module.DemoResult, "succeeded"),
    ):
        assert isinstance(inspect.getattr_static(owner, name), property), name
    assert tuple(field.name for field in dataclasses.fields(runner_module.DemoRun)) == (
        "name",
        "expected_status",
        "lock",
        "lock_path",
        "bundle",
        "bundle_path",
        "replayed",
    )
    assert tuple(field.name for field in dataclasses.fields(runner_module.DemoResult)) == (
        "destination",
        "runs",
        "duration_s",
    )
    assert tuple(
        field.name for field in dataclasses.fields(compatibility_module.CompatibilityRegistry)
    ) == ("schema_version", "implementations")


def test_aliases_and_errors_are_frozen() -> None:
    assert get_args(Action) == ("ACT", "ABSTAIN", "ESCALATE", "DENY")
    assert get_args(Status) == ("PASS", "BLOCK", "INCONCLUSIVE", "ERROR")
    assert get_args(EvidenceScope) == ("demo", "iid")
    assert get_origin(Action) is get_origin(Status) is get_origin(EvidenceScope) is Literal
    outcome = records_module.Outcome
    assert set(get_args(outcome.__value__)) == {
        records_module.ChoiceAnswer,
        records_module.ProviderFailure,
    }
    errors = errors_module
    for subclass in (errors.SchemaError, errors.IntegrityError, errors.ProviderSetupError):
        assert issubclass(subclass, errors.ActsealError)
        assert subclass.__mro__[1] is errors.ActsealError
    assert issubclass(errors.ActsealError, Exception)
    assert compatibility_module.LegacySchemaError.__mro__[1] is errors.SchemaError
    factory = runner_module.ModelFactory
    assert get_origin(factory) is collections.abc.Callable
    assert get_args(factory)[0] == []
    assert get_args(factory)[1] == "DecisionModel"  # forward reference to the protocol


def test_version_string_is_exported_and_well_formed() -> None:
    assert isinstance(actseal.__version__, str)
    assert re.fullmatch(r"\d+\.\d+\.\d+([-+.][0-9A-Za-z.+-]+)?", actseal.__version__)
    assert "__version__" in actseal.__all__


# --------------------------------------------------------------------------- #
# Constants: documented meanings and the values the manifest states
# --------------------------------------------------------------------------- #


def test_schema_and_limit_constants() -> None:
    assert records_module.SCHEMA_VERSION == 1
    assert records_module.CONTRACT_SCHEMA_VERSION == 1
    assert records_module.LOCK_SCHEMA_VERSION == 2
    assert evidence_module.BUNDLE_SCHEMA_VERSION == 2
    assert RECEIPT_SCHEMA_VERSION == 1
    assert compatibility_module.RELEASE_RECEIPT_SCHEMA_VERSION == 1
    assert compatibility_module.REGISTRY_SCHEMA_VERSION == 1
    assert (records_module.MIN_OPTIONS, records_module.MAX_OPTIONS) == (2, 16)
    assert records_module.MAX_CASES_PER_SPLIT == 10_000
    assert records_module.MASS_TOLERANCE == 1e-12
    assert set(records_module.FAILURE_CODES) == {
        "timeout",
        "rate_limit",
        "provider_error",
        "malformed_response",
        "identity_mismatch",
        "unknown_choice",
        "input_too_long",
        "unavailable",
    }
    assert set(records_module.PROVIDERS) == {"fixture", "laya"}
    assert serialization_module.MAX_JSON_BYTES == 128 * 1024 * 1024
    assert serialization_module.MAX_JSON_DEPTH == 32
    assert contract_module.MAX_ROW_BYTES == 1024 * 1024
    assert locking_module.MAX_LOCK_BYTES == 32 * 1024 * 1024
    assert evidence_module.MAX_BUNDLE_BYTES == 128 * 1024 * 1024
    assert compatibility_module.MAX_REGISTRY_BYTES == 1024 * 1024
    assert fixture_module.MAX_ROW_BYTES == 1024 * 1024
    assert fixture_module.MAX_FIXTURE_BYTES == 128 * 1024 * 1024


def test_reason_and_layout_constants() -> None:
    assert policy_module.REASON_FALLBACK_USED == "policy.fallback_used"
    assert policy_module.REASON_UNKNOWN_CHOICE == "policy.unknown_choice"
    assert policy_module.REASON_PROVIDER_PREFIX == "provider."
    assert policy_module.REASON_DISALLOWED_CHOICE == "policy.disallowed_choice"
    assert policy_module.REASON_LOW_CONFIDENCE == "policy.low_confidence"
    assert policy_module.REASON_ALLOWED == "policy.allowed"
    assert assessment_module.REASON_RISK_EXCEEDS_LIMIT == "risk.exceeds_limit"
    assert assessment_module.REASON_COVERAGE_BELOW_MINIMUM == "coverage.below_minimum"
    assert assessment_module.REASON_EVIDENCE_INSUFFICIENT == "evidence.insufficient"
    assert assessment_module.REASON_NO_ACCEPTED_CASES == "risk.no_accepted_cases"
    assert assessment_module.REASON_CONTRACT_SATISFIED == "contract.satisfied"
    assert assessment_module.REASON_WORKER_INVALIDATED == "infrastructure.worker_invalidated"
    assert assessment_module.REASON_FAULT_PREFIX == "fault."
    assert assessment_module.REASON_INTEGRITY_PREFIX == "integrity."
    assert assessment_module.TAIL_DIVISOR == 4
    replay_reasons = {
        name: getattr(replay_module, name)
        for name in replay_module.__all__
        if name.startswith("REASON_")
    }
    assert replay_reasons == {
        "REASON_BUNDLE_IO": "integrity.bundle_io",
        "REASON_BUNDLE_SCHEMA": "integrity.bundle_schema",
        "REASON_BUNDLE_HASH": "integrity.bundle_hash",
        "REASON_LOCK_SCHEMA": "integrity.lock_schema",
        "REASON_LEGACY_SCHEMA": "integrity.legacy_schema",
        "REASON_EXPECTED_LOCK": "integrity.expected_lock",
        "REASON_LOCK": "integrity.lock",
        "REASON_INPUTS": "integrity.inputs",
        "REASON_RECORDS_SCHEMA": "integrity.records_schema",
        "REASON_FAULTS_SCHEMA": "integrity.faults_schema",
        "REASON_VERDICT_SCHEMA": "integrity.verdict_schema",
        "REASON_VERDICT": "integrity.verdict",
    }
    assert replay_module.UNKNOWN_LOCK_SHA256 == "0" * 64
    assert replay_module.UNKNOWN_SCOPE == "demo"
    assert evidence_module.BUNDLE_FILES == (
        "manifest.json",
        "lock.json",
        "calibration.jsonl",
        "verification.jsonl",
        "records.jsonl",
        "faults.jsonl",
        "verdict.json",
    )
    assert evidence_module.BUNDLE_FILES[1:] == evidence_module.DATA_FILES
    assert faults_module.FAULT_STATE == "Actseal deterministic fault campaign."
    assert [(spec.kind, spec.expected_action) for spec in locking_module.FAULT_INVENTORY] == [
        ("timeout", "ESCALATE"),
        ("rate_limit", "ESCALATE"),
        ("malformed_response", "ESCALATE"),
        ("identity_mismatch", "ESCALATE"),
        ("unknown_choice", "DENY"),
        ("low_confidence", "ABSTAIN"),
    ]
    assert runner_module.REQUEST_TIMEOUT_S == 30.0
    assert runner_module.LOCK_FILE_NAME == "lock.json"
    assert runner_module.EVIDENCE_DIRECTORY == "evidence"
    assert runner_module.DEMO_INPUTS_DIRECTORY == "inputs"
    assert runner_module.DEMO_RUNS == ("bad", "fixed") == demo_data_module.RUNS
    assert runner_module.DEMO_EXPECTED == {"bad": "BLOCK", "fixed": "PASS"}
    assert dict(EXIT_CODES) == {"PASS": 0, "BLOCK": 1, "INCONCLUSIVE": 2, "ERROR": 3}
    assert EXIT_ERROR == 3
    assert laya_module.STARTUP_TIMEOUT_S == 120.0
    assert laya_module.THREADS == 4
    assert (laya_module.MAX_LEN, laya_module.HEAD_MAX_LEN) == (1024, 256)
    assert (laya_module.OPTION_TOKEN_LIMIT, laya_module.OPTION_BUDGET) == (48, 240)


def test_identity_constants_have_the_documented_shape() -> None:
    """Identity values may change with a release; their shape and meaning may not."""
    for value in (
        fixture_module.ADAPTER_VERSION,
        laya_module.ADAPTER_VERSION,
        normalization_module.NORMALIZER_VERSION,
        fixture_module.MODEL_NAME,
        laya_module.MODEL_ID,
        laya_module.REVISION,
        normalization_module.LAYA_MODEL_MARKER,
        compatibility_module.CURRENT_ENGINE,
    ):
        assert type(value) is str
        assert value
    assert compatibility_module.CURRENT_ENGINE in compatibility_module.SUPPORTED_ENGINES
    assert isinstance(compatibility_module.SUPPORTED_ENGINES, frozenset)
    for name, digest in laya_module.ARTIFACT_HASHES:
        assert name
        assert re.fullmatch(r"[0-9a-f]{64}", digest) is not None, name
    assert sorted(laya_module.ARTIFACT_HASHES) == list(laya_module.ARTIFACT_HASHES)
    assert normalization_module.FIXTURE_MASS_TOLERANCE == records_module.MASS_TOLERANCE
    assert normalization_module.LAYA_MASS_TOLERANCE_PER_OPTION == 0.00005


# --------------------------------------------------------------------------- #
# Documentation agreement: every export is named in docs/stability.md
# --------------------------------------------------------------------------- #


def test_stability_manifest_names_every_public_export() -> None:
    text = STABILITY_DOC.read_text(encoding="utf-8")
    mentioned = set(re.findall(r"`([A-Za-z_][A-Za-z0-9_.]*)`", text))
    mentioned |= set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", text))
    missing = {
        f"{module_name}.{name}"
        for module_name, (_, names) in EXPORTS.items()
        for name in names
        if name not in mentioned
    }
    assert not missing, sorted(missing)
    for required in ("clopper_pearson_tail", "labels", "as_expected", "succeeded", "__version__"):
        assert required in mentioned, required
    assert "actseal-choice-v1" in text
    assert "python -m actseal" in text


# --------------------------------------------------------------------------- #
# CLI inventory: commands, options, abbreviation, help/version as text
# --------------------------------------------------------------------------- #


def _help(argv: list[str], capsys: pytest.CaptureFixture[str]) -> str:
    assert main(argv) == 0
    out, err = capsys.readouterr()
    assert err == ""
    return out


def _options(help_text: str) -> set[str]:
    return set(re.findall(r"(?<![\w-])(--[a-z][a-z0-9-]*)", help_text))


def test_cli_commands_and_options_are_exactly_the_inventory(
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _help(["--help"], capsys)
    assert root.startswith("usage: actseal")
    assert _options(root) == {"--help", "--version"}
    for command in ("lock", "verify", "replay", "demo"):
        assert f"\n    {command} " in root
    assert not re.search(r"\n    (?!lock |verify |replay |demo )[a-z]+ ", root)
    for command, options in CLI_OPTIONS.items():
        text = _help([command, "--help"], capsys)
        assert text.startswith(f"usage: actseal {command}")
        assert _options(text) == options | {"--help"}, command
    replay_help = _help(["replay", "-h"], capsys)
    assert "DIRECTORY" in replay_help
    version_help = main(["--version"])
    assert version_help == 0
    out, _ = capsys.readouterr()
    assert out == f"actseal {actseal.__version__}\n"


@pytest.mark.parametrize(
    "argv",
    [
        [
            "lock",
            "--contr",
            "c",
            "--calibration",
            "c",
            "--verification",
            "v",
            "--provider",
            "fixture",
            "--out",
            "o",
        ],
        [
            "verify",
            "--loc",
            "l",
            "--calibration",
            "c",
            "--verification",
            "v",
            "--provider",
            "fixture",
            "--out",
            "o",
        ],
        [
            "verify",
            "--lock",
            "l",
            "--calib",
            "c",
            "--verification",
            "v",
            "--provider",
            "fixture",
            "--out",
            "o",
        ],
        ["replay", "dir", "--expected-lock", "a" * 64],
        ["replay", "dir", "--expected"],
        ["demo", "--ou", "x"],
        ["demo", "--out", "x", "--js"],
        ["--vers"],
        ["--hel"],
    ],
    ids=" ".join,
)
def test_abbreviated_options_are_rejected_on_every_parser(
    argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    code = main([*argv, "--json"])
    out, err = capsys.readouterr()
    assert code == 3
    assert err == ""
    document = json.loads(out)
    assert document["schema_version"] == 1
    assert document["status"] == "ERROR"
    assert document["exit_code"] == 3
    assert str(document["error"]).startswith("usage:")
    code = main(argv)
    out, err = capsys.readouterr()
    assert code == 3
    assert out == ""
    assert "error: usage:" in err


# --------------------------------------------------------------------------- #
# Every JSON receipt variant is versioned
# --------------------------------------------------------------------------- #


def _receipt(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, dict[str, object]]:
    code = main([*argv, "--json"])
    out, err = capsys.readouterr()
    assert err == ""
    assert out.count("\n") == 1
    document = json.loads(out)
    assert isinstance(document, dict)
    assert document["schema_version"] == RECEIPT_SCHEMA_VERSION == 1
    assert document["exit_code"] == code
    assert document["ok"] == (code == 0)
    return code, document


def _demo_argv(run: str, lock: Path, out: Path | None) -> list[str]:
    argv = (
        ["lock", "--contract", str(PACKAGED_INPUTS / f"{run}.toml")]
        if out is None
        else ["verify", "--lock", str(lock)]
    )
    argv += [
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
    return argv


def test_every_json_receipt_variant_carries_schema_version_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    lock = tmp_path / "lock.json"
    code, locked = _receipt(_demo_argv("fixed", lock, None), capsys)
    assert code == 0
    assert locked["command"] == "lock"
    assert set(locked) == {
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
    }
    assert locked["replay_engine_version"] == "actseal-choice-v1"

    out = tmp_path / "evidence"
    code, verified = _receipt(_demo_argv("fixed", lock, out), capsys)
    assert code == 0
    assert verified["command"] == "verify"
    verdict_keys = {
        "status",
        "reasons",
        "total",
        "accepted",
        "errors",
        "risk",
        "coverage",
        "evidence_scope",
        "lock_sha256",
    }
    assert set(verified) == verdict_keys | {
        "schema_version",
        "command",
        "exit_code",
        "ok",
        "failures",
        "warnings",
        "faults",
        "out",
    }

    code, replayed = _receipt(["replay", str(out)], capsys)
    assert code == 0
    assert replayed["command"] == "replay"
    assert set(replayed) == verdict_keys | {
        "schema_version",
        "command",
        "exit_code",
        "ok",
        "bundle",
        "expected_lock_sha256",
        "notes",
    }
    assert replayed["expected_lock_sha256"] is None
    assert replayed["notes"] == []
    code, anchored = _receipt(
        ["replay", str(out), "--expected-lock-sha256", str(locked["lock_sha256"])], capsys
    )
    assert code == 0
    assert anchored["expected_lock_sha256"] == locked["lock_sha256"]

    code, failed = _receipt(["replay", str(tmp_path / "missing")], capsys)
    assert code == 3
    assert failed["command"] == "replay"
    assert failed["status"] == "ERROR"
    assert failed["reasons"] == ["integrity.bundle_io"]

    code, usage = _receipt(["replay"], capsys)
    assert code == 3
    assert usage["command"] == "replay"
    assert set(usage) == {"schema_version", "command", "exit_code", "ok", "status", "error"}
    assert str(usage["error"]).startswith("usage:")

    code, unparsed = _receipt(["bogus"], capsys)
    assert code == 3
    assert unparsed["command"] == "actseal"
    assert set(unparsed) == {"schema_version", "command", "exit_code", "ok", "status", "error"}

    code, exists = _receipt(_demo_argv("fixed", lock, None), capsys)
    assert code == 3
    assert exists["command"] == "lock"
    assert exists["error"] == "destination already exists"


def test_demo_receipt_is_versioned_and_complete(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, demo = _receipt(["demo", "--out", str(tmp_path / "demo")], capsys)
    assert code == 0
    assert demo["command"] == "demo"
    assert set(demo) == {
        "schema_version",
        "command",
        "exit_code",
        "ok",
        "status",
        "evidence_scope",
        "demo_only",
        "note",
        "out",
        "duration_s",
        "runs",
    }
    runs = demo["runs"]
    assert isinstance(runs, dict)
    assert set(runs) == {"bad", "fixed"}
    for name, run in runs.items():
        assert isinstance(run, dict)
        assert "schema_version" not in run  # the receipt is versioned once, at the top level
        assert set(run) >= {
            "status",
            "expected_status",
            "as_expected",
            "lock",
            "evidence",
            "replay",
            "replay_matches",
            "failures",
            "warnings",
            "faults",
        }, name


def test_help_and_version_remain_text(capsys: pytest.CaptureFixture[str]) -> None:
    for argv in (["--help", "--json"], ["--version", "--json"], ["lock", "--help", "--json"]):
        assert main(argv) == 0
        out, _ = capsys.readouterr()
        with pytest.raises(json.JSONDecodeError):
            json.loads(out)


def test_written_bundle_manifest_is_schema_2(tmp_path: Path) -> None:
    out = write_bundle(make_bundle(), tmp_path / "run")
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 2
    lock = json.loads((out / "lock.json").read_text(encoding="utf-8"))
    assert lock["schema_version"] == 2
    assert lock["replay_engine_version"] == "actseal-choice-v1"
