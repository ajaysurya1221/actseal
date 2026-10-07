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
    change_threshold,
    corrupt_dataset,
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
PACKAGED_REGISTRY = REPO_ROOT / "src" / "actseal" / "compatibility_registry.json"
#: The reviewed packaged registry: the 1.0.0 source and the committed archive's original
#: (unreleased prerelease) producer (amendment V1-037), plus the reviewed 1.0.1 final
#: candidate source (amendment V1-055). The committed run is therefore a
#: registry-approved, not exact, implementation for the running source.
APPROVED_REGISTRY = {
    "schema_version": 1,
    "implementations": {
        "8f316f679b2ed5be4ce19127da87db21511ce4de2ff1450439fcf3c549598ed3": ENGINE,
        "a5fe090202f75b07510407937a86ae35a7653a75eab3f4daa2d0ace2e7641642": ENGINE,
        "dced01d79e64799a19a75c0957f3684a48249c58ebb27d346336e7420195bcb4": ENGINE,
    },
}


def approve(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *fingerprints: str) -> Path:
    """Point ``load_registry`` at a temporary registry approving ``fingerprints`` for the engine.

    The packaged registry file is never edited; the patch is undone by pytest.
    """
    path = tmp_path / "registry.json"
    path.write_text(registry_text(dict.fromkeys(fingerprints, ENGINE)), encoding="utf-8")
    monkeypatch.setattr(compatibility_module, "_REGISTRY_PATH", path)
    return path


