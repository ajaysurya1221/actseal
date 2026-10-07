"""docs/cli.md agrees with the installed command line: usage, options, exits, receipts."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from actseal.cli import EXIT_CODES, main
from docs.conftest import DOCS, fences, table_rows

CLI_DOC = DOCS / "cli.md"
PACKAGED_INPUTS = Path(__file__).resolve().parents[2] / "src" / "actseal" / "demo_data"
COMMANDS = ("lock", "verify", "replay", "demo")
VERDICT_FIELDS = {
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


def _help(argv: list[str], capsys: pytest.CaptureFixture[str]) -> str:
    assert main(argv) == 0
    out, err = capsys.readouterr()
    assert err == ""
    return out


def _usage_tokens(text: str) -> list[str]:
    """Whitespace-insensitive token list of the ``usage:`` paragraph."""
    usage = text.split("\n\n", 1)[0]
    return usage.replace("usage: ", "").split()


def _documented_usage() -> dict[str, list[str]]:
    signatures = fences(CLI_DOC, "text")[0]
    documented: dict[str, list[str]] = {}
    for line in signatures.splitlines():
        if line.startswith("actseal "):
            command = line.split()[1]
            key = command if command in COMMANDS else "actseal"
            documented[key] = line.split()
        else:
            documented[list(documented)[-1]].extend(line.split())
    return documented


def test_documented_usage_lines_match_help_output(capsys: pytest.CaptureFixture[str]) -> None:
    documented = _documented_usage()
    assert set(documented) == {"actseal", *COMMANDS}
    assert documented["actseal"] == _usage_tokens(_help(["--help"], capsys))
    for command in COMMANDS:
        assert documented[command] == _usage_tokens(_help([command, "--help"], capsys)), command


def test_option_table_matches_help_and_rejects_abbreviations(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rows = table_rows(CLI_DOC.read_text(encoding="utf-8"), "Command")
    documented = {
        row[0].strip("`"): set(re.findall(r"--[a-z][a-z0-9-]*", row[1] + row[2])) for row in rows
    }
    for command in COMMANDS:
        help_text = _help([command, "--help"], capsys)
        actual = set(re.findall(r"(?<![\w-])(--[a-z][a-z0-9-]*)", help_text))
        assert documented[command] == actual - {"--help"}, command
    assert documented["root"] == {"--version", "--help"}
    for option in documented["demo"]:
        assert len(option) > 3
        code = main(["demo", option[:-1], "x", "--json"])
        out, _ = capsys.readouterr()
        assert code == 3
        assert str(json.loads(out)["error"]).startswith("usage:"), option
    assert main(["demo", "--version"]) == 3


def test_exit_code_table_matches_the_frozen_mapping() -> None:
    rows = table_rows(CLI_DOC.read_text(encoding="utf-8"), "Exit")
    documented = {row[1].strip("`"): int(row[0]) for row in rows}
    assert documented == dict(EXIT_CODES)


def _documented_fields(receipt: str) -> set[str]:
    rows = table_rows(CLI_DOC.read_text(encoding="utf-8"), "Receipt")
    cells = {row[0].strip("`"): row[1] for row in rows}
    description = cells[receipt].split("; each run holds")[0]  # top-level fields only
    description = re.sub(r"\{[^}]*\}", "", description)  # nested object fields
    description = re.sub(r"\([^)]*\)", "", description)  # parenthetical notes
    fields = set(re.findall(r"`([a-z0-9_]+)`", description))
    if "the verdict fields" in description:
        fields |= VERDICT_FIELDS
    return fields


def _receipt(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, dict[str, object]]:
    code = main([*argv, "--json"])
    out, err = capsys.readouterr()
    assert err == ""
    document = json.loads(out)
    assert isinstance(document, dict)
    assert document["schema_version"] == 1
    assert document["exit_code"] == code
    assert document["ok"] == (code == 0)
    return code, document


def test_receipt_field_table_matches_real_receipts(
    task_tmpdir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    lock = task_tmpdir / "lock.json"
    inputs = [
        "--calibration",
        str(PACKAGED_INPUTS / "fixed_calibration.jsonl"),
        "--verification",
        str(PACKAGED_INPUTS / "fixed_verification.jsonl"),
        "--provider",
        "fixture",
        "--responses",
        str(PACKAGED_INPUTS / "fixed_responses.jsonl"),
    ]
    code, locked = _receipt(
        ["lock", "--contract", str(PACKAGED_INPUTS / "fixed.toml"), *inputs, "--out", str(lock)],
        capsys,
    )
    assert code == 0
    assert set(locked) == _documented_fields("lock")
    identity = locked["model_identity"]
    assert isinstance(identity, dict)
    assert set(identity) == {
        "provider",
        "model",
        "revision",
        "adapter_version",
        "normalizer_version",
    }

    evidence = task_tmpdir / "evidence"
    code, verified = _receipt(
        ["verify", "--lock", str(lock), *inputs, "--out", str(evidence)], capsys
    )
    assert code == 0
    assert set(verified) == _documented_fields("verify")

    code, replayed = _receipt(["replay", str(evidence)], capsys)
    assert code == 0
    assert set(replayed) == _documented_fields("replay")
    assert replayed["notes"] == []

    code, failed = _receipt(["replay", str(task_tmpdir / "missing")], capsys)
    assert code == 3
    assert set(failed) == _documented_fields("replay")
    assert failed["status"] == "ERROR"

    code, usage = _receipt(["replay"], capsys)
    assert code == 3
    assert set(usage) == _documented_fields("any error")
    assert usage["command"] == "replay"

    code, unparsed = _receipt(["bogus"], capsys)
    assert code == 3
    assert unparsed["command"] == "actseal"

    code, demo = _receipt(["demo", "--out", str(task_tmpdir / "demo")], capsys)
    assert code == 0
    assert set(demo) == _documented_fields("demo")
    runs = demo["runs"]
    assert isinstance(runs, dict)
    assert set(runs) == {"bad", "fixed"}
    run_fields = VERDICT_FIELDS | {
        "failures",
        "warnings",
        "faults",
        "expected_status",
        "as_expected",
        "lock",
        "evidence",
        "replay",
        "replay_matches",
    }
    for run in runs.values():
        assert set(run) == run_fields
        assert set(run["replay"]) == VERDICT_FIELDS


def test_bad_demo_replay_exits_one_as_documented(
    demo_workspace: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A faithful replay of BLOCK evidence exits 1, not 0 and not 3."""
    code = main(["replay", str(demo_workspace / "actseal-demo" / "bad" / "evidence"), "--json"])
    out, _ = capsys.readouterr()
    document = json.loads(out)
    assert code == 1
    assert document["status"] == "BLOCK"
    assert "integrity" not in " ".join(document["reasons"])


