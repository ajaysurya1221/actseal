"""Cross-release replay against evidence produced by a genuinely different source tree.

A second copy of the ``actseal`` package is written under the pytest temporary
directory with only its ``__version__`` string changed, which is exactly the
release-bump situation the v1.0 compatibility model exists for. Its
implementation fingerprint therefore differs from the running tree's. Evidence
is produced by running the real CLI inside that copy in a child interpreter, and
then replayed by the running tree (and vice versa) under every registry
condition. No fingerprint is monkeypatched: only the registry a verifier trusts
is varied, in-process through the loader's path and in the child through the
packaged registry file of the copied tree.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import actseal.compatibility as compatibility_module
from actseal.cli import main
from actseal.compatibility import CURRENT_ENGINE, REGISTRY_FILE
from actseal.contract import read_input_text
from actseal.errors import IntegrityError
from actseal.locking import parse_lock
from actseal.replay import REASON_LOCK, replay
from actseal.runner import verify_run
from actseal.serialization import implementation_fingerprint

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "src" / "actseal"
PACKAGED_INPUTS = PACKAGE / "demo_data"
RUN = "fixed"
VERSION_LINE = re.compile(r'^__version__ = ".*"$', re.MULTILINE)

_CHILD = r"""
import io
import json
import sys

root = sys.argv[1]
sys.path.insert(0, root)
import actseal  # noqa: E402
from actseal.cli import main  # noqa: E402
from actseal.serialization import implementation_fingerprint  # noqa: E402

assert actseal.__file__.startswith(root), actseal.__file__
argv = sys.argv[2:]
buffer = io.StringIO()
real = sys.stdout
sys.stdout = buffer
try:
    code = main(argv) if argv else 0
finally:
    sys.stdout = real
print(
    json.dumps(
        {
            "code": code,
            "stdout": buffer.getvalue(),
            "fingerprint": implementation_fingerprint(),
            "version": actseal.__version__,
        }
    )
)
"""


def child_env() -> dict[str, str]:
    return {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}


def run_in_tree(root: Path, argv: list[str]) -> dict[str, object]:
    result = subprocess.run(  # noqa: S603 - fixed interpreter and literal script, no user input
        [sys.executable, "-c", _CHILD, str(root), *argv],
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
        cwd=str(root),
        env=child_env(),
    )
    assert result.returncode == 0, result.stderr[-2000:]
    report = json.loads(result.stdout)
    assert isinstance(report, dict)
    return report


def tree_json(report: dict[str, object]) -> dict[str, object]:
    document = json.loads(str(report["stdout"]))
    assert isinstance(document, dict)
    return document


def write_registry(root: Path, entries: dict[str, str]) -> None:
    (root / "actseal" / REGISTRY_FILE).write_text(
        json.dumps({"schema_version": 1, "implementations": entries}), encoding="utf-8"
    )


def lock_argv(lock: Path) -> list[str]:
    return [
        "lock",
        "--contract",
        str(PACKAGED_INPUTS / f"{RUN}.toml"),
        "--calibration",
        str(PACKAGED_INPUTS / f"{RUN}_calibration.jsonl"),
        "--verification",
        str(PACKAGED_INPUTS / f"{RUN}_verification.jsonl"),
        "--provider",
        "fixture",
        "--responses",
        str(PACKAGED_INPUTS / f"{RUN}_responses.jsonl"),
        "--out",
        str(lock),
        "--json",
    ]


def verify_argv(lock: Path, out: Path) -> list[str]:
    return [
        "verify",
        "--lock",
        str(lock),
        "--calibration",
        str(PACKAGED_INPUTS / f"{RUN}_calibration.jsonl"),
        "--verification",
        str(PACKAGED_INPUTS / f"{RUN}_verification.jsonl"),
        "--provider",
        "fixture",
        "--responses",
        str(PACKAGED_INPUTS / f"{RUN}_responses.jsonl"),
        "--out",
        str(out),
        "--json",
    ]


@pytest.fixture(scope="module")
def other_tree(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A copy of the package whose only source change is the version string."""
    root = tmp_path_factory.mktemp("other-release")
    shutil.copytree(PACKAGE, root / "actseal", ignore=shutil.ignore_patterns("__pycache__"))
    init = root / "actseal" / "__init__.py"
    text = init.read_text(encoding="utf-8")
    assert len(VERSION_LINE.findall(text)) == 1
    init.write_text(
        VERSION_LINE.sub('__version__ = "0.0.0+cross-release-test"', text), encoding="utf-8"
    )
    return root


