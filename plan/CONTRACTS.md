# Actseal v1 frozen interface contract

Status: normative specification v1, 2026-10-06. T00 implements these records;
their implementation becomes frozen after T00 ACCEPT. Product code is Claude-owned.
An approved amendment must precede any change to the public interfaces below.

## 1. Public record types

All records are frozen dataclasses with tuple children, constructed only from
validated input. Do not retain caller-owned mutable containers. Public types
live in `src/actseal/records.py`; schema exceptions in `errors.py`.
The exact field order below is constructor order. Fields have no implicit defaults
unless a default is explicitly stated. Serialized field names match Python names.

| Type | Exact fields |
|---|---|
| `Option` | `label: str`, `description: str` |
| `ChoiceQuestion` | `question_id: str`, `instructions: str`, `options: tuple[Option, ...]` |
| `Case` | `case_id: str`, `state: str`, `expected_label: str` |
| `CaseRef` | `case_id: str`, `sha256: str` |
| `ModelIdentity` | `provider: str`, `model: str`, `revision: str`, `artifact_hashes: tuple[tuple[str, str], ...]`, `adapter_version: str`, `normalizer_version: str`, `runtime: tuple[tuple[str, str], ...]` |
| `DecisionRequest` | `case_id: str`, `state: str`, `question: ChoiceQuestion` |
| `CapturedOutcome` | `request_sha256: str`, `identity: ModelIdentity`, `body_json: str | None`, `failure_code: str | None`, `warnings: tuple[str, ...]`, `fallback_used: bool` |
| `ChoiceAnswer` | `choice: str`, `probabilities: tuple[tuple[str, float], ...]`, `selected_probability: float`, `provider_confidence: float | None`, `warnings: tuple[str, ...]`, `fallback_used: bool` |
| `ProviderFailure` | `code: str`, `warnings: tuple[str, ...]`, `fallback_used: bool` |
| `LockedPolicy` | `known_labels: tuple[str, ...]`, `allowed_labels: tuple[str, ...]`, `threshold: float` |
| `GateLimits` | `max_risk: float`, `min_coverage: float`, `alpha: float` |
| `Contract` | `schema_version: int`, `name: str`, `question: ChoiceQuestion`, `policy: LockedPolicy`, `limits: GateLimits`, `evidence_scope: str`, `population: str` |
| `FaultSpec` | `scenario_id: str`, `kind: str`, `expected_action: str` |
| `PlanLock` | `schema_version: int`, `contract: Contract`, `model_identity: ModelIdentity`, `calibration_sha256: str`, `verification_sha256: str`, `calibration_inventory: tuple[CaseRef, ...]`, `verification_inventory: tuple[CaseRef, ...]`, `verification_cases: tuple[Case, ...]`, `fault_inventory: tuple[FaultSpec, ...]`, `implementation_sha256: str`, `sha256: str` |
| `PolicyDecision` | `action: str`, `choice: str | None`, `reason: str`, `fallback_used: bool` |
| `DecisionRecord` | `case_id: str`, `capture: CapturedOutcome`, `outcome: ChoiceAnswer | ProviderFailure`, `decision: PolicyDecision` |
| `FaultResult` | `scenario_id: str`, `request: DecisionRequest`, `capture: CapturedOutcome`, `outcome: ChoiceAnswer | ProviderFailure`, `decision: PolicyDecision` |
| `Interval` | `lower: float`, `upper: float` |
| `Verdict` | `status: str`, `reasons: tuple[str, ...]`, `total: int`, `accepted: int`, `errors: int`, `risk: Interval`, `coverage: Interval`, `evidence_scope: str`, `lock_sha256: str` |
| `EvidenceBundle` | `lock: PlanLock`, `calibration_jsonl: str`, `verification_jsonl: str`, `records: tuple[DecisionRecord, ...]`, `faults: tuple[FaultResult, ...]`, `verdict: Verdict` |