def _usage_error(argv: list[str], capsys: pytest.CaptureFixture[str]) -> str:
    code = main([*argv, "--json"])
    out, err = capsys.readouterr()
    assert code == 3
    assert err == ""
    document = json.loads(out)
    assert document["status"] == "ERROR"
    error = document["error"]
    assert isinstance(error, str)
    assert error.startswith("usage:")
    return error


def test_documented_experimental_flag_restrictions_match_the_cli(
    task_tmpdir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The PROVISIONAL opt-in is documented exactly as enforced, command by command."""
    text = CLI_DOC.read_text(encoding="utf-8")
    rows = {row[0].strip("`"): row for row in table_rows(text, "Command")}
    for command in ("lock", "verify"):
        assert "{fixture,laya,jev}" in rows[command][1], command
        assert "--experimental-provider" in rows[command][2], command
        assert "PROVISIONAL" in rows[command][2], command
    for command in ("replay", "demo", "root"):
        assert "--experimental-provider" not in " ".join(rows[command]), command
    prose = re.sub(r"\s+", " ", text)
    for phrase in (
        "`--provider jev --experimental-provider`",
        "stable** provider choices are `fixture` and `laya`",
        "Without the flag the command is a usage error",
        "`replay` and `demo` do not accept `--experimental-provider`",
        "`jev` with `--offline` is a setup error",
        "may change or be removed in any release",
    ):
        assert phrase in prose, phrase

    inputs = [
        "--calibration",
        str(PACKAGED_INPUTS / "fixed_calibration.jsonl"),
        "--verification",
        str(PACKAGED_INPUTS / "fixed_verification.jsonl"),
    ]
    lock = ["lock", "--contract", str(PACKAGED_INPUTS / "fixed.toml"), *inputs]
    verify = ["verify", "--lock", str(task_tmpdir / "absent.json"), *inputs]
    out = ["--out", str(task_tmpdir / "out")]
    responses = ["--responses", str(PACKAGED_INPUTS / "fixed_responses.jsonl")]
    for head in (lock, verify):
        assert _usage_error([*head, "--provider", "jev", *out], capsys) == (
            "usage: --experimental-provider is required with --provider jev"
        )
        assert (
            _usage_error(
                [*head, "--provider", "jev", "--experimental-provider", *responses, *out], capsys
            )
            == "usage: --responses is not accepted with --provider jev"
        )
        assert (
            _usage_error(
                [*head, "--provider", "fixture", "--experimental-provider", *responses, *out],
                capsys,
            )
            == "usage: --experimental-provider is not accepted with --provider fixture"
        )
        assert (
            _usage_error([*head, "--provider", "laya", "--experimental-provider", *out], capsys)
            == "usage: --experimental-provider is not accepted with --provider laya"
        )
    for argv in (
        ["replay", str(task_tmpdir / "absent"), "--experimental-provider"],
        ["demo", "--out", str(task_tmpdir / "demo"), "--experimental-provider"],
    ):
        assert _usage_error(argv, capsys) == (
            "usage: unrecognized arguments: 1 token(s) not accepted; see --help"
        )
    assert not (task_tmpdir / "out").exists()
    assert not (task_tmpdir / "demo").exists()
