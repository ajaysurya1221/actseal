# Actseal 1.x stability manifest

Status: normative for every 1.x release, frozen with Task 02 of the v1.0.0 plan
(plan/v1/PLAN.md, section E; amendment V1-003). This document enumerates the
complete public surface. A name that appears here is STABLE unless it is marked
PROVISIONAL. A name that does not appear here, or begins with an underscore, is
private. The companion documents are the [versioning policy](versioning.md),
the [0.1.0 to 1.0.0 migration guide](migration.md) and the published
[wire schemas](schemas/README.md). Exact record field semantics remain in
[CONTRACTS](../plan/CONTRACTS.md).

## What STABLE means

STABLE means **compatible throughout 1.x**: the name exists, accepts the
documented inputs with the documented meanings, returns the documented shape,
and raises or returns the documented failure class. A minor release may add
commands, constants, or optional arguments whose defaults preserve existing
behaviour. It may not add fields to an existing strict schema version
(lock 2, manifest 2, receipt 1, registry 1) or to the default CLI receipt
shapes: the published schemas reject unknown fields, so the shapes they
describe are frozen for 1.x. Additional formats or semantics arrive only as a
separately versioned, explicitly opt-in interface that preserves every
existing stable surface. Removal or an incompatible change waits for 2.0 under
the [versioning policy](versioning.md); see
[ADR 0015](decisions/0015-v1-stability-and-replay-compatibility.md).

STABLE does **not** freeze:

- model answers, provider outputs, or the contents of any evidence produced by
  a model;
- filesystem paths supplied by callers or printed back to them;
- elapsed times, durations, or any performance figure;
- incidental English wording of human-readable output, help text, log notes and
  exception messages beyond the leading field or invariant name (for example
  `implementation_sha256: ...`) and the error class;
- the demo inputs, their counts and their measured timings, which are examples
  and not an application interface;
- the *values* of identity and version constants (adapter versions, normalizer
  version, model identifiers, artifact hashes, the current replay engine, the
  implementation fingerprint). Their documented **meanings** are stable; their
  values identify the actual implementation or model and may change only with a
  separately identified release.

Scripts must consume the versioned JSON receipts, never the text output.

PROVISIONAL surfaces live only under `actseal.experimental` or behind an
explicit experimental CLI flag and may change in any release.

## Command line

The console script `actseal` and `python -m actseal` are STABLE. Commands are
exactly `lock`, `verify`, `replay` and `demo`. Every command accepts `--json`.
Abbreviated long options are rejected by the root parser and by every
subcommand (`--ou` is never `--out`). `--version` is a root-only option
(`actseal --version`; `actseal COMMAND --version` is a usage error, `ERROR` 3).
`-h`/`--help` is accepted at the root and at every command. Both remain text
output.

| Command | Required | Optional |
|---|---|---|
| `lock` | `--contract PATH`, `--calibration PATH`, `--verification PATH`, `--provider {fixture,laya}`, `--out PATH` | `--responses PATH`, `--offline`, `--json`; PROVISIONAL: `--provider jev` with `--experimental-provider` |
| `verify` | `--lock PATH`, `--calibration PATH`, `--verification PATH`, `--provider {fixture,laya}`, `--out DIRECTORY` | `--responses PATH`, `--offline`, `--json`; PROVISIONAL: `--provider jev` with `--experimental-provider` |
| `replay` | `DIRECTORY` (positional bundle directory) | `--expected-lock-sha256 HEX`, `--json` |
| `demo` | `--out NEW_DIRECTORY` | `--json` |
| root | | `--version` (root only), `-h`/`--help` |

Provider rules: `fixture` requires `--responses`; `laya` forbids it; `--offline`
is accepted by both. The STABLE provider choices are `fixture` and `laya`; they
reject `--experimental-provider`. The experimental Jev adapter is PROVISIONAL
(ADR 0017): `lock` and `verify` accept it only as
`--provider jev --experimental-provider`, it is never selected implicitly,
it rejects `--responses`, its adapter rejects `--offline` as a setup error
before reading `JEV_API_KEY`, and `replay`/`demo` do not accept the flag. The
`jev` choice, the flag and the adapter carry no 1.x promise and may change or
be removed in any release; the receipt shapes below are unchanged by it.

