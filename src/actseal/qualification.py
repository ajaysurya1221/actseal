"""Opt-in calibration sidecars and fixed-sample qualification.

The selection plan is sealed and written before the first calibration capture.
Only the existing verification engine issues a verdict. Replay uses data and
pure normalization/policy/selection code; it imports no provider adapter.
Hashes establish internal consistency, not sampling or execution provenance.
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import stat
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, Final, cast

from actseal import compatibility
from actseal.contract import parse_cases, parse_contract, read_input_text
from actseal.errors import IntegrityError, ProviderSetupError, SchemaError
from actseal.evidence import (
    MAX_BUNDLE_BYTES,
    _Budget,
    _check_path_text,
    _encode_dataset,
    _encode_rows,
    _exclusive_rename,
    _read_exact,
    _write_file,
    decode_rows,
)
from actseal.normalization import normalize, request_sha256
from actseal.policy import evaluate
from actseal.records import (
    PROVIDERS,
    Case,
    ChoiceAnswer,
    Contract,
    DecisionRecord,
    DecisionRequest,
    EvidenceBundle,
    ModelIdentity,
    PlanLock,
)
from actseal.selection import (
    DEFAULT_SELECTION_TAIL,
    CalibrationCase,
    SelectionResult,
    select_threshold,
)
from actseal.serialization import (
    canonical_json,
    from_data,
    implementation_fingerprint,
    sha256_bytes,
    strict_json_loads,
    to_data,
)

if TYPE_CHECKING:
    from actseal.adapters.base import DecisionModel
    from actseal.runner import ModelFactory

__all__ = [
    "DEFAULT_GRID",
    "CalibrationRun",
    "QualificationRun",
    "calibrate_run",
    "qualify_run",
    "replay_selection",
]

DEFAULT_GRID: Final = (0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0)
_DATA_FILES: Final = ("selection_plan.json", "calibration.jsonl", "records.jsonl", "selection.json")
_FILES: Final = (*_DATA_FILES, "manifest.json")
_PLAN_KEYS: Final = frozenset(
    {
        "schema_version",
        "contract",
        "grid",
        "target_pass_probability",
        "selection_tail",
        "n_verify",
        "calibration_sha256",
        "verification_sha256",
        "model_identity",
        "implementation_sha256",
        "replay_engine_version",
        "sha256",
    }
)
_HEX: Final = re.compile(r"[0-9a-f]{64}")
_PROBABILITY_ABS_TOL: Final = 1e-10
_PROBABILITY_REL_TOL: Final = 1e-9


@dataclass(frozen=True)
class CalibrationRun:
    """Published selection and optional derived contract under one new root."""

    destination: Path
    selection: SelectionResult
    manifest_sha256: str
    contract_path: Path | None


@dataclass(frozen=True)
class QualificationRun:
    """Calibration plus the existing verification result, when a threshold exists."""

    destination: Path
    calibration: CalibrationRun
    lock: PlanLock | None
    bundle: EvidenceBundle | None
    receipt_path: Path | None

    @property
    def lock_path(self) -> Path | None:
        return self.destination / "lock.json" if self.lock is not None else None

    @property
    def bundle_path(self) -> Path | None:
        return self.destination / "evidence" if self.bundle is not None else None


@dataclass(frozen=True)
class _Plan:
    contract: Contract
    grid: tuple[float, ...]
    target_pass_probability: float
    selection_tail: float
    n_verify: int
    calibration_sha256: str
    verification_sha256: str
    model_identity: ModelIdentity
    implementation_sha256: str
    replay_engine_version: str

    def select(self, cases: Sequence[CalibrationCase]) -> SelectionResult:
        return select_threshold(
            grid=self.grid,
            cases=cases,
            n_verify=self.n_verify,
            max_risk=self.contract.limits.max_risk,
            min_coverage=self.contract.limits.min_coverage,
            alpha=self.contract.limits.alpha,
            target_pass_probability=self.target_pass_probability,
            selection_tail=self.selection_tail,
        )

    def document(self) -> dict[str, object]:
        contract = to_data(self.contract)
        policy = cast(dict[str, object], contract["policy"])
        del policy["threshold"]
        return _seal(
            {
                "schema_version": 1,
                "contract": contract,
                "grid": list(self.grid),
                "target_pass_probability": self.target_pass_probability,
                "selection_tail": self.selection_tail,
                "n_verify": self.n_verify,
                "calibration_sha256": self.calibration_sha256,
                "verification_sha256": self.verification_sha256,
                "model_identity": to_data(self.model_identity),
                "implementation_sha256": self.implementation_sha256,
                "replay_engine_version": self.replay_engine_version,
            }
        )


def _seal(value: dict[str, object]) -> dict[str, object]:
    return {**value, "sha256": sha256_bytes(canonical_json(value))}


def _object(value: object, keys: set[str] | frozenset[str], name: str) -> dict[str, object]:
    if type(value) is not dict or set(value) != keys:
        raise SchemaError(f"{name}: unexpected fields or object type")
    return cast(dict[str, object], value)


def _number(value: object, name: str) -> float:
    if type(value) not in (int, float):
        raise SchemaError(f"{name}: expected a finite number")
    try:
        number = float(cast(int | float, value))
    except OverflowError:
        raise SchemaError(f"{name}: expected a finite number") from None
    if not math.isfinite(number):
        raise SchemaError(f"{name}: expected a finite number")
    return number


def _digest(value: object, name: str) -> str:
    if not isinstance(value, str) or _HEX.fullmatch(value) is None:
        raise SchemaError(f"{name}: expected lowercase SHA256")
    return value


def _json_document(data: bytes) -> object:
    try:
        value = strict_json_loads(data.decode("utf-8"))
    except UnicodeDecodeError:
        raise SchemaError("document: expected UTF-8") from None
    if canonical_json(value) + b"\n" != data:
        raise SchemaError("document: expected canonical JSON and one LF")
    return value


def _check_seal(value: dict[str, object]) -> None:
    digest = _digest(value["sha256"], "sha256")
    if sha256_bytes(canonical_json({k: v for k, v in value.items() if k != "sha256"})) != digest:
        raise IntegrityError("sha256: document self-hash mismatch")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise SchemaError("schema_version: unsupported version")


def _decode_plan(data: bytes) -> _Plan:
    value = _object(_json_document(data), _PLAN_KEYS, "selection_plan")
    _check_seal(value)
    contract_data = _object(
        value["contract"],
        {"schema_version", "name", "question", "policy", "limits", "evidence_scope", "population"},
        "contract",
    )
    policy = _object(contract_data["policy"], {"known_labels", "allowed_labels"}, "policy")
    contract = from_data(Contract, {**contract_data, "policy": {**policy, "threshold": 1.0}})
    grid = value["grid"]
    if type(grid) is not list:
        raise SchemaError("grid: expected an array")
    n_verify = value["n_verify"]
    if type(n_verify) is not int:
        raise SchemaError("n_verify: expected an integer")
    engine = value["replay_engine_version"]
    if not isinstance(engine, str):
        raise SchemaError("replay_engine_version: expected a string")
    plan = _Plan(
        contract,
        tuple(_number(t, "grid") for t in grid),
        _number(value["target_pass_probability"], "target_pass_probability"),
        _number(value["selection_tail"], "selection_tail"),
        n_verify,
        _digest(value["calibration_sha256"], "calibration_sha256"),
        _digest(value["verification_sha256"], "verification_sha256"),
        from_data(ModelIdentity, value["model_identity"]),
        _digest(value["implementation_sha256"], "implementation_sha256"),
        engine,
    )
    try:
        plan.select(())  # The frozen selector owns numerical domains and grid validation.
    except (TypeError, ValueError) as exc:
        raise SchemaError(f"selection_plan: {exc}") from None
    _check_replay_compatibility(plan)
    return plan


def _check_replay_compatibility(plan: _Plan) -> None:
    """Apply bundle replay's supported-engine and exact/dual-registration rules."""
    if plan.replay_engine_version not in compatibility.SUPPORTED_ENGINES:
        raise IntegrityError("replay_engine_version: unsupported replay engine")
    current = implementation_fingerprint()
    if plan.implementation_sha256 == current:
        return
    approved = compatibility.load_registry()
    engine = plan.replay_engine_version
    if (
        approved.engine_for(plan.implementation_sha256) != engine
        or approved.engine_for(current) != engine
    ):
        raise IntegrityError(
            "implementation_sha256: does not match the current implementation or an "
            "approved compatible implementation for its replay engine"
        )


