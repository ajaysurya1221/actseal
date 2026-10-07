# ADR 0017: Optional experimental Jev decision provider behind an explicit flag

- Status: approved boundary (plan/v1/PLAN.md sections C and E; amendment
  V1-011); included in the 1.0.0 candidate as PROVISIONAL (V1-036) with the
  explicit CLI opt-in integrated; no accepted live evidence.
- Date: 2026-10-07.

## Decision

Actseal may ship a cloud decision provider for the proprietary TypeSafe/Jev
service only as a **PROVISIONAL** adapter at
`actseal.experimental.providers.jev.JevModel(*, offline: bool = False)`,
selectable solely through `--provider jev --experimental-provider`. It is
never selected implicitly, carries no 1.x compatibility promise, and may
change or be removed in any release under the
[stability manifest](../stability.md).

The boundary is fixed by the approved plan:

- The zero-dependency core, the `fixture` provider, the optional `laya`
  adapter, assessment and replay stay fully usable without any key or
  account. Making a proprietary service necessary for v1 would contradict
  the project's core.
- The service is proprietary and bring-your-own-key: the adapter reads only
  `JEV_API_KEY`, rejects offline or missing-key setup before any request, and
  never writes the key or authentication headers into the captures, evidence,
  logs, diagnostics or locks it owns. The reviewed guard detects the literal
  key and a limited set of JSON escapings in material it records; it does not
  promise to sanitize arbitrarily encoded secret material that a malicious
  provider body might contain, so raw bodies remain data to review before
  sharing.
- Gating uses the normalized **selected-option probability** from the
  returned distribution, not the vendor's confidence field; provider
  confidence is preserved as `provider_confidence` evidence only.
- Identity is the pinned, vendor-reported model target (`jev-1.13.0`) with an
  empty artifact-hash tuple. It is a vendor claim about a remote service, not a
  local artifact attestation, and must not be described as equivalent to the
  Laya adapter's verified weight hashes.
- One attempt per request with a validated per-request timeout: no retry, no
  redirect following, no fallback to another provider. Callers keep the fixed
  collection schedule and deadline; timeout behaviour is bounded as specified
  for the transport, which is not a universal hard wall-clock bound on
  operating-system or network operations. Fault injection targets local
  transport doubles, never the live service.
- Replay imports no transport module; successful raw bodies are preserved so
  recorded evidence normalizes offline.

## Rationale

Both research tracks supported attempting an optional adapter with a real
recorded audit, and the user authorized meaningful credit use for it. A
PROVISIONAL surface lets that evidence be gathered without widening the
stable provider set (`fixture`, `laya`) or the frozen policy and statistical
semantics. The plan's reading of the vendor terms (customer API integrations
permitted; no credential sharing, resale, distillation or training from
outputs) is a bounded interpretation recorded for engineering scope, not a
legal guarantee; this ADR does not refresh or re-interpret those terms.

## Consequences

- `jev` is admitted in serialized records and the published schemas
  (V1-011, V1-021) so that captures and faults can carry its identity; the
  stable default CLI choices remain `fixture` and `laya`, and `jev` is
  reachable only through the explicit experimental opt-in. (Historical
  status, superseded: when this ADR was first written the opt-in was not yet
  integrated and documentation described Jev as conditional preparation; the
  integrated state is recorded in "Evidence and status" below.)
- A provider-reported version can be wrong or change server-side; evidence
  collected through it carries that weaker identity claim visibly.
- If the adapter is not integrated and green by the recorded deadline it is
  cut to a later 1.x release; the cut changes no stable surface.

## Evidence and status

- Adapter and transport tests: source-scoped ACCEPT on PR 28 at
  `c2e27d2235eb98be0f97c9ec6d38b0c8ff235dfa`, eight hosted CI jobs passing.
  That acceptance covers the reviewed source only. On that source `jev` is
  admitted in `records.PROVIDERS` and the schemas for serialized identities,
  `open_model` refuses it explicitly, and the `.env.example` placeholder was
  verified to contain exactly one empty assignment (V1-029).
- Native checks at `c2e27d2`: the five cached-native tests passed
  independently alongside the 390 focused offline tests for that source
  (plan/v1/STATE.md, Task 05 row). That receipt covers the reviewed Task 05
  source only; the final Task 19 integration (CLI opt-in, runner registration
  and any registry entry) changes source and therefore requires its own
  native revalidation before acceptance.
- Status on 7 October 2026 (1.0.0 candidate, source fingerprint
  `8f316f67…98ed3`): the inclusion decision is **retain as PROVISIONAL**
  (V1-036). The explicit CLI opt-in `--provider jev --experimental-provider`
  and the `open_model("jev", ...)` branch are integrated and scoped-accepted
  (Task 19 `b0031f5`); the shared conformance suite, canonical fault campaign
  and CLI/runner routing are exercised over mocked transports with every
  socket blocked; the cached-native checks were repeated at that integration
  (six tests) with no skips. Hosted CI on the candidate fails only for the
  absent architecture figure, not for any provider test.
- Live evidence (status as of 7 October 2026): live collection has not
  begun and no live Jev result is accepted as evidence; the Task 06
  operational receipts under `plan/v1/reviews/` and `plan/v1/reports/` hold
  the chronology. The Jev prerelease producer fingerprint is not in the
  compatibility registry. No v1 release has occurred.
- Related: [ADR 0004](0004-identity-normalization-fallback.md) (identity and
  fallback), [ADR 0015](0015-v1-stability-and-replay-compatibility.md)
  (PROVISIONAL surfaces), [providers](../providers.md).
