"""The ``actseal`` command line: exact shapes, exit codes, output discipline, isolation.

Commands run in-process through ``actseal.cli.main`` against the packaged
ADR 0013 inputs (copied into pytest temporary directories) or small datasets
built with the real authorities. Expected statuses come from the pipeline
itself (``assess``/``replay``) or from the prespecified demo inequalities; no
metric is authored. Subprocess tests prove that ``replay`` and ``demo`` work
with provider imports and network access denied.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import NoReturn

import pytest
from test_evidence import CALIBRATION, GOLD, answer_json, verification_jsonl
from test_providers import pinned_identity
from test_runner import CONTRACT_TOML, RESOURCE_NAMES, ScriptedModel, write_responses

import actseal
import actseal.cli as cli_module
import actseal.experimental.providers.jev as jev_module
import actseal.runner as runner_module
from actseal.adapters.base import DecisionModel
from actseal.assessment import REASON_WORKER_INVALIDATED
from actseal.cli import EXIT_CODES, EXIT_ERROR, main
from actseal.contract import parse_contract, read_input_text
from actseal.evidence import BUNDLE_FILES
from actseal.locking import parse_lock, validate_lock
from actseal.records import ModelIdentity
from actseal.replay import UNKNOWN_LOCK_SHA256, replay
from actseal.serialization import canonical_json, to_data
from provider_support import JevProfile

ROOT = Path(__file__).resolve().parents[2]
PACKAGED = ROOT / "src" / "actseal" / "demo_data"
FULL = {"lower": 0.0, "upper": 1.0}

Run = Callable[[Sequence[str]], tuple[int, str, str]]


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def run(capsys: pytest.CaptureFixture[str]) -> Run:
    def invoke(argv: Sequence[str]) -> tuple[int, str, str]:
        code = main(argv)
        captured = capsys.readouterr()
        return code, captured.out, captured.err

    return invoke


@pytest.fixture
def inputs(tmp_path: Path) -> dict[str, Path]:
    directory = tmp_path / "inputs"
    directory.mkdir()
    paths: dict[str, Path] = {}
    for name in RESOURCE_NAMES:
        target = directory / name
        target.write_bytes((PACKAGED / name).read_bytes())
        paths[name] = target
    return paths


def lock_argv(inputs: dict[str, Path], run_name: str, out: Path, *extra: str) -> list[str]:
    return [
        "lock",
        "--contract",
        str(inputs[f"{run_name}.toml"]),
        "--calibration",
        str(inputs[f"{run_name}_calibration.jsonl"]),
        "--verification",
        str(inputs[f"{run_name}_verification.jsonl"]),
        "--provider",
        "fixture",
        "--responses",
        str(inputs[f"{run_name}_responses.jsonl"]),
        "--out",
        str(out),
        *extra,
    ]


def verify_argv(
    inputs: dict[str, Path], run_name: str, lock: Path, out: Path, *extra: str
) -> list[str]:
    return [
        "verify",
        "--lock",
        str(lock),
        "--calibration",
        str(inputs[f"{run_name}_calibration.jsonl"]),
        "--verification",
        str(inputs[f"{run_name}_verification.jsonl"]),
        "--provider",
        "fixture",
        "--responses",
        str(inputs[f"{run_name}_responses.jsonl"]),
        "--out",
        str(out),
        *extra,
    ]


def one_json(stdout: str) -> dict[str, object]:
    """``--json`` output is exactly one JSON object on one line."""
    assert stdout.endswith("\n")
    assert stdout.count("\n") == 1
    document = json.loads(stdout)
    assert isinstance(document, dict)
    return document


def locked(run: Run, inputs: dict[str, Path], run_name: str, tmp_path: Path) -> Path:
    out = tmp_path / f"{run_name}.lock.json"
    code, _, _ = run(lock_argv(inputs, run_name, out))
    assert code == 0
    return out


def verified(run: Run, inputs: dict[str, Path], run_name: str, tmp_path: Path) -> tuple[int, Path]:
    lock = locked(run, inputs, run_name, tmp_path)
    out = tmp_path / f"{run_name}.evidence"
    code, _, _ = run(verify_argv(inputs, run_name, lock, out))
    return code, out


# --------------------------------------------------------------------------- #
# Usage, help, exit codes
# --------------------------------------------------------------------------- #


USAGE_ERRORS: list[list[str]] = [
    [],
    ["bogus"],
    ["--json"],
    ["lock"],
    ["verify"],
    ["replay"],
    ["demo"],
    ["demo", "--out"],
    ["demo", "--out", "x", "--timeout-seconds", "5"],
    ["verify", "--timeout-seconds", "5"],
    ["replay", "dir", "--timeout-seconds", "5"],
    ["lock", "--provider", "jev"],
    ["demo", "--out", "x", "extra"],
    ["replay", "dir", "--expected-lock-sha256"],
    ["verify", "--lock", "l", "--calibration", "c", "--verification", "v", "--out", "o"],
    # --experimental-provider belongs to lock/verify only; replay and demo reject it.
    ["replay", "dir", "--experimental-provider"],
    ["demo", "--out", "x", "--experimental-provider"],
    ["--experimental-provider", "replay", "dir"],
]


@pytest.mark.parametrize(
    "argv",
    [argv for argv in USAGE_ERRORS if "--json" not in argv],
    ids=lambda argv: " ".join(argv) or "<none>",
)
def test_usage_errors_exit_3_in_text_mode(run: Run, argv: list[str]) -> None:
    code, out, err = run(argv)
    assert code == EXIT_ERROR == 3
    assert out == ""
    assert "error: usage:" in err


@pytest.mark.parametrize("argv", USAGE_ERRORS, ids=lambda argv: " ".join(argv) or "<none>")
def test_usage_errors_exit_3_in_json_mode(run: Run, argv: list[str]) -> None:
    code, out, err = run([*argv, "--json"])
    assert code == 3
    document = one_json(out)
    assert document["exit_code"] == 3
    assert document["status"] == "ERROR"
    assert document["ok"] is False
    assert str(document["error"]).startswith("usage:")
    assert err == ""


@pytest.mark.parametrize(
    "argv",
    [
        ["--help"],
        ["-h"],
        ["lock", "--help"],
        ["verify", "-h"],
        ["replay", "--help"],
        ["demo", "-h"],
    ],
)
def test_help_exits_0(run: Run, argv: list[str]) -> None:
    code, out, _ = run(argv)
    assert code == 0
    assert out.startswith("usage: actseal")
    assert "--timeout-seconds" not in out


def test_help_lists_exactly_the_frozen_commands(run: Run) -> None:
    _, out, _ = run(["--help"])
    for command in ("lock", "verify", "replay", "demo"):
        assert f"\n    {command} " in out
    _, lock_help, _ = run(["lock", "--help"])
    for option in ("--contract", "--calibration", "--verification", "--provider", "--responses"):
        assert option in lock_help
    assert "--offline" in lock_help
    assert "--experimental-provider" in lock_help
    assert "{fixture,laya,jev}" in lock_help
    assert "--out" in lock_help
    assert "--json" in lock_help
    _, verify_help, _ = run(["verify", "--help"])
    assert "--experimental-provider" in verify_help
    assert "{fixture,laya,jev}" in verify_help
    _, replay_help, _ = run(["replay", "--help"])
    assert "--expected-lock-sha256" in replay_help
    assert "--provider" not in replay_help
    assert "--experimental-provider" not in replay_help
    _, demo_help, _ = run(["demo", "--help"])
    assert "--provider" not in demo_help
    assert "--experimental-provider" not in demo_help


def test_version_exits_0(run: Run) -> None:
    code, out, err = run(["--version"])
    assert code == 0
    assert err == ""
    # The 1.0.1 release candidate (amendment V1-055); the printed version is
    # always the installed package's own version string.
    assert actseal.__version__ == "1.0.1"
    assert out == f"actseal {actseal.__version__}\n"


def test_exit_code_table_is_frozen() -> None:
    assert dict(EXIT_CODES) == {"PASS": 0, "BLOCK": 1, "INCONCLUSIVE": 2, "ERROR": 3}


def test_main_reads_sys_argv_by_default(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["actseal", "--help"])
    assert main() == 0
    assert capsys.readouterr().out.startswith("usage: actseal")


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (["--responses", "r.jsonl"], "--responses is not accepted with --provider laya"),
        ([], "--responses is required with --provider fixture"),
    ],
)
def test_provider_option_rules(
    run: Run, tmp_path: Path, inputs: dict[str, Path], argv: list[str], message: str
) -> None:
    provider = "laya" if "--responses" in argv else "fixture"
    base = [
        "lock",
        "--contract",
        str(inputs["bad.toml"]),
        "--calibration",
        str(inputs["bad_calibration.jsonl"]),
        "--verification",
        str(inputs["bad_verification.jsonl"]),
        "--provider",
        provider,
        "--out",
        str(tmp_path / "lock.json"),
    ]
    code, out, err = run([*base, *argv])
    assert code == 3
    assert message in err
    assert out == ""
    assert not (tmp_path / "lock.json").exists()
    code, out, err = run([*base, *argv, "--json"])
    assert code == 3
    assert one_json(out)["error"] == f"usage: {message}"


def test_fixture_offline_workflow_succeeds(
    run: Run, inputs: dict[str, Path], tmp_path: Path
) -> None:
    """``--offline`` with the fixture provider states its existing behavior: a full real run."""
    lock = tmp_path / "lock.json"
    code, stdout, stderr = run(lock_argv(inputs, "fixed", lock, "--offline", "--json"))
    assert code == 0
    assert stderr == ""
    assert one_json(stdout)["ok"] is True
    out = tmp_path / "evidence"
    code, stdout, stderr = run(verify_argv(inputs, "fixed", lock, out, "--offline", "--json"))
    assert code == 0
    assert stderr == ""
    document = one_json(stdout)
    assert document["status"] == "PASS"
    assert (document["total"], document["accepted"], document["errors"]) == (128, 128, 0)
    assert replay(out).status == "PASS"
    assert run(["replay", str(out)])[0] == 0
    # The same inputs without --offline produce the identical lock: the flag changes nothing.
    again = tmp_path / "again.json"
    assert run(lock_argv(inputs, "fixed", again))[0] == 0
    assert again.read_bytes() == lock.read_bytes()


SENTINEL = "PRIVATE_SENTINEL_7f3a"


def sentinel_argvs(inputs: dict[str, Path], tmp_path: Path) -> list[list[str]]:
    """Command lines whose only defect carries a synthetic secret in a raw argv value."""
    lock = lock_argv(inputs, "fixed", tmp_path / "lock.json")
    bad_provider = list(lock)
    bad_provider[bad_provider.index("--provider") + 1] = SENTINEL
    return [
        [SENTINEL],
        [f"--{SENTINEL}"],
        ["demo", "--out", str(tmp_path / "demo"), SENTINEL],
        ["demo", "--out", str(tmp_path / "demo"), f"--{SENTINEL}"],
        ["demo", "--out", str(tmp_path / "demo"), f"--{SENTINEL}={SENTINEL}"],
        ["demo", "--out", str(tmp_path / "demo"), f"--json={SENTINEL}"],
        ["demo", f"--out={SENTINEL}", f"--timeout-seconds={SENTINEL}"],
        ["replay", str(tmp_path / "absent"), "--timeout-seconds", SENTINEL],
        ["replay", str(tmp_path / "absent"), "--expected-lock-sha256", SENTINEL],
        bad_provider,
        [*lock, "--offline", SENTINEL],
    ]


def test_usage_errors_never_echo_argv_values(
    run: Run, inputs: dict[str, Path], tmp_path: Path
) -> None:
    for argv in sentinel_argvs(inputs, tmp_path):
        for mode in ([], ["--json"]):
            code, out, err = run([*argv, *mode])
            assert code == 3, argv
            assert SENTINEL not in out, argv
            assert SENTINEL not in err, argv
            if mode:
                document = one_json(out)
                assert document["status"] == "ERROR"
                assert SENTINEL not in json.dumps(document)
            else:
                assert out == ""
                assert err.startswith("actseal ")
    assert not (tmp_path / "lock.json").exists()
    assert not (tmp_path / "demo").exists()


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (
            [SENTINEL],
            "usage: argument COMMAND: invalid choice (choose from lock, verify, replay, demo)",
        ),
        ([f"--{SENTINEL}"], "usage: the following arguments are required: COMMAND"),
        (
            ["demo", "--out", "x", f"--{SENTINEL}"],
            "usage: unrecognized arguments: 1 token(s) not accepted; see --help",
        ),
        (
            ["demo", "--out", "x", SENTINEL, f"--{SENTINEL}"],
            "usage: unrecognized arguments: 2 token(s) not accepted; see --help",
        ),
        (
            ["demo", "--out", "x", f"--json={SENTINEL}"],
            "usage: argument --json: does not take a value",
        ),
        (["demo", "--out"], "usage: argument --out: expected one argument"),
        (["demo"], "usage: the following arguments are required: --out"),
        ([], "usage: the following arguments are required: COMMAND"),
    ],
)
def test_usage_diagnostics_stay_bounded_and_useful(
    run: Run, argv: list[str], expected: str
) -> None:
    code, out, _ = run([*argv, "--json"])
    assert code == 3
    assert one_json(out)["error"] == expected
    code, out, err = run(argv)
    assert code == 3
    assert out == ""
    assert err.endswith(f": error: {expected}\n")


def test_invalid_provider_choice_lists_only_accepted_choices(
    run: Run, inputs: dict[str, Path], tmp_path: Path
) -> None:
    argv = lock_argv(inputs, "fixed", tmp_path / "lock.json")
    argv[argv.index("--provider") + 1] = SENTINEL
    code, out, _ = run([*argv, "--json"])
    assert code == 3
    assert one_json(out)["error"] == (
        "usage: argument --provider: invalid choice (choose from fixture, laya, jev)"
    )
    code, _, err = run(argv)
    assert code == 3
    assert err == (
        "actseal lock: error: usage: argument --provider: invalid choice "
        "(choose from fixture, laya, jev)\n"
    )


def test_bounded_usage_message_rewrites_every_shape() -> None:
    rewrite = cli_module._bounded_usage_message
    assert rewrite(f"argument --provider: invalid choice: '{SENTINEL}' (choose from 'a')") == (
        "argument --provider: invalid choice (choose from fixture, laya, jev)"
    )
    assert rewrite(f"argument COMMAND: invalid choice: '{SENTINEL}: x' (choose from 'a')") == (
        "argument COMMAND: invalid choice (choose from lock, verify, replay, demo)"
    )
    assert rewrite(f"argument --other: invalid choice: '{SENTINEL}'") == (
        "argument --other: invalid choice"
    )
    assert (
        rewrite("argument --out: expected one argument") == "argument --out: expected one argument"
    )
    assert (
        rewrite("argument DIRECTORY: expected 2 arguments")
        == "argument DIRECTORY: expected 2 arguments"
    )
    assert rewrite(f"argument --json: ignored explicit argument '{SENTINEL}'") == (
        "argument --json: does not take a value"
    )
    assert (
        rewrite(f"argument --out: invalid Path value: '{SENTINEL}'")
        == "argument --out: invalid value"
    )
    assert rewrite(f"unrecognized arguments: {SENTINEL}") == "invalid command line; see --help"
    assert rewrite(f"something unexpected {SENTINEL}") == "invalid command line; see --help"
    assert rewrite("the following arguments are required: --lock, --out") == (
        "the following arguments are required: --lock, --out"
    )


# --------------------------------------------------------------------------- #
# lock
# --------------------------------------------------------------------------- #


def test_lock_writes_a_validated_lock_and_reports_identity(
    run: Run, inputs: dict[str, Path], tmp_path: Path
) -> None:
    out = tmp_path / "lock.json"
    code, stdout, stderr = run(lock_argv(inputs, "fixed", out))
    assert code == 0
    assert stderr == ""
    lock = parse_lock(read_input_text(out))
    validate_lock(lock)
    assert out.read_bytes() == canonical_json(to_data(lock)) + b"\n"
    assert lock.model_identity.provider == "fixture"
    assert (
        lock.model_identity.revision
        == hashlib.sha256(inputs["fixed_responses.jsonl"].read_bytes()).hexdigest()
    )
    assert f"lock_sha256: {lock.sha256}" in stdout
    assert f"implementation_sha256: {lock.implementation_sha256}" in stdout
    assert "provider: fixture" in stdout
    assert "verification_cases: 128" in stdout
    assert "calibration_cases: 12" in stdout
    assert f"out: {out}" in stdout


def test_lock_json_output(run: Run, inputs: dict[str, Path], tmp_path: Path) -> None:
    out = tmp_path / "lock.json"
    code, stdout, stderr = run(lock_argv(inputs, "bad", out, "--json"))
    assert code == 0
    assert stderr == ""
    document = one_json(stdout)
    lock = parse_lock(read_input_text(out))
    assert document["command"] == "lock"
    assert document["exit_code"] == 0
    assert document["ok"] is True
    assert document["lock_sha256"] == lock.sha256
    assert document["implementation_sha256"] == lock.implementation_sha256
    assert document["evidence_scope"] == "demo"
    assert document["contract"] == "support-triage-bad"
    assert document["model_identity"] == {
        "provider": "fixture",
        "model": "recorded-choice-v1",
        "revision": lock.model_identity.revision,
        "adapter_version": "1",
        "normalizer_version": "1",
    }
    assert document["out"] == str(out)


def test_lock_never_overwrites_an_existing_path(
    run: Run, inputs: dict[str, Path], tmp_path: Path
) -> None:
    out = tmp_path / "lock.json"
    assert run(lock_argv(inputs, "fixed", out))[0] == 0
    before = out.read_bytes()
    code, stdout, stderr = run(lock_argv(inputs, "bad", out))
    assert code == 3
    assert stdout == ""
    assert "destination already exists" in stderr
    assert out.read_bytes() == before
    code, stdout, _ = run(lock_argv(inputs, "bad", out, "--json"))
    assert code == 3
    assert one_json(stdout)["error"] == "destination already exists"
    assert out.read_bytes() == before


def test_lock_rejects_leaking_datasets_as_error_3(
    run: Run, inputs: dict[str, Path], tmp_path: Path
) -> None:
    argv = lock_argv(inputs, "fixed", tmp_path / "lock.json")
    argv[argv.index("--calibration") + 1] = str(inputs["fixed_verification.jsonl"])
    code, _, stderr = run(argv)
    assert code == 3
    assert "SchemaError" in stderr
    assert not (tmp_path / "lock.json").exists()


def test_os_errors_are_sanitized_without_echoing_paths(
    run: Run, inputs: dict[str, Path], tmp_path: Path
) -> None:
    secret = tmp_path / "secret-directory-name" / "contract.toml"
    argv = lock_argv(inputs, "fixed", tmp_path / "lock.json")
    argv[argv.index("--contract") + 1] = str(secret)
    code, stdout, stderr = run(argv)
    assert code == 3
    assert stdout == ""
    assert "operating-system error" in stderr
    assert "secret-directory-name" not in stderr
    code, stdout, stderr = run([*argv, "--json"])
    assert code == 3
    document = one_json(stdout)
    assert "secret-directory-name" not in stdout
    assert str(document["error"]).startswith("operating-system error")


# --------------------------------------------------------------------------- #
# verify and replay against the demo inputs
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(("run_name", "expected"), [("bad", 1), ("fixed", 0)])
def test_verify_and_replay_exit_codes_follow_the_genuine_verdict(
    run: Run, inputs: dict[str, Path], tmp_path: Path, run_name: str, expected: int
) -> None:
    code, out = verified(run, inputs, run_name, tmp_path)
    assert code == expected
    assert sorted(p.name for p in out.iterdir()) == sorted(BUNDLE_FILES)
    verdict = replay(out)
    assert EXIT_CODES[verdict.status] == expected
    code, stdout, _ = run(["replay", str(out)])
    assert code == expected
    assert f"status: {verdict.status}" in stdout
    assert f"lock_sha256: {verdict.lock_sha256}" in stdout
    code, stdout, _ = run(["replay", str(out), "--expected-lock-sha256", verdict.lock_sha256])
    assert code == expected
    assert f"expected_lock_sha256: {verdict.lock_sha256}" in stdout


def test_verify_text_output_surfaces_every_documented_field(
    run: Run, inputs: dict[str, Path], tmp_path: Path
) -> None:
    lock = locked(run, inputs, "bad", tmp_path)
    out = tmp_path / "evidence"
    code, stdout, stderr = run(verify_argv(inputs, "bad", lock, out))
    assert code == 1
    verdict = replay(out)
    lines = stdout.splitlines()
    assert lines[0] == "status: BLOCK"
    assert lines[1] == "reasons: risk.exceeds_limit"
    assert lines[2] == "accepted/total: 128/128"
    assert lines[3] == "errors/accepted: 32/128"
    assert lines[4] == f"risk: [{verdict.risk.lower!r}, {verdict.risk.upper!r}]"
    assert lines[5] == f"coverage: [{verdict.coverage.lower!r}, {verdict.coverage.upper!r}]"
    assert lines[6] == "evidence_scope: demo"
    assert lines[7] == f"lock_sha256: {verdict.lock_sha256}"
    assert lines[8].startswith("faults: fault.timeout=ESCALATE fault.rate_limit=ESCALATE")
    assert lines[8].endswith("fault.unknown_choice=DENY fault.low_confidence=ABSTAIN")
    assert lines[9] == f"out: {out}"
    assert "actseal verify: failures: none" in stderr
    assert "actseal verify: warnings: none" in stderr


def test_verify_json_output_is_complete_and_pure(
    run: Run, inputs: dict[str, Path], tmp_path: Path
) -> None:
    lock = locked(run, inputs, "fixed", tmp_path)
    out = tmp_path / "evidence"
    code, stdout, stderr = run(verify_argv(inputs, "fixed", lock, out, "--json"))
    assert code == 0
    assert stderr == ""
    document = one_json(stdout)
    verdict = replay(out)
    assert document["command"] == "verify"
    assert document["exit_code"] == 0
    assert document["ok"] is True
    assert document["status"] == "PASS"
    assert document["reasons"] == ["contract.satisfied"]
    assert (document["total"], document["accepted"], document["errors"]) == (128, 128, 0)
    assert document["risk"] == {"lower": verdict.risk.lower, "upper": verdict.risk.upper}
    assert document["coverage"] == {
        "lower": verdict.coverage.lower,
        "upper": verdict.coverage.upper,
    }
    assert document["evidence_scope"] == "demo"
    assert document["lock_sha256"] == verdict.lock_sha256
    assert document["failures"] == {}
    assert document["warnings"] == {}
    faults = document["faults"]
    assert isinstance(faults, dict)
    assert faults["fault.low_confidence"] == {"action": "ABSTAIN", "expected_action": "ABSTAIN"}
    assert len(faults) == 6
    assert document["out"] == str(out)


def test_failure_summary_counts_a_malformed_body_among_genuine_pass_evidence(
    run: Run, inputs: dict[str, Path], tmp_path: Path
) -> None:
    """One malformed fixture body among 128: statistical PASS with 127 accepted, 1 failure shown."""
    rows = inputs["fixed_responses.jsonl"].read_bytes().split(b"\n")
    broken = json.loads(rows[5])
    broken["body_json"] = "{"
    rows[5] = json.dumps(broken).encode("utf-8")
    responses = tmp_path / "one-malformed.jsonl"
    responses.write_bytes(b"\n".join(rows))
    lock = tmp_path / "lock.json"
    argv = lock_argv(inputs, "fixed", lock)
    argv[argv.index("--responses") + 1] = str(responses)
    assert run(argv)[0] == 0
    out = tmp_path / "evidence"
    argv = verify_argv(inputs, "fixed", lock, out, "--json")
    argv[argv.index("--responses") + 1] = str(responses)
    code, stdout, _ = run(argv)
    assert code == 0
    document = one_json(stdout)
    assert document["status"] == "PASS"
    assert (document["total"], document["accepted"], document["errors"]) == (128, 127, 0)
    assert document["failures"] == {"malformed_response": 1}
    assert document["warnings"] == {"normalize.invalid_json": 1}
    verdict = replay(out)
    assert (verdict.status, verdict.accepted) == ("PASS", 127)
    argv = verify_argv(inputs, "fixed", lock, tmp_path / "text")
    argv[argv.index("--responses") + 1] = str(responses)
    code, _, stderr = run(argv)
    assert code == 0
    assert "actseal verify: failures: malformed_response=1" in stderr
    assert "actseal verify: warnings: normalize.invalid_json=1" in stderr


def test_failure_summary_counts_every_normalized_failure_once(run: Run, tmp_path: Path) -> None:
    """Malformed, unknown-choice and transport failures each count once; warnings stay exact."""
    contract = tmp_path / "contract.toml"
    contract.write_text(CONTRACT_TOML, encoding="utf-8")
    calibration = tmp_path / "calibration.jsonl"
    calibration.write_bytes(CALIBRATION.encode("utf-8"))
    verification = tmp_path / "verification.jsonl"
    verification.write_bytes(verification_jsonl().encode("utf-8"))
    rows: dict[str, tuple[str | None, str | None]] = {
        cid: (answer_json(label), None) for cid, _, label in GOLD
    }
    rows["v-002"] = ("{", None)
    rows["v-003"] = (answer_json("billing").replace('"billing"', '"refunds"', 1), None)
    rows["v-004"] = (None, "rate_limit")
    rows["v-005"] = (None, "provider_error")
    responses = write_responses(tmp_path / "responses.jsonl", rows)
    common = [
        "--calibration",
        str(calibration),
        "--verification",
        str(verification),
        "--provider",
        "fixture",
        "--responses",
        str(responses),
    ]
    lock = tmp_path / "lock.json"
    assert run(["lock", "--contract", str(contract), *common, "--out", str(lock)])[0] == 0
    out = tmp_path / "evidence"
    code, stdout, _ = run(["verify", "--lock", str(lock), *common, "--out", str(out), "--json"])
    assert code == 2
    document = one_json(stdout)
    assert document["status"] == "INCONCLUSIVE"
    assert (document["total"], document["accepted"], document["errors"]) == (6, 2, 0)
    assert document["failures"] == {
        "malformed_response": 1,
        "provider_error": 1,
        "rate_limit": 1,
        "unknown_choice": 1,
    }
    assert document["warnings"] == {
        "normalize.invalid_json": 1,
        "normalize.unknown_choice": 1,
    }
    failures = document["failures"]
    assert isinstance(failures, dict)
    assert sum(failures.values()) == 4


def test_verify_refuses_a_different_fixture_before_any_call(
    run: Run, inputs: dict[str, Path], tmp_path: Path
) -> None:
    lock = locked(run, inputs, "bad", tmp_path)
    out = tmp_path / "evidence"
    argv = verify_argv(inputs, "bad", lock, out)
    argv[argv.index("--responses") + 1] = str(inputs["fixed_responses.jsonl"])
    code, stdout, stderr = run(argv)
    assert code == 3
    assert stdout == ""
    assert "IntegrityError: model_identity" in stderr
    assert not out.exists()


def test_verify_refuses_provider_and_input_mismatches(
    run: Run, inputs: dict[str, Path], tmp_path: Path
) -> None:
    lock = locked(run, inputs, "bad", tmp_path)
    out = tmp_path / "evidence"
    argv = verify_argv(inputs, "bad", lock, out)
    laya = list(argv)
    laya[laya.index("--provider") + 1] = "laya"
    del laya[laya.index("--responses") : laya.index("--responses") + 2]
    code, _, stderr = run(laya)
    assert code == 3
    assert "IntegrityError: model_identity.provider" in stderr
    swapped = list(argv)
    swapped[swapped.index("--verification") + 1] = str(inputs["fixed_verification.jsonl"])
    code, _, stderr = run([*swapped, "--json"])
    assert code == 3
    assert not out.exists()


def test_verify_refuses_an_existing_destination(
    run: Run, inputs: dict[str, Path], tmp_path: Path
) -> None:
    lock = locked(run, inputs, "fixed", tmp_path)
    out = tmp_path / "evidence"
    assert run(verify_argv(inputs, "fixed", lock, out))[0] == 0
    before = {p.name: p.read_bytes() for p in out.iterdir()}
    code, _, stderr = run(verify_argv(inputs, "fixed", lock, out))
    assert code == 3
    assert "destination already exists" in stderr
    assert {p.name: p.read_bytes() for p in out.iterdir()} == before


def test_verify_rejects_timeout_override(run: Run, inputs: dict[str, Path], tmp_path: Path) -> None:
    lock = locked(run, inputs, "fixed", tmp_path)
    out = tmp_path / "evidence"
    code, _, stderr = run(verify_argv(inputs, "fixed", lock, out, "--timeout-seconds", "5"))
    assert code == 3
    assert "usage:" in stderr
    assert not out.exists()


def test_verify_inconclusive_exits_2(run: Run, tmp_path: Path) -> None:
    contract = tmp_path / "contract.toml"
    contract.write_text(CONTRACT_TOML, encoding="utf-8")
    calibration = tmp_path / "calibration.jsonl"
    calibration.write_bytes(CALIBRATION.encode("utf-8"))
    verification = tmp_path / "verification.jsonl"
    verification.write_bytes(verification_jsonl().encode("utf-8"))
    responses = write_responses(
        tmp_path / "responses.jsonl", {cid: (answer_json(label), None) for cid, _, label in GOLD}
    )
    lock = tmp_path / "lock.json"
    argv = [
        "--calibration",
        str(calibration),
        "--verification",
        str(verification),
        "--provider",
        "fixture",
        "--responses",
        str(responses),
    ]
    assert run(["lock", "--contract", str(contract), *argv, "--out", str(lock)])[0] == 0
    out = tmp_path / "evidence"
    code, stdout, _ = run(["verify", "--lock", str(lock), *argv, "--out", str(out), "--json"])
    assert code == 2
    document = one_json(stdout)
    assert document["status"] == "INCONCLUSIVE"
    assert document["reasons"] == ["evidence.insufficient"]
    assert (document["total"], document["accepted"]) == (6, 6)
    assert run(["replay", str(out)])[0] == 2


def test_verify_worker_loss_is_error_3_with_a_complete_diagnostic_bundle(
    run: Run, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A regular Laya timeout followed by unavailable captures: all retained, ERROR 3."""
    contract = tmp_path / "contract.toml"
    contract.write_text(CONTRACT_TOML, encoding="utf-8")
    calibration = tmp_path / "calibration.jsonl"
    calibration.write_bytes(CALIBRATION.encode("utf-8"))
    verification = tmp_path / "verification.jsonl"
    verification.write_bytes(verification_jsonl().encode("utf-8"))
    identity = pinned_identity()

    def script(case_id: str) -> tuple[str | None, str | None, tuple[str, ...]]:
        index = [cid for cid, _, _ in GOLD].index(case_id)
        if index < 2:
            return None, "timeout", ("laya.load_warning:RuntimeWarning:clamped",)
        return None, "unavailable", ("laya.unavailable:timeout",)

    models: list[ScriptedModel] = []

    def fake_open_model(provider: str, *, responses: Path | None, offline: bool) -> ScriptedModel:
        assert (provider, responses, offline) == ("laya", None, True)
        model = ScriptedModel(identity, script)
        models.append(model)
        return model

    monkeypatch.setattr(cli_module, "open_model", fake_open_model)
    common = ["--calibration", str(calibration), "--verification", str(verification)]
    lock = tmp_path / "lock.json"
    code, _, _ = run(
        [
            "lock",
            "--contract",
            str(contract),
            *common,
            "--provider",
            "laya",
            "--offline",
            "--out",
            str(lock),
        ]
    )
    assert code == 0
    out = tmp_path / "evidence"
    code, stdout, stderr = run(
        [
            "verify",
            "--lock",
            str(lock),
            *common,
            "--provider",
            "laya",
            "--offline",
            "--out",
            str(out),
            "--json",
        ]
    )
    assert code == 3
    assert stderr == ""
    document = one_json(stdout)
    assert document["status"] == "ERROR"
    assert document["reasons"] == [REASON_WORKER_INVALIDATED]
    assert (document["total"], document["accepted"], document["errors"]) == (0, 0, 0)
    assert document["risk"] == FULL
    assert document["coverage"] == FULL
    assert document["failures"] == {"timeout": 2, "unavailable": 4}
    assert document["warnings"] == {
        "laya.load_warning:RuntimeWarning:clamped": 2,
        "laya.unavailable:timeout": 4,
    }
    assert len(models) == 2  # one for lock, one for verify; never a replacement mid-run
    assert [cid for cid, _ in models[1].calls] == [cid for cid, _, _ in GOLD]
    assert {timeout for _, timeout in models[1].calls} == {30.0}
    assert all(model.closed == 1 for model in models)
    assert (out / "records.jsonl").read_bytes().count(b"\n") == 6
    assert replay(out).reasons == (REASON_WORKER_INVALIDATED,)
    code, stdout, stderr = run(["replay", str(out)])
    assert code == 3
    assert "status: ERROR" in stdout
    assert f"reasons: {REASON_WORKER_INVALIDATED}" in stdout
    code, stdout, stderr = run(
        [
            "verify",
            "--lock",
            str(lock),
            *common,
            "--provider",
            "laya",
            "--offline",
            "--out",
            str(tmp_path / "e2"),
        ]
    )
    assert code == 3
    assert "actseal verify: failures: timeout=2 unavailable=4" in stderr
    assert "laya.unavailable:timeout=4" in stderr


