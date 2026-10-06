"""Filesystem and data-only boundary acceptance on pytest-owned temporary paths.

Executable-looking strings travel through lock, verify and replay in guarded
subprocesses (sockets, process spawning, ``exec``/``eval`` and prohibited
imports instrumented to fail) and must remain inert data with the environment
unchanged. Bundle directories with symlinks, extra or nonregular entries,
manifest traversal, sparse oversized files, excess nesting and oversized rows
must ERROR with the documented reasons, without reading targets and without
any effect outside the temporary directory.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

import pytest
from acceptance_support import (
    BUNDLE_FILES,
    MODULE_ENTRY,
    ZERO_HASH,
    Workspace,
    answer_body,
    cases_jsonl,
    clean_env,
    contract_toml,
    document_bytes,
    lock_argv,
    make_cases,
    nested,
    read_document,
    read_rows,
    rehash_bundle,
    responses_jsonl,
    rows_bytes,
    run_cli,
    verify_argv,
    write_workspace,
)

from actseal.records import Interval
from actseal.replay import replay

FULL = Interval(0.0, 1.0)
MIB = 1024 * 1024

PAYLOADS: tuple[str, ...] = (
    "__import__('os').system('touch {marker}')",
    "$(touch {marker}); `touch {marker}`; ; rm -rf /tmp/never",
    "import os; os.environ['ACTSEAL_ACCEPTANCE_PWNED'] = '1'",
    "{{7*7}} ${{HOME}} %PATH% \\u0000 " + chr(0) + " " + chr(0x202E) + " <script>alert(1)</script>",
    "exec(open('/etc/passwd').read()); eval('1+1')",
    "actseal.adapters.laya:LayaModel\npickle.loads(b'...')",
)

_GUARDED = r"""
import builtins
import io
import json
import os
import socket
import subprocess
import sys

marker = sys.argv[1]
blocked = tuple(sys.argv[2].split(","))
environment = dict(os.environ)
attempts = []


def deny(name):
    def _deny(*_args, **_kwargs):
        attempts.append(name)
        raise RuntimeError("denied: " + name)

    return _deny


for attribute in ("socket", "create_connection", "getaddrinfo", "socketpair"):
    setattr(socket, attribute, deny("socket." + attribute))


def _blocked(name):
    return any(name == root or name.startswith(root + ".") for root in blocked)


class DenyImports:
    def find_spec(self, name, path=None, target=None):
        if _blocked(name):
            attempts.append("import:" + name)
            raise ImportError("blocked import: " + name)
        return None


sys.meta_path.insert(0, DenyImports())

from actseal.cli import main  # noqa: E402

if not _blocked("actseal.adapters.fixture"):
    # The fixture provider is the one product module lock/verify import lazily;
    # importing it here keeps the import system's own exec() out of the guarded window.
    import actseal.adapters.fixture  # noqa: E402, F401

# Process spawning and dynamic code execution are denied once the package is
# imported (dataclass construction and module loading legitimately compile code
# at import time); every input/bundle byte is only processed inside main() below.
for attribute in ("system", "popen", "execv", "execve", "spawnv", "fork", "posix_spawn"):
    if hasattr(os, attribute):
        setattr(os, attribute, deny("os." + attribute))
subprocess.Popen = deny("subprocess.Popen")
subprocess.run = deny("subprocess.run")
builtins.exec = deny("exec")
builtins.eval = deny("eval")
builtins.compile = deny("compile")

buffer = io.StringIO()
real_stdout = sys.stdout
sys.stdout = buffer
try:
    code = main(sys.argv[3:])
finally:
    sys.stdout = real_stdout
