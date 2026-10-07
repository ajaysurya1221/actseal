# Actseal Python guide

The [stability manifest](stability.md) is the exhaustive, normative inventory
of the public Python surface: every record field, constant and signature. This
guide groups that surface by task and shows small runnable examples. The
examples use only names that exist in 1.x; there are no convenience wrappers
beyond the ones listed here.

The runtime core imports only the standard library. Importing `actseal` never
imports an optional model stack, and `actseal.replay` works with the Laya
extra absent.

## Surface by group

| Group | Module | Names |
|---|---|---|
| Records (also re-exported from `actseal`) | `actseal.records` | `Option`, `ChoiceQuestion`, `Case`, `CaseRef`, `ModelIdentity`, `DecisionRequest`, `CapturedOutcome`, `ChoiceAnswer`, `ProviderFailure`, `LockedPolicy`, `GateLimits`, `Contract`, `FaultSpec`, `PlanLock`, `PolicyDecision`, `DecisionRecord`, `FaultResult`, `Interval`, `Verdict`, `EvidenceBundle` |
| Aliases and errors (also re-exported) | `actseal.records`, `actseal.errors` | `Action`, `Status`, `EvidenceScope`, `Outcome`; `ActsealError`, `SchemaError`, `IntegrityError`, `ProviderSetupError` |
| Serialization (also re-exported) | `actseal.serialization` | `canonical_json`, `sha256_bytes`, `strict_json_loads`, `to_data`, `from_data`, `implementation_fingerprint` |
| Contract and locking | `actseal.contract`, `actseal.locking` | `read_input_text`, `parse_contract`, `parse_cases`; `case_digest`, `lock_digest`, `create_lock`, `validate_lock`, `validate_inputs`, `parse_lock` |
| Decision and statistical path | `actseal.policy`, `actseal.normalization`, `actseal.faults`, `actseal.stats`, `actseal.assessment` | `evaluate`; `normalize`, `request_sha256`, `laya_mass_tolerance`; `fault_capture`, `run_fault_campaign`; `clopper_pearson_tail`; `assess` |
| Evidence and replay | `actseal.evidence`, `actseal.replay` | `write_bundle`, `read_bundle_files`, `decode_document`, `decode_rows`; `replay` |
| Compatibility | `actseal.compatibility` | `CompatibilityRegistry`, `LegacySchemaError`, `parse_registry`, `load_registry`, `check_replay_compatibility`, `require_exact_implementation`, `is_legacy_lock`, `is_legacy_manifest` |
| Runner and CLI | `actseal.runner`, `actseal.cli` | `ModelFactory`, `open_model`, `write_lock`, `collect`, `lock_run`, `verify_run`, `demo_run`, `DemoRun`, `DemoResult`; `main` |
| Providers | `actseal.adapters.base`, `actseal.adapters.fixture`, `actseal.adapters.laya` | `DecisionModel`; `FixtureModel`, `validate_timeout`; `LayaModel` |

Records are frozen dataclasses with slots; constructor order is field order and
is listed in the manifest. Children are tuples. Every constructor validates its
fields and raises `SchemaError` naming the field, never echoing the value.
Exported constants (limits, reason codes, file names, identity values) are
listed in the manifest's constants table.

## Signatures

Each row names the exact module path. These signatures are frozen for 1.x;
`tests/docs` checks them against the installed package.