String discriminator domains are fixed, validated at construction and documented
in aliases: `Action = Literal['ACT','ABSTAIN','ESCALATE','DENY']`,
`Status = Literal['PASS','BLOCK','INCONCLUSIVE','ERROR']`,
`EvidenceScope = Literal['demo','iid']`,
`Outcome = ChoiceAnswer | ProviderFailure`. Annotate corresponding fields with
these aliases rather than unconstrained str in the actual implementation.
`provider` supports `fixture` and `laya` in v1. Do not implement Jev in these tasks.

Validation: nonempty IDs and descriptions; unique 2..16 option labels; at least
one allowed label, a subset of known labels; `0 < threshold <= 1`; risk and coverage
limits in [0,1]; `1e-6 <= alpha < 1`; integers reject bool; numbers reject bool,
NaN and infinities. All hash fields are lowercase 64-character SHA256 hex, except
revision (a provider-defined nonempty string). Tuple key maps reject duplicates;
artifact/runtime pairs serialize sorted by key. Probability pairs follow question
option order. Unknown object fields and enum values are schema errors.

`CapturedOutcome` has exactly one of body_json or failure_code. A raw body may be
malformed JSON: that is valid recorded provider-failure evidence, not damaged
bundle structure. Headers, credentials and arbitrary exception text are excluded.

## 2. Errors and serialization (T00)

Public exceptions: `ActsealError`, and its subclasses `SchemaError`,
`IntegrityError`, `ProviderSetupError`. Error messages name the failing field or
invariant without leaking source values or secrets.

`serialization.py` exports:

```python
def canonical_json(value: object) -> bytes: ...
def sha256_bytes(data: bytes) -> str: ...
def strict_json_loads(text: str) -> object: ...
def to_data(record: object) -> dict[str, object]: ...
def from_data(record_type: type[T], value: object) -> T: ...
def implementation_fingerprint() -> str: ...
```

`T` is a TypeVar over supported record classes. No arbitrary class import or
instantiation. Union outcomes use an explicit `kind: 'answer' | 'failure'` tag.
Canonical JSON is UTF-8, ensure_ascii=False, sorted keys, compact separators,
allow_nan=False, no terminal newline. Wire files add one LF after each canonical
JSON object. Deeply bounded strict parsing rejects duplicate JSON keys, nonfinite
constants, unsupported fields/types, records over 1 MiB and nesting over 32.
Bundle aggregate size limit is 128 MiB; datasets at most 10,000 cases per split.

`implementation_fingerprint` hashes a canonical sorted map of all installed
`actseal/**/*.py` relative paths to source-byte hashes, excluding caches. It must
not execute source. Same source bytes in a checkout and wheel yield the same hash.
This is an implementation identity, not a signature or source authenticity proof.

`PlanLock.sha256` is the canonical hash of the serialized lock with only its own
`sha256` field omitted. Constructors validate hash syntax; `validate_lock` checks
the actual self-seal. Do not silently reseal incoming records.

## 3. Contracts, datasets and locking (T10)

```python
def parse_contract(path: Path) -> Contract: ...
def parse_cases(text: str, question: ChoiceQuestion) -> tuple[Case, ...]: ...
def create_lock(
    contract: Contract, calibration_jsonl: str, verification_jsonl: str,
    model_identity: ModelIdentity,
) -> PlanLock: ...
def validate_lock(lock: PlanLock) -> None: ...
def validate_inputs(
    lock: PlanLock, calibration_jsonl: str, verification_jsonl: str,
) -> tuple[Case, ...]: ...
def evaluate(outcome: Outcome, policy: LockedPolicy) -> PolicyDecision: ...
```

`contract.py` owns parsing; `locking.py` owns locks and input checks; `policy.py`
owns evaluate. TOML exact shape:

```toml
schema_version = 1
name = "support-triage"
evidence_scope = "demo"
population = "Authored support-routing demonstration; no deployment claim"

[question]
question_id = "department"
instructions = "Select the department responsible for this ticket."
options = [
  {label = "billing", description = "Payments and refunds"},
  {label = "technical", description = "Technical support"},
  {label = "sales", description = "Purchasing questions"},
]

[policy]
allowed_labels = ["billing", "technical", "sales"]
threshold = 0.90

[risk]
max_risk = 0.05
min_coverage = 0.50
alpha = 0.05
```

