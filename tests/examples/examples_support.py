"""Helpers for the ``examples/action_gate`` tests.

The example lives outside the ``actseal`` package and is imported by path, so
these tests run in the default core environment with no key, model or
network. The modules are loaded once per session and typed as ``ModuleType``;
their attributes are therefore ``Any`` in the tests.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import shutil
import sys
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


def write_producer(run_dir: Path, producer: dict[str, object]) -> None:
    (run_dir / "PRODUCER.json").write_text(
        json.dumps(producer, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def corrupt_seal(run_dir: Path, seal: str) -> None:
    """Replace the archived lock's own seal (root and bundle copies) with ``seal``.

    The verdict, manifest and ``PRODUCER.json`` are rewritten to agree, so
    every ordinary hash check passes and only the self-seal is wrong. The
    producer fingerprint is left as it is.
    """
    evidence = run_dir / "evidence"
    lock = read_json(evidence / "lock.json")
    lock["sha256"] = seal
    lock_bytes = canonical(lock) + b"\n"
    (evidence / "lock.json").write_bytes(lock_bytes)
    (run_dir / "lock.json").write_bytes(lock_bytes)
    verdict = read_json(evidence / "verdict.json")
    verdict["lock_sha256"] = seal
    (evidence / "verdict.json").write_bytes(canonical(verdict) + b"\n")
    rehash_bundle(evidence)
    producer = read_json(run_dir / "PRODUCER.json")
    producer["lock_sha256"] = seal
    write_producer(run_dir, producer)


def registry_text(entries: dict[str, str]) -> str:
    return json.dumps({"schema_version": 1, "implementations": entries})


def foreign_copy(run_dir: Path, destination: Path, fingerprint: str) -> str:
    """Copy a recorded run as if a different implementation had produced it.

    The lock is resealed with ``fingerprint`` as its producer, the verdict and
    manifest are rehashed to match and ``PRODUCER.json`` is updated, so every
    ordinary integrity check passes and only replay-engine compatibility can
    object. Returns the new lock seal. This is a test forgery of provenance,
    which is exactly what the example's check must refuse to replay.
    """
    shutil.copytree(run_dir, destination)
    evidence = destination / "evidence"
    lock = read_json(evidence / "lock.json")
    lock["implementation_sha256"] = fingerprint
    unsealed = {key: value for key, value in lock.items() if key != "sha256"}
    seal = sha256_hex(canonical(unsealed))
    lock_bytes = canonical({**unsealed, "sha256": seal}) + b"\n"
    (evidence / "lock.json").write_bytes(lock_bytes)
    (destination / "lock.json").write_bytes(lock_bytes)
    verdict = read_json(evidence / "verdict.json")
    verdict["lock_sha256"] = seal
    (evidence / "verdict.json").write_bytes(canonical(verdict) + b"\n")
    rehash_bundle(evidence)
    producer = read_json(destination / "PRODUCER.json")
    producer["implementation_sha256"] = fingerprint
    producer["lock_sha256"] = seal
    write_producer(destination, producer)
    return seal