| Function | Signature |
|---|---|
| `actseal.contract.read_input_text` | `(path: Path, *, limit: int = MAX_JSON_BYTES) -> str` |
| `actseal.contract.parse_contract` | `(path: Path) -> Contract` |
| `actseal.contract.parse_cases` | `(text: str, question: ChoiceQuestion) -> tuple[Case, ...]` |
| `actseal.locking.case_digest` | `(case: Case) -> str` |
| `actseal.locking.lock_digest` | `(lock: PlanLock) -> str` |
| `actseal.locking.create_lock` | `(contract: Contract, calibration_jsonl: str, verification_jsonl: str, model_identity: ModelIdentity) -> PlanLock` |
| `actseal.locking.validate_lock` | `(lock: PlanLock) -> None` |
| `actseal.locking.validate_inputs` | `(lock: PlanLock, calibration_jsonl: str, verification_jsonl: str) -> tuple[Case, ...]` |
| `actseal.locking.parse_lock` | `(text: str) -> PlanLock` |
| `actseal.policy.evaluate` | `(outcome: Outcome, policy: LockedPolicy) -> PolicyDecision` |
| `actseal.normalization.normalize` | `(capture: CapturedOutcome, question: ChoiceQuestion, expected_identity: ModelIdentity) -> Outcome` |
| `actseal.normalization.request_sha256` | `(request: DecisionRequest) -> str` |
| `actseal.normalization.laya_mass_tolerance` | `(option_count: int) -> float` |
| `actseal.faults.fault_capture` | `(lock: PlanLock, spec: FaultSpec) -> tuple[DecisionRequest, CapturedOutcome]` |
| `actseal.faults.run_fault_campaign` | `(lock: PlanLock) -> tuple[FaultResult, ...]` |
| `actseal.stats.clopper_pearson_tail` | `(successes: int, n: int, tail: float) -> tuple[float, float]` |
| `actseal.assessment.assess` | `(records: Sequence[DecisionRecord], lock: PlanLock, faults: Sequence[FaultResult]) -> Verdict` |
| `actseal.evidence.write_bundle` | `(bundle: EvidenceBundle, destination: Path) -> Path` |
| `actseal.evidence.read_bundle_files` | `(bundle: Path) -> dict[str, bytes]` |
| `actseal.evidence.decode_document` | `(name: str, data: bytes, record_type: type[_D]) -> _D` |
| `actseal.evidence.decode_rows` | `(name: str, data: bytes, record_type: type[_D]) -> tuple[_D, ...]` |
| `actseal.replay.replay` | `(bundle: Path, *, expected_lock_sha256: str \| None = None) -> Verdict` |
| `actseal.compatibility.parse_registry` | `(text: str) -> CompatibilityRegistry` |
| `actseal.compatibility.load_registry` | `() -> CompatibilityRegistry` |
| `actseal.compatibility.check_replay_compatibility` | `(lock: PlanLock, *, registry: CompatibilityRegistry \| None = None) -> None` |
| `actseal.compatibility.require_exact_implementation` | `(lock: PlanLock) -> None` |
| `actseal.compatibility.is_legacy_lock` | `(value: object) -> bool` |
| `actseal.compatibility.is_legacy_manifest` | `(value: object) -> bool` |
| `actseal.serialization.canonical_json` | `(value: object) -> bytes` |
| `actseal.serialization.sha256_bytes` | `(data: bytes) -> str` |
| `actseal.serialization.strict_json_loads` | `(text: str) -> object` |
| `actseal.serialization.to_data` | `(record: object) -> dict[str, object]` |
| `actseal.serialization.from_data` | `(record_type: type[T], value: object) -> T` |
| `actseal.serialization.implementation_fingerprint` | `() -> str` |
| `actseal.runner.open_model` | `(provider: str, *, responses: Path \| None, offline: bool) -> DecisionModel` |
| `actseal.runner.write_lock` | `(lock: PlanLock, destination: Path) -> Path` |
| `actseal.runner.collect` | `(model: DecisionModel, lock: PlanLock, cases: tuple[Case, ...]) -> tuple[DecisionRecord, ...]` |
| `actseal.runner.lock_run` | `(contract_path: Path, calibration_path: Path, verification_path: Path, destination: Path, *, model_factory: ModelFactory) -> PlanLock` |
| `actseal.runner.verify_run` | `(lock_path: Path, calibration_path: Path, verification_path: Path, destination: Path, *, provider: str, model_factory: ModelFactory) -> tuple[EvidenceBundle, Path]` |
| `actseal.runner.demo_run` | `(destination: Path) -> DemoResult` |
| `actseal.cli.main` | `(argv: Sequence[str] \| None = None) -> int` |
| `actseal.adapters.fixture.validate_timeout` | `(timeout_s: object) -> float` |
| `actseal.adapters.fixture.FixtureModel.__init__` | `(self, responses: Path) -> None` |
| `actseal.adapters.laya.LayaModel.__init__` | `(self, *, offline: bool = False) -> None` |
| `actseal.adapters.base.DecisionModel.identity` | `(self) -> ModelIdentity` |
| `actseal.adapters.base.DecisionModel.decide` | `(self, request: DecisionRequest, *, timeout_s: float) -> CapturedOutcome` |
| `actseal.adapters.base.DecisionModel.close` | `(self) -> None` |

