# Actseal versioning policy

Status: normative for 1.x, frozen with Task 02 of the v1.0.0 plan. The
[stability manifest](stability.md) lists what the promises below apply to; the
[migration guide](migration.md) records the one deliberate break set at 1.0.0.

## Semantic versions

Actseal follows `MAJOR.MINOR.PATCH`.

| Change | Allowed in |
|---|---|
| Bug fixes that preserve every STABLE behaviour; reviewed compatibility registry entries approving an exact reviewed source fingerprint (a released tree, or the named reviewed prerelease producer of retained schema-2 evidence) for an existing engine | patch |
| New commands, new constants, new optional arguments or flags whose defaults preserve existing behaviour; a new replay engine that must be explicitly selected; a separately versioned, explicitly opt-in interface for an additional format or semantics | minor |
| Adding a field to an existing strict schema version or to a default CLI receipt shape, removal of a STABLE name or flag, an incompatible change to a STABLE behaviour or schema, a new required constructor field | 2.0 only |

Stable 1.x schemas and semantics remain supported throughout 1.x. The
published schemas reject unknown fields, so an existing schema version (lock
2, manifest 2, receipt 1, registry 1) and the default CLI receipt shapes never
gain fields within 1.x; a new field is a new schema version or a new opt-in
interface, and every existing stable surface keeps working unchanged. A
STABLE surface is deprecated before it is removed: the deprecation is
documented in the changelog and the stability manifest, remains in place for
at least one minor release **and** at least 90 days, and the removal happens
only in 2.0. [ADR 0015](decisions/0015-v1-stability-and-replay-compatibility.md)
records these decisions.

PROVISIONAL surfaces (`actseal.experimental`, explicit experimental CLI flags)
carry no compatibility promise and may change in any release.

## Security support

Security fixes target the latest 1.x minor at its latest patch. Legacy 0.1.0
replay availability (an isolated pinned `actseal==0.1.0` installation, see the
[migration guide](migration.md)) is a compatibility path for reading historical
evidence; it is not a promise to maintain a 0.1 security branch indefinitely.

## Version constants

| Document | Constant | 1.0.0 value | Who reads it |
|---|---|---|---|
| Contract TOML | `actseal.records.CONTRACT_SCHEMA_VERSION` (alias `SCHEMA_VERSION`) | 1 | `parse_contract`, `Contract` |
| Lock document | `actseal.records.LOCK_SCHEMA_VERSION` | 2 | `PlanLock`, `parse_lock` |
| Bundle manifest and contained record encoding | `actseal.evidence.BUNDLE_SCHEMA_VERSION` | 2 | `write_bundle`, `read_bundle_files` |
| CLI JSON receipt | `actseal.cli.RECEIPT_SCHEMA_VERSION` | 1 | every `--json` receipt |
| Release provenance receipt | `actseal.compatibility.RELEASE_RECEIPT_SCHEMA_VERSION` | 1 | release tooling |
| Compatibility registry | `actseal.compatibility.REGISTRY_SCHEMA_VERSION` | 1 | `parse_registry` |

The manifest version also versions the canonical encoding of the records it
inventories (`lock.json`, `records.jsonl`, `faults.jsonl`, `verdict.json`); the
contained records carry no separate version field.

## Producer provenance versus replay engine

A lock records two different facts:

- `implementation_sha256` is **producer provenance**: the fingerprint of every
  installed `actseal/**/*.py` source file at collection time. Any source change,
  including a version bump, changes it.
- `replay_engine_version` names the **replay semantics** the evidence was
  produced under (`actseal-choice-v1` for 1.x: canonical encoding, policy
  precedence, normalizer behaviour, the six canonical faults and the
  Clopper-Pearson assessment).

Rules (`actseal.compatibility.check_replay_compatibility`, applied by the
shared `validate_lock`):

1. The engine must be supported by the running release.
2. The exact running fingerprint always validates under a supported engine.
3. Any other producer fingerprint validates only when **both** it and the
   running fingerprint are registered for that engine in the packaged
   `compatibility_registry.json`.
4. New collection (`collect`, `verify_run`) requires the exact running
   fingerprint regardless of the registry.

## Registry approval process

The registry ships as `{"schema_version": 1, "implementations": {"<full
lowercase 64-hex source SHA-256>": "<engine>"}}`. Approval of an entry requires:

