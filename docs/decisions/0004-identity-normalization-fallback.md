# ADR 0004: Normalize strictly and keep fallback outside certified action authority

- Status: accepted.
- Date: 2026-10-06.

## Decision

Separate provider transport, strict response normalization, pure policy evaluation, and application execution. A provider result cannot itself execute an action. Bind the frozen policy to its provider/model revision or artifact digest, prompt and question/choice inventory, preprocessing, decoding configuration, normalizer version, threshold, and label-to-action/error policy. Record the identity used for every case.

The normalizer rejects malformed structures, unsupported labels, non-finite/out-of-range scores, unexpected model identity, and other violations of the provider's documented categorical response contract. Do not repair malformed responses into confident decisions, coerce booleans into numeric probabilities, or substitute an identity alias without recording a different system. Provider-specific wire formats and exact signatures are frozen in [CONTRACTS](../../plan/CONTRACTS.md).

Policy precedence is deterministic:

1. A matching frozen hard-deny rule returns DENY.
2. Provider/identity/schema failure or use of an uncertified fallback returns ESCALATE.
3. A valid primary response below the frozen threshold returns ABSTAIN.
4. A valid primary response at or above the threshold returns ACT, with its frozen action mapping.

The optional Jev adapter reads `JEV_API_KEY` from the environment; no key is part of a lock, request record, report, or repository. A missing key, timeout, malformed response, or unavailable pinned model must be surfaced. The core and fixture quickstart remain keyless, and the real local model path uses open weights.

Jev-to-Laya fallback may supply a diagnostic recommendation. It must preserve `fallback_used`, the triggering failure, and both attempted identities, and return ESCALATE unless a separately certified chain exists. Such chain certification is v2. Fallback success cannot inherit the primary system's certification or enter the ACT numerator. A hard deny remains DENY.

## Consequences

Failure behavior is observable and testable. The integrating application remains responsible for honoring Actseal's returned disposition and for protecting its trusted policy. Provider confidence is a model score used by the frozen selector, not proof that an action is safe. The verification gate assesses empirical outcomes and declared contract behavior.