`known_labels` is derived from ordered options, never independently configurable.
JSONL has exactly `case_id`, `state`, `expected_label` per line, all strings.
Reject empty datasets, blank interior records, duplicate case IDs, invalid labels,
or more than 10,000 rows. Reject exact repeated state texts within or across splits
and intersecting IDs. This catches literal leakage, not semantic overlap or false
claims about independence. Preserve UTF-8 state text without case/whitespace repair.
Hash whole raw JSONL bytes plus each canonical case in ordered inventories.

Threshold selection is external and precedes lock creation; v1 does no fitting.
Lock creation binds the contract, model identity, both raw inputs/inventories,
current implementation fingerprint and all six fault specifications below.
Lock creation performs no model calls itself. CLI creates the provider first to
obtain its actual identity. A lock cannot attest that a human has never seen data.

Policy precedence:
1. Any fallback_used outcome -> ESCALATE, reason `policy.fallback_used`.
2. ProviderFailure `unknown_choice` -> DENY, `policy.unknown_choice`.
3. Other ProviderFailure -> ESCALATE, `provider.<failure_code>`.
4. Choice outside known/allowed labels -> DENY, `policy.disallowed_choice`.
5. selected_probability < threshold -> ABSTAIN, `policy.low_confidence`.
6. Otherwise ACT, `policy.allowed`.

Only ACT carries a choice; other dispositions have choice=None. Always carry the
fallback flag. No provider confidence or suggested action can override this table.

## 4. Providers, normalization and faults (T30)

```python
class DecisionModel(Protocol):
    def identity(self) -> ModelIdentity: ...
    def decide(self, request: DecisionRequest, *, timeout_s: float) -> CapturedOutcome: ...
    def close(self) -> None: ...

def normalize(capture: CapturedOutcome, question: ChoiceQuestion,
              expected_identity: ModelIdentity) -> Outcome: ...

class FixtureModel:
    def __init__(self, responses: Path) -> None: ...

class LayaModel:
    def __init__(self, *, offline: bool = False) -> None: ...

def run_fault_campaign(lock: PlanLock) -> tuple[FaultResult, ...]: ...
```

Protocol is in `adapters/base.py`; implementations in `adapters/fixture.py` and
`adapters/laya.py`. Pure `normalization.py` must import no model/client libraries;
replay uses it without importing adapters. The protocol itself is dependency-free.

Fixture file format: JSONL rows `{case_id, body_json, failure_code, warnings}`;
body_json is a string, not an embedded JSON object. Exactly one body/failure.
No fixture model identity is accepted from the file. Derive identity provider=fixture,
model=recorded-choice-v1, revision=SHA256(raw file), artifact_hashes=((responses,
file_hash),), adapter_version=1, normalizer_version=1, runtime=(). Unknown or duplicate
case IDs are errors; a missing requested case is `ProviderSetupError`, not a skip.
Captured request hash is canonical serialized DecisionRequest SHA256.

Response body format for both current adapters:
`{type:'choice', choice:str, probabilities:{label:number,...}, confidence?:number,
answer_confidence?:number, action?:object}`. Unknown envelope fields are ignored
only when explicitly documented in docs/providers.md; no guessed schema repair.
Unknown choice -> ProviderFailure(unknown_choice). Otherwise require exactly all
declared probability keys, finite values in [0,1], and positive sum. Fixture sum
tolerance is 1e-12; Laya tolerance is `0.00005 * option_count + 1e-12`. Reject beyond
tolerance. Normalize by the observed sum and gate on the returned choice's probability.
Do not replace a provider's selected label with an argmax label. Distributions are
ordered by the question; preserve the raw body even when normalization rejects it.
Identity mismatch is detected before trusting any response field.

