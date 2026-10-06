# Actseal versioning policy

Status: normative for 1.x, frozen with Task 02 of the v1.0.0 plan. The
[stability manifest](stability.md) lists what the promises below apply to; the
[migration guide](migration.md) records the one deliberate break set at 1.0.0.

## Semantic versions

Actseal follows `MAJOR.MINOR.PATCH`.

| Change | Allowed in |
|---|---|
| Bug fixes that preserve every STABLE behaviour; reviewed compatibility registry entries approving an exact released source fingerprint for an existing engine | patch |
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

- the exact fingerprint of a reviewed, released source tree (never a
  speculative or future hash, never a wildcard or range);
- an archived-evidence regression test showing that evidence produced by that
  fingerprint replays under the engine with unchanged verdicts;
- review and acceptance recorded in the release plan. Codex approves the final
  1.0.0 runtime hash at integration (Task 19); the registry is empty until
  then, and the exact-source path works with an empty registry.

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

## Release provenance receipt (schema 1)

Release tooling, not the package, emits one JSON receipt per release. It binds:
the package version, the git tag, the source commit, the lock hash of the
release acceptance evidence, the CI workflow run, the immutable artifact ID,
every distribution filename with its size and SHA-256, and the verification
results (tests, metadata checks, post-publication install and replay). It
contains no credentials. Its field set is owned by the release workflow task
and versioned by `RELEASE_RECEIPT_SCHEMA_VERSION`.
