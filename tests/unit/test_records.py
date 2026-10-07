"""Direct-constructor validation, immutability and local invariants of every record."""

from __future__ import annotations

import dataclasses
import math
from collections.abc import Callable
from typing import Any

import pytest

from actseal.errors import ActsealError, SchemaError
from actseal.records import (
    Case,
    CaseRef,
    ChoiceAnswer,
    ChoiceQuestion,
    Contract,
    DecisionRecord,
    FaultSpec,
    GateLimits,
    Interval,
    LockedPolicy,
    ModelIdentity,
    Option,
    PolicyDecision,
    ProviderFailure,
    Verdict,
)
from conftest import (
    HEX_0,
    HEX_1,
    HEX_A,
    HEX_B,
    HEX_C,
    HEX_D,
    HEX_E,
    HEX_F,
    SAMPLE_BUILDERS,
    make_answer,
    make_bundle,
    make_capture,
    make_case,
    make_contract,
    make_decision,
    make_fault_result,
    make_fault_spec,
    make_identity,
    make_limits,
    make_lock,
    make_policy,
    make_question,
    make_record,
    make_request,
    make_verdict,
)

RECORD_NAMES = sorted(SAMPLE_BUILDERS)


def _replace(record: Any, **changes: Any) -> Any:
    """Rebuild ``record`` through its constructor with ``changes`` applied."""
    return dataclasses.replace(record, **changes)


def _build(record_type: Callable[..., Any], *args: Any) -> Any:
    """Call a constructor with deliberately ill-typed runtime inputs."""
    return record_type(*args)


# --------------------------------------------------------------------------- #
# Construction and immutability
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name", RECORD_NAMES)
def test_every_record_constructs_and_is_frozen(name: str) -> None:
    record = SAMPLE_BUILDERS[name]()
    assert type(record).__name__ == name
    first_field = dataclasses.fields(record)[0].name
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(record, first_field, getattr(record, first_field))
    with pytest.raises(dataclasses.FrozenInstanceError):
        delattr(record, first_field)


@pytest.mark.parametrize("name", RECORD_NAMES)
def test_every_record_is_recursively_immutable(name: str) -> None:
    def check(value: object, path: str) -> None:
        if dataclasses.is_dataclass(value) and not isinstance(value, type):
            for field in dataclasses.fields(value):
                check(getattr(value, field.name), f"{path}.{field.name}")
        elif isinstance(value, tuple):
            for index, item in enumerate(value):
                check(item, f"{path}[{index}]")
        else:
            assert isinstance(value, str | int | float | bool | type(None)), path

    check(SAMPLE_BUILDERS[name](), name)


def test_constructor_field_order_matches_contract() -> None:
    expected = {
        "Option": ("label", "description"),
        "ChoiceQuestion": ("question_id", "instructions", "options"),
        "Case": ("case_id", "state", "expected_label"),
        "CaseRef": ("case_id", "sha256"),
        "ModelIdentity": (
            "provider",
            "model",
            "revision",
            "artifact_hashes",
            "adapter_version",
            "normalizer_version",
            "runtime",
        ),
        "DecisionRequest": ("case_id", "state", "question"),
        "CapturedOutcome": (
            "request_sha256",
            "identity",
            "body_json",
            "failure_code",
            "warnings",
            "fallback_used",
        ),
        "ChoiceAnswer": (
            "choice",
            "probabilities",
            "selected_probability",
            "provider_confidence",
            "warnings",
            "fallback_used",
        ),
        "ProviderFailure": ("code", "warnings", "fallback_used"),
        "LockedPolicy": ("known_labels", "allowed_labels", "threshold"),
        "GateLimits": ("max_risk", "min_coverage", "alpha"),
        "Contract": (
            "schema_version",
            "name",
            "question",
            "policy",
            "limits",
            "evidence_scope",
            "population",
        ),
        "FaultSpec": ("scenario_id", "kind", "expected_action"),
        "PlanLock": (
            "schema_version",
            "contract",
            "model_identity",
            "calibration_sha256",
            "verification_sha256",
            "calibration_inventory",
            "verification_inventory",
            "verification_cases",
            "fault_inventory",
            "implementation_sha256",
            "sha256",
            "replay_engine_version",
        ),
        "PolicyDecision": ("action", "choice", "reason", "fallback_used"),
        "DecisionRecord": ("case_id", "capture", "outcome", "decision"),
        "FaultResult": ("scenario_id", "request", "capture", "outcome", "decision"),
        "Interval": ("lower", "upper"),
        "Verdict": (
            "status",
            "reasons",
            "total",
            "accepted",
            "errors",
            "risk",
            "coverage",
            "evidence_scope",
            "lock_sha256",
        ),
        "EvidenceBundle": (
            "lock",
            "calibration_jsonl",
            "verification_jsonl",
            "records",
            "faults",
            "verdict",
        ),
    }
    assert set(expected) == set(SAMPLE_BUILDERS)
    for name, fields in expected.items():
        record = SAMPLE_BUILDERS[name]()
        assert tuple(f.name for f in dataclasses.fields(record)) == fields
        assert all(f.default is dataclasses.MISSING for f in dataclasses.fields(record))