`_D` ranges over `DecisionRecord | FaultResult | Verdict | PlanLock`; `T` is
any public record type. `ModelFactory` is `Callable[[], DecisionModel]`.
`DemoRun` exposes the properties `verdict` and `as_expected`; `DemoResult`
exposes `succeeded`; `ChoiceQuestion` exposes `labels`.

## Examples

The examples below are executed by `tests/docs` in order, in a directory
where `actseal demo --out ./actseal-demo` has already run, so that
`./actseal-demo/inputs` holds the authored support-triage files. Later
examples reuse files written by earlier ones. Every output path must be new.

### Evaluate one outcome against a frozen policy

`evaluate` is pure: it takes a normalized outcome and a locked policy and
returns the decision in the frozen precedence order. Only `ACT` carries a
choice.

```python
from actseal import ChoiceAnswer, LockedPolicy, ProviderFailure
from actseal.policy import evaluate

policy = LockedPolicy(
    known_labels=("billing", "technical", "sales"),
    allowed_labels=("billing", "technical"),
    threshold=0.9,
)
confident = ChoiceAnswer(
    choice="billing",
    probabilities=(("billing", 0.95), ("technical", 0.03), ("sales", 0.02)),
    selected_probability=0.95,
    provider_confidence=None,
    warnings=(),
    fallback_used=False,
)
decision = evaluate(confident, policy)
assert (decision.action, decision.choice, decision.reason) == ("ACT", "billing", "policy.allowed")

hesitant = ChoiceAnswer(
    "billing", (("billing", 0.6), ("technical", 0.3), ("sales", 0.1)), 0.6, None, (), False
)
assert evaluate(hesitant, policy).action == "ABSTAIN"

not_allowed = ChoiceAnswer(
    "sales", (("billing", 0.05), ("technical", 0.03), ("sales", 0.92)), 0.92, None, (), False
)
assert evaluate(not_allowed, policy).action == "DENY"

failed = ProviderFailure(code="timeout", warnings=(), fallback_used=False)
assert evaluate(failed, policy).action == "ESCALATE"
```

### Lock, verify and replay from Python

`lock_run` and `verify_run` are the same protocol the CLI runs: fixed
30-second request deadline, every locked case exactly once, six canonical
faults, one new bundle. The model factory is called once per run and the
provider is closed on every path.

```python
from pathlib import Path

from actseal.adapters.fixture import FixtureModel
from actseal.replay import replay
from actseal.runner import lock_run, verify_run

inputs = Path("actseal-demo/inputs")
responses = inputs / "fixed_responses.jsonl"

lock = lock_run(
    inputs / "fixed.toml",
    inputs / "fixed_calibration.jsonl",
    inputs / "fixed_verification.jsonl",
    Path("recheck.lock.json"),
    model_factory=lambda: FixtureModel(responses),
)
bundle, bundle_path = verify_run(
    Path("recheck.lock.json"),
    inputs / "fixed_calibration.jsonl",
    inputs / "fixed_verification.jsonl",
    Path("recheck-evidence"),
    provider="fixture",
    model_factory=lambda: FixtureModel(responses),
)
assert bundle.verdict.status == "PASS"
assert bundle.verdict.total == 128 and bundle.verdict.accepted == 128

replayed = replay(bundle_path, expected_lock_sha256=lock.sha256)
assert replayed == bundle.verdict
```

The `fixed` fixture is authored to match its labels, so this run is expected
to `PASS`; that is a property of the synthetic demo, not a model result.

### Reuse the locked policy at runtime

An application that deploys a policy should load the lock it verified,
validate it, **bind each capture to the request it is deciding**, normalize
the capture against the locked identity and evaluate with the locked policy.
The application owns what happens next: Actseal returns a decision, it does
not execute or block anything.

Binding is the caller's job. `normalize` takes no request parameter, so it
cannot tell whether a capture answers the request in hand; the runner builds
each capture from its own request, and assessment and replay re-check every
recorded `request_sha256` against the locked case. A live gate must do the
same check itself, before normalization and before any action, and fail
closed when it does not hold.

