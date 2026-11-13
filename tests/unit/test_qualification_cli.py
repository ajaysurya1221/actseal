"""Observable command behavior for the separate calibration workflow."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from test_cli import DEMO_BLOCKED, REPLAY_BLOCKED, isolated

from actseal.cli import main

PACKAGED = Path(__file__).resolve().parents[2] / "src" / "actseal" / "demo_data"
SCHEMAS = Path(__file__).resolve().parents[2] / "docs" / "schemas"


def receipt(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, dict[str, object]]:
    code = main([*argv, "--json"])
    out, err = capsys.readouterr()
    assert err == ""
    assert out.count("\n") == 1
    document = json.loads(out)
    assert isinstance(document, dict)
    assert document["schema_version"] == 1
    assert document["exit_code"] == code
    schema = json.loads((SCHEMAS / "qualification-cli-receipt.schema.json").read_text())
    Draft202012Validator(schema).validate(document)
    return code, document


def qualification_argv(command: str, destination: Path) -> list[str]:
    return [
        command,
        "--contract",
        str(PACKAGED / "qualify.toml"),
        "--calibration",
        str(PACKAGED / "qualify_calibration.jsonl"),
        "--verification",
        str(PACKAGED / "qualify_verification.jsonl"),
        "--provider",
        "fixture",
        "--responses",
        str(PACKAGED / "qualify_responses.jsonl"),
        "--out",
        str(destination),
    ]


def test_plan_has_no_provider_or_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    code, document = receipt(
        [
            "plan",
            "--max-risk",
            "1",
            "--min-coverage",
            "0",
            "--alpha",
            ".05",
            "--expected-risk",
            "0",
            "--expected-coverage",
            "1",
        ],
        capsys,
    )
    assert code == 0
    assert document["verification_cases"] == 1
    assert document["reason"] == "planning.reachable"
    assert list(tmp_path.iterdir()) == []


def test_plan_unreachable_exits_inconclusive(capsys: pytest.CaptureFixture[str]) -> None:
    code, document = receipt(
        [
            "plan",
            "--max-risk",
            "0",
            "--min-coverage",
            "1",
            "--alpha",
            ".05",
            "--expected-risk",
            "1",
            "--expected-coverage",
            "0",
        ],
        capsys,
    )
    assert code == 2
    assert document["verification_cases"] is None
    assert document["reason"] == "planning.not_reachable"


def test_plan_cli_imports_no_provider() -> None:
    report = isolated(
        REPLAY_BLOCKED + ",actseal.experimental",
        [
            "plan",
            "--max-risk",
            "1",
            "--min-coverage",
            "0",
            "--alpha",
            ".05",
            "--expected-risk",
            "0",
            "--expected-coverage",
            "1",
            "--json",
        ],
    )
    assert report["blocked_loaded"] == []
    assert report["code"] == 0


@pytest.mark.parametrize("command", ["plan", "calibrate", "qualify", "replay-selection"])
def test_new_help_contains_no_unearned_claims(
    command: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([command, "--help"]) == 0
    out, err = capsys.readouterr()
    assert err == ""
    for prohibited in ("guaranteed", "certified", "safe"):
        assert prohibited not in out.lower()


def test_calibrate_does_not_collect_verification(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    destination = tmp_path / "calibrated"
    code, document = receipt(qualification_argv("calibrate", destination), capsys)
    assert code == 0
    assert document["status"] == "SELECTED"
    selection = document["selection"]
    assert isinstance(selection, dict)
    assert selection["threshold"] == 0.95
    assert (destination / "contract.toml").is_file()
    assert not (destination / "lock.json").exists()
    assert not (destination / "evidence").exists()
    code, replayed = receipt(["replay-selection", str(destination / "calibration")], capsys)
    assert code == 0
    assert replayed["status"] == "SELECTED"
    assert replayed["selection"] == selection


def test_qualify_produces_real_pass_and_linked_receipt(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    destination = tmp_path / "qualified"
    code, document = receipt(qualification_argv("qualify", destination), capsys)
    assert code == 0
    assert document["status"] == "PASS"
    verdict = document["verdict"]
    assert isinstance(verdict, dict)
    assert (verdict["total"], verdict["accepted"], verdict["errors"]) == (100, 100, 0)
    assert (destination / "qualification.json").is_file()
    assert (destination / "evidence" / "records.jsonl").is_file()


def test_no_threshold_skips_verification(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    destination = tmp_path / "none"
    code, document = receipt([*qualification_argv("qualify", destination), "--grid", "1"], capsys)
    assert code == 2
    selection = document["selection"]
    assert isinstance(selection, dict)
    assert selection["reason"] == "calibration.no_threshold"
    assert document["verdict"] is None
    assert not (destination / "contract.toml").exists()
    assert not (destination / "evidence").exists()
    assert not (destination / "lock.json").exists()


def test_demo_qualify_is_synthetic_and_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, document = receipt(["demo", "--qualify", "--out", str(tmp_path / "demo")], capsys)
    assert code == 0
    assert document["command"] == "demo"
    assert document["mode"] == "qualify"
    assert document["demo_only"] is True
    assert document["evidence_scope"] == "demo"
    assert document["status"] == "PASS"
    assert "synthetic" in str(document["note"])


def test_demo_qualify_chooses_persistent_temporary_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    code, document = receipt(["demo", "--qualify"], capsys)
    assert code == 0
    destination = Path(str(document["out"]))
    assert destination.is_relative_to(tmp_path)
    assert (destination / "qualification.json").is_file()


def test_replay_selection_cli_imports_no_adapters_or_transport(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    destination = tmp_path / "selected"
    code, _ = receipt(qualification_argv("calibrate", destination), capsys)
    assert code == 0
    report = isolated(
        REPLAY_BLOCKED + ",actseal.experimental",
        ["replay-selection", str(destination / "calibration"), "--json"],
    )
    assert report["blocked_loaded"] == []
    assert report["code"] == 0


def test_qualification_demo_imports_no_live_provider_or_transport(tmp_path: Path) -> None:
    report = isolated(
        DEMO_BLOCKED + ",actseal.experimental",
        ["demo", "--qualify", "--out", str(tmp_path / "demo"), "--json"],
    )
    assert report["blocked_loaded"] == []
    assert report["code"] == 0


@pytest.mark.parametrize("changed", ["record", "grid", "verification_size", "manifest"])
def test_replay_selection_tampering_exits_error(
    changed: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    destination = tmp_path / "selected"
    code, _ = receipt(qualification_argv("calibrate", destination), capsys)
    assert code == 0
    directory = destination / "calibration"
    if changed == "record":
        path = directory / "records.jsonl"
        records = path.read_text().splitlines()
        record = json.loads(records[0])
        record["case_id"] = "tampered-case"
        path.write_text("\n".join([json.dumps(record), *records[1:]]) + "\n")
    elif changed == "manifest":
        path = directory / "manifest.json"
        document = json.loads(path.read_text())
        document["sha256"] = "0" * 64
        path.write_text(json.dumps(document))
    else:
        path = directory / "selection_plan.json"
        document = json.loads(path.read_text())
        if changed == "grid":
            document["grid"][0] = 0.51
        else:
            document["n_verify"] = 99
        path.write_text(json.dumps(document))
    code, failed = receipt(["replay-selection", str(directory)], capsys)
    assert code == 3
    assert failed["status"] == "ERROR"


@pytest.mark.parametrize("command", ["calibrate", "qualify"])
def test_experimental_opt_in_checked_before_inputs(
    command: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = qualification_argv(command, tmp_path / "out")
    argv[argv.index("fixture")] = "decision-api"
    code, document = receipt(argv, capsys)
    assert code == 3
    assert "--experimental-provider is required" in str(document["error"])
    assert not (tmp_path / "out").exists()