def test_error_hierarchy() -> None:
    assert issubclass(SchemaError, ActsealError)
    assert issubclass(ActsealError, Exception)
    with pytest.raises(ActsealError):
        Option("", "x")


# --------------------------------------------------------------------------- #
# Defensive copies: caller-owned containers never alias record state
# --------------------------------------------------------------------------- #


def test_mutating_source_list_does_not_change_question() -> None:
    options: Any = [Option("a", "A"), Option("b", "B")]
    question = ChoiceQuestion("q", "pick", options)
    options.append(Option("c", "C"))
    options[0] = Option("z", "Z")
    assert question.options == (Option("a", "A"), Option("b", "B"))
    assert isinstance(question.options, tuple)


def test_mutating_source_pairs_does_not_change_identity() -> None:
    artifacts: Any = [["weights", HEX_A]]
    runtime: Any = [["os", "linux"], ["python", "3.12"]]
    identity = ModelIdentity("laya", "m", "rev", artifacts, "1", "1", runtime)
    artifacts[0][1] = HEX_B
    artifacts.append(["extra", HEX_C])
    runtime.clear()
    assert identity.artifact_hashes == (("weights", HEX_A),)
    assert identity.runtime == (("os", "linux"), ("python", "3.12"))
    assert all(isinstance(pair, tuple) for pair in identity.artifact_hashes)


def test_runtime_and_artifact_maps_are_sorted_by_key() -> None:
    identity = _build(
        ModelIdentity,
        "laya",
        "m",
        "rev",
        [["b", HEX_B], ["a", HEX_A]],
        "1",
        "1",
        [["z", "1"], ["y", "2"]],
    )
    assert identity.artifact_hashes == (("a", HEX_A), ("b", HEX_B))
    assert identity.runtime == (("y", "2"), ("z", "1"))


def test_mutating_source_probabilities_and_warnings_does_not_change_answer() -> None:
    probabilities: Any = [["a", 0.5], ["b", 0.5]]
    warnings: Any = ["w"]
    answer = ChoiceAnswer("a", probabilities, 0.5, None, warnings, False)
    probabilities[0][1] = 0.0
    warnings.append("extra")
    assert answer.probabilities == (("a", 0.5), ("b", 0.5))
    assert answer.warnings == ("w",)


def test_probabilities_preserve_given_order() -> None:
    answer = ChoiceAnswer("b", (("b", 0.3), ("a", 0.7)), 0.3, None, (), False)
    assert answer.probabilities == (("b", 0.3), ("a", 0.7))


@pytest.mark.parametrize("bad", ["ab", b"ab", {"a": 1}, {"a", "b"}, iter(["a", "b"]), 3])
def test_strings_and_other_iterables_are_rejected_as_sequences(bad: Any) -> None:
    with pytest.raises(SchemaError, match="known_labels"):
        LockedPolicy(bad, ("a",), 0.5)
    with pytest.raises(SchemaError, match="warnings"):
        ProviderFailure("timeout", bad, False)


def test_integer_inputs_are_normalized_to_float() -> None:
    limits = GateLimits(0, 1, 0.5)
    assert limits.max_risk == 0.0
    assert type(limits.max_risk) is float
    assert type(limits.min_coverage) is float


# --------------------------------------------------------------------------- #
# Domain validation for every record
# --------------------------------------------------------------------------- #

NAN = float("nan")
INF = float("inf")