- the exact fingerprint of a reviewed source tree (never a speculative or
  future hash, never a wildcard or range). Ordinarily that is a released tree;
  the one exception is a named, reviewed prerelease source whose retained
  schema-2 evidence ships with the package and is approved by an explicit,
  per-fingerprint amendment;
- an archived-evidence regression test showing that evidence produced by that
  fingerprint replays under the engine with unchanged verdicts;
- review and acceptance recorded in the release plan.

The 1.0.0 registry holds exactly two entries, both for `actseal-choice-v1`,
approved by amendment V1-037 after an independent compatibility probe:

| Fingerprint | Source | Status |
|---|---|---|
| `8f316f679b2ed5be4ce19127da87db21511ce4de2ff1450439fcf3c549598ed3` | the 1.0.0 source itself (final version metadata commit `0b57933`) | the running implementation of this release |
| `a5fe090202f75b07510407937a86ae35a7653a75eab3f4daa2d0ace2e7641642` | reviewed source `76758d7084e396c8960718d28c1cad5fb70bac03`, the producer of the retained `examples/action_gate/recorded/a5fe090202f7` archive | an **unreleased prerelease** tree carrying a `0.1.0` version string; it is not the released actseal 0.1.0 implementation, and its archive is schema-2 evidence, not legacy schema-1 evidence |

Each entry maps one exact producer fingerprint to one replay engine; that is
the whole content of the registry. It is producer/engine configuration, not
an allowlist of archives, bundles or lock digests: evidence produced by an
approved producer under that engine replays here whichever bundle it is in,
and the retained `examples/action_gate/recorded/a5fe090202f7` archive
(external lock digest
`cb009be0039afefd995f6eac3a8bd9767d6bf026a73273b47e87a51fc9fbd715`) is the
archived-evidence regression test that justified the second entry, not a
special case consulted at replay time. The second entry does not approve
other prerelease trees, any hash range, or evidence from any other producer,
and it does not claim that a release occurred at that source. Any later
change to the packaged Python sources changes the running fingerprint,
invalidates the first entry and requires a new fingerprint and review. The
exact-source path (rule 2) never consults the registry.

Because every source change, including a patch release, changes the
fingerprint, a reviewed entry approving an exact released fingerprint for an
existing engine may ship in a patch release. Approval is always explicit and
per fingerprint; there is no wildcard, range or "all patches of" form.

A new engine is a minor release and must be explicitly selected; existing
engines keep their semantics and remain the default behaviour. Evidence is
interpreted through the engine recorded in its lock and is never reinterpreted
under a newer engine.

The registry is trusted verifier configuration. It does not authenticate any
bundle, response or execution; it states which implementations a verifier is
willing to treat as equivalent for replay.

## Release receipts (schema 1)

Release tooling (`tools/check_release.py`), not the package, emits three JSON
receipts per release, all at `RELEASE_RECEIPT_SCHEMA_VERSION` 1 and described by
the strict promotion-profile schemas in `docs/schemas/` (see the
[wire schemas index](schemas/README.md#release-receipts-release-tooling-not-the-package)).
The build receipt records the tag, the source commit, the originating workflow
run and the two built distributions. The post-publication receipt records the
official-PyPI download hashes, the published metadata, the attestation
inspection and the clean-container demo/replay outcomes. The release receipt
binds the package version, the git tag, the source commit, the CI workflow run
with its build and verification attempts, the immutable Actions artifact ID and
digest, every distribution filename with its size and SHA-256, the verify-matrix
result and the embedded post-publication evidence; it is mirrored with
`SHA256SUMS` to the draft GitHub release. In the build and release receipts
`lock_sha256` is the SHA-256 of the repository `uv.lock` dependency lockfile at
the source commit; it is **not** an Actseal decision lock (`lock.json`) and
binds the release environment, not any evidence bundle. The post-publication
receipt has no such field. The receipts contain no credentials, and neither
they nor `SHA256SUMS` prove on their own that CI ran: when the pipeline
succeeds, each job compares the distribution hashes against the build
checksums and the receipts record those comparisons.
Their attestation fields record that PEP 740 attestation presence, the trusted
publisher identity and the statement subjects were inspected; they do not claim
cryptographic verification. Unknown fields are rejected at every level, so these
shapes never gain fields within schema 1; a receipt that fails promotion is never
rewritten to pass. [ADR 0016](decisions/0016-release-promotion-and-receipts.md)
records the promotion design.
