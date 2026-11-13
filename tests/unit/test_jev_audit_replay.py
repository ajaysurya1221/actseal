"""Golden replay regression test for the retained jev-audit evidence archive.

Models ``tests/examples/test_recorded.py::
test_every_active_recorded_run_replays_to_its_archived_verdict`` for the
``docs/results/jev-audit-2026-10-08/evidence`` archive: a real bundle whose
producer -- the unreleased benchmark snapshot
``d3edbab2dfbd44a0e9e272e1671143517832e3b4`` -- is not the running
implementation. Before plan/v2 M2 this producer fingerprint was registered for
no engine, so replay with the packaged registry returned ERROR
``integrity.lock`` (as the archive's own README documented at publication).
M2 registered it (and the resulting running fingerprint) for
``actseal-choice-v1``, so dual registration now makes it replay, offline and
with no model or network call, to its recorded INCONCLUSIVE verdict. This test
never writes to the archive; it only reads the committed bytes.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from actseal.compatibility import SUPPORTED_ENGINES
from actseal.evidence import BUNDLE_FILES, decode_document, read_bundle_files
from actseal.locking import parse_lock, validate_lock
from actseal.records import Verdict
from actseal.replay import replay
from actseal.serialization import implementation_fingerprint

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_DIR = ROOT / "docs" / "results" / "jev-audit-2026-10-08"
EVIDENCE = ARCHIVE_DIR / "evidence"

#: Producer of this archive: the unreleased benchmark snapshot identified in the
#: archive's own README, not the running implementation of this (or any released)
#: actseal tree.
PRODUCER_FINGERPRINT = "167038cb709ff839f26a21ef55cc63ebd988d797ac56e82d0227ecad1a08eb7c"
#: External lock digest recorded in the archive's README and `inputs/preregistration.json`.
EXTERNAL_LOCK_SHA256 = "e901ad5ebdfdb2b81b97517a72b320eb29cda1588c2b7496e4cc43091034a87a"
#: Recorded result (archive README "Results" table): 639 scheduled/captured verification
#: cases, 580 accepted (ACT) actions, 24 of them wrong.
RECORDED_TOTAL, RECORDED_ACCEPTED, RECORDED_ERRORS = 639, 580, 24


@pytest.fixture
def before_bytes() -> dict[str, bytes]:
    return {name: (EVIDENCE / name).read_bytes() for name in BUNDLE_FILES}


def test_archive_exists_and_is_a_foreign_but_registry_approved_producer() -> None:
    assert EVIDENCE.is_dir(), "the jev-audit example must ship its evidence bundle"
    lock = parse_lock((EVIDENCE / "lock.json").read_text(encoding="utf-8"))
    assert lock.implementation_sha256 == PRODUCER_FINGERPRINT
    assert lock.implementation_sha256 != implementation_fingerprint()
    assert lock.replay_engine_version in SUPPORTED_ENGINES
    assert lock.sha256 == EXTERNAL_LOCK_SHA256
    validate_lock(lock)  # dual registration through the real packaged registry


def test_jev_audit_evidence_replays_to_its_recorded_inconclusive_verdict(
    before_bytes: dict[str, bytes],
) -> None:
    recorded = decode_document("verdict.json", read_bundle_files(EVIDENCE)["verdict.json"], Verdict)
    assert recorded.status == "INCONCLUSIVE"
    assert recorded.reasons == ("evidence.insufficient",)
    assert recorded.lock_sha256 == EXTERNAL_LOCK_SHA256
    assert (recorded.total, recorded.accepted, recorded.errors) == (
        RECORDED_TOTAL,
        RECORDED_ACCEPTED,
        RECORDED_ERRORS,
    )

    replayed = replay(EVIDENCE, expected_lock_sha256=EXTERNAL_LOCK_SHA256)
    assert replayed.status != "ERROR", replayed.reasons
    assert replayed == recorded
    assert replayed.status == "INCONCLUSIVE"
    assert (replayed.total, replayed.accepted, replayed.errors) == (
        RECORDED_TOTAL,
        RECORDED_ACCEPTED,
        RECORDED_ERRORS,
    )

    # Replay never writes to the archive: every bundle file is byte-identical after.
    after_bytes = {name: (EVIDENCE / name).read_bytes() for name in BUNDLE_FILES}
    assert after_bytes == before_bytes


def test_replay_without_an_expected_lock_sha256_agrees(before_bytes: dict[str, bytes]) -> None:
    replayed = replay(EVIDENCE)
    assert replayed.status == "INCONCLUSIVE"
    assert replayed.lock_sha256 == EXTERNAL_LOCK_SHA256
    after_bytes = {name: (EVIDENCE / name).read_bytes() for name in BUNDLE_FILES}
    assert after_bytes == before_bytes