BAD_CONSTRUCTIONS: list[tuple[str, Any, str]] = [
    ("Option empty label", lambda: Option("", "d"), "label"),
    ("Option empty description", lambda: Option("l", ""), "description"),
    ("Option non-string", lambda: _build(Option, 1, "d"), "label"),
    ("Question empty id", lambda: _replace(make_question(), question_id=""), "question_id"),
    (
        "Question empty instructions",
        lambda: _replace(make_question(), instructions=""),
        "instructions",
    ),
    (
        "Question one option",
        lambda: _replace(make_question(), options=(Option("a", "A"),)),
        "options",
    ),
    (
        "Question 17 options",
        lambda: _replace(make_question(), options=tuple(Option(str(i), "d") for i in range(17))),
        "options",
    ),
    (
        "Question duplicate labels",
        lambda: _replace(make_question(), options=(Option("a", "A"), Option("a", "B"))),
        "options",
    ),
    (
        "Question option wrong type",
        lambda: _replace(make_question(), options=("a", "b")),
        "options",
    ),
    ("Case empty id", lambda: _replace(make_case(), case_id=""), "case_id"),
    ("Case empty state", lambda: _replace(make_case(), state=""), "state"),
    ("Case empty label", lambda: _replace(make_case(), expected_label=""), "expected_label"),
    ("CaseRef uppercase hash", lambda: CaseRef("c", HEX_A.upper()), "sha256"),
    ("CaseRef short hash", lambda: CaseRef("c", HEX_A[:63]), "sha256"),
    ("CaseRef non-hex", lambda: CaseRef("c", "g" * 64), "sha256"),
    ("Identity empty provider", lambda: _replace(make_identity(), provider=""), "provider"),
    ("Identity empty revision", lambda: _replace(make_identity(), revision=""), "revision"),
    (
        "Identity artifact non-hash",
        lambda: _replace(make_identity(), artifact_hashes=(("w", "abc"),)),
        "artifact_hashes",
    ),
    (
        "Identity duplicate artifact key",
        lambda: _replace(make_identity(), artifact_hashes=(("w", HEX_A), ("w", HEX_B))),
        "artifact_hashes",
    ),
    (
        "Identity duplicate runtime key",
        lambda: _replace(make_identity(), runtime=(("k", "1"), ("k", "2"))),
        "runtime",
    ),
    (
        "Identity runtime triple",
        lambda: _replace(make_identity(), runtime=(("k", "1", "2"),)),
        "runtime",
    ),
    (
        "Identity runtime non-string",
        lambda: _replace(make_identity(), runtime=(("k", 1),)),
        "runtime",
    ),
    ("Request empty state", lambda: _replace(make_request(), state=""), "state"),
    ("Request wrong question", lambda: _replace(make_request(), question="q"), "question"),
    (
        "Capture both body and failure",
        lambda: _replace(make_capture(), failure_code="timeout"),
        "body_json/failure_code",
    ),
    (
        "Capture neither body nor failure",
        lambda: _replace(make_capture(), body_json=None),
        "body_json/failure_code",
    ),
    (
        "Capture unknown failure code",
        lambda: _replace(make_capture(failed=True), failure_code="boom"),
        "failure_code",
    ),
    ("Capture bad hash", lambda: _replace(make_capture(), request_sha256="x"), "request_sha256"),
    ("Capture bad identity", lambda: _replace(make_capture(), identity="id"), "identity"),
    ("Capture int fallback", lambda: _replace(make_capture(), fallback_used=1), "fallback_used"),
    ("Capture warnings not seq", lambda: _replace(make_capture(), warnings="w"), "warnings"),
    ("Answer empty choice", lambda: _replace(make_answer(), choice=""), "choice"),
    ("Answer unknown choice", lambda: _replace(make_answer(), choice="other"), "choice"),
    (
        "Answer selected mismatch",
        lambda: _replace(make_answer(), selected_probability=0.5),
        "selected_probability",
    ),
    (
        "Answer probability > 1",
        lambda: ChoiceAnswer("a", (("a", 1.5), ("b", 0.0)), 1.5, None, (), False),
        "probabilities",
    ),
    (
        "Answer negative probability",
        lambda: ChoiceAnswer("a", (("a", -0.5), ("b", 0.0)), -0.5, None, (), False),
        "probabilities",
    ),
    (
        "Answer NaN probability",
        lambda: ChoiceAnswer("a", (("a", NAN), ("b", 0.0)), NAN, None, (), False),
        "probabilities",
    ),
    (
        "Answer bool probability",
        lambda: ChoiceAnswer("a", (("a", True), ("b", 0.0)), 1.0, None, (), False),
        "probabilities",
    ),
    (
        "Answer duplicate labels",
        lambda: ChoiceAnswer("a", (("a", 0.5), ("a", 0.5)), 0.5, None, (), False),
        "probabilities",
    ),
    (
        "Answer single probability",
        lambda: ChoiceAnswer("a", (("a", 1.0),), 1.0, None, (), False),
        "probabilities",
    ),
    (
        "Answer confidence > 1",
        lambda: _replace(make_answer(), provider_confidence=1.5),
        "provider_confidence",
    ),
    (
        "Answer confidence inf",
        lambda: _replace(make_answer(), provider_confidence=INF),
        "provider_confidence",
    ),
    ("Answer fallback str", lambda: _replace(make_answer(), fallback_used="no"), "fallback_used"),
    ("Failure unknown code", lambda: ProviderFailure("oops", (), False), "code"),
    ("Failure empty code", lambda: ProviderFailure("", (), False), "code"),
    (
        "Failure warning non-string",
        lambda: _build(ProviderFailure, "timeout", (1,), False),
        "warnings",
    ),
    ("Failure empty warning", lambda: ProviderFailure("timeout", ("",), False), "warnings"),
    ("Policy no allowed", lambda: _replace(make_policy(), allowed_labels=()), "allowed_labels"),
    (
        "Policy allowed not subset",
        lambda: _replace(make_policy(), allowed_labels=("other",)),
        "allowed_labels",
    ),
    (
        "Policy duplicate allowed",
        lambda: _replace(make_policy(), allowed_labels=("billing", "billing")),
        "allowed_labels",
    ),
    (
        "Policy duplicate known",
        lambda: _replace(make_policy(), known_labels=("billing", "billing")),
        "known_labels",
    ),
    ("Policy one known", lambda: LockedPolicy(("a",), ("a",), 0.5), "known_labels"),
    ("Policy threshold 0", lambda: _replace(make_policy(), threshold=0.0), "threshold"),
    ("Policy threshold > 1", lambda: _replace(make_policy(), threshold=1.01), "threshold"),
    ("Policy threshold bool", lambda: _replace(make_policy(), threshold=True), "threshold"),
    ("Policy threshold NaN", lambda: _replace(make_policy(), threshold=NAN), "threshold"),
    ("Policy threshold str", lambda: _replace(make_policy(), threshold="0.9"), "threshold"),
    ("Limits risk > 1", lambda: _replace(make_limits(), max_risk=1.5), "max_risk"),
    ("Limits risk negative", lambda: _replace(make_limits(), max_risk=-0.1), "max_risk"),
    ("Limits coverage inf", lambda: _replace(make_limits(), min_coverage=INF), "min_coverage"),
    ("Limits alpha too small", lambda: _replace(make_limits(), alpha=1e-7), "alpha"),
    ("Limits alpha 1", lambda: _replace(make_limits(), alpha=1.0), "alpha"),
    ("Limits alpha bool", lambda: _replace(make_limits(), alpha=False), "alpha"),
    ("Contract version 2", lambda: _replace(make_contract(), schema_version=2), "schema_version"),
    (
        "Contract version bool",
        lambda: _replace(make_contract(), schema_version=True),
        "schema_version",
    ),
    (
        "Contract version str",
        lambda: _replace(make_contract(), schema_version="1"),
        "schema_version",
    ),
    ("Contract empty name", lambda: _replace(make_contract(), name=""), "name"),
    (
        "Contract bad scope",
        lambda: _replace(make_contract(), evidence_scope="prod"),
        "evidence_scope",
    ),
    ("Contract empty population", lambda: _replace(make_contract(), population=""), "population"),
    (
        "Contract policy labels mismatch",
        lambda: _replace(
            make_contract(), policy=LockedPolicy(("billing", "sales"), ("billing",), 0.9)
        ),
        "policy.known_labels",
    ),
    (
        "Contract policy label order",
        lambda: _replace(
            make_contract(),
            policy=LockedPolicy(("sales", "technical", "billing"), ("billing",), 0.9),
        ),
        "policy.known_labels",
    ),
    ("Contract wrong question", lambda: _replace(make_contract(), question=None), "question"),
    ("Contract wrong policy", lambda: _replace(make_contract(), policy={}), "policy"),
    ("Contract wrong limits", lambda: _replace(make_contract(), limits=()), "limits"),
    (
        "FaultSpec bad action",
        lambda: _build(FaultSpec, "fault.x", "x", "ALLOW"),
        "expected_action",
    ),
    (
        "FaultSpec lowercase action",
        lambda: _build(FaultSpec, "fault.x", "x", "act"),
        "expected_action",
    ),
    ("FaultSpec empty kind", lambda: FaultSpec("fault.x", "", "ACT"), "kind"),
    ("Lock version 0", lambda: _replace(make_lock(), schema_version=0), "schema_version"),
    ("Lock version 1", lambda: _replace(make_lock(), schema_version=1), "schema_version"),
    (
        "Lock empty engine",
        lambda: _replace(make_lock(), replay_engine_version=""),
        "replay_engine_version",
    ),
    (
        "Lock engine not text",
        lambda: _replace(make_lock(), replay_engine_version=1),
        "replay_engine_version",
    ),
    ("Lock bad hash", lambda: _replace(make_lock(), sha256="deadbeef"), "sha256"),
    (
        "Lock bad implementation hash",
        lambda: _replace(make_lock(), implementation_sha256=""),
        "implementation_sha256",
    ),
    (
        "Lock empty calibration inventory",
        lambda: _replace(make_lock(), calibration_inventory=()),
        "calibration_inventory",
    ),
    (
        "Lock duplicate calibration ids",
        lambda: _replace(
            make_lock(), calibration_inventory=(CaseRef("c-001", HEX_E), CaseRef("c-001", HEX_F))
        ),
        "calibration_inventory",
    ),
    (
        "Lock verification cases count mismatch",
        lambda: _replace(make_lock(), verification_cases=()),
        "verification_cases",
    ),
    (
        "Lock verification cases id mismatch",
        lambda: _replace(make_lock(), verification_cases=(Case("v-999", "s", "billing"),)),
        "verification_cases",
    ),
    (
        "Lock verification case unknown label",
        lambda: _replace(make_lock(), verification_cases=(Case("v-001", "s", "legal"),)),
        "verification_cases",
    ),
    (
        "Lock duplicate fault ids",
        lambda: _replace(make_lock(), fault_inventory=(make_fault_spec(), make_fault_spec())),
        "fault_inventory",
    ),
    ("Lock wrong contract", lambda: _replace(make_lock(), contract="c"), "contract"),
    ("Lock wrong identity", lambda: _replace(make_lock(), model_identity=None), "model_identity"),
    (
        "Lock inventory wrong type",
        lambda: _replace(make_lock(), verification_inventory=(make_case(),)),
        "verification_inventory",
    ),
    ("Decision bad action", lambda: _build(PolicyDecision, "ALLOW", "a", "r", False), "action"),
    ("Decision ACT without choice", lambda: PolicyDecision("ACT", None, "r", False), "choice"),
    ("Decision ABSTAIN with choice", lambda: PolicyDecision("ABSTAIN", "a", "r", False), "choice"),
    ("Decision empty reason", lambda: PolicyDecision("DENY", None, "", False), "reason"),
    (
        "Decision fallback int",
        lambda: _build(PolicyDecision, "DENY", None, "r", 0),
        "fallback_used",
    ),
    ("Record empty id", lambda: _replace(make_record(), case_id=""), "case_id"),
    ("Record wrong capture", lambda: _replace(make_record(), capture=None), "capture"),
    ("Record wrong outcome", lambda: _replace(make_record(), outcome="answer"), "outcome"),
    ("Record wrong decision", lambda: _replace(make_record(), decision="ACT"), "decision"),
    (
        "Record answer without body",
        lambda: _replace(make_record(), capture=make_capture(failed=True)),
        "outcome",
    ),
    (
        "Record fallback mismatch",
        lambda: _replace(make_record(), decision=PolicyDecision("ESCALATE", None, "r", True)),
        "decision.fallback_used",
    ),
    ("FaultResult empty id", lambda: _replace(make_fault_result(), scenario_id=""), "scenario_id"),
    ("FaultResult wrong request", lambda: _replace(make_fault_result(), request="r"), "request"),
    ("Interval lower > upper", lambda: Interval(0.6, 0.5), "lower"),
    ("Interval upper > 1", lambda: Interval(0.0, 1.5), "upper"),
    ("Interval negative", lambda: Interval(-0.1, 0.5), "lower"),
    ("Interval nan", lambda: Interval(NAN, 0.5), "lower"),
    ("Interval bool", lambda: Interval(False, True), "lower"),
    ("Verdict bad status", lambda: _replace(make_verdict(), status="OK"), "status"),
    ("Verdict unsorted reasons", lambda: _replace(make_verdict(), reasons=("b", "a")), "reasons"),
    ("Verdict duplicate reasons", lambda: _replace(make_verdict(), reasons=("a", "a")), "reasons"),
    ("Verdict negative total", lambda: _replace(make_verdict(), total=-1), "total"),
    ("Verdict accepted > total", lambda: _replace(make_verdict(), accepted=2), "accepted"),
    ("Verdict errors > accepted", lambda: _replace(make_verdict(), errors=2), "errors"),
    ("Verdict bool total", lambda: _replace(make_verdict(), total=True), "total"),
    ("Verdict float total", lambda: _replace(make_verdict(), total=1.0), "total"),
    ("Verdict total > 10000", lambda: _replace(make_verdict(), total=10001), "total"),
    ("Verdict wrong risk", lambda: _replace(make_verdict(), risk=(0.0, 1.0)), "risk"),
    (
        "Verdict bad scope",
        lambda: _replace(make_verdict(), evidence_scope="prod"),
        "evidence_scope",
    ),
    ("Verdict bad hash", lambda: _replace(make_verdict(), lock_sha256="x"), "lock_sha256"),
    (
        "Verdict ERROR with counts",
        lambda: Verdict("ERROR", (), 1, 0, 0, Interval(0, 1), Interval(0, 1), "demo", HEX_1),
        "status",
    ),
    (
        "Verdict ERROR with narrow interval",
        lambda: Verdict("ERROR", (), 0, 0, 0, Interval(0, 0.5), Interval(0, 1), "demo", HEX_1),
        "status",
    ),
    (
        "Verdict PASS with zero accepted",
        lambda: _replace(make_verdict(), accepted=0, errors=0),
        "accepted",
    ),
    (
        "Verdict PASS with zero cases",
        lambda: _replace(make_verdict(), total=0, accepted=0, errors=0),
        "total",
    ),
    (
        "Verdict BLOCK with zero cases",
        lambda: Verdict("BLOCK", ("a",), 0, 0, 0, Interval(0, 1), Interval(0, 1), "demo", HEX_1),
        "total",
    ),
    (
        "Verdict INCONCLUSIVE with zero cases",
        lambda: Verdict("INCONCLUSIVE", (), 0, 0, 0, Interval(0, 1), Interval(0, 1), "demo", HEX_1),
        "total",
    ),
    (
        "Identity unknown provider",
        lambda: _replace(make_identity(), provider="unsupported"),
        "provider",
    ),
    (
        "Identity provider wrong case",
        lambda: _replace(make_identity(), provider="Laya"),
        "provider",
    ),
    (
        "Answer zero total mass",
        lambda: ChoiceAnswer("a", (("a", 0.0), ("b", 0.0)), 0.0, None, (), False),
        "probabilities",
    ),
    (
        "Answer total mass two",
        lambda: ChoiceAnswer("a", (("a", 1.0), ("b", 1.0)), 1.0, None, (), False),
        "probabilities",
    ),
    (
        "Answer total mass below one",
        lambda: ChoiceAnswer("a", (("a", 0.5), ("b", 0.4)), 0.5, None, (), False),
        "probabilities",
    ),
    (
        "Answer total mass outside tolerance",
        lambda: ChoiceAnswer("a", (("a", 0.5), ("b", 0.5 + 3e-12)), 0.5, None, (), False),
        "probabilities",
    ),
    ("Limits overflow", lambda: _replace(make_limits(), max_risk=10**400), "max_risk"),
    ("Limits negative overflow", lambda: _replace(make_limits(), alpha=-(10**400)), "alpha"),
    ("Interval overflow", lambda: Interval(0, 10**400), "upper"),
    ("Policy overflow", lambda: _replace(make_policy(), threshold=10**400), "threshold"),
    (
        "Answer overflow probability",
        lambda: ChoiceAnswer("a", (("a", 10**400), ("b", 0.0)), 1.0, None, (), False),
        "probabilities",
    ),
    (
        "Answer overflow confidence",
        lambda: _replace(make_answer(), provider_confidence=10**400),
        "provider_confidence",
    ),
]


