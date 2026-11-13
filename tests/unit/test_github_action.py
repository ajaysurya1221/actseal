"""Composite-action contracts without a YAML dependency or hosted network calls."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
ACTION = ROOT / "action.yml"


def scripts() -> dict[str, str]:
    """Read the deliberately restricted block-scalar subset used by this action."""
    result: dict[str, str] = {}
    name = ""
    lines = ACTION.read_text().splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("    - name: "):
            name = line.removeprefix("    - name: ")
        if line == "      run: |":
            body = []
            index += 1
            while index < len(lines) and (lines[index].startswith("        ") or not lines[index]):
                body.append(lines[index][8:])
                index += 1
            assert name
            assert body
            result[name] = "\n".join(body) + "\n"
            continue
        index += 1
    return result


def python_script(name: str) -> str:
    script = scripts()[name]
    assert script.startswith("python - <<'PY'\n")
    assert script.endswith("\nPY\n")
    return script.removeprefix("python - <<'PY'\n").removesuffix("PY\n")


def run_script(name: str) -> None:
    # Execute this repository's reviewed action block; subprocess is controlled below.
    exec(compile(python_script(name), str(ACTION), "exec"), {"__name__": "__main__"})  # noqa: S102


@pytest.fixture
def action_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    values = {
        "RUNNER_TEMP": str(tmp_path),
        "GITHUB_OUTPUT": str(tmp_path / "outputs"),
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary"),
        "ACTSEAL_MODE": "replay",
        "ACTSEAL_ARGS": "'bundle with spaces'",
        "ACTSEAL_REPORT": "true",
        "ACTSEAL_UPLOAD": "true",
        "ACTSEAL_SOURCE": "pypi",
        "ACTSEAL_VERSION": "2.0.0",
        "GITHUB_ACTION_PATH": str(ROOT),
    }
    monkeypatch.chdir(tmp_path)
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    return values


def outputs(path: str) -> dict[str, str]:
    return dict(line.split("=", 1) for line in Path(path).read_text().splitlines())


def test_action_pins_and_inputs_do_not_enter_script_text() -> None:
    body = ACTION.read_text()
    assert "using: composite" in body
    assert set(scripts()) == {"Install Actseal", "Run Actseal", "Render report", "Return verdict"}
    for script in scripts().values():
        assert "${{" not in script
    for line in body.splitlines():
        if "uses:" in line:
            value = line.split("uses:", 1)[1].split("#", 1)[0].strip()
            assert re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}", value)
    assert "actions/attest@" not in body
    assert "if: ${{ always() }}" in body
    assert "if-no-files-found: error" in body


@pytest.mark.parametrize(
    ("code", "status"), [(0, "PASS"), (1, "BLOCK"), (2, "INCONCLUSIVE"), (3, "ERROR")]
)
def test_command_receipt_preserves_every_exit_and_copies_only_evidence(
    action_env: dict[str, str], monkeypatch: pytest.MonkeyPatch, code: int, status: str
) -> None:
    bundle = Path("bundle with spaces")
    bundle.mkdir()
    (bundle / "manifest.json").write_text("{}")
    (bundle / "private.txt").write_text("must not upload")
    injected = "$(touch COMMAND_INJECTION);`touch COMMAND_INJECTION`"
    monkeypatch.setenv("ACTSEAL_ARGS", f"'{bundle}' --expected-lock-sha256 '{injected}'")
    called: list[list[str]] = []

    def command(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        called.append(argv)
        assert kwargs.get("shell", False) is False
        return subprocess.CompletedProcess(
            argv,
            code,
            json.dumps(
                {
                    "schema_version": 1,
                    "command": "replay",
                    "exit_code": code,
                    "status": status,
                    "bundle": str(bundle),
                }
            ),
            "",
        )

    monkeypatch.setattr(subprocess, "run", command)
    run_script("Run Actseal")
    result = outputs(action_env["GITHUB_OUTPUT"])
    assert result["exit-code"] == str(code)
    assert result["verdict"] == status
    assert result["evidence-path"] == str(bundle.resolve())
    assert called[0][1:] == [
        "-I",
        "-m",
        "actseal",
        "replay",
        str(bundle),
        "--expected-lock-sha256",
        injected,
        "--json",
    ]
    assert not Path("COMMAND_INJECTION").exists()
    artifact = Path(result["artifact-path"])
    assert (artifact / "evidence" / "manifest.json").read_text() == "{}"
    assert not (artifact / "evidence" / "private.txt").exists()
    assert json.loads((artifact / "receipt.json").read_text())["status"] == status


@pytest.mark.parametrize("raw_args", ["'unclosed", "bundle\nwith-newline"])
def test_invalid_arguments_fail_closed_before_execution(
    action_env: dict[str, str], monkeypatch: pytest.MonkeyPatch, raw_args: str
) -> None:
    monkeypatch.setenv("ACTSEAL_ARGS", raw_args)

    def unexpected(*_args: object, **_kwargs: object) -> None:
        pytest.fail("invalid action arguments reached a command")

    monkeypatch.setattr(subprocess, "run", unexpected)
    run_script("Run Actseal")
    assert outputs(action_env["GITHUB_OUTPUT"])["exit-code"] == "3"


def test_qualify_uses_receipt_root_and_keeps_partial_calibration(
    action_env: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    root = Path("qualification")
    (root / "calibration").mkdir(parents=True)
    (root / "calibration" / "selection.json").write_text("{}")
    monkeypatch.setenv("ACTSEAL_MODE", "qualify")
    monkeypatch.setenv("ACTSEAL_ARGS", "--out qualification")

    def command(argv: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            argv,
            2,
            json.dumps(
                {
                    "schema_version": 1,
                    "command": "qualify",
                    "exit_code": 2,
                    "status": "INCONCLUSIVE",
                    "out": "qualification",
                    "verdict": None,
                }
            ),
            "",
        )

    monkeypatch.setattr(subprocess, "run", command)
    run_script("Run Actseal")
    result = outputs(action_env["GITHUB_OUTPUT"])
    assert result["exit-code"] == "2"
    assert result["evidence-path"] == str(root.resolve())
    assert (Path(result["artifact-path"]) / "evidence/calibration/selection.json").is_file()


@pytest.mark.parametrize("valid", [True, False])
def test_report_summary_is_only_appended_after_render_succeeds(
    action_env: dict[str, str], monkeypatch: pytest.MonkeyPatch, valid: bool
) -> None:
    artifact = Path(action_env["RUNNER_TEMP"]) / "artifact"
    artifact.mkdir()
    monkeypatch.setenv("ACTSEAL_ARTIFACT_PATH", str(artifact))
    monkeypatch.setenv("ACTSEAL_EVIDENCE_PATH", str(Path("bundle").resolve()))

    def command(argv: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        target = Path(argv[argv.index("--out") + 1])
        if valid:
            target.mkdir()
            (target / "report.md").write_text("# BLOCK\n")
        return subprocess.CompletedProcess(argv, 0 if valid else 3, "", "")

    monkeypatch.setattr(subprocess, "run", command)
    run_script("Render report")
    summary = Path(action_env["GITHUB_STEP_SUMMARY"]).read_text()
    assert ("# BLOCK" in summary) is valid
    if not valid:
        assert "Report unavailable" in summary
    assert outputs(action_env["GITHUB_OUTPUT"])["report-exit-code"] == ("0" if valid else "3")


@pytest.mark.usefixtures("action_env")
def test_install_uses_exact_pypi_pin_without_a_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[list[str]] = []

    def command(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        seen.append(argv)
        assert kwargs.get("shell", False) is False
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(subprocess, "run", command)
    run_script("Install Actseal")
    assert seen[0][-1] == "actseal==2.0.0"
    assert "https://pypi.org/simple" in seen[0]


def test_selftest_has_both_real_modes_and_explicit_checkout_install() -> None:
    text = (ROOT / ".github/workflows/action-selftest.yml").read_text()
    assert "source: checkout" in text
    assert "mode: replay" in text
    assert "mode: qualify" in text
    assert "examples/action_gate/recorded/a5fe090202f7/evidence" in text
    assert "qualify_calibration.jsonl" in text
    assert "uses: ./" in text


def test_action_documentation_has_no_unearned_claims() -> None:
    text = (ROOT / "docs/github-action.md").read_text().lower()
    assert not re.search(r"\b(?:guaranteed|certified|safe|best)\b", text)
    assert "gh attestation verify" in text
    assert "actseal itself verifies no signature" in text


@pytest.mark.parametrize("code", ["0", "1", "2", "3", "", "1;touch EXECUTED"])
def test_final_shell_step_preserves_codes_without_expansion(tmp_path: Path, code: str) -> None:
    result = subprocess.run(  # noqa: S603 - fixed repository script; hostile data is only in env
        ["/bin/bash", "-c", scripts()["Return verdict"]],
        cwd=tmp_path,
        env={**os.environ, "ACTSEAL_EXIT_CODE": code},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == (int(code) if code in {"0", "1", "2", "3"} else 3)
    assert not (tmp_path / "EXECUTED").exists()


@pytest.mark.usefixtures("action_env")
@pytest.mark.parametrize("version", ["latest", "1.0.1;touch EXECUTED", "1.0.1 --index-url other"])
def test_install_rejects_nonexact_versions_before_execution(
    monkeypatch: pytest.MonkeyPatch, version: str
) -> None:
    monkeypatch.setenv("ACTSEAL_VERSION", version)

    def unexpected(*_args: object, **_kwargs: object) -> None:
        pytest.fail("invalid release reached installer")

    monkeypatch.setattr(subprocess, "run", unexpected)
    with pytest.raises(SystemExit, match="exact release"):
        run_script("Install Actseal")


@pytest.mark.parametrize("stdout", ["not json", '{"status":"PASS","exit_code":0}'])
def test_malformed_receipt_does_not_create_a_pass_output(
    action_env: dict[str, str], monkeypatch: pytest.MonkeyPatch, stdout: str
) -> None:
    def command(argv: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 0, stdout, "")

    monkeypatch.setattr(subprocess, "run", command)
    run_script("Run Actseal")
    result = outputs(action_env["GITHUB_OUTPUT"])
    assert result["exit-code"] == "3"
    assert result["verdict"] == "ERROR"


def test_embedded_run_script_executes_real_offline_qualification(
    action_env: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    import shlex  # noqa: PLC0415 - local command-argument assembly

    inputs = ROOT / "src/actseal/demo_data"
    args = [
        "--contract",
        str(inputs / "qualify.toml"),
        "--calibration",
        str(inputs / "qualify_calibration.jsonl"),
        "--verification",
        str(inputs / "qualify_verification.jsonl"),
        "--provider",
        "fixture",
        "--responses",
        str(inputs / "qualify_responses.jsonl"),
        "--offline",
        "--out",
        "qualification",
    ]
    monkeypatch.setenv("ACTSEAL_MODE", "qualify")
    monkeypatch.setenv("ACTSEAL_ARGS", shlex.join(args))
    run_script("Run Actseal")
    result = outputs(action_env["GITHUB_OUTPUT"])
    assert result["exit-code"] == "0"
    assert result["verdict"] == "PASS"
    artifact = Path(result["artifact-path"]) / "evidence"
    assert (artifact / "qualification.json").is_file()
    assert (artifact / "calibration/selection.json").is_file()
    assert (artifact / "evidence/verdict.json").is_file()
    monkeypatch.setenv("ACTSEAL_EVIDENCE_PATH", result["evidence-path"])
    monkeypatch.setenv("ACTSEAL_ARTIFACT_PATH", result["artifact-path"])
    run_script("Render report")
    assert outputs(action_env["GITHUB_OUTPUT"])["report-exit-code"] == "0"
    report = Path(result["artifact-path"]) / "report"
    assert {path.name for path in report.iterdir()} == {"report.html", "report.md", "badge.json"}
    summary = Path(action_env["GITHUB_STEP_SUMMARY"]).read_text()
    assert "PASS" in summary
    assert "Report unavailable" not in summary


def test_staging_failure_retains_original_command_exit(
    action_env: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bundle = Path("bundle with spaces")
    bundle.mkdir()
    (bundle / "manifest.json").write_text("{}")

    def command(argv: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            argv,
            2,
            json.dumps(
                {
                    "schema_version": 1,
                    "command": "replay",
                    "exit_code": 2,
                    "status": "INCONCLUSIVE",
                    "bundle": str(bundle),
                }
            ),
            "",
        )

    def copying_error(*_args: object, **_kwargs: object) -> None:
        raise OSError("injected artifact copy failure")

    monkeypatch.setattr(subprocess, "run", command)
    monkeypatch.setattr(shutil, "copyfile", copying_error)
    run_script("Run Actseal")
    result = outputs(action_env["GITHUB_OUTPUT"])
    assert result["exit-code"] == "2"
    assert result["verdict"] == "INCONCLUSIVE"
    assert "::warning::Actseal evidence staging failed" in capsys.readouterr().out


@pytest.mark.parametrize("present", [False, True])
def test_hosted_selftest_checks_the_report_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, present: bool
) -> None:
    text = (ROOT / ".github/workflows/action-selftest.yml").read_text()
    checks = re.findall(r"          python - <<'PY'\n(.*?)          PY", text, re.DOTALL)
    assert len(checks) == 2
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    if present:
        report = tmp_path / "actseal-artifact-fixture/report"
        report.mkdir(parents=True)
        (report / "report.html").write_text("<h1>PASS</h1>")
        (report / "report.md").write_text("# PASS\n")
        (report / "badge.json").write_text('{"message":"PASS"}')
    for check in checks:
        code = "\n".join(line[10:] for line in check.splitlines())
        if present:
            exec(compile(code, "selftest-report-check", "exec"), {})  # noqa: S102
        else:
            with pytest.raises(AssertionError):
                exec(compile(code, "selftest-report-check", "exec"), {})  # noqa: S102
