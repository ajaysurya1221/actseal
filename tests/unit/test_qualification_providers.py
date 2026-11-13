"""Qualification uses every provider through the existing collection protocol.

Fixture/recorded use local files, Laya uses the conformance fake worker and
the two HTTP providers use fake stdlib connections. No model or network call.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from actseal.adapters.base import DecisionModel
from actseal.contract import parse_cases, parse_contract, read_input_text
from actseal.qualification import qualify_run, replay_selection
from actseal.replay import replay
from provider_support import PROFILE_NAMES, build_profile

PACKAGED = Path(__file__).resolve().parents[2] / "src" / "actseal" / "demo_data"


@pytest.mark.parametrize("profile_name", PROFILE_NAMES)
@pytest.mark.parametrize("selected", [True, False], ids=["selected", "no-threshold"])
def test_every_provider_keeps_selection_separate_from_verification(
    profile_name: str, selected: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile = build_profile(profile_name, tmp_path, monkeypatch)
    contract_path = PACKAGED / "qualify.toml"
    calibration_path = PACKAGED / "qualify_calibration.jsonl"
    verification_path = PACKAGED / "qualify_verification.jsonl"
    contract = parse_contract(contract_path)
    calibration = parse_cases(read_input_text(calibration_path), contract.question)
    verification = parse_cases(read_input_text(verification_path), contract.question)
    case_ids = tuple(case.case_id for case in (*calibration, *verification))
    opened: list[DecisionModel] = []

    def factory() -> DecisionModel:
        model = profile.open(body=profile.valid_raw_body(contract.question), case_ids=case_ids)
        opened.append(model)
        return model

    provider = profile_name.removesuffix("-fake")
    result = qualify_run(
        contract_path,
        calibration_path,
        verification_path,
        tmp_path / "qualified",
        provider=provider,
        model_factory=factory,
        grid=(0.5, 1.0) if selected else (1.0,),
    )
    assert replay_selection(result.destination / "calibration") == result.calibration.selection
    if not selected:
        assert result.calibration.selection.reason == "calibration.no_threshold"
        assert result.calibration.selection.threshold is None
        assert result.bundle is None
        assert result.lock is None
        assert result.receipt_path is None
        assert not (result.destination / "evidence").exists()
        assert not (result.destination / "contract.toml").exists()
        assert len(opened) == 1
        if provider in {"laya", "jev", "decision-api"}:
            assert profile.requests_sent(opened[0]) == 64
        return
    assert result.calibration.selection.threshold == 0.5
    assert result.lock is not None
    assert result.lock.model_identity.provider == provider
    assert result.bundle is not None
    assert result.bundle.verdict.status == "PASS"
    assert (
        result.bundle.verdict.total,
        result.bundle.verdict.accepted,
        result.bundle.verdict.errors,
    ) == (100, 100, 0)
    assert tuple(record.case_id for record in result.bundle.records) == tuple(
        case.case_id for case in verification
    )
    assert len(result.bundle.faults) == 6
    assert all(
        fault.decision.action == spec.expected_action
        for fault, spec in zip(result.bundle.faults, result.lock.fault_inventory, strict=True)
    )
    if provider == "recorded":
        assert "scope.recorded_provider_faults_not_tested" in result.bundle.verdict.reasons
        assert all(
            "recorded: provider faults not tested" in record.capture.warnings
            for record in result.bundle.records
        )
    elif provider in {"laya", "jev", "decision-api"}:
        assert [profile.requests_sent(model) for model in opened] == [64, 0, 100]
    assert result.bundle_path is not None
    assert replay(result.bundle_path) == result.bundle.verdict
