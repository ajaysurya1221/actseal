# ADR 0017: Optional experimental Jev decision provider behind an explicit flag

- Status: approved boundary (plan/v1/PLAN.md sections C and E; amendment
  V1-011); implementation source-scoped ACCEPT only, inclusion pending.
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
  never writes the key or authentication headers into requests-at-rest,
  captures, evidence, logs, diagnostics or locks.
- Gating uses the normalized **selected-option probability** from the
  returned distribution, not the vendor's confidence field; provider
  confidence is preserved as `provider_confidence` evidence only.
- Identity is the pinned, vendor-reported model target (`jev-1.13.0`) with an
  empty artifact-hash tuple. It is a vendor claim about a remote service, not a
  local artifact attestation, and must not be described as equivalent to the
  Laya adapter's verified weight hashes.
- One attempt per request with the fixed collection deadline: no retry, no
  redirect following, no fallback to another provider. Fault injection
  targets local transport doubles, never the live service.
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

- `records.PROVIDERS` and the CLI choices remain `fixture` and `laya` until
  integration explicitly registers the experimental provider (V1-011,
  Task 19). Documentation describes Jev as conditional preparation, not
  shipped behaviour.
- A provider-reported version can be wrong or change server-side; evidence
  collected through it carries that weaker identity claim visibly.
- If the adapter is not integrated and green by the recorded deadline it is
  cut to a later 1.x release; the cut changes no stable surface.

## Evidence and status

- Adapter and transport tests: source-scoped ACCEPT on PR 28 at
  `c2e27d2235eb98be0f97c9ec6d38b0c8ff235dfa`, eight hosted CI jobs passing.
  That acceptance covers the reviewed source only.
- Pending: runner/CLI registration, native receipts for changed paths, the
  `.env.example` placeholder file, live integration and the final inclusion
  decision. No live request, key or `.env` access was involved in recording
  this decision, and no v1 release has occurred.
- Related: [ADR 0004](0004-identity-normalization-fallback.md) (identity and
  fallback), [ADR 0015](0015-v1-stability-and-replay-compatibility.md)
  (PROVISIONAL surfaces), [providers](../providers.md).