def test_verify_setup_failure_is_error_3_without_a_bundle(
    run: Run, inputs: dict[str, Path], tmp_path: Path
) -> None:
    lock = locked(run, inputs, "fixed", tmp_path)
    truncated = tmp_path / "truncated.jsonl"
    rows = inputs["fixed_responses.jsonl"].read_bytes().split(b"\n")
    truncated.write_bytes(b"\n".join(rows[:-2]) + b"\n")  # drops the final recorded case
    relock = tmp_path / "relock.json"
    argv = lock_argv(inputs, "fixed", relock)
    argv[argv.index("--responses") + 1] = str(truncated)
    assert run(argv)[0] == 0
    del lock
    out = tmp_path / "evidence"
    argv = verify_argv(inputs, "fixed", relock, out)
    argv[argv.index("--responses") + 1] = str(truncated)
    code, stdout, stderr = run(argv)
    assert code == 3
    assert stdout == ""
    assert "ProviderSetupError" in stderr
    assert not out.exists()
    assert [p.name for p in tmp_path.iterdir() if p.name.startswith(".actseal")] == []


def test_replay_errors(run: Run, inputs: dict[str, Path], tmp_path: Path) -> None:
    code, out = verified(run, inputs, "fixed", tmp_path)
    assert code == 0
    code, stdout, _ = run(["replay", str(out), "--expected-lock-sha256", "a" * 64, "--json"])
    assert code == 3
    document = one_json(stdout)
    assert document["status"] == "ERROR"
    assert document["reasons"] == ["integrity.expected_lock"]
    assert document["lock_sha256"] == replay(out).lock_sha256  # observed, never the expectation
    assert document["expected_lock_sha256"] == "a" * 64
    code, stdout, stderr = run(["replay", str(out), "--expected-lock-sha256", "nothex"])
    assert code == 3
    assert "SchemaError" in stderr
    code, stdout, _ = run(["replay", str(tmp_path / "absent"), "--json"])
    assert code == 3
    document = one_json(stdout)
    assert document["reasons"] == ["integrity.bundle_io"]
    assert document["lock_sha256"] == UNKNOWN_LOCK_SHA256
    (out / "verdict.json").write_bytes(b"{}\n")
    code, _, _ = run(["replay", str(out)])
    assert code == 3


