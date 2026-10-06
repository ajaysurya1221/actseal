"""The committed recorded run(s): producer identity, preserved bytes, offline replay."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from actseal.adapters.fixture import FixtureModel
from actseal.compatibility import SUPPORTED_ENGINES
from actseal.contract import parse_contract
from actseal.evidence import BUNDLE_FILES, decode_document, read_bundle_files
from actseal.locking import parse_lock, validate_lock
from actseal.records import Verdict
from actseal.replay import replay
from actseal.serialization import implementation_fingerprint
from examples.examples_support import EXAMPLE_DIR, RECORDED_DIR, read_json, sha256_hex


def recorded_dirs() -> list[Path]:
    assert RECORDED_DIR.is_dir(), "the example must ship a recorded run"
    runs = sorted(path for path in RECORDED_DIR.iterdir() if path.is_dir())
    assert runs, "the example must ship at least one recorded run"
    return runs


@pytest.mark.parametrize("run_dir", recorded_dirs(), ids=lambda path: path.name)
def test_producer_identity_describes_the_recorded_lock(run: ModuleType, run_dir: Path) -> None:
    producer = run.load_producer(run_dir)
    lock = parse_lock((run_dir / "lock.json").read_text(encoding="utf-8"))
    assert lock.sha256 == producer.lock_sha256
    assert lock.implementation_sha256 == producer.implementation_sha256
    assert lock.replay_engine_version == producer.replay_engine_version in SUPPORTED_ENGINES
    assert run_dir.name == producer.implementation_sha256[: len(run_dir.name)]
    assert (run_dir / "lock.json").read_bytes() == (run_dir / "evidence" / "lock.json").read_bytes()
    assert sorted(p.name for p in (run_dir / "evidence").iterdir()) == sorted(BUNDLE_FILES)
    assert sorted(p.name for p in run_dir.iterdir()) == ["PRODUCER.json", "evidence", "lock.json"]
    assert len(producer.source_commit) == 40
    raw = read_json(run_dir / "PRODUCER.json")
    assert "synthetic" in str(raw["note"])
    assert "no model, key or network" in str(raw["note"])


@pytest.mark.parametrize("run_dir", recorded_dirs(), ids=lambda path: path.name)
def test_recorded_inputs_are_the_committed_authored_inputs(run: ModuleType, run_dir: Path) -> None:
    producer = run.load_producer(run_dir)
    assert producer.inputs == run.input_hashes()
    files = read_bundle_files(run_dir / "evidence")
    assert sha256_hex(files["calibration.jsonl"]) == dict(producer.inputs)["calibration.jsonl"]
    assert sha256_hex(files["verification.jsonl"]) == dict(producer.inputs)["verification.jsonl"]
    assert b"expected_label" not in files["records.jsonl"]
    assert b"expected_label" not in files["faults.jsonl"]


@pytest.mark.parametrize("run_dir", recorded_dirs(), ids=lambda path: path.name)
def test_recorded_records_faults_and_verdict_reproduce_from_the_inputs(
    run: ModuleType, run_dir: Path, fresh: Any
) -> None:
    recorded = read_bundle_files(run_dir / "evidence")
    fresh_files = read_bundle_files(fresh.bundle_path)
    assert recorded["records.jsonl"] == fresh_files["records.jsonl"]
    assert recorded["faults.jsonl"] == fresh_files["faults.jsonl"]
    recorded_verdict = decode_document("verdict.json", recorded["verdict.json"], Verdict)
    assert replace(recorded_verdict, lock_sha256=fresh.lock.sha256) == fresh.replayed
    assert recorded_verdict.status == run.load_producer(run_dir).verdict_status


@pytest.mark.parametrize("run_dir", recorded_dirs(), ids=lambda path: path.name)
def test_archived_contract_and_fixture_identity_are_the_frozen_ones(run_dir: Path) -> None:
    lock = parse_lock((run_dir / "lock.json").read_text(encoding="utf-8"))
    assert lock.contract == parse_contract(EXAMPLE_DIR / "contract.toml")
    assert lock.model_identity == FixtureModel(EXAMPLE_DIR / "responses.jsonl").identity()


@pytest.mark.parametrize("run_dir", recorded_dirs(), ids=lambda path: path.name)
def test_every_active_recorded_run_replays_to_its_archived_verdict(
    run: ModuleType, run_dir: Path
) -> None:
    """V1-020: core replay owns general validation; each active archive must replay non-ERROR.

    A run whose producer is neither the running implementation nor a
    registry-approved pair fails here. That is the intended signal: record a
    separately identified fresh run with ``run.py --record`` or obtain a
    reviewed compatibility decision; never edit, reseal or move the archive.
    """
    producer = run.load_producer(run_dir)
    recorded = decode_document(
        "verdict.json", read_bundle_files(run_dir / "evidence")["verdict.json"], Verdict
    )
    replayed = replay(run_dir / "evidence", expected_lock_sha256=producer.lock_sha256)
    assert replayed.status != "ERROR", (run_dir.name, replayed.reasons)
    assert replayed == recorded, run_dir.name
    validate_lock(parse_lock((run_dir / "lock.json").read_text(encoding="utf-8")))
    if producer.implementation_sha256 != implementation_fingerprint():
        # Only a reviewed registry entry on both sides can make this pass.
        assert producer.replay_engine_version in SUPPORTED_ENGINES