@pytest.fixture(scope="module")
def other_fingerprint(other_tree: Path) -> str:
    report = run_in_tree(other_tree, [])
    assert report["version"] == "0.0.0+cross-release-test"
    fingerprint = str(report["fingerprint"])
    assert fingerprint != implementation_fingerprint()
    return fingerprint


@pytest.fixture(scope="module")
def other_evidence(
    other_tree: Path, other_fingerprint: str, tmp_path_factory: pytest.TempPathFactory
) -> tuple[Path, Path, dict[str, object]]:
    """Lock and verify run by the OTHER tree; returns (lock path, bundle path, verify receipt)."""
    workspace = tmp_path_factory.mktemp("other-evidence")
    lock = workspace / "lock.json"
    locked = tree_json(run_in_tree(other_tree, lock_argv(lock)))
    assert locked["exit_code"] == 0
    assert locked["implementation_sha256"] == other_fingerprint
    assert locked["replay_engine_version"] == CURRENT_ENGINE
    out = workspace / "evidence"
    verified = tree_json(run_in_tree(other_tree, verify_argv(lock, out)))
    assert verified["status"] == "PASS"
    assert verified["exit_code"] == 0
    return lock, out, verified


def point_registry_at(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, entries: dict[str, str]
) -> None:
    path = tmp_path / "registry.json"
    path.write_text(json.dumps({"schema_version": 1, "implementations": entries}), encoding="utf-8")
    monkeypatch.setattr(compatibility_module, "_REGISTRY_PATH", path)


# --------------------------------------------------------------------------- #
# Fingerprints
# --------------------------------------------------------------------------- #


def test_version_bump_changes_the_fingerprint_but_the_registry_does_not(
    other_tree: Path, other_fingerprint: str
) -> None:
    write_registry(other_tree, {other_fingerprint: CURRENT_ENGINE, "1" * 64: CURRENT_ENGINE})
    assert run_in_tree(other_tree, [])["fingerprint"] == other_fingerprint
    write_registry(other_tree, {})
    assert run_in_tree(other_tree, [])["fingerprint"] == other_fingerprint


# --------------------------------------------------------------------------- #
# Other tree produced the evidence; this tree replays it
# --------------------------------------------------------------------------- #


