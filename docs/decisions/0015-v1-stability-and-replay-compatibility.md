# ADR 0015: v1 public stability, strict formats and replay compatibility

- Status: accepted with the v1.0.0 plan (section E, amendment V1-003) and the
  Task 02 reviews; recorded here after implementation.
- Date: 2026-10-06.

## Decision

Actseal 1.x publishes a normative public surface in
[docs/stability.md](../stability.md) and a versioning policy in
[docs/versioning.md](../versioning.md). Every name in the manifest is STABLE
unless marked PROVISIONAL; existing convenience exports are enumerated, not
quietly made private. STABLE means compatible throughout 1.x; it does not
freeze model answers, caller paths, timings, incidental wording or the
*values* of identity and version constants.

**Strict formats do not gain fields.** Lock documents (schema 2), bundle
manifests (schema 2, which also versions the contained record encoding), CLI
JSON receipts (schema 1) and the compatibility registry (schema 1) are
described by published Draft 2020-12 schemas that reject unknown fields. An
existing schema version and the default CLI receipt shapes therefore never
gain a field within 1.x. A minor release may add commands, constants or
optional arguments whose defaults preserve existing behaviour; any additional
format or semantics ships as a separately versioned, explicitly opt-in
interface that leaves every existing stable surface unchanged. Removal and
incompatible change wait for 2.0, after documented deprecation of at least one
minor release and 90 days.

**Producer provenance and replay engine are separate.** `implementation_sha256`
remains the exact source fingerprint of the producer. `replay_engine_version`
(initially `actseal-choice-v1`) names the replay semantics. The shared
`validate_lock` accepts the exact running fingerprint under a supported
engine, or a producer/running pair whose fingerprints are both registered for
the lock's engine in the packaged registry. New collection requires the exact
running fingerprint. A new engine arrives only in a minor release, only as an
explicitly selected option, preserving existing engines, their semantics and
the default behaviour; evidence is interpreted through the engine recorded in
its lock and is never reinterpreted under a newer engine.

**The registry is explicit and exact.** `compatibility_registry.json` maps
full lowercase 64-hex source fingerprints to engine identifiers. The loader
rejects unknown fields, duplicate keys, malformed hashes, unsupported engines
and any wildcard or range form. Entries are added only by review with
archived-evidence regression tests; because every source change alters the
fingerprint, a reviewed exact-fingerprint entry for an existing engine may
ship in a patch release. The registry is trusted verifier configuration, not
proof of evidence authenticity. As decided, the registry stayed empty until
integration; the packaged 1.0.0 registry holds exactly the two mappings
recorded in the status section below.

**0.1.0 evidence is isolated, not migrated.** Schema-1 locks and manifests
are detected before generic decoding and rejected with `LegacySchemaError`
and operator guidance; replay reports `integrity.legacy_schema` with the
ADR 0012 unknown-identity sentinel. Legacy bytes are never rewritten or
resealed, and no converter presents a resealed document as the original
evidence. Historical replay uses an isolated pinned `actseal==0.1.0`
installation; a 1.0 evaluation creates a new lock and a separately identified
run.

**Security support covers the latest 1.x minor at its latest patch.** Legacy
0.1.0 replay availability is a compatibility path, not a promise to maintain
a 0.1 security branch.

## Consequences

Scripts consume versioned JSON receipts and can rely on exact receipt shapes
for the life of 1.x. Cross-release replay within 1.x is possible only through
reviewed registry entries; an unregistered pair is ERROR `integrity.lock`,
reporting the decoded lock digest, which is a verifier-configuration limit and
not a judgement on the evidence. Introducing a new wire field, a new engine or
a new output format is a deliberate, separately versioned act rather than an
incidental change.

## Evidence and validation

Task 02 and its repairs (reports 02, 02R2) implement these rules; the public
surface snapshot, compatibility, two-source-tree cross-release and genuine
schema validation tests enforce them. The receipt schema gained a shared
`BundlePayload` definition in 02R2 after review showed nested demo runs did
not carry command-level fields; that repair corrected the schema to the
shipped output, not the output to the schema.

## Status — 7 October 2026

Amendment V1-037 approved exactly two `actseal-choice-v1` entries after an
independent compatibility probe, and the packaged
`compatibility_registry.json` of 1.0.0 contains exactly them:
the 1.0.0 source fingerprint
`8f316f679b2ed5be4ce19127da87db21511ce4de2ff1450439fcf3c549598ed3` and the
original producer `a5fe090202f75b07510407937a86ae35a7653a75eab3f4daa2d0ace2e7641642`
of the retained `examples/action_gate/recorded/a5fe090202f7` archive (an
unreleased prerelease tree, not the released 0.1.0). Both are producer/engine
mappings, not an archive allowlist; the unchanged archive replays with its
full stored verdict under both, and empty, one-sided and wrong-engine
registries still reject it in explicit temporary fixtures. Any further Python
source change invalidates the first entry and requires a new fingerprint and
review ([versioning policy](../versioning.md)). That fingerprint is unchanged
through the pre-tag documentation and asset commits; the tag and publication
receipts are recorded in `plan/v1/RELEASE_NOTES.md`.

## Addendum — 8 October 2026: the 1.0.1 registry

Decision. Amendment V1-055 ([change log](../../plan/v1/CHANGE_LOG.md))
bundles the 1.0.1 hardening (streaming JSONL readers, the native IPC sequence
type check and the corrected numerical-kernel exception guide) with the
version bump and one registry entry. Replay semantics are unchanged, so this
is an addendum, not a new decision record. After every packaged Python change,
including the `1.0.1` version metadata, was final, the reviewed final
candidate's source fingerprint was computed by
`actseal.serialization.implementation_fingerprint()` and recomputed
independently with `hashlib` over the same sorted path-to-hash map:

`dced01d79e64799a19a75c0957f3684a48249c58ebb27d346336e7420195bcb4`

That exact mapping is added for `actseal-choice-v1` beside both entries
recorded above, which stay approved: the 1.0.1 registry holds exactly three
entries. This approves a reviewed release candidate before tagging and
publication; it does not record a release, and the tag and publication remain
separate steps with their own receipts. The pre-bump hardening fingerprint
was never a candidate and is not registered. As the
[versioning policy](../versioning.md#registry-approval-process) now states, a
later source change leaves an earlier entry approved for replay; that entry
simply no longer identifies the running source.

Evidence. With the three-entry registry the unchanged retained archive
`examples/action_gate/recorded/a5fe090202f7` replays to its entire stored
PASS verdict through the packaged registry, and
`examples/action_gate/run.py --check` reports no errors. The empty,
one-sided, other-producer and wrong-engine temporary registries still reject
it with `integrity.lock`, and its lock is still refused for new collection.
The exact-registry tests pin the three fingerprints as reviewed literals.
Merging the bundle requires its independent acceptance and green hosted CI on
the exact reviewed commit, recorded under `plan/v1/reviews/`.
