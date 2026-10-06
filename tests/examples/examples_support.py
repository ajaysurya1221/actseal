"""Helpers for the ``examples/action_gate`` tests.

The example lives outside the ``actseal`` package and is imported by path, so
these tests run in the default core environment with no key, model or
network. The modules are loaded once per session and typed as ``ModuleType``;
their attributes are therefore ``Any`` in the tests.

The archive forgeries below (``foreign_copy``, ``rewrite_lock``,
``corrupt_seal``, ``corrupt_dataset``) rewrite *copies* of the committed run
under a test's temporary directory. They exist to prove what the example's
check refuses; the committed recording is never touched.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import shutil
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_DIR = REPO_ROOT / "examples" / "action_gate"
RUN_SCRIPT = EXAMPLE_DIR / "run.py"
GENERATOR = EXAMPLE_DIR / "generate_data.py"
RECORDED_DIR = EXAMPLE_DIR / "recorded"
DATA_FILES = (
    "contract.toml",
    "calibration.jsonl",
    "verification.jsonl",
    "responses.jsonl",
    "tickets.jsonl",
)
BUNDLE_DATA_FILES = (
    "lock.json",
    "calibration.jsonl",
    "verification.jsonl",
    "records.jsonl",
    "faults.jsonl",
    "verdict.json",
)


def load_module(name: str) -> ModuleType:
    """Import ``gate``, ``run`` or ``generate_data`` from the example directory."""
    if str(EXAMPLE_DIR) not in sys.path:
        sys.path.insert(0, str(EXAMPLE_DIR))
    return importlib.import_module(name)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: object) -> bytes:
    """Documented canonical JSON: sorted keys, compact separators, UTF-8, no newline."""
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_bytes().decode("utf-8"))
    assert isinstance(value, dict)
    return value


def write_producer(run_dir: Path, producer: dict[str, object]) -> None:
    (run_dir / "PRODUCER.json").write_text(
        json.dumps(producer, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def rehash_bundle(bundle: Path) -> None:
    """Rewrite ``manifest.json`` so every ordinary per-file hash is consistent again."""
    files = {
        name: {"size": len(data), "sha256": sha256_hex(data)}
        for name in BUNDLE_DATA_FILES
        for data in [(bundle / name).read_bytes()]
    }
    unsealed: dict[str, object] = {"schema_version": 2, "files": files}
    manifest = {**unsealed, "sha256": sha256_hex(canonical(unsealed))}
    (bundle / "manifest.json").write_bytes(canonical(manifest) + b"\n")


def rewrite_lock(
    run_dir: Path,
    mutate: Callable[[dict[str, object]], None] | None = None,
    *,
    seal: str | None = None,
) -> str:
    """Rewrite a copied run's lock consistently and return the new seal.

    ``mutate`` edits the decoded lock document; the lock is then resealed
    (or given the literal ``seal``), written to both the root and the bundle,
    the verdict's ``lock_sha256`` and the manifest are rewritten to agree, and
    ``PRODUCER.json`` is updated to the new seal and producer fingerprint. Every
    ordinary hash check passes afterwards; only semantic checks can object.
    """
    evidence = run_dir / "evidence"
    lock = read_json(evidence / "lock.json")
    if mutate is not None:
        mutate(lock)
    unsealed = {key: value for key, value in lock.items() if key != "sha256"}
    new_seal = sha256_hex(canonical(unsealed)) if seal is None else seal
    lock_bytes = canonical({**unsealed, "sha256": new_seal}) + b"\n"
    (evidence / "lock.json").write_bytes(lock_bytes)
    (run_dir / "lock.json").write_bytes(lock_bytes)
    verdict = read_json(evidence / "verdict.json")
    verdict["lock_sha256"] = new_seal
    (evidence / "verdict.json").write_bytes(canonical(verdict) + b"\n")
    rehash_bundle(evidence)
    producer = read_json(run_dir / "PRODUCER.json")
    producer["lock_sha256"] = new_seal
    producer["implementation_sha256"] = lock["implementation_sha256"]
    write_producer(run_dir, producer)
    return new_seal


def foreign_copy(run_dir: Path, destination: Path, fingerprint: str) -> str:
    """Copy a recorded run as if a different implementation had produced it.

    The lock is resealed with ``fingerprint`` as its producer and everything
    else is rewritten to agree, so only replay-engine compatibility can
    object. This is a test forgery of provenance; it returns the new seal.
    """
    shutil.copytree(run_dir, destination)

    def set_producer(lock: dict[str, object]) -> None:
        lock["implementation_sha256"] = fingerprint

    return rewrite_lock(destination, set_producer)


def corrupt_seal(run_dir: Path, seal: str) -> None:
    """Give the archived lock a wrong self-seal while every ordinary hash still agrees."""
    rewrite_lock(run_dir, seal=seal)


def change_threshold(run_dir: Path, threshold: float) -> str:
    """Consistently change the archived policy threshold (lock, verdict, manifest, producer)."""

    def set_threshold(lock: dict[str, object]) -> None:
        contract = lock["contract"]
        assert isinstance(contract, dict)
        policy = contract["policy"]
        assert isinstance(policy, dict)
        policy["threshold"] = threshold

    return rewrite_lock(run_dir, set_threshold)


def corrupt_dataset(run_dir: Path) -> None:
    """Alter one archived verification state text and rehash the manifest to match."""
    path = run_dir / "evidence" / "verification.jsonl"
    data = path.read_bytes()
    altered = data.replace(b"Ticket GATE-V-000:", b"Ticket GATE-V-000 (edited):", 1)
    assert altered != data
    path.write_bytes(altered)
    rehash_bundle(run_dir / "evidence")


def registry_text(entries: dict[str, str]) -> str:
    return json.dumps({"schema_version": 1, "implementations": entries})
