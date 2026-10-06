"""The run.py interface: --check, --route, --record, usage errors, foreign and damaged runs."""

from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

import actseal.compatibility as compatibility_module
from actseal.replay import replay
from actseal.serialization import implementation_fingerprint
from examples.examples_support import (
    EXAMPLE_DIR,
    RECORDED_DIR,
    REPO_ROOT,
    RUN_SCRIPT,
    corrupt_seal,
    foreign_copy,
    read_json,
    registry_text,
    rehash_bundle,
)

HEX_0 = "0" * 64
HEX_E = "e" * 64
HEX_F = "f" * 64
COMMIT = "0123456789abcdef0123456789abcdef01234567"
ENGINE = "actseal-choice-v1"


def approve(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *fingerprints: str) -> Path:
    """Point ``load_registry`` at a temporary registry approving ``fingerprints`` for the engine.

    The packaged registry file is never edited; the patch is undone by pytest.
    """
    path = tmp_path / "registry.json"
    path.write_text(registry_text(dict.fromkeys(fingerprints, ENGINE)), encoding="utf-8")
    monkeypatch.setattr(compatibility_module, "_REGISTRY_PATH", path)
    return path


def committed_run() -> Path:
    runs = sorted(path for path in RECORDED_DIR.iterdir() if path.is_dir())
    assert runs
    return runs[0]


def test_check_passes_on_the_committed_example(run: ModuleType) -> None:
    out = io.StringIO()
    assert run.main(["--check"], out=out) == 0
    text = out.getvalue()
    assert text.rstrip().endswith("action_gate --check: 0 error(s)")
    assert "[error]" not in text
    assert "[ok] routing: queue journal holds exactly the 3 ACT tickets" in text
    assert "replay equals the recorded" in text


def test_check_runs_as_the_documented_command() -> None:
    result = subprocess.run(  # noqa: S603 - fixed interpreter and repository script
        [sys.executable, str(RUN_SCRIPT), "--check"],
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "0 error(s)" in result.stdout


def test_route_replays_the_recorded_run_and_prints_the_journal(run: ModuleType) -> None:
    out = io.StringIO()
    assert run.main(["--route"], out=out) == 0
    text = out.getvalue()
    assert "replayed PASS" in text
    assert "T-1001: ACT (policy.allowed) -> queued billing" in text
    assert "T-1004: ABSTAIN (policy.low_confidence) -> held_for_review" in text
    assert (
        "queue journal: [('billing', 'T-1001'), ('technical', 'T-1002'), ('sales', 'T-1003')]"
        in text
    )


def test_record_writes_a_new_identified_run_and_never_overwrites(
    run: ModuleType, tmp_path: Path
) -> None:
    destination = tmp_path / "runs" / "fresh"
    out = io.StringIO()
    assert run.main(["--record", str(destination), "--source-commit", COMMIT], out=out) == 0
    producer = run.load_producer(destination)
    assert producer.source_commit == COMMIT
    assert producer.verdict_status == "PASS"
    assert producer.inputs == run.input_hashes()
    assert (
        replay(destination / "evidence", expected_lock_sha256=producer.lock_sha256).status == "PASS"
    )
    assert read_json(destination / "PRODUCER.json")["format"] == run.PRODUCER_FORMAT
    with pytest.raises(FileExistsError):
        run.record(destination, source_commit=COMMIT)
    assert sorted(p.name for p in destination.iterdir()) == [
        "PRODUCER.json",
        "evidence",
        "lock.json",
    ]


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["--check", "--route"],
        ["--chec"],
        ["--record", "x"],
        ["--record", "x", "--source-commit", "abc"],
        ["--check", "--source-commit", COMMIT],
        ["--bogus"],
    ],
)
def test_usage_errors_exit_two(run: ModuleType, argv: list[str]) -> None:
    assert run.main(argv, out=io.StringIO()) == 2
    assert not (REPO_ROOT / "x").exists()


def test_help_exits_zero(run: ModuleType, capsys: pytest.CaptureFixture[str]) -> None:
    assert run.main(["--help"], out=io.StringIO()) == 0
    assert "--record DIRECTORY" in capsys.readouterr().out


