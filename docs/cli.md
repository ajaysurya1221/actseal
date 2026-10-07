# Actseal command-line reference

The console script `actseal` and `python -m actseal` are the same program.
Commands are exactly `lock`, `verify`, `replay` and `demo`. This page documents
the signatures that the [stability manifest](stability.md) freezes for 1.x;
the manifest is normative where the two differ. The receipts are described by
[cli-receipt.schema.json](schemas/cli-receipt.schema.json).

## Signatures

```text
actseal [-h] [--version] COMMAND ...
actseal lock [-h] --contract PATH --calibration PATH --verification PATH
             --provider {fixture,laya} [--responses PATH] [--offline]
             --out PATH [--json]
actseal verify [-h] --lock PATH --calibration PATH --verification PATH
               --provider {fixture,laya} [--responses PATH] [--offline]
               --out DIRECTORY [--json]
actseal replay [-h] [--expected-lock-sha256 HEX] [--json] DIRECTORY
actseal demo [-h] --out NEW_DIRECTORY [--json]
```

| Command | Required | Optional |
|---|---|---|
| `lock` | `--contract PATH`, `--calibration PATH`, `--verification PATH`, `--provider {fixture,laya}`, `--out PATH` | `--responses PATH`, `--offline`, `--json` |
| `verify` | `--lock PATH`, `--calibration PATH`, `--verification PATH`, `--provider {fixture,laya}`, `--out DIRECTORY` | `--responses PATH`, `--offline`, `--json` |
| `replay` | `DIRECTORY` (positional bundle directory) | `--expected-lock-sha256 HEX`, `--json` |
| `demo` | `--out NEW_DIRECTORY` | `--json` |
| root | `COMMAND` | `--version` (root only), `-h`/`--help` |

Rules that apply to every command:

- **No abbreviated options.** `--ou` is never `--out`; an abbreviation is a
  usage error on the root parser and on every subcommand. Spell options in
  full in scripts.
- `-h`/`--help` is accepted at the root and at every command and prints text.
  `--version` is accepted only at the root (`actseal --version`); after a
  command it is a usage error.
- `--provider fixture` requires `--responses PATH`; `--provider laya` rejects
  `--responses`. `--offline` is accepted by both providers: for `laya` it
  selects the prepared offline cache, for `fixture` it states the adapter's
  existing network-free behaviour and changes nothing.
- The stable provider choices are `fixture` and `laya`. No other provider is
  selected implicitly. A provisional Jev transport, if a later release ships
  it, would require an explicit experimental flag and is not part of this
  reference; see [providers](providers.md).
- Output paths must be **new**. `lock --out`, `verify --out` and `demo --out`
  refuse an existing file, directory or symlink and never overwrite; the parent
  directory must already exist.
- Usage diagnostics name options, metavars and accepted choices. They never
  echo a command-line value, a path supplied by the operating system, a raw
  response body or arbitrary exception text.

## Exit codes

| Exit | Status | Meaning |
|---|---|---|
| 0 | `PASS` | Valid evidence satisfies the frozen contract. |
| 1 | `BLOCK` | Valid evidence establishes a risk or coverage limit violation, or a canonical fault violated its required action. |
| 2 | `INCONCLUSIVE` | Valid evidence proves neither `PASS` nor `BLOCK`. |
| 3 | `ERROR` | Invalid or incomplete evidence, a usage or setup error, an existing destination, an operating-system failure or an invalidated native-worker experiment. |

Two commands have special success semantics:

- `lock` has no verdict; it exits 0 when the lock was sealed and written.
- `demo` exits 0 only when its deliberately bad run is `BLOCK`, its fixed run
  is `PASS` and both fresh replays equal the recorded verdicts. Any other
  outcome is `ERROR` 3; the demo never relabels its bad run as a success.

`verify` and `replay` map the verdict directly to the exit code. A faithful
replay of `BLOCK` evidence therefore exits 1, and a faithful replay of a
diagnostic `ERROR` bundle exits 3. In a shell or CI step that stops on a
nonzero exit, inspect the recorded status instead of treating that exit as a
tool failure. Usage errors always exit 3, never argparse's default 2.

## Text and JSON output

Without `--json`, the report is human-readable text on stdout; warnings,
captured failure counts and advisory notes go to stderr. That wording is not a
stable interface. With `--json`, exactly one JSON object is written to stdout
and nothing else; warnings and failures become fields of that object.

Every JSON receipt, including every error and usage error, carries
`schema_version` (the integer `1`) and `command` (`lock`, `verify`, `replay`,
`demo`, or `actseal` when no command could be parsed). The field set of each
receipt shape is frozen for 1.x; no field is added to an existing shape within
1.x.