def test_probability_mass_tolerance_boundary() -> None:
    within = ChoiceAnswer("a", (("a", 0.5), ("b", 0.5 + 5e-13)), 0.5, None, (), False)
    assert within.probabilities[1][1] == 0.5 + 5e-13
    assert ChoiceAnswer("a", (("a", 1.0), ("b", 0.0)), 1.0, None, (), False).choice == "a"
    assert ChoiceAnswer("b", (("a", 1.0), ("b", 0.0)), 0.0, None, (), False).choice == "b"


def test_supported_providers_are_accepted() -> None:
    assert _replace(make_identity(), provider="fixture").provider == "fixture"
    assert _replace(make_identity(), provider="laya").provider == "laya"


def test_non_error_verdicts_require_cases() -> None:
    block = Verdict("BLOCK", ("a",), 3, 0, 0, Interval(0, 1), Interval(0, 0.7), "demo", HEX_1)
    assert block.accepted == 0
    inconclusive = Verdict(
        "INCONCLUSIVE", (), 1, 1, 1, Interval(0, 1), Interval(0, 1), "demo", HEX_1
    )
    assert inconclusive.total == 1
    with pytest.raises(SchemaError, match="accepted"):
        Verdict("PASS", (), 3, 0, 0, Interval(0, 1), Interval(0, 1), "demo", HEX_1)