def test_foreign_producer_run_is_reported_not_replayed_and_not_rewritten(
    run: ModuleType, tmp_path: Path
) -> None:
    root = tmp_path / "recorded"
    root.mkdir()
    # Named to sort before the committed run so --route visibly skips it first.
    foreign = root / "000000000000"
    seal = foreign_copy(committed_run(), foreign, HEX_0)
    before = {p.name: p.read_bytes() for p in (foreign / "evidence").iterdir()}
    out = io.StringIO()
    assert run.check(out, recorded_root=root) == 1
    text = out.getvalue()
    assert "[info] recorded/000000000000: not replayable under the running implementation" in text
    assert "unapproved pair; archive seal and inventories verified); bytes preserved" in text
    assert "[error] recorded: no exact or registry-approved recorded run replays" in text
    assert {p.name: p.read_bytes() for p in (foreign / "evidence").iterdir()} == before
    assert read_json(foreign / "PRODUCER.json")["lock_sha256"] == seal
    # With a compatible run beside it the foreign run is tolerated and the check passes.
    shutil.copytree(committed_run(), root / committed_run().name)
    out = io.StringIO()
    assert run.check(out, recorded_root=root) == 0
    assert "[info] recorded/000000000000: not replayable" in out.getvalue()
    out = io.StringIO()
    assert run.route(out, recorded_root=root) == 0
    assert "recorded/000000000000: unapproved producer 000000000000; not used" in out.getvalue()
    assert f"recorded/{committed_run().name}: replayed PASS" in out.getvalue()
    assert "(exact)" in out.getvalue()


def test_route_without_a_compatible_run_fails_with_guidance(
    run: ModuleType, tmp_path: Path
) -> None:
    root = tmp_path / "recorded"
    root.mkdir()
    foreign_copy(committed_run(), root / "ffffffffffff", HEX_F)
    out = io.StringIO()
    assert run.route(out, recorded_root=root) == 1
    assert "no exact or registry-approved recorded run matches" in out.getvalue()
    assert "--record DIRECTORY --source-commit SHA" in out.getvalue()


def test_invalid_archived_seal_fails_the_check_beside_a_valid_current_run(
    run: ModuleType, tmp_path: Path
) -> None:
    """A corrupt archive is an error, never relabelled as a harmless compatibility notice."""
    root = tmp_path / "recorded"
    root.mkdir()
    shutil.copytree(committed_run(), root / committed_run().name)
    broken = root / "ffffffffffff"
    foreign_copy(committed_run(), broken, HEX_F)
    corrupt_seal(broken, HEX_E)
    # Every ordinary hash agrees and the producer identity describes the lock;
    # replay would still say exactly ``integrity.lock``, as for an unapproved producer.
    assert replay(broken / "evidence", expected_lock_sha256=HEX_E).reasons == ("integrity.lock",)
    out = io.StringIO()
    assert run.check(out, recorded_root=root) == 1
    text = out.getvalue()
    assert "[error] recorded/ffffffffffff: lock.sha256: archived self-seal does not match" in text
    assert "not replayable" not in text
    assert f"[ok] recorded/{committed_run().name}: replay equals the recorded PASS (exact" in text
    out = io.StringIO()
    assert run.route(out, recorded_root=root) == 0  # the valid current run is used


def test_invalid_archived_seal_with_the_running_fingerprint_fails_too(
    run: ModuleType, tmp_path: Path
) -> None:
    root = tmp_path / "recorded"
    root.mkdir()
    broken = root / committed_run().name
    shutil.copytree(committed_run(), broken)
    corrupt_seal(broken, HEX_E)
    out = io.StringIO()
    assert run.check(out, recorded_root=root) == 1
    assert "archived self-seal does not match" in out.getvalue()


