"""Atomic evidence bundle writing and bounded reading against the real accepted authorities.

Every bundle here is produced with ``create_lock``/``validate_lock``,
``normalize``, ``evaluate``, ``run_fault_campaign`` and ``assess``; the writer
is never handed a stub. Expected manifests and digests are recomputed in this
module with ``hashlib`` and ``json`` directly, independently of
``actseal.evidence``. Destructive paths run only inside pytest temporary
directories. The native exclusive rename is exercised for real on every
supported platform; its unsupported branches are reached by replacing the
platform name or the C-library loader, never by weakening the invariant.
"""

from __future__ import annotations

import ctypes
import errno
import hashlib
import json
import os
import stat
import sys
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import actseal.evidence as evidence_module
from actseal.assessment import REASON_WORKER_INVALIDATED, assess
from actseal.contract import read_input_text
from actseal.errors import IntegrityError, SchemaError
from actseal.evidence import (
    BUNDLE_FILES,
    CALIBRATION_FILE,
    DATA_FILES,
    FAULTS_FILE,
    LOCK_FILE,
    MANIFEST_FILE,
    MAX_BUNDLE_BYTES,
    RECORDS_FILE,
    VERDICT_FILE,
    VERIFICATION_FILE,
    decode_document,
    decode_rows,
    read_bundle_files,
    write_bundle,
)
from actseal.faults import run_fault_campaign
from actseal.locking import MAX_LOCK_BYTES, create_lock, lock_digest, validate_lock
from actseal.normalization import normalize, request_sha256
from actseal.policy import evaluate
from actseal.records import (
    CapturedOutcome,
    Case,
    ChoiceAnswer,
    Contract,
    DecisionRecord,
    DecisionRequest,
    EvidenceBundle,
    FaultResult,
    GateLimits,
    Interval,
    LockedPolicy,
    ModelIdentity,
    PlanLock,
    PolicyDecision,
    ProviderFailure,
    Verdict,
)
from actseal.serialization import canonical_json, to_data
from conftest import HEX_B, make_contract, make_identity

# --------------------------------------------------------------------------- #
# Evidence builders (real authorities only)
# --------------------------------------------------------------------------- #

CALIBRATION = '{"case_id": "c-001", "state": "Calibration one.", "expected_label": "billing"}\n'

GOLD: tuple[tuple[str, str, str], ...] = (
    ("v-001", "Refund missing after cancellation.", "billing"),
    ("v-002", "Login page returns 500.", "technical"),
    ("v-003", "Is there bulk license pricing?", "sales"),
    ("v-004", "Charged twice this month.", "billing"),
    ("v-005", "App crashes on launch.", "technical"),
    ("v-006", "Need a quote for fifty seats.", "sales"),
)
ALL_LABELS = ("billing", "technical", "sales")
ZERO_USAGE = {
    "input_tokens": 0,
    "output_tokens": 0,
    "state_tokens": 0,
    "state_tokens_dropped": 0,
    "truncated": False,
    "truncated_questions": [],
}
FULL = Interval(0.0, 1.0)
ONE_MIB = 1024 * 1024