def test_overflow_is_a_schema_error_not_overflow_error() -> None:
    with pytest.raises(SchemaError, match="max_risk") as excinfo:
        GateLimits(10**400, 0.5, 0.5)
    assert not isinstance(excinfo.value, OverflowError)
    assert "10" not in str(excinfo.value).split(":", 1)[1]


@pytest.mark.parametrize(("label", "build", "field"), BAD_CONSTRUCTIONS, ids=lambda v: str(v)[:40])
def test_constructors_reject_invalid_domains(label: str, build: Any, field: str) -> None:
    with pytest.raises(SchemaError) as excinfo:
        build()
    assert field in str(excinfo.value), label


def test_verdict_error_shape_is_accepted() -> None:
    verdict = Verdict(
        "ERROR", ("integrity.lock",), 0, 0, 0, Interval(0, 1), Interval(0, 1), "demo", HEX_1
    )
    assert verdict.total == 0
    assert verdict.risk == Interval(0.0, 1.0)


def test_bundle_invariants() -> None:
    bundle = make_bundle()
    assert bundle.verdict.lock_sha256 == bundle.lock.sha256
    with pytest.raises(SchemaError, match="records"):
        _replace(bundle, records=())
    with pytest.raises(SchemaError, match="records"):
        _replace(bundle, records=(_replace(make_record(), case_id="v-002"),))
    with pytest.raises(SchemaError, match="faults"):
        _replace(bundle, faults=(make_fault_result(),))
    with pytest.raises(SchemaError, match=r"verdict\.lock_sha256"):
        _replace(bundle, verdict=_replace(make_verdict(), lock_sha256=HEX_0))
    with pytest.raises(SchemaError, match=r"verdict\.evidence_scope"):
        _replace(bundle, verdict=_replace(make_verdict(), evidence_scope="iid"))
    with pytest.raises(SchemaError, match="calibration_jsonl"):
        _replace(bundle, calibration_jsonl="")
    with pytest.raises(SchemaError, match="lock"):
        _replace(bundle, lock=None)


