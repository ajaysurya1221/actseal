# ADR 0004: Normalize strictly and keep fallback outside certified action authority

- Status: accepted.
- Date: 2026-10-06.

## Decision

Separate provider transport, strict response normalization, pure policy evaluation, and application execution. A provider result cannot itself execute an action. Bind the frozen policy to its provider/model revision or artifact digest, prompt and question/choice inventory, preprocessing, decoding configuration, normalizer version, threshold, and label-to-action/error policy. Record the identity used for every case.

The normalizer rejects malformed structures, unsupported labels, non-finite/out-of-range scores, unexpected model identity, and other violations of the provider's documented categorical response contract. Do not repair malformed responses into confident decisions, coerce booleans into numeric probabilities, or substitute an identity alias without recording a different system. Provider-specific wire formats and exact signatures are frozen in [CONTRACTS](../../plan/CONTRACTS.md).

Policy precedence is deterministic:

1. Any fallback_used outcome returns ESCALATE.
2. An unknown choice returns DENY; other provider/identity/schema failures return ESCALATE.
3. A valid but disallowed choice returns DENY.
4. An allowed choice below threshold returns ABSTAIN; at or above threshold returns ACT.

Jev and actual fallback execution are deferred to v2. An eventual adapter reads `JEV_API_KEY` from the environment; no key is part of a lock, request record, report, or repository. A missing key, timeout, malformed response, or unavailable pinned model must be surfaced. The core and fixture quickstart remain keyless, and the real local model path uses open weights.

Future Jev-to-Laya fallback may supply a diagnostic recommendation. It must preserve `fallback_used`, the triggering failure, and both attempted identities, and return ESCALATE unless a separately certified chain exists. Fallback success cannot inherit the primary system's certification or enter the ACT numerator. v1 has no fallback execution.

## Status — 7 October 2026

The paragraphs above record the 6 October decision as made. Since then the
Jev adapter exists in the 1.0.0 candidate as `actseal.experimental.providers.jev`,
PROVISIONAL and selectable only with `--provider jev --experimental-provider`
([ADR 0017](0017-experimental-decision-provider.md)); it reads `JEV_API_KEY`
only at construction, keeps the key out of identity, captures, locks and
diagnostics, and surfaces missing-key, timeout, malformed-response and
unavailable outcomes as specified here. No live Jev request has been accepted
as evidence. Actual fallback execution remains outside v1 exactly as decided;
the `fallback_used` precedence is unchanged.

## Consequences

Failure behavior is observable and testable. The integrating application remains responsible for honoring Actseal's returned disposition and for protecting its trusted policy. Provider confidence is a model score used by the frozen selector, not proof that an action is safe. The verification gate assesses empirical outcomes and declared contract behavior.