Exit codes are STABLE: `PASS` 0, `BLOCK` 1, `INCONCLUSIVE` 2, `ERROR` 3. Usage
errors, setup errors, invalid inputs, existing destinations and operating-system
failures are `ERROR` 3. A successful `lock` exits 0. `demo` exits 0 only when
its deliberately bad run is `BLOCK`, its fixed run is `PASS` and both fresh
replays equal the recorded verdicts.

### JSON receipts (schema 1)

With `--json` exactly one JSON object is written to stdout. Every receipt,
including every error and usage error, carries `schema_version` (the integer
`1`) and `command` (`lock`, `verify`, `replay`, `demo`, or `actseal` when the
command could not be parsed). Field names, JSON types and meanings are STABLE;
the exact variants are published in
[cli-receipt.schema.json](schemas/cli-receipt.schema.json).

| Receipt | Fields |
|---|---|
| any error | `schema_version`, `command`, `exit_code` (3), `ok` (false), `status` (`"ERROR"`), `error` (sanitized message) |
| `lock` | `exit_code` (0), `ok`, `lock_sha256`, `implementation_sha256`, `replay_engine_version`, `evidence_scope`, `contract`, `model_identity` {`provider`, `model`, `revision`, `adapter_version`, `normalizer_version`}, `verification_cases`, `calibration_cases`, `out` |
| `verify` | the bundle payload (verdict fields `status`, `reasons`, `total`, `accepted`, `errors`, `risk` {`lower`, `upper`}, `coverage` {`lower`, `upper`}, `evidence_scope`, `lock_sha256`, plus `failures` (code to count), `warnings` (code to count), `faults` (scenario id to {`action`, `expected_action`})) and the command-level fields `exit_code`, `ok`, `out` |
| `replay` | verdict fields, `exit_code`, `ok`, `bundle`, `expected_lock_sha256` (string or null), `notes` (array of advisory strings; contains the legacy guidance for actseal 0.1.0 evidence, otherwise empty) |
| `demo` | `exit_code`, `ok`, `status` (`PASS` or `ERROR`), `evidence_scope` (`demo`), `demo_only` (true), `note`, `out`, `duration_s`, `runs` {`bad`, `fixed`} each holding the bundle payload (verdict fields, `failures`, `warnings`, `faults`; no `exit_code`, `ok` or `out` of its own) plus `expected_status`, `as_expected`, `lock`, `evidence`, `replay` (verdict object) and `replay_matches` |

## Python surface

Signatures below are copied from the 1.0 source. Positional order is part of the
contract for records (dataclass constructors) and for every function listed.

### Records (`actseal.records`, also re-exported from `actseal`)

Frozen dataclasses; constructor order is field order. Children are tuples.