# --------------------------------------------------------------------------- #
# demo
# --------------------------------------------------------------------------- #


def test_demo_succeeds_with_genuine_block_and_pass(run: Run, tmp_path: Path) -> None:
    out = tmp_path / "demo"
    code, stdout, stderr = run(["demo", "--out", str(out), "--json"])
    assert code == 0
    assert stderr == ""
    document = one_json(stdout)
    assert document["command"] == "demo"
    assert document["ok"] is True
    assert document["exit_code"] == 0
    assert document["evidence_scope"] == "demo"
    assert document["demo_only"] is True
    assert "not a population benchmark" in str(document["note"]).lower()
    assert document["out"] == str(out)
    duration = document["duration_s"]
    assert isinstance(duration, float)
    assert 0.0 <= duration < 60.0
    runs = document["runs"]
    assert isinstance(runs, dict)
    assert list(runs) == ["bad", "fixed"]
    for name, expected in (("bad", "BLOCK"), ("fixed", "PASS")):
        entry = runs[name]
        assert isinstance(entry, dict)
        assert entry["expected_status"] == expected
        assert entry["status"] == expected
        assert entry["as_expected"] is True
        assert entry["replay_matches"] is True
        replayed = entry["replay"]
        assert isinstance(replayed, dict)
        assert replayed["status"] == expected
        assert replayed["lock_sha256"] == entry["lock_sha256"]
        assert entry["evidence"] == str(out / name / "evidence")
        assert entry["lock"] == str(out / name / "lock.json")
        fresh = replay(out / name / "evidence", expected_lock_sha256=str(entry["lock_sha256"]))
        assert fresh.status == expected
        assert (entry["total"], entry["accepted"]) == (fresh.total, fresh.accepted) == (128, 128)
        assert entry["errors"] == fresh.errors
        assert entry["risk"] == {"lower": fresh.risk.lower, "upper": fresh.risk.upper}
    bad = runs["bad"]
    fixed = runs["fixed"]
    assert isinstance(bad, dict)
    assert isinstance(fixed, dict)
    assert bad["errors"] == 32
    assert fixed["errors"] == 0
    assert bad["reasons"] == ["risk.exceeds_limit"]
    assert fixed["reasons"] == ["contract.satisfied"]