def _selection_document(selection: SelectionResult) -> dict[str, object]:
    return {
        "schema_version": 1,
        "threshold": selection.threshold,
        "reason": selection.reason,
        "points": [
            {
                "threshold": point.threshold,
                "accepted": point.accepted,
                "errors": point.errors,
                "predicted_pass_probability": point.predicted_pass_probability,
            }
            for point in selection.points
        ],
    }


def _encoded_document(value: dict[str, object], budget: _Budget) -> bytes:
    data = canonical_json(value) + b"\n"
    budget.charge(len(data))
    return data


def _new_destination(destination: Path) -> None:
    _check_path_text("destination", destination)
    if os.path.lexists(destination):
        raise FileExistsError("destination: already exists")
    if not destination.parent.is_dir():
        raise SchemaError("destination: parent directory does not exist")


def _split_inputs(contract: Contract, calibration: str, verification: str) -> tuple[Case, ...]:
    cases = parse_cases(calibration, contract.question)
    held_out = parse_cases(verification, contract.question)
    ids = {case.case_id for case in cases}
    states = {case.state for case in cases}
    if any(case.case_id in ids or case.state in states for case in held_out):
        raise SchemaError("verification: case id or state also present in calibration")
    return cases


def _calibration_cases(
    plan: _Plan, cases: tuple[Case, ...], records: tuple[DecisionRecord, ...]
) -> tuple[CalibrationCase, ...]:
    if len(cases) != len(records):
        raise IntegrityError("records: calibration record count mismatch")
    policy = replace(plan.contract.policy, threshold=min(plan.grid))
    eligibility = replace(policy, threshold=math.nextafter(0.0, 1.0))
    scored: list[CalibrationCase] = []
    for case, record in zip(cases, records, strict=True):
        request = DecisionRequest(case.case_id, case.state, plan.contract.question)
        if record.case_id != case.case_id or record.capture.request_sha256 != request_sha256(
            request
        ):
            raise IntegrityError("records: case or request mismatch")
        outcome = normalize(record.capture, plan.contract.question, plan.model_identity)
        if outcome != record.outcome or evaluate(outcome, policy) != record.decision:
            raise IntegrityError("records: outcome or decision does not reproduce")
        eligible = evaluate(outcome, eligibility).action == "ACT"
        if eligible and isinstance(outcome, ChoiceAnswer):
            scored.append(
                CalibrationCase(outcome.selected_probability, outcome.choice == case.expected_label)
            )
        else:
            scored.append(CalibrationCase(score=None, correct=False))
    return tuple(scored)