def test_lock_accepts_matching_inventories() -> None:
    lock = make_lock()
    assert lock.verification_cases[0].case_id == lock.verification_inventory[0].case_id
    assert lock.calibration_sha256 == HEX_C
    assert lock.verification_sha256 == HEX_D


def test_capture_allows_empty_and_malformed_body() -> None:
    capture = _replace(make_capture(), body_json="{not json")
    assert capture.body_json == "{not json"
    assert _replace(make_capture(), body_json="").body_json == ""


def test_provider_failure_with_body_is_valid_evidence() -> None:
    record = DecisionRecord(
        "v-001",
        make_capture(),
        ProviderFailure("malformed_response", ("w",), False),
        PolicyDecision("ESCALATE", None, "provider.malformed_response", False),
    )
    assert record.capture.body_json is not None


def test_error_messages_do_not_echo_values() -> None:
    sentinel = "sk-very-sensitive-value"
    with pytest.raises(SchemaError) as excinfo:
        CaseRef("case", sentinel)
    assert sentinel not in str(excinfo.value)
    with pytest.raises(SchemaError) as excinfo:
        ProviderFailure(sentinel, (), False)
    assert sentinel not in str(excinfo.value)
    with pytest.raises(SchemaError) as excinfo:
        _build(Contract, 1, "n", make_question(), make_policy(), make_limits(), sentinel, "p")
    assert sentinel not in str(excinfo.value)