def test_registry_approved_archive_is_checked_and_routed(
    run: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An archive from a foreign producer that the registry pairs with the running source."""
    root = tmp_path / "recorded"
    root.mkdir()
    foreign = root / "ffffffffffff"
    seal = foreign_copy(committed_run(), foreign, HEX_F)
    before = {p.name: p.read_bytes() for p in (foreign / "evidence").iterdir()}
    producer = run.load_producer(foreign)
    assert run.compatibility_status(producer) == "unapproved"
    registry = approve(monkeypatch, tmp_path, HEX_F, implementation_fingerprint())
    assert run.compatibility_status(producer) == "approved"
    out = io.StringIO()
    assert run.check(out, recorded_root=root) == 0
    text = out.getvalue()
    assert (
        "[ok] recorded/ffffffffffff: replay equals the recorded PASS (approved implementation)"
        in text
    )
    assert "not replayable" not in text
    out = io.StringIO()
    assert run.route(out, recorded_root=root) == 0
    assert "recorded/ffffffffffff: replayed PASS" in out.getvalue()
    assert "(approved)" in out.getvalue()
    assert (
        "queue journal: [('billing', 'T-1001'), ('technical', 'T-1002'), ('sales', 'T-1003')]"
        in out.getvalue()
    )
    # Nothing was rewritten: not the archive, not the producer record, not the registry.
    assert {p.name: p.read_bytes() for p in (foreign / "evidence").iterdir()} == before
    assert read_json(foreign / "PRODUCER.json")["lock_sha256"] == seal
    assert registry.read_text(encoding="utf-8") == registry_text(
        {HEX_F: ENGINE, implementation_fingerprint(): ENGINE}
    )
    assert read_json(
        EXAMPLE_DIR.parents[1] / "src" / "actseal" / "compatibility_registry.json"
    ) == {
        "schema_version": 1,
        "implementations": {},
    }


def test_one_sided_registration_does_not_approve(
    run: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "recorded"
    root.mkdir()
    foreign_copy(committed_run(), root / "ffffffffffff", HEX_F)
    approve(monkeypatch, tmp_path, HEX_F)  # the running fingerprint is not registered
    assert run.compatibility_status(run.load_producer(root / "ffffffffffff")) == "unapproved"
    out = io.StringIO()
    assert run.check(out, recorded_root=root) == 1
    assert "not replayable under the running implementation" in out.getvalue()
    out = io.StringIO()
    assert run.route(out, recorded_root=root) == 1


def test_damaged_or_mismatched_runs_fail_the_check(run: ModuleType, tmp_path: Path) -> None:
    root = tmp_path / "recorded"
    root.mkdir()
    damaged = root / "damaged"
    shutil.copytree(committed_run(), damaged)
    records = damaged / "evidence" / "records.jsonl"
    records.write_bytes(records.read_bytes().replace(b'"choice":"billing"', b'"choice":"sales"', 1))
    out = io.StringIO()
    assert run.check(out, recorded_root=root) == 1
    assert "[error] recorded/damaged:" in out.getvalue()
    # Rehashed so ordinary hashes agree: records now differ from the fresh run and replay objects.
    rehash_bundle(damaged / "evidence")
    out = io.StringIO()
    assert run.check(out, recorded_root=root) == 1
    assert "records.jsonl differs from the fresh run" in out.getvalue()
    assert "differs from the record" in out.getvalue()


def test_stale_inputs_fail_the_check(run: ModuleType, tmp_path: Path) -> None:
    root = tmp_path / "recorded"
    root.mkdir()
    stale = root / "stale"
    shutil.copytree(committed_run(), stale)
    producer = read_json(stale / "PRODUCER.json")
    inputs = producer["inputs"]
    assert isinstance(inputs, dict)
    inputs["contract.toml"] = HEX_F
    (stale / "PRODUCER.json").write_text(
        json.dumps(producer, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    out = io.StringIO()
    assert run.check(out, recorded_root=root) == 1
    assert (
        "[error] recorded/stale: authored inputs changed since this run was recorded"
        in out.getvalue()
    )


def test_empty_recorded_root_fails_the_check(run: ModuleType, tmp_path: Path) -> None:
    out = io.StringIO()
    assert run.check(out, recorded_root=tmp_path / "missing") == 1
    assert "[error] recorded: no recorded run under recorded/" in out.getvalue()


def test_example_imports_only_public_actseal_names() -> None:
    """The example is an integrator: no private (underscore) actseal attribute is used."""
    for name in ("gate.py", "run.py"):
        text = (EXAMPLE_DIR / name).read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith("from actseal"):
                assert "import _" not in line, line
                assert ", _" not in line, line