def forbid_queue_operations(run: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """Make any routing (the only path to a queue operation) fail the test loudly."""

    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("a queue operation was attempted")

    monkeypatch.setattr(run, "route_all", forbidden)


def snapshot(run_dir: Path) -> dict[str, bytes]:
    return {str(p.relative_to(run_dir)): p.read_bytes() for p in run_dir.rglob("*") if p.is_file()}


def committed_run() -> Path:
    runs = sorted(path for path in RECORDED_DIR.iterdir() if path.is_dir())
    assert runs
    return runs[0]


def assert_refused(run: ModuleType, root: Path, *fragments: str) -> str:
    """``--check`` and ``--route`` both fail, mention every fragment and perform no queue effect."""
    out = io.StringIO()
    assert run.check(out, recorded_root=root) == 1
    text = out.getvalue()
    for fragment in fragments:
        assert fragment in text, (fragment, text)
    assert "[info] routing: skipped; no queue operation while any active archive fails" in text
    assert "[ok] routing" not in text
    out = io.StringIO()
    assert run.route(out, recorded_root=root) == 1
    assert "route refused:" in out.getvalue()
    assert "no queue operation was performed" in out.getvalue()
    assert "queue journal" not in out.getvalue()
    return text


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


@pytest.mark.parametrize("beside_valid_run", [False, True], ids=["alone", "beside-valid"])
def test_unapproved_foreign_archive_fails_with_no_queue_effect_and_preserved_bytes(
    run: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, beside_valid_run: bool
) -> None:
    """V1-020: an unsupported active archive fails --check and --route, even beside a valid run."""
    root = tmp_path / "recorded"
    root.mkdir()
    foreign = root / "000000000000"  # sorts first, so it would be routed if tolerated
    seal = foreign_copy(committed_run(), foreign, HEX_0)
    if beside_valid_run:
        shutil.copytree(committed_run(), root / committed_run().name)
    before = snapshot(root)
    forbid_queue_operations(run, monkeypatch)
    text = assert_refused(
        run,
        root,
        "[error] recorded/000000000000: replay ERROR ['integrity.lock'] does not reproduce the "
        "recorded PASS",
        "producer 000000000000 is not supported by the running implementation",
        "(no registry approval); bytes preserved",
    )
    assert "[info] recorded/000000000000" not in text  # never a benign notice
    if beside_valid_run:
        assert (
            f"[ok] recorded/{committed_run().name}: replay equals the recorded PASS "
            "(registry-approved implementation)" in text
        )
    assert snapshot(root) == before
    assert read_json(foreign / "PRODUCER.json")["lock_sha256"] == seal
    assert read_json(PACKAGED_REGISTRY) == APPROVED_REGISTRY


def test_dual_approved_foreign_archive_passes_check_and_route(
    run: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both fingerprints registered for the engine: core replay accepts, so does the example."""
    root = tmp_path / "recorded"
    root.mkdir()
    foreign = root / "ffffffffffff"
    seal = foreign_copy(committed_run(), foreign, HEX_F)
    before = snapshot(root)
    registry = approve(monkeypatch, tmp_path, HEX_F, implementation_fingerprint())
    out = io.StringIO()
    assert run.check(out, recorded_root=root) == 0
    text = out.getvalue()
    assert (
        "[ok] recorded/ffffffffffff: replay equals the recorded PASS "
        "(registry-approved implementation)" in text
    )
    assert "[ok] routing: queue journal holds exactly the 3 ACT tickets" in text
    out = io.StringIO()
    assert run.route(out, recorded_root=root) == 0
    assert "recorded/ffffffffffff: replayed PASS" in out.getvalue()
    assert (
        "queue journal: [('billing', 'T-1001'), ('technical', 'T-1002'), ('sales', 'T-1003')]"
        in out.getvalue()
    )
    # Nothing was rewritten: not the archive, not the producer record, not any registry.
    assert snapshot(root) == before
    assert read_json(foreign / "PRODUCER.json")["lock_sha256"] == seal
    assert registry.read_text(encoding="utf-8") == registry_text(
        {HEX_F: ENGINE, implementation_fingerprint(): ENGINE}
    )
    assert read_json(PACKAGED_REGISTRY) == APPROVED_REGISTRY


@pytest.mark.parametrize("registered", ["producer", "running"])
def test_one_sided_registration_fails_check_and_route(
    run: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, registered: str
) -> None:
    root = tmp_path / "recorded"
    root.mkdir()
    foreign_copy(committed_run(), root / "ffffffffffff", HEX_F)
    approve(
        monkeypatch, tmp_path, HEX_F if registered == "producer" else implementation_fingerprint()
    )
    before = snapshot(root)
    forbid_queue_operations(run, monkeypatch)
    assert_refused(
        run,
        root,
        "[error] recorded/ffffffffffff: replay ERROR ['integrity.lock'] does not reproduce",
    )
    assert snapshot(root) == before


def test_root_and_bundle_lock_mismatch_fails(
    run: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The root lock.json must be the bundle's lock.json byte for byte."""
    root = tmp_path / "recorded"
    root.mkdir()
    mismatched = root / committed_run().name
    shutil.copytree(committed_run(), mismatched)
    other = tmp_path / "other"
    foreign_copy(committed_run(), other, HEX_F)
    # A different, internally valid lock at the root; PRODUCER.json describes that root lock.
    shutil.copyfile(other / "lock.json", mismatched / "lock.json")
    shutil.copyfile(other / "PRODUCER.json", mismatched / "PRODUCER.json")
    forbid_queue_operations(run, monkeypatch)
    assert_refused(
        run,
        root,
        f"[error] recorded/{committed_run().name}: lock.json: root copy differs from the bundle",
    )


def test_rehashed_dataset_corruption_fails(
    run: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An archived dataset edited and rehashed so ordinary hashes agree is still refused."""
    root = tmp_path / "recorded"
    root.mkdir()
    corrupted = root / committed_run().name
    shutil.copytree(committed_run(), corrupted)
    corrupt_dataset(corrupted)
    forbid_queue_operations(run, monkeypatch)
    assert_refused(
        run,
        root,
        f"[error] recorded/{committed_run().name}: verification.jsonl: bundle dataset differs "
        "from the committed input",
    )


def test_consistently_changed_foreign_policy_fails_even_when_approved(
    run: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A foreign archive with a different frozen policy is refused before replay is consulted."""
    root = tmp_path / "recorded"
    root.mkdir()
    foreign = root / "ffffffffffff"
    foreign_copy(committed_run(), foreign, HEX_F)
    change_threshold(foreign, 0.5)
    approve(monkeypatch, tmp_path, HEX_F, implementation_fingerprint())
    before = snapshot(root)
    forbid_queue_operations(run, monkeypatch)
    assert_refused(
        run,
        root,
        "[error] recorded/ffffffffffff: lock.contract: differs from the frozen contract.toml",
    )
    assert snapshot(root) == before


@pytest.mark.parametrize("fingerprint", [None, HEX_F], ids=["running-producer", "foreign-producer"])
def test_invalid_archived_seal_fails_beside_a_valid_current_run(
    run: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fingerprint: str | None
) -> None:
    """A corrupt archive is an error reported by the core replay, never tolerated."""
    root = tmp_path / "recorded"
    root.mkdir()
    shutil.copytree(committed_run(), root / committed_run().name)
    broken = root / "ffffffffffff"
    if fingerprint is None:
        shutil.copytree(committed_run(), broken)
    else:
        foreign_copy(committed_run(), broken, fingerprint)
    corrupt_seal(broken, HEX_E)
    assert replay(broken / "evidence", expected_lock_sha256=HEX_E).reasons == ("integrity.lock",)
    forbid_queue_operations(run, monkeypatch)
    text = assert_refused(
        run,
        root,
        "[error] recorded/ffffffffffff: replay ERROR ['integrity.lock'] does not reproduce the "
        "recorded PASS",
    )
    # The committed archive's producer is the approved original, not the running source.
    assert (
        f"[ok] recorded/{committed_run().name}: replay equals the recorded PASS "
        "(registry-approved implementation)" in text
    )


def test_damaged_or_mismatched_runs_fail_the_check(
    run: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "recorded"
    root.mkdir()
    damaged = root / "damaged"
    shutil.copytree(committed_run(), damaged)
    records = damaged / "evidence" / "records.jsonl"
    records.write_bytes(records.read_bytes().replace(b'"choice":"billing"', b'"choice":"sales"', 1))
    forbid_queue_operations(run, monkeypatch)
    assert_refused(run, root, "[error] recorded/damaged:")
    # Rehashed so ordinary hashes agree: records now differ from the fresh run and replay objects.
    rehash_bundle(damaged / "evidence")
    assert_refused(
        run,
        root,
        "[error] recorded/damaged: records.jsonl differs from the fresh run",
        "[error] recorded/damaged: replay ERROR",
        "does not reproduce the recorded PASS",
    )


def test_stale_inputs_fail_the_check(
    run: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
    forbid_queue_operations(run, monkeypatch)
    assert_refused(
        run,
        root,
        "[error] recorded/stale: producer.inputs: differ from the committed authored inputs",
    )


def test_empty_recorded_root_fails_check_and_route(
    run: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    forbid_queue_operations(run, monkeypatch)
    assert_refused(run, tmp_path / "missing", "[error] recorded: no recorded run under recorded/")


def test_example_imports_only_public_actseal_names() -> None:
    """The example is an integrator: no private (underscore) actseal attribute is used."""
    for name in ("gate.py", "run.py"):
        text = (EXAMPLE_DIR / name).read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith("from actseal"):
                assert "import _" not in line, line
                assert ", _" not in line, line
