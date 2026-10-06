# Actseal wire schemas

JSON Schema (draft 2020-12) documents for the frozen 1.x wire formats listed in
the [stability manifest](../stability.md). They are documentation of the shapes
that `actseal` writes and accepts. The Python validators in `actseal.records`,
`actseal.serialization`, `actseal.evidence`, `actseal.cli` and
`actseal.compatibility` are authoritative and strictly **stricter**: they also
enforce the canonical byte form (sorted keys, compact separators, one terminal
LF per document or row, no NaN or Infinity, nesting at most 32, byte ceilings)
and the cross-field invariants listed per schema below, which JSON Schema
cannot express. A document that validates against a schema here may still be
rejected by Actseal; a document Actseal accepts always validates here.

| File | Describes | Version constant | Value |
|---|---|---|---|
| [lock.schema.json](lock.schema.json) | `lock.json`: the `PlanLock` document | `records.LOCK_SCHEMA_VERSION` | 2 |
| [manifest.schema.json](manifest.schema.json) | `manifest.json`: the bundle manifest | `evidence.BUNDLE_SCHEMA_VERSION` | 2 |
| [captured-outcome.schema.json](captured-outcome.schema.json) | `CapturedOutcome` as embedded in records and faults | bundle schema | 2 |
| [decision-record.schema.json](decision-record.schema.json) | one row of `records.jsonl` (`DecisionRecord`) | bundle schema | 2 |
| [fault-result.schema.json](fault-result.schema.json) | one row of `faults.jsonl` (`FaultResult`) | bundle schema | 2 |
| [verdict.schema.json](verdict.schema.json) | `verdict.json` (`Verdict`) | bundle schema | 2 |
| [cli-receipt.schema.json](cli-receipt.schema.json) | every `--json` receipt variant | `cli.RECEIPT_SCHEMA_VERSION` | 1 |
| [compatibility-registry.schema.json](compatibility-registry.schema.json) | `src/actseal/compatibility_registry.json` | `compatibility.REGISTRY_SCHEMA_VERSION` | 1 |

The contract TOML (schema 1) is not JSON and is specified in
[CONTRACTS](../../plan/CONTRACTS.md) section 3.

## Release receipts (release tooling, not the package)

The release workflow's helper, `tools/check_release.py`, writes three JSON
receipts per release. Their promotion-profile schemas live in the sibling
directory `docs/release-schemas/`, because this directory enumerates exactly
the formats the `actseal` package itself reads and writes. All three carry
`schema_version` 1 (`compatibility.RELEASE_RECEIPT_SCHEMA_VERSION`) and reject
unknown fields at every object level; see the
[versioning policy](../versioning.md#release-receipts-schema-1) and
[ADR 0016](../decisions/0016-release-promotion-and-receipts.md).

| File | Describes | Written by |
|---|---|---|
| [build-receipt.schema.json](../release-schemas/build-receipt.schema.json) | `build-receipt.json`: tag, source commit, `uv.lock` hash, originating run and the two built distributions | `check_release.py distributions` (build job) |
| [postpublish-receipt.schema.json](../release-schemas/postpublish-receipt.schema.json) | `postpublish-receipt.json`: official-PyPI download hashes, published metadata, attestation inspection and the clean-container smoke outcomes | `check_release.py postpublish` (pinned container) |
| [release-receipt.schema.json](../release-schemas/release-receipt.schema.json) | `release-receipt.json`: the binding of version, tag, commit, `uv.lock` hash, run/attempts, immutable artifact and the embedded post-publication evidence; mirrored to the draft GitHub release with `SHA256SUMS` | `check_release.py release-receipt` (mirror job) |

`lock_sha256` in these receipts is the SHA-256 of the repository `uv.lock` at
the source commit, not an Actseal decision lock. Inspection-only receipts (a
rehearsal build with a branch ref and null workflow metadata, a post-publication
run against a local or test index, or one that tolerated missing attestations)
deliberately fail these schemas and are never promoted. The helper is stricter
than the schemas: it rejects duplicate keys and nonfinite numbers while decoding,
requires exact integers where JSON Schema would accept `1.0`, and enforces the
cross-field equalities listed in the versioning policy. The provenance fields
record that attestation presence, trusted-publisher identity and statement
subjects were inspected; no cryptographic signature verification is claimed.
`tests/release/test_release_schemas.py` validates receipts the helper actually
writes against these schemas with the same local, non-fetching validator.

## Invariants not expressed in the schemas

**Lock.** `sha256` equals the canonical hash of the document with only `sha256`
omitted. `contract.policy.known_labels` equals the question option labels in
order; `allowed_labels` is a nonempty subset. Every `verification_cases[i]`
has the same `case_id` as `verification_inventory[i]` and an `expected_label`
among the known labels; each inventory entry's `sha256` is the canonical hash
of its case. Calibration and verification inventories share no case id.
`fault_inventory` equals the frozen six-scenario table. `replay_engine_version`
must be a supported engine and `implementation_sha256` must satisfy the
compatibility rules for the running release. A document with exactly the
eleven 0.1.0 fields at `schema_version` 1 is reported as legacy.

**Manifest.** `sha256` is the self-hash with only `sha256` omitted; every
`size` equals the file's byte length and every entry `sha256` its digest;
`lock.json` is at most 32 MiB and the seven files together at most 128 MiB.

**CapturedOutcome.** Exactly one of `body_json` and `failure_code` is present
(expressed with `oneOf`). `request_sha256` is the canonical hash of the
reconstructed `DecisionRequest`. `identity.provider` must be `fixture` or
`laya`; `artifact_hashes` and `runtime` keys are unique and serialized sorted.

**DecisionRecord / FaultResult.** `outcome` and `decision` must equal a fresh
re-normalization of `capture` against the locked identity and a fresh policy
evaluation. `ChoiceAnswer.selected_probability` equals the probability recorded
for `choice`; probability labels are unique, follow the question option order
and sum to 1 within 1e-12; `decision.fallback_used` equals
`outcome.fallback_used`; an answer outcome requires a captured `body_json`.
Records appear once per locked verification case in lock order; faults once
per locked scenario in lock order, with `request`/`capture` equal to the
canonical generator.

**Verdict.** `reasons` are sorted. `accepted <= total`, `errors <= accepted`,
`lower <= upper` in each interval. `ERROR` requires zero counts and `[0, 1]`
intervals; otherwise `total > 0`, and `PASS` requires `accepted > 0`.
`lock_sha256` equals the bundle's lock seal and `evidence_scope` the contract's.

**CLI receipt.** `exit_code` follows `status` (`PASS` 0, `BLOCK` 1,
`INCONCLUSIVE` 2, `ERROR` 3); `ok` is `exit_code == 0`. `demo.exit_code` is 0
only when both runs are `as_expected`. The shared `BundlePayload` definition
(verdict fields, `failures`, `warnings`, `faults`) carries no command-level
field: `exit_code`, `ok` and `out` belong to the `verify` receipt itself, and a
nested demo run has none of them.

These schemas are exercised by `tests/unit/test_schema_validation.py`, which
validates real product output (every bundle file, both demo runs and every CLI
receipt variant including error paths) with a Draft 2020-12 validator over a
local, non-fetching registry of these files.

**Compatibility registry.** Keys are exact fingerprints; duplicate keys are
rejected by the strict parser; the file is at most 1 MiB.