def _collect_calibration(
    model: DecisionModel, plan: _Plan, cases: tuple[Case, ...]
) -> tuple[DecisionRecord, ...]:
    from actseal.runner import REQUEST_TIMEOUT_S  # noqa: PLC0415 - collection only

    if plan.implementation_sha256 != implementation_fingerprint():
        raise IntegrityError(
            "implementation_sha256: new collection requires the exact current implementation"
        )
    policy = replace(plan.contract.policy, threshold=min(plan.grid))
    records: list[DecisionRecord] = []
    for case in cases:
        request = DecisionRequest(case.case_id, case.state, plan.contract.question)
        capture = model.decide(request, timeout_s=REQUEST_TIMEOUT_S)
        outcome = normalize(capture, plan.contract.question, plan.model_identity)
        records.append(DecisionRecord(case.case_id, capture, outcome, evaluate(outcome, policy)))
    return tuple(records)


def _contract_toml(contract: Contract) -> bytes:
    """Emit the ordinary contract grammar, using JSON strings as TOML basic strings."""

    def string(value: str) -> str:
        return json.dumps(value, ensure_ascii=False).replace("\x7f", "\\u007f")

    options = ",".join(
        f"{{label={string(option.label)},description={string(option.description)}}}"
        for option in contract.question.options
    )
    allowed = ",".join(string(label) for label in contract.policy.allowed_labels)
    text = (
        f"schema_version = {contract.schema_version}\nname = {string(contract.name)}\n"
        f"evidence_scope = {string(contract.evidence_scope)}\n"
        f"population = {string(contract.population)}\n"
        f"[question]\nquestion_id = {string(contract.question.question_id)}\n"
        f"instructions = {string(contract.question.instructions)}\noptions = [{options}]\n"
        f"[policy]\nallowed_labels = [{allowed}]\nthreshold = {contract.policy.threshold!r}\n"
        f"[risk]\nmax_risk = {contract.limits.max_risk!r}\n"
        f"min_coverage = {contract.limits.min_coverage!r}\nalpha = {contract.limits.alpha!r}\n"
    )
    return text.encode("utf-8")


