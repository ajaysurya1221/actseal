# Actseal v1 architecture

**Normative design; complete implementation verification pending.** This document describes required v0.1.0 behavior, not a shipped-capability receipt. [CONTRACTS](../plan/CONTRACTS.md) defines exact schemas and signatures; [STATE](../plan/STATE.md) and the [release checklist](../plan/RELEASE_CHECKLIST.md) record acceptance status.

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
  -> atomic new data-only evidence directory

Evidence directory
  -> bounded file/schema/hash/lock checks
  -> reconstruct requests, normalize raw captures and evaluate policy again
  -> validate canonical faults and recompute assessment
  -> compare stored and reconstructed results -> matching verdict or ERROR
```

Locking performs no inference or threshold fitting. The CLI constructs the selected provider to observe identity before creating the lock. Raw input bytes, full verification cases and ordered inventories must agree. Duplicate IDs and exact repeated state text across/within splits are rejected; this does not establish semantic independence or honest withholding of labels.

## Module boundaries

| Boundary | Responsibility |
|---|---|
| records / errors / serialization | Immutable validated records, bounded strict JSON, canonical bytes, hashes and installed-source fingerprint. |
| contract / locking / policy | Parse inputs, validate self-seals/inventories, evaluate the frozen selector. No provider or fault-runtime import in locking. |
| adapters / normalization | Capture provider-shaped data; separately validate identity, schema and selected probability. Normalization imports no model or adapter. |
| faults | Pure canonical capture generator and six-scenario campaign using the same normalizer/evaluator. No assessment/replay import. |
| stats / assessment | Audited CP kernel; complete semantic/inventory validation before risk/coverage assessment. |
| evidence / replay | Atomic data-only bundles and fresh offline semantic recomputation. No provider imports or network calls. |
| runner / CLI / packaged demo | Compose accepted interfaces, enforce collection constants, close providers and expose explicit statuses. |

The decision-model boundary is `identity() -> ModelIdentity`, `decide(request, *, timeout_s) -> CapturedOutcome`, and `close() -> None`. v1 has a recorded fixture adapter and an optional pinned native Laya CPU adapter. Core fixture/replay paths require no model library, key or service. Jev and actual fallback execution are outside v1.

## Policy and provider behavior

Policy order is fixed: any fallback flag → ESCALATE; unknown-choice failure → DENY; other provider failure → ESCALATE; disallowed choice → DENY; selected probability below threshold → ABSTAIN; otherwise ACT. Only ACT carries a choice. A vendor confidence or action field cannot override this order; normalization must not replace the returned selected label with argmax.

Laya captures retain the complete native response, including answer IDs and usage/truncation diagnostics. Pre-inference token-layout validation and pure replayable response checks are both required. See [providers](providers.md) for exact pins, rounding tolerance and the published checkpoint calibration caveat.

The evidence-producing runner fixes startup at 120 seconds and each normal request at 30.0 seconds. These constants are bound through the implementation fingerprint; no deadline override exists in v1. A timeout terminates and joins the resident worker; later calls remain unavailable. Unexpected death/EOF/unusable IPC also invalidates it. Every scheduled terminal record is retained, without restart or replacement samples.

Under [ADR 0009](decisions/0009-worker-loss-invalidates-statistical-run.md), a regular Laya timeout/unavailable invalidates the statistical experiment as ERROR, even when the captured failure correctly produces ESCALATE. Its bundle is diagnostic evidence. Canonical injected faults are separate, and nonfatal failures remain in a valid experiment's denominator.

## Evidence boundary

Bundles contain exactly `manifest.json`, `lock.json`, `calibration.jsonl`, `verification.jsonl`, `records.jsonl`, `faults.jsonl` and `verdict.json`. Fresh replay must reconstruct semantics rather than return the archived verdict. An unsupported implementation fingerprint is ERROR; there is no automatic migration or resealing.

Integrity and replay do not authenticate authorship, actual inference, label truth or sampling history. See the [statistical contract](statistical-contract.md) and [threat model](threat-model.md) before interpreting a PASS.
