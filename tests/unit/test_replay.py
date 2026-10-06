"""Semantic offline replay against bundles written by the real writer and real authorities.

Forgeries are applied to a written bundle's files and every ordinary file and
manifest hash is recomputed independently (``test_evidence.rewrite``), so each
test shows that checksum validity alone never preserves a stored verdict.
Expected verdicts come from a direct ``assess`` on the same evidence, never
from ``replay`` itself. Builders are shared with ``test_evidence``.

Documented limit: a wholly rewritten, internally consistent bundle (new lock,
new raw inputs, new inventories, new seal, recomputed verdict and hashes)
replays cleanly. Only a separately trusted expected lock digest detects that
its identity changed; no test here asserts otherwise (ADR 0005).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import replace
from pathlib import Path

import pytest
from test_evidence import (
    CALIBRATION,
    GOLD,
    body_for,
    compact,
    contract_with,
    laya_identity,
    make_bundle,
    make_lock,
    nested,
    read_files,
    record_for,
    records_for,
    rewrite,
    rows_bytes,
    rows_of,
    verification_jsonl,
)

from actseal.assessment import (
    REASON_CONTRACT_SATISFIED,
    REASON_EVIDENCE_INSUFFICIENT,
    REASON_RISK_EXCEEDS_LIMIT,
    REASON_WORKER_INVALIDATED,
    assess,
)
from actseal.errors import SchemaError
from actseal.evidence import (
    CALIBRATION_FILE,
    FAULTS_FILE,
    LOCK_FILE,
    MANIFEST_FILE,
    RECORDS_FILE,
    VERDICT_FILE,
    VERIFICATION_FILE,
    write_bundle,
)
from actseal.faults import run_fault_campaign
from actseal.locking import FAULT_INVENTORY, case_digest, lock_digest, validate_lock
from actseal.records import (
    CaseRef,
    DecisionRecord,
    EvidenceBundle,
    FaultResult,
    Interval,
    PlanLock,
    PolicyDecision,
    ProviderFailure,
    Verdict,
)
from actseal.replay import (
    REASON_BUNDLE_HASH,
    REASON_BUNDLE_IO,
    REASON_BUNDLE_SCHEMA,
    REASON_EXPECTED_LOCK,
    REASON_FAULTS_SCHEMA,
    REASON_INPUTS,
    REASON_LOCK,
    REASON_LOCK_SCHEMA,
    REASON_RECORDS_SCHEMA,
    REASON_VERDICT,
    REASON_VERDICT_SCHEMA,
    UNKNOWN_LOCK_SHA256,
    UNKNOWN_SCOPE,
    replay,
)
from actseal.serialization import canonical_json, to_data

FULL = Interval(0.0, 1.0)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def assert_error(verdict: Verdict, *reasons: str, scope: str, lock_sha256: str) -> None:
    assert verdict.status == "ERROR"
    assert verdict.reasons == tuple(sorted(reasons))
    assert (verdict.total, verdict.accepted, verdict.errors) == (0, 0, 0)
    assert verdict.risk == FULL
    assert verdict.coverage == FULL
    assert verdict.evidence_scope == scope
    assert verdict.lock_sha256 == lock_sha256


def assert_unknown_error(verdict: Verdict, *reasons: str) -> None:
    assert_error(verdict, *reasons, scope=UNKNOWN_SCOPE, lock_sha256=UNKNOWN_LOCK_SHA256)


def assert_lock_error(verdict: Verdict, lock: PlanLock, *reasons: str) -> None:
    assert_error(verdict, *reasons, scope=lock.contract.evidence_scope, lock_sha256=lock.sha256)


def written(tmp_path: Path, bundle: EvidenceBundle | None = None) -> tuple[Path, EvidenceBundle]:
    bundle = bundle or make_bundle()
    return write_bundle(bundle, tmp_path / "run"), bundle


def reseal(lock: PlanLock) -> PlanLock:
    return replace(lock, sha256=lock_digest(lock))


def lock_bytes(lock: PlanLock) -> bytes:
    return canonical_json(to_data(lock)) + b"\n"


def verdict_bytes(verdict: Verdict) -> bytes:
    return canonical_json(to_data(verdict)) + b"\n"


def fault_index(kind: str) -> int:
    return next(index for index, spec in enumerate(FAULT_INVENTORY) if spec.kind == kind)


# --------------------------------------------------------------------------- #
# Fresh verdicts
# --------------------------------------------------------------------------- #


def test_replay_returns_the_freshly_assessed_inconclusive_verdict(tmp_path: Path) -> None:
    out, bundle = written(tmp_path)
    verdict = replay(out)
    assert verdict == assess(bundle.records, bundle.lock, bundle.faults)
    assert verdict == bundle.verdict
    assert verdict.status == "INCONCLUSIVE"
    assert verdict.reasons == (REASON_EVIDENCE_INSUFFICIENT,)
    assert (verdict.total, verdict.accepted, verdict.errors) == (6, 6, 0)
    assert verdict.lock_sha256 == bundle.lock.sha256
    assert replay(out, expected_lock_sha256=bundle.lock.sha256) == verdict


def test_replay_returns_pass_and_block_from_recomputation(tmp_path: Path) -> None:
    passing = make_bundle(make_lock(contract_with(max_risk=0.6, min_coverage=0.4)))
    assert passing.verdict.status == "PASS"
    out = write_bundle(passing, tmp_path / "pass")
    assert replay(out) == passing.verdict
    assert replay(out).reasons == (REASON_CONTRACT_SATISFIED,)

    lock = make_lock()
    wrong = ["technical", "sales", "billing", "technical", "sales", "billing"]
    blocking = make_bundle(lock, records_for(lock, wrong))
    assert blocking.verdict.status == "BLOCK"
    out = write_bundle(blocking, tmp_path / "block")
    assert replay(out) == blocking.verdict
    assert replay(out).reasons == (REASON_RISK_EXCEEDS_LIMIT,)


def test_replay_accepts_laya_evidence_with_the_full_native_envelope(tmp_path: Path) -> None:
    lock = make_lock(identity=laya_identity())
    out, bundle = written(tmp_path, make_bundle(lock))
    assert bundle.records[0].capture.body_json is not None
    assert '"usage"' in bundle.records[0].capture.body_json
    verdict = replay(out)
    assert verdict == bundle.verdict
    assert verdict.status == "INCONCLUSIVE"
    assert (verdict.total, verdict.accepted) == (6, 6)


def test_replay_preserves_crlf_and_unicode_raw_inputs(tmp_path: Path) -> None:
    cases = (
        ("v-001", "Café ☕ refund \U0001f4b3 missing.", "billing"),
        ("v-002", "ログイン returns 500.", "technical"),
        ("v-003", "Bulk license pricing?", "sales"),
    )
    verification = verification_jsonl(cases, newline="\r\n")
    lock = make_lock(verification=verification)
    bundle = make_bundle(lock, verification=verification)
    out = write_bundle(bundle, tmp_path / "run")
    assert replay(out) == bundle.verdict
    assert replay(out).total == 3
    rewrite(out, {VERIFICATION_FILE: verification.replace("\r\n", "\n").encode("utf-8")})
    assert_lock_error(replay(out), lock, REASON_INPUTS)


def test_replay_does_not_modify_the_bundle(tmp_path: Path) -> None:
    out, _ = written(tmp_path)
    before = read_files(out)
    replay(out)
    replay(out, expected_lock_sha256="1" * 64)
    assert read_files(out) == before


def test_replay_type_misuse_raises_schema_error(tmp_path: Path) -> None:
    out, bundle = written(tmp_path)
    with pytest.raises(SchemaError, match="bundle"):
        replay(str(out))  # type: ignore[arg-type]
    with pytest.raises(SchemaError, match="bundle: must not contain NUL") as info:
        replay(tmp_path / "run\x00suffix")
    assert "\x00" not in str(info.value)
    with pytest.raises(SchemaError, match="expected_lock_sha256"):
        replay(out, expected_lock_sha256=bundle.lock.sha256.upper())
    with pytest.raises(SchemaError, match="expected_lock_sha256"):
        replay(out, expected_lock_sha256="abc")
    with pytest.raises(SchemaError, match="expected_lock_sha256"):
        replay(out, expected_lock_sha256=b"a" * 64)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# Identity: external digest, sentinel, decoded-but-invalid locks
# --------------------------------------------------------------------------- #


def test_wrong_external_lock_digest_is_an_error_reporting_the_observed_seal(
    tmp_path: Path,
) -> None:
    out, bundle = written(tmp_path)
    expected = "1" * 64
    verdict = replay(out, expected_lock_sha256=expected)
    assert_lock_error(verdict, bundle.lock, REASON_EXPECTED_LOCK)
    assert verdict.lock_sha256 != expected


def test_missing_bundle_and_structural_defects_use_the_unknown_lock_sentinel(
    tmp_path: Path,
) -> None:
    out, bundle = written(tmp_path)
    assert_unknown_error(replay(tmp_path / "missing"), REASON_BUNDLE_IO)
    with_expected = replay(tmp_path / "missing", expected_lock_sha256="1" * 64)
    assert_unknown_error(with_expected, REASON_BUNDLE_IO)
    (out / "extra.txt").write_bytes(b"")
    assert_unknown_error(replay(out), REASON_BUNDLE_SCHEMA)
    (out / "extra.txt").unlink()
    assert replay(out) == bundle.verdict
    data = (out / RECORDS_FILE).read_bytes()
    (out / RECORDS_FILE).write_bytes(data.replace(b"billing", b"technic", 1))
    assert_unknown_error(replay(out), REASON_BUNDLE_HASH)


def test_file_that_is_not_a_directory_is_an_io_or_schema_error(tmp_path: Path) -> None:
    file = tmp_path / "file"
    file.write_bytes(b"{}\n")
    assert_unknown_error(replay(file), REASON_BUNDLE_SCHEMA)


def _lock_schema_mutations() -> dict[str, Callable[[bytes], bytes]]:
    def pretty(data: bytes) -> bytes:
        return json.dumps(json.loads(data), sort_keys=True, indent=1).encode("utf-8") + b"\n"

    def invalid(data: bytes) -> bytes:
        return data[:-3] + b"\n"

    def unknown_version(data: bytes) -> bytes:
        value = json.loads(data)
        value["schema_version"] = 3
        return compact(value) + b"\n"

    def extra_field(data: bytes) -> bytes:
        value = json.loads(data)
        value["created"] = "now"
        return compact(value) + b"\n"

    def missing_lf(data: bytes) -> bytes:
        return data.rstrip(b"\n")

    def duplicate_key(data: bytes) -> bytes:
        return data.replace(b'"schema_version":2', b'"schema_version":2,"schema_version":2', 1)

    def unsupported_provider(data: bytes) -> bytes:
        value = json.loads(data)
        value["model_identity"]["provider"] = "jev"
        return compact(value) + b"\n"

    def bad_seal_syntax(data: bytes) -> bytes:
        value = json.loads(data)
        value["sha256"] = "G" * 64
        return compact(value) + b"\n"

    return {
        "pretty_printed": pretty,
        "invalid_json": invalid,
        "unknown_schema_version": unknown_version,
        "extra_field": extra_field,
        "missing_terminal_lf": missing_lf,
        "duplicate_key": duplicate_key,
        "unsupported_provider": unsupported_provider,
        "bad_seal_syntax": bad_seal_syntax,
    }


@pytest.mark.parametrize("mutation", sorted(_lock_schema_mutations()))
def test_undecodable_lock_is_an_error_with_the_sentinel_identity(
    tmp_path: Path, mutation: str
) -> None:
    out, bundle = written(tmp_path)
    rewrite(out, {LOCK_FILE: _lock_schema_mutations()[mutation]((out / LOCK_FILE).read_bytes())})
    assert_unknown_error(replay(out), REASON_LOCK_SCHEMA)
    assert_unknown_error(replay(out, expected_lock_sha256=bundle.lock.sha256), REASON_LOCK_SCHEMA)


def test_decoded_lock_with_a_broken_seal_reports_its_recorded_seal(tmp_path: Path) -> None:
    out, bundle = written(tmp_path)
    broken = replace(bundle.lock, sha256="1" * 64)
    rewrite(out, {LOCK_FILE: lock_bytes(broken)})
    verdict = replay(out)
    assert_lock_error(verdict, broken, REASON_LOCK)
    assert verdict.lock_sha256 == "1" * 64
    assert verdict.evidence_scope == bundle.lock.contract.evidence_scope
    both = replay(out, expected_lock_sha256=bundle.lock.sha256)
    assert_lock_error(both, broken, REASON_EXPECTED_LOCK, REASON_LOCK)


def test_foreign_implementation_fingerprint_is_an_error_even_when_resealed(
    tmp_path: Path,
) -> None:
    out, bundle = written(tmp_path)
    foreign = reseal(replace(bundle.lock, implementation_sha256="2" * 64))
    assert lock_digest(foreign) == foreign.sha256
    stored = replace(bundle.verdict, lock_sha256=foreign.sha256)
    rewrite(out, {LOCK_FILE: lock_bytes(foreign), VERDICT_FILE: verdict_bytes(stored)})
    verdict = replay(out)
    assert_lock_error(verdict, foreign, REASON_LOCK)
    assert verdict.lock_sha256 == foreign.sha256 != bundle.lock.sha256
    assert_lock_error(
        replay(out, expected_lock_sha256=bundle.lock.sha256),
        foreign,
        REASON_EXPECTED_LOCK,
        REASON_LOCK,
    )


def test_changed_gold_label_with_stale_inventory_is_a_lock_error(tmp_path: Path) -> None:
    out, bundle = written(tmp_path)
    cases = list(bundle.lock.verification_cases)
    cases[0] = replace(cases[0], expected_label="technical")
    tampered = reseal(replace(bundle.lock, verification_cases=tuple(cases)))
    rewrite(out, {LOCK_FILE: lock_bytes(tampered)})
    assert_lock_error(replay(out), tampered, REASON_LOCK)


def test_changed_gold_label_with_rebuilt_inventory_fails_against_the_raw_dataset(
    tmp_path: Path,
) -> None:
    out, bundle = written(tmp_path)
    cases = list(bundle.lock.verification_cases)
    cases[0] = replace(cases[0], expected_label="technical")
    inventory = tuple(CaseRef(case.case_id, case_digest(case)) for case in cases)
    reauthored = reseal(
        replace(bundle.lock, verification_cases=tuple(cases), verification_inventory=inventory)
    )
    validate_lock(reauthored)
    stored = replace(bundle.verdict, lock_sha256=reauthored.sha256)
    rewrite(out, {LOCK_FILE: lock_bytes(reauthored), VERDICT_FILE: verdict_bytes(stored)})
    assert_lock_error(replay(out), reauthored, REASON_INPUTS)


def test_wholly_rewritten_consistent_bundle_is_detected_only_by_the_external_digest(
    tmp_path: Path,
) -> None:
    """Documented limit (ADR 0005): rewriting labels, raw input, inventories, seal, verdict
    and every hash yields a bundle that replays as consistent evidence. Only the separately
    trusted lock digest exposes the identity change; nothing authenticates the responses."""
    out, bundle = written(tmp_path)
    assert bundle.verdict.errors == 0
    relabelled = tuple(
        (cid, state, "technical" if cid == "v-001" else label) for cid, state, label in GOLD
    )
    verification = verification_jsonl(relabelled)
    rewritten_lock = make_lock(verification=verification)
    assert rewritten_lock.sha256 != bundle.lock.sha256
    rewritten = make_bundle(rewritten_lock, bundle.records, verification=verification)
    assert rewritten.verdict.errors == 1
    rewrite(
        out,
        {
            LOCK_FILE: lock_bytes(rewritten_lock),
            VERIFICATION_FILE: verification.encode("utf-8"),
            VERDICT_FILE: verdict_bytes(rewritten.verdict),
        },
    )
    verdict = replay(out)
    assert verdict.status != "ERROR"
    assert verdict == rewritten.verdict
    assert verdict.lock_sha256 == rewritten_lock.sha256
    assert_lock_error(
        replay(out, expected_lock_sha256=bundle.lock.sha256), rewritten_lock, REASON_EXPECTED_LOCK
    )
    assert replay(out, expected_lock_sha256=rewritten_lock.sha256) == rewritten.verdict


def test_correct_external_digest_does_not_authenticate_rewritten_responses(
    tmp_path: Path,
) -> None:
    """Same lock, replaced responses, recomputed outcomes/verdict/hashes: replays cleanly
    with the correct external digest. The digest anchors identity, not responses."""
    out, bundle = written(tmp_path)
    lock = bundle.lock
    wrong = ["technical", "sales", "billing", "technical", "sales", "billing"]
    swapped = make_bundle(lock, records_for(lock, wrong))
    assert swapped.verdict.status == "BLOCK"
    rows = [to_data(record) for record in swapped.records]
    rewrite(out, {RECORDS_FILE: rows_bytes(rows), VERDICT_FILE: verdict_bytes(swapped.verdict)})
    verdict = replay(out, expected_lock_sha256=lock.sha256)
    assert verdict == swapped.verdict
    assert verdict.status == "BLOCK"


# --------------------------------------------------------------------------- #
# Raw inputs
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name", [CALIBRATION_FILE, VERIFICATION_FILE])
def test_altered_raw_dataset_bytes_are_an_inputs_error(tmp_path: Path, name: str) -> None:
    out, bundle = written(tmp_path)
    data = (out / name).read_bytes()
    rewrite(out, {name: data.replace(b"\n", b"\r\n", 1)})
    assert_lock_error(replay(out), bundle.lock, REASON_INPUTS)
    rewrite(out, {name: data.replace(b"}", b" }", 1)})
    assert_lock_error(replay(out), bundle.lock, REASON_INPUTS)
    rewrite(out, {name: data})
    assert replay(out) == bundle.verdict


def test_swapped_dataset_files_are_an_inputs_error(tmp_path: Path) -> None:
    out, bundle = written(tmp_path)
    files = read_files(out)
    rewrite(
        out,
        {CALIBRATION_FILE: files[VERIFICATION_FILE], VERIFICATION_FILE: files[CALIBRATION_FILE]},
    )
    assert_lock_error(replay(out), bundle.lock, REASON_INPUTS)


# --------------------------------------------------------------------------- #
# Records: semantic forgeries with every ordinary hash recomputed
# --------------------------------------------------------------------------- #


def _record_forgeries() -> dict[str, tuple[Callable[[list[dict[str, object]]], None], set[str]]]:
    def stored_choice_and_action(rows: list[dict[str, object]]) -> None:
        # The raw body says billing with 0.95; the stored answer and ACT now claim technical.
        outcome = nested(rows[0], "outcome")
        outcome["choice"] = "technical"
        outcome["probabilities"] = [["billing", 0.025], ["technical", 0.95], ["sales", 0.025]]
        nested(rows[0], "decision")["choice"] = "technical"

    def stored_action_only(rows: list[dict[str, object]]) -> None:
        decision = nested(rows[0], "decision")
        decision["action"] = "ABSTAIN"
        decision["choice"] = None
        decision["reason"] = "policy.low_confidence"

    def inflated_probability(rows: list[dict[str, object]]) -> None:
        outcome = nested(rows[0], "outcome")
        outcome["probabilities"] = [["billing", 0.96], ["technical", 0.02], ["sales", 0.02]]
        outcome["selected_probability"] = 0.96

    def swapped_request_hashes(rows: list[dict[str, object]]) -> None:
        first = nested(rows[0], "capture")
        second = nested(rows[1], "capture")
        first["request_sha256"], second["request_sha256"] = (
            second["request_sha256"],
            first["request_sha256"],
        )

    def corrupted_raw_body(rows: list[dict[str, object]]) -> None:
        capture = nested(rows[1], "capture")
        body = str(capture["body_json"])
        assert "technical" in body
        capture["body_json"] = body.replace('"choice": "technical"', '"choice": "sales"')

    def invented_answer_for_corrupted_body(rows: list[dict[str, object]]) -> None:
        nested(rows[2], "capture")["body_json"] = "{"

    def relabelled_failure(rows: list[dict[str, object]]) -> None:
        rows[3]["outcome"] = {
            "kind": "failure",
            "code": "timeout",
            "warnings": [],
            "fallback_used": False,
        }
        rows[3]["decision"] = {
            "action": "ESCALATE",
            "choice": None,
            "reason": "provider.timeout",
            "fallback_used": False,
        }

    def missing_record(rows: list[dict[str, object]]) -> None:
        rows.pop()

    def duplicate_record(rows: list[dict[str, object]]) -> None:
        rows[5] = dict(rows[4])

    def reordered_records(rows: list[dict[str, object]]) -> None:
        rows[0], rows[1] = rows[1], rows[0]

    def foreign_id(rows: list[dict[str, object]]) -> None:
        rows[5]["case_id"] = "v-999"

    def extra_record(rows: list[dict[str, object]]) -> None:
        rows.append(dict(rows[0]))

    def dropped_warning(rows: list[dict[str, object]]) -> None:
        nested(rows[0], "capture")["warnings"] = ["adapter.slow"]

    def foreign_identity_with_answer(rows: list[dict[str, object]]) -> None:
        nested(rows[0], "capture", "identity")["revision"] = "f" * 64

    return {
        "stored_choice_and_action": (
            stored_choice_and_action,
            {"integrity.outcome", "integrity.decision"},
        ),
        "stored_action_only": (stored_action_only, {"integrity.decision"}),
        "inflated_probability": (inflated_probability, {"integrity.outcome"}),
        "swapped_request_hashes": (swapped_request_hashes, {"integrity.request_hash"}),
        "corrupted_raw_body": (corrupted_raw_body, {"integrity.outcome", "integrity.decision"}),
        "invented_answer_for_corrupted_body": (
            invented_answer_for_corrupted_body,
            {"integrity.outcome", "integrity.decision"},
        ),
        "relabelled_failure": (relabelled_failure, {"integrity.outcome", "integrity.decision"}),
        "missing_record": (missing_record, {"integrity.records"}),
        "duplicate_record": (duplicate_record, {"integrity.records"}),
        "reordered_records": (reordered_records, {"integrity.records"}),
        "foreign_id": (foreign_id, {"integrity.records"}),
        "extra_record": (extra_record, {"integrity.records"}),
        "dropped_warning": (dropped_warning, {"integrity.outcome"}),
        "foreign_identity_with_answer": (
            foreign_identity_with_answer,
            {"integrity.outcome", "integrity.decision"},
        ),
    }


@pytest.mark.parametrize("forgery", sorted(_record_forgeries()))
def test_record_forgeries_with_recomputed_hashes_are_errors(tmp_path: Path, forgery: str) -> None:
    out, bundle = written(tmp_path)
    mutate, expected = _record_forgeries()[forgery]
    rows = rows_of((out / RECORDS_FILE).read_bytes())
    mutate(rows)
    rewrite(out, {RECORDS_FILE: rows_bytes(rows)})
    verdict = replay(out)
    assert_lock_error(verdict, bundle.lock, *expected, REASON_VERDICT)


def test_stored_pass_is_never_preserved_for_forged_records(tmp_path: Path) -> None:
    lock = make_lock(contract_with(max_risk=0.6, min_coverage=0.4))
    honest = make_bundle(lock, records_for(lock, ["technical", None, None, None, None, None]))
    assert honest.verdict.status == "INCONCLUSIVE"
    out = write_bundle(honest, tmp_path / "run")
    rows = rows_of((out / RECORDS_FILE).read_bytes())
    nested(rows[0], "outcome")["choice"] = "billing"
    nested(rows[0], "outcome")["probabilities"] = [
        ["billing", 0.95],
        ["technical", 0.025],
        ["sales", 0.025],
    ]
    nested(rows[0], "decision")["choice"] = "billing"
    forged_pass = make_bundle(lock, records_for(lock)).verdict
    assert forged_pass.status == "PASS"
    rewrite(out, {RECORDS_FILE: rows_bytes(rows), VERDICT_FILE: verdict_bytes(forged_pass)})
    verdict = replay(out)
    assert_lock_error(verdict, lock, "integrity.outcome", "integrity.decision", REASON_VERDICT)


def test_forged_stored_verdict_alone_is_an_error(tmp_path: Path) -> None:
    out, bundle = written(tmp_path)
    forged = replace(bundle.verdict, status="PASS", reasons=(REASON_CONTRACT_SATISFIED,))
    rewrite(out, {VERDICT_FILE: verdict_bytes(forged)})
    assert_lock_error(replay(out), bundle.lock, REASON_VERDICT)
    counts = replace(bundle.verdict, accepted=5)
    rewrite(out, {VERDICT_FILE: verdict_bytes(counts)})
    assert_lock_error(replay(out), bundle.lock, REASON_VERDICT)
    other_scope = replace(bundle.verdict, evidence_scope="iid")
    rewrite(out, {VERDICT_FILE: verdict_bytes(other_scope)})
    assert_lock_error(replay(out), bundle.lock, REASON_VERDICT)


def test_malformed_recorded_body_is_valid_data_but_a_corrupted_body_is_not(tmp_path: Path) -> None:
    lock = make_lock()
    records = list(records_for(lock))
    records[1] = record_for(lock, lock.verification_cases[1], body="{")
    assert records[1].outcome == ProviderFailure(
        "malformed_response", ("normalize.invalid_json",), False
    )
    bundle = make_bundle(lock, records)
    out = write_bundle(bundle, tmp_path / "run")
    verdict = replay(out)
    assert verdict == bundle.verdict
    assert verdict.status == "INCONCLUSIVE"
    assert (verdict.total, verdict.accepted) == (6, 5)
    rows = rows_of((out / RECORDS_FILE).read_bytes())
    nested(rows[0], "capture")["body_json"] = "{"
    rewrite(out, {RECORDS_FILE: rows_bytes(rows)})
    assert_lock_error(replay(out), lock, "integrity.outcome", "integrity.decision", REASON_VERDICT)


def test_nonfatal_provider_failures_remain_denominator_observations(tmp_path: Path) -> None:
    lock = make_lock(identity=laya_identity())
    cases = lock.verification_cases
    records = (
        record_for(lock, cases[0]),
        record_for(lock, cases[1], body=body_for(lock, "nowhere")),
        record_for(lock, cases[2], failure_code="rate_limit"),
        record_for(lock, cases[3], failure_code="provider_error"),
        record_for(lock, cases[4], failure_code="input_too_long"),
        record_for(lock, cases[5], body="{"),
    )
    assert records[1].decision == PolicyDecision("DENY", None, "policy.unknown_choice", False)
    assert [record.decision.action for record in records[2:]] == ["ESCALATE"] * 4
    bundle = make_bundle(lock, records)
    out = write_bundle(bundle, tmp_path / "run")
    verdict = replay(out)
    assert verdict == bundle.verdict
    assert verdict.status == "INCONCLUSIVE"
    assert REASON_WORKER_INVALIDATED not in verdict.reasons
    assert (verdict.total, verdict.accepted, verdict.errors) == (6, 1, 0)


# --------------------------------------------------------------------------- #
# Faults
# --------------------------------------------------------------------------- #


def _fault_forgeries() -> dict[str, tuple[Callable[[list[dict[str, object]]], None], set[str]]]:
    timeout = fault_index("timeout")
    rate_limit = fault_index("rate_limit")
    low = fault_index("low_confidence")

    def omitted(rows: list[dict[str, object]]) -> None:
        rows.pop(low)

    def duplicated(rows: list[dict[str, object]]) -> None:
        rows.append(dict(rows[0]))

    def reordered(rows: list[dict[str, object]]) -> None:
        rows[timeout], rows[rate_limit] = rows[rate_limit], rows[timeout]

    def swapped_capture_faithfully(rows: list[dict[str, object]]) -> None:
        # The rate_limit capture, outcome and decision filed under the timeout scenario.
        source = rows[rate_limit]
        rows[timeout]["capture"] = source["capture"]
        rows[timeout]["outcome"] = source["outcome"]
        rows[timeout]["decision"] = source["decision"]

    def swapped_request(rows: list[dict[str, object]]) -> None:
        rows[timeout]["request"] = rows[rate_limit]["request"]

    def changed_fault_state(rows: list[dict[str, object]]) -> None:
        nested(rows[low], "request")["state"] = "Actseal deterministic fault campaign!"

    def forged_fault_decision(rows: list[dict[str, object]]) -> None:
        decision = nested(rows[low], "decision")
        decision["action"] = "ACT"
        decision["choice"] = "billing"
        decision["reason"] = "policy.allowed"

    def claimed_violation(rows: list[dict[str, object]]) -> None:
        decision = nested(rows[timeout], "decision")
        decision["action"] = "DENY"
        decision["reason"] = "policy.unknown_choice"

    return {
        "omitted_scenario": (omitted, {"integrity.faults"}),
        "duplicated_scenario": (duplicated, {"integrity.faults"}),
        "reordered_scenarios": (reordered, {"integrity.faults"}),
        "swapped_capture_faithfully": (swapped_capture_faithfully, {"integrity.fault_capture"}),
        "swapped_request": (swapped_request, {"integrity.fault_request"}),
        "changed_fault_state": (
            changed_fault_state,
            {"integrity.fault_request"},
        ),
        "forged_fault_decision": (forged_fault_decision, {"integrity.fault_decision"}),
        "claimed_violation": (claimed_violation, {"integrity.fault_decision"}),
    }


@pytest.mark.parametrize("forgery", sorted(_fault_forgeries()))
def test_fault_forgeries_with_recomputed_hashes_are_errors(tmp_path: Path, forgery: str) -> None:
    out, bundle = written(tmp_path)
    mutate, expected = _fault_forgeries()[forgery]
    rows = rows_of((out / FAULTS_FILE).read_bytes())
    mutate(rows)
    rewrite(out, {FAULTS_FILE: rows_bytes(rows)})
    assert_lock_error(replay(out), bundle.lock, *expected, REASON_VERDICT)


def test_canonical_faults_from_another_lock_are_detected(tmp_path: Path) -> None:
    out, bundle = written(tmp_path)
    other = make_lock(identity=laya_identity())
    other_faults = run_fault_campaign(other)
    rows = rows_of((out / FAULTS_FILE).read_bytes())
    index = fault_index("low_confidence")
    rows[index] = to_data(other_faults[index])
    rewrite(out, {FAULTS_FILE: rows_bytes(rows)})
    assert_lock_error(
        replay(out),
        bundle.lock,
        "integrity.fault_capture",
        "integrity.fault_outcome",
        "integrity.fault_decision",
        REASON_VERDICT,
    )


# --------------------------------------------------------------------------- #
# ADR 0009: regular worker loss is a diagnostic ERROR bundle
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("code", ["timeout", "unavailable"])
def test_regular_laya_worker_loss_replays_as_the_diagnostic_error(
    tmp_path: Path, code: str
) -> None:
    lock = make_lock(identity=laya_identity())
    records = list(records_for(lock))
    records[3] = record_for(lock, lock.verification_cases[3], failure_code=code)
    assert records[3].decision == PolicyDecision("ESCALATE", None, f"provider.{code}", False)
    bundle = make_bundle(lock, records)
    assert bundle.verdict.status == "ERROR"
    out = write_bundle(bundle, tmp_path / "run")
    verdict = replay(out)
    assert_lock_error(verdict, lock, REASON_WORKER_INVALIDATED)
    assert verdict == bundle.verdict
    rows = rows_of((out / RECORDS_FILE).read_bytes())
    assert len(rows) == 6
    assert nested(rows[3], "capture")["failure_code"] == code
    assert replay(out, expected_lock_sha256=lock.sha256) == verdict


def test_worker_loss_error_is_distinct_from_fixture_failures_and_synthetic_faults(
    tmp_path: Path,
) -> None:
    fixture_lock = make_lock()
    records = list(records_for(fixture_lock))
    case = fixture_lock.verification_cases[3]
    records[3] = record_for(fixture_lock, case, failure_code="timeout")
    fixture_bundle = make_bundle(fixture_lock, records)
    out = write_bundle(fixture_bundle, tmp_path / "fixture")
    verdict = replay(out)
    assert verdict.status == "INCONCLUSIVE"
    assert (verdict.total, verdict.accepted) == (6, 5)

    laya_lock = make_lock(identity=laya_identity())
    laya_bundle = make_bundle(laya_lock)
    timeout_fault = laya_bundle.faults[fault_index("timeout")]
    assert timeout_fault.capture.failure_code == "timeout"
    out = write_bundle(laya_bundle, tmp_path / "laya")
    verdict = replay(out)
    assert verdict.status == "INCONCLUSIVE"
    assert REASON_WORKER_INVALIDATED not in verdict.reasons
    assert (verdict.total, verdict.accepted) == (6, 6)


def test_worker_loss_bundle_with_forged_records_reports_integrity_not_infrastructure(
    tmp_path: Path,
) -> None:
    lock = make_lock(identity=laya_identity())
    records = list(records_for(lock))
    records[0] = record_for(lock, lock.verification_cases[0], failure_code="timeout")
    bundle = make_bundle(lock, records)
    out = write_bundle(bundle, tmp_path / "run")
    rows = rows_of((out / RECORDS_FILE).read_bytes())
    rows.pop()
    rewrite(out, {RECORDS_FILE: rows_bytes(rows)})
    assert_lock_error(replay(out), lock, "integrity.records", REASON_VERDICT)


def test_a_stored_worker_loss_error_cannot_hide_a_healthy_run(tmp_path: Path) -> None:
    out, bundle = written(tmp_path)
    fake_error = Verdict(
        "ERROR",
        (REASON_WORKER_INVALIDATED,),
        0,
        0,
        0,
        FULL,
        FULL,
        bundle.lock.contract.evidence_scope,
        bundle.lock.sha256,
    )
    rewrite(out, {VERDICT_FILE: verdict_bytes(fake_error)})
    assert_lock_error(replay(out), bundle.lock, REASON_VERDICT)


# --------------------------------------------------------------------------- #
# Wire-level defects in records, faults and verdict
# --------------------------------------------------------------------------- #


def test_wire_defects_in_evidence_files_report_each_schema_code(tmp_path: Path) -> None:
    out, bundle = written(tmp_path)
    files = read_files(out)
    rewrite(out, {RECORDS_FILE: files[RECORDS_FILE].replace(b'"case_id":', b'"case_id": ', 1)})
    assert_lock_error(replay(out), bundle.lock, REASON_RECORDS_SCHEMA)
    rewrite(
        out,
        {
            RECORDS_FILE: files[RECORDS_FILE],
            FAULTS_FILE: files[FAULTS_FILE].rstrip(b"\n"),
            VERDICT_FILE: files[VERDICT_FILE] + b"\n",
        },
    )
    assert_lock_error(replay(out), bundle.lock, REASON_FAULTS_SCHEMA, REASON_VERDICT_SCHEMA)
    rewrite(out, {FAULTS_FILE: files[FAULTS_FILE], VERDICT_FILE: files[VERDICT_FILE]})
    assert replay(out) == bundle.verdict


def test_oversized_row_and_excess_nesting_are_schema_errors_not_crashes(tmp_path: Path) -> None:
    out, bundle = written(tmp_path)
    original_records = (out / RECORDS_FILE).read_bytes()
    rows = rows_of(original_records)
    nested(rows[0], "capture")["body_json"] = "x" * (1024 * 1024)
    rewrite(out, {RECORDS_FILE: rows_bytes(rows)})
    assert_lock_error(replay(out), bundle.lock, REASON_RECORDS_SCHEMA)
    rows = rows_of((out / FAULTS_FILE).read_bytes())
    deep: object = 1
    for _ in range(33):
        deep = [deep]
    rows[0]["request"] = deep
    rewrite(out, {FAULTS_FILE: rows_bytes(rows)})
    assert_lock_error(replay(out), bundle.lock, REASON_FAULTS_SCHEMA, REASON_RECORDS_SCHEMA)
    rewrite(out, {RECORDS_FILE: original_records})
    assert_lock_error(replay(out), bundle.lock, REASON_FAULTS_SCHEMA)


def test_oversized_lock_and_aggregate_fail_before_any_content_is_read(tmp_path: Path) -> None:
    out, _ = written(tmp_path)
    os.truncate(out / LOCK_FILE, 32 * 1024 * 1024 + 1)
    assert_unknown_error(replay(out), REASON_BUNDLE_SCHEMA)
    out2 = write_bundle(make_bundle(), tmp_path / "second")
    os.truncate(out2 / RECORDS_FILE, 128 * 1024 * 1024)
    assert_unknown_error(replay(out2), REASON_BUNDLE_SCHEMA)


# --------------------------------------------------------------------------- #
# Bounded, non-echoing error paths
# --------------------------------------------------------------------------- #


def test_error_reasons_are_fixed_codes_that_never_echo_payloads(tmp_path: Path) -> None:
    sentinel = "SENSITIVE-SOURCE-VALUE-9f8e7d"
    cases = tuple((cid, f"{state} {sentinel}", label) for cid, state, label in GOLD)
    verification = verification_jsonl(cases)
    lock = make_lock(verification=verification)
    bundle = make_bundle(lock, verification=verification)
    out = write_bundle(bundle, tmp_path / "run")
    rows = rows_of((out / RECORDS_FILE).read_bytes())
    nested(rows[0], "decision")["reason"] = sentinel
    nested(rows[0], "decision")["action"] = "DENY"
    nested(rows[0], "decision")["choice"] = None
    rewrite(out, {RECORDS_FILE: rows_bytes(rows)})
    verdict = replay(out)
    assert verdict.status == "ERROR"
    for reason in verdict.reasons:
        assert reason.startswith("integrity.")
        assert sentinel not in reason
        assert reason.replace(".", "").replace("_", "").isalnum()
    assert sentinel not in repr(verdict)
    with pytest.raises(SchemaError) as info:
        replay(out, expected_lock_sha256=sentinel)
    assert sentinel not in str(info.value)


# --------------------------------------------------------------------------- #
# Isolation: subprocess with provider imports and network denied
# --------------------------------------------------------------------------- #

_ISOLATED_REPLAY = r"""
import json
import os
import socket
import sys