| Record | Fields in order |
|---|---|
| `Option` | `label: str`, `description: str` |
| `ChoiceQuestion` | `question_id: str`, `instructions: str`, `options: tuple[Option, ...]`; property `labels -> tuple[str, ...]` |
| `Case` | `case_id: str`, `state: str`, `expected_label: str` |
| `CaseRef` | `case_id: str`, `sha256: str` |
| `ModelIdentity` | `provider: str`, `model: str`, `revision: str`, `artifact_hashes: tuple[tuple[str, str], ...]`, `adapter_version: str`, `normalizer_version: str`, `runtime: tuple[tuple[str, str], ...]` |
| `DecisionRequest` | `case_id: str`, `state: str`, `question: ChoiceQuestion` |
| `CapturedOutcome` | `request_sha256: str`, `identity: ModelIdentity`, `body_json: str \| None`, `failure_code: str \| None`, `warnings: tuple[str, ...]`, `fallback_used: bool` |
| `ChoiceAnswer` | `choice: str`, `probabilities: tuple[tuple[str, float], ...]`, `selected_probability: float`, `provider_confidence: float \| None`, `warnings: tuple[str, ...]`, `fallback_used: bool` |
| `ProviderFailure` | `code: str`, `warnings: tuple[str, ...]`, `fallback_used: bool` |
| `LockedPolicy` | `known_labels: tuple[str, ...]`, `allowed_labels: tuple[str, ...]`, `threshold: float` |
| `GateLimits` | `max_risk: float`, `min_coverage: float`, `alpha: float` |
| `Contract` | `schema_version: int` (1), `name: str`, `question: ChoiceQuestion`, `policy: LockedPolicy`, `limits: GateLimits`, `evidence_scope: EvidenceScope`, `population: str` |
| `FaultSpec` | `scenario_id: str`, `kind: str`, `expected_action: Action` |
| `PlanLock` | `schema_version: int` (2), `contract: Contract`, `model_identity: ModelIdentity`, `calibration_sha256: str`, `verification_sha256: str`, `calibration_inventory: tuple[CaseRef, ...]`, `verification_inventory: tuple[CaseRef, ...]`, `verification_cases: tuple[Case, ...]`, `fault_inventory: tuple[FaultSpec, ...]`, `implementation_sha256: str`, `sha256: str`, `replay_engine_version: str` |
| `PolicyDecision` | `action: Action`, `choice: str \| None`, `reason: str`, `fallback_used: bool` |
| `DecisionRecord` | `case_id: str`, `capture: CapturedOutcome`, `outcome: Outcome`, `decision: PolicyDecision` |
| `FaultResult` | `scenario_id: str`, `request: DecisionRequest`, `capture: CapturedOutcome`, `outcome: Outcome`, `decision: PolicyDecision` |
| `Interval` | `lower: float`, `upper: float` |
| `Verdict` | `status: Status`, `reasons: tuple[str, ...]`, `total: int`, `accepted: int`, `errors: int`, `risk: Interval`, `coverage: Interval`, `evidence_scope: EvidenceScope`, `lock_sha256: str` |
| `EvidenceBundle` | `lock: PlanLock`, `calibration_jsonl: str`, `verification_jsonl: str`, `records: tuple[DecisionRecord, ...]`, `faults: tuple[FaultResult, ...]`, `verdict: Verdict` |

`PlanLock.replay_engine_version` is the one 1.0 constructor change: appended
after `sha256`, so every 0.1 positional argument keeps its position. The
constructor requires a nonempty string; engine *support* is decided by
`actseal.compatibility`, not by the record.

Type aliases: `Action = Literal["ACT", "ABSTAIN", "ESCALATE", "DENY"]`,
`Status = Literal["PASS", "BLOCK", "INCONCLUSIVE", "ERROR"]`,
`EvidenceScope = Literal["demo", "iid"]`, `Outcome = ChoiceAnswer | ProviderFailure`.

### Errors (`actseal.errors`, also re-exported from `actseal`)

`ActsealError` (base); `SchemaError`, `IntegrityError`, `ProviderSetupError`
(subclasses). `actseal.compatibility.LegacySchemaError` is a `SchemaError`
subclass raised for real actseal 0.1.0 (schema 1) locks and manifests.

### Serialization (`actseal.serialization`, also re-exported from `actseal`)

```python
def canonical_json(value: object) -> bytes: ...
def sha256_bytes(data: bytes) -> str: ...
def strict_json_loads(text: str) -> object: ...
def to_data(record: object) -> dict[str, object]: ...
def from_data(record_type: type[T], value: object) -> T: ...
def implementation_fingerprint() -> str: ...
```

Canonical encoding (UTF-8, `ensure_ascii=False`, sorted keys, compact
separators, no NaN/Infinity, no terminal newline; wire files add one LF per
object) and the fingerprint algorithm (canonical sorted map of installed
`actseal/**/*.py` paths to source hashes, excluding caches, never executing
source) are STABLE. The fingerprint is an implementation identity, not a
signature. `actseal.__version__` is the installed package version string.

### Contract and locking (`actseal.contract`, `actseal.locking`)