```python
from pathlib import Path

from actseal.contract import read_input_text
from actseal.locking import MAX_LOCK_BYTES, parse_lock, validate_lock
from actseal.normalization import normalize, request_sha256
from actseal.policy import evaluate
from actseal.records import CapturedOutcome, DecisionRequest, PolicyDecision

lock = parse_lock(read_input_text(Path("recheck.lock.json"), limit=MAX_LOCK_BYTES))
validate_lock(lock)
question = lock.contract.question
policy = lock.contract.policy
identity = lock.model_identity

executed: list[str] = []  # the application's own queue; Actseal never touches it


def route_ticket(request: DecisionRequest, capture: CapturedOutcome) -> PolicyDecision:
    """Application-owned gate: bind, normalize, evaluate, then act only on ACT."""
    if capture.request_sha256 != request_sha256(request):
        # The capture answers some other request. Fail closed: no normalization,
        # no policy evaluation, no application action.
        raise ValueError("capture does not bind the request being decided")
    decision = evaluate(normalize(capture, question, identity), policy)
    if decision.action == "ACT":
        executed.append(f"{request.case_id}->{decision.choice}")
    # ABSTAIN, DENY and ESCALATE are the application's explicit non-execution paths.
    return decision


request = DecisionRequest(
    "live-001", "Ticket LIVE-001: my invoice shows a duplicate charge.", question
)
body = '{"type": "choice", "choice": "billing", "probabilities": {"billing": 0.95, "technical": 0.03, "sales": 0.02}}'
bound = CapturedOutcome(request_sha256(request), identity, body, None, (), False)
decision = route_ticket(request, bound)
assert (decision.action, decision.choice) == ("ACT", "billing")
assert executed == ["live-001->billing"]

other = DecisionRequest("live-002", "Ticket LIVE-002: the app crashes on launch.", question)
foreign = CapturedOutcome(request_sha256(other), identity, body, None, (), False)
try:
    route_ticket(request, foreign)
except ValueError:
    pass
else:
    raise AssertionError("a capture for another request must never be evaluated")
assert executed == ["live-001->billing"]  # nothing ran for the foreign capture

low_body = '{"type": "choice", "choice": "billing", "probabilities": {"billing": 0.6, "technical": 0.3, "sales": 0.1}}'
low = CapturedOutcome(request_sha256(request), identity, low_body, None, (), False)
assert route_ticket(request, low).action == "ABSTAIN"
assert executed == ["live-001->billing"]  # ABSTAIN executed nothing
```

The captures here are hand-written to show the record shapes. In production
each capture comes from one `DecisionModel.decide(request, ...)` call made by
the application for that same request, against the identity the lock
recorded. A capture with a different identity normalizes to
`identity_mismatch` and escalates; a capture for a different request is
refused before normalization. The exception path is application code too: it
may route to the application's escalation handling, but it must not evaluate
or execute.

### Read a bundle and recompute its verdict

```python
from pathlib import Path

from actseal import Verdict
from actseal.evidence import VERDICT_FILE, decode_document, read_bundle_files
from actseal.replay import replay

files = read_bundle_files(Path("recheck-evidence"))
assert sorted(files) == sorted(
    [
        "manifest.json",
        "lock.json",
        "calibration.jsonl",
        "verification.jsonl",
        "records.jsonl",
        "faults.jsonl",
        "verdict.json",
    ]
)
recorded = decode_document(VERDICT_FILE, files[VERDICT_FILE], Verdict)
assert replay(Path("recheck-evidence")) == recorded
```

`replay` returns a `Verdict` for invalid evidence too: `ERROR` with zero
counts, `[0, 1]` intervals and `reasons` naming the violated invariant. It
raises `SchemaError` only for wrong Python argument shapes.

### Canonical encoding and digests

```python
from pathlib import Path

from actseal import Interval, Verdict, canonical_json, from_data, sha256_bytes, to_data
from actseal.contract import read_input_text
from actseal.locking import MAX_LOCK_BYTES, case_digest, lock_digest, parse_lock

verdict = Verdict(
    "BLOCK",
    ("risk.exceeds_limit",),
    128,
    128,
    32,
    Interval(0.168, 0.347),
    Interval(0.966, 1.0),
    "demo",
    "a" * 64,
)
data = to_data(verdict)
assert from_data(Verdict, data) == verdict
assert len(sha256_bytes(canonical_json(data))) == 64

lock = parse_lock(read_input_text(Path("recheck.lock.json"), limit=MAX_LOCK_BYTES))
# Record digests are computed over the canonical encoding.
assert lock_digest(lock) == lock.sha256
assert case_digest(lock.verification_cases[0]) == lock.verification_inventory[0].sha256
# Raw-input and fixture identities hash the supplied file bytes as they are.
inputs = Path("actseal-demo/inputs")
assert sha256_bytes((inputs / "fixed_calibration.jsonl").read_bytes()) == lock.calibration_sha256
assert sha256_bytes((inputs / "fixed_responses.jsonl").read_bytes()) == lock.model_identity.revision
```