def _publish_calibration(
    temporary: Path, plan: _Plan, model: DecisionModel, calibration: str, cases: tuple[Case, ...]
) -> tuple[SelectionResult, str]:
    directory = temporary / "calibration"
    directory.mkdir()
    budget = _Budget(MAX_BUNDLE_BYTES)
    files = {"selection_plan.json": _encoded_document(plan.document(), budget)}
    files["calibration.jsonl"] = _encode_dataset("calibration.jsonl", calibration, budget)
    # The closed file and its self-hash exist before any response is requested.
    _write_file(directory / "selection_plan.json", files["selection_plan.json"])
    records = _collect_calibration(model, plan, cases)
    selection = plan.select(_calibration_cases(plan, cases, records))
    files["records.jsonl"] = _encode_rows("records.jsonl", records, budget)
    files["selection.json"] = _encoded_document(_selection_document(selection), budget)
    files["manifest.json"] = _encoded_document(
        _seal(
            {
                "schema_version": 1,
                "files": {
                    name: {"size": len(data), "sha256": sha256_bytes(data)}
                    for name, data in files.items()
                },
            }
        ),
        budget,
    )
    for name, data in files.items():
        if name != "selection_plan.json":
            _write_file(directory / name, data)
    # Validate our complete output before publishing it or deriving a contract.
    replay_selection(directory)
    if selection.threshold is not None:
        contract = replace(
            plan.contract, policy=replace(plan.contract.policy, threshold=selection.threshold)
        )
        contract_path = temporary / "contract.toml"
        _write_file(contract_path, _contract_toml(contract))
        if parse_contract(contract_path) != contract:
            raise IntegrityError("contract: derived TOML does not round trip")
    return selection, sha256_bytes(files["manifest.json"])


