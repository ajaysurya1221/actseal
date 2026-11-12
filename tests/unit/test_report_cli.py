"""Reports are published only after offline replay and qualification linkage checks."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from test_cli import REPLAY_BLOCKED, isolated
from test_evidence import laya_identity, make_bundle, make_lock, record_for, records_for, rewrite
from test_qualification import reseal
from test_qualification_cli import qualification_argv

from actseal.cli import main
from actseal.evidence import write_bundle
from actseal.serialization import canonical_json, sha256_bytes


def _qualify(path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(qualification_argv("qualify", path)) == 0
    capsys.readouterr()


def test_report_replays_qualification_and_is_relocation_deterministic(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "qualification"
    _qualify(source, capsys)
    moved = tmp_path / "different-name"
    shutil.copytree(source, moved)
    for directory, name in ((source, "first"), (moved, "second")):
        assert main(["report", str(directory), "--out", str(tmp_path / name), "--json"]) == 0
        receipt = json.loads(capsys.readouterr().out)
        assert receipt["status"] == "PASS"
        assert receipt["command"] == "report"
    first, second = tmp_path / "first", tmp_path / "second"
    assert {p.name for p in first.iterdir()} == {"report.html", "report.md", "badge.json"}
    for path in first.iterdir():
        assert path.read_bytes() == (second / path.name).read_bytes()
        assert str(tmp_path).encode() not in path.read_bytes()
    text = (first / "report.md").read_text()
    assert "0.95" in text
    assert "descriptive, not verified" in text
    assert "replay-selection calibration" in text


@pytest.mark.parametrize(("run", "status"), [("bad", "BLOCK"), ("fixed", "PASS")])
def test_report_renders_plain_bundle_without_changing_verdict(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], run: str, status: str
) -> None:
    source = tmp_path / "demo"
    assert main(["demo", "--out", str(source)]) == 0
    capsys.readouterr()
    out = tmp_path / "report"
    assert main(["report", str(source / run / "evidence"), "--out", str(out)]) == 0
    message = json.loads((out / "badge.json").read_text())["message"]
    if status == "PASS":
        assert message == "PASS · ≥96.6% alone @ ≤5.0% risk"
    else:
        assert message == status
    assert "replay-selection" not in (out / "report.md").read_text()


@pytest.mark.parametrize(
    "relative",
    ["evidence/records.jsonl", "calibration/records.jsonl", "calibration/manifest.json"],
)
def test_report_refuses_tampered_evidence_without_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], relative: str
) -> None:
    source = tmp_path / "qualification"
    _qualify(source, capsys)
    with (source / relative).open("ab") as stream:
        stream.write(b" ")
    out = tmp_path / "report"
    assert main(["report", str(source), "--out", str(out), "--json"]) == 3
    assert json.loads(capsys.readouterr().out)["status"] == "ERROR"
    assert not out.exists()


@pytest.mark.parametrize("field", ["lock_sha256", "calibration_manifest_sha256", "verdict"])
def test_report_refuses_unlinked_qualification_receipt(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], field: str
) -> None:
    source = tmp_path / "qualification"
    _qualify(source, capsys)
    path = source / "qualification.json"
    receipt = json.loads(path.read_bytes())
    if field == "verdict":
        receipt[field]["accepted"] -= 1
    else:
        receipt[field] = "f" * 64
    path.write_bytes(canonical_json(receipt) + b"\n")
    out = tmp_path / "report"
    assert main(["report", str(source), "--out", str(out)]) == 3
    assert not out.exists()


def test_report_requires_complete_qualification_and_preserves_existing_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "qualification"
    _qualify(source, capsys)
    out = tmp_path / "report"
    out.mkdir()
    sentinel = out / "sentinel"
    sentinel.write_bytes(b"keep")
    assert main(["report", str(source), "--out", str(out)]) == 3
    assert sentinel.read_bytes() == b"keep"
    (source / "qualification.json").unlink()
    assert main(["report", str(source), "--out", str(tmp_path / "missing")]) == 3
    assert not (tmp_path / "missing").exists()


def test_report_imports_no_live_provider(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "qualification"
    _qualify(source, capsys)
    result = isolated(
        REPLAY_BLOCKED + ",actseal.experimental",
        ["report", str(source), "--out", str(tmp_path / "report"), "--json"],
    )
    assert result["blocked_loaded"] == []
    assert result["code"] == 0


def test_report_checks_plan_to_bundle_link_after_successful_selection_replay(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "qualification"
    _qualify(source, capsys)
    sidecar = source / "calibration"
    plan = json.loads((sidecar / "selection_plan.json").read_bytes())
    plan["verification_sha256"] = "f" * 64
    del plan["sha256"]
    plan["sha256"] = sha256_bytes(canonical_json(plan))
    reseal(sidecar, "selection_plan.json", plan)
    receipt_path = source / "qualification.json"
    receipt = json.loads(receipt_path.read_bytes())
    receipt["calibration_manifest_sha256"] = sha256_bytes((sidecar / "manifest.json").read_bytes())
    receipt_path.write_bytes(canonical_json(receipt) + b"\n")
    assert main(["replay-selection", str(sidecar)]) == 0
    capsys.readouterr()
    out = tmp_path / "report"
    assert main(["report", str(source), "--out", str(out)]) == 3
    assert "selection plan does not match" in capsys.readouterr().err
    assert not out.exists()


def test_report_cannot_write_inside_evidence(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "qualification"
    _qualify(source, capsys)
    for directory in (source / "evidence", source / "calibration"):
        out = directory / "report"
        assert main(["report", str(source), "--out", str(out)]) == 3
        assert not out.exists()


def test_report_renders_replayed_diagnostic_error_but_refuses_forgery(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    lock = make_lock(identity=laya_identity())
    records = list(records_for(lock))
    records[3] = record_for(lock, lock.verification_cases[3], failure_code="timeout")
    bundle = make_bundle(lock, records)
    source = write_bundle(bundle, tmp_path / "evidence")
    out = tmp_path / "report"
    assert main(["report", str(source), "--out", str(out)]) == 0
    assert json.loads((out / "badge.json").read_bytes())["message"] == "ERROR"
    capsys.readouterr()
    data = json.loads((source / "verdict.json").read_bytes())
    data["reasons"] = ["integrity.records"]
    rewrite(source, {"verdict.json": canonical_json(data) + b"\n"})
    assert main(["report", str(source), "--out", str(tmp_path / "forged")]) == 3
    assert not (tmp_path / "forged").exists()
