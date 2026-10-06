# ADR 0005: Replay data through pure logic and require external trust for provenance

- Status: accepted.
- Date: 2026-10-06.

## Decision

An evidence bundle contains bounded JSON data: the frozen lock, expected case inventory, recorded provider response bodies, normalized outcomes, fault-test observations, and derived policy/statistical results. Replay imports no bundle-supplied code, provider module, or model; restores no environment variables; and makes no network call. It re-normalizes recorded bodies and recomputes the deterministic policy and statistical gate.

Verify schema/version support, byte/content digests, lock identity, nested record integrity, and exact inventory completeness before accepting a replay. Reject missing, duplicate, foreign, or mismatched cases. Any discrepancy between stored and re-derived normalized outcomes or results is ERROR. A recorded provider failure remains valid data that can produce ESCALATE; corrupting its evidence is a distinct ERROR.

Use canonical serialization with sorted keys, compact separators, UTF-8, and rejection of non-finite numbers. Define hash inclusion precisely in the frozen contract, including which fields are volatile. Never exclude arbitrary user payload fields merely because their names resemble timestamps or digests. Do not persist authorization headers or credentials; publish only reviewed synthetic example bodies in the initial release.

## Trust boundary

A self-contained digest can detect a changed record only relative to a trusted expected digest. Anyone able to rewrite an entire bundle can recompute its internal hashes. Successful internal replay proves consistency with the supplied evidence, not who produced it, whether the provider was actually contacted, or whether its labels were honestly selected.

An expected lock digest obtained through a separately trusted channel anchors the expected locked identity only. It does not authenticate response records, provider calls or execution: an author can retain the same lock while replacing responses and recomputing internally consistent outcomes, verdicts and bundle hashes. Comparing an external lock digest must not be presented as authenticating those rewritten responses.

A separately trusted digest of the complete bundle can anchor those exact bundle bytes, but even that comparison alone does not prove honest inference, labels or sampling history. A mutable digest stored beside an untrusted bundle is not an external trust channel. The v1 CLI accepts an expected **lock** digest; it does not implement full-bundle attestation, signatures, a signing service, remote attestation or a tamperproof ledger. The runtime receives an already trusted locked policy from its host; parsing a submitted lock must not silently make it authoritative.

See [CONTRACTS](../../plan/CONTRACTS.md) for exact evidence schemas and CLI behavior. Publication copy must distinguish **integrity/replay** from **authenticated provenance**.