```python
def read_input_text(path: Path, *, limit: int = MAX_JSON_BYTES) -> str: ...
def parse_contract(path: Path) -> Contract: ...
def parse_cases(text: str, question: ChoiceQuestion) -> tuple[Case, ...]: ...


def case_digest(case: Case) -> str: ...
def lock_digest(lock: PlanLock) -> str: ...
def create_lock(
    contract: Contract,
    calibration_jsonl: str,
    verification_jsonl: str,
    model_identity: ModelIdentity,
) -> PlanLock: ...
def validate_lock(lock: PlanLock) -> None: ...
def validate_inputs(
    lock: PlanLock, calibration_jsonl: str, verification_jsonl: str
) -> tuple[Case, ...]: ...
def parse_lock(text: str) -> PlanLock: ...
```

`validate_lock` checks wire size, the self-seal, replay-engine compatibility
(below), the frozen six-fault inventory and case coherence. `parse_lock`
decodes strictly without resealing and raises `LegacySchemaError` for a real
schema-1 lock.

### Decision and statistical path

```python
# actseal.policy
def evaluate(outcome: Outcome, policy: LockedPolicy) -> PolicyDecision: ...


# actseal.normalization
def normalize(
    capture: CapturedOutcome, question: ChoiceQuestion, expected_identity: ModelIdentity
) -> Outcome: ...
def request_sha256(request: DecisionRequest) -> str: ...
def laya_mass_tolerance(option_count: int) -> float: ...


# actseal.faults
def fault_capture(lock: PlanLock, spec: FaultSpec) -> tuple[DecisionRequest, CapturedOutcome]: ...
def run_fault_campaign(lock: PlanLock) -> tuple[FaultResult, ...]: ...


# actseal.stats
def clopper_pearson_tail(successes: int, n: int, tail: float) -> tuple[float, float]: ...


# actseal.assessment
def assess(
    records: Sequence[DecisionRecord], lock: PlanLock, faults: Sequence[FaultResult]
) -> Verdict: ...
```

### Evidence and replay (`actseal.evidence`, `actseal.replay`)

```python
def write_bundle(bundle: EvidenceBundle, destination: Path) -> Path: ...
def read_bundle_files(bundle: Path) -> dict[str, bytes]: ...
def decode_document(name: str, data: bytes, record_type: type[_D]) -> _D: ...
def decode_rows(name: str, data: bytes, record_type: type[_D]) -> tuple[_D, ...]: ...
def replay(bundle: Path, *, expected_lock_sha256: str | None = None) -> Verdict: ...
```

`_D` ranges over `DecisionRecord | FaultResult | Verdict | PlanLock`. Replay
imports no adapter, transport or optional library.

### Compatibility (`actseal.compatibility`, new in 1.0)

```python
CURRENT_ENGINE = "actseal-choice-v1"
SUPPORTED_ENGINES = frozenset({"actseal-choice-v1"})


class LegacySchemaError(SchemaError): ...


@dataclass(frozen=True, slots=True)
class CompatibilityRegistry:
    schema_version: int
    implementations: tuple[tuple[str, str], ...]  # (implementation_sha256, engine), sorted

    def engine_for(self, implementation_sha256: str) -> str | None: ...


def parse_registry(text: str) -> CompatibilityRegistry: ...
def load_registry() -> CompatibilityRegistry: ...
def check_replay_compatibility(
    lock: PlanLock, *, registry: CompatibilityRegistry | None = None
) -> None: ...
def require_exact_implementation(lock: PlanLock) -> None: ...
def is_legacy_lock(value: object) -> bool: ...
def is_legacy_manifest(value: object) -> bool: ...
```

Rules, applied by the shared `validate_lock` and therefore by
`validate_inputs`, `assess`, `write_bundle` and `replay`:

1. The lock's `replay_engine_version` must be in `SUPPORTED_ENGINES`.
2. A lock whose `implementation_sha256` equals the running
   `implementation_fingerprint()` is valid; the registry is not consulted.
3. Otherwise **both** the producer fingerprint and the running fingerprint
   must be registered for exactly the lock's engine in the packaged registry
   `compatibility_registry.json`. One side alone is rejected.