def calibrate_run(
    contract_path: Path,
    calibration_path: Path,
    verification_path: Path,
    destination: Path,
    *,
    model_factory: ModelFactory,
    grid: Sequence[float] = DEFAULT_GRID,
    target_pass_probability: float = 0.8,
    selection_tail: float = DEFAULT_SELECTION_TAIL,
) -> CalibrationRun:
    """Select on calibration only; publish a sidecar and selected contract exclusively."""
    _new_destination(destination)
    contract = parse_contract(contract_path)
    calibration = read_input_text(calibration_path)
    verification = read_input_text(verification_path)
    cases = _split_inputs(contract, calibration, verification)
    n_verify = len(parse_cases(verification, contract.question))
    # Reject bad selection inputs before a provider is opened.
    try:
        select_threshold(
            grid=grid,
            cases=(),
            n_verify=n_verify,
            max_risk=contract.limits.max_risk,
            min_coverage=contract.limits.min_coverage,
            alpha=contract.limits.alpha,
            target_pass_probability=target_pass_probability,
            selection_tail=selection_tail,
        )
    except (TypeError, ValueError) as exc:
        raise SchemaError(f"selection_plan: {exc}") from None
    frozen_grid = tuple(float(t) for t in grid)
    model = model_factory()
    temporary: Path | None = None
    try:
        try:
            identity = model.identity()
            if not isinstance(identity, ModelIdentity):
                raise ProviderSetupError("identity: provider did not report a ModelIdentity")
            plan = _Plan(
                contract,
                frozen_grid,
                float(target_pass_probability),
                float(selection_tail),
                n_verify,
                sha256_bytes(calibration.encode("utf-8")),
                sha256_bytes(verification.encode("utf-8")),
                identity,
                implementation_fingerprint(),
                compatibility.CURRENT_ENGINE,
            )
            temporary = Path(tempfile.mkdtemp(prefix=".actseal-selection-", dir=destination.parent))
            selection, manifest_sha256 = _publish_calibration(
                temporary, plan, model, calibration, cases
            )
        finally:
            model.close()
        _exclusive_rename(temporary, destination)
    except BaseException:
        if temporary is not None:
            shutil.rmtree(temporary, ignore_errors=True)
        raise
    return CalibrationRun(
        destination,
        selection,
        manifest_sha256,
        destination / "contract.toml" if selection.threshold is not None else None,
    )


def _read_sidecar(directory: Path) -> dict[str, bytes]:
    _check_path_text("directory", directory)
    if not stat.S_ISDIR(directory.lstat().st_mode):
        raise SchemaError("calibration: expected a regular directory")
    sizes: dict[str, int] = {}
    budget = _Budget(MAX_BUNDLE_BYTES)
    with os.scandir(directory) as entries:
        for entry in entries:
            if entry.name not in _FILES or entry.name in sizes:
                raise SchemaError("calibration: unexpected file")
            info = entry.stat(follow_symlinks=False)
            if not stat.S_ISREG(info.st_mode) or not 1 <= info.st_size <= MAX_BUNDLE_BYTES:
                raise SchemaError("calibration: expected bounded nonempty regular files")
            budget.charge(info.st_size)
            sizes[entry.name] = info.st_size
    if set(sizes) != set(_FILES):
        raise SchemaError("calibration: missing file")
    raw = {name: _read_exact(directory / name, name, sizes[name]) for name in _FILES}
    manifest = _object(
        _json_document(raw["manifest.json"]), {"schema_version", "files", "sha256"}, "manifest"
    )
    _check_seal(manifest)
    inventory = _object(manifest["files"], set(_DATA_FILES), "manifest.files")
    for name in _DATA_FILES:
        entry_data = _object(inventory[name], {"size", "sha256"}, "manifest entry")
        if type(entry_data["size"]) is not int or entry_data["size"] != sizes[name]:
            raise IntegrityError("manifest: file size mismatch")
        if _digest(entry_data["sha256"], "file sha256") != sha256_bytes(raw[name]):
            raise IntegrityError("manifest: file hash mismatch")
    return raw


def _compare_selection(value: object, expected: SelectionResult) -> None:
    stored = _object(value, {"schema_version", "threshold", "reason", "points"}, "selection")
    if type(stored["schema_version"]) is not int or stored["schema_version"] != 1:
        raise SchemaError("selection: unsupported version")
    threshold = stored["threshold"]
    if threshold is not None:
        threshold = _number(threshold, "threshold")
    if threshold != expected.threshold or stored["reason"] != expected.reason:
        raise IntegrityError("selection: threshold or reason does not reproduce")
    points = stored["points"]
    if type(points) is not list or len(points) != len(expected.points):
        raise SchemaError("selection: grid length mismatch")
    for value_point, expected_point in zip(points, expected.points, strict=True):
        point = _object(
            value_point,
            {"threshold", "accepted", "errors", "predicted_pass_probability"},
            "selection point",
        )
        if _number(point["threshold"], "threshold") != expected_point.threshold:
            raise IntegrityError("selection: grid threshold mismatch")
        for field in ("accepted", "errors"):
            if type(point[field]) is not int or point[field] != getattr(expected_point, field):
                raise IntegrityError("selection: counts do not reproduce")
        probability = _number(point["predicted_pass_probability"], "predicted_pass_probability")
        if not 0.0 <= probability <= 1.0 or not math.isclose(
            probability,
            expected_point.predicted_pass_probability,
            rel_tol=_PROBABILITY_REL_TOL,
            abs_tol=_PROBABILITY_ABS_TOL,
        ):
            raise IntegrityError("selection: predicted probability does not reproduce")