LONE_SURROGATES = ("\ud800", "\udfff", "ok\ud83d", "\ude00tail", "mid\udc00dle")


@pytest.mark.parametrize("bad", LONE_SURROGATES)
def test_string_fields_reject_unpaired_surrogates_at_construction(bad: str) -> None:
    sentinel_free = "\\u" not in bad
    assert sentinel_free
    cases: list[tuple[str, Any]] = [
        ("label", lambda: Option(bad, "d")),
        ("description", lambda: Option("l", bad)),
        ("question_id", lambda: _replace(make_question(), question_id=bad)),
        ("state", lambda: _replace(make_case(), state=bad)),
        ("revision", lambda: _replace(make_identity(), revision=bad)),
        ("body_json", lambda: _replace(make_capture(), body_json=bad)),
        ("warnings[0]", lambda: _replace(make_capture(), warnings=(bad,))),
        ("choice", lambda: _replace(make_decision(), choice=bad)),
        ("reason", lambda: _replace(make_decision(), reason=bad)),
        ("known_labels[0]", lambda: LockedPolicy((bad, "b"), ("b",), 0.5)),
        ("runtime[0].key", lambda: _replace(make_identity(), runtime=((bad, "v"),))),
        ("runtime[0].value", lambda: _replace(make_identity(), runtime=(("k", bad),))),
        (
            "artifact_hashes[0].key",
            lambda: _replace(make_identity(), artifact_hashes=((bad, HEX_A),)),
        ),
        (
            "probabilities[0].label",
            lambda: ChoiceAnswer("b", ((bad, 0.0), ("b", 1.0)), 1.0, None, (), False),
        ),
        ("population", lambda: _replace(make_contract(), population=bad)),
        ("calibration_jsonl", lambda: _replace(make_bundle(), calibration_jsonl=bad)),
        ("reasons[0]", lambda: _replace(make_verdict(), reasons=(bad,))),
    ]
    for field, build in cases:
        with pytest.raises(SchemaError, match="Unicode") as excinfo:
            build()
        message = str(excinfo.value)
        assert message.startswith(field), field
        assert bad not in message
        assert message.isascii()


def test_valid_non_ascii_strings_are_preserved() -> None:
    text = "café ☃ \U0001f600 Ж א ก"
    option = Option(text, "\U0001f600")
    assert option.label == text
    case = _replace(make_case(), state=text)
    assert case.state == text
    capture = _replace(make_capture(), body_json=text, warnings=(text,))
    assert capture.body_json == text
    assert capture.warnings == (text,)
    identity = _replace(make_identity(), runtime=((text, text),))
    assert identity.runtime == ((text, text),)


def test_decision_record_equality_and_hash() -> None:
    assert make_record() == make_record()
    assert hash(make_record()) == hash(make_record())
    assert make_record() != _replace(make_record(), case_id="v-002")


def test_question_labels_property() -> None:
    assert make_question().labels == ("billing", "technical", "sales")


def test_sample_decision_values_are_finite() -> None:
    answer = make_answer()
    assert math.isfinite(answer.selected_probability)
    assert make_decision().choice == answer.choice
    assert HEX_B != HEX_A