def test_demo_text_output(run: Run, tmp_path: Path) -> None:
    out = tmp_path / "demo"
    code, stdout, stderr = run(["demo", "--out", str(out)])
    assert code == 0
    assert stdout.startswith("demo: Authored synthetic demonstration (evidence_scope=demo)")
    assert "[bad] expected BLOCK, observed BLOCK, replay BLOCK (match)" in stdout
    assert "[fixed] expected PASS, observed PASS, replay PASS (match)" in stdout
    assert "  errors/accepted: 32/128" in stdout
    assert "  errors/accepted: 0/128" in stdout
    assert stdout.rstrip().endswith("result: success")
    assert "actseal demo: [bad] failures: none" in stderr
    assert "actseal demo: [fixed] warnings: none" in stderr


def test_demo_refuses_existing_destination(run: Run, tmp_path: Path) -> None:
    out = tmp_path / "demo"
    out.mkdir()
    code, stdout, stderr = run(["demo", "--out", str(out), "--json"])
    assert code == 3
    assert one_json(stdout)["error"] == "destination already exists"
    assert stderr == ""
    assert list(out.iterdir()) == []


def test_demo_failure_is_error_3(run: Run, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(runner_module.DEMO_EXPECTED, "fixed", "BLOCK")
    code, stdout, _ = run(["demo", "--out", str(tmp_path / "demo"), "--json"])
    assert code == 3
    document = one_json(stdout)
    assert document["ok"] is False
    assert document["status"] == "ERROR"
    runs = document["runs"]
    assert isinstance(runs, dict)
    fixed = runs["fixed"]
    assert isinstance(fixed, dict)
    assert fixed["status"] == "PASS"  # the genuine result is still reported
    assert fixed["as_expected"] is False


# --------------------------------------------------------------------------- #
# Isolation: subprocess with provider imports and network denied
# --------------------------------------------------------------------------- #

_ISOLATED = r"""
import json
import socket
import sys

BLOCKED = tuple(sys.argv[1].split(","))


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

from actseal.cli import main  # noqa: E402

import io  # noqa: E402

buffer = io.StringIO()
real_stdout = sys.stdout
sys.stdout = buffer
try:
    code = main(sys.argv[2:])
finally:
    sys.stdout = real_stdout
loaded = sorted(name for name in sys.modules if _blocked(name))
print(json.dumps({"code": code, "stdout": buffer.getvalue(), "blocked_loaded": loaded}))
"""

REPLAY_BLOCKED = (
    "actseal.adapters,laya,torch,transformers,huggingface_hub,safetensors,numpy,"
    "importlib.metadata,subprocess,multiprocessing,urllib.request,http,ssl,pickle,runpy"
)
DEMO_BLOCKED = (
    "actseal.adapters.laya,laya,torch,transformers,huggingface_hub,safetensors,numpy,"
    "importlib.metadata,subprocess,multiprocessing,urllib.request,http,ssl,pickle,runpy"
)


def isolated(blocked: str, argv: Sequence[str]) -> dict[str, object]:
    result = subprocess.run(  # noqa: S603 - fixed interpreter and literal script, no user input
        [sys.executable, "-c", _ISOLATED, blocked, *argv],
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
        cwd=str(Path(sys.executable).parent),
        env={k: v for k, v in os.environ.items() if k != "PYTHONPATH"},
    )
    report = json.loads(result.stdout)
    assert isinstance(report, dict)
    return report


def test_replay_cli_works_with_adapters_and_network_denied(
    run: Run, inputs: dict[str, Path], tmp_path: Path
) -> None:
    code, out = verified(run, inputs, "bad", tmp_path)
    assert code == 1
    report = isolated(REPLAY_BLOCKED, ["replay", str(out), "--json"])
    assert report["blocked_loaded"] == []
    assert report["code"] == 1
    document = one_json(str(report["stdout"]))
    assert document["status"] == "BLOCK"
    assert document["lock_sha256"] == replay(out).lock_sha256


def test_demo_cli_works_with_live_providers_and_network_denied(tmp_path: Path) -> None:
    report = isolated(DEMO_BLOCKED, ["demo", "--out", str(tmp_path / "demo"), "--json"])
    assert report["blocked_loaded"] == []
    assert report["code"] == 0
    document = one_json(str(report["stdout"]))
    assert document["ok"] is True
    runs = document["runs"]
    assert isinstance(runs, dict)
    assert [runs[name]["status"] for name in ("bad", "fixed")] == ["BLOCK", "PASS"]


def test_module_entrypoint_runs_main() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "actseal", "--help"],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 0
    assert result.stdout.startswith("usage: actseal")
    result = subprocess.run(
        [sys.executable, "-m", "actseal"],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 3


def test_importing_the_cli_loads_no_adapter() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; import actseal.cli; import actseal.__main__; "
                "print(sorted(m for m in sys.modules if m.startswith("
                "('actseal.adapters', 'actseal.experimental', 'http', 'ssl'))))"
            ),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    assert result.stdout.strip() == "[]"