`canonical_json` (UTF-8, sorted keys, compact separators, no NaN or Infinity,
no terminal newline) is the byte form of **record** digests: `case_digest`,
`lock_digest`, `request_sha256`, the bundle manifest's self-seal and the map
that `implementation_fingerprint` hashes. Other digests are over **raw bytes**
exactly as supplied and are never re-encoded: `PlanLock.calibration_sha256`
and `verification_sha256` are `sha256_bytes` of the raw JSONL text that
`create_lock` received; each manifest file entry hashes the published file's
bytes; the fixture identity's `revision` and `artifact_hashes` hash the raw
fixture file; and the implementation fingerprint hashes each installed source
file's bytes before canonically encoding the path-to-hash map. Preserving the
raw bytes is what makes those identities meaningful, so a reader must not
"normalize" them before hashing.

### Interval arithmetic

```python
from actseal.stats import clopper_pearson_tail

lower, upper = clopper_pearson_tail(0, 128, 0.05 / 4)
assert lower == 0.0
assert 0.0 < upper < 0.04
```

The assessment allocates `alpha / 4` to each of the four tails; the
[statistical contract](statistical-contract.md) defines the domain and the
verdict rules. Call `assess` with records, lock and faults to obtain a
`Verdict`; `verify_run` and `replay` do that for you.

## Providers

`DecisionModel` is a `typing.Protocol` with three methods: `identity()`,
`decide(request, *, timeout_s)` and `close()`. A provider captures raw
evidence; it never normalizes, retries, falls back or authorizes an action.
`decide` returns a `CapturedOutcome` and never raises for a captured failure;
setup problems raise `ProviderSetupError`.

The current stable providers are `FixtureModel(responses: Path)`, which
replays a recorded JSONL file and derives its identity from that file's bytes,
and `LayaModel(*, offline: bool = False)`, the optional pinned native CPU
adapter described in [providers](providers.md). `open_model` builds either by
name.

In the v1.0 scope the runner accepts those two stable providers plus one
PROVISIONAL experimental provider: `ModelIdentity.provider` accepts `fixture`,
`laya` or `jev`, and `verify_run` requires the requested provider to equal the
locked one. `open_model("jev", responses=None, offline=False)` is the Python
opt-in for the experimental Jev cloud adapter
(`actseal.experimental.providers.jev.JevModel(*, offline: bool = False)`): the
explicit string selects it, the module is imported only in that branch,
`responses` is rejected, and `offline=True` raises `ProviderSetupError` before
the adapter reads `JEV_API_KEY`. On the command line the same selection
additionally requires `--experimental-provider`. Nothing under
`actseal.experimental` is part of the 1.x promise; see
[providers](providers.md) for its boundary and current (mocked-only)
verification status. A class of your own can satisfy the protocol for typing
and for tests, but it cannot be sealed into a lock or collected against through
the runner. Calling `decide` directly produces raw captures; it does not
execute the locked collection protocol, which the runner owns together with its
fixed deadlines. A later 1.x release may add a provider only as an additive,
explicitly selected option under the [versioning policy](versioning.md).

## Errors

`ActsealError` is the base. `SchemaError` means a document, record or argument
violates its documented shape; `IntegrityError` means a lock, input, identity
or implementation check failed; `ProviderSetupError` means a provider could not
be built or asked for its identity. `actseal.compatibility.LegacySchemaError`
is a `SchemaError` raised for actseal 0.1.0 locks and manifests; see the
[migration guide](migration.md). Messages name fields and invariants and never
echo input values.

## Related

- [Stability manifest](stability.md): the normative inventory and constants.
- [Versioning policy](versioning.md): what may change in a minor or patch.
- [Wire schemas](schemas/README.md): JSON Schema for every document.
- [Concepts](concepts.md) and the [CLI reference](cli.md).
