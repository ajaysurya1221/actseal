# Actseal v1 architecture

The [stability manifest](stability.md), [versioning policy](versioning.md),
[migration guide](migration.md) and [wire schemas](schemas/README.md) are
normative for 1.x. [CONTRACTS](../plan/CONTRACTS.md) is the historical v0.1
core contract that those documents superseded; it remains the record of the
unchanged statistical and policy semantics. The [CLI review](../plan/reviews/T50-02.md)
and [native integration receipt](../plan/reports/T70-native.md) record the
v0.1 tested product paths; the 1.0.0 candidate's receipts are under `plan/v1/`.

Actseal evaluates one frozen categorical decision policy. The application supplies a question with 2–16 labels, an allowed-label subset, a prespecified selected-probability threshold and risk/coverage limits. The application remains responsible for obeying the returned disposition and deploying the same trusted policy/system that was evaluated.

## Data flow

```text
TOML contract + labelled calibration/verification JSONL + observed model identity
  -> strict parsing and literal-overlap checks
  -> PlanLock: raw hashes, ordered cases, policy, model/runtime, implementation
  -> capture every scheduled verification request once, in order
  -> pure normalization -> deterministic policy -> DecisionRecord
  -> six canonical fault scenarios, recorded separately
  -> semantic validation and statistical assessment -> Verdict
  -> exclusive atomic publication of a new data-only evidence directory

Evidence directory
  -> bounded file/schema/hash/lock checks
  -> reconstruct requests, normalize raw captures and evaluate policy again
  -> validate canonical faults and recompute assessment
  -> compare stored and reconstructed results -> matching verdict or ERROR
```

Locking performs no inference or threshold fitting. The CLI constructs the selected provider to observe identity before creating the lock. Raw input bytes, full verification cases and ordered inventories must agree. Duplicate IDs and exact repeated state text across/within splits are rejected; this does not establish semantic independence or honest withholding of labels. Shared bounded readers preserve raw UTF-8/newline bytes; structural lock decoding is followed by seal/implementation validation, as specified in [ADR 0010](decisions/0010-shared-bounded-input-helpers.md).

## Module boundaries

| Boundary | Responsibility |
|---|---|
| records / errors / serialization | Immutable validated records, bounded strict JSON, canonical bytes, hashes and installed-source fingerprint. |
| contract / locking / policy | Parse inputs, validate self-seals/inventories, evaluate the frozen selector. No provider or fault-runtime import in locking. |
| adapters / normalization | Capture provider-shaped data (`adapters.fixture`, `adapters.laya`, and the PROVISIONAL `experimental.providers.jev`); separately validate identity, schema and selected probability. Normalization imports no model, adapter or transport. |
| faults | Pure canonical capture generator and six-scenario campaign using the same normalizer/evaluator. No assessment/replay import. |
| stats / assessment | Audited CP kernel; complete semantic/inventory validation before risk/coverage assessment. |
| evidence / replay | Exclusive atomic publication of data-only bundles and fresh offline semantic recomputation. No provider imports or network calls. |
| runner / CLI / packaged demo | Compose accepted interfaces, enforce collection constants, close providers and expose explicit statuses. |

The decision-model boundary is `identity() -> ModelIdentity`, `decide(request, *, timeout_s) -> CapturedOutcome`, and `close() -> None`. 1.x has a recorded fixture adapter and an optional pinned native Laya CPU adapter as stable providers, plus the PROVISIONAL experimental Jev cloud adapter (`actseal.experimental.providers.jev`), selectable only with `--provider jev --experimental-provider` and carrying no compatibility promise or accepted live evidence; see [providers](providers.md). Core fixture/replay paths require no model library, key or service. Actual fallback execution is outside v1.

## Policy and provider behavior

Policy order is fixed: any fallback flag → ESCALATE; unknown-choice failure → DENY; other provider failure → ESCALATE; disallowed choice → DENY; selected probability below threshold → ABSTAIN; otherwise ACT. Only ACT carries a choice. A vendor confidence or action field cannot override this order; normalization must not replace the returned selected label with argmax.

Laya captures retain the complete native response, including answer IDs and usage/truncation diagnostics. Pre-inference token-layout validation and pure replayable response checks are both required. See [providers](providers.md) for exact pins, rounding tolerance and the published checkpoint calibration caveat.

The v1 collection protocol fixes startup at 120 seconds and each normal request at 30.0 seconds, with no deadline override; the fingerprint-bound runner enforces these [ADR 0008](decisions/0008-fixed-collection-deadlines.md) constants. The worker semantics are Laya-specific: the native adapter runs one resident model in a spawned worker process, terminates and joins it on timeout, and leaves later calls unavailable; unexpected death/EOF/unusable IPC also invalidates it. The fixture adapter reads one local file in process, and the experimental Jev adapter makes one in-process stdlib HTTPS attempt per request with the deadline as its socket timeout (not a hard wall-clock bound). The collector retains every scheduled terminal record without restart or replacement samples for every provider.

Under [ADR 0009](decisions/0009-worker-loss-invalidates-statistical-run.md), a regular Laya timeout/unavailable invalidates the statistical experiment as ERROR, even when the captured failure correctly produces ESCALATE. Its bundle is diagnostic evidence. That rule is specific to the resident native worker; a fixture or Jev `timeout`/`unavailable` capture is an ordinary terminal failure record that stays in the denominator and escalates. Canonical injected faults are separate, and nonfatal failures remain in a valid experiment's denominator.