def test_sanitizer_never_echoes_exception_text() -> None:
    assert cli_module._sanitize(RuntimeError("secret token value")) == "unexpected RuntimeError"
    assert cli_module._sanitize(FileNotFoundError(2, "No such file", "/secret")) == (
        "operating-system error: No such file or directory"
    )
    assert cli_module._sanitize(FileExistsError(17, "exists", "/secret")) == (
        "destination already exists"
    )
    assert cli_module._sanitize(NotImplementedError("exclusive rename: x")) == (
        "unsupported platform operation: exclusive rename: x"
    )


def test_unexpected_exception_becomes_error_3(
    run: Run, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(_destination: Path) -> object:
        raise RuntimeError("secret detail")

    monkeypatch.setattr(cli_module, "demo_run", explode)
    code, stdout, stderr = run(["demo", "--out", str(tmp_path / "demo")])
    assert code == 3
    assert stdout == ""
    assert stderr == "actseal demo: error: unexpected RuntimeError\n"


def test_identity_helper_reports_only_identity_fields() -> None:
    identity = ModelIdentity("fixture", "m", "r", (), "1", "1", (("k", "v"),))
    assert cli_module._identity_data(identity) == {
        "provider": "fixture",
        "model": "m",
        "revision": "r",
        "adapter_version": "1",
        "normalizer_version": "1",
    }


# --------------------------------------------------------------------------- #
# PROVISIONAL Jev opt-in (ADR 0017): explicit flag, no key, no socket, mocked only
# --------------------------------------------------------------------------- #


def _forbidden(*_args: object, **_kwargs: object) -> NoReturn:
    pytest.fail("no provider may be built, no key read and no connection opened here")


def _forbid_provider_construction(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every seam that could build a provider, read the key or connect fails the test."""
    monkeypatch.delenv(jev_module.API_KEY_ENV, raising=False)
    monkeypatch.setattr(cli_module, "open_model", _forbidden)
    monkeypatch.setattr(cli_module, "lock_run", _forbidden)
    monkeypatch.setattr(cli_module, "verify_run", _forbidden)
    monkeypatch.setattr(jev_module, "_api_key_from_environment", _forbidden)
    monkeypatch.setattr(jev_module, "_default_connect", _forbidden)


EXPERIMENTAL_USAGE: list[tuple[str, list[str], str]] = [
    ("jev", [], "--experimental-provider is required with --provider jev"),
    (
        "jev",
        ["--responses", "r.jsonl"],
        "--experimental-provider is required with --provider jev",
    ),
    (
        "jev",
        ["--experimental-provider", "--responses", "r.jsonl"],
        "--responses is not accepted with --provider jev",
    ),
    (
        "fixture",
        ["--experimental-provider", "--responses", "r.jsonl"],
        "--experimental-provider is not accepted with --provider fixture",
    ),
    (
        "laya",
        ["--experimental-provider"],
        "--experimental-provider is not accepted with --provider laya",
    ),
    (
        "laya",
        ["--experimental-provider", "--offline"],
        "--experimental-provider is not accepted with --provider laya",
    ),
]


EXPERIMENTAL_USAGE_CASES: list[tuple[str, str, list[str], str]] = [
    (command, provider, extra, message)
    for command in ("lock", "verify")
    for provider, extra, message in EXPERIMENTAL_USAGE
]


@pytest.mark.parametrize(
    "case",
    EXPERIMENTAL_USAGE_CASES,
    ids=[
        f"{command} {provider} {' '.join(extra)}".strip()
        for command, provider, extra, _ in EXPERIMENTAL_USAGE_CASES
    ],
)
def test_experimental_flag_rules_are_usage_errors_before_any_provider_or_environment(
    run: Run,
    inputs: dict[str, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: tuple[str, str, list[str], str],
) -> None:
    """Missing or misplaced opt-in is a versioned usage ERROR 3 with nothing constructed."""
    command, provider, extra, message = case
    _forbid_provider_construction(monkeypatch)
    head = (
        ["lock", "--contract", str(inputs["fixed.toml"])]
        if command == "lock"
        else ["verify", "--lock", str(tmp_path / "absent-lock.json")]
    )
    out_path = tmp_path / "out"
    argv = [
        *head,
        "--calibration",
        str(inputs["fixed_calibration.jsonl"]),
        "--verification",
        str(inputs["fixed_verification.jsonl"]),
        "--provider",
        provider,
        *extra,
        "--out",
        str(out_path),
    ]
    code, out, err = run(argv)
    assert code == 3
    assert out == ""
    assert err == f"actseal {command}: error: usage: {message}\n"
    code, out, err = run([*argv, "--json"])
    assert code == 3
    assert err == ""
    document = one_json(out)
    assert document["schema_version"] == 1
    assert document["command"] == command
    assert document["status"] == "ERROR"
    assert document["error"] == f"usage: {message}"
    assert not out_path.exists()


def test_jev_offline_is_a_setup_error_before_the_key_is_read(
    run: Run, inputs: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``--provider jev --experimental-provider --offline`` is ERROR 3 from the adapter."""
    monkeypatch.delenv(jev_module.API_KEY_ENV, raising=False)
    monkeypatch.setattr(jev_module, "_api_key_from_environment", _forbidden)
    monkeypatch.setattr(jev_module, "_default_connect", _forbidden)
    lock = tmp_path / "lock.json"
    argv = [
        "lock",
        "--contract",
        str(inputs["fixed.toml"]),
        "--calibration",
        str(inputs["fixed_calibration.jsonl"]),
        "--verification",
        str(inputs["fixed_verification.jsonl"]),
        "--provider",
        "jev",
        "--experimental-provider",
        "--offline",
        "--out",
        str(lock),
    ]
    expected = (
        "ProviderSetupError: offline: the experimental Jev adapter has no offline mode; "
        "no request was made"
    )
    code, out, err = run([*argv, "--json"])
    assert code == 3
    assert err == ""
    document = one_json(out)
    assert document["status"] == "ERROR"
    assert document["error"] == expected
    assert not lock.exists()
    code, out, err = run(argv)
    assert code == 3
    assert out == ""
    assert err == f"actseal lock: error: {expected}\n"
    assert not lock.exists()


JEV_COMMON = (
    "--calibration",
    "fixed_calibration.jsonl",
    "--verification",
    "fixed_verification.jsonl",
)
JEV_SELECT = ("--provider", "jev", "--experimental-provider")


def _mock_jev_transport(
    inputs: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> tuple[JevProfile, str, list[DecisionModel]]:
    """Route ``open_model("jev")`` to a real ``JevModel`` over the conformance fake connection.

    No key is read (the environment read is forbidden and the variable is
    unset) and no socket is opened (the connection factory is forbidden).
    """
    monkeypatch.delenv(jev_module.API_KEY_ENV, raising=False)
    monkeypatch.setattr(jev_module, "_api_key_from_environment", _forbidden)
    monkeypatch.setattr(jev_module, "_default_connect", _forbidden)
    profile = JevProfile()
    body = profile.valid_raw_body(parse_contract(inputs["fixed.toml"]).question)
    opened: list[DecisionModel] = []

    def fake_jev(*, offline: bool = False) -> DecisionModel:
        assert offline is False
        model = profile.open(body=body)
        opened.append(model)
        return model

    monkeypatch.setattr(jev_module, "JevModel", fake_jev)
    return profile, body, opened


def _jev_common(inputs: dict[str, Path]) -> list[str]:
    return [inputs[token].as_posix() if token in inputs else token for token in JEV_COMMON]


def _jev_lock(run: Run, inputs: dict[str, Path], lock: Path) -> dict[str, object]:
    """Seal a Jev lock through the CLI opt-in; returns the JSON receipt."""
    argv = ["lock", "--contract", str(inputs["fixed.toml"]), *_jev_common(inputs), *JEV_SELECT]
    code, stdout, stderr = run([*argv, "--out", str(lock), "--json"])
    assert code == 0
    assert stderr == ""
    return one_json(stdout)


def test_jev_cli_round_trip_over_a_fake_transport(
    run: Run, inputs: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mocked end to end: lock, verify and replay through the explicit opt-in.

    The real ``JevModel`` runs over the conformance fake connection, so no key
    is read and no socket is opened. Receipt shapes are the fixture shapes:
    the opt-in adds no field, and ``model_identity`` names the provider. The
    bundle replays with the adapter, every transport module and the native
    stack denied.
    """
    profile, _, opened = _mock_jev_transport(inputs, monkeypatch)
    common = _jev_common(inputs)
    jev = list(JEV_SELECT)
    fixture_lock = locked(run, inputs, "fixed", tmp_path)
    code, stdout, _ = run(lock_argv(inputs, "fixed", tmp_path / "fixture-again.json", "--json"))
    assert code == 0
    fixture_lock_receipt = one_json(stdout)

    lock = tmp_path / "jev.lock.json"
    document = _jev_lock(run, inputs, lock)
    assert set(document) == set(fixture_lock_receipt)
    assert document["model_identity"] == {
        "provider": "jev",
        "model": jev_module.MODEL,
        "revision": jev_module.REVISION,
        "adapter_version": jev_module.ADAPTER_VERSION,
        "normalizer_version": "1",
    }
    sealed = parse_lock(read_input_text(lock))
    validate_lock(sealed)
    assert sealed.model_identity.provider == "jev"
    assert sealed.model_identity.artifact_hashes == ()
    assert document["lock_sha256"] == sealed.sha256

    out = tmp_path / "jev.evidence"
    code, stdout, stderr = run(
        ["verify", "--lock", str(lock), *common, *jev, "--out", str(out), "--json"]
    )
    assert stderr == ""
    document = one_json(stdout)
    verdict = replay(out, expected_lock_sha256=sealed.sha256)
    assert verdict.status != "ERROR"
    assert code == EXIT_CODES[verdict.status]
    assert document["status"] == verdict.status
    assert document["reasons"] == list(verdict.reasons)
    assert document["lock_sha256"] == verdict.lock_sha256 == sealed.sha256
    assert (document["total"], document["accepted"]) == (verdict.total, verdict.accepted)
    assert document["failures"] == {}
    assert len(opened) == 2  # one model for lock, one for verify; nothing replaced mid-run
    assert all(profile.worker_alive(model) is False for model in opened)
    assert profile.requests_sent(opened[1]) == verdict.total == 128
    fixture_out = tmp_path / "fixture.evidence"
    code, stdout, _ = run(verify_argv(inputs, "fixed", fixture_lock, fixture_out, "--json"))
    assert code == 0
    assert set(document) == set(one_json(stdout))

    code, stdout, _ = run(["replay", str(out), "--expected-lock-sha256", sealed.sha256, "--json"])
    assert code == EXIT_CODES[verdict.status]
    assert one_json(stdout)["status"] == verdict.status
    report = isolated(REPLAY_BLOCKED + ",actseal.experimental", ["replay", str(out), "--json"])
    assert report["blocked_loaded"] == []
    assert report["code"] == EXIT_CODES[verdict.status]
    assert one_json(str(report["stdout"]))["lock_sha256"] == sealed.sha256


def test_jev_lock_refuses_stable_providers_missing_opt_in_and_offline(
    run: Run, inputs: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Against a Jev lock: provider mismatch and missing opt-in fail before any factory call.

    With the real constructor restored, ``--offline`` is the adapter's setup
    error, raised before the (forbidden) key read.
    """
    real_jev_model = jev_module.JevModel
    _mock_jev_transport(inputs, monkeypatch)
    common = _jev_common(inputs)
    jev = list(JEV_SELECT)
    lock = tmp_path / "jev.lock.json"
    _jev_lock(run, inputs, lock)
    monkeypatch.setattr(cli_module, "open_model", _forbidden)
    for provider in (
        ["--provider", "fixture", "--responses", str(inputs["fixed_responses.jsonl"])],
        ["--provider", "laya"],
    ):
        code, stdout, _ = run(
            [
                "verify",
                "--lock",
                str(lock),
                *common,
                *provider,
                "--out",
                str(tmp_path / "no"),
                "--json",
            ]
        )
        assert code == 3
        assert one_json(stdout)["error"] == (
            "IntegrityError: model_identity.provider: requested provider does not match the lock"
        )
    # ... and jev without the opt-in is still a usage error against its own lock.
    code, stdout, _ = run(
        [
            "verify",
            "--lock",
            str(lock),
            *common,
            "--provider",
            "jev",
            "--out",
            str(tmp_path / "no"),
            "--json",
        ]
    )
    assert code == 3
    assert one_json(stdout)["error"] == (
        "usage: --experimental-provider is required with --provider jev"
    )
    assert not (tmp_path / "no").exists()
    # With the real constructor restored, --offline on the Jev lock is a setup error before the key.
    monkeypatch.setattr(cli_module, "open_model", runner_module.open_model)
    monkeypatch.setattr(jev_module, "JevModel", real_jev_model)
    code, stdout, _ = run(
        [
            "verify",
            "--lock",
            str(lock),
            *common,
            *jev,
            "--offline",
            "--out",
            str(tmp_path / "no"),
            "--json",
        ]
    )
    assert code == 3
    error = one_json(stdout)["error"]
    assert isinstance(error, str)
    assert error.startswith("ProviderSetupError: offline:")
    assert not (tmp_path / "no").exists()
