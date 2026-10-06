"""Public CLI workflow acceptance: real subprocesses, both installed entrypoints.

Every command here runs ``python -m actseal`` or the ``actseal`` console script
in a fresh subprocess with independently generated inputs. Expected exit codes
come from the frozen table (PASS 0, BLOCK 1, INCONCLUSIVE 2, ERROR 3); expected
statuses come from the ADR 0003 rule evaluated with an independent exact
Clopper-Pearson oracle, never from the product's own output. No network path
is used; the fixture provider reads one local file.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from acceptance_support import (
    ENTRIES,
    EXIT_CODES,
    LABELS,
    Workspace,
    canonical,
    contract_toml,
    expected_bounds,
    expected_status,
    lock_argv,
    read_document,
    reseal_lock,
    run_cli,
    tree,
    verify_argv,
    write_workspace,
)

LIMITS = {"max_risk": 0.05, "min_coverage": 0.5, "alpha": 0.05}
SENTINEL = "ACCEPTANCE_SECRET_9c1f"


@pytest.fixture(params=sorted(ENTRIES), ids=sorted(ENTRIES))
def entry(request: pytest.FixtureRequest) -> tuple[str, ...]:
    return ENTRIES[str(request.param)]


def assert_matches_oracle(
    document: dict[str, object], *, total: int, accepted: int, errors: int
) -> None:
    """The reported counts, intervals and status equal the independently computed ones."""
    assert (document["total"], document["accepted"], document["errors"]) == (
        total,
        accepted,
        errors,
    )
    risk, coverage = expected_bounds(total, accepted, errors, LIMITS["alpha"])
    reported_risk = document["risk"]
    reported_coverage = document["coverage"]
    assert isinstance(reported_risk, dict)
    assert isinstance(reported_coverage, dict)
    assert reported_risk["lower"] == pytest.approx(risk[0], abs=1e-9)
    assert reported_risk["upper"] == pytest.approx(risk[1], abs=1e-9)
    assert reported_coverage["lower"] == pytest.approx(coverage[0], abs=1e-9)
    assert reported_coverage["upper"] == pytest.approx(coverage[1], abs=1e-9)
    assert document["status"] == expected_status(total, accepted, errors, **LIMITS)
    assert document["exit_code"] == EXIT_CODES[str(document["status"])]


def workflow(
    entry: tuple[str, ...], workspace: Workspace, tmp_path: Path, name: str
) -> tuple[Path, Path, dict[str, object]]:
    """lock -> verify (JSON) for one workspace; returns lock path, bundle path and verify JSON."""
    lock = tmp_path / f"{name}.lock.json"
    locked = run_cli(entry, [*lock_argv(workspace, lock), "--json"], cwd=tmp_path)
    assert locked.code == 0, locked.stderr
    assert locked.stderr == ""
    lock_document = locked.json()
    assert lock_document["ok"] is True
    assert lock_document["command"] == "lock"
    assert lock_document["verification_cases"] == len(workspace.cases)
    out = tmp_path / f"{name}.evidence"
    verified = run_cli(entry, [*verify_argv(workspace, lock, out), "--json"], cwd=tmp_path)
    assert verified.stderr == ""
    document = verified.json()
    assert document["command"] == "verify"
    assert document["lock_sha256"] == lock_document["lock_sha256"]
    assert document["evidence_scope"] == "demo"
    assert document["out"] == str(out)
    assert verified.code == document["exit_code"]
    return lock, out, document


# --------------------------------------------------------------------------- #
# Acceptance 1: bad BLOCK, fixed PASS, insufficient INCONCLUSIVE, usage ERROR
# --------------------------------------------------------------------------- #


def test_public_workflow_yields_block_pass_and_inconclusive(
    entry: tuple[str, ...], tmp_path: Path
) -> None:
    bad = write_workspace(tmp_path / "bad", count=96, wrong=range(24), prefix="bad")
    fixed = write_workspace(tmp_path / "fixed", count=96, prefix="fixed")
    small = write_workspace(tmp_path / "small", count=6, prefix="small")
    expectations = {
        "bad": (bad, 96, 96, 24, "BLOCK", ["risk.exceeds_limit"]),
        "fixed": (fixed, 96, 96, 0, "PASS", ["contract.satisfied"]),
        "small": (small, 6, 6, 0, "INCONCLUSIVE", ["evidence.insufficient"]),
    }
    for name, (workspace, total, accepted, errors, status, reasons) in expectations.items():
        _, out, document = workflow(entry, workspace, tmp_path, name)
        assert document["status"] == status, name
        assert document["reasons"] == reasons, name
        assert_matches_oracle(document, total=total, accepted=accepted, errors=errors)
        assert document["failures"] == {}
        assert document["warnings"] == {}
        faults = document["faults"]
        assert isinstance(faults, dict)
        assert [faults[key]["action"] for key in faults] == [
            faults[key]["expected_action"] for key in faults
        ]
        assert len(faults) == 6
        # Replay in a fresh subprocess recomputes the same verdict and exit code.
        replayed = run_cli(entry, ["replay", str(out), "--json"], cwd=tmp_path)
        assert replayed.code == EXIT_CODES[status], replayed.stderr
        replay_document = replayed.json()
        assert replay_document["command"] == "replay"
        assert replay_document["status"] == status
        assert replay_document["reasons"] == reasons
        assert replay_document["lock_sha256"] == document["lock_sha256"]
        assert replay_document["bundle"] == str(out)
        assert replay_document["expected_lock_sha256"] is None
        assert_matches_oracle(replay_document, total=total, accepted=accepted, errors=errors)
        anchored = run_cli(
            entry,
            ["replay", str(out), "--expected-lock-sha256", str(document["lock_sha256"])],
            cwd=tmp_path,
        )
        assert anchored.code == EXIT_CODES[status]
        assert f"status: {status}" in anchored.stdout
        assert f"lock_sha256: {document['lock_sha256']}" in anchored.stdout
        wrong_anchor = run_cli(
            entry, ["replay", str(out), "--expected-lock-sha256", "a" * 64, "--json"], cwd=tmp_path
        )
        assert wrong_anchor.code == 3
        wrong_document = wrong_anchor.json()
        assert wrong_document["status"] == "ERROR"
        assert wrong_document["reasons"] == ["integrity.expected_lock"]
        assert wrong_document["lock_sha256"] == document["lock_sha256"]  # observed, not expected
        assert (wrong_document["total"], wrong_document["accepted"]) == (0, 0)


def test_text_mode_reports_every_documented_field(tmp_path: Path) -> None:
    entry = ENTRIES["console"]
    workspace = write_workspace(tmp_path / "ws", count=9, wrong=[0], prefix="txt")
    lock = tmp_path / "lock.json"
    locked = run_cli(entry, lock_argv(workspace, lock), cwd=tmp_path)
    assert locked.code == 0
    assert locked.stdout.startswith("lock_sha256: ")
    for field in ("implementation_sha256", "contract", "evidence_scope", "provider", "model"):
        assert f"\n{field}: " in locked.stdout
    out = tmp_path / "evidence"
    verified = run_cli(entry, verify_argv(workspace, lock, out), cwd=tmp_path)
    assert verified.code == 2
    lines = verified.stdout.splitlines()
    assert lines[0] == "status: INCONCLUSIVE"
    assert lines[1] == "reasons: evidence.insufficient"
    assert lines[2] == "accepted/total: 9/9"
    assert lines[3] == "errors/accepted: 1/9"
    assert lines[4].startswith("risk: [")
    assert lines[5].startswith("coverage: [")
    assert lines[6] == "evidence_scope: demo"
    assert lines[7].startswith("lock_sha256: ")
    assert lines[8].startswith("faults: fault.timeout=ESCALATE")
    assert lines[9] == f"out: {out}"
    assert "actseal verify: failures: none" in verified.stderr
    assert "actseal verify: warnings: none" in verified.stderr


USAGE_CASES: dict[str, list[str]] = {
    "no-command": [],
    "unknown-command": [SENTINEL],
    "demo-without-out": ["demo"],
    "timeout-override-demo": ["demo", "--out", "x", "--timeout-seconds", "5"],
    "timeout-override-verify": ["verify", "--timeout-seconds", SENTINEL],
    "timeout-override-replay": ["replay", "dir", "--timeout-seconds", "5"],
    "invalid-provider": ["lock", "--provider", SENTINEL],
    "extra-token": ["demo", "--out", "x", SENTINEL],
    "missing-hash-value": ["replay", "dir", "--expected-lock-sha256"],
    "json-with-value": ["demo", "--out", "x", f"--json={SENTINEL}"],
}


@pytest.mark.parametrize("name", sorted(USAGE_CASES))
def test_malformed_usage_is_error_3_with_parseable_json(
    entry: tuple[str, ...], tmp_path: Path, name: str
) -> None:
    argv = USAGE_CASES[name]
    text = run_cli(entry, argv, cwd=tmp_path)
    assert text.code == 3
    assert text.stdout == ""
    assert "error: usage:" in text.stderr
    assert SENTINEL not in text.stderr
    as_json = run_cli(entry, [*argv, "--json"], cwd=tmp_path)
    assert as_json.code == 3
    assert as_json.stderr == ""
    document = as_json.json()
    assert document["status"] == "ERROR"
    assert document["ok"] is False
    assert document["exit_code"] == 3
    assert str(document["error"]).startswith("usage:")
    assert SENTINEL not in as_json.stdout
    assert sorted(path.name for path in tmp_path.iterdir()) == []


def test_invalid_expected_hash_and_missing_bundle_are_error_3(
    entry: tuple[str, ...], tmp_path: Path
) -> None:
    for bad_hex in ("nothex", "A" * 64, "a" * 63, f"{SENTINEL}{'a' * 50}"):
        result = run_cli(
            entry,
            ["replay", str(tmp_path / "absent"), "--expected-lock-sha256", bad_hex, "--json"],
            cwd=tmp_path,
        )
        assert result.code == 3, bad_hex
        document = result.json()
        assert document["status"] == "ERROR"
        assert "SchemaError" in str(document["error"])
        assert SENTINEL not in result.stdout
    missing = run_cli(entry, ["replay", str(tmp_path / "absent"), "--json"], cwd=tmp_path)
    assert missing.code == 3
    document = missing.json()
    assert document["status"] == "ERROR"
    assert document["reasons"] == ["integrity.bundle_io"]
    assert document["lock_sha256"] == "0" * 64
    assert (document["total"], document["accepted"], document["errors"]) == (0, 0, 0)
    assert document["risk"] == {"lower": 0.0, "upper": 1.0}
    assert document["coverage"] == {"lower": 0.0, "upper": 1.0}


def test_provider_option_rules_and_fixture_offline(entry: tuple[str, ...], tmp_path: Path) -> None:
    workspace = write_workspace(tmp_path / "ws", count=6, prefix="off")
    lock = tmp_path / "lock.json"
    laya_with_responses = lock_argv(workspace, lock)
    laya_with_responses[laya_with_responses.index("--provider") + 1] = "laya"
    result = run_cli(entry, [*laya_with_responses, "--json"], cwd=tmp_path)
    assert result.code == 3
    assert result.json()["error"] == "usage: --responses is not accepted with --provider laya"
    without_responses = lock_argv(workspace, lock)
    del without_responses[
        without_responses.index("--responses") : (without_responses.index("--responses") + 2)
    ]
    result = run_cli(entry, without_responses, cwd=tmp_path)
    assert result.code == 3
    assert "--responses is required with --provider fixture" in result.stderr
    assert not lock.exists()
    # fixture --offline is an accepted no-op: a full real run with the identical lock.
    offline = run_cli(entry, [*lock_argv(workspace, lock, "--offline"), "--json"], cwd=tmp_path)
    assert offline.code == 0, offline.stderr
    plain_lock = tmp_path / "plain.json"
    plain = run_cli(entry, lock_argv(workspace, plain_lock), cwd=tmp_path)
    assert plain.code == 0
    assert lock.read_bytes() == plain_lock.read_bytes()
    out = tmp_path / "evidence"
    argv = [*verify_argv(workspace, lock, out, "--offline"), "--json"]
    verified = run_cli(entry, argv, cwd=tmp_path)
    assert verified.code == 2, verified.stderr
    assert verified.json()["status"] == "INCONCLUSIVE"
    replayed = run_cli(entry, ["replay", str(out)], cwd=tmp_path)
    assert replayed.code == 2


# --------------------------------------------------------------------------- #
# Acceptance 1: recorded changes invalidate locked evidence
# --------------------------------------------------------------------------- #


def test_changed_inputs_or_fixture_are_refused_before_collection(
    entry: tuple[str, ...], tmp_path: Path
) -> None:
    workspace = write_workspace(tmp_path / "ws", count=6, prefix="chg")
    lock = tmp_path / "lock.json"
    assert run_cli(entry, lock_argv(workspace, lock), cwd=tmp_path).code == 0
    out = tmp_path / "evidence"
    # Source change: one gold label edited in the verification split.
    relabelled = tmp_path / "relabelled.jsonl"
    text = workspace.verification.read_text(encoding="utf-8")
    assert '"expected_label": "billing"' in text
    relabelled.write_text(
        text.replace('"expected_label": "billing"', '"expected_label": "sales"', 1),
        encoding="utf-8",
    )
    argv = verify_argv(workspace, lock, out, "--json")
    argv[argv.index("--verification") + 1] = str(relabelled)
    result = run_cli(entry, argv, cwd=tmp_path)
    assert result.code == 3
    assert "IntegrityError: verification_sha256" in str(result.json()["error"])
    assert not out.exists()
    # Model change: a different recorded-response file is a different identity.
    other = write_workspace(tmp_path / "other", count=6, selected=0.96, prefix="chg")
    argv = verify_argv(workspace, lock, out)
    argv[argv.index("--responses") + 1] = str(other.responses)
    result = run_cli(entry, argv, cwd=tmp_path)
    assert result.code == 3
    assert "IntegrityError: model_identity" in result.stderr
    assert not out.exists()
    # Provider change against the locked provider.
    argv = verify_argv(workspace, lock, out)
    argv[argv.index("--provider") + 1] = "laya"
    del argv[argv.index("--responses") : argv.index("--responses") + 2]
    result = run_cli(entry, argv, cwd=tmp_path)
    assert result.code == 3
    assert "IntegrityError: model_identity.provider" in result.stderr
    assert not out.exists()
    assert sorted(p.name for p in tmp_path.iterdir() if p.name.startswith(".actseal")) == []


def test_edited_lock_fields_cannot_reuse_the_original_experiment(
    entry: tuple[str, ...], tmp_path: Path
) -> None:
    """Threshold/schema/label/implementation edits are new or invalid locks, never the same one."""
    workspace = write_workspace(tmp_path / "ws", count=6, prefix="lk")
    lock = tmp_path / "lock.json"
    assert run_cli(entry, lock_argv(workspace, lock), cwd=tmp_path).code == 0
    original = read_document(lock)
    original_hash = str(original["sha256"])
    out = tmp_path / "evidence"
    assert run_cli(entry, verify_argv(workspace, lock, out), cwd=tmp_path).code == 2

    # Threshold edit, correctly resealed: verify runs a DIFFERENT experiment whose
    # evidence does not replay under the original trusted lock digest.
    raised = json.loads(json.dumps(original))
    raised["contract"]["policy"]["threshold"] = 0.96
    raised_path = tmp_path / "raised.json"
    raised_path.write_bytes(canonical(reseal_lock(raised)) + b"\n")
    raised_out = tmp_path / "raised.evidence"
    argv = [*verify_argv(workspace, raised_path, raised_out), "--json"]
    result = run_cli(entry, argv, cwd=tmp_path)
    assert result.code == 2
    document = result.json()
    assert document["lock_sha256"] != original_hash
    assert document["accepted"] == 0  # 0.95 < 0.96: every case abstains under the new lock
    assert document["reasons"] == ["evidence.insufficient", "risk.no_accepted_cases"]
    anchored = run_cli(
        entry,
        ["replay", str(raised_out), "--expected-lock-sha256", original_hash, "--json"],
        cwd=tmp_path,
    )
    assert anchored.code == 3
    assert anchored.json()["reasons"] == ["integrity.expected_lock"]

    # Edits that are not valid experiments at all.
    unsealed = json.loads(json.dumps(original))
    unsealed["contract"]["policy"]["threshold"] = 0.5
    foreign_impl = json.loads(json.dumps(original))
    foreign_impl["implementation_sha256"] = "e" * 64
    schema = json.loads(json.dumps(original))
    schema["schema_version"] = 2
    relabelled = json.loads(json.dumps(original))
    relabelled["verification_cases"][0]["expected_label"] = "sales"
    invalid_locks = {
        "threshold-without-reseal": (unsealed, "IntegrityError: sha256"),
        "foreign-implementation": (reseal_lock(foreign_impl), "IntegrityError: implementation"),
        "schema-version": (reseal_lock(schema), "SchemaError"),
        "label-with-stale-inventory": (reseal_lock(relabelled), "IntegrityError"),
    }
    for name, (document_data, expected_error) in invalid_locks.items():
        path = tmp_path / f"{name}.json"
        path.write_bytes(canonical(document_data) + b"\n")
        destination = tmp_path / f"{name}.evidence"
        argv = [*verify_argv(workspace, path, destination), "--json"]
        result = run_cli(entry, argv, cwd=tmp_path)
        assert result.code == 3, name
        assert expected_error in str(result.json()["error"]), name
        assert not destination.exists(), name
    assert sorted(p.name for p in tmp_path.iterdir() if p.name.startswith(".actseal")) == []


def test_existing_destinations_are_never_overwritten(
    entry: tuple[str, ...], tmp_path: Path
) -> None:
    workspace = write_workspace(tmp_path / "ws", count=6, prefix="ow")
    lock = tmp_path / "lock.json"
    assert run_cli(entry, lock_argv(workspace, lock), cwd=tmp_path).code == 0
    lock_bytes = lock.read_bytes()
    result = run_cli(entry, [*lock_argv(workspace, lock), "--json"], cwd=tmp_path)
    assert result.code == 3
    assert result.json()["error"] == "destination already exists"
    assert lock.read_bytes() == lock_bytes
    out = tmp_path / "evidence"
    assert run_cli(entry, verify_argv(workspace, lock, out), cwd=tmp_path).code == 2
    before = tree(out)
    result = run_cli(entry, verify_argv(workspace, lock, out), cwd=tmp_path)
    assert result.code == 3
    assert "destination already exists" in result.stderr
    assert tree(out) == before
    dangling = tmp_path / "dangling"
    dangling.symlink_to(tmp_path / "nowhere")
    result = run_cli(entry, verify_argv(workspace, lock, dangling), cwd=tmp_path)
    assert result.code == 3
    assert not (tmp_path / "nowhere").exists()


def test_demo_block_and_pass_replay_with_their_lock_digests(
    entry: tuple[str, ...], tmp_path: Path
) -> None:
    out = tmp_path / "demo"
    result = run_cli(entry, ["demo", "--out", str(out), "--json"], cwd=tmp_path)
    assert result.code == 0, result.stderr
    document = result.json()
    assert document["ok"] is True
    assert document["demo_only"] is True
    runs = document["runs"]
    assert isinstance(runs, dict)
    assert list(runs) == ["bad", "fixed"]
    for name, status in (("bad", "BLOCK"), ("fixed", "PASS")):
        run = runs[name]
        assert isinstance(run, dict)
        assert run["status"] == status
        assert run["as_expected"] is True
        assert run["replay_matches"] is True
        assert_matches_oracle(
            {**run, "exit_code": EXIT_CODES[status]},
            total=128,
            accepted=128,
            errors=32 if name == "bad" else 0,
        )
        replayed = run_cli(
            entry,
            ["replay", str(run["evidence"]), "--expected-lock-sha256", str(run["lock_sha256"])],
            cwd=tmp_path,
        )
        assert replayed.code == EXIT_CODES[status]
    again = run_cli(entry, ["demo", "--out", str(out), "--json"], cwd=tmp_path)
    assert again.code == 3
    assert again.json()["error"] == "destination already exists"


def test_captured_failures_count_against_a_strict_coverage_limit(tmp_path: Path) -> None:
    """Two transport failures among 30 cases stay in n; a strict coverage limit BLOCKs."""
    entry = ENTRIES["module"]
    min_coverage = 0.999
    strict = contract_toml(name="strict-coverage", min_coverage=min_coverage)
    workspace = write_workspace(
        tmp_path / "ws", count=30, failures={1: "provider_error", 4: "rate_limit"}, contract=strict
    )
    lock = tmp_path / "lock.json"
    assert run_cli(entry, lock_argv(workspace, lock), cwd=tmp_path).code == 0
    out = tmp_path / "evidence"
    result = run_cli(entry, [*verify_argv(workspace, lock, out), "--json"], cwd=tmp_path)
    risk, coverage = expected_bounds(30, 28, 0, 0.05)
    assert coverage[1] < min_coverage  # independently: the coverage upper bound is below the limit
    assert result.code == 1
    document = result.json()
    assert document["status"] == "BLOCK"
    assert document["reasons"] == ["coverage.below_minimum"]
    assert (document["total"], document["accepted"], document["errors"]) == (30, 28, 0)
    assert document["failures"] == {"provider_error": 1, "rate_limit": 1}
    assert document["coverage"] == {
        "lower": pytest.approx(coverage[0], abs=1e-9),
        "upper": pytest.approx(coverage[1], abs=1e-9),
    }
    assert document["risk"] == {
        "lower": pytest.approx(risk[0], abs=1e-9),
        "upper": pytest.approx(risk[1], abs=1e-9),
    }
    assert set(LABELS) == {"billing", "technical", "sales"}
