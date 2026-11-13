"""Direct unit coverage for ``qualification.load_qualification_evidence``.

The report command used to re-derive its qualification linkage checks inline
in ``cli.py``, which sat outside the implementation fingerprint. Those checks
now live in ``load_qualification_evidence`` itself, so these tests call it
directly -- no CLI involved -- and prove it still rejects tampered evidence.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from test_qualification import inputs

from actseal.adapters.fixture import FixtureModel
from actseal.errors import IntegrityError
from actseal.qualification import load_qualification_evidence, qualify_run
from actseal.serialization import canonical_json, to_data


def test_load_qualification_evidence_accepts_a_genuine_root(tmp_path: Path) -> None:
    contract, cal, ver, responses = inputs(tmp_path)
    destination = tmp_path / "qualification"
    result = qualify_run(
        contract,
        cal,
        ver,
        destination,
        provider="fixture",
        model_factory=lambda: FixtureModel(responses),
    )
    assert result.bundle is not None
    evidence = load_qualification_evidence(destination, tmp_path / "report")
    assert evidence.lock == result.lock
    assert evidence.verdict == result.bundle.verdict
    assert evidence.selection == result.calibration.selection
    assert result.lock is not None
    assert evidence.calibration_total == len(result.lock.calibration_inventory)


def test_rejects_sidecar_calibration_hash_mismatch(tmp_path: Path) -> None:
    """Tampering the sidecar's calibration.jsonl without its declared hash is rejected."""
    contract, cal, ver, responses = inputs(tmp_path)
    destination = tmp_path / "qualification"
    result = qualify_run(
        contract,
        cal,
        ver,
        destination,
        provider="fixture",
        model_factory=lambda: FixtureModel(responses),
    )
    assert result.bundle is not None
    sidecar_calibration = destination / "calibration" / "calibration.jsonl"
    sidecar_calibration.write_bytes(sidecar_calibration.read_bytes() + b" ")
    with pytest.raises(IntegrityError):
        load_qualification_evidence(destination, tmp_path / "report")


def test_rejects_selection_threshold_differing_from_lock_threshold(tmp_path: Path) -> None:
    """A lock swapped in from a different (differently thresholded) run is rejected.

    Both runs share identical contract/calibration/verification bytes and the
    same fixture responses, so every other selection-plan/lock field (the
    calibration and verification hashes, the model identity, ``n_verify``, the
    implementation hash) stays identical between them; only the threshold
    chosen by selection differs, because run ``b`` is calibrated against a
    single-point grid that excludes the ``a`` run's chosen threshold.
    """
    root = tmp_path / "shared"
    root.mkdir()
    contract, cal, ver, responses = inputs(root)

    def model_factory() -> FixtureModel:
        return FixtureModel(responses)

    destination_a = tmp_path / "a"
    result_a = qualify_run(
        contract, cal, ver, destination_a, provider="fixture", model_factory=model_factory
    )
    destination_b = tmp_path / "b"
    result_b = qualify_run(
        contract,
        cal,
        ver,
        destination_b,
        provider="fixture",
        model_factory=model_factory,
        grid=(0.9,),
    )
    assert result_a.bundle is not None
    assert result_b.bundle is not None
    assert result_a.lock is not None
    assert result_b.lock is not None
    assert result_a.calibration.selection.threshold == 0.95
    assert result_b.calibration.selection.threshold == 0.9
    assert result_a.calibration.selection.threshold != result_b.calibration.selection.threshold

    # Every other linkage field is identical between the two runs: swapping in
    # b's lock and evidence isolates the threshold mismatch as the one check
    # that trips.
    assert result_a.lock.calibration_sha256 == result_b.lock.calibration_sha256
    assert result_a.lock.verification_sha256 == result_b.lock.verification_sha256
    assert result_a.lock.model_identity == result_b.lock.model_identity
    assert len(result_a.lock.verification_cases) == len(result_b.lock.verification_cases)
    assert result_a.lock.implementation_sha256 == result_b.lock.implementation_sha256

    shutil.rmtree(destination_a / "evidence")
    shutil.copytree(destination_b / "evidence", destination_a / "evidence")
    (destination_a / "lock.json").write_bytes((destination_b / "lock.json").read_bytes())

    receipt_path = destination_a / "qualification.json"
    receipt = json.loads(receipt_path.read_bytes())
    receipt["lock_sha256"] = result_b.lock.sha256
    receipt["verdict"] = to_data(result_b.bundle.verdict)
    receipt_path.write_bytes(canonical_json(receipt) + b"\n")

    with pytest.raises(IntegrityError, match="selection plan does not match"):
        load_qualification_evidence(destination_a, tmp_path / "report")