The support-triage demo evaluates **different authored fixture outcomes under the same policy and limits**. Its two authored runs produce BLOCK and PASS; they do not demonstrate a repaired model, a threshold fitted to observed outcomes or a paired model comparison. [ADR 0013](decisions/0013-prespecified-synthetic-demo.md) fixes the synthetic inputs before T50 implementation. [T50 acceptance](../plan/reviews/T50-02.md) records actual installed-demo results and matching cross-platform evidence.

## Evidence boundary

Bundles contain exactly `manifest.json`, `lock.json`, `calibration.jsonl`, `verification.jsonl`, `records.jsonl`, `faults.jsonl` and `verdict.json`. Fresh replay must reconstruct semantics rather than return the archived verdict. An unsupported implementation fingerprint is ERROR; there is no automatic migration or resealing.

[ADR 0012](decisions/0012-replay-errors-and-exclusive-publication.md) publishes the completed sibling temporary directory through an operation that atomically refuses an existing destination. The private evidence helper uses macOS `renamex_np(RENAME_EXCL)` or Linux `renameat2(RENAME_NOREPLACE)` through stdlib `ctypes` and the system C library. Missing native support, unsupported filesystems/platforms and other publication errors fail explicitly, with no overwriting fallback. [T40 acceptance](../plan/reviews/T40-02.md) includes real exclusive-publication checks on both hosted operating systems. This promises neither support for every filesystem, power-loss durability nor protection against a hostile process replacing ancestor directories.

For invalid bundle evidence, replay returns ERROR. Before strict lock decoding succeeds, diagnostics use `evidence_scope=demo` and `lock_sha256` equal to 64 zero characters: an unknown-identity sentinel, never certification. After structural decoding, retain the decoded scope/hash even if later seal or integrity checks fail; these remain untrusted diagnostic values. Never substitute an expected external digest for the observed identity. ERROR counts are zero and intervals `[0,1]`. Invalid Python call arguments, including wrong types, malformed expected digests and NUL-bearing paths, may raise `SchemaError`; the CLI maps them to exit 3.

Integrity and replay do not authenticate authorship, actual inference, label truth or sampling history. A separately trusted lock hash anchors the expected identity only: an author can keep that lock while rewriting responses and recomputing consistent results. See [ADR 0005](decisions/0005-data-only-replay-and-trust.md), the [statistical contract](statistical-contract.md) and the [threat model](threat-model.md) before interpreting a PASS.

## Python API

Import the protocol and pure functions from their modules:

```python
from actseal.adapters.base import DecisionModel
from actseal.normalization import normalize
from actseal.policy import evaluate
from actseal.replay import replay
```

`DecisionModel` describes `identity()`, `decide(request, *, timeout_s)` and
`close()`. It is a protocol, not a model constructor. Importing these modules
does not load an optional model stack.

Before deploying a policy, replay its evidence against a lock hash obtained
through your own trusted configuration or approval process. Supply the actual
64-character lowercase SHA256 digest; reading it from the same bundle does not
establish an independent trust anchor. This integration fragment assumes
`bundle_path` and `trusted_lock_sha256` were supplied by your application:

```python
verdict = replay(bundle_path, expected_lock_sha256=trusted_lock_sha256)
if verdict.status != "PASS":
    raise RuntimeError("Decision policy has no matching PASS evidence")
```

A demo PASS establishes only the authored demonstration's result. Population
interpretation requires the statistical contract's sampling assumptions and
appropriate evidence scope. Even a trusted lock hash does not authenticate
provider responses, execution history or gold labels.

Use the exact validated lock, its question and its unchanged policy in the
application. Compare the model's complete `identity()` with
`lock.model_identity` before requests. Construct each `DecisionRequest` with
`lock.contract.question`, capture once, then apply the same pure path used by
assessment and replay:

```python
capture = model.decide(request, timeout_s=30.0)
outcome = normalize(capture, lock.contract.question, lock.model_identity)
decision = evaluate(outcome, lock.contract.policy)
```

Here `model` implements `DecisionModel`; `lock` and `request` are validated
application inputs. Keep capture/outcome warnings visible, retain failure
details, and close the provider in a `finally` block. The application must check
`decision.action` before performing any side effect:

| Action | Caller behavior |
| --- | --- |
| `ACT` | Execute only the returned permitted `choice`. |
| `ABSTAIN` | Do not execute; use the application's abstention path. |
| `ESCALATE` | Do not execute; route for review or explicit recovery. |
| `DENY` | Reject the proposed action. |

This runnable, synthetic example shows only the evaluator's return value; it
does not establish PASS evidence or population performance:

```python
from actseal.policy import evaluate
from actseal.records import ChoiceAnswer, LockedPolicy

policy = LockedPolicy(("billing", "technical"), ("billing",), 0.90)
answer = ChoiceAnswer(
    choice="billing",
    probabilities=(("billing", 0.95), ("technical", 0.05)),
    selected_probability=0.95,
    provider_confidence=None,
    warnings=(),
    fallback_used=False,
)
decision = evaluate(answer, policy)
print(decision.action, decision.choice, decision.reason)
# ACT billing policy.allowed
```

`evaluate` applies one policy to one normalized outcome. It neither certifies a
population nor enforces an outer application's behavior. A deployment must keep
the evaluated policy/model configuration and relevant operating regime fixed;
changing them requires new evidence. Handle all four actions explicitly.
