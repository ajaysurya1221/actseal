# Actseal v1 architecture

**Core accepted through T40; CLI/demo, final acceptance and release pending.** The implemented records, contracts, providers, assessment and evidence/replay have task acceptance. [T40's review](../plan/reviews/T40-02.md) records the latest core verification; it is not a CLI, quickstart or release receipt. [CONTRACTS](../plan/CONTRACTS.md) defines exact schemas/signatures; [STATE](../plan/STATE.md) tracks subsequent integration.

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

Locking performs no inference or threshold fitting. The pending CLI integration must construct the selected provider to observe identity before creating the lock. Raw input bytes, full verification cases and ordered inventories must agree. Duplicate IDs and exact repeated state text across/within splits are rejected; this does not establish semantic independence or honest withholding of labels. Shared bounded readers preserve raw UTF-8/newline bytes; structural lock decoding is followed by seal/implementation validation, as specified in [ADR 0010](decisions/0010-shared-bounded-input-helpers.md).

## Module boundaries

| Boundary | Responsibility |
|---|---|
| records / errors / serialization | Immutable validated records, bounded strict JSON, canonical bytes, hashes and installed-source fingerprint. |
| contract / locking / policy | Parse inputs, validate self-seals/inventories, evaluate the frozen selector. No provider or fault-runtime import in locking. |
| adapters / normalization | Capture provider-shaped data; separately validate identity, schema and selected probability. Normalization imports no model or adapter. |
| faults | Pure canonical capture generator and six-scenario campaign using the same normalizer/evaluator. No assessment/replay import. |
| stats / assessment | Audited CP kernel; complete semantic/inventory validation before risk/coverage assessment. |
| evidence / replay | Exclusive atomic publication of data-only bundles and fresh offline semantic recomputation. No provider imports or network calls. |
| runner / CLI / packaged demo — pending T50 | Compose accepted interfaces, enforce collection constants, close providers and expose explicit statuses. |

The decision-model boundary is `identity() -> ModelIdentity`, `decide(request, *, timeout_s) -> CapturedOutcome`, and `close() -> None`. v1 has a recorded fixture adapter and an optional pinned native Laya CPU adapter. Core fixture/replay paths require no model library, key or service. Jev and actual fallback execution are outside v1.

## Policy and provider behavior

Policy order is fixed: any fallback flag → ESCALATE; unknown-choice failure → DENY; other provider failure → ESCALATE; disallowed choice → DENY; selected probability below threshold → ABSTAIN; otherwise ACT. Only ACT carries a choice. A vendor confidence or action field cannot override this order; normalization must not replace the returned selected label with argmax.

Laya captures retain the complete native response, including answer IDs and usage/truncation diagnostics. Pre-inference token-layout validation and pure replayable response checks are both required. See [providers](providers.md) for exact pins, rounding tolerance and the published checkpoint calibration caveat.

The v1 collection protocol fixes startup at 120 seconds and each normal request at 30.0 seconds, with no deadline override; T50 must enforce these [ADR 0008](decisions/0008-fixed-collection-deadlines.md) constants through the fingerprint-bound runner. The accepted adapter terminates and joins its resident worker on timeout; later calls remain unavailable. Unexpected death/EOF/unusable IPC also invalidates it. The collector must retain every scheduled terminal record, without restart or replacement samples; full CLI collection remains pending.

Under [ADR 0009](decisions/0009-worker-loss-invalidates-statistical-run.md), a regular Laya timeout/unavailable invalidates the statistical experiment as ERROR, even when the captured failure correctly produces ESCALATE. Its bundle is diagnostic evidence. Canonical injected faults are separate, and nonfatal failures remain in a valid experiment's denominator.

The planned support-triage demo evaluates **different authored fixture outcomes under the same policy and limits**. Its two runs target BLOCK and PASS; they do not demonstrate a repaired model, a threshold fitted to observed outcomes or a paired model comparison. [ADR 0013](decisions/0013-prespecified-synthetic-demo.md) fixes the synthetic inputs before T50 implementation. Actual installed-demo receipts remain pending.

## Evidence boundary

Bundles contain exactly `manifest.json`, `lock.json`, `calibration.jsonl`, `verification.jsonl`, `records.jsonl`, `faults.jsonl` and `verdict.json`. Fresh replay must reconstruct semantics rather than return the archived verdict. An unsupported implementation fingerprint is ERROR; there is no automatic migration or resealing.

[ADR 0012](decisions/0012-replay-errors-and-exclusive-publication.md) publishes the completed sibling temporary directory through an operation that atomically refuses an existing destination. The private evidence helper uses macOS `renamex_np(RENAME_EXCL)` or Linux `renameat2(RENAME_NOREPLACE)` through stdlib `ctypes` and the system C library. Missing native support, unsupported filesystems/platforms and other publication errors fail explicitly, with no overwriting fallback. [T40 acceptance](../plan/reviews/T40-02.md) includes real exclusive-publication checks on both hosted operating systems. This promises neither support for every filesystem, power-loss durability nor protection against a hostile process replacing ancestor directories.

For invalid bundle evidence, replay returns ERROR. Before strict lock decoding succeeds, diagnostics use `evidence_scope=demo` and `lock_sha256` equal to 64 zero characters: an unknown-identity sentinel, never certification. After structural decoding, retain the decoded scope/hash even if later seal or integrity checks fail; these remain untrusted diagnostic values. Never substitute an expected external digest for the observed identity. ERROR counts are zero and intervals `[0,1]`. Invalid Python call arguments, including wrong types, malformed expected digests and NUL-bearing paths, may raise `SchemaError`; the planned CLI maps them to exit 3.

Integrity and replay do not authenticate authorship, actual inference, label truth or sampling history. A separately trusted lock hash anchors the expected identity only: an author can keep that lock while rewriting responses and recomputing consistent results. See [ADR 0005](decisions/0005-data-only-replay-and-trust.md), the [statistical contract](statistical-contract.md) and the [threat model](threat-model.md) before interpreting a PASS.