Failure codes: `timeout`, `rate_limit`, `provider_error`, `malformed_response`,
`identity_mismatch`, `unknown_choice`, `input_too_long`, `unavailable`.
No silent retry or fallback in v1. Unknown adapter exceptions are surfaced as
provider_error with a bounded, nonsecret warning code; setup errors stop the run.

Laya exact runtime/model pins and loading/preflight APIs are in docs/providers.md.
Run one resident CPU model in a spawned child process, four Torch threads, eager,
FP32, compile=False and fast=False. Startup has a 120s bound; per-request timeout
default 30s, validated finite >0. On a request timeout terminate and join the worker;
return timeout and make later calls explicitly unavailable until a new model object
is created. close() is idempotent and leaves no worker alive. Unit tests use a tiny
fake worker; they do not download weights or import the Laya stack.
Reject overflow in the full state/question/options token layout before inference;
never silently truncate. Record and surface upstream calibration/runtime warnings.
No automatic CPU/MPS/device switch. Respect offline mode and actual observed device.

Fault campaign is separate from the statistical sample. It calls the SAME
normalizer and evaluator on a fixed synthetic request per scenario, with IDs
`fault.<kind>`. For identity_mismatch use a changed observed revision. For low_confidence,
return a known selected label with probability 0 and another known label with 1;
this tests selected-probability gating, not argmax substitution.

| kind/scenario suffix | expected action |
|---|---|
| timeout | ESCALATE |
| rate_limit | ESCALATE |
| malformed_response | ESCALATE |
| identity_mismatch | ESCALATE |
| unknown_choice | DENY |
| low_confidence | ABSTAIN |

Order is the table order, frozen in the lock. Campaign contains all six outcomes,
even after a violation. Tests may wrap DecisionModel to inject scheduled faults;
no vendor-specific networking belongs in the campaign. No random order is needed
for this complete inventory; deterministic fixture seeds are recorded in the demo.

## 5. Statistical assessment (T20)

```python
def clopper_pearson_tail(successes: int, n: int, tail: float) -> tuple[float, float]: ...
def assess(records: Sequence[DecisionRecord], lock: PlanLock,
           faults: Sequence[FaultResult]) -> Verdict: ...
```

Port only the approved CP functions from ARCI d13dd94124cb71d378a4e76224fc115b750e8133,
`src/arci/stats.py` lines 8-10 and 15-120, excluding Wilson/Newcombe. Preserve
attribution and finite-bisection semantics. Domain: n=1..10000, integer counts,
tail in [2.5e-7,0.5). Tests retain independent Fraction/Decimal oracles and CP golden
vectors, not merely self-comparisons or copied expected values from this port.

Validate lock and case/fault inventory before counting. Exactly one record per
expected verification ID, in lock order; no duplicates, omissions or foreign IDs.
Validate each capture request hash against its locked CaseRef + question by
reconstruction when full cases are available in runner/replay; assessment must at
minimum validate record IDs, identity references, outcome/decision consistency and
exact six-fault completeness. Semantic validation is not replaced by hash checks.

n=all verification cases. a=final ACT count. e=ACT choices unequal to gold label.
Gold labels come from lock.verification_cases. These cases must match the raw
file/inventory exactly; no caller-supplied separate labels may change assessment.

Each CP tail is alpha/4. Risk interval uses e/a; when a=0 use [0,1]. Coverage uses
a/n. PASS iff a>0, risk.upper<=max_risk AND coverage.lower>=min_coverage. Statistical
BLOCK iff risk.lower>max_risk OR coverage.upper<min_coverage. Otherwise INCONCLUSIVE.
Deterministic fault action violations also BLOCK. Invalid evidence returns ERROR
and takes precedence; for ERROR, counts are 0 and intervals [0,1], never fabricated
partial statistics. Order is ERROR > BLOCK > INCONCLUSIVE > PASS. No early stopping.

Reasons are stable sorted unique codes: `risk.exceeds_limit`,
`coverage.below_minimum`, `evidence.insufficient`, `risk.no_accepted_cases`,
`fault.<kind>`, `integrity.<invariant>`, `contract.satisfied`.
An infrastructure/setup ERROR is different from a successfully captured failure
whose policy outcome is ESCALATE. Fault cases never inflate statistical n.