4. New collection (`collect` and `verify_run`) additionally requires the exact
   running fingerprint, checked before any provider is constructed or any
   `decide` call is made. A replay-compatible lock is never collected against.

The registry document is `{"schema_version": 1, "implementations":
{"<lowercase 64-hex source SHA-256>": "<engine>"}}`. The loader rejects
unknown fields, duplicate keys, malformed hashes, unsupported engines and any
wildcard or range form. The file is packaged beside the module and is outside
the implementation fingerprint (which hashes only `*.py`). Entries are added
only by review with archived-evidence regression tests; the 1.0.0 registry
ships exactly two reviewed entries for `actseal-choice-v1` (the 1.0.0 source
itself and the unreleased prerelease producer of the retained
`examples/action_gate` archive), listed with their provenance in the
[versioning policy](versioning.md#registry-approval-process). The registry is
trusted verifier configuration, not proof that evidence is authentic.

### Runner and CLI (`actseal.runner`, `actseal.cli`)

```python
ModelFactory = Callable[[], DecisionModel]

def open_model(provider: str, *, responses: Path | None, offline: bool) -> DecisionModel: ...
def write_lock(lock: PlanLock, destination: Path) -> Path: ...
def collect(
    model: DecisionModel, lock: PlanLock, cases: tuple[Case, ...]
) -> tuple[DecisionRecord, ...]: ...
def lock_run(
    contract_path: Path,
    calibration_path: Path,
    verification_path: Path,
    destination: Path,
    *,
    model_factory: ModelFactory,
) -> PlanLock: ...
def verify_run(
    lock_path: Path,
    calibration_path: Path,
    verification_path: Path,
    destination: Path,
    *,
    provider: str,
    model_factory: ModelFactory,
) -> tuple[EvidenceBundle, Path]: ...
def demo_run(destination: Path) -> DemoResult: ...

@dataclass(frozen=True, slots=True)
class DemoRun:
    name: str
    expected_status: str
    lock: PlanLock
    lock_path: Path
    bundle: EvidenceBundle
    bundle_path: Path
    replayed: Verdict
    # properties
    verdict -> Verdict
    as_expected -> bool

@dataclass(frozen=True, slots=True)
class DemoResult:
    destination: Path
    runs: tuple[DemoRun, ...]
    duration_s: float
    # property
    succeeded -> bool

# actseal.cli
def main(argv: Sequence[str] | None = None) -> int: ...
```

No runner entry point accepts a deadline override (ADR 0008).

### Providers (`actseal.adapters`)

```python
# actseal.adapters.base
class DecisionModel(Protocol):
    def identity(self) -> ModelIdentity: ...
    def decide(self, request: DecisionRequest, *, timeout_s: float) -> CapturedOutcome: ...
    def close(self) -> None: ...


# actseal.adapters.fixture
class FixtureModel:
    def __init__(self, responses: Path) -> None: ...


def validate_timeout(timeout_s: object) -> float: ...


# actseal.adapters.laya
class LayaModel:
    def __init__(self, *, offline: bool = False) -> None: ...
```

`identity()` describes the immutable execution identity of the loaded model.
Locally verified artifact hashes (Laya) and a vendor-reported version string
(any cloud transport) are different kinds of evidence and must not be
described as equivalent. Native Laya support is limited to the tested
configurations in [providers](providers.md).

## Exported constants

Documented meanings are STABLE. Identity and version *values* identify the
actual implementation or model and may change only with a separately
identified release; limit values change only with a reviewed contract
amendment.

| Module | Names | Meaning |
|---|---|---|
| `actseal` | `__version__` | Installed package version |
| `actseal.records` | `SCHEMA_VERSION`, `CONTRACT_SCHEMA_VERSION` (1); `LOCK_SCHEMA_VERSION` (2); `MIN_OPTIONS` (2), `MAX_OPTIONS` (16); `MAX_CASES_PER_SPLIT` (10000); `MASS_TOLERANCE` (1e-12); `FAILURE_CODES`; `PROVIDERS` | Contract TOML and lock schema versions; option, case and probability-mass limits; the eight failure codes; the admitted serialized provider set `{fixture, laya, jev}`, where `fixture` and `laya` are the stable CLI choices and `jev` is the identity provider of the PROVISIONAL experimental adapter (admitted for recorded evidence and replay; not a stable CLI choice) |
| `actseal.serialization` | `MAX_JSON_BYTES` (128 MiB), `MAX_JSON_DEPTH` (32) | Strict-parser ceilings |
| `actseal.contract` | `MAX_ROW_BYTES` (1 MiB) | JSONL row ceiling |
| `actseal.locking` | `FAULT_INVENTORY`, `MAX_LOCK_BYTES` (32 MiB) | The frozen six-scenario fault table in order; lock document ceiling |
| `actseal.policy` | `REASON_FALLBACK_USED`, `REASON_UNKNOWN_CHOICE`, `REASON_PROVIDER_PREFIX`, `REASON_DISALLOWED_CHOICE`, `REASON_LOW_CONFIDENCE`, `REASON_ALLOWED` | Policy decision reason codes |
| `actseal.normalization` | `NORMALIZER_VERSION`, `FIXTURE_MASS_TOLERANCE`, `LAYA_MASS_TOLERANCE_PER_OPTION`, `LAYA_MODEL_MARKER` | Normalizer profile identity, mass tolerances and the Laya wire marker |
| `actseal.faults` | `FAULT_STATE` | The literal synthetic state text of every canonical fault request |
| `actseal.assessment` | `REASON_RISK_EXCEEDS_LIMIT`, `REASON_COVERAGE_BELOW_MINIMUM`, `REASON_EVIDENCE_INSUFFICIENT`, `REASON_NO_ACCEPTED_CASES`, `REASON_CONTRACT_SATISFIED`, `REASON_WORKER_INVALIDATED`, `REASON_FAULT_PREFIX`, `REASON_INTEGRITY_PREFIX`, `TAIL_DIVISOR` (4) | Verdict reason codes and the CP tail allocation |
| `actseal.evidence` | `MANIFEST_FILE`, `LOCK_FILE`, `CALIBRATION_FILE`, `VERIFICATION_FILE`, `RECORDS_FILE`, `FAULTS_FILE`, `VERDICT_FILE`, `DATA_FILES`, `BUNDLE_FILES`, `BUNDLE_SCHEMA_VERSION` (2), `MAX_BUNDLE_BYTES` (128 MiB) | Bundle file names and order, manifest schema version, aggregate ceiling |
| `actseal.replay` | `REASON_BUNDLE_IO`, `REASON_BUNDLE_SCHEMA`, `REASON_BUNDLE_HASH`, `REASON_LOCK_SCHEMA`, `REASON_LEGACY_SCHEMA`, `REASON_EXPECTED_LOCK`, `REASON_LOCK`, `REASON_INPUTS`, `REASON_RECORDS_SCHEMA`, `REASON_FAULTS_SCHEMA`, `REASON_VERDICT_SCHEMA`, `REASON_VERDICT`, `UNKNOWN_LOCK_SHA256`, `UNKNOWN_SCOPE` | Replay integrity reason codes and the ADR 0012 unknown-identity sentinel |
| `actseal.runner` | `REQUEST_TIMEOUT_S` (30.0), `LOCK_FILE_NAME`, `EVIDENCE_DIRECTORY`, `DEMO_INPUTS_DIRECTORY`, `DEMO_RUNS`, `DEMO_EXPECTED` | Fixed collection deadline; lock and demo layout constants; prespecified demo outcomes |
| `actseal.cli` | `EXIT_CODES`, `EXIT_ERROR` (3), `RECEIPT_SCHEMA_VERSION` (1) | Status to exit code map; receipt schema version |
| `actseal.compatibility` | `CURRENT_ENGINE`, `SUPPORTED_ENGINES`, `REGISTRY_SCHEMA_VERSION` (1), `REGISTRY_FILE`, `MAX_REGISTRY_BYTES` (1 MiB), `RELEASE_RECEIPT_SCHEMA_VERSION` (1), `LEGACY_GUIDANCE` | Replay engine identity and support; registry file and limits; release receipt version; legacy operator guidance |
| `actseal.adapters.fixture` | `ADAPTER_VERSION`, `MODEL_NAME`, `MAX_ROW_BYTES`, `MAX_FIXTURE_BYTES` | Fixture adapter identity and file limits |
| `actseal.adapters.laya` | `ADAPTER_VERSION`, `MODEL_ID`, `REVISION`, `ARTIFACT_HASHES`, `MAX_LEN`, `HEAD_MAX_LEN`, `OPTION_TOKEN_LIMIT`, `OPTION_BUDGET`, `STARTUP_TIMEOUT_S` (120.0), `THREADS` (4) | Pinned checkpoint identity, token layout limits and runtime constants |
| `actseal.demo_data` | `RUNS`, `RESOURCE_FILES` | Packaged demo run names and resource file names |

## Frozen semantics

These behaviours are STABLE for 1.x and change only at 2.0:

- **Policy precedence**: fallback flag -> ESCALATE; `unknown_choice` failure ->
  DENY; other provider failure -> ESCALATE; choice outside allowed labels ->
  DENY; selected probability below threshold -> ABSTAIN; otherwise ACT. Only
  ACT carries a choice; the fallback flag is always carried.
- **Denominators**: `n` is every locked verification case; `a` is final ACT
  decisions; `e` is ACT choices unequal to the locked gold label. Faults never
  enter `n`.
- **Clopper-Pearson allocation**: each tail is `alpha / 4`; risk is `[0, 1]`
  when `a == 0`; PASS requires `a > 0`.
- **Verdict precedence**: ERROR > BLOCK > INCONCLUSIVE > PASS, with the PASS,
  BLOCK and ADR 0009 worker-loss rules of the [statistical contract](statistical-contract.md).
- **Six canonical faults**: `timeout`, `rate_limit`, `malformed_response`,
  `identity_mismatch` (ESCALATE), `unknown_choice` (DENY), `low_confidence`
  (ABSTAIN), in that order, generated by `fault_capture`.
- **Canonical encoding** and the **implementation fingerprint** algorithm.
- **Exact-source collection** and **dual-registration cross-release replay**.

## Schema versions

| Document | Version constant | Value |
|---|---|---|
| Contract TOML | `records.CONTRACT_SCHEMA_VERSION` (`SCHEMA_VERSION`) | 1 |
| Lock (`lock.json`) | `records.LOCK_SCHEMA_VERSION` | 2 |
| Bundle manifest and contained record encoding | `evidence.BUNDLE_SCHEMA_VERSION` | 2 |
| CLI JSON receipt | `cli.RECEIPT_SCHEMA_VERSION` | 1 |
| Release provenance receipt | `compatibility.RELEASE_RECEIPT_SCHEMA_VERSION` | 1 |
| Compatibility registry | `compatibility.REGISTRY_SCHEMA_VERSION` | 1 |

Schema-1 locks and manifests belong to actseal 0.1.0 and are rejected with
`LegacySchemaError` / `integrity.legacy_schema`; see the
[migration guide](migration.md).

## Supported replay engines

| Engine | Releases | Status |
|---|---|---|
| `actseal-choice-v1` | 1.0.0 and later 1.x | STABLE |

Within 1.x, evidence produced by an earlier 1.x release replays only when both
that release's source fingerprint and the running release's source fingerprint
are registered for the engine. Replay of 0.1.0 evidence uses an isolated pinned
`actseal==0.1.0` installation.

A new engine may arrive in a minor release only as an explicitly selected
option; `actseal-choice-v1`, its semantics and its default behaviour are
preserved. Evidence is always interpreted through the engine recorded in its
lock and is never reinterpreted under a newer engine.

## Not stable

Private names (leading underscore), test helpers, the contents and timings of
the packaged demo, the wording of text output and help, exception text beyond
the leading field name, platform-specific details of exclusive publication,
and anything under `actseal.experimental`.
