# Migrating from actseal 0.1.0 to 1.0.0

Status: normative, frozen with Task 02 of the v1.0.0 plan. Read with the
[stability manifest](stability.md) and the [versioning policy](versioning.md).

## Summary

1.0.0 freezes the public surface and separates **producer provenance** from
**replay compatibility**. To do that it changes the lock and manifest formats
once. Existing 0.1.0 locks and evidence bundles are **not** converted: they
remain valid 0.1.0 evidence and replay under an isolated pinned 0.1.0
installation. Starting a 1.0 evaluation creates a new lock and a separately
identified run.

## Intentional breaks

| Area | 0.1.0 | 1.0.0 | Effect |
|---|---|---|---|
| Lock document | `schema_version` 1, eleven fields | `schema_version` 2, plus required final field `replay_engine_version` (`"actseal-choice-v1"`) inside the seal | 0.1.0 locks are rejected by `parse_lock` with `LegacySchemaError` and migration guidance; `PlanLock(...)` positional callers must append the engine string |
| Bundle manifest | `schema_version` 1 | `schema_version` 2 (also versions the contained record encoding) | 0.1.0 bundles are rejected by `read_bundle_files` with `LegacySchemaError`; `replay` returns ERROR with reason `integrity.legacy_schema` and the unknown-identity sentinel; the CLI exits 3 with the guidance in `notes` |
| Lock validation | `implementation_sha256` must equal the running fingerprint | Exact running fingerprint, **or** producer and running fingerprints both registered for the lock's engine | Within 1.x, approved prior releases replay; collection still requires the exact fingerprint |
| Collection | Checked through `validate_inputs` only | `collect()` and `verify_run` additionally call `require_exact_implementation` before any provider is built or asked to decide | A replay-compatible foreign lock can never be collected against |
| CLI JSON receipts | No version field | Top-level `schema_version: 1` on every receipt, including errors and usage errors | Consumers can discriminate receipt versions |
| `lock --json` | | Adds `replay_engine_version` | Additive |
| `replay --json` | | Adds `notes` (array of advisory strings) | Additive; text mode prints notes to stderr |
| CLI option parsing | Subcommands accepted abbreviated long options | Abbreviations rejected on the root parser and every subcommand | Scripts that relied on prefixes such as `--ou` must spell options in full |
| `records.SCHEMA_VERSION` | The single schema version (1) | Still 1, now documented as the contract TOML version; `CONTRACT_SCHEMA_VERSION` (1) and `LOCK_SCHEMA_VERSION` (2) added | Code that compared a lock's version with `SCHEMA_VERSION` must use `LOCK_SCHEMA_VERSION` |
| New module | | `actseal.compatibility` with the registry loader, compatibility rules and legacy detection | Additive |

## What is unchanged

- The contract TOML (schema 1), its exact shape and validation rules.
- Every record constructor except `PlanLock`, every alias and every error class.
- Canonical JSON encoding, hashing, the strict parser and its limits, and the
  implementation fingerprint algorithm.
- Policy precedence, denominators, the `alpha / 4` Clopper-Pearson allocation,
  verdict precedence and the six canonical faults.
- Provider protocol, fixture and Laya constructors, normalization behaviour.
- Commands, flags, exit codes and every existing receipt field and meaning.
- The numerical oracles and historical reports in this repository.

## Replaying 0.1.0 evidence

Legacy bytes are never rewritten. There is no converter that reseals a 0.1.0
lock or bundle and presents the result as the original evidence: a reseal
would be a new document with a new identity, not the evidence that was
collected. Replay historical evidence with the release that produced it, in an
isolated environment:

```bash
uvx actseal==0.1.0 replay DIRECTORY --json
```

or

```bash
pipx run actseal==0.1.0 replay DIRECTORY --json
```

or, in a dedicated virtual environment,

```bash
python -m venv actseal-0.1.0
actseal-0.1.0/bin/pip install actseal==0.1.0
actseal-0.1.0/bin/actseal replay DIRECTORY --json
```

Supply `--expected-lock-sha256` with the lock digest your own approval process
recorded for that run. 0.1.0 receipts carry no `schema_version` field.

## Starting a 1.0 evaluation

1. Keep the 0.1.0 contract TOML and datasets; they are unchanged.
2. Run `actseal lock` with the 1.0 installation. The new lock is schema 2, records
   the 1.0 implementation fingerprint and `replay_engine_version`, and has a new
   `lock_sha256`.
3. Run `actseal verify` against that new lock. The bundle manifest is schema 2.
4. Record the new lock digest in your approval process and replay with
   `--expected-lock-sha256`.

The 1.0 run is a separately identified experiment. Its verdict is not a
restatement of the 0.1.0 verdict, even when inputs and fixture responses are
identical.

## Cross-release replay inside 1.x

Later 1.x releases may replay 1.0.0 evidence once both fingerprints are
registered for `actseal-choice-v1` in the packaged registry (see the
[versioning policy](versioning.md)). The 1.0.0 registry approves exactly two
fingerprints: the 1.0.0 source itself and the unreleased prerelease producer
of the retained `examples/action_gate/recorded/a5fe090202f7` archive, so that
archive replays to its stored verdict under 1.0.0. That prerelease producer
carried a `0.1.0` version string but is not the released actseal 0.1.0: its
evidence is schema 2 and is unaffected by the legacy rule above. Evidence from
any other source tree is ERROR with reason `integrity.lock`, reporting the
decoded lock digest; the ERROR is a verifier-configuration limit, not a
statement that the evidence is invalid.