BLOCKED = (
    "actseal.adapters", "laya", "torch", "transformers", "huggingface_hub", "safetensors",
    "numpy", "scipy", "pickle", "shelve", "marshal_io", "subprocess", "multiprocessing",
    "urllib.request", "urllib.error", "http", "ssl", "importlib.metadata", "runpy",
    "code", "codeop", "ctypes.util", "ctypes.macholib",
)


def _blocked(name):
    return any(name == root or name.startswith(root + ".") for root in BLOCKED)


class DenyImports:
    def find_spec(self, name, path=None, target=None):
        if _blocked(name):
            raise ImportError(f"blocked import: {name}")
        return None


sys.meta_path.insert(0, DenyImports())


def _no_network(*_args, **_kwargs):
    raise RuntimeError("network blocked")


socket.socket = _no_network
socket.create_connection = _no_network
socket.getaddrinfo = _no_network
socket.socketpair = _no_network

environment = dict(os.environ)
from pathlib import Path  # noqa: E402

from actseal.replay import replay  # noqa: E402

before = set(sys.modules)
verdict = replay(Path(sys.argv[1]))
loaded = sorted(name for name in set(sys.modules) - before if _blocked(name))
ever = sorted(name for name in sys.modules if _blocked(name))
print(
    json.dumps(
        {
            "status": verdict.status,
            "reasons": list(verdict.reasons),
            "total": verdict.total,
            "lock_sha256": verdict.lock_sha256,
            "loaded_blocked": loaded,
            "any_blocked": ever,
            "environment_unchanged": environment == dict(os.environ),
            "marker_exists": os.path.exists(sys.argv[2]),
        }
    )
)
"""

PAYLOADS = (
    "__import__('os').system('touch {marker}')",
    "$(touch {marker}); `touch {marker}`",
    "import os; os.environ['ACTSEAL_REPLAY_PWNED'] = '1'",
    "{{7*7}} ${{HOME}} %PATH% \\u0000 " + chr(0) + " " + chr(0x202E),
    "exec(open('/etc/passwd').read())",
    "actseal.adapters.laya:LayaModel",
)


def _payload_bundle(tmp_path: Path, marker: Path) -> EvidenceBundle:
    cases = tuple(
        (cid, payload.format(marker=marker) + f" {index}", label)
        for index, ((cid, _, label), payload) in enumerate(zip(GOLD, PAYLOADS, strict=True))
    )
    verification = verification_jsonl(cases)
    calibration = CALIBRATION.replace("Calibration one.", "import sys; sys.exit(3)")
    lock = make_lock(calibration=calibration, verification=verification)
    records = list(records_for(lock))
    records[1] = record_for(
        lock,
        lock.verification_cases[1],
        body='{"type":"choice","choice":"__import__(\'os\')","probabilities":{}}',
        warnings=("__import__('os').system('id')",),
    )
    records[2] = record_for(lock, lock.verification_cases[2], body=f"__import__('os'); {marker}")
    bundle = make_bundle(lock, records, calibration=calibration, verification=verification)
    assert bundle.verdict.status == "INCONCLUSIVE"
    assert (bundle.verdict.total, bundle.verdict.accepted) == (6, 4)
    del tmp_path
    return bundle


def _run_isolated(out: Path, marker: Path) -> Mapping[str, object]:
    result = subprocess.run(  # noqa: S603 - fixed interpreter and literal script, no user input
        [sys.executable, "-c", _ISOLATED_REPLAY, str(out), str(marker)],
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    report = json.loads(result.stdout)
    assert isinstance(report, dict)
    return report


def test_replay_in_a_subprocess_with_providers_and_network_denied(tmp_path: Path) -> None:
    marker = tmp_path / "pwned.marker"
    bundle = _payload_bundle(tmp_path, marker)
    out = write_bundle(bundle, tmp_path / "run")
    report = _run_isolated(out, marker)
    assert report["status"] == "INCONCLUSIVE"
    assert report["total"] == 6
    assert report["lock_sha256"] == bundle.lock.sha256
    assert report["loaded_blocked"] == []
    assert report["any_blocked"] == []
    assert report["environment_unchanged"] is True
    assert report["marker_exists"] is False
    assert not marker.exists()
    assert "ACTSEAL_REPLAY_PWNED" not in os.environ


def test_forged_payload_bundle_in_a_subprocess_errors_without_executing_anything(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "pwned.marker"
    bundle = _payload_bundle(tmp_path, marker)
    out = write_bundle(bundle, tmp_path / "run")
    rows = rows_of((out / RECORDS_FILE).read_bytes())
    nested(rows[0], "decision")["reason"] = f"__import__('os').system('touch {marker}')"
    rewrite(out, {RECORDS_FILE: rows_bytes(rows)})
    report = _run_isolated(out, marker)
    assert report["status"] == "ERROR"
    assert report["reasons"] == ["integrity.decision", REASON_VERDICT]
    assert report["loaded_blocked"] == []
    assert report["marker_exists"] is False


def test_replay_module_imports_no_adapter_or_native_module() -> None:
    script = (
        "import sys\n"
        "import actseal.replay\n"
        "loaded = sorted(name for name in sys.modules if name.split('.')[0] in "
        "('laya', 'torch', 'transformers', 'huggingface_hub', 'safetensors', 'numpy', 'scipy', "
        "'pickle', 'subprocess', 'multiprocessing') "
        "or name.startswith('actseal.adapters'))\n"
        "print(loaded)\n"
    )
    result = subprocess.run(  # noqa: S603 - fixed interpreter and literal script, no user input
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    assert result.stdout.strip() == "[]"


def test_manifest_and_bundle_files_are_data_only(tmp_path: Path) -> None:
    out, _ = written(tmp_path)
    names = sorted(path.name for path in out.iterdir())
    assert names == sorted(
        [
            MANIFEST_FILE,
            LOCK_FILE,
            CALIBRATION_FILE,
            VERIFICATION_FILE,
            RECORDS_FILE,
            FAULTS_FILE,
            VERDICT_FILE,
        ]
    )
    assert all(name.endswith((".json", ".jsonl")) for name in names)
    for name in names:
        json_rows = (out / name).read_bytes().split(b"\n")[:-1]
        for row in json_rows:
            json.loads(row)


def test_decoded_records_match_the_bundle_objects(tmp_path: Path) -> None:
    out, bundle = written(tmp_path)
    rows = rows_of((out / RECORDS_FILE).read_bytes())
    assert rows == [to_data(record) for record in bundle.records]
    assert isinstance(bundle.records[0], DecisionRecord)
    assert isinstance(bundle.faults[0], FaultResult)