| Receipt | Fields |
|---|---|
| any error | `schema_version`, `command`, `exit_code` (3), `ok` (false), `status` (`"ERROR"`), `error` (sanitized message) |
| `lock` | `schema_version`, `command`, `exit_code` (0), `ok`, `lock_sha256`, `implementation_sha256`, `replay_engine_version`, `evidence_scope`, `contract`, `model_identity` {`provider`, `model`, `revision`, `adapter_version`, `normalizer_version`}, `verification_cases`, `calibration_cases`, `out` |
| `verify` | `schema_version`, `command`, the verdict fields (`status`, `reasons`, `total`, `accepted`, `errors`, `risk` {`lower`, `upper`}, `coverage` {`lower`, `upper`}, `evidence_scope`, `lock_sha256`), `failures` (failure code to count), `warnings` (warning code to count), `faults` (scenario id to {`action`, `expected_action`}), `exit_code`, `ok`, `out` |
| `replay` | `schema_version`, `command`, the verdict fields, `exit_code`, `ok`, `bundle`, `expected_lock_sha256` (string or null), `notes` (array of advisory strings; the actseal 0.1.0 legacy guidance when applicable, otherwise empty) |
| `demo` | `schema_version`, `command`, `exit_code`, `ok`, `status` (`PASS` or `ERROR`), `evidence_scope` (`demo`), `demo_only` (true), `note`, `out`, `duration_s`, `runs` {`bad`, `fixed`}; each run holds the verdict fields, `failures`, `warnings`, `faults`, `expected_status`, `as_expected`, `lock`, `evidence`, `replay` (a verdict object) and `replay_matches`, and has no `exit_code`, `ok` or `out` of its own |

`ok` is always `exit_code == 0`. Path-valued fields (`out`, `bundle`, `lock`,
`evidence`) echo the caller's own arguments; their formatting is not frozen.
`duration_s` is a measurement, not a performance promise.

## `lock`

```text
actseal lock [-h] --contract PATH --calibration PATH --verification PATH
             --provider {fixture,laya} [--responses PATH] [--offline]
             --out PATH [--json]
```

Reads and validates the contract TOML and both labelled JSONL splits, builds
the provider only to observe its identity, closes it, seals the lock and writes
one canonical lock document to the new file `--out`. No decision request is
sent. The receipt reports `lock_sha256`, the producer `implementation_sha256`,
`replay_engine_version` (`actseal-choice-v1`), the contract name and scope,
the observed model identity and both case counts.

## `verify`

```text
actseal verify [-h] --lock PATH --calibration PATH --verification PATH
               --provider {fixture,laya} [--responses PATH] [--offline]
               --out DIRECTORY [--json]
```

Decodes the lock, validates its seal and replay-engine compatibility, checks
that the supplied splits match the locked inventories, requires the requested
provider to equal the locked provider and the running package to be the exact
producer implementation, builds the provider, compares its complete observed
identity with the locked identity, captures every locked verification case
exactly once in lock order at the fixed 30-second request deadline, runs the
six canonical faults, assesses and publishes one new bundle under `--out`.

A setup failure before collection exits 3 without a bundle. Captured provider
failures during collection are terminal case records, not setup failures; the
run continues and the verdict decides their meaning. There is no deadline
override, retry, restart or replacement sample.

## `replay`

```text
actseal replay [-h] [--expected-lock-sha256 HEX] [--json] DIRECTORY
```

Recomputes the verdict of the bundle in `DIRECTORY` from its seven files
without importing a provider, loading a model or contacting a network. The
exit code is the recomputed verdict's code. Invalid evidence is an `ERROR`
verdict whose `reasons` name the violated invariant (for example
`integrity.bundle_hash` or `integrity.legacy_schema`); wrong Python-level
argument shapes such as a malformed digest are also exit 3.

`--expected-lock-sha256 HEX` compares the bundle's lock digest with a
64-character lowercase hex digest you obtained through a separately trusted
channel. A mismatch is `ERROR` with reason `integrity.expected_lock`. Reading
the digest out of the bundle you are checking provides no independent anchor,
and even a matching trusted digest does not authenticate response records or
prove execution took place.

A bundle written by actseal 0.1.0 (schema 1) is `ERROR` with reason
`integrity.legacy_schema`; the receipt's `notes` carry the pinned-replay
guidance from the [migration guide](migration.md).

## `demo`

```text
actseal demo [-h] --out NEW_DIRECTORY [--json]
```

Copies the packaged authored support-triage inputs into `NEW_DIRECTORY/inputs`,
then for each of the runs `bad` and `fixed` creates a lock bound to the
installed implementation, collects all 128 cases once, runs the six faults,
assesses, writes `NEW_DIRECTORY/<run>/evidence` and replays it against the
lock's digest. Every count, interval and verdict in the output is computed at
run time. The data is synthetic (`evidence_scope=demo`): it is not a population
benchmark, a trained or repaired model, or deployment certification. The
[example README](../examples/support_triage/README.md) documents the authored
rules.

## Related

- [Quickstart](quickstart.md): the three commands against the published
  package.
- [Concepts](concepts.md): what decisions, verdicts and scopes mean.
- [Python guide](python-api.md): the same protocol from Python.
- [Providers](providers.md): fixture and native Laya setup and limits.