def test_other_release_evidence_replays_here_only_with_dual_registration(
    other_evidence: tuple[Path, Path, dict[str, object]],
    other_fingerprint: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    lock_path, bundle, receipt = other_evidence
    lock = parse_lock(read_input_text(lock_path))
    assert lock.implementation_sha256 == other_fingerprint != implementation_fingerprint()
    current = implementation_fingerprint()

    # Default: the packaged registry is empty, so this is a foreign producer.
    rejected = replay(bundle)
    assert rejected.status == "ERROR"
    assert rejected.reasons == (REASON_LOCK,)
    assert rejected.lock_sha256 == lock.sha256  # decoded identity is retained

    # One side registered is never enough.
    for entries in ({other_fingerprint: CURRENT_ENGINE}, {current: CURRENT_ENGINE}):
        point_registry_at(monkeypatch, tmp_path, entries)
        assert replay(bundle).reasons == (REASON_LOCK,), entries

    # Both registered for the lock's engine: the fresh verdict equals the recorded one.
    point_registry_at(
        monkeypatch, tmp_path, {other_fingerprint: CURRENT_ENGINE, current: CURRENT_ENGINE}
    )
    verdict = replay(bundle)
    assert verdict.status == receipt["status"] == "PASS"
    assert list(verdict.reasons) == receipt["reasons"]
    assert (verdict.total, verdict.accepted, verdict.errors) == (
        receipt["total"],
        receipt["accepted"],
        receipt["errors"],
    )
    assert {"lower": verdict.risk.lower, "upper": verdict.risk.upper} == receipt["risk"]
    assert verdict.lock_sha256 == receipt["lock_sha256"] == lock.sha256
    assert replay(bundle, expected_lock_sha256=lock.sha256) == verdict

    # The CLI agrees and the receipt is versioned.
    code = main(["replay", str(bundle), "--json"])
    assert code == 0
    assert replay(bundle) == verdict


def test_this_release_never_collects_against_the_other_release_lock(
    other_evidence: tuple[Path, Path, dict[str, object]],
    other_fingerprint: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lock_path, _, _ = other_evidence
    point_registry_at(
        monkeypatch,
        tmp_path,
        {other_fingerprint: CURRENT_ENGINE, implementation_fingerprint(): CURRENT_ENGINE},
    )

    def never_called() -> object:
        pytest.fail("model factory must not be called for a foreign producer")

    with pytest.raises(IntegrityError, match="new collection requires the exact current"):
        verify_run(
            lock_path,
            PACKAGED_INPUTS / f"{RUN}_calibration.jsonl",
            PACKAGED_INPUTS / f"{RUN}_verification.jsonl",
            tmp_path / "run",
            provider="fixture",
            model_factory=never_called,  # type: ignore[arg-type]
        )
    code = main(verify_argv(lock_path, tmp_path / "cli-run"))
    document = json.loads(capsys.readouterr().out)
    assert code == 3
    assert document["schema_version"] == 1
    assert str(document["error"]).startswith("IntegrityError: implementation_sha256")
    assert not (tmp_path / "cli-run").exists()


# --------------------------------------------------------------------------- #
# This tree produced the evidence; the other tree replays it
# --------------------------------------------------------------------------- #


def test_this_release_evidence_replays_in_the_other_release_only_when_its_registry_approves(
    other_tree: Path, other_fingerprint: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    lock = tmp_path / "lock.json"
    assert main(lock_argv(lock)) == 0
    locked = json.loads(capsys.readouterr().out)
    assert locked["implementation_sha256"] == implementation_fingerprint()
    out = tmp_path / "evidence"
    assert main(verify_argv(lock, out)) == 0
    verified = json.loads(capsys.readouterr().out)
    assert verified["status"] == "PASS"
    current = implementation_fingerprint()

    write_registry(other_tree, {})
    rejected = tree_json(run_in_tree(other_tree, ["replay", str(out), "--json"]))
    assert rejected["exit_code"] == 3
    assert rejected["reasons"] == [REASON_LOCK]
    assert rejected["lock_sha256"] == verified["lock_sha256"]

    write_registry(other_tree, {current: CURRENT_ENGINE})
    assert tree_json(run_in_tree(other_tree, ["replay", str(out), "--json"]))["exit_code"] == 3

    write_registry(other_tree, {current: CURRENT_ENGINE, other_fingerprint: CURRENT_ENGINE})
    accepted = tree_json(run_in_tree(other_tree, ["replay", str(out), "--json"]))
    assert accepted["schema_version"] == 1
    assert accepted["exit_code"] == 0
    assert accepted["status"] == "PASS"
    for field in ("reasons", "total", "accepted", "errors", "risk", "coverage", "lock_sha256"):
        assert accepted[field] == verified[field], field

    # Even with approval the other release cannot collect against this lock.
    collected = tree_json(run_in_tree(other_tree, verify_argv(lock, tmp_path / "other-run")))
    assert collected["exit_code"] == 3
    assert str(collected["error"]).startswith("IntegrityError: implementation_sha256")
    assert not (tmp_path / "other-run").exists()
    write_registry(other_tree, {})