def replay_selection(directory: Path) -> SelectionResult:
    """Recompute selection offline; counts/threshold exact, probabilities abs 1e-10/rel 1e-9."""
    files = _read_sidecar(directory)
    plan = _decode_plan(files["selection_plan.json"])
    if sha256_bytes(files["calibration.jsonl"]) != plan.calibration_sha256:
        raise IntegrityError("calibration_sha256: calibration input mismatch")
    cases = parse_cases(files["calibration.jsonl"].decode("utf-8"), plan.contract.question)
    records = decode_rows("records.jsonl", files["records.jsonl"], DecisionRecord)
    selection = plan.select(_calibration_cases(plan, cases, records))
    _compare_selection(_json_document(files["selection.json"]), selection)
    return selection


def qualify_run(
    contract_path: Path,
    calibration_path: Path,
    verification_path: Path,
    destination: Path,
    *,
    provider: str,
    model_factory: ModelFactory,
    grid: Sequence[float] = DEFAULT_GRID,
    target_pass_probability: float = 0.8,
    selection_tail: float = DEFAULT_SELECTION_TAIL,
) -> QualificationRun:
    """Calibrate, then run the existing lock/verify pipeline on the held-out cases."""
    from actseal.runner import lock_run, verify_run  # noqa: PLC0415 - no runner on replay

    if provider not in PROVIDERS:
        raise SchemaError("provider: unsupported value")
    calibration = calibrate_run(
        contract_path,
        calibration_path,
        verification_path,
        destination,
        model_factory=model_factory,
        grid=grid,
        target_pass_probability=target_pass_probability,
        selection_tail=selection_tail,
    )
    if calibration.contract_path is None:
        return QualificationRun(destination, calibration, None, None, None)
    files = _read_sidecar(destination / "calibration")
    plan = _decode_plan(files["selection_plan.json"])
    lock_path = destination / "lock.json"
    lock = lock_run(
        calibration.contract_path,
        calibration_path,
        verification_path,
        lock_path,
        model_factory=model_factory,
    )
    selected_contract = replace(
        plan.contract,
        policy=replace(
            plan.contract.policy, threshold=cast(float, calibration.selection.threshold)
        ),
    )
    if (
        lock.contract != selected_contract
        or lock.model_identity != plan.model_identity
        or lock.calibration_sha256 != plan.calibration_sha256
        or lock.verification_sha256 != plan.verification_sha256
        or len(lock.verification_cases) != plan.n_verify
        or lock.implementation_sha256 != plan.implementation_sha256
    ):
        raise IntegrityError("qualification: verification lock differs from the selection plan")
    bundle, _ = verify_run(
        lock_path,
        calibration_path,
        verification_path,
        destination / "evidence",
        provider=provider,
        model_factory=model_factory,
    )
    # Provider lifecycle hooks have run since calibration was published. Link
    # only the same complete sidecar that selected this verification contract.
    current_files = _read_sidecar(destination / "calibration")
    if sha256_bytes(current_files["manifest.json"]) != calibration.manifest_sha256:
        raise IntegrityError("qualification: calibration manifest changed during verification")
    replay_selection(destination / "calibration")
    receipt_path = destination / "qualification.json"
    receipt = {
        "schema_version": 1,
        "calibration_manifest_sha256": calibration.manifest_sha256,
        "lock_sha256": lock.sha256,
        "verdict": to_data(bundle.verdict),
    }
    _write_file(receipt_path, _encoded_document(receipt, _Budget(MAX_BUNDLE_BYTES)))
    return QualificationRun(destination, calibration, lock, bundle, receipt_path)