print(
    json.dumps(
        {
            "code": code,
            "stdout": buffer.getvalue(),
            "attempts": attempts,
            "blocked_loaded": sorted(name for name in sys.modules if _blocked(name)),
            "environment_unchanged": environment == dict(os.environ),
            "marker_exists": os.path.exists(marker),
        }
    )
)
"""

REPLAY_BLOCKED = (
    "actseal.adapters,laya,torch,transformers,huggingface_hub,safetensors,numpy,"
    "urllib.request,http,ssl,pickle,runpy,multiprocessing"
)
FIXTURE_BLOCKED = REPLAY_BLOCKED.replace("actseal.adapters,", "actseal.adapters.laya,")


def guarded(argv: list[str], *, marker: Path, blocked: str, cwd: Path) -> dict[str, object]:
    result = subprocess.run(  # noqa: S603 - fixed interpreter and literal guard script
        [sys.executable, "-c", _GUARDED, str(marker), blocked, *argv],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(cwd),
        env=clean_env(),
        timeout=300,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert isinstance(report, dict)
    return {str(key): value for key, value in report.items()}


def payload_workspace(directory: Path, marker: Path) -> Workspace:
    """Inputs whose every free-text field carries an executable-looking payload."""
    directory.mkdir(parents=True, exist_ok=False)
    cases = [
        (cid, payload.format(marker=marker) + f" case {index}", label)
        for index, ((cid, _, label), payload) in enumerate(
            zip(make_cases("pay", len(PAYLOADS)), PAYLOADS, strict=True)
        )
    ]
    calibration = [
        (cid, f"import sys; sys.exit({index}) {state}", label)
        for index, (cid, state, label) in enumerate(make_cases("pay-cal", 3))
    ]
    rows: dict[str, tuple[str | None, str | None]] = {
        cid: (answer_body(label), None) for cid, _, label in cases
    }
    rows[cases[1][0]] = (f"__import__('os').system('touch {marker}')", None)  # malformed body
    rows[cases[2][0]] = (
        json.dumps(
            {"type": "choice", "choice": PAYLOADS[0].format(marker=marker), "probabilities": {}}
        ),
        None,
    )
    workspace = Workspace(
        directory,
        directory / "contract.toml",
        directory / "calibration.jsonl",
        directory / "verification.jsonl",
        directory / "responses.jsonl",
        tuple(cases),
    )
    population = f"Payload population $(touch {marker}) `touch {marker}`"
    contract = contract_toml(name="payload-contract").replace(
        "Acceptance synthetic support-routing inputs; no deployment claim", population
    )
    workspace.contract.write_text(contract, encoding="utf-8")
    workspace.calibration.write_bytes(cases_jsonl(calibration).encode("utf-8"))
    workspace.verification.write_bytes(cases_jsonl(cases).encode("utf-8"))
    text = responses_jsonl(rows).replace(
        '"warnings": []', "\"warnings\": [\"__import__('os').system('id')\"]"
    )
    workspace.responses.write_bytes(text.encode("utf-8"))
    return workspace


# --------------------------------------------------------------------------- #
# Acceptance 4: executable-looking data stays inert
# --------------------------------------------------------------------------- #


def test_executable_looking_data_stays_inert_through_lock_verify_and_replay(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "pwned.marker"
    workspace = payload_workspace(tmp_path / "ws", marker)
    lock = tmp_path / "lock.json"
    lock_report = guarded(
        [*lock_argv(workspace, lock), "--json"],
        marker=marker,
        blocked=FIXTURE_BLOCKED,
        cwd=tmp_path,
    )
    assert lock_report["code"] == 0, lock_report
    assert json.loads(str(lock_report["stdout"]))["ok"] is True
    out = tmp_path / "evidence"
    verify_report = guarded(
        [*verify_argv(workspace, lock, out), "--json"],
        marker=marker,
        blocked=FIXTURE_BLOCKED,
        cwd=tmp_path,
    )
    assert verify_report["code"] == 2, verify_report
    document = json.loads(str(verify_report["stdout"]))
    assert document["status"] == "INCONCLUSIVE"
    assert (document["total"], document["accepted"]) == (6, 4)
    assert document["failures"] == {"malformed_response": 1, "unknown_choice": 1}
    replay_report = guarded(
        ["replay", str(out), "--json"], marker=marker, blocked=REPLAY_BLOCKED, cwd=tmp_path
    )
    assert replay_report["code"] == 2, replay_report
    assert json.loads(str(replay_report["stdout"]))["lock_sha256"] == document["lock_sha256"]
    # Each stage has its own guard receipt; every one must be clean independently.
    receipts = {"lock": lock_report, "verify": verify_report, "replay": replay_report}
    for stage, receipt in receipts.items():
        assert receipt["attempts"] == [], (stage, receipt["attempts"])
        assert receipt["blocked_loaded"] == [], stage
        assert receipt["environment_unchanged"] is True, stage
        assert receipt["marker_exists"] is False, stage
    # The payloads are preserved verbatim as data in the sealed evidence.
    assert (out / "verification.jsonl").read_bytes() == workspace.verification.read_bytes()
    records = (out / "records.jsonl").read_text(encoding="utf-8")
    assert "__import__('os').system('id')" in records
    assert PAYLOADS[0].format(marker=marker) in records
    assert not marker.exists()
    assert "ACTSEAL_ACCEPTANCE_PWNED" not in os.environ
    assert sorted(p.name for p in tmp_path.iterdir()) == ["evidence", "lock.json", "ws"]


# --------------------------------------------------------------------------- #
# Acceptance 4: directory shape, traversal, size and depth limits
# --------------------------------------------------------------------------- #


@pytest.fixture
def bundle(tmp_path: Path) -> Path:
    workspace = write_workspace(tmp_path / "ws", count=6, prefix="fs")
    lock = tmp_path / "lock.json"
    assert run_cli(MODULE_ENTRY, lock_argv(workspace, lock), cwd=tmp_path).code == 0
    out = tmp_path / "evidence"
    assert run_cli(MODULE_ENTRY, verify_argv(workspace, lock, out), cwd=tmp_path).code == 2
    return out


def assert_structural_error(verdict_path: Path, cwd: Path) -> None:
    """ERROR with exactly ``integrity.bundle_schema`` and the unknown-lock sentinel.

    Reading an unreadable (mode 000) target would surface as ``integrity.bundle_io``
    instead, so where a test makes its target unreadable this single reason code also
    demonstrates that the target was never opened (when not running as root).
    """
    verdict = replay(verdict_path)
    assert verdict.status == "ERROR"
    assert verdict.reasons == ("integrity.bundle_schema",)
    assert verdict.lock_sha256 == ZERO_HASH
    assert (verdict.total, verdict.accepted, verdict.errors) == (0, 0, 0)
    assert verdict.risk == FULL
    assert verdict.coverage == FULL
    result = run_cli(MODULE_ENTRY, ["replay", str(verdict_path), "--json"], cwd=cwd)
    assert result.code == 3
    assert result.json()["reasons"] == ["integrity.bundle_schema"]


Defect = Callable[[Path, Path], Path]


def _defects() -> dict[str, Defect]:
    def symlinked_records(bundle: Path, tmp_path: Path) -> Path:
        target = tmp_path / "outside-secret.jsonl"
        target.write_bytes(b"not json at all\n")
        target.chmod(0o000)  # opening it would be a PermissionError -> integrity.bundle_io
        (bundle / "records.jsonl").unlink()
        (bundle / "records.jsonl").symlink_to(target)
        return bundle

    def extra_file(bundle: Path, _tmp: Path) -> Path:
        (bundle / "notes.txt").write_text("extra", encoding="utf-8")
        return bundle

    def extra_hidden_file(bundle: Path, _tmp: Path) -> Path:
        (bundle / ".DS_Store").write_bytes(b"\x00")
        return bundle

    def missing_file(bundle: Path, _tmp: Path) -> Path:
        (bundle / "faults.jsonl").unlink()
        return bundle

    def directory_in_place_of_file(bundle: Path, _tmp: Path) -> Path:
        (bundle / "verdict.json").unlink()
        (bundle / "verdict.json").mkdir()
        return bundle

    def empty_file(bundle: Path, _tmp: Path) -> Path:
        (bundle / "calibration.jsonl").write_bytes(b"")
        return bundle

    def bundle_path_is_symlink(bundle: Path, tmp_path: Path) -> Path:
        link = tmp_path / "link"
        link.symlink_to(bundle)
        return link

    def bundle_path_is_a_file(_bundle: Path, tmp_path: Path) -> Path:
        path = tmp_path / "file-not-dir"
        path.write_text("{}", encoding="utf-8")
        return path

    def manifest_traversal(bundle: Path, _tmp: Path) -> Path:
        manifest = read_document(bundle / "manifest.json")
        files = nested(manifest, "files")
        files["../lock.json"] = files.pop("lock.json")
        unsealed = {"schema_version": 2, "files": files}
        import hashlib  # noqa: PLC0415 - local, independent self-hash recomputation

        canonical = json.dumps(unsealed, sort_keys=True, separators=(",", ":")).encode()
        manifest = {**unsealed, "sha256": hashlib.sha256(canonical).hexdigest()}
        (bundle / "manifest.json").write_bytes(document_bytes(manifest))
        return bundle

    return {
        "symlinked_records": symlinked_records,
        "extra_file": extra_file,
        "extra_hidden_file": extra_hidden_file,
        "missing_file": missing_file,
        "directory_in_place_of_file": directory_in_place_of_file,
        "empty_file": empty_file,
        "bundle_path_is_symlink": bundle_path_is_symlink,
        "bundle_path_is_a_file": bundle_path_is_a_file,
        "manifest_traversal": manifest_traversal,
    }


@pytest.mark.parametrize("name", sorted(_defects()))
def test_structural_defects_are_schema_errors_with_the_unknown_lock_sentinel(
    bundle: Path, tmp_path: Path, name: str
) -> None:
    before = sorted(p.name for p in tmp_path.iterdir())
    path = _defects()[name](bundle, tmp_path)
    created = sorted(p.name for p in tmp_path.iterdir())
    assert_structural_error(path, tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == created
    assert set(before) <= set(created)
    if name == "symlinked_records":
        target = tmp_path / "outside-secret.jsonl"
        assert os.lstat(target).st_size == len(b"not json at all\n")
        target.chmod(0o644)  # restore for cleanup, then check the bytes were left intact
        assert target.read_bytes() == b"not json at all\n"


def test_size_ceilings_reject_sparse_unreadable_oversized_files_as_schema_errors(
    bundle: Path, tmp_path: Path
) -> None:
    """Oversized files are rejected by size alone: they are sparse, unreadable, and fast.

    ``os.truncate`` allocates no data blocks; mode 000 makes any attempted open a
    ``PermissionError`` (``integrity.bundle_io``) rather than the observed
    ``integrity.bundle_schema`` when the process is unprivileged and permissions
    are enforced. The elapsed-time bound checks prompt completion, not read absence.
    """
    cases = {
        "verdict.json": 128 * MIB + 1,
        "lock.json": 32 * MIB + 1,
    }
    oversized: list[Path] = []
    for name, size in cases.items():
        copy = tmp_path / f"copy-{name}"
        shutil.copytree(bundle, copy)
        os.truncate(copy / name, size)  # sparse: no model-scale allocation
        (copy / name).chmod(0o000)
        oversized.append(copy / name)
        started = time.monotonic()
        assert_structural_error(copy, tmp_path)
        assert time.monotonic() - started < 10.0, name
    aggregate = tmp_path / "copy-aggregate"
    shutil.copytree(bundle, aggregate)
    os.truncate(aggregate / "verification.jsonl", 100 * MIB)  # each under its own ceiling
    os.truncate(aggregate / "records.jsonl", 30 * MIB)
    for name in ("verification.jsonl", "records.jsonl"):
        (aggregate / name).chmod(0o000)
        oversized.append(aggregate / name)
    started = time.monotonic()
    assert_structural_error(aggregate, tmp_path)
    assert time.monotonic() - started < 10.0
    for path in oversized:
        path.chmod(0o644)  # restore for pytest's temporary-directory cleanup


def test_depth_and_row_limits_are_schema_errors_with_the_decoded_lock(
    bundle: Path, tmp_path: Path
) -> None:
    lock_sha256 = str(read_document(bundle / "lock.json")["sha256"])
    deep = tmp_path / "deep"
    shutil.copytree(bundle, deep)
    verdict = read_document(deep / "verdict.json")
    nested_value: object = 1
    for _ in range(40):
        nested_value = [nested_value]
    verdict["reasons"] = nested_value
    rehash_bundle(deep, {"verdict.json": document_bytes(verdict)})
    result = replay(deep)
    assert result.status == "ERROR"
    assert result.reasons == ("integrity.verdict_schema",)
    assert result.lock_sha256 == lock_sha256
    wide = tmp_path / "wide"
    shutil.copytree(bundle, wide)
    rows = read_rows(wide / "records.jsonl")
    nested(rows[0], "capture")["warnings"] = ["w" * (MIB + 16)]
    rehash_bundle(wide, {"records.jsonl": rows_bytes(rows)})
    result = replay(wide)
    assert result.status == "ERROR"
    assert result.reasons == ("integrity.records_schema",)
    assert result.lock_sha256 == lock_sha256
    cli = run_cli(MODULE_ENTRY, ["replay", str(wide), "--json"], cwd=tmp_path)
    assert cli.code == 3
    assert cli.json()["reasons"] == ["integrity.records_schema"]


def test_dataset_row_limit_is_enforced_before_any_provider_call(tmp_path: Path) -> None:
    workspace = write_workspace(tmp_path / "ws", count=6, prefix="big")
    too_many = tmp_path / "too-many.jsonl"
    too_many.write_bytes(cases_jsonl(make_cases("many", 10_001)).encode("utf-8"))
    argv = lock_argv(workspace, tmp_path / "lock.json", "--json")
    argv[argv.index("--verification") + 1] = str(too_many)
    argv[argv.index("--responses") + 1] = str(tmp_path / "absent-responses.jsonl")
    result = run_cli(MODULE_ENTRY, argv, cwd=tmp_path)
    assert result.code == 3
    assert "SchemaError" in str(result.json()["error"])  # not a missing-fixture setup error
    assert not (tmp_path / "lock.json").exists()
    exactly = tmp_path / "exactly.jsonl"
    exactly.write_bytes(cases_jsonl(make_cases("many", 10_000)).encode("utf-8"))
    argv[argv.index("--verification") + 1] = str(exactly)
    result = run_cli(MODULE_ENTRY, argv, cwd=tmp_path)
    assert result.code == 3
    assert "ProviderSetupError" in str(result.json()["error"])  # dataset accepted; fixture absent


def test_replay_has_no_side_effects(bundle: Path, tmp_path: Path) -> None:
    def snapshot(root: Path) -> dict[str, tuple[int, int, int]]:
        return {
            str(p.relative_to(root)): (p.stat().st_size, p.stat().st_mtime_ns, p.stat().st_ino)
            for p in sorted(root.rglob("*"))
        }

    before = snapshot(tmp_path)
    assert sorted(p.name for p in bundle.iterdir()) == sorted(BUNDLE_FILES)
    assert replay(bundle).status == "INCONCLUSIVE"
    assert run_cli(MODULE_ENTRY, ["replay", str(bundle)], cwd=tmp_path).code == 2
    assert snapshot(tmp_path) == before
