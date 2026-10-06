# ADR 0005: Replay data through pure logic and require external trust for provenance

- Status: accepted.
- Date: 2026-10-06.

## Decision

An evidence bundle contains bounded JSON data: the frozen lock, expected case inventory, recorded provider response bodies, normalized outcomes, fault-test observations, and derived policy/statistical results. Replay imports no bundle-supplied code, provider module, or model; restores no environment variables; and makes no network call. It re-normalizes recorded bodies and recomputes the deterministic policy and statistical gate.

Verify schema/version support, byte/content digests, lock identity, nested record integrity, and exact inventory completeness before accepting a replay. Reject missing, duplicate, foreign, or mismatched cases. Any discrepancy between stored and re-derived normalized outcomes or results is ERROR. A recorded provider failure remains valid data that can produce ESCALATE; corrupting its evidence is a distinct ERROR.

Use canonical serialization with sorted keys, compact separators, UTF-8, and rejection of non-finite numbers. Define hash inclusion precisely in the frozen contract, including which fields are volatile. Never exclude arbitrary user payload fields merely because their names resemble timestamps or digests. Do not persist authorization headers or credentials; publish only reviewed synthetic example bodies in the initial release.

## Trust boundary

A self-contained digest can detect a changed record only relative to a trusted expected digest. Anyone able to rewrite an entire bundle can recompute its internal hashes. Successful internal replay proves consistency with the supplied evidence, not who produced it, whether the provider was actually contacted, or whether its labels were honestly selected.

For provenance-sensitive use, the caller must obtain the expected lock/bundle digest through a separately trusted channel and compare it before use. A mutable digest stored beside the bundle is not that channel. v1 does not implement signatures, a signing service, remote attestation, or a tamperproof ledger. The runtime receives an already trusted locked policy from its host; parsing a submitted lock must not silently make it authoritative.

See [CONTRACTS](../../plan/CONTRACTS.md) for exact evidence schemas and CLI behavior. Publication copy must distinguish **integrity/replay** from **authenticated provenance**.