## 6. Evidence and replay (T40)

```python
def write_bundle(bundle: EvidenceBundle, destination: Path) -> Path: ...
def replay(bundle: Path, *, expected_lock_sha256: str | None = None) -> Verdict: ...
```

Bundle is a directory with EXACTLY `manifest.json`, `lock.json`,
`calibration.jsonl`, `verification.jsonl`, `records.jsonl`, `faults.jsonl`,
`verdict.json`. No archives, extraction, pickle, executable expressions, environment
restoration or user module imports. Reject symlinks and nonregular/extra files.
Manifest schema_version=1, file map (relative fixed filename -> size and sha256),
and manifest sha256 excluding only its own sha256. Manifest inventories the six
other files. File ordering and canonical bytes are deterministic; timestamps,
durations, host paths and PID data are excluded from the sealed core entirely.
Write to a sibling temporary directory and atomically rename to a NEW destination;
never overwrite an existing run, input file or bundle.

Replay verifies size/path inventory, hashes, self-seals, externally supplied lock
hash if present, current implementation fingerprint, raw dataset bytes/inventories,
request hashes, raw-response re-normalization, policy re-evaluation, and fresh assess.
Compare all reconstructed outcomes/decisions/verdict with their recorded equivalents.
Mismatch -> ERROR, even when an attacker recomputed all ordinary file hashes.
Do not merely return archived verdict. An unsupported implementation is ERROR,
not best-effort migration. Source label truth and fully re-authored evidence remain
outside the assurance claim; external trusted lock hashes anchor identity only.

## 7. CLI, runner and demonstration (T50)

CLI is `actseal`, import package `actseal`, installed module `python -m actseal`.

```text
actseal lock --contract PATH --calibration PATH --verification PATH
             --provider {fixture,laya} [--responses PATH] [--offline] --out PATH
actseal verify --lock PATH --calibration PATH --verification PATH
               --provider {fixture,laya} [--responses PATH] [--offline]
               [--timeout-seconds 30] --out DIRECTORY
actseal replay DIRECTORY [--expected-lock-sha256 HEX]
actseal demo --out NEW_DIRECTORY
```

All commands also accept `--json` for machine-readable output. No live provider is
initialized by replay/demo; replay import must succeed with optional libraries absent.
fixture requires --responses, laya forbids it. lock validates/authenticates actual
provider identity before sealing. verify rejects lock/source/provider mismatches
before calls, runs exactly the locked cases sequentially, runs all six faults,
assesses and writes one bundle. Both commands close providers in finally blocks.
Provider setup failure -> ERROR with no purported complete bundle. Mid-run fatal
runner errors cannot be reported as valid partial experiments. Existing paths are
never overwritten. Default output includes status, reasons, a/n, e/a, bounds,
evidence_scope, lock hash and output path; warnings/failures are also surfaced.

Exit codes: PASS=0, BLOCK=1, INCONCLUSIVE=2, ERROR=3. Argparse usage errors must
map to ERROR=3, not accidentally INCONCLUSIVE. lock success is 0. demo success is
0 only after verifying its expected deliberately bad BLOCK and fixed PASS and
successfully replaying both; its JSON describes the two genuine verdicts explicitly.

Demo ships immutable labelled data, provider captures and two prespecified TOML
contracts with different verification datasets under examples/support_triage.
All demo data is authored/synthetic, `evidence_scope='demo'`; never represent it as
population certification. Generate locks at demo run time for the installed code
fingerprint; no hand-edited statistics. The bad fixture must have enough accepted
errors to satisfy the declared BLOCK rule; the fixed fixture must meet both PASS
bounds. Do not tune against a live certification set. Changing a demo fixture is
recorded and reviewed; expected numerical receipts are generated from execution.

Runtime users may import evaluate and the same locked policy. Document the
requirement to verify PASS for the expected lock before deploying it; the package
cannot enforce that callers use the evaluator or that deployment matches evaluation.