def verification_jsonl(cases: Sequence[tuple[str, str, str]] = GOLD, newline: str = "\n") -> str:
    return "".join(
        json.dumps(
            {"case_id": case_id, "state": state, "expected_label": label}, ensure_ascii=False
        )
        + newline
        for case_id, state, label in cases
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


def contract_with(
    *,
    allowed: tuple[str, ...] = ALL_LABELS,
    threshold: float = 0.9,
    max_risk: float = 0.05,
    min_coverage: float = 0.5,
    alpha: float = 0.05,
) -> Contract:
    base = make_contract()
    return Contract(
        1,
        base.name,
        base.question,
        LockedPolicy(ALL_LABELS, allowed, threshold),
        GateLimits(max_risk, min_coverage, alpha),
        base.evidence_scope,
        base.population,
    )


def make_lock(
    contract: Contract | None = None,
    identity: ModelIdentity | None = None,
    *,
    calibration: str = CALIBRATION,
    verification: str | None = None,
) -> PlanLock:
    lock = create_lock(
        contract or contract_with(),
        calibration,
        verification if verification is not None else verification_jsonl(),
        identity or make_identity(),
    )
    validate_lock(lock)
    return lock


def answer_json(choice: str, selected: float = 0.95) -> str:
    rest = (1.0 - selected) / (len(ALL_LABELS) - 1)
    probabilities = {label: (selected if label == choice else rest) for label in ALL_LABELS}
    return json.dumps({"type": "choice", "choice": choice, "probabilities": probabilities})


def body_for(lock: PlanLock, choice: str, selected: float = 0.95) -> str:
    inner = answer_json(choice, selected)
    if lock.model_identity.provider != "laya":
        return inner
    envelope = {
        "model": "laya-rl-agent",
        "answers": {lock.contract.question.question_id: json.loads(inner)},
        "usage": dict(ZERO_USAGE),
    }
    return json.dumps(envelope)


def request_for(lock: PlanLock, case: Case) -> DecisionRequest:
    return DecisionRequest(case.case_id, case.state, lock.contract.question)


def capture_for(
    lock: PlanLock,
    case: Case,
    *,
    body: str | None = None,
    failure_code: str | None = None,
    identity: ModelIdentity | None = None,
    warnings: tuple[str, ...] = (),
    fallback_used: bool = False,
    request: DecisionRequest | None = None,
) -> CapturedOutcome:
    if body is None and failure_code is None:
        body = body_for(lock, case.expected_label)
    return CapturedOutcome(
        request_sha256(request or request_for(lock, case)),
        identity or lock.model_identity,
        body,
        failure_code,
        warnings,
        fallback_used,
    )


def record_from_capture(lock: PlanLock, case: Case, capture: CapturedOutcome) -> DecisionRecord:
    """A faithful record: real normalization against the lock, real policy evaluation."""
    outcome = normalize(capture, lock.contract.question, lock.model_identity)
    decision = evaluate(outcome, lock.contract.policy)
    return DecisionRecord(case.case_id, capture, outcome, decision)


def record_for(lock: PlanLock, case: Case, **capture_fields: object) -> DecisionRecord:
    capture = capture_for(lock, case, **capture_fields)  # type: ignore[arg-type]
    return record_from_capture(lock, case, capture)


def records_for(
    lock: PlanLock, choices: Sequence[str | None] | None = None, selected: float = 0.95
) -> tuple[DecisionRecord, ...]:
    """One faithful ACT-shaped record per locked case; ``None`` means the gold label."""
    cases = lock.verification_cases
    picks = choices if choices is not None else [None] * len(cases)
    assert len(picks) == len(cases)
    return tuple(
        record_for(lock, case, body=body_for(lock, pick or case.expected_label, selected))
        for case, pick in zip(cases, picks, strict=True)
    )


def make_bundle(
    lock: PlanLock | None = None,
    records: Sequence[DecisionRecord] | None = None,
    faults: Sequence[FaultResult] | None = None,
    verdict: Verdict | None = None,
    *,
    calibration: str = CALIBRATION,
    verification: str | None = None,
) -> EvidenceBundle:
    """A complete bundle whose verdict is, by default, the real fresh assessment."""
    lock = lock or make_lock()
    typed_records = tuple(records) if records is not None else records_for(lock)
    typed_faults = tuple(faults) if faults is not None else run_fault_campaign(lock)
    return EvidenceBundle(
        lock,
        calibration,
        verification if verification is not None else verification_jsonl(),
        typed_records,
        typed_faults,
        verdict or assess(typed_records, lock, typed_faults),
    )


# --------------------------------------------------------------------------- #
# Independent wire helpers (hashlib/json only; no actseal.evidence internals)
# --------------------------------------------------------------------------- #


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compact(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def seal_manifest(unsealed: Mapping[str, object]) -> bytes:
    """Independent manifest encoding: self-hash over everything but ``sha256``, plus LF."""
    sealed = {**unsealed, "sha256": sha256_hex(compact(unsealed))}
    return compact(sealed) + b"\n"


def independent_manifest(files: Mapping[str, bytes]) -> bytes:
    inventory = {
        name: {"size": len(data), "sha256": sha256_hex(data)} for name, data in files.items()
    }
    return seal_manifest({"schema_version": 1, "files": inventory})


def read_files(directory: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in sorted(directory.iterdir())}


def rewrite(directory: Path, changes: Mapping[str, bytes]) -> None:
    """The adversary: replace files and recompute every ordinary manifest hash."""
    for name, data in changes.items():
        (directory / name).write_bytes(data)
    files = {name: (directory / name).read_bytes() for name in DATA_FILES}
    (directory / MANIFEST_FILE).write_bytes(independent_manifest(files))


def rows_of(data: bytes) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in data.decode("utf-8").split("\n")[:-1]:
        row = json.loads(line)
        assert isinstance(row, dict)
        rows.append(row)
    return rows


def rows_bytes(rows: Sequence[Mapping[str, object]]) -> bytes:
    return b"".join(compact(row) + b"\n" for row in rows)


def nested(row: Mapping[str, object], *keys: str) -> dict[str, object]:
    """Descend into decoded JSON objects, asserting each step is an object."""
    current: object = row
    for key in keys:
        assert isinstance(current, dict)
        current = current[key]
    assert isinstance(current, dict)
    return current


def temp_leftovers(parent: Path) -> list[str]:
    return sorted(name for name in os.listdir(parent) if name.startswith(".actseal-bundle-"))


def written(tmp_path: Path, bundle: EvidenceBundle | None = None, name: str = "run") -> Path:
    return write_bundle(bundle or make_bundle(), tmp_path / name)


# --------------------------------------------------------------------------- #
# Writer: determinism, canonical bytes and raw dataset preservation
# --------------------------------------------------------------------------- #


def test_write_is_byte_identical_across_independent_roots(tmp_path: Path) -> None:
    bundle = make_bundle()
    before = to_data(bundle)
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    first = write_bundle(bundle, tmp_path / "a" / "run")
    second = write_bundle(bundle, tmp_path / "b" / "run")
    assert first == tmp_path / "a" / "run"
    assert sorted(path.name for path in first.iterdir()) == sorted(BUNDLE_FILES)
    assert read_files(first) == read_files(second)
    assert all((first / name).is_file() for name in BUNDLE_FILES)
    assert not any((first / name).is_symlink() for name in BUNDLE_FILES)
    assert to_data(bundle) == before


def test_manifest_matches_an_independent_digest_computation(tmp_path: Path) -> None:
    out = written(tmp_path)
    files = read_files(out)
    data_files = {name: files[name] for name in DATA_FILES}
    assert files[MANIFEST_FILE] == independent_manifest(data_files)
    manifest = json.loads(files[MANIFEST_FILE])
    assert set(manifest) == {"schema_version", "files", "sha256"}
    assert manifest["schema_version"] == 1
    assert set(manifest["files"]) == set(DATA_FILES)
    for name, data in data_files.items():
        assert manifest["files"][name] == {"size": len(data), "sha256": sha256_hex(data)}
    unsealed = {"schema_version": 1, "files": manifest["files"]}
    assert manifest["sha256"] == sha256_hex(compact(unsealed))


def test_written_documents_are_canonical_json_with_one_lf(tmp_path: Path) -> None:
    bundle = make_bundle()
    files = read_files(written(tmp_path, bundle))
    assert files[LOCK_FILE] == canonical_json(to_data(bundle.lock)) + b"\n"
    assert files[VERDICT_FILE] == canonical_json(to_data(bundle.verdict)) + b"\n"
    assert files[RECORDS_FILE] == b"".join(
        canonical_json(to_data(record)) + b"\n" for record in bundle.records
    )
    assert files[FAULTS_FILE] == b"".join(
        canonical_json(to_data(fault)) + b"\n" for fault in bundle.faults
    )
    assert files[CALIBRATION_FILE] == CALIBRATION.encode("utf-8")
    assert files[VERIFICATION_FILE] == verification_jsonl().encode("utf-8")
    assert len(files[RECORDS_FILE].split(b"\n")) == len(bundle.records) + 1
    assert len(files[FAULTS_FILE].split(b"\n")) == 7


def test_raw_dataset_bytes_with_crlf_and_unicode_are_preserved(tmp_path: Path) -> None:
    cases = (
        ("v-001", "Café ☕ refund \U0001f4b3 missing.", "billing"),
        ("v-002", "ログインページ returns 500.", "technical"),
        ("v-003", "Bulk license pricing?\ttabs kept", "sales"),
    )
    verification = verification_jsonl(cases, newline="\r\n")
    calibration = (
        '{"case_id": "c-001", "state": "Calibration über one.", "expected_label": "billing"}\r\n'
    )
    lock = make_lock(calibration=calibration, verification=verification)
    bundle = make_bundle(lock, calibration=calibration, verification=verification)
    files = read_files(written(tmp_path, bundle))
    assert files[VERIFICATION_FILE] == verification.encode("utf-8")
    assert files[CALIBRATION_FILE] == calibration.encode("utf-8")
    assert b"\r\n" in files[VERIFICATION_FILE]
    assert "☕".encode() in files[VERIFICATION_FILE]
    assert files[RECORDS_FILE].count(b"\r") == 0
    assert read_bundle_files(tmp_path / "run")[VERIFICATION_FILE] == verification.encode("utf-8")


def test_sealed_files_contain_no_host_paths_or_volatile_values(tmp_path: Path) -> None:
    out = written(tmp_path)
    blob = b"".join(read_files(out).values())
    assert str(tmp_path).encode() not in blob
    assert str(out.resolve()).encode() not in blob
    for name in ("timestamp", "duration", "pid", "created_at", "hostname", "authorization"):
        assert name.encode() not in blob


# --------------------------------------------------------------------------- #
# Writer: new destinations only, exclusive publication and cleanup
# --------------------------------------------------------------------------- #


def test_existing_directory_file_and_symlink_destinations_are_refused(tmp_path: Path) -> None:
    bundle = make_bundle()
    directory = tmp_path / "dir"
    directory.mkdir()
    (directory / "keep").write_bytes(b"original")
    file = tmp_path / "file"
    file.write_bytes(b"original file")
    link = tmp_path / "link"
    link.symlink_to(tmp_path / "missing")
    for destination in (directory, file, link):
        with pytest.raises(FileExistsError, match="already exists"):
            write_bundle(bundle, destination)
    assert (directory / "keep").read_bytes() == b"original"
    assert sorted(path.name for path in directory.iterdir()) == ["keep"]
    assert file.read_bytes() == b"original file"
    assert link.is_symlink()
    assert not link.exists()
    assert temp_leftovers(tmp_path) == []


def test_write_into_a_missing_parent_propagates_the_os_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        write_bundle(make_bundle(), tmp_path / "missing" / "run")
    assert not (tmp_path / "missing").exists()


def test_mid_write_failure_leaves_no_partial_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "sibling").write_bytes(b"sibling")
    real_write = evidence_module._write_file

    def failing(path: Path, data: bytes) -> None:
        if path.name == RECORDS_FILE:
            raise OSError(errno.ENOSPC, "injected write failure")
        real_write(path, data)

    monkeypatch.setattr(evidence_module, "_write_file", failing)
    with pytest.raises(OSError, match="injected"):
        write_bundle(make_bundle(), tmp_path / "run")
    assert sorted(os.listdir(tmp_path)) == ["sibling"]
    assert (tmp_path / "sibling").read_bytes() == b"sibling"


def test_raced_empty_destination_directory_survives_the_real_exclusive_rename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An empty destination appears after the preliminary existence check; the native
    exclusive rename must refuse it and leave both directories untouched."""
    real_rename = evidence_module._exclusive_rename
    destination = tmp_path / "run"
    seen: list[list[str]] = []

    def racing(source: Path, target: Path) -> None:
        assert target == destination
        assert not target.exists()
        target.mkdir()
        seen.append(sorted(os.listdir(source)))
        real_rename(source, target)

    monkeypatch.setattr(evidence_module, "_exclusive_rename", racing)
    with pytest.raises(FileExistsError):
        write_bundle(make_bundle(), destination)
    assert seen == [sorted(BUNDLE_FILES)]
    assert destination.is_dir()
    assert os.listdir(destination) == []
    assert temp_leftovers(tmp_path) == []


def test_raced_destination_file_survives_the_real_exclusive_rename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_rename = evidence_module._exclusive_rename
    destination = tmp_path / "run"

    def racing(source: Path, target: Path) -> None:
        target.write_bytes(b"raced file")
        real_rename(source, target)

    monkeypatch.setattr(evidence_module, "_exclusive_rename", racing)
    with pytest.raises(OSError, match="exclusive rename failed"):
        write_bundle(make_bundle(), destination)
    assert destination.is_file()
    assert destination.read_bytes() == b"raced file"
    assert temp_leftovers(tmp_path) == []


def test_exclusive_rename_publishes_to_an_absent_destination_and_refuses_an_existing_one(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "inner").write_bytes(b"inner")
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    with pytest.raises(FileExistsError):
        evidence_module._exclusive_rename(source, occupied)
    assert os.listdir(occupied) == []
    assert os.listdir(source) == ["inner"]
    evidence_module._exclusive_rename(source, tmp_path / "published")
    assert not source.exists()
    assert (tmp_path / "published" / "inner").read_bytes() == b"inner"


def test_unsupported_platform_fails_explicitly_without_publishing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    with pytest.raises(NotImplementedError, match="unsupported platform"):
        write_bundle(make_bundle(), tmp_path / "run")
    assert not (tmp_path / "run").exists()
    assert temp_leftovers(tmp_path) == []


def test_missing_native_symbol_fails_explicitly_without_publishing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(evidence_module, "_load_libc", SimpleNamespace)
    with pytest.raises(NotImplementedError, match="not available"):
        write_bundle(make_bundle(), tmp_path / "run")
    assert not (tmp_path / "run").exists()
    assert temp_leftovers(tmp_path) == []


@pytest.mark.parametrize("code", [errno.EINVAL, errno.ENOSYS, errno.ENOTSUP, errno.EXDEV])
def test_unsupported_filesystem_errors_propagate_with_their_errno(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, code: int
) -> None:
    def refusing(*_args: object) -> int:
        ctypes.set_errno(code)
        return -1

    fake = SimpleNamespace(renamex_np=refusing, renameat2=refusing)
    monkeypatch.setattr(evidence_module, "_load_libc", lambda: fake)
    with pytest.raises(OSError, match="exclusive rename failed") as info:
        write_bundle(make_bundle(), tmp_path / "run")
    assert info.value.errno == code
    assert not isinstance(info.value, FileExistsError)
    assert not (tmp_path / "run").exists()
    assert temp_leftovers(tmp_path) == []


def test_relative_destination_is_published_from_the_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    out = write_bundle(make_bundle(), Path("relative-run"))
    assert out == Path("relative-run")
    assert sorted(os.listdir(tmp_path / "relative-run")) == sorted(BUNDLE_FILES)


# --------------------------------------------------------------------------- #
# Writer: semantic validation before sealing
# --------------------------------------------------------------------------- #


def test_writer_rejects_a_forged_verdict(tmp_path: Path) -> None:
    lock = make_lock()
    records = records_for(lock)
    faults = run_fault_campaign(lock)
    honest = assess(records, lock, faults)
    assert honest.status == "INCONCLUSIVE"
    forged = replace(honest, status="PASS", reasons=("contract.satisfied",))
    with pytest.raises(IntegrityError, match="verdict"):
        write_bundle(make_bundle(lock, records, faults, forged), tmp_path / "run")
    assert not (tmp_path / "run").exists()


def test_writer_rejects_records_that_do_not_reproduce(tmp_path: Path) -> None:
    lock = make_lock()
    records = list(records_for(lock))
    records[0] = replace(
        records[0], decision=PolicyDecision("ABSTAIN", None, "policy.low_confidence", False)
    )
    faults = run_fault_campaign(lock)
    dishonest = assess(records, lock, faults)
    assert dishonest.status == "ERROR"
    with pytest.raises(IntegrityError, match="evidence"):
        write_bundle(make_bundle(lock, records, faults, dishonest), tmp_path / "run")
    assert not (tmp_path / "run").exists()


def test_writer_rejects_inputs_that_do_not_match_the_lock(tmp_path: Path) -> None:
    lock = make_lock()
    other = verification_jsonl(tuple((cid, state + " ", label) for cid, state, label in GOLD))
    with pytest.raises(IntegrityError, match="verification_sha256"):
        write_bundle(make_bundle(lock, verification=other), tmp_path / "run")
    with pytest.raises(IntegrityError, match="calibration_sha256"):
        write_bundle(make_bundle(lock, calibration=CALIBRATION + " "), tmp_path / "run")


def test_writer_rejects_a_tampered_lock(tmp_path: Path) -> None:
    lock = make_lock()
    tampered = replace(lock, sha256="1" * 64)
    records = records_for(tampered)
    faults = run_fault_campaign(tampered)
    verdict = assess(records, tampered, faults)
    assert verdict.status == "ERROR"
    with pytest.raises(IntegrityError, match="sha256"):
        write_bundle(make_bundle(tampered, records, faults, verdict), tmp_path / "run")


def test_writer_preserves_a_complete_infrastructure_error_bundle(tmp_path: Path) -> None:
    lock = make_lock(identity=laya_identity())
    records = list(records_for(lock))
    records[2] = record_for(lock, lock.verification_cases[2], failure_code="timeout")
    faults = run_fault_campaign(lock)
    verdict = assess(records, lock, faults)
    assert verdict.status == "ERROR"
    assert verdict.reasons == (REASON_WORKER_INVALIDATED,)
    out = write_bundle(make_bundle(lock, records, faults, verdict), tmp_path / "run")
    files = read_files(out)
    assert len(rows_of(files[RECORDS_FILE])) == 6
    stored = json.loads(files[VERDICT_FILE])
    assert stored["status"] == "ERROR"
    assert stored["total"] == 0


def test_writer_rejects_an_oversized_record_row(tmp_path: Path) -> None:
    lock = make_lock()
    case = lock.verification_cases[0]
    huge_choice = "x" * (ONE_MIB + 1)
    body = json.dumps(
        {"type": "choice", "choice": huge_choice, "probabilities": dict.fromkeys(ALL_LABELS, 0.0)}
    )
    faithful = record_for(lock, case, body=body)
    assert faithful.outcome == ProviderFailure(
        "unknown_choice", ("normalize.unknown_choice",), False
    )
    assert faithful.decision.action == "DENY"
    records = (faithful, *records_for(lock)[1:])
    with pytest.raises(SchemaError, match=r"records\.jsonl\[0\]: row exceeds"):
        write_bundle(make_bundle(lock, records), tmp_path / "run")
    assert not (tmp_path / "run").exists()


def test_writer_rejects_argument_type_misuse(tmp_path: Path) -> None:
    bundle = make_bundle()
    with pytest.raises(SchemaError, match="bundle"):
        write_bundle(to_data(bundle), tmp_path / "run")  # type: ignore[arg-type]
    with pytest.raises(SchemaError, match="destination"):
        write_bundle(bundle, str(tmp_path / "run"))  # type: ignore[arg-type]
    assert temp_leftovers(tmp_path) == []


def test_denominator_failures_and_malformed_bodies_are_written_as_data(tmp_path: Path) -> None:
    lock = make_lock()
    cases = lock.verification_cases
    records = (
        record_for(lock, cases[0]),
        record_for(lock, cases[1], body="{"),
        record_for(lock, cases[2], body=body_for(lock, "nowhere")),
        record_for(lock, cases[3], failure_code="rate_limit"),
        record_for(lock, cases[4], body=body_for(lock, "technical", 0.5)),
        record_for(lock, cases[5], fallback_used=True),
    )
    actions = [record.decision.action for record in records]
    assert actions == ["ACT", "ESCALATE", "DENY", "ESCALATE", "ABSTAIN", "ESCALATE"]
    bundle = make_bundle(lock, records)
    assert bundle.verdict.status == "INCONCLUSIVE"
    assert (bundle.verdict.total, bundle.verdict.accepted) == (6, 1)
    out = write_bundle(bundle, tmp_path / "run")
    rows = rows_of(read_files(out)[RECORDS_FILE])
    assert [nested(row, "decision")["action"] for row in rows] == actions
    assert nested(rows[1], "capture")["body_json"] == "{"


# --------------------------------------------------------------------------- #
# Reader: structure, symlinks, sizes
# --------------------------------------------------------------------------- #


def test_reader_returns_the_exact_written_bytes(tmp_path: Path) -> None:
    out = written(tmp_path)
    files = read_bundle_files(out)
    assert files == read_files(out)
    assert list(files) == list(BUNDLE_FILES)


def test_reader_rejects_a_missing_or_nondirectory_bundle(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        read_bundle_files(tmp_path / "missing")
    file = tmp_path / "file"
    file.write_bytes(b"{}\n")
    with pytest.raises(SchemaError, match="must be a directory"):
        read_bundle_files(file)
    with pytest.raises(SchemaError, match="bundle"):
        read_bundle_files(str(tmp_path))  # type: ignore[arg-type]


def test_reader_rejects_a_symlinked_bundle_directory(tmp_path: Path) -> None:
    out = written(tmp_path)
    link = tmp_path / "link"
    link.symlink_to(out, target_is_directory=True)
    with pytest.raises(SchemaError, match="must not be a symlink"):
        read_bundle_files(link)
    assert read_bundle_files(out)


def _structure_mutations() -> dict[str, Callable[[Path], None]]:
    def missing(out: Path) -> None:
        (out / FAULTS_FILE).unlink()

    def extra(out: Path) -> None:
        (out / "notes.txt").write_bytes(b"extra")

    def hidden_extra(out: Path) -> None:
        (out / ".DS_Store").write_bytes(b"")

    def renamed(out: Path) -> None:
        (out / VERDICT_FILE).rename(out / "Verdict.json")

    def symlinked_file(out: Path) -> None:
        target = out.parent / "elsewhere.json"
        target.write_bytes((out / VERDICT_FILE).read_bytes())
        (out / VERDICT_FILE).unlink()
        (out / VERDICT_FILE).symlink_to(target)

    def subdirectory(out: Path) -> None:
        (out / RECORDS_FILE).unlink()
        (out / RECORDS_FILE).mkdir()

    def fifo(out: Path) -> None:
        (out / CALIBRATION_FILE).unlink()
        os.mkfifo(out / CALIBRATION_FILE)

    def empty(out: Path) -> None:
        (out / VERIFICATION_FILE).write_bytes(b"")

    def oversized_lock(out: Path) -> None:
        os.truncate(out / LOCK_FILE, MAX_LOCK_BYTES + 1)

    def oversized_aggregate(out: Path) -> None:
        os.truncate(out / RECORDS_FILE, MAX_BUNDLE_BYTES)

    def oversized_single(out: Path) -> None:
        os.truncate(out / FAULTS_FILE, MAX_BUNDLE_BYTES + 1)

    return {
        "missing_file": missing,
        "extra_file": extra,
        "hidden_extra_file": hidden_extra,
        "renamed_file": renamed,
        "symlinked_file": symlinked_file,
        "subdirectory": subdirectory,
        "fifo": fifo,
        "empty_file": empty,
        "oversized_lock": oversized_lock,
        "oversized_aggregate": oversized_aggregate,
        "oversized_single_file": oversized_single,
    }


@pytest.mark.parametrize("mutation", sorted(_structure_mutations()))
def test_reader_rejects_structural_defects_before_reading_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    out = written(tmp_path)
    _structure_mutations()[mutation](out)
    opened: list[str] = []

    def spying(path: Path, *, limit: int) -> str:
        opened.append(path.name)
        return read_input_text(path, limit=limit)

    monkeypatch.setattr(evidence_module, "read_input_text", spying)
    with pytest.raises(SchemaError):
        read_bundle_files(out)
    assert opened == []


def test_reader_rejects_a_file_whose_size_grew_after_inspection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = written(tmp_path)
    real_inspect = evidence_module._inspect

    def inspect_then_grow(bundle: Path) -> dict[str, int]:
        sizes = real_inspect(bundle)
        with (bundle / FAULTS_FILE).open("ab") as handle:
            handle.write(b"\n")
        return sizes

    monkeypatch.setattr(evidence_module, "_inspect", inspect_then_grow)
    with pytest.raises((SchemaError, IntegrityError)):
        read_bundle_files(out)


def test_reader_rejects_invalid_utf8_in_any_file(tmp_path: Path) -> None:
    out = written(tmp_path)
    invalid = b'{"case_id":"v","state":"\xff","expected_label":"billing"}\n'
    rewrite(out, {VERIFICATION_FILE: invalid})
    with pytest.raises(SchemaError, match="valid UTF-8"):
        read_bundle_files(out)


# --------------------------------------------------------------------------- #
# Reader: manifest shape and hashes
# --------------------------------------------------------------------------- #


def _manifest_of(out: Path) -> dict[str, object]:
    value = json.loads((out / MANIFEST_FILE).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _unsealed(out: Path) -> dict[str, object]:
    manifest = _manifest_of(out)
    return {"schema_version": manifest["schema_version"], "files": manifest["files"]}


def _files_entry(unsealed: Mapping[str, object]) -> dict[str, dict[str, object]]:
    files = unsealed["files"]
    assert isinstance(files, dict)
    return files


_Edit = Callable[[dict[str, object]], None]


def _edit(apply: _Edit) -> Callable[[Path], bytes]:
    """Apply ``apply`` to the unsealed manifest of a written bundle and reseal it."""

    def build(out: Path) -> bytes:
        unsealed = _unsealed(out)
        apply(unsealed)
        return seal_manifest(unsealed)

    return build


def _set_top(key: str, value: object) -> _Edit:
    def apply(unsealed: dict[str, object]) -> None:
        unsealed[key] = value

    return apply


def _set_entry(name: str, key: str, value: object) -> _Edit:
    def apply(unsealed: dict[str, object]) -> None:
        _files_entry(unsealed)[name][key] = value

    return apply


def _rename_entry(old: str, new: str) -> _Edit:
    def apply(unsealed: dict[str, object]) -> None:
        files = _files_entry(unsealed)
        files[new] = files.pop(old)

    return apply


def _add_entry(name: str) -> _Edit:
    def apply(unsealed: dict[str, object]) -> None:
        _files_entry(unsealed)[name] = {"size": 1, "sha256": "0" * 64}

    return apply


def _drop_entry(name: str) -> _Edit:
    def apply(unsealed: dict[str, object]) -> None:
        _files_entry(unsealed).pop(name)

    return apply


def _drop_entry_key(name: str, key: str) -> _Edit:
    def apply(unsealed: dict[str, object]) -> None:
        _files_entry(unsealed)[name].pop(key)

    return apply


def _mutate_entry(name: str, key: str, change: Callable[[object], object]) -> _Edit:
    def apply(unsealed: dict[str, object]) -> None:
        entry = _files_entry(unsealed)[name]
        entry[key] = change(entry[key])

    return apply


def _deeply_nested() -> object:
    nested: object = 1
    for _ in range(33):
        nested = [nested]
    return nested


def _raw_manifest_mutations() -> dict[str, Callable[[Path], bytes]]:
    """Mutations that cannot be expressed as a resealed edit."""

    def missing_files_key(out: Path) -> bytes:
        del out
        return seal_manifest({"schema_version": 1})

    def non_string_self_hash(out: Path) -> bytes:
        return compact({**_unsealed(out), "sha256": 1}) + b"\n"

    def pretty_printed(out: Path) -> bytes:
        return json.dumps(_manifest_of(out), sort_keys=True, indent=2).encode("utf-8") + b"\n"

    def missing_terminal_lf(out: Path) -> bytes:
        return (out / MANIFEST_FILE).read_bytes().rstrip(b"\n")

    def duplicate_key(out: Path) -> bytes:
        data = (out / MANIFEST_FILE).read_bytes()
        return data.replace(b'"schema_version":1', b'"schema_version":1,"schema_version":1', 1)

    def not_an_object(out: Path) -> bytes:
        del out
        return b"[]\n"

    def invalid_json(out: Path) -> bytes:
        del out
        return b"{\n"

    def broken_self_hash(out: Path) -> bytes:
        return compact({**_unsealed(out), "sha256": "2" * 64}) + b"\n"

    return {
        "missing_files_key": missing_files_key,
        "non_string_self_hash": non_string_self_hash,
        "pretty_printed": pretty_printed,
        "missing_terminal_lf": missing_terminal_lf,
        "duplicate_key": duplicate_key,
        "not_an_object": not_an_object,
        "invalid_json": invalid_json,
        "broken_self_hash": broken_self_hash,
    }


def _manifest_mutations() -> dict[str, tuple[Callable[[Path], bytes], type[Exception]]]:
    schema: dict[str, Callable[[Path], bytes]] = {
        "unknown_version": _edit(_set_top("schema_version", 2)),
        "bool_version": _edit(_set_top("schema_version", True)),
        "extra_key": _edit(_set_top("created", "2026-10-06")),
        "traversal_name": _edit(_rename_entry(VERDICT_FILE, "../" + VERDICT_FILE)),
        "absolute_name": _edit(_rename_entry(FAULTS_FILE, "/etc/passwd")),
        "manifest_inventories_itself": _edit(_add_entry(MANIFEST_FILE)),
        "unsupported_extra_name": _edit(_add_entry("adapter.py")),
        "missing_name": _edit(_drop_entry(LOCK_FILE)),
        "entry_extra_key": _edit(_set_entry(LOCK_FILE, "mtime", 0)),
        "entry_missing_key": _edit(_drop_entry_key(LOCK_FILE, "size")),
        "bool_size": _edit(_set_entry(VERDICT_FILE, "size", True)),
        "float_size": _edit(_mutate_entry(VERDICT_FILE, "size", lambda v: float(str(v)))),
        "zero_size": _edit(_set_entry(VERDICT_FILE, "size", 0)),
        "oversized_lock_size": _edit(_set_entry(LOCK_FILE, "size", MAX_LOCK_BYTES + 1)),
        "uppercase_digest": _edit(_mutate_entry(VERDICT_FILE, "sha256", lambda v: str(v).upper())),
        "short_digest": _edit(_set_entry(VERDICT_FILE, "sha256", "ab" * 31)),
        "deep_nesting": _edit(_set_entry(LOCK_FILE, "size", _deeply_nested())),
    }
    integrity: dict[str, Callable[[Path], bytes]] = {
        "wrong_size": _edit(_mutate_entry(RECORDS_FILE, "size", lambda v: int(str(v)) + 1)),
        "wrong_file_hash": _edit(_set_entry(RECORDS_FILE, "sha256", "1" * 64)),
    }
    raw = _raw_manifest_mutations()
    result: dict[str, tuple[Callable[[Path], bytes], type[Exception]]] = {}
    for name, build in {**schema, **raw}.items():
        result[name] = (build, SchemaError)
    for name, build in integrity.items():
        result[name] = (build, IntegrityError)
    result["broken_self_hash"] = (raw["broken_self_hash"], IntegrityError)
    return result


@pytest.mark.parametrize("mutation", sorted(_manifest_mutations()))
def test_reader_rejects_malformed_or_mismatched_manifests(tmp_path: Path, mutation: str) -> None:
    out = written(tmp_path)
    build, expected = _manifest_mutations()[mutation]
    (out / MANIFEST_FILE).write_bytes(build(out))
    with pytest.raises(expected):
        read_bundle_files(out)


def test_reader_rejects_a_changed_file_even_with_a_valid_manifest(tmp_path: Path) -> None:
    out = written(tmp_path)
    data = (out / VERDICT_FILE).read_bytes()
    assert b"INCONCLUSIVE" in data
    (out / VERDICT_FILE).write_bytes(data.replace(b"INCONCLUSIVE", b"XNCONCLUSIVE"))
    with pytest.raises(IntegrityError, match=r"verdict\.json\.sha256"):
        read_bundle_files(out)
    (out / VERDICT_FILE).write_bytes(data.replace(b"INCONCLUSIVE", b"PASS"))
    with pytest.raises(IntegrityError, match=r"verdict\.json\.size"):
        read_bundle_files(out)


def test_reader_accepts_an_independently_recomputed_manifest(tmp_path: Path) -> None:
    out = written(tmp_path)
    data = (out / VERDICT_FILE).read_bytes()
    rewrite(out, {VERDICT_FILE: data.replace(b"INCONCLUSIVE", b"PASS")})
    files = read_bundle_files(out)
    assert b"PASS" in files[VERDICT_FILE]


def test_reader_does_not_follow_a_symlinked_file_even_when_hashes_match(tmp_path: Path) -> None:
    out = written(tmp_path)
    target = tmp_path / "outside.jsonl"
    target.write_bytes((out / FAULTS_FILE).read_bytes())
    (out / FAULTS_FILE).unlink()
    (out / FAULTS_FILE).symlink_to(target)
    with pytest.raises(SchemaError, match="symlink"):
        read_bundle_files(out)


def test_file_permissions_are_regular_and_directory_is_private(tmp_path: Path) -> None:
    out = written(tmp_path)
    for name in BUNDLE_FILES:
        mode = (out / name).stat().st_mode
        assert stat.S_ISREG(mode)
    assert stat.S_IMODE(out.stat().st_mode) & 0o077 == 0


# --------------------------------------------------------------------------- #
# Strict canonical decoding of rows and documents
# --------------------------------------------------------------------------- #


def test_decode_rows_round_trips_written_records_and_faults(tmp_path: Path) -> None:
    bundle = make_bundle()
    files = read_files(written(tmp_path, bundle))
    assert decode_rows(RECORDS_FILE, files[RECORDS_FILE], DecisionRecord) == bundle.records
    assert decode_rows(FAULTS_FILE, files[FAULTS_FILE], FaultResult) == bundle.faults
    assert decode_document(VERDICT_FILE, files[VERDICT_FILE], Verdict) == bundle.verdict
    assert decode_document(LOCK_FILE, files[LOCK_FILE], PlanLock) == bundle.lock


def _row_mutations() -> dict[str, Callable[[bytes], bytes]]:
    def oversized(data: bytes) -> bytes:
        rows = rows_of(data)
        nested(rows[0], "capture")["body_json"] = "x" * ONE_MIB
        return rows_bytes(rows)

    def no_terminal_lf(data: bytes) -> bytes:
        return data.rstrip(b"\n")

    def crlf_rows(data: bytes) -> bytes:
        return data.replace(b"\n", b"\r\n")

    def blank_interior(data: bytes) -> bytes:
        first, rest = data.split(b"\n", 1)
        return first + b"\n\n" + rest

    def non_canonical_spacing(data: bytes) -> bytes:
        return data.replace(b'"case_id":', b'"case_id": ', 1)

    def unsorted_keys(data: bytes) -> bytes:
        rows = rows_of(data)
        text = json.dumps(rows[0], ensure_ascii=False, separators=(",", ":"))
        reordered = json.dumps(dict(reversed(list(rows[0].items()))), separators=(",", ":"))
        assert reordered != text
        return reordered.encode() + b"\n" + rows_bytes(rows[1:])

    def unknown_field(data: bytes) -> bytes:
        rows = rows_of(data)
        rows[0]["timestamp"] = "2026-10-06T00:00:00Z"
        return rows_bytes(rows)

    def missing_field(data: bytes) -> bytes:
        rows = rows_of(data)
        rows[0].pop("decision")
        return rows_bytes(rows)

    def duplicate_key(data: bytes) -> bytes:
        return data.replace(b'"case_id":"v-001"', b'"case_id":"v-001","case_id":"v-001"', 1)

    def nonfinite(data: bytes) -> bytes:
        assert b'"selected_probability":0.95' in data
        return data.replace(b'"selected_probability":0.95', b'"selected_probability":NaN', 1)

    def deep_nesting(data: bytes) -> bytes:
        rows = rows_of(data)
        nested: object = 1
        for _ in range(33):
            nested = [nested]
        rows[0]["capture"] = nested
        return rows_bytes(rows)

    def bool_flag(data: bytes) -> bytes:
        rows = rows_of(data)
        nested(rows[0], "decision")["fallback_used"] = 0
        return rows_bytes(rows)

    def too_many_rows(data: bytes) -> bytes:
        return data + b"{}\n" * 10_000

    def empty(data: bytes) -> bytes:
        del data
        return b""

    def only_lf(data: bytes) -> bytes:
        del data
        return b"\n"

    def array_row(data: bytes) -> bytes:
        return b"[]\n" + data

    return {
        "oversized_row": oversized,
        "no_terminal_lf": no_terminal_lf,
        "crlf_rows": crlf_rows,
        "blank_interior": blank_interior,
        "non_canonical_spacing": non_canonical_spacing,
        "unsorted_keys": unsorted_keys,
        "unknown_field": unknown_field,
        "missing_field": missing_field,
        "duplicate_key": duplicate_key,
        "nonfinite": nonfinite,
        "deep_nesting": deep_nesting,
        "bool_flag": bool_flag,
        "too_many_rows": too_many_rows,
        "empty": empty,
        "only_lf": only_lf,
        "array_row": array_row,
    }


@pytest.mark.parametrize("mutation", sorted(_row_mutations()))
def test_decode_rows_rejects_every_wire_defect(tmp_path: Path, mutation: str) -> None:
    files = read_files(written(tmp_path))
    mutated = _row_mutations()[mutation](files[RECORDS_FILE])
    with pytest.raises(SchemaError):
        decode_rows(RECORDS_FILE, mutated, DecisionRecord)


def test_decode_rows_row_limit_excludes_the_lf_terminator() -> None:
    """A row of exactly 1 MiB excluding its LF is a size-legal row (its content then fails
    strict decoding); one more byte is rejected by size first."""
    exact = b"x" * ONE_MIB + b"\n"
    with pytest.raises(SchemaError, match=r"\[0\]: \$"):
        decode_rows(RECORDS_FILE, exact, DecisionRecord)
    with pytest.raises(SchemaError, match="row exceeds"):
        decode_rows(RECORDS_FILE, b"x" * (ONE_MIB + 1) + b"\n", DecisionRecord)
    with pytest.raises(SchemaError, match="row exceeds"):
        decode_rows(RECORDS_FILE, b"x" * ONE_MIB + b"\r\n", DecisionRecord)


def test_decode_document_requires_exactly_one_canonical_object(tmp_path: Path) -> None:
    files = read_files(written(tmp_path))
    verdict = files[VERDICT_FILE]
    with pytest.raises(SchemaError, match="one LF"):
        decode_document(VERDICT_FILE, verdict.rstrip(b"\n"), Verdict)
    with pytest.raises(SchemaError, match="canonical"):
        decode_document(VERDICT_FILE, verdict + b"\n", Verdict)
    with pytest.raises(SchemaError):
        decode_document(VERDICT_FILE, verdict + verdict, Verdict)
    with pytest.raises(SchemaError, match="canonical"):
        decode_document(VERDICT_FILE, b" " + verdict, Verdict)
    with pytest.raises(SchemaError):
        decode_document(VERDICT_FILE, files[LOCK_FILE], Verdict)


def test_decoded_records_are_frozen_public_records(tmp_path: Path) -> None:
    files = read_files(written(tmp_path))
    records = decode_rows(RECORDS_FILE, files[RECORDS_FILE], DecisionRecord)
    assert isinstance(records[0].outcome, ChoiceAnswer)
    assert isinstance(records[0].outcome.probabilities, tuple)
    assert isinstance(records[0].capture.warnings, tuple)
    assert isinstance(records[0].capture.identity.artifact_hashes, tuple)
    assert (
        lock_digest(decode_document(LOCK_FILE, files[LOCK_FILE], PlanLock))
        == json.loads(files[LOCK_FILE])["sha256"]
    )


# --------------------------------------------------------------------------- #
# REVIEW T40-01 finding 1: embedded NUL must never reach the native call
# --------------------------------------------------------------------------- #


def _no_native_call() -> ctypes.CDLL:
    pytest.fail("the native helper was reached with an invalid path")


@pytest.mark.parametrize(
    "destination",
    [
        pytest.param(Path("new\x00suffix"), id="nul_in_name"),
        pytest.param(Path("new") / "\x00" / "run", id="nul_component"),
        pytest.param(Path("p\x00q") / "run", id="nul_in_parent"),
    ],
)
def test_nul_destination_is_rejected_before_any_filesystem_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, destination: Path
) -> None:
    monkeypatch.setattr(evidence_module, "_load_libc", _no_native_call)
    (tmp_path / "sibling").write_bytes(b"sibling")
    with pytest.raises(SchemaError, match="destination: must not contain NUL") as info:
        write_bundle(make_bundle(), tmp_path / destination)
    assert "\x00" not in str(info.value)
    assert sorted(os.listdir(tmp_path)) == ["sibling"]
    assert not (tmp_path / "new").exists()
    assert not (tmp_path / "p").exists()
    assert temp_leftovers(tmp_path) == []


def test_native_helper_rejects_nul_in_either_path_without_publishing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(evidence_module, "_load_libc", _no_native_call)
    source = tmp_path / "source"
    source.mkdir()
    (source / "marker").write_bytes(b"marker")
    with pytest.raises(SchemaError, match="destination: must not contain NUL"):
        evidence_module._exclusive_rename(source, tmp_path / "new\x00suffix")
    with pytest.raises(SchemaError, match="source: must not contain NUL"):
        evidence_module._exclusive_rename(tmp_path / "source\x00x", tmp_path / "new")
    assert sorted(os.listdir(tmp_path)) == ["source"]
    assert (source / "marker").read_bytes() == b"marker"
    assert not (tmp_path / "new").exists()


def test_native_helper_still_publishes_a_plain_path_after_the_nul_guard(tmp_path: Path) -> None:
    """The guard is a pure argument check: the real native publish still runs afterwards."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "marker").write_bytes(b"marker")
    evidence_module._exclusive_rename(source, tmp_path / "new")
    assert (tmp_path / "new" / "marker").read_bytes() == b"marker"
    assert not source.exists()


def test_reader_and_c_path_reject_nul_paths(tmp_path: Path) -> None:
    with pytest.raises(SchemaError, match="bundle: must not contain NUL"):
        read_bundle_files(tmp_path / "run\x00x")
    with pytest.raises(SchemaError, match="field: must not contain NUL"):
        evidence_module._c_path("field", Path("a\x00b"))
    assert evidence_module._c_path("field", Path("plain")) == b"plain"


# --------------------------------------------------------------------------- #
# REVIEW T40-01 finding 2: running aggregate budget with early stop
# --------------------------------------------------------------------------- #


def _counting_canonical_json(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Count canonical serializations made by the evidence module (not by assess)."""
    sizes: list[int] = []

    def counting(value: object) -> bytes:
        data = canonical_json(value)
        sizes.append(len(data))
        return data

    monkeypatch.setattr(evidence_module, "canonical_json", counting)
    return sizes


def _wire_sizes(bundle: EvidenceBundle) -> tuple[int, int, int, list[int]]:
    """Independently computed lock/dataset/row wire sizes (each incl. its LF)."""
    lock = len(canonical_json(to_data(bundle.lock))) + 1
    calibration = len(bundle.calibration_jsonl.encode("utf-8"))
    verification = len(bundle.verification_jsonl.encode("utf-8"))
    rows = [len(canonical_json(to_data(record))) + 1 for record in bundle.records]
    return lock, calibration, verification, rows


def test_budget_charges_every_byte_and_rejects_before_retaining() -> None:
    budget = evidence_module._Budget(10)
    budget.charge(4)
    assert budget.remaining == 6
    with pytest.raises(SchemaError, match="aggregate size exceeds 10 bytes"):
        budget.charge(7)
    assert budget.used == 4
    budget.charge(6)
    assert budget.remaining == 0
    with pytest.raises(SchemaError, match="aggregate"):
        budget.charge(1)


def test_dataset_encoding_rejects_oversized_text_before_allocating_bytes() -> None:
    budget = evidence_module._Budget(10)
    with pytest.raises(SchemaError, match="aggregate"):
        evidence_module._encode_dataset("x", "a" * 11, budget)
    assert budget.used == 0
    assert evidence_module._encode_dataset("x", "a" * 10, budget) == b"a" * 10
    with pytest.raises(SchemaError, match="aggregate"):
        evidence_module._encode_dataset("y", "b", budget)
    multibyte = evidence_module._Budget(10)
    with pytest.raises(SchemaError, match="aggregate"):
        evidence_module._encode_dataset("z", "é" * 6, multibyte)  # 6 chars, 12 bytes
    assert multibyte.used == 0


def test_small_budget_stops_encoding_at_the_first_overflowing_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = make_bundle()
    lock, calibration, verification, rows = _wire_sizes(bundle)
    assert len(rows) == 6
    # Budget admits the lock, both datasets and exactly two records rows.
    limit = lock + calibration + verification + rows[0] + rows[1]
    sizes = _counting_canonical_json(monkeypatch)
    with pytest.raises(SchemaError, match="aggregate size exceeds"):
        evidence_module._encode_files(bundle, limit)
    # lock + rows 0, 1 and the overflowing row 2: nothing after it is serialized.
    assert len(sizes) == 4
    assert sizes == [lock - 1, rows[0] - 1, rows[1] - 1, rows[2] - 1]

    # One byte less: the second row itself overflows.
    sizes.clear()
    with pytest.raises(SchemaError, match="aggregate size exceeds"):
        evidence_module._encode_files(bundle, limit - 1)
    assert len(sizes) == 3

    # A budget that ends inside the raw datasets never serializes a row at all.
    sizes.clear()
    with pytest.raises(SchemaError, match="aggregate size exceeds"):
        evidence_module._encode_files(bundle, lock + calibration + verification - 1)
    assert len(sizes) == 1


def test_many_records_sharing_one_large_body_stop_early_through_the_writer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A small in-memory bundle (one shared padded body) would serialize to far more than
    the budget; the writer stops after a handful of rows instead of materializing all."""
    count = 30
    cases = tuple(
        (f"v-{index:03d}", f"Verification case {index}.", ALL_LABELS[index % 3])
        for index in range(count)
    )
    verification = verification_jsonl(cases)
    lock = make_lock(verification=verification)
    shared_body = json.dumps(
        {
            "type": "choice",
            "choice": "x" * (600 * 1024),
            "probabilities": dict.fromkeys(ALL_LABELS, 0.0),
        }
    )
    records = tuple(record_for(lock, case, body=shared_body) for case in lock.verification_cases)
    assert all(record.decision.action == "DENY" for record in records)
    bundle = make_bundle(lock, records, verification=verification)
    # Thirty DENY decisions: a = 0, coverage upper < 0.5 -> a valid statistical BLOCK.
    assert bundle.verdict.status == "BLOCK"
    assert (bundle.verdict.total, bundle.verdict.accepted) == (count, 0)
    monkeypatch.setattr(evidence_module, "MAX_BUNDLE_BYTES", 2 * ONE_MIB)
    sizes = _counting_canonical_json(monkeypatch)
    with pytest.raises(SchemaError, match="aggregate size exceeds"):
        write_bundle(bundle, tmp_path / "run")
    # lock plus at most four ~600 KiB rows before the 2 MiB budget is exhausted.
    assert 2 <= len(sizes) <= 5
    assert sum(sizes) < 4 * ONE_MIB
    assert not (tmp_path / "run").exists()
    assert temp_leftovers(tmp_path) == []
    assert os.listdir(tmp_path) == []


def test_aggregate_limit_is_exact_including_manifest_and_every_lf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = make_bundle()
    files = read_files(written(tmp_path, bundle, "reference"))
    total = sum(len(data) for data in files.values())
    lock, calibration, verification, rows = _wire_sizes(bundle)
    faults = [len(canonical_json(to_data(fault))) + 1 for fault in bundle.faults]
    verdict = len(canonical_json(to_data(bundle.verdict))) + 1
    assert (
        total
        == len(files[MANIFEST_FILE])
        + lock
        + calibration
        + verification
        + sum(rows)
        + sum(faults)
        + verdict
    )
    assert all(data.endswith(b"\n") for name, data in files.items() if name != CALIBRATION_FILE)

    monkeypatch.setattr(evidence_module, "MAX_BUNDLE_BYTES", total)
    exact = write_bundle(bundle, tmp_path / "exact")
    assert read_files(exact) == files

    monkeypatch.setattr(evidence_module, "MAX_BUNDLE_BYTES", total - 1)
    with pytest.raises(SchemaError, match=f"aggregate size exceeds {total - 1} bytes"):
        write_bundle(bundle, tmp_path / "over")
    assert not (tmp_path / "over").exists()
    assert temp_leftovers(tmp_path) == []


def test_full_size_default_budget_is_the_contract_ceiling() -> None:
    assert MAX_BUNDLE_BYTES == 128 * 1024 * 1024
    budget = evidence_module._Budget(MAX_BUNDLE_BYTES)
    budget.charge(MAX_BUNDLE_BYTES)
    with pytest.raises(SchemaError, match="aggregate"):
        budget.charge(1)


# --------------------------------------------------------------------------- #
# REVIEW T40-01 finding 3: directory enumeration stops at the first bad entry
# --------------------------------------------------------------------------- #


class _FakeScandir:
    """Stands in for ``os.scandir``: a context manager over a caller-supplied iterator."""

    def __init__(self, entries: Iterator[object]) -> None:
        self._entries = entries

    def __enter__(self) -> Iterator[object]:
        return self._entries

    def __exit__(self, *_exc: object) -> None:
        return None


def _entry(name: str) -> object:
    return SimpleNamespace(name=name)


def _instrumented_inventory(
    monkeypatch: pytest.MonkeyPatch, names: Sequence[str], *, endless_tail: bool
) -> list[str]:
    consumed: list[str] = []

    def entries() -> Iterator[object]:
        for name in names:
            consumed.append(name)
            yield _entry(name)
        while endless_tail:
            consumed.append("tail")
            yield _entry("tail")

    monkeypatch.setattr(os, "scandir", lambda _path: _FakeScandir(entries()))
    return consumed


def test_inventory_stops_at_the_first_unexpected_entry_without_traversing_the_tail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    consumed = _instrumented_inventory(monkeypatch, ["zzz-unexpected"], endless_tail=True)
    with pytest.raises(SchemaError, match="exactly the seven"):
        evidence_module._inventory(tmp_path)
    assert consumed == ["zzz-unexpected"]


def test_inventory_stops_at_an_eighth_entry_after_seven_valid_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    consumed = _instrumented_inventory(monkeypatch, [*BUNDLE_FILES, "notes.txt"], endless_tail=True)
    with pytest.raises(SchemaError, match="exactly the seven"):
        evidence_module._inventory(tmp_path)
    assert consumed == [*BUNDLE_FILES, "notes.txt"]


def test_inventory_stops_at_a_repeated_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    consumed = _instrumented_inventory(
        monkeypatch, [LOCK_FILE, VERDICT_FILE, LOCK_FILE], endless_tail=True
    )
    with pytest.raises(SchemaError, match="exactly the seven"):
        evidence_module._inventory(tmp_path)
    assert consumed == [LOCK_FILE, VERDICT_FILE, LOCK_FILE]


def test_inventory_reports_missing_names_after_a_valid_short_listing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    consumed = _instrumented_inventory(monkeypatch, list(BUNDLE_FILES[:-1]), endless_tail=False)
    with pytest.raises(SchemaError, match="exactly the seven"):
        evidence_module._inventory(tmp_path)
    assert consumed == list(BUNDLE_FILES[:-1])
    consumed = _instrumented_inventory(monkeypatch, [], endless_tail=False)
    with pytest.raises(SchemaError, match="exactly the seven"):
        evidence_module._inventory(tmp_path)


def test_inventory_accepts_exactly_the_seven_names_in_any_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    shuffled = list(reversed(BUNDLE_FILES))
    consumed = _instrumented_inventory(monkeypatch, shuffled, endless_tail=False)
    found = evidence_module._inventory(tmp_path)
    assert sorted(found) == sorted(BUNDLE_FILES)
    assert consumed == shuffled


def test_reader_rejects_a_directory_with_many_extra_entries_before_reading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = written(tmp_path)
    for index in range(300):
        (out / f"zz-extra-{index:03d}").write_bytes(b"")
    opened: list[str] = []

    def spying(path: Path, *, limit: int) -> str:
        opened.append(path.name)
        return read_input_text(path, limit=limit)

    monkeypatch.setattr(evidence_module, "read_input_text", spying)
    with pytest.raises(SchemaError, match="exactly the seven"):
        read_bundle_files(out)
    assert opened == []
